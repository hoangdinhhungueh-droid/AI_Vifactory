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

import hmac
import json
import logging as _logging
import os
import re
import time
from contextlib import asynccontextmanager
from pathlib import Path

import requests as _rq
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

from app import log_redact  # noqa: F401
from app.routes.mpt_g5 import router as mpt_g5_router
from app.services.artifact_sync import router as _sync_router
from app.services.episode_images import router as _episode_images_router
from app.services.preflight_episode import router as _preflight_router
from app.services.story_check import router as _story_check_router
from app.services.trend_gate_ai import router as _trend_gate_router
from app.services.trend_verify import router as _trend_verify_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Security posture check on startup (Rule 121 & Boss Round 4 Item 5)
    token = os.getenv("VF_API_TOKEN", "").strip() or VF_API_TOKEN
    if not token:
        _logger.warning(
            "[STARTUP AUDIT] VF_API_TOKEN is unset in environment. Requests will fail-closed with 401 Unauthorized unless VF_ALLOW_UNAUTH_LOOPBACK=1 is explicitly configured for local loopback IPC."
        )
    # Telegram inline-button poller startup (Phase 4)
    try:
        from app.services.telegram_poller import start_poller as _vf_start_tg_poller
        _vf_start_tg_poller()
    except Exception as _e:
        _logger.error("Telegram poller startup failed during lifespan init: %s", _e, exc_info=True)
    yield

app = FastAPI(title="AI Video Factory API", version="v11.8", lifespan=lifespan)

# --- Prometheus metrics endpoint (G6-8) ---
try:
    from fastapi.responses import Response as _Resp
    from prometheus_client import CONTENT_TYPE_LATEST, REGISTRY, generate_latest
    @app.get("/metrics")
    def metrics_endpoint():
        return _Resp(content=generate_latest(REGISTRY), media_type=CONTENT_TYPE_LATEST)
except ImportError as _p_err:
    _logging.getLogger("app.main").debug("Prometheus client not installed, skipping /metrics: %s", _p_err)

_logger = _logging.getLogger("app.main")


_CACHED_GIT_SHA: str | None = None


def _resolve_git_sha() -> str:
    """Resolves git commit SHA dynamically from env or disk git rev-parse HEAD.
    Cached once per process to prevent unbounded subprocess overhead (Rule 126/138).
    """
    global _CACHED_GIT_SHA
    if _CACHED_GIT_SHA is not None:
        return _CACHED_GIT_SHA

    env_sha = os.getenv("GIT_COMMIT_SHA", "").strip()
    if env_sha:
        _CACHED_GIT_SHA = env_sha
        return _CACHED_GIT_SHA

    try:
        import subprocess
        sha = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=Path(__file__).resolve().parent.parent,
            stderr=subprocess.DEVNULL
        ).decode().strip()
        if sha:
            _CACHED_GIT_SHA = sha
            return _CACHED_GIT_SHA
    except Exception as exc:
        _logger.warning("Failed to resolve git_sha via git rev-parse: %s", exc)

    _CACHED_GIT_SHA = "unknown"
    return _CACHED_GIT_SHA


# ── Health ───────────────────────────────────────────────────────────────────
@app.get("/api/v1/health")
def health(request: Request):
    """Health check endpoint.
    Drops git_sha for unauthenticated external requests (Boss Round 12 Item 8).
    Includes git_sha for authenticated callers, verified loopback, or test clients.
    """
    token = os.getenv("VF_API_TOKEN", "").strip() or VF_API_TOKEN
    auth_header = request.headers.get("Authorization", "")
    client_host = getattr(getattr(request, "client", None), "host", "")
    has_forwarded = bool(request.headers.get("x-forwarded-for") or request.headers.get("cf-connecting-ip"))
    is_loopback = client_host in ("127.0.0.1", "::1", "localhost", "testclient", "") and not has_forwarded

    is_authed = False
    if token and auth_header and hmac.compare_digest(auth_header.encode("utf-8"), f"Bearer {token}".encode("utf-8")):
        is_authed = True
    elif is_loopback or os.getenv("VF_ALLOW_PUBLIC_HEALTH_GIT_SHA") == "1":
        is_authed = True

    resp: dict[str, Any] = {"status": "ok"}
    if is_authed:
        resp["git_sha"] = _resolve_git_sha()
    return resp

# ── Auth Helper ─────────────────────────────────────────────────────────────
VF_API_TOKEN = os.getenv("VF_API_TOKEN", "").strip()
_last_unset_token_log_time: float = 0.0


def _verify_auth(request: Request) -> None:
    """Verifies Bearer token.
    Fail-closed posture: If VF_API_TOKEN is unset, rejects requests with 401 Unauthorized
    unless VF_ALLOW_UNAUTH_LOOPBACK=1 or ALLOW_UNAUTHENTICATED_LOOPBACK=1 is explicitly configured.
    Rate limits unset-token warning to once per 60 seconds.
    Uses timing-safe hmac.compare_digest (Rule 121/125 & Boss Item 25).
    """
    global _last_unset_token_log_time
    token = os.getenv("VF_API_TOKEN", "").strip() or VF_API_TOKEN
    client_host = getattr(getattr(request, "client", None), "host", "")
    has_forwarded = bool(request.headers.get("x-forwarded-for") or request.headers.get("cf-connecting-ip"))
    is_loopback = client_host in ("127.0.0.1", "::1", "localhost") and not has_forwarded

    if not token:
        allow_loopback = (
            os.getenv("VF_ALLOW_UNAUTH_LOOPBACK") == "1"
            or os.getenv("ALLOW_UNAUTHENTICATED_LOOPBACK") == "1"
        )
        now = time.time()
        if now - _last_unset_token_log_time >= 60.0:
            _last_unset_token_log_time = now
            if allow_loopback and is_loopback:
                _logger.warning(
                    f"[SECURITY ALERT] VF_API_TOKEN is unset. Loopback unauthenticated bypass is active; verified loopback call from {client_host} permitted."
                )
            else:
                _logger.critical(
                    f"[SECURITY ALERT] VF_API_TOKEN is unset or caller {client_host} is non-loopback. Rejecting request (fail-closed)."
                )
        if not (allow_loopback and is_loopback):
            raise HTTPException(
                status_code=401,
                detail="Unauthorized: server authentication token not configured or non-loopback caller (fail-closed)",
            )
        return

    auth_header = request.headers.get("Authorization", "")
    expected = f"Bearer {token}"
    if not hmac.compare_digest(auth_header.encode("utf-8"), expected.encode("utf-8")):
        raise HTTPException(
            status_code=401,
            detail="Unauthorized: invalid or missing Bearer token",
        )


# --- Prometheus metrics endpoint (G6-8, gated by _verify_auth - Boss Round 12 Item 8) ---
try:
    from fastapi.responses import Response as _Resp
    from prometheus_client import CONTENT_TYPE_LATEST, REGISTRY, generate_latest
    @app.get("/metrics", dependencies=[Depends(_verify_auth)])
    def metrics_endpoint():
        return _Resp(content=generate_latest(REGISTRY), media_type=CONTENT_TYPE_LATEST)
except ImportError as _p_err:
    _logging.getLogger("app.main").debug("Prometheus client not installed, skipping /metrics: %s", _p_err)



@app.get("/api/v1/diag", dependencies=[Depends(_verify_auth)])
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
        _logger.error("Diagnostic failure in /api/v1/diag: %s", e)
        return JSONResponse(
            status_code=503,
            content={"status": "error", "reason": "Diagnostic failure"},
        )

# ── §1.3 Pipeline LLM endpoint (ModelGateway + Cost Tracking) ────────────────
class LLMRequest(BaseModel):
    prompt: str
    task_type: str = "SETUP_ORCHESTRATE"
    system: str = ""

@app.post("/api/v1/llm")
def call_llm(req: LLMRequest, request: Request):
    """Pipeline router for n8n/local agents.

    Security posture: Bound strictly to 127.0.0.1:8000 localhost loopback for internal
    IPC and n8n workflows. When VF_API_TOKEN is set in environment, Bearer token
    authentication is enforced (Rule 121 application security).
    """
    _verify_auth(request)
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
        s["min_calls"] = 0
        s["min_tokens"] = 0
        s["min_reset"] = now + 60
    if now > s["day_reset"]:
        s["day_calls"] = 0
        s["day_tokens"] = 0
        s["day_reset"] = now + 86400
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
        return "near tpm limit"
    if lim["rpd"] and s["day_calls"] + 1 > lim["rpd"] * SAFETY:
        return f"near rpd limit ({s['day_calls']}/{lim['rpd']})"
    if lim["tpd"] and s["day_tokens"] + est_tok > lim["tpd"] * SAFETY:
        return "near tpd limit"
    return None

def _record(provider: str, tok: int):
    s = _gate(provider)
    s["min_calls"] += 1
    s["min_tokens"] += tok
    s["day_calls"] += 1
    s["day_tokens"] += tok

@app.get("/v1/budget", dependencies=[Depends(_verify_auth)])
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

def _apply_notion_gates(body: dict, last_user: str | list | None, autonomous: bool) -> dict:
    tools = body.get("tools")
    if not tools:
        return body

    # Normalize last_user if list or other structure (Rule 121 & Boss Item 25)
    user_text = ""
    if isinstance(last_user, list):
        user_text = " ".join(
            p.get("text", "") if isinstance(p, dict) else str(p)
            for p in last_user
        )
    elif isinstance(last_user, str):
        user_text = last_user
    elif last_user is not None:
        user_text = str(last_user)

    # ① NOTION CAP: strip API-* not in NOTION_KEEP (always, unconditional)
    tools = [t for t in tools
             if not t.get("function", {}).get("name", "").startswith("API-")
             or t["function"]["name"] in NOTION_KEEP]

    # ② NOTION INTENT GATE: if enabled + not autonomous + not in tool-loop + no Notion mention → strip all API-*
    if NOTION_GATE_ENABLED and not autonomous and user_text:
        if not NOTION_RE.search(user_text):
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
    except Exception as exc:
        _logger.debug("Failed writing /tmp/sys_dump.txt: %s", exc)

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
    """OpenAI-compatible chat completions proxy for local agent brains.

    Security posture: Bound to 127.0.0.1:8000 localhost loopback. When VF_API_TOKEN
    is configured in environment, Bearer token authentication is enforced.
    """
    _verify_auth(request)
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
        body.pop("tools", None)
        body.pop("tool_choice", None)
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

# Modular sub-routers for specialized pipeline services (MPT, Trend, Story, Sync)
# Note: app.s1_score router was decommissioned on 28/07/2026 to prevent duplicate alerts (Rule 125 Single Truth).
app.include_router(mpt_g5_router, dependencies=[Depends(_verify_auth)])
app.include_router(_trend_gate_router, dependencies=[Depends(_verify_auth)])
app.include_router(_trend_verify_router, dependencies=[Depends(_verify_auth)])
app.include_router(_story_check_router, dependencies=[Depends(_verify_auth)])
app.include_router(_episode_images_router, dependencies=[Depends(_verify_auth)])
app.include_router(_preflight_router, dependencies=[Depends(_verify_auth)])
app.include_router(_sync_router, dependencies=[Depends(_verify_auth)])

