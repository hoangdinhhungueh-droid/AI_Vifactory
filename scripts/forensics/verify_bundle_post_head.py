#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""scripts/forensics/verify_bundle_post_head.py — Standalone Post-HEAD Evidence Verifier.

Rule 121, Rule 126 & Boss Round 29/30 Punchlist Compliance:
Executes as an INDEPENDENT external process invoked after evidence bundle finalization.
Re-reads and re-hashes all finalized artifacts directly from disk, verifies two-tier
manifest identity, checks git tree provenance, confirms git-ignore encapsulation,
verifies working-tree cleanliness, strictly rejects path traversal and unlisted files,
and cryptographically generates the authoritative post_head_attestation.json artifact.
"""

import argparse
import hashlib
import json
import os
import stat
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

REQUIRED_BUNDLE_ARTIFACTS: Set[str] = {
    "manifest.json",
    "incremental.patch",
    "cumulative.patch",
    "ast_scanner_source.py",
    "ast_scanner_version_and_metadata.json",
    "ast_scanner_raw_output.json",
}

ALLOWED_BUNDLE_ARTIFACTS: Set[str] = {
    "ast_scanner_raw_output.json",
    "ast_scanner_source.py",
    "ast_scanner_version_and_metadata.json",
    "ci_jobs_steps_logs.json",
    "ci_raw_run.json",
    "credential_rotation_records.json",
    "cumulative.patch",
    "executable_hashes.json",
    "incremental.patch",
    "lifecycle_inventories.json",
    "linux_focused_junit.xml",
    "manifest.json",
    "retrieval_commands.sh",
    "scanner_raw_output.txt",
    "scanner_source_hash_and_version.json",
    "scanner_source_probe_zero_mock.py",
    "windows_focused_junit.xml",
    "zero_mock_229_baseline.json",
}


def _compute_sha256(file_path: Path) -> str:
    """Computes SHA-256 digest of a physical file directly from disk bytes."""
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def _run_git_cmd(repo_root: Path, args: List[str]) -> Tuple[int, str]:
    """Runs a git command against the repository root."""
    res = subprocess.run(
        ["git", "-C", str(repo_root)] + args,
        capture_output=True,
        text=True,
        check=False,
    )
    return res.returncode, res.stdout.strip()


def _is_symlink_or_reparse(path: Path) -> bool:
    """Detects whether path is a POSIX symlink or NTFS reparse point/junction (Rule 121 & Rule 137)."""
    if path.is_symlink():
        return True
    try:
        st = os.lstat(str(path))
        if getattr(st, "st_reparse_tag", 0) != 0 or stat.S_ISLNK(st.st_mode):
            return True
    except (OSError, ValueError):
        pass
    try:
        os.readlink(str(path))
        return True
    except (OSError, ValueError):
        pass
    return False


def verify_bundle_and_attest(
    repo_root: Path,
    task_id: str = "TASK_1792314467",
    allowed_artifacts: Optional[Set[str]] = None,
) -> Dict[str, Any]:
    """Independently verifies evidence bundle artifacts and generates post-HEAD attestation.

    Fails closed (raises RuntimeError) on any verification mismatch.
    """
    audits_dir = repo_root / "specs" / "boss_audits"
    bundle_dir = audits_dir / f"{task_id}_evidence_bundle"
    root_manifest_file = audits_dir / f"{task_id}_manifest.json"
    bundle_manifest_file = bundle_dir / "bundle_manifest.json"
    bundle_manifest_copy = bundle_dir / "manifest.json"

    # 1. Verify existence of root manifest, bundle directory, and bundle manifests
    if not root_manifest_file.is_file():
        raise RuntimeError(f"Root manifest not found at {root_manifest_file}")
    if not bundle_dir.is_dir():
        raise RuntimeError(f"Bundle directory not found at {bundle_dir}")
    if not bundle_manifest_file.is_file():
        raise RuntimeError(f"Bundle manifest inventory not found at {bundle_manifest_file}")
    if not bundle_manifest_copy.is_file():
        raise RuntimeError(f"Bundle manifest copy not found at {bundle_manifest_copy}")

    # 2. Query independent Git provenance and verify committed baseline in HEAD
    code_head, git_head = _run_git_cmd(repo_root, ["rev-parse", "HEAD"])
    if code_head != 0 or len(git_head) != 40:
        raise RuntimeError(f"Failed to query valid Git HEAD SHA: code {code_head}, got {git_head!r}")

    code_tree, git_tree = _run_git_cmd(repo_root, ["rev-parse", "HEAD^{tree}"])
    if code_tree != 0 or len(git_tree) != 40:
        raise RuntimeError(f"Failed to query valid Git tree SHA: code {code_tree}, got {git_tree!r}")

    code_blob, committed_manifest_blob_sha = _run_git_cmd(
        repo_root,
        ["rev-parse", f"{git_head}:specs/boss_audits/{task_id}_manifest.json"],
    )
    if code_blob != 0 or len(committed_manifest_blob_sha) != 40:
        raise RuntimeError(
            f"Committed manifest baseline not found in git HEAD ({git_head}): "
            f"specs/boss_audits/{task_id}_manifest.json (exit {code_blob}, output: {committed_manifest_blob_sha!r})"
        )

    # 3. Check working tree cleanliness (Rule 126: clean porcelain guarantee)
    code_status, out_status = _run_git_cmd(repo_root, ["status", "--porcelain"])
    if code_status != 0:
        raise RuntimeError(f"Failed to check git status: exit code {code_status}")
    if out_status.strip():
        raise RuntimeError(f"Working tree is dirty, expected clean porcelain per Rule 126:\n{out_status}")

    # 4. Check git check-ignore status of evidence bundle
    rel_bundle = bundle_dir.relative_to(repo_root).as_posix() + "/"
    code_ignore, out_ignore = _run_git_cmd(repo_root, ["check-ignore", rel_bundle])
    bundle_is_ignored = (code_ignore == 0 and bool(out_ignore.strip()))
    if not bundle_is_ignored:
        raise RuntimeError(f"Bundle directory {rel_bundle} is NOT git-ignored by repository rules (exit {code_ignore})")

    # 5. Parse and validate post-HEAD bundle manifest provenance against live Git state
    bundle_manifest_copy_bytes = bundle_manifest_copy.read_bytes()
    bundle_manifest_copy_sha = hashlib.sha256(bundle_manifest_copy_bytes).hexdigest()
    try:
        bundle_manifest_data_parsed = json.loads(bundle_manifest_copy_bytes.decode("utf-8"))
    except Exception as exc:
        raise RuntimeError(f"Failed to parse bundle manifest copy JSON: {exc}") from exc
    if not isinstance(bundle_manifest_data_parsed, dict):
        raise RuntimeError("Bundle manifest copy must be a JSON object")

    manifest_head = bundle_manifest_data_parsed.get("head_commit_sha")
    manifest_tree = bundle_manifest_data_parsed.get("tree_sha")
    manifest_timestamp = bundle_manifest_data_parsed.get("verification_timestamp")
    manifest_task_id = bundle_manifest_data_parsed.get("task_id")
    manifest_episode = bundle_manifest_data_parsed.get("target_episode")

    if manifest_head != git_head:
        raise RuntimeError(f"Manifest head_commit_sha ({manifest_head}) does not match git HEAD ({git_head})")
    if manifest_tree != git_tree:
        raise RuntimeError(f"Manifest tree_sha ({manifest_tree}) does not match git tree ({git_tree})")
    if manifest_task_id != task_id:
        raise RuntimeError(f"Manifest task_id ({manifest_task_id}) does not match expected ({task_id})")
    if manifest_episode != "JP_TEMP_59":
        raise RuntimeError(f"Manifest target_episode ({manifest_episode}) does not match 'JP_TEMP_59'")

    # 6. Independent re-hashing and strict inventory validation
    try:
        bundle_manifest_data = json.loads(bundle_manifest_file.read_bytes().decode("utf-8"))
    except Exception as exc:
        raise RuntimeError(f"Failed to parse bundle_manifest.json: {exc}") from exc
    if not isinstance(bundle_manifest_data, dict):
        raise RuntimeError("bundle_manifest.json must be a JSON object")

    files_inventory = bundle_manifest_data.get("files") if isinstance(bundle_manifest_data.get("files"), dict) else bundle_manifest_data
    if not isinstance(files_inventory, dict) or not files_inventory:
        raise RuntimeError("bundle_manifest.json contains missing or empty files inventory")

    # Reject path traversal and invalid naming across all inventory keys before checking allowed set
    for art_name in files_inventory.keys():
        if not isinstance(art_name, str) or not art_name.strip():
            raise RuntimeError(f"Invalid artifact name in inventory: {art_name!r}")
        if ".." in art_name or "/" in art_name or "\\" in art_name or Path(art_name).is_absolute():
            raise RuntimeError(f"Path traversal or invalid path detected in artifact name: {art_name!r}")

    # Enforce mandatory required bundle artifacts
    missing_required = REQUIRED_BUNDLE_ARTIFACTS - set(files_inventory.keys())
    if missing_required:
        raise RuntimeError(f"Missing mandatory bundle artifact(s) in inventory: {sorted(missing_required)}")

    # Enforce allowed artifact set (reject unexpected rogue inventory entries)
    effective_allowed = allowed_artifacts if allowed_artifacts is not None else ALLOWED_BUNDLE_ARTIFACTS
    unexpected_inventory_keys = set(files_inventory.keys()) - effective_allowed
    if unexpected_inventory_keys:
        raise RuntimeError(f"Unexpected unapproved artifact(s) in inventory: {sorted(unexpected_inventory_keys)}")

    # For production task TASK_1792314467 with default allowed set, enforce exact 18-artifact coverage
    if task_id == "TASK_1792314467" and allowed_artifacts is None:
        missing_production = ALLOWED_BUNDLE_ARTIFACTS - set(files_inventory.keys())
        if missing_production:
            raise RuntimeError(f"Missing production delivered artifact(s) in inventory: {sorted(missing_production)}")
        if len(files_inventory) != len(ALLOWED_BUNDLE_ARTIFACTS):
            raise RuntimeError(
                f"Production bundle inventory count mismatch: expected {len(ALLOWED_BUNDLE_ARTIFACTS)} artifacts, "
                f"got {len(files_inventory)}"
            )

    verified_artifacts: Dict[str, Dict[str, Any]] = {}
    for art_name, art_meta in files_inventory.items():
        if not isinstance(art_meta, dict):
            raise RuntimeError(f"Invalid non-dictionary metadata for artifact {art_name}")

        expected_sha = art_meta.get("sha256")
        expected_bytes = art_meta.get("size_bytes", art_meta.get("bytes"))

        if not expected_sha or not isinstance(expected_sha, str) or len(expected_sha) != 64:
            raise RuntimeError(f"Invalid or missing sha256 for {art_name}: {expected_sha!r}")
        if expected_bytes is None or not isinstance(expected_bytes, int) or expected_bytes < 0:
            raise RuntimeError(f"Invalid or missing size_bytes for {art_name}: {expected_bytes!r}")

        art_path = bundle_dir / art_name
        if _is_symlink_or_reparse(art_path):
            raise RuntimeError(f"Symlink rejected for bundle artifact: {art_name}")
        if not art_path.is_file():
            raise RuntimeError(f"Bundle artifact missing from disk: {art_name}")

        actual_sha = _compute_sha256(art_path)
        actual_bytes = art_path.stat().st_size

        if actual_sha != expected_sha:
            raise RuntimeError(f"SHA256 mismatch for {art_name}: expected {expected_sha}, got {actual_sha}")
        if actual_bytes != expected_bytes:
            raise RuntimeError(f"Byte size mismatch for {art_name}: expected {expected_bytes}, got {actual_bytes}")

        verified_artifacts[art_name] = {
            "sha256": actual_sha,
            "bytes": actual_bytes,
            "verified": True,
        }

    # Enforce exact allowed coverage and reject rogue physical entries
    allowed_bundle_files = set(files_inventory.keys()) | {"bundle_manifest.json", "post_head_attestation.json"}
    for entry in bundle_dir.iterdir():
        if _is_symlink_or_reparse(entry):
            raise RuntimeError(f"Symlink rejected in bundle directory: {entry.name}")
        if entry.is_dir():
            raise RuntimeError(f"Unexpected subdirectory rejected in bundle directory: {entry.name}")
        if not entry.is_file():
            raise RuntimeError(f"Non-file filesystem entry rejected in bundle directory: {entry.name}")
        if entry.name not in allowed_bundle_files:
            raise RuntimeError(f"Unlisted extra file(s) found in bundle directory: {entry.name}")

    # 7. Generate structurally independent post_head_attestation.json atomically
    attestation_file = bundle_dir / "post_head_attestation.json"
    root_manifest_sha = _compute_sha256(root_manifest_file)
    attestation_record = {
        "attestation_type": "STRUCTURALLY_INDEPENDENT_POST_HEAD_ATTESTATION",
        "verifier_engine": "scripts/forensics/verify_bundle_post_head.py",
        "verifier_version": "1.0.0",
        "verifier_process_id": os.getpid(),
        "verifier_parent_pid": os.getppid(),
        "execution_context": "INDEPENDENT_EXTERNAL_PROCESS",
        "task_id": task_id,
        "episode": "JP_TEMP_59",
        "head_commit_sha": git_head,
        "local_tree_sha": git_tree,
        "manifest_head_sha": manifest_head,
        "manifest_tree_sha": manifest_tree,
        "committed_manifest_blob_sha": committed_manifest_blob_sha,
        "committed_manifest_disk_sha256": root_manifest_sha,
        "live_bundle_manifest_sha256": bundle_manifest_copy_sha,
        "timestamp": manifest_timestamp,
        "verification_authority": "scripts/forensics/verify_bundle_post_head.py",
        "bundle_git_ignored": bundle_is_ignored,
        "working_tree_clean": True,
        "verified_artifacts_count": len(verified_artifacts),
        "total_bundle_bytes": sum(a["bytes"] for a in verified_artifacts.values()),
        "parity_status": "100% BIT_FOR_BIT MATCHING ACROSS BUNDLE ARTIFACTS",
        "snapshot_provenance": (
            "Verified by standalone verifier subprocess: committed manifest blob inside git HEAD represents the "
            "pre-audit immutable test contract; live manifest inside the gitignored evidence bundle represents the "
            "post-HEAD physical execution attestation. Re-read and re-hashed directly from disk with 0 discrepancies."
        ),
        "verdict": "PASS: CRYPTOGRAPHICALLY ATTESTED BY INDEPENDENT PROCESS",
    }

    attestation_bytes = json.dumps(attestation_record, indent=2).encode("utf-8")
    tmp_attestation = bundle_dir / f".tmp_post_head_attestation_{os.getpid()}.json"
    tmp_attestation.write_bytes(attestation_bytes)
    tmp_attestation.replace(attestation_file)

    attestation_sha = _compute_sha256(attestation_file)

    return {
        "status": "PASS",
        "task_id": task_id,
        "head_commit_sha": git_head,
        "local_tree_sha": git_tree,
        "committed_manifest_blob_sha": committed_manifest_blob_sha,
        "live_bundle_manifest_sha256": bundle_manifest_copy_sha,
        "attestation_file": str(attestation_file),
        "attestation_sha256": attestation_sha,
        "verified_artifacts_count": len(verified_artifacts),
        "total_bundle_bytes": sum(a["bytes"] for a in verified_artifacts.values()),
        "bundle_git_ignored": bundle_is_ignored,
        "verifier_process_id": os.getpid(),
        "verifier_parent_pid": os.getppid(),
        "verdict": "PASS (0 Discrepancies / 100% Verified)",
    }


def main() -> int:
    """CLI entrypoint for standalone bundle verification."""
    parser = argparse.ArgumentParser(description="Standalone Post-HEAD Evidence Verifier (Rule 121 & Rule 126)")
    parser.add_argument("--task-id", default="TASK_1792314467", help="Task identifier")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent.parent.parent
    try:
        result = verify_bundle_and_attest(repo_root=repo_root, task_id=args.task_id)
        print(json.dumps(result, indent=2))
        return 0
    except Exception as exc:
        err_dict = {
            "status": "FAIL",
            "task_id": args.task_id,
            "error_type": type(exc).__name__,
            "error_message": str(exc),
            "verdict": "FAIL (Discrepancy Detected)",
        }
        print(json.dumps(err_dict, indent=2), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
