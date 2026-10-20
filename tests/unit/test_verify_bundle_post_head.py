# tests/unit/test_verify_bundle_post_head.py
"""Unit tests for standalone post-HEAD bundle verifier (Rule 121, Rule 126 & Boss Round 29 Item 2).
Verifies:
1. Re-reading and independent re-hashing of physical bundle artifacts.
2. Rejection of missing root manifest, missing bundle directory, or corrupt artifacts.
3. Cryptographic attestation recording with process and parent PID capture.
Zero test-doubles policy: utilizes real filesystem artifacts via tmp_path without mocks (Rule 118).
"""

import hashlib
import json
import subprocess
from pathlib import Path

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


def test_verify_bundle_rejects_parity_mismatch(tmp_path: Path):
    """Verifies fail-closed behavior when root manifest and bundle manifest copy diverge."""
    _init_test_git_repo(tmp_path)
    audits_dir = tmp_path / "specs" / "boss_audits"
    bundle_dir = audits_dir / "TASK_TEST_evidence_bundle"
    bundle_dir.mkdir(parents=True)

    root_manifest = audits_dir / "TASK_TEST_manifest.json"
    root_manifest.write_text('{"version": "1.0", "tag": "root"}', encoding="utf-8")

    (bundle_dir / "bundle_manifest.json").write_text("{}", encoding="utf-8")
    (bundle_dir / "manifest.json").write_text('{"version": "1.0", "tag": "divergent_copy"}', encoding="utf-8")

    with pytest.raises(RuntimeError) as exc_info:
        verify_bundle_and_attest(repo_root=tmp_path, task_id="TASK_TEST")
    assert "Bit-for-bit parity mismatch" in str(exc_info.value)


def test_verify_bundle_rejects_corrupted_artifact_digest(tmp_path: Path):
    """Verifies fail-closed behavior when an artifact recorded in bundle_manifest has wrong hash."""
    _init_test_git_repo(tmp_path)
    audits_dir = tmp_path / "specs" / "boss_audits"
    bundle_dir = audits_dir / "TASK_TEST_evidence_bundle"
    bundle_dir.mkdir(parents=True)

    manifest_json = json.dumps({"verification_timestamp": "2026-10-20T00:00:00Z"})
    (audits_dir / "TASK_TEST_manifest.json").write_text(manifest_json, encoding="utf-8")
    (bundle_dir / "manifest.json").write_text(manifest_json, encoding="utf-8")

    # Create artifact with actual content
    test_art = bundle_dir / "test_artifact.bin"
    test_art.write_bytes(b"actual_bytes")

    # Record fraudulent hash in bundle_manifest.json
    bundle_manifest_data = {
        "test_artifact.bin": {
            "sha256": "0000000000000000000000000000000000000000000000000000000000000000",
            "bytes": len(b"actual_bytes"),
        }
    }
    (bundle_dir / "bundle_manifest.json").write_text(json.dumps(bundle_manifest_data), encoding="utf-8")

    with pytest.raises(RuntimeError) as exc_info:
        verify_bundle_and_attest(repo_root=tmp_path, task_id="TASK_TEST")
    assert "SHA256 mismatch for test_artifact.bin" in str(exc_info.value)


def test_verify_bundle_and_attest_success_creates_attestation(tmp_path: Path):
    """Verifies that on completely valid bundle, verifier succeeds and creates post_head_attestation.json."""
    _init_test_git_repo(tmp_path)
    audits_dir = tmp_path / "specs" / "boss_audits"
    bundle_dir = audits_dir / "TASK_TEST_evidence_bundle"
    bundle_dir.mkdir(parents=True)

    manifest_json = json.dumps({"verification_timestamp": "2026-10-20T00:00:00Z", "head_commit_sha": "abc"})
    (audits_dir / "TASK_TEST_manifest.json").write_text(manifest_json, encoding="utf-8")
    (bundle_dir / "manifest.json").write_text(manifest_json, encoding="utf-8")

    test_art = bundle_dir / "valid_art.txt"
    test_content = b"valid content"
    test_art.write_bytes(test_content)
    test_sha = hashlib.sha256(test_content).hexdigest()

    bundle_manifest_data = {
        "valid_art.txt": {
            "sha256": test_sha,
            "bytes": len(test_content),
        }
    }
    (bundle_dir / "bundle_manifest.json").write_text(json.dumps(bundle_manifest_data), encoding="utf-8")

    res = verify_bundle_and_attest(repo_root=tmp_path, task_id="TASK_TEST")
    assert res["status"] == "PASS"
    assert res["verified_artifacts_count"] == 1
    attestation_file = Path(res["attestation_file"])
    assert attestation_file.is_file()

    attestation_data = json.loads(attestation_file.read_text(encoding="utf-8"))
    assert attestation_data["attestation_type"] == "STRUCTURALLY_INDEPENDENT_POST_HEAD_ATTESTATION"
    assert attestation_data["verifier_process_id"] > 0
    assert attestation_data["verdict"] == "PASS: CRYPTOGRAPHICALLY ATTESTED BY INDEPENDENT PROCESS"
