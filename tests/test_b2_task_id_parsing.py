"""Regression tests for B2 task_id fallback parsing.

Guards the bug where a hyphen-convention task_id (`en-enron-collapse-ep006`)
collapsed into one token, making market the entire id and silently selecting
Korean narration for an English episode.
"""
import pytest

from app.services import story_engine_b2 as b2


@pytest.fixture(autouse=True)
def no_external_lookups(tmp_path, monkeypatch):
    """Force the task_id-parsing fallback: no local cache, no Notion."""
    monkeypatch.setattr(b2, "PENDING_TASKS_DIR", str(tmp_path))
    monkeypatch.setattr(b2, "query_db", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("offline")))


LANG_FOR_MARKET = {"EN": "English", "JP": "Japanese", "KR": "Korean"}


class TestUnderscoreConvention:
    @pytest.mark.parametrize("task_id,market,topic", [
        ("EN_EP0204_milgram_obedience_system", "EN", "Milgram Obedience System"),
        ("JP_EP0007_livedoor_scandal", "JP", "Livedoor Scandal"),
        ("KR_EP0005_yoo_young_chul_case", "KR", "Yoo Young Chul Case"),
    ])
    def test_market_and_topic(self, task_id, market, topic):
        meta = b2.load_task_metadata(task_id)
        assert meta["market"] == market
        assert meta["topic"] == topic


class TestHyphenConvention:
    @pytest.mark.parametrize("task_id,market,topic", [
        ("en-enron-collapse-ep006", "EN", "Enron Collapse"),
        ("jp-livedoor-scandal-ep011", "JP", "Livedoor Scandal"),
        ("kr-hanbo-steel-ep003", "KR", "Hanbo Steel"),
    ])
    def test_market_and_topic(self, task_id, market, topic):
        meta = b2.load_task_metadata(task_id)
        assert meta["market"] == market
        assert meta["topic"] == topic

    def test_english_task_does_not_become_korean(self):
        """The exact failure mode: en- prefix must not fall through to Korean."""
        meta = b2.load_task_metadata("en-enron-collapse-ep006")
        assert LANG_FOR_MARKET[meta["market"].upper()] == "English"

    def test_episode_token_excluded_from_topic(self):
        meta = b2.load_task_metadata("en-enron-collapse-ep006")
        assert "ep006" not in meta["topic"].lower()


class TestUnknownPrefix:
    def test_unknown_market_defaults_to_en(self):
        meta = b2.load_task_metadata("xx-some-topic-ep001")
        assert meta["market"] == "EN"

    def test_bare_task_id_still_yields_a_topic(self):
        meta = b2.load_task_metadata("standalone")
        assert meta["topic"]
        assert meta["market"] == "EN"

    def test_market_case_is_normalised(self):
        assert b2.load_task_metadata("Jp-Some-Case-ep002")["market"] == "JP"
