import pytest,sys
sys.path.insert(0,"/root/video_factory")
from app.services.mpt_ported.bgm_selector import MOOD_TO_GENRE,_get_genre,BGM_GENRES
def test_coverage():
    for m,g in MOOD_TO_GENRE.items(): assert g in BGM_GENRES
def test_known(): assert _get_genre("epic")=="epic"; assert _get_genre("HAPPY")=="happy"
def test_fallback(): assert _get_genre("xyz")=="epic"
@pytest.mark.integration
@pytest.mark.asyncio
async def test_filesystem():
    from pathlib import Path
    d=Path("/root/video_factory/assets/bgm")
    if not any(d.glob("*.mp3")): pytest.skip("no bgm")
    import app.services.mpt_ported.bgm_selector as bs; bs.BGM_CATALOG_DIR=str(d)
    from app.services.mpt_ported.bgm_selector import select_bgm
    r=await select_bgm("epic",60.0); assert "path" in r and "license_url" in r
