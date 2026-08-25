import pytest,sys
sys.path.insert(0,"/root/video_factory")
from app.services.mpt_ported.audio_normalize import LUFS_TARGETS,TRUE_PEAK_MAX
def test_lufs_platforms():
    for p in ["spotify","youtube","tiktok","dailymotion","default"]: assert p in LUFS_TARGETS
    assert LUFS_TARGETS["spotify"]==-14.0; assert LUFS_TARGETS["dailymotion"]==-16.0
def test_true_peak(): assert TRUE_PEAK_MAX==-1.0
@pytest.mark.asyncio
async def test_missing_raises():
    from app.services.mpt_ported.audio_normalize import normalize_audio
    with pytest.raises(Exception): await normalize_audio("/tmp/no_vf.wav","/tmp/vf/out.wav")
