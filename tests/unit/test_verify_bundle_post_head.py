# tests/unit/test_verify_bundle_post_head.py
"""Unit tests for standalone post-HEAD bundle verifier (Rule 121, Rule 126 & Boss Round 29/30 Punchlist).
Verifies:
1. Re-reading and independent re-hashing of physical bundle artifacts.
2. Rejection of uncommitted baseline, un-ignored bundles, dirty trees, and provenance mismatches.
3. Rejection of path traversal, symlink escapes, missing required artifacts, and unlisted extra files.
4. Cryptographic attestation recording with process and parent PID capture, and post-write byte-hash parity.
Zero test-doubles policy: utilizes real hermetic filesystem artifacts via tmp_path without test doubles (Rule 118).
"""

import hashlib
import json
import os
import subprocess
from pathlib import Path
from typing import Any, Dict

import pytest

from scripts.forensics.verify_bundle_post_head import (
    _compute_sha256,
    verify_bundle_and_attest,
)


def _init_test_git_repo(repo_root: Path):
    """Initializes a real hermetic git repository in tmp_path without test doubles."""
    subprocess.run(["git", "-C", str(repo_root), "init"], capture_output=True, check=True)
    subprocess.run(["git", "-C", str(repo_root), "config", "user.name", "Test Runner"], capture_output=True, check=True)
    subprocess.run(["git", "-C", str(repo_root), "config", "user.email", "test@example.com"], capture_output=True, check=True)
    subprocess.run(["git", "-C", str(repo_root), "commit", "--allow-empty", "-m", "init"], capture_output=True, check=True)


def _create_valid_hermetic_fixture(repo_root: Path, task_id: str = "TASK_TEST") -> Dict[str, Any]:
    """Sets up a fully valid hermetic git repository with committed baseline manifest and ignored bundle."""
    _init_test_git_repo(repo_root)

    # 1. Setup .gitignore ignoring evidence bundle
    gitignore = repo_root / ".gitignore"
    gitignore.write_text(f"specs/boss_audits/{task_id}_evidence_bundle/\n", encoding="utf-8")

    # 2. Setup baseline manifest
    audits_dir = repo_root / "specs" / "boss_audits"
    audits_dir.mkdir(parents=True, exist_ok=True)
    root_manifest = audits_dir / f"{task_id}_manifest.json"
    baseline_payload = {
        "manifest_version": "1.0",
        "task_id": task_id,
        "target_episode": "JP_TEMP_59",
    }
    root_manifest.write_bytes(json.dumps(baseline_payload, indent=2).encode("utf-8"))

    # 3. Commit .gitignore and baseline manifest into HEAD
    subprocess.run(["git", "-C", str(repo_root), "add", ".gitignore", str(root_manifest)], capture_output=True, check=True)
    subprocess.run(["git", "-C", str(repo_root), "commit", "-m", "commit baseline manifest and gitignore"], capture_output=True, check=True)

    # 4. Query live git HEAD and tree SHA of this committed state
    head_sha = subprocess.run(["git", "-C", str(repo_root), "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
    tree_sha = subprocess.run(["git", "-C", str(repo_root), "rev-parse", "HEAD^{tree}"], capture_output=True, text=True, check=True).stdout.strip()

    # 5. Create evidence bundle directory (git-ignored)
    bundle_dir = audits_dir / f"{task_id}_evidence_bundle"
    bundle_dir.mkdir(parents=True, exist_ok=True)

    # 6. Create bundle manifest copy with live head_sha and tree_sha
    bundle_manifest_copy = bundle_dir / "manifest.json"
    bundle_manifest_payload = {
        "manifest_version": "1.0",
        "verification_timestamp": "2026-10-20T00:00:00Z",
        "task_id": task_id,
        "target_episode": "JP_TEMP_59",
        "head_commit_sha": head_sha,
        "tree_sha": tree_sha,
    }
    bundle_manifest_copy_bytes = json.dumps(bundle_manifest_payload, indent=2).encode("utf-8")
    bundle_manifest_copy.write_bytes(bundle_manifest_copy_bytes)

    # 7. Create all required bundle artifacts
    required_artifacts = {
        "manifest.json": bundle_manifest_copy_bytes,
        "incremental.patch": b"diff --git a/file b/file\n",
        "cumulative.patch": b"diff --git a/all b/all\n",
        "ast_scanner_source.py": b"# AST scanner source code\n",
        "ast_scanner_version_and_metadata.json": b'{"version": "2.2.0"}\n',
        "ast_scanner_raw_output.json": b'{"defects": []}\n',
    }

    files_inventory = {}
    for fname, fbytes in required_artifacts.items():
        fpath = bundle_dir / fname
        fpath.write_bytes(fbytes)
        files_inventory[fname] = {
            "sha256": hashlib.sha256(fbytes).hexdigest(),
            "size_bytes": len(fbytes),
        }

    bundle_manifest_file = bundle_dir / "bundle_manifest.json"
    inventory_payload = {
        "bundle_version": "2.0",
        "task_id": task_id,
        "files_count": len(files_inventory),
        "files": files_inventory,
    }
    bundle_manifest_file.write_bytes(json.dumps(inventory_payload, indent=2).encode("utf-8"))

    return {
        "head_sha": head_sha,
        "tree_sha": tree_sha,
        "bundle_dir": bundle_dir,
        "audits_dir": audits_dir,
        "root_manifest": root_manifest,
        "bundle_manifest_file": bundle_manifest_file,
        "bundle_manifest_payload": inventory_payload,
        "files_inventory": files_inventory,
    }


def test_compute_sha256_computes_exact_digest(tmp_path: Path):
    """Verifies that _compute_sha256 returns exact hash for known file content."""
    sample_file = tmp_path / "sample.txt"
    sample_content = b"Standalone Verifier Cryptographic Test Payload"
    sample_file.write_bytes(sample_content)

    expected_hash = hashlib.sha256(sample_content).hexdigest()
    assert _compute_sha256(sample_file) == expected_hash


def test_verify_bundle_rejects_missing_root_manifest(tmp_path: Path):
    """Verifies fail-closed behavior when root manifest is missing."""
    _init_test_git_repo(tmp_path)
    with pytest.raises(RuntimeError) as exc_info:
        verify_bundle_and_attest(repo_root=tmp_path, task_id="TASK_NONEXISTENT")
    assert "Root manifest not found" in str(exc_info.value)


def test_verify_bundle_rejects_missing_bundle_dir(tmp_path: Path):
    """Verifies fail-closed behavior when bundle directory does not exist."""
    _init_test_git_repo(tmp_path)
    audits_dir = tmp_path / "specs" / "boss_audits"
    audits_dir.mkdir(parents=True)
    (audits_dir / "TASK_TEST_manifest.json").write_text("{}", encoding="utf-8")

    with pytest.raises(RuntimeError) as exc_info:
        verify_bundle_and_attest(repo_root=tmp_path, task_id="TASK_TEST")
    assert "Bundle directory not found" in str(exc_info.value)


def test_verify_bundle_rejects_missing_bundle_manifest(tmp_path: Path):
    """Verifies fail-closed behavior when bundle_manifest.json is missing."""
    fix = _create_valid_hermetic_fixture(tmp_path, "TASK_TEST")
    fix["bundle_manifest_file"].unlink()

    with pytest.raises(RuntimeError) as exc_info:
        verify_bundle_and_attest(repo_root=tmp_path, task_id="TASK_TEST")
    assert "Bundle manifest inventory not found" in str(exc_info.value)


def test_verify_bundle_rejects_corrupted_artifact_digest(tmp_path: Path):
    """Verifies fail-closed behavior when an artifact recorded in bundle_manifest has wrong hash."""
    fix = _create_valid_hermetic_fixture(tmp_path, "TASK_TEST")
    payload = fix["bundle_manifest_payload"]
    payload["files"]["ast_scanner_source.py"]["sha256"] = "0" * 64
    fix["bundle_manifest_file"].write_bytes(json.dumps(payload, indent=2).encode("utf-8"))

    with pytest.raises(RuntimeError) as exc_info:
        verify_bundle_and_attest(repo_root=tmp_path, task_id="TASK_TEST")
    assert "SHA256 mismatch for ast_scanner_source.py" in str(exc_info.value)


def test_verify_bundle_rejects_uncommitted_baseline(tmp_path: Path):
    """Verifies fail-closed rejection when the root manifest is not committed in git HEAD."""
    _init_test_git_repo(tmp_path)
    gitignore = tmp_path / ".gitignore"
    gitignore.write_text("specs/boss_audits/TASK_TEST_evidence_bundle/\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(tmp_path), "add", ".gitignore"], capture_output=True, check=True)
    subprocess.run(["git", "-C", str(tmp_path), "commit", "-m", "add gitignore"], capture_output=True, check=True)

    head_sha = subprocess.run(["git", "-C", str(tmp_path), "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
    tree_sha = subprocess.run(["git", "-C", str(tmp_path), "rev-parse", "HEAD^{tree}"], capture_output=True, text=True, check=True).stdout.strip()

    audits_dir = tmp_path / "specs" / "boss_audits"
    audits_dir.mkdir(parents=True, exist_ok=True)
    root_manifest = audits_dir / "TASK_TEST_manifest.json"
    manifest_bytes = json.dumps({
        "manifest_version": "1.0",
        "verification_timestamp": "2026-10-20T00:00:00Z",
        "task_id": "TASK_TEST",
        "target_episode": "JP_TEMP_59",
        "head_commit_sha": head_sha,
        "tree_sha": tree_sha,
    }, indent=2).encode("utf-8")
    root_manifest.write_bytes(manifest_bytes)
    # Manifest is uncommitted!

    bundle_dir = audits_dir / "TASK_TEST_evidence_bundle"
    bundle_dir.mkdir(parents=True, exist_ok=True)
    (bundle_dir / "manifest.json").write_bytes(manifest_bytes)
    (bundle_dir / "bundle_manifest.json").write_bytes(b'{"files": {}}')

    with pytest.raises(RuntimeError) as exc_info:
        verify_bundle_and_attest(repo_root=tmp_path, task_id="TASK_TEST")
    assert "Committed manifest baseline not found in git HEAD" in str(exc_info.value)


def test_verify_bundle_rejects_unignored_bundle(tmp_path: Path):
    """Verifies fail-closed rejection when the evidence bundle directory is not git-ignored."""
    _create_valid_hermetic_fixture(tmp_path, "TASK_TEST")
    # Remove gitignore and commit
    gitignore = tmp_path / ".gitignore"
    gitignore.unlink()
    subprocess.run(["git", "-C", str(tmp_path), "add", ".gitignore"], capture_output=True, check=True)
    subprocess.run(["git", "-C", str(tmp_path), "commit", "-m", "remove gitignore"], capture_output=True, check=True)

    with pytest.raises(RuntimeError) as exc_info:
        verify_bundle_and_attest(repo_root=tmp_path, task_id="TASK_TEST")
    # Will fail on either dirty working tree (untracked bundle) or NOT git-ignored
    err_msg = str(exc_info.value)
    assert ("Working tree is dirty" in err_msg) or ("NOT git-ignored" in err_msg)


def test_verify_bundle_rejects_dirty_working_tree(tmp_path: Path):
    """Verifies fail-closed rejection when tracked files in the repository are modified."""
    _create_valid_hermetic_fixture(tmp_path, "TASK_TEST")
    # Mutate a tracked file
    (tmp_path / ".gitignore").write_text("# dirty modification\n", encoding="utf-8")

    with pytest.raises(RuntimeError) as exc_info:
        verify_bundle_and_attest(repo_root=tmp_path, task_id="TASK_TEST")
    assert "Working tree is dirty" in str(exc_info.value)


def test_verify_bundle_rejects_path_traversal(tmp_path: Path):
    """Verifies fail-closed rejection when an artifact contains path traversal sequence."""
    fix = _create_valid_hermetic_fixture(tmp_path, "TASK_TEST")
    payload = fix["bundle_manifest_payload"]
    payload["files"]["../escaped_file.txt"] = {"sha256": "a" * 64, "size_bytes": 10}
    fix["bundle_manifest_file"].write_bytes(json.dumps(payload, indent=2).encode("utf-8"))

    with pytest.raises(RuntimeError) as exc_info:
        verify_bundle_and_attest(repo_root=tmp_path, task_id="TASK_TEST")
    assert "Path traversal or invalid path detected" in str(exc_info.value)


def test_verify_bundle_rejects_symlink_artifact(tmp_path: Path):
    """Verifies fail-closed rejection when a bundle artifact is a symlink or physical NTFS junction escape."""
    fix = _create_valid_hermetic_fixture(tmp_path, "TASK_TEST")
    real_target_dir = tmp_path.parent / "real_external_dir"
    real_target_dir.mkdir(parents=True, exist_ok=True)
    real_target_file = real_target_dir / "inner.txt"
    real_target_file.write_bytes(b"external data")

    symlink_path = fix["bundle_dir"] / "ast_scanner_source.py"
    symlink_path.unlink()
    try:
        symlink_path.symlink_to(real_target_file)
    except (OSError, NotImplementedError):
        # On Windows without SeCreateSymbolicLinkPrivilege, create a genuine physical
        # NTFS directory junction reparse point (supported unprivileged on Windows NTFS)
        # to physically exercise the verifier's escape rejection logic without test doubles.
        res = subprocess.run(["cmd", "/c", "mklink", "/J", str(symlink_path), str(real_target_dir)], capture_output=True, check=True)
        assert res.returncode == 0

    payload = fix["bundle_manifest_payload"]
    payload["files"]["ast_scanner_source.py"] = {
        "sha256": hashlib.sha256(b"external data").hexdigest(),
        "size_bytes": len(b"external data"),
    }
    fix["bundle_manifest_file"].write_bytes(json.dumps(payload, indent=2).encode("utf-8"))

    with pytest.raises(RuntimeError) as exc_info:
        verify_bundle_and_attest(repo_root=tmp_path, task_id="TASK_TEST")
    assert "Symlink rejected" in str(exc_info.value)


def test_verify_bundle_rejects_unexpected_inventory_key(tmp_path: Path):
    """Verifies fail-closed rejection when bundle_manifest.json contains an unapproved inventory key."""
    fix = _create_valid_hermetic_fixture(tmp_path, "TASK_TEST")
    payload = fix["bundle_manifest_payload"]
    payload["files"]["unapproved_rogue_artifact.json"] = {
        "sha256": "0" * 64,
        "size_bytes": 100,
    }
    fix["bundle_manifest_file"].write_bytes(json.dumps(payload, indent=2).encode("utf-8"))

    with pytest.raises(RuntimeError) as exc_info:
        verify_bundle_and_attest(repo_root=tmp_path, task_id="TASK_TEST")
    assert "Unexpected unapproved artifact(s) in inventory" in str(exc_info.value)


def test_verify_bundle_rejects_malformed_top_level_json_array(tmp_path: Path):
    """Verifies fail-closed rejection when bundle_manifest.json is a JSON array instead of an object."""
    fix = _create_valid_hermetic_fixture(tmp_path, "TASK_TEST")
    fix["bundle_manifest_file"].write_bytes(b"[1, 2, 3]")

    with pytest.raises(RuntimeError) as exc_info:
        verify_bundle_and_attest(repo_root=tmp_path, task_id="TASK_TEST")
    assert "bundle_manifest.json must be a JSON object" in str(exc_info.value)


def test_verify_bundle_rejects_malformed_manifest_copy(tmp_path: Path):
    """Verifies fail-closed rejection when manifest.json copy in bundle is not a JSON object."""
    fix = _create_valid_hermetic_fixture(tmp_path, "TASK_TEST")
    (fix["bundle_dir"] / "manifest.json").write_bytes(b'["not", "a", "dict"]')

    with pytest.raises(RuntimeError) as exc_info:
        verify_bundle_and_attest(repo_root=tmp_path, task_id="TASK_TEST")
    assert "Bundle manifest copy must be a JSON object" in str(exc_info.value)


def test_verify_bundle_rejects_unexpected_subdirectory(tmp_path: Path):
    """Verifies fail-closed rejection when an unexpected subdirectory is present in bundle directory."""
    fix = _create_valid_hermetic_fixture(tmp_path, "TASK_TEST")
    rogue_dir = fix["bundle_dir"] / "rogue_subdir"
    rogue_dir.mkdir()

    with pytest.raises(RuntimeError) as exc_info:
        verify_bundle_and_attest(repo_root=tmp_path, task_id="TASK_TEST")
    assert "Unexpected subdirectory rejected in bundle directory" in str(exc_info.value)


def test_verify_bundle_rejects_missing_required_artifact(tmp_path: Path):
    """Verifies fail-closed rejection when a mandatory required artifact is missing from inventory."""
    fix = _create_valid_hermetic_fixture(tmp_path, "TASK_TEST")
    payload = fix["bundle_manifest_payload"]
    del payload["files"]["ast_scanner_source.py"]
    (fix["bundle_dir"] / "ast_scanner_source.py").unlink()
    fix["bundle_manifest_file"].write_bytes(json.dumps(payload, indent=2).encode("utf-8"))

    with pytest.raises(RuntimeError) as exc_info:
        verify_bundle_and_attest(repo_root=tmp_path, task_id="TASK_TEST")
    assert "Missing mandatory bundle artifact" in str(exc_info.value)


def test_verify_bundle_rejects_unlisted_extra_file(tmp_path: Path):
    """Verifies fail-closed rejection when unlisted physical files exist in bundle directory."""
    fix = _create_valid_hermetic_fixture(tmp_path, "TASK_TEST")
    extra_file = fix["bundle_dir"] / "rogue_unlisted_file.bin"
    extra_file.write_bytes(b"rogue data")

    with pytest.raises(RuntimeError) as exc_info:
        verify_bundle_and_attest(repo_root=tmp_path, task_id="TASK_TEST")
    assert "Unlisted extra file(s) found in bundle directory" in str(exc_info.value)


def test_verify_bundle_rejects_mismatched_head_provenance(tmp_path: Path):
    """Verifies fail-closed rejection when manifest head_commit_sha does not match live git HEAD."""
    fix = _create_valid_hermetic_fixture(tmp_path, "TASK_TEST")
    divergent_manifest = {
        "manifest_version": "1.0",
        "verification_timestamp": "2026-10-20T00:00:00Z",
        "task_id": "TASK_TEST",
        "target_episode": "JP_TEMP_59",
        "head_commit_sha": "0" * 40,
        "tree_sha": fix["tree_sha"],
    }
    m_bytes = json.dumps(divergent_manifest, indent=2).encode("utf-8")
    (fix["bundle_dir"] / "manifest.json").write_bytes(m_bytes)
    fix["bundle_manifest_payload"]["files"]["manifest.json"]["sha256"] = hashlib.sha256(m_bytes).hexdigest()
    fix["bundle_manifest_payload"]["files"]["manifest.json"]["size_bytes"] = len(m_bytes)
    fix["bundle_manifest_file"].write_bytes(json.dumps(fix["bundle_manifest_payload"], indent=2).encode("utf-8"))

    with pytest.raises(RuntimeError) as exc_info:
        verify_bundle_and_attest(repo_root=tmp_path, task_id="TASK_TEST")
    assert "does not match git HEAD" in str(exc_info.value)


def test_verify_bundle_rejects_mismatched_tree_provenance(tmp_path: Path):
    """Verifies fail-closed rejection when manifest tree_sha does not match live git tree."""
    fix = _create_valid_hermetic_fixture(tmp_path, "TASK_TEST")
    divergent_manifest = {
        "manifest_version": "1.0",
        "verification_timestamp": "2026-10-20T00:00:00Z",
        "task_id": "TASK_TEST",
        "target_episode": "JP_TEMP_59",
        "head_commit_sha": fix["head_sha"],
        "tree_sha": "0" * 40,
    }
    m_bytes = json.dumps(divergent_manifest, indent=2).encode("utf-8")
    (fix["bundle_dir"] / "manifest.json").write_bytes(m_bytes)
    fix["bundle_manifest_payload"]["files"]["manifest.json"]["sha256"] = hashlib.sha256(m_bytes).hexdigest()
    fix["bundle_manifest_payload"]["files"]["manifest.json"]["size_bytes"] = len(m_bytes)
    fix["bundle_manifest_file"].write_bytes(json.dumps(fix["bundle_manifest_payload"], indent=2).encode("utf-8"))

    with pytest.raises(RuntimeError) as exc_info:
        verify_bundle_and_attest(repo_root=tmp_path, task_id="TASK_TEST")
    assert "does not match git tree" in str(exc_info.value)


def test_verify_bundle_and_attest_success_creates_attestation(tmp_path: Path):
    """Verifies that on completely valid bundle, verifier succeeds and creates post_head_attestation.json."""
    _create_valid_hermetic_fixture(tmp_path, "TASK_TEST")

    res = verify_bundle_and_attest(repo_root=tmp_path, task_id="TASK_TEST")
    assert res["status"] == "PASS"
    assert res["verified_artifacts_count"] == 6
    assert res["bundle_git_ignored"] is True
    assert isinstance(res["verifier_process_id"], int) and res["verifier_process_id"] == os.getpid()
    assert isinstance(res["verifier_parent_pid"], int) and res["verifier_parent_pid"] == os.getppid()

    attestation_file = Path(res["attestation_file"])
    assert attestation_file.is_file()

    # Verify post-write byte-hash parity directly from disk bytes
    disk_hash = _compute_sha256(attestation_file)
    assert disk_hash == res["attestation_sha256"]

    attestation_data = json.loads(attestation_file.read_bytes().decode("utf-8"))
    assert attestation_data["attestation_type"] == "STRUCTURALLY_INDEPENDENT_POST_HEAD_ATTESTATION"
    assert attestation_data["verifier_process_id"] == os.getpid()
    assert attestation_data["verifier_parent_pid"] == os.getppid()
    assert attestation_data["verdict"] == "PASS: CRYPTOGRAPHICALLY ATTESTED BY INDEPENDENT PROCESS"
