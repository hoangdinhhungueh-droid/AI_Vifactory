"""tests/test_real_env_sync_guard.py — Test Suite for Real Environment Sync Guard & Git Backup.

Validates:
  1. Git backup checkpoint creation (branch + stash capture).
  2. Git rollback mechanism.
  3. Real environment feasibility evaluation probe.
  4. Live Real environment E2E audit execution.
  5. Integration with OrchestratorRunner (--mode sync, --mode deploy).
"""

import subprocess
import sys
import unittest
from pathlib import Path

import pytest

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from scripts.orchestrator.real_env_sync_guard import RealEnvSyncGuard


class TestRealEnvSyncGuard(unittest.TestCase):
    """Unit and integration tests for RealEnvSyncGuard."""

    def setUp(self):
        self.guard = RealEnvSyncGuard(root_dir=ROOT_DIR)

    def test_01_create_git_backup_checkpoint(self):
        """Verifies that Git backup checkpoint branch and stash are created safely."""
        res = self.guard.create_git_backup_checkpoint(prefix="test_backup")
        self.assertEqual(res.get("status"), "success")
        record = res.get("backup_record", {})
        self.assertIn("backup_branch", record)
        self.assertTrue(record["backup_branch"].startswith("backup/test_backup_"))
        self.assertIn("head_sha", record)
        self.assertTrue(len(record["head_sha"]) >= 40)

        # Verify branch actually exists in git
        branch_name = record["backup_branch"]
        verify_cmd = subprocess.run(
            ["git", "-C", str(ROOT_DIR), "rev-parse", "--verify", branch_name],
            capture_output=True,
            text=True,
        )
        self.assertEqual(verify_cmd.returncode, 0, f"Branch {branch_name} should exist in git")

        # Clean up test branch
        subprocess.run(
            ["git", "-C", str(ROOT_DIR), "branch", "-D", branch_name],
            capture_output=True,
            text=True,
        )

    def test_02_rollback_invalid_ref_fails_safely(self):
        """Verifies that attempting to rollback to an invalid ref returns error without touching git."""
        res = self.guard.rollback_git_checkpoint("non_existent_branch_random_12345")
        self.assertEqual(res.get("status"), "error")
        self.assertIn("does not exist", res.get("error", ""))

    @pytest.mark.integration
    def test_03_evaluate_real_env_sync(self):
        """Verifies real environment feasibility evaluation against live VPS."""
        res = self.guard.evaluate_real_env_sync(allow_remote_dirty=True)
        self.assertEqual(res.get("status"), "success")
        self.assertTrue(res.get("ready"), f"Evaluation should be ready, got issues: {res.get('issues')}")
        checks = res.get("checks", {})
        self.assertTrue(checks.get("local_ast_valid"))
        self.assertTrue(checks.get("vps_reachable"))
        self.assertGreater(checks.get("vps_free_disk_mb", 0), 2000)
        self.assertGreater(checks.get("vps_free_ram_mb", 0), 300)

    @pytest.mark.integration
    def test_04_audit_real_env_e2e_live(self):
        """Verifies live Real Environment E2E audit on VPS host."""
        res = self.guard.audit_real_env_e2e(suite="smoke")
        self.assertEqual(res.get("status"), "success")
        self.assertTrue(res.get("passed"))
        self.assertEqual(res.get("verdict"), "PASS")
        audit_res = res.get("audit_results", {})
        self.assertIn("live_master_smoke_gate", audit_res)
        self.assertTrue(audit_res["live_master_smoke_gate"].get("passed"))
        self.assertEqual(audit_res["live_master_smoke_gate"].get("exit_code"), 0)

    def test_05_runner_cli_options(self):
        """Verifies that runner.py parser supports all new flags."""
        from scripts.orchestrator.runner import build_parser

        parser = build_parser()
        args = parser.parse_args(["--mode", "sync", "--with-backup", "--audit-real-env", "--auto-rollback"])
        self.assertTrue(args.with_backup)
        self.assertTrue(args.audit_real_env)
        self.assertTrue(args.auto_rollback)
        self.assertEqual(args.mode, "sync")


if __name__ == "__main__":
    unittest.main()
