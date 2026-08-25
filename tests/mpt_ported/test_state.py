import sys; sys.path.insert(0,"/root/video_factory")
from app.services.mpt_ported.state import idempotent_stage
def test_callable(): assert callable(idempotent_stage)
def test_wraps():
    @idempotent_stage("s")
    async def dummy(eid): return "done"
    assert dummy.__name__=="dummy"
