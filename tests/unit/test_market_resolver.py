"""tests/unit/test_market_resolver.py

Unit tests for core/market_resolver.py (Rule 128, 134).
Verifies:
1. Absent input raises ValueError fail-closed.
2. Aliases normalize strictly to canonical set {EN, JA, KR, VN}.
3. Invalid market codes raise ValueError fail-closed.
4. Precedence: explicit market_raw > ctx.manifest.market > ctx.config.market.
"""

from pathlib import Path

import pytest

from core.config import LimitsConfig, PipelineConfig, RenderConfig, RunContext, VideoGenConfig, VoiceConfig
from core.market_resolver import resolve_canonical_market
from core.paths import resolve_run_paths
from core.run_manifest import RunManifest


def test_market_resolver_absent_input_raises_value_error():
    """Fail-closed on absent market (Rule 118, 134)."""
    with pytest.raises(ValueError, match="No market specified"):
        resolve_canonical_market(None, ctx=None)

    # Context with None in both manifest and config
    paths = resolve_run_paths("test_run", repo_root=Path("."))
    manifest = RunManifest.create_new("test_run", profile="e2e_min")
    manifest.market = None
    cfg = PipelineConfig(
        name="test",
        market=None,
        limits=LimitsConfig(),
        video_generation=VideoGenConfig(),
        voice=VoiceConfig(),
        render=RenderConfig()
    )
    ctx = RunContext(
        run_id="test_run",
        paths=paths,
        manifest=manifest,
        config=cfg
    )
    with pytest.raises(ValueError, match="No market specified in manifest or config"):
        resolve_canonical_market(None, ctx=ctx)


def test_market_resolver_alias_normalization():
    """Normalizes market aliases strictly to {EN, JA, KR, VN}."""
    assert resolve_canonical_market("en") == "EN"
    assert resolve_canonical_market("EN") == "EN"
    assert resolve_canonical_market("ja") == "JA"
    assert resolve_canonical_market("JA") == "JA"
    assert resolve_canonical_market("jp") == "JA"
    assert resolve_canonical_market("JP") == "JA"
    assert resolve_canonical_market("ko") == "KR"
    assert resolve_canonical_market("KO") == "KR"
    assert resolve_canonical_market("kr") == "KR"
    assert resolve_canonical_market("KR") == "KR"
    assert resolve_canonical_market("vi") == "VN"
    assert resolve_canonical_market("VI") == "VN"
    assert resolve_canonical_market("vn") == "VN"
    assert resolve_canonical_market("VN") == "VN"


def test_market_resolver_invalid_code_raises_value_error():
    """Rejects unapproved market codes."""
    for bad in ["FR", "DE", "ES", "CN", "GLOBAL", "XYZ", "", "   "]:
        with pytest.raises(ValueError):
            resolve_canonical_market(bad)


def test_market_resolver_invalid_type_raises_type_error():
    """Fail-closed on invalid argument types with TypeError (Boss Round 6)."""
    for bad_type in [123, 45.6, ["EN"], {"foo": "bar"}, True]:
        with pytest.raises(TypeError, match="invalid market_raw type"):
            resolve_canonical_market(bad_type)


def test_market_resolver_precedence(tmp_path):
    """Precedence: explicit market_raw > manifest > config."""
    paths = resolve_run_paths("test_run_prec", repo_root=tmp_path)
    manifest = RunManifest.create_new("test_run_prec", profile="e2e_min")
    manifest.market = "KR"
    cfg = PipelineConfig(
        name="test_prec",
        market="JA",
        limits=LimitsConfig(),
        video_generation=VideoGenConfig(),
        voice=VoiceConfig(),
        render=RenderConfig()
    )
    ctx = RunContext(
        run_id="test_run_prec",
        paths=paths,
        manifest=manifest,
        config=cfg
    )

    # 1. Explicit raw market wins over manifest and config
    assert resolve_canonical_market("VN", ctx=ctx) == "VN"

    # 2. Manifest wins over config when raw is None
    assert resolve_canonical_market(None, ctx=ctx) == "KR"

    # 3. Config wins when manifest is None
    manifest.market = None
    assert resolve_canonical_market(None, ctx=ctx) == "JA"
