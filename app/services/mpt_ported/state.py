"""MPT-G4: Idempotent stage decorator + Postgres episode state.

FIX 29/06: stages pass the full `episode` dict as the first positional arg,
but the decorator named it `episode_id`. _set did e.rsplit(...) on that dict
-> "'dict' object has no attribute 'rsplit'" / asyncpg "expected str, got dict".
_coerce_eid() now extracts a string id for all DB writes; fn() still receives
the original arg so stage signatures are unchanged.
"""
import asyncio, functools, os
from typing import Optional
_DB = os.getenv("DATABASE_URL","")

def _coerce_eid(x):
    """Stages may pass the whole episode dict; return a plain string episode_id."""
    if isinstance(x, dict):
        x = x.get("episode_id") or x.get("id") or ""
    return str(x)

async def _get(c,e,s):
    e=_coerce_eid(e)
    r=await c.fetchrow("SELECT stage_status FROM vf_episode_state WHERE episode_id=$1 AND current_stage=$2",e,s)
    return r["stage_status"] if r else None

async def _set(c,e,s,st):
    e=_coerce_eid(e); sid=e.rsplit("-ep",1)[0]
    await c.execute("INSERT INTO vf_episode_state (episode_id,series_id,current_stage,stage_status) VALUES ($1,$2,$3,$4) ON CONFLICT (episode_id) DO UPDATE SET current_stage=$3,stage_status=$4,updated_at=NOW()",e,sid,s,st)

def idempotent_stage(stage_name):
    def dec(fn):
        @functools.wraps(fn)
        async def wrapper(episode_id,*a,**kw):
            if not _DB: return await fn(episode_id,*a,**kw)
            _eid=_coerce_eid(episode_id)
            try:
                import asyncpg; conn=await asyncpg.connect(_DB)
                try:
                    st=await _get(conn,_eid,stage_name)
                    if st=="done":
                        # FLOW FIX 27/07/2026: returning None made callers crash
                        # ('NoneType' has no attribute 'get') and run_episode then
                        # silently degraded to a single fallback background clip.
                        if os.getenv("VF_IDEMPOTENT_SKIP", "0") == "1":
                            print(f"[idempotent] {stage_name} done-skip (pass-through)")
                            return episode_id
                        print(f"[idempotent] {stage_name} already done -> re-running (set VF_IDEMPOTENT_SKIP=1 to skip)")
                    await _set(conn,_eid,stage_name,"in_progress")
                finally: await conn.close()
            except Exception as e: print(f"[idempotent] DB err: {e} - run anyway")
            result=await fn(episode_id,*a,**kw)
            try:
                import asyncpg; conn=await asyncpg.connect(_DB); await _set(conn,_eid,stage_name,"done"); await conn.close()
            except Exception as e: print(f"[idempotent] update err: {e}")
            return result
        return wrapper
    return dec
