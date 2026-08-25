import pytest,sys
sys.path.insert(0,"/root/video_factory")
from app.services.mpt_ported.video_render import SEG_MAX_SEC,ASPECT_SIZES,_aspect_to_size,XFADE_DURATION
def test_seg(): assert SEG_MAX_SEC==3600
def test_xfade(): assert XFADE_DURATION==0.5
def test_portrait(): assert ASPECT_SIZES["9:16"]==(1080,1920)
def test_all_aspects():
    for a in ["9:16","16:9","1:1"]: w,h=_aspect_to_size(a); assert w>0 and h>0
def test_unknown(): assert _aspect_to_size("x")==(1080,1920)
@pytest.mark.asyncio
async def test_no_clips():
    from app.services.mpt_ported.video_render import render_video
    with pytest.raises(Exception): await render_video([],"/tmp/f.mp3","/tmp/vf/o.mp4")
