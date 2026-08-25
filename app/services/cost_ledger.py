"""Tiny append-only cost ledger (27/07/2026).

Why this exists: run_episode imported app.services.credit_gate, which does not
exist on this box, so _usage_summary stayed None and every Telegram "Episode
READY" card reported "est cost: $0.00" even after paid image generation
generations. Nothing here can raise: cost reporting must never break a render.

Storage: one JSONL file per UTC day under VF_COST_DIR (default /var/vf/cost).
Each line: {ts, kind, units, usd, episode_id, note}
"""
import json
import os
import time

LEDGER_DIR = os.environ.get("VF_COST_DIR", "/var/vf/cost")

# Unit prices in USD. Override any of them with env vars when pricing changes.
# of the current chain is free, but we still record the units so the breakdown
# shows what actually ran.
UNIT_USD = {
    "edge_tts_chars": 0.0,
    "whisper_minutes": 0.0,
    "remotion_render": 0.0,
    "serpapi_search": float(os.environ.get("VF_COST_SERPAPI", "0.005")),
    "llm_tokens_1k": float(os.environ.get("VF_COST_LLM_1K", "0.0")),
}


def _path(ts=None) -> str:
    day = time.strftime("%Y-%m-%d", time.gmtime(ts or time.time()))
    return os.path.join(LEDGER_DIR, day + ".jsonl")


def record(kind: str, units: float = 1.0, episode_id: str = "",
           usd=None, note: str = "") -> None:
    """Append one usage row. Never raises."""
    try:
        if usd is None:
            usd = UNIT_USD.get(kind, 0.0) * float(units)
        os.makedirs(LEDGER_DIR, exist_ok=True)
        row = {
            "ts": round(time.time(), 3),
            "kind": kind,
            "units": units,
            "usd": round(float(usd), 6),
            "episode_id": episode_id or "",
            "note": note[:120],
        }
        with open(_path(), "a", encoding="utf-8") as f:
            f.write(json.dumps(row) + "\n")
    except Exception:
        pass


def _rows(t_from: float = 0.0, t_to=None):
    t_to = t_to if t_to is not None else time.time()
    out = []
    try:
        days = {_path(t_from), _path(t_to)}
        for p in days:
            if not os.path.exists(p):
                continue
            with open(p, encoding="utf-8") as f:
                for line in f:
                    try:
                        r = json.loads(line)
                    except Exception:
                        continue
                    if t_from <= float(r.get("ts", 0)) <= float(t_to):
                        out.append(r)
    except Exception:
        return out
    return out


def cost_between(t_from: float, t_to=None, episode_id: str = ""):
    """Total USD in a time window, optionally filtered by episode_id."""
    try:
        rows = _rows(t_from, t_to)
        if episode_id:
            rows = [r for r in rows if r.get("episode_id") in ("", episode_id)]
        return round(sum(float(r.get("usd") or 0) for r in rows), 4)
    except Exception:
        return None


def breakdown_between(t_from: float, t_to=None) -> dict:
    """{kind: {units, usd}} for a time window - used in the Telegram card."""
    agg = {}
    try:
        for r in _rows(t_from, t_to):
            k = r.get("kind", "?")
            cur = agg.setdefault(k, {"units": 0.0, "usd": 0.0})
            cur["units"] += float(r.get("units") or 0)
            cur["usd"] = round(cur["usd"] + float(r.get("usd") or 0), 6)
    except Exception:
        pass
    return agg


def today_usd() -> float:
    day_start = time.mktime(time.strptime(
        time.strftime("%Y-%m-%d", time.gmtime()), "%Y-%m-%d"))
    return cost_between(day_start) or 0.0
