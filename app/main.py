# ── app/main.py — AI Video Factory API (v11.8 — canonical paste-đè toàn bộ) ──
# GET  /api/v1/health        → health check
# POST /api/v1/llm           → pipeline router cho n8n                [§1.3]
# POST /v1/chat/completions  → OC-V agent brain (tool-calling)        [§7.1 v11.8]
# GET  /v1/models            → model list
# GET  /v1/budget            → per-provider quota snapshot            [v10.1]
#
# v11.8 additions vs v9:
#   v10   — CHAT_UPSTREAMS vs REASONING_UPSTREAMS; is_heavy routing
#   v10.1 — Budget Gate: predictive per-provider LIMITS×SAFETY, _would_exceed, cooldowns
#   v11.8 — ① NOTION CAP (22→NOTION_KEEP, always); ② NOTION INTENT GATE (strip all
#            API-* when msg doesn't mention Notion; bypass x-vf-autonomous:1);
#            DUMP_SYS (env DUMP_SYS=1 → breakdown san(sys) by header)

import os, json, re, time
import requests as _rq
from datetime import datetime, timezone
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

app = FastAPI(title="AI Video Factory API", version="v11.8")

# --- Prometheus metrics endpoint (G6-8) ---
try:
    from prometheus_client import generate_latest, CONTENT_TYPE_LATEST, CollectorRegistry, REGISTRY
    from fastapi.responses import Response as _Resp
    @app.get("/metrics")
    def metrics_endpoint():
        return _Resp(content=generate_latest(REGISTRY), media_type=CONTENT_TYPE_LATEST)
except ImportError:
    pass

# ── Health ───────────────────────────────────────────────────────────────────
@app.get("/api/v1/health")
def health():
    return {"status": "ok"}

@app.get("/api/v1/diag")
def diag():
    """Provider audit & health diagnostics via ModelGateway."""
    try:
        from app.services.model_gateway import get_global_gateway
        gw = get_global_gateway()
        return {
            "status": "ok",
            "provider": "hhtech_gateway",
            "model": gw.hhtech_model,
            "cost_summary": gw.cost_tracker.monthly_report() if gw.cost_tracker else {},
        }
    except Exception as e:
        return {"status": "error", "reason": str(e)}

# ── §1.3 Pipeline LLM endpoint (ModelGateway + Cost Tracking) ────────────────
class LLMRequest(BaseModel):
    prompt: str
    task_type: str = "SETUP_ORCHESTRATE"
    system: str = ""

@app.post("/api/v1/llm")
def call_llm(req: LLMRequest):
    from app.services.model_gateway import get_global_gateway
    gw = get_global_gateway()
    text = gw.call_llm(prompt=req.prompt, system_prompt=req.system)
    return {"text": text, "model": gw.hhtech_model, "provider": "hhtech"}

# ── §7.1 OC-V agent brain: OpenAI-compatible chat (v11.8) ────────────────────
_BROWSER_UA = os.getenv(
    "BENCH_UA",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
)

# v10 — tách CHAT vs REASONING upstreams
CHAT_UPSTREAMS = [
    {"name": "hhtech", "base": os.getenv("HHTECH_BASE_URL", "https://hhtechapi.com/v1"),
     "key": os.getenv("HHTECH_API_KEY", ""),
     "model": "claude-sonnet-5-5"},                         # PRIMARY: Claude Sonnet 5.5 via HHTech
    {"name": "openrouter", "base": "https://openrouter.ai/api/v1",
     "key": os.getenv("OPENROUTER_API_KEY", ""),
     "model": "nvidia/nemotron-3-nano-30b-a3b:free"},
    {"name": "mistral", "base": os.getenv("MISTRAL_BASE_URL", "https://api.mistral.ai/v1"),
     "key": os.getenv("MISTRAL_API_KEY", ""),
     "model": os.getenv("MISTRAL_MODEL", "mistral-medium-latest")},
    {"name": "cerebras", "base": os.getenv("CEREBRAS_BASE_URL", "https://api.cerebras.ai/v1"),
     "key": os.getenv("CEREBRAS_API_KEY", ""),
     "model": "gpt-oss-120b"},                              # ctx cap ~64K
    {"name": "gemini", "base": "https://generativelanguage.googleapis.com/v1beta/openai",
     "key": os.getenv("GEMINI_API_KEY", ""),
     "model": os.getenv("GEMINI_MODEL_25FL", "gemini-2.5-flash")},
    {"name": "onmay",  "base": os.getenv("ONMAY_BASE_URL", "").rstrip("/"),
     "key": os.getenv("ONMAY_API_KEY", ""),
     "model": os.getenv("GEMINI_MODEL", "gemini-2.5-flash")},  # LUÔN CUỐI
]

REASONING_UPSTREAMS = [
    {"name": "hhtech",   "base": os.getenv("HHTECH_BASE_URL", "https://hhtechapi.com/v1"),
     "key": os.getenv("HHTECH_API_KEY", ""), "model": "claude-sonnet-5-5"},
    {"name": "cerebras", "base": os.getenv("CEREBRAS_BASE_URL", "https://api.cerebras.ai/v1"),
     "key": os.getenv("CEREBRAS_API_KEY", ""), "model": "gpt-oss-120b"},
    {"name": "mistral",  "base": os.getenv("MISTRAL_BASE_URL", "https://api.mistral.ai/v1"),
     "key": os.getenv("MISTRAL_API_KEY", ""),
     "model": os.getenv("MISTRAL_MODEL", "mistral-medium-latest")},
    {"name": "gemini",   "base": "https://generativelanguage.googleapis.com/v1beta/openai",
     "key": os.getenv("GEMINI_API_KEY", ""),
     "model": os.getenv("GEMINI_MODEL_25FL", "gemini-2.5-flash")},
    {"name": "openrouter","base": "https://openrouter.ai/api/v1",
     "key": os.getenv("OPENROUTER_API_KEY", ""),
     "model": "nvidia/nemotron-3-nano-30b-a3b:free"},
    {"name": "onmay",    "base": os.getenv("ONMAY_BASE_URL", "").rstrip("/"),
     "key": os.getenv("ONMAY_API_KEY", ""),
     "model": os.getenv("GEMINI_MODEL", "gemini-2.5-flash")},
]

# ── v10.1 Budget Gate ─────────────────────────────────────────────────────────
# Predictive: skip provider BEFORE calling if _would_exceed; no 429 round-trip.
# Cooldown per limit type: per-min=60s, per-day=3600s.
SAFETY = float(os.getenv("BUDGET_SAFETY", "0.85"))
LIMITS = {
    #                  tpm     rpm   rpd       tpd
    "openrouter":  {"tpm": 0,  "rpm": 20,  "rpd": 1000,   "tpd": 0},
    "cerebras":    {"tpm": 60000, "rpm": 30, "rpd": 0,    "tpd": 1_000_000},
    "gemini":      {"tpm": 250000,"rpm": 0,  "rpd": 1500, "tpd": 0},
    "mistral":     {"tpm": 0,  "rpm": 60,  "rpd": 0,      "tpd": 0},
    "onmay":       {"tpm": 0,  "rpm": 0,   "rpd": 200,    "tpd": 0},
}
_budget_state: dict = {}   # {provider: {"min_calls":0, "min_tokens":0, "day_calls":0, "day_tokens":0, "min_reset":0, "day_reset":0}}

def _gate(provider: str) -> dict:
    now = time.time()
    s = _budget_state.setdefault(provider, {
        "min_calls": 0, "min_tokens": 0, "day_calls": 0, "day_tokens": 0,
        "min_reset": now + 60, "day_reset": now + 86400,
    })
    if now > s["min_reset"]:
        s["min_calls"] = 0; s["min_tokens"] = 0; s["min_reset"] = now + 60
    if now > s["day_reset"]:
        s["day_calls"] = 0; s["day_tokens"] = 0; s["day_reset"] = now + 86400
    return s

def _would_exceed(provider: str, est_tok: int) -> str | None:
    """Return reason string if provider would exceed SAFETY limit; else None."""
    lim = LIMITS.get(provider)
    if not lim:
        return None
    s = _gate(provider)
    if lim["rpm"] and s["min_calls"] + 1 > lim["rpm"] * SAFETY:
        return f"near rpm limit ({s['min_calls']}/{lim['rpm']})"
    if lim["tpm"] and s["min_tokens"] + est_tok > lim["tpm"] * SAFETY:
        return f"near tpm limit"
    if lim["rpd"] and s["day_calls"] + 1 > lim["rpd"] * SAFETY:
        return f"near rpd limit ({s['day_calls']}/{lim['rpd']})"
    if lim["tpd"] and s["day_tokens"] + est_tok > lim["tpd"] * SAFETY:
        return f"near tpd limit"
    return None

def _record(provider: str, tok: int):
    s = _gate(provider)
    s["min_calls"] += 1; s["min_tokens"] += tok
    s["day_calls"] += 1; s["day_tokens"] += tok

@app.get("/v1/budget")
def budget_snapshot():
    now = time.time()
    out = {}
    for p in LIMITS:
        s = _gate(p)
        out[p] = {
            "min_calls": s["min_calls"], "min_tokens": s["min_tokens"],
            "day_calls": s["day_calls"], "day_tokens": s["day_tokens"],
            "min_resets_in": max(0, int(s["min_reset"] - now)),
            "day_resets_in": max(0, int(s["day_reset"] - now)),
        }
    return out

# ── NOTION GATE helpers ───────────────────────────────────────────────────────
# ① NOTION CAP — unconditional: keep only NOTION_KEEP tools from API-* (22 → 4)
NOTION_KEEP = set(os.getenv("NOTION_KEEP",
    "API-post-search,API-retrieve-a-page,API-query-data-source,API-get-block-children"
).split(","))

# ② NOTION INTENT GATE — strip ALL API-* when message doesn't mention Notion
NOTION_GATE_ENABLED = os.getenv("NOTION_GATE_ENABLED", "1") == "1"
NOTION_RE = re.compile(
    r"\bnotion\b|notion\s*db|trang notion|database|tìm trang|đọc page|ghi page"
    r"|query|block|workspace|agent queue|update notion|write notion",
    re.I,
)

def _apply_notion_gates(body: dict, last_user: str | None, autonomous: bool) -> dict:
    tools = body.get("tools")
    if not tools:
        return body

    # ① NOTION CAP: strip API-* not in NOTION_KEEP (always, unconditional)
    tools = [t for t in tools
             if not t.get("function", {}).get("name", "").startswith("API-")
             or t["function"]["name"] in NOTION_KEEP]

    # ② NOTION INTENT GATE: if enabled + not autonomous + not in tool-loop + no Notion mention → strip all API-*
    if NOTION_GATE_ENABLED and not autonomous and last_user is not None:
        # Defensive: ensure last_user is string (edge case: API can send nested list structures)
        if isinstance(last_user, list):
            last_user_str = " ".join(
                p.get("text", "") if isinstance(p, dict) else str(p)
                for p in last_user
            )
        else:
            last_user_str = str(last_user) if last_user else ""
        
        if last_user_str and not NOTION_RE.search(last_user_str):
            tools = [t for t in tools
                     if not t.get("function", {}).get("name", "").startswith("API-")]
            print("[gate:②] stripped all API-* (no Notion intent in last_user)", flush=True)

    body = dict(body)
    body["tools"] = tools
    if not tools:
        body.pop("tool_choice", None)
    return body

# ── DUMP_SYS helper ───────────────────────────────────────────────────────────
def _dump_sys(messages: list):
    """If DUMP_SYS=1, print system prompt breakdown by heading to logs + /tmp/sys_dump.txt"""
    if os.getenv("DUMP_SYS") != "1":
        return
    sys_msgs = [m for m in messages if m.get("role") == "system"]
    if not sys_msgs:
        return
    sys_text = "\n".join(m.get("content", "") for m in sys_msgs)
    tok_total = len(sys_text) // 4
    # breakdown by ## heading
    sections = re.split(r"(^#{1,3} .+$)", sys_text, flags=re.M)
    lines = [f"=== DUMP_SYS: san(sys)={tok_total} tok total ==="]
    current = "preamble"
    buf = []
    for seg in sections:
        if re.match(r"^#{1,3} ", seg):
            if buf:
                lines.append(f"  [{current}] ~{len(' '.join(buf))//4} tok")
            current = seg.strip()
            buf = []
        else:
            buf.append(seg)
    if buf:
        lines.append(f"  [{current}] ~{len(' '.join(buf))//4} tok")
    out = "\n".join(lines)
    print(out, flush=True)
    try:
        with open("/tmp/sys_dump.txt", "w") as f:
            f.write(out + "\n")
    except Exception:
        pass

# ── SSE helper (MUST be above @app.post decorator — lesson 04/06) ─────────────
def _fake_sse(data):
    choice = (data.get("choices") or [{}])[0]
    msg = choice.get("message") or {}
    chunk = {
        "id": data.get("id", "chatcmpl-local"),
        "object": "chat.completion.chunk",
        "created": data.get("created", 0),
        "model": data.get("model", "auto"),
        "choices": [{"index": 0,
                     "delta": {"role": "assistant", "content": msg.get("content") or ""},
                     "finish_reason": None}],
    }
    if msg.get("tool_calls"):
        chunk["choices"][0]["delta"]["tool_calls"] = msg["tool_calls"]
    yield "data: " + json.dumps(chunk) + "\n\n"
    done = {
        "id": chunk["id"], "object": "chat.completion.chunk",
        "created": chunk["created"], "model": chunk["model"],
        "choices": [{"index": 0, "delta": {},
                     "finish_reason": choice.get("finish_reason", "stop")}],
    }
    yield "data: " + json.dumps(done) + "\n\n"
    yield "data: [DONE]\n\n"

# ── Main chat handler ─────────────────────────────────────────────────────────
@app.post("/v1/chat/completions")
async def oai_chat_completions(request: Request):
    body = await request.json()           # raw JSON — KHÔNG Pydantic → không 422
    autonomous = request.headers.get("x-vf-autonomous") == "1"

    _wants_stream = bool(body.get("stream"))   # CAPTURE trước khi pop (SDK mac dinh stream=true)
    body.pop("stream", None)

    # strip OpenAI-only fields (gemini/cerebras 400, mistral 422)
    for _k in ("store", "metadata", "service_tier", "reasoning_effort",
               "prompt_cache_key", "safety_identifier", "stream_options"):
        body.pop(_k, None)

    msgs     = body.get("messages") or []
    est      = len(json.dumps(body)) // 4
    tool_msgs = sum(1 for m in msgs if m.get("role") == "tool")

    # DUMP_SYS breakdown (env DUMP_SYS=1)
    _dump_sys(msgs)

    # last_user message (for NOTION GATE ②)
    _raw = next(
        (m.get("content") for m in reversed(msgs) if m.get("role") == "user"), None
    )
    if isinstance(_raw, list):
        last_user = " ".join(p.get("text", "") for p in _raw if isinstance(p, dict))
    elif isinstance(_raw, str):
        last_user = _raw
    else:
        last_user = None

    # ① + ② NOTION GATES
    body = _apply_notion_gates(body, last_user, autonomous)

    # loop-guard v9.1: tool_msgs>=4 or est>30000 → strip tools, force text
    if tool_msgs >= 4 or est > 30000:
        body.pop("tools", None); body.pop("tool_choice", None)
        print(f"[loop-guard] stripped tools (tool_msgs={tool_msgs} est={est}) → force text", flush=True)

    # v10: is_heavy → REASONING chain; else CHAT chain
    is_heavy = tool_msgs >= 1 or est > 20000
    upstreams = REASONING_UPSTREAMS if is_heavy else CHAT_UPSTREAMS
    chain_name = "reasoning" if is_heavy else "chat"

    n_msgs  = len(msgs)
    n_tools = len(body.get("tools") or [])
    last_err = None

    for up in upstreams:
        if not up["key"] or not up["base"]:
            print(f"[{chain_name}] skip {up['name']}: missing key/base", flush=True)
            continue

        # v10.1 Budget Gate: skip if _would_exceed
        reason = _would_exceed(up["name"], est)
        if reason:
            print(f"[gate] skip {up['name']}: {reason} → next tier", flush=True)
            continue

        payload = dict(body)
        payload["model"] = up["model"]
        payload["stream"] = False

        try:
            r = _rq.post(
                f"{up['base']}/chat/completions",
                headers={
                    "Authorization": f"Bearer {up['key']}",
                    "Content-Type": "application/json",
                    "User-Agent": _BROWSER_UA,
                },
                json=payload, timeout=300,
            )
            if r.status_code >= 400:
                last_err = f"{up['name']} {r.status_code}: {r.text[:800]}"
                print(f"[{chain_name}] FAIL {up['name']} (msgs={n_msgs} tools={n_tools}) → {last_err}", flush=True)
                continue
            try:
                data = r.json()
            except Exception:
                last_err = f"{up['name']} BADJSON {r.status_code} ct={r.headers.get('content-type')}"
                print(f"[{chain_name}] BADJSON {up['name']} → {last_err}", flush=True)
                continue

            # record usage for Budget Gate
            used_tok = (data.get("usage") or {}).get("total_tokens", est)
            _record(up["name"], used_tok)

            print(f"[{chain_name}] OK via {up['name']} ({up['model']}) msgs={n_msgs} tools={n_tools}", flush=True)
            if _wants_stream:
                return StreamingResponse(_fake_sse(data), media_type="text/event-stream")
            return JSONResponse(data)

        except Exception as e:
            last_err = f"{up['name']} ERR: {e}"
            print(f"[{chain_name}] EXC {last_err}", flush=True)
            continue

    print(f"[{chain_name}] 502 ALL UPSTREAMS FAILED | last_err={last_err}", flush=True)
    return JSONResponse(
        status_code=502,
        content={"error": {"message": last_err or "no upstream available"}},
    )

@app.get("/v1/models")
def oai_models():
    return {"object": "list", "data": [{"id": "auto", "object": "model", "owned_by": "vpsRouter"}]}

# S1 trend scoring + pipeline entrypoint (page 03/05 spec, 2026-06-12)
# DISABLED 28/07/2026: legacy CPM/niche S1 scorer (pre-dates trend_gate_ai.py
# 26/07 redesign). Not wired into current raw-pool/gate flow; no active cron,
# n8n workflow, or celery beat calls it (verified). Disabled to stop duplicate
# "TREND_READY" Telegram noti alongside the RAW POOL / GATE noti. Kept
# importable (app.tasks still imports score_pipeline_run), just not routed.
# from app.s1_score import router as s1_router
# app.include_router(s1_router)

from app.routes.mpt_g5 import router as mpt_g5_router
app.include_router(mpt_g5_router)

# -- S2 run-episode route (full pipeline) --------------------------------
from app.routes.run_episode_route import router as run_episode_router
from app.routes.produce_episode_route import router as produce_episode_router
app.include_router(run_episode_router)
app.include_router(produce_episode_router)

# Trend/keyword discovery engine (free crawl + SerpApi-confirm top-N), 18/06
# REMOVED 27/07/2026: trend_discovery.py (v3) is superseded by discover-v5
# (repointed 26/06; discover-v5 is the sole live n8n cron target and the
# only Notion-AI-gated writer). File renamed to .deprecated_<ts> for
# rollback safety; no longer imported or routed.

from app import log_redact  # noqa: F401  # mask api_key in logs (b)
from app import log_redact  # noqa: F401  (mask api_key in logs)

# discover-digest router (N1, 18/06)
# ARCHIVED 09/08/2026 Phase-1: trend_digest router retired (v3 flow superseded)
# ARCHIVED 09/08/2026 Phase-1: trend_digest include removed

# DISABLED 22/07 - trend_reasoning superseded by Smart Trend-Keyword Cache Gate1/Gate2
# (stops unwanted 'VF REASONING' Telegram spam). Kept importable, just not routed.
# from app.services.trend_reasoning import router as _reason_router
# app.include_router(_reason_router)


# -- Telegram inline-button poller (two-way approval loop, Phase 4) ---------
try:
    from app.services.telegram_poller import start_poller as _vf_start_tg_poller

    @app.on_event("startup")
    async def _vf_startup_tg_poller():
        try:
            _vf_start_tg_poller()
        except Exception as _e:  # noqa: BLE001
            import logging as _lg
            _lg.getLogger("app.main").warning("tg poller start failed: %s", _e)
except Exception as _e:  # noqa: BLE001
    import logging as _lg
    _lg.getLogger("app.main").warning("tg poller import failed: %s", _e)


# DISABLED 28/07/2026: discover-v5 fully superseded by trend_gate_ai.py
# (/api/v1/trend-raw + /api/v1/trend-commit, 26/07 "Notion AI is the crawl
# brain" redesign). VPS cron that called this was already disabled 26/07
# (see /etc/crontab). Also disabled because _persist_brain_v5() writes
# accepted candidates DIRECTLY to the Notion Brain DB, bypassing the gate -
# conflicts with "Notion AI gate is the ONLY library writer" design. Kept
# importable, just not routed, to stop duplicate "DISCOVER-v5"/"RAW POOL"
# Telegram noti and prevent unreviewed writes.
# from app.services.trend_discovery_v5 import router as _discover_v5_router
# app.include_router(_discover_v5_router)


# Notion AI = crawl brain + curation gate (26/07/2026): /api/v1/trend-raw + /api/v1/trend-commit
from app.services.trend_gate_ai import router as _trend_gate_router
from app.services.trend_verify import router as _trend_verify_router
app.include_router(_trend_gate_router)
app.include_router(_trend_verify_router)
# Phase 2b (10/08/2026): story-check endpoint — gate story from Story
# Library body, write scores back to Notion (Luong chuan v1 BUOC 3).
from app.services.story_check import router as _story_check_router
app.include_router(_story_check_router)
# Phase 2b (10/08/2026): generate-images endpoint — compile from Notion
# then BG/FG generation + chroma-key (Rule 76) + R2 + IAL rows (BUOC 6).
from app.services.episode_images import router as _episode_images_router
app.include_router(_episode_images_router)
# Phase 2b (10/08/2026): preflight endpoint — combined green-light gate
# before render (compile --require-images + hash match + duration + TTS).
from app.services.preflight_episode import router as _preflight_router
app.include_router(_preflight_router)




from app.services.artifact_sync import router as _sync_router
app.include_router(_sync_router)
