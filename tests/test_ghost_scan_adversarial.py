#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/test_ghost_scan_adversarial.py — Adversarial Verification of Anti-Ghost Scanner (Rule 125 & Boss Item 8).

Verifies that tools/ghost_scan.py is truly falsifiable and immediately catches:
1. Planted backup files (*.bak, *.backup).
2. Planted unapproved versioned shadow files (*_v2.py, *_v3.py).
3. Quarantined legacy imports in canonical directories.
"""

from tools import ghost_scan


def test_ghost_scan_detects_planted_bak_file(tmp_path, monkeypatch):
    """Adversarial Test: Planting a .bak file in scanned directory must trigger a violation."""
    fake_root = tmp_path / "repo"
    fake_root.mkdir()
    vox_dir = fake_root / "vox"
    vox_dir.mkdir()
    planted_bak = vox_dir / "pipeline.bak"
    planted_bak.write_text("# ghost backup code", encoding="utf-8")

    monkeypatch.setattr(ghost_scan, "REPO_ROOT", fake_root)
    ghosts = ghost_scan.scan_ghost_files()

    assert len(ghosts) >= 1
    assert any("pipeline.bak" in g for g in ghosts)


def test_ghost_scan_detects_planted_v2_shadow_file(tmp_path, monkeypatch):
    """Adversarial Test: Planting a *_v2.py file must trigger a violation."""
    fake_root = tmp_path / "repo"
    fake_root.mkdir()
    core_dir = fake_root / "core"
    core_dir.mkdir()
    planted_v2 = core_dir / "director_v2.py"
    planted_v2.write_text("# shadow version", encoding="utf-8")

    monkeypatch.setattr(ghost_scan, "REPO_ROOT", fake_root)
    ghosts = ghost_scan.scan_ghost_files()

    assert len(ghosts) >= 1
    assert any("director_v2.py" in g for g in ghosts)


def test_ghost_scan_detects_forbidden_legacy_import(tmp_path):
    """Adversarial Test: Importing from quarantined legacy must be flagged by AST inspector."""
    bad_py = tmp_path / "canonical_module.py"
    bad_py.write_text(
        "import os\n"
        "from legacy.old_pipeline import run_old\n"
        "import legacy.shadow_util\n",
        encoding="utf-8"
    )

    violations = ghost_scan.check_ast_imports(bad_py)
    assert len(violations) == 2
    assert any("legacy.old_pipeline" in v[0] for v in violations)
    assert any("legacy.shadow_util" in v[0] for v in violations)


def test_ghost_scan_main_exits_nonzero_on_violation(tmp_path, monkeypatch):
    """Adversarial Test: tools/ghost_scan.py main() returns exit code 1 when violations exist."""
    fake_root = tmp_path / "repo"
    fake_root.mkdir()
    vox_dir = fake_root / "vox"
    vox_dir.mkdir()
    (vox_dir / "ghost.bak").write_text("bad", encoding="utf-8")

    monkeypatch.setattr(ghost_scan, "REPO_ROOT", fake_root)
    code = ghost_scan.main()
    assert code == 1


def test_ghost_scan_detects_planted_scratch_probe_file(tmp_path, monkeypatch):
    """Adversarial Test: Planting an untracked scratch probe file must trigger a violation."""
    fake_root = tmp_path / "repo"
    fake_root.mkdir()
    scripts_dir = fake_root / "scripts"
    scripts_dir.mkdir()
    (scripts_dir / "scratch_probe_test.py").write_text("print('scratch')", encoding="utf-8")

    monkeypatch.setattr(ghost_scan, "REPO_ROOT", fake_root)
    ghosts = ghost_scan.scan_ghost_files()
    assert len(ghosts) == 1
    assert "scratch_probe_test.py" in ghosts[0]

