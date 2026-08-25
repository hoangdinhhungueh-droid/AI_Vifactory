"""Character reference store + lock - keeps KEY character/setting/object images
consistent across chapters & episodes of a series.

The 'lock' mechanism (user requirement): you don't have to prompt every image
up front, but the KEY images (character / setting / object) MUST stay identical
across chapters. So we SAVE them to a durable store and REUSE the locked image
as the Kie.ai reference on every later chapter -> the character looks the same.

Persistence: JSON DB (free, durable, testable). Optional R2 public hosting is
handled by image_gen (the public_url is just stored here).

Notion AI decides WHEN to lock (creative judgment). This module is the
mechanical store - pure stdlib, no network.

Data layout:
{
  "series": {
    "<series_id>": {
      "refs": {
        "<kind>:<name>": {name, kind, public_url, local_path, prompt,
                           locked, created, updated}
      }
    }
  }
}
"""
from __future__ import annotations

import json
import os
import tempfile
import time


def _db_path() -> str:
    return os.getenv("VF_CHARREFS_DB", "/root/video_factory/db/character_refs.json")


def _load() -> dict:
    p = _db_path()
    try:
        with open(p, "r") as f:
            data = json.load(f)
        if isinstance(data, dict) and "series" in data:
            return data
    except FileNotFoundError:
        pass
    except Exception:
        pass
    return {"series": {}}


def _save(data: dict) -> None:
    p = _db_path()
    os.makedirs(os.path.dirname(p), exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(p), suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp, p)  # atomic
    finally:
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except Exception:
                pass


def _norm(s: str) -> str:
    return " ".join(str(s or "").split()).strip()


def _key(name: str, kind: str) -> str:
    return f"{(kind or 'character').lower()}:{_norm(name).lower()}"


def _series(data: dict, series_id: str) -> dict:
    sid = _norm(series_id) or "_default"
    return data.setdefault("series", {}).setdefault(sid, {}).setdefault("refs", {})


def get_ref(series_id: str, name: str, kind: str = "character") -> dict | None:
    refs = _load().get("series", {}).get(_norm(series_id) or "_default", {}).get("refs", {})
    return refs.get(_key(name, kind))


def list_refs(series_id: str) -> list:
    refs = _load().get("series", {}).get(_norm(series_id) or "_default", {}).get("refs", {})
    return list(refs.values())


def save_ref(series_id: str, name: str, *, public_url=None, local_path=None,
             kind: str = "character", prompt=None, lock: bool = False) -> dict:
    data = _load()
    refs = _series(data, series_id)
    k = _key(name, kind)
    now = int(time.time())
    existing = refs.get(k, {})
    rec = {
        "name": _norm(name),
        "kind": (kind or "character").lower(),
        "public_url": public_url if public_url is not None else existing.get("public_url"),
        "local_path": local_path if local_path is not None else existing.get("local_path"),
        "prompt": prompt if prompt is not None else existing.get("prompt"),
        "locked": bool(existing.get("locked")) or bool(lock),
        "created": existing.get("created", now),
        "updated": now,
    }
    refs[k] = rec
    _save(data)
    return rec


def lock_ref(series_id: str, name: str, kind: str = "character") -> dict | None:
    data = _load()
    refs = _series(data, series_id)
    k = _key(name, kind)
    if k not in refs:
        return None
    refs[k]["locked"] = True
    refs[k]["updated"] = int(time.time())
    _save(data)
    return refs[k]


def is_locked(series_id: str, name: str, kind: str = "character") -> bool:
    rec = get_ref(series_id, name, kind)
    return bool(rec and rec.get("locked"))


def get_locked_url(series_id: str, name: str, kind: str = "character") -> str | None:
    """Return the locked public_url for reuse as a Kie reference, else None."""
    rec = get_ref(series_id, name, kind)
    if rec and rec.get("locked") and rec.get("public_url"):
        return rec["public_url"]
    return None


def locked_ref_urls(series_id: str, max_n: int = 8) -> list:
    """Up to `max_n` locked public_urls for this series (Kie.ai 8-ref input)."""
    urls = []
    for rec in list_refs(series_id):
        if rec.get("locked") and rec.get("public_url"):
            urls.append(rec["public_url"])
        if len(urls) >= max_n:
            break
    return urls


def primary_character_name(character_pack: list) -> str | None:
    """Best-effort: the first named character in the pack = the lock anchor."""
    for c in (character_pack or []):
        if isinstance(c, dict):
            nm = _norm(c.get("name") or c.get("id") or "")
        else:
            nm = _norm(c)
        if nm:
            return nm
    return None
