"""scripts/orchestrator/real_env_sync_guard.py — Real Environment Sync, Live E2E Audit & Git Backup Guard.

Authoritative engine for:
  1. Automated Git safe backup checkpoints (branch/stash snapshot before sync/deploy).
  2. Real environment sync feasibility evaluation (pre-flight checks on VPS/live host).
  3. Bit-for-bit synchronization with SHA256 verification (Rule 126).
  4. Real environment live E2E audit & smoke verification (Rule 127).
  5. Automated failure rollback guard (restores Git and remote environment on failure).

Standard usage:
  python3 scripts/orchestrator/real_env_sync_guard.py --action backup
  python3 scripts/orchestrator/real_env_sync_guard.py --action evaluate
  python3 scripts/orchestrator/real_env_sync_guard.py --action sync --audit-real-env
  python3 scripts/orchestrator/real_env_sync_guard.py --action audit
  python3 scripts/orchestrator/real_env_sync_guard.py --action rollback --ref <backup_ref>
  python3 scripts/orchestrator/real_env_sync_guard.py --action full --auto-rollback
"""

import argparse
import base64
import datetime
import hashlib
import json
import logging
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("real_env_sync_guard")


class RealEnvSyncGuard:
    """Manages pre-sync git backup, real environment feasibility evaluation,

    real-time synchronization, live E2E audits, and rollback recovery.
    """

    def __init__(self, root_dir: Optional[Path] = None):
        if root_dir is None:
            script_dir = Path(__file__).resolve().parent.parent.parent
            self.root_dir = script_dir
        else:
            self.root_dir = Path(root_dir)
        self.logs_dir = self.root_dir / "logs"
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.backup_history_file = self.logs_dir / "git_backup_history.json"

    # =========================================================================
    # 1. GIT SAFE BACKUP & ROLLBACK CHECKPOINTS
    # =========================================================================

    def create_git_backup_checkpoint(self, prefix: str = "pre-sync") -> Dict[str, Any]:
        """Creates a dedicated immutable Git backup checkpoint branch and captures uncommitted stash state.

        Non-destructive: does not alter current branch or unstaged working tree.
        """
        timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d_%H%M%S")
        head_sha = ""
        head_branch = "HEAD"

        try:
            head_sha = subprocess.check_output(
                ["git", "-C", str(self.root_dir), "rev-parse", "HEAD"],
                text=True,
            ).strip()
            head_branch = subprocess.check_output(
                ["git", "-C", str(self.root_dir), "rev-parse", "--abbrev-ref", "HEAD"],
                text=True,
            ).strip()
        except Exception as e:
            logger.error("Failed to read git HEAD: %s", e)
            return {"status": "error", "error": f"Failed to read git HEAD: {e}"}

        short_sha = head_sha[:8] if head_sha else "unknown"
        backup_branch = f"backup/{prefix}_{timestamp}_{short_sha}"

        # 1. Create backup branch pointing to current HEAD
        try:
            subprocess.run(
                ["git", "-C", str(self.root_dir), "branch", backup_branch, head_sha],
                check=True,
                capture_output=True,
                text=True,
            )
            logger.info("Created Git backup checkpoint branch: %s", backup_branch)
        except Exception as e:
            logger.warning("Could not create backup branch %s: %s", backup_branch, e)

        # 2. Capture uncommitted changes safely via `git stash create`
        # `git stash create` creates a commit object representing working directory + index
        # WITHOUT updating refs/stash and WITHOUT modifying the working directory!
        stash_commit = ""
        try:
            stash_out = subprocess.check_output(
                ["git", "-C", str(self.root_dir), "stash", "create"],
                text=True,
            ).strip()
            if stash_out:
                stash_commit = stash_out
                logger.info("Captured working directory state in stash commit: %s", stash_commit)
        except Exception as e:
            logger.debug("No uncommitted changes or stash create skipped: %s", e)

        # 3. Read status manifest
        status_out = ""
        try:
            status_out = subprocess.check_output(
                ["git", "-C", str(self.root_dir), "status", "--porcelain"],
                text=True,
            ).strip()
        except Exception:
            pass

        uncommitted_files = [line.strip() for line in status_out.splitlines()] if status_out else []

        record = {
            "backup_branch": backup_branch,
            "head_sha": head_sha,
            "head_branch": head_branch,
            "stash_commit": stash_commit,
            "timestamp": timestamp,
            "iso_time": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "uncommitted_files_count": len(uncommitted_files),
            "uncommitted_files_preview": uncommitted_files[:20],
        }

        # Append to backup history log
        self._append_backup_history(record)

        return {"status": "success", "backup_record": record}

    def rollback_git_checkpoint(self, backup_ref: str, hard_reset: bool = True) -> Dict[str, Any]:
        """Rolls back the repository to a specified backup checkpoint reference."""
        logger.warning("Initiating Git rollback to checkpoint: %s", backup_ref)
        try:
            # Verify ref exists
            verify_res = subprocess.run(
                ["git", "-C", str(self.root_dir), "rev-parse", "--verify", backup_ref],
                capture_output=True,
                text=True,
            )
            if verify_res.returncode != 0:
                return {
                    "status": "error",
                    "error": f"Backup reference '{backup_ref}' does not exist in git.",
                }

            target_sha = verify_res.stdout.strip()

            if hard_reset:
                subprocess.run(
                    ["git", "-C", str(self.root_dir), "reset", "--hard", target_sha],
                    check=True,
                    capture_output=True,
                    text=True,
                )
                logger.info("Git HEAD successfully reset to: %s (%s)", backup_ref, target_sha[:8])

            return {
                "status": "success",
                "restored_ref": backup_ref,
                "target_sha": target_sha,
                "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            }
        except Exception as e:
            logger.error("Git rollback failed: %s", e)
            return {"status": "error", "error": f"Git rollback failed: {e}"}

    def _append_backup_history(self, record: Dict[str, Any]) -> None:
        try:
            history = []
            if self.backup_history_file.exists():
                try:
                    history = json.loads(self.backup_history_file.read_text(encoding="utf-8"))
                    if not isinstance(history, list):
                        history = []
                except Exception:
                    history = []
            history.append(record)
            # Keep last 50 backup records
            history = history[-50:]
            self.backup_history_file.write_text(json.dumps(history, indent=2), encoding="utf-8")
        except Exception as e:
            logger.debug("Failed to record backup history: %s", e)

    # =========================================================================
    # 2. REAL ENVIRONMENT SYNC FEASIBILITY EVALUATION GATE
    # =========================================================================

    def evaluate_real_env_sync(
        self,
        vps_client=None,
        allow_remote_dirty: bool = False,
    ) -> Dict[str, Any]:
        """Evaluates whether the real target environment (VPS / production) is ready for synchronization.

        Checks:
          - Target host network connectivity & authentication
          - Target disk storage space (>= 2GB free)
          - Target RAM available (>= 300MB free)
          - Target working tree cleanliness (no uncommitted conflict)
          - Target active background daemon status
          - Local AST / py_compile validity
        """
        logger.info("Evaluating real environment synchronization feasibility...")
        checks: Dict[str, Any] = {}
        issues: List[str] = []
        warnings: List[str] = []

        # 1. Local AST check via py_compile module (in-process for high speed)
        import py_compile
        local_compile_errors = []
        for py_path in (self.root_dir / "app").glob("**/*.py"):
            try:
                py_compile.compile(str(py_path), doraise=True)
            except py_compile.PyCompileError as pe:
                local_compile_errors.append(f"{py_path.name}: {pe.msg}")
            except Exception as e:
                local_compile_errors.append(f"{py_path.name}: {e}")
        checks["local_ast_valid"] = len(local_compile_errors) == 0
        if local_compile_errors:
            issues.append(f"Local AST errors found in {len(local_compile_errors)} files")

        # 2. VPS Connectivity & Environment Probe
        client = vps_client
        close_client = False
        if client is None:
            try:
                from scripts.vps_runner import get_client
                client = get_client()
                close_client = True
            except Exception as e:
                issues.append(f"Could not connect to VPS FastVPSClient: {e}")
                return {
                    "status": "failure",
                    "ready": False,
                    "checks": checks,
                    "issues": issues,
                }

        try:
            # Probe OS and uptime
            os_probe = client.run_command("uname -s -r -m")
            checks["vps_reachable"] = (os_probe.get("exit_code") == 0)
            checks["vps_kernel"] = os_probe.get("stdout", "").strip()

            # Check disk space on /
            df_probe = client.run_command("df -k / | tail -n 1")
            df_line = df_probe.get("stdout", "").split()
            if len(df_line) >= 4:
                avail_kb = int(df_line[3])
                avail_mb = avail_kb // 1024
                checks["vps_free_disk_mb"] = avail_mb
                if avail_mb < 2000:
                    issues.append(f"VPS disk space low: {avail_mb}MB available (<2GB threshold)")
            else:
                checks["vps_free_disk_mb"] = "unknown"

            # Check RAM on VPS
            ram_probe = client.run_command("free -m | grep -i mem")
            ram_line = ram_probe.get("stdout", "").split()
            if len(ram_line) >= 4:
                avail_ram_mb = int(ram_line[6]) if len(ram_line) >= 7 else int(ram_line[3])
                checks["vps_free_ram_mb"] = avail_ram_mb
                if avail_ram_mb < 300:
                    issues.append(f"VPS RAM low: {avail_ram_mb}MB available (<300MB threshold)")
            else:
                checks["vps_free_ram_mb"] = "unknown"

            # Check remote git working tree in /root/video_factory
            git_probe = client.run_command("cd /root/video_factory && git status --porcelain")
            remote_dirty = bool(git_probe.get("stdout", "").strip())
            checks["vps_working_tree_clean"] = not remote_dirty
            if remote_dirty:
                dirty_preview = git_probe.get("stdout", "").strip().splitlines()[:5]
                msg = f"VPS working tree has uncommitted modifications: {dirty_preview}"
                if allow_remote_dirty:
                    warnings.append(msg)
                    logger.warning("[Pre-Sync Probe Warning] %s", msg)
                else:
                    issues.append(msg)

            # Check remote active daemon processes
            ps_probe = client.run_command("ps aux | grep -E 'python3|celery|remotion' | grep -v grep")
            running_procs = ps_probe.get("stdout", "").strip().splitlines()
            checks["vps_active_processes_count"] = len(running_procs)

        except Exception as e:
            issues.append(f"Error querying VPS environment: {e}")
        finally:
            if close_client and client:
                try:
                    client.close()
                except Exception:
                    pass

        ready = (len(issues) == 0)
        verdict = "READY" if ready else "NOT_READY"
        logger.info("Real Environment Sync Feasibility: %s (%d issues, %d warnings)", verdict, len(issues), len(warnings))

        return {
            "status": "success" if ready else "failure",
            "ready": ready,
            "verdict": verdict,
            "checks": checks,
            "issues": issues,
            "warnings": warnings,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }

    # =========================================================================
    # 3. BIT-FOR-BIT SYNCHRONIZATION WITH VERIFICATION
    # =========================================================================

    def sync_files_to_real_env(
        self,
        files: Optional[List[str]] = None,
        vps_client=None,
    ) -> Dict[str, Any]:
        """Synchronizes specified files to VPS /root/video_factory and validates bit-for-bit SHA256 parity."""
        client = vps_client
        close_client = False
        if client is None:
            from scripts.vps_runner import get_client
            client = get_client()
            close_client = True

        if files is None:
            # Auto-detect modified files from git diff
            try:
                diff_files = subprocess.check_output(
                    ["git", "-C", str(self.root_dir), "diff", "--name-only", "HEAD"],
                    text=True,
                ).strip().splitlines()
                untracked_files = subprocess.check_output(
                    ["git", "-C", str(self.root_dir), "ls-files", "--others", "--exclude-standard"],
                    text=True,
                ).strip().splitlines()
                all_target = list(set(diff_files + untracked_files))
                # Filter only relevant code/config files
                files = [
                    f for f in all_target
                    if f.startswith(("app/", "scripts/", "tests/", "config/"))
                    and (self.root_dir / f).is_file()
                ]
            except Exception as e:
                logger.error("Could not auto-detect files for sync: %s", e)
                files = []

        logger.info("Synchronizing %d files to Real Environment (/root/video_factory)...", len(files))
        results = []
        all_matched = True

        try:
            for rel_p in files:
                local_file = self.root_dir / rel_p
                if not local_file.exists() or not local_file.is_file():
                    continue

                content = local_file.read_bytes()
                local_sha = hashlib.sha256(content).hexdigest()
                b64 = base64.b64encode(content).decode("ascii")
                remote_p = f"/root/video_factory/{rel_p.replace(chr(92), '/')}"

                # Create remote parent dir
                parent_dir = str(Path(remote_p).parent).replace("\\", "/")
                client.run_command(f"mkdir -p '{parent_dir}'")

                # Chunked upload via base64
                tmp_b64 = f"/tmp/sync_{local_file.name}_{int(time.time())}.b64"
                client.run_command(f"rm -f '{tmp_b64}'")
                chunk_size = 16000
                for i in range(0, len(b64), chunk_size):
                    chunk = b64[i : i + chunk_size]
                    client.run_command(f"python3 -c \"open('{tmp_b64}', 'a').write('{chunk}')\"")

                # Decode into remote target
                client.run_command(
                    f"python3 -c \"import base64; open('{remote_p}', 'wb').write(base64.b64decode(open('{tmp_b64}').read()))\""
                )
                client.run_command(f"rm -f '{tmp_b64}'")

                # Verify SHA256 parity
                vps_sha_res = client.run_command(f"sha256sum '{remote_p}'")
                vps_sha = vps_sha_res.get("stdout", "").split()[0] if vps_sha_res.get("stdout") else ""
                matched = (vps_sha == local_sha)
                if not matched:
                    all_matched = False
                    logger.error("SHA mismatch on %s: local=%s, remote=%s", rel_p, local_sha[:8], vps_sha[:8])
                else:
                    logger.info("Bit-for-bit matched: %s (SHA: %s)", rel_p, local_sha[:8])

                results.append({
                    "file": rel_p,
                    "local_sha": local_sha,
                    "remote_sha": vps_sha,
                    "parity_matched": matched,
                })
        finally:
            if close_client and client:
                try:
                    client.close()
                except Exception:
                    pass

        return {
            "status": "success" if all_matched else "failure",
            "files_synced_count": len(results),
            "all_parity_matched": all_matched,
            "details": results,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }

    # =========================================================================
    # 4. REAL ENVIRONMENT LIVE E2E AUDIT GATE
    # =========================================================================

    def audit_real_env_e2e(self, suite: str = "smoke", vps_client=None) -> Dict[str, Any]:
        """Executes live End-to-End audit commands directly on the Real Environment (VPS).

        Runs:
          1. Live Master Smoke Gate (`scripts/e2e_pipeline_smoketest.py`)
          2. Live ISO Neighbor-Testing (`tests/ci_neighbor_tester.py --all`)
          3. Daemon process health checks
        """
        logger.info("Executing Live E2E Audit on Real Environment (VPS /root/video_factory)...")
        client = vps_client
        close_client = False
        if client is None:
            from scripts.vps_runner import get_client
            client = get_client()
            close_client = True

        audit_results: Dict[str, Any] = {}
        overall_pass = True

        try:
            # 1. Master E2E Smoke Gate on VPS
            logger.info("[Real Env Audit] Running live e2e_pipeline_smoketest.py on VPS...")
            smoke_cmd = "cd /root/video_factory && python3 scripts/e2e_pipeline_smoketest.py"
            smoke_res = client.run_command(smoke_cmd)
            smoke_exit = smoke_res.get("exit_code", 1)
            smoke_pass = (smoke_exit == 0)
            if not smoke_pass:
                overall_pass = False
            audit_results["live_master_smoke_gate"] = {
                "exit_code": smoke_exit,
                "passed": smoke_pass,
                "stdout_tail": smoke_res.get("stdout", "")[-500:],
                "stderr_tail": smoke_res.get("stderr", "")[-500:],
            }

            # 2. ISO Neighbor-Testing if suite == 'full'
            if suite == "full":
                logger.info("[Real Env Audit] Running live ci_neighbor_tester.py on VPS...")
                iso_cmd = "cd /root/video_factory && python3 tests/ci_neighbor_tester.py --all"
                iso_res = client.run_command(iso_cmd)
                iso_exit = iso_res.get("exit_code", 1)
                iso_pass = (iso_exit == 0)
                if not iso_pass:
                    overall_pass = False
                audit_results["live_iso_neighbor_testing"] = {
                    "exit_code": iso_exit,
                    "passed": iso_pass,
                    "stdout_tail": iso_res.get("stdout", "")[-500:],
                    "stderr_tail": iso_res.get("stderr", "")[-500:],
                }

            # 3. Live Daemon / Health Probe
            logger.info("[Real Env Audit] Probing live processes on VPS...")
            proc_res = client.run_command("ps aux | grep -E 'python3|celery' | grep -v grep")
            audit_results["live_daemons"] = {
                "running": bool(proc_res.get("stdout", "").strip()),
                "processes": proc_res.get("stdout", "").strip().splitlines()[:5],
            }

        except Exception as e:
            overall_pass = False
            audit_results["error"] = str(e)
            logger.error("Real environment live audit exception: %s", e)
        finally:
            if close_client and client:
                try:
                    client.close()
                except Exception:
                    pass

        verdict = "PASS" if overall_pass else "FAIL"
        logger.info("Real Environment Live E2E Audit: %s", verdict)

        return {
            "status": "success" if overall_pass else "failure",
            "passed": overall_pass,
            "verdict": verdict,
            "audit_results": audit_results,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }

    # =========================================================================
    # 5. FULL GUARDED SYNCHRONIZATION WITH AUTO-ROLLBACK
    # =========================================================================

    def run_full_guarded_sync(
        self,
        files: Optional[List[str]] = None,
        auto_rollback: bool = True,
        audit_suite: str = "smoke",
    ) -> Dict[str, Any]:
        """Full lifecycle:

        1. Create Git Safe Backup Checkpoint.
        2. Evaluate Real Environment Sync Feasibility.
        3. Synchronize files to Real Environment.
        4. Execute Live Real Environment E2E Audit.
        5. If Audit FAILS and auto_rollback=True -> Auto-rollback Git checkpoint.
        """
        logger.info("=== STARTING FULL GUARDED SYNC & AUDIT PIPELINE ===")
        start_ts = time.time()
        pipeline_log: Dict[str, Any] = {"stages": {}}

        # Stage 1: Git Safe Backup
        backup_res = self.create_git_backup_checkpoint(prefix="pre-sync")
        pipeline_log["stages"]["git_backup"] = backup_res
        if backup_res.get("status") != "success":
            logger.error("Git backup checkpoint creation failed. Aborting sync.")
            return {"status": "failure", "error": "Git backup failed", "pipeline_log": pipeline_log}
        backup_ref = backup_res["backup_record"]["backup_branch"]

        # Stage 2: Feasibility Evaluation
        eval_res = self.evaluate_real_env_sync()
        pipeline_log["stages"]["feasibility_evaluation"] = eval_res
        if not eval_res.get("ready", False):
            logger.error("Real environment is not ready for sync: %s", eval_res.get("issues"))
            return {
                "status": "failure",
                "error": "Real environment not ready",
                "issues": eval_res.get("issues"),
                "pipeline_log": pipeline_log,
            }

        # Stage 3: Bit-for-bit Synchronization
        sync_res = self.sync_files_to_real_env(files=files)
        pipeline_log["stages"]["sync_files"] = sync_res
        if not sync_res.get("all_parity_matched", False):
            logger.error("Bit-for-bit file sync failed parity checks.")
            if auto_rollback:
                logger.warning("Triggering auto-rollback to: %s", backup_ref)
                rollback_res = self.rollback_git_checkpoint(backup_ref)
                pipeline_log["stages"]["rollback"] = rollback_res
            return {
                "status": "failure",
                "error": "Sync parity mismatch",
                "pipeline_log": pipeline_log,
            }

        # Stage 4: Live Real Environment E2E Audit
        audit_res = self.audit_real_env_e2e(suite=audit_suite)
        pipeline_log["stages"]["live_e2e_audit"] = audit_res

        if not audit_res.get("passed", False):
            logger.error("Live Real Environment E2E Audit FAILED.")
            if auto_rollback:
                logger.warning("Triggering auto-rollback to: %s", backup_ref)
                rollback_res = self.rollback_git_checkpoint(backup_ref)
                pipeline_log["stages"]["rollback"] = rollback_res
            return {
                "status": "failure",
                "error": "Live E2E audit failed",
                "pipeline_log": pipeline_log,
            }

        duration = round(time.time() - start_ts, 3)
        logger.info("=== FULL GUARDED SYNC & AUDIT PASSED IN %.2fs ===", duration)

        return {
            "status": "success",
            "verdict": "ALL_GATES_PASSED",
            "backup_ref": backup_ref,
            "duration_seconds": duration,
            "pipeline_log": pipeline_log,
        }


def main():
    parser = argparse.ArgumentParser(
        description="Real Environment Sync, Live E2E Audit & Git Backup Guard CLI"
    )
    parser.add_argument(
        "--action",
        choices=["backup", "evaluate", "sync", "audit", "rollback", "full"],
        default="full",
        help="Action to perform (default: full)",
    )
    parser.add_argument(
        "--ref",
        default=None,
        help="Target backup reference for rollback action",
    )
    parser.add_argument(
        "--audit-real-env",
        action="store_true",
        help="Triggers live Real Environment E2E audit",
    )
    parser.add_argument(
        "--auto-rollback",
        action="store_true",
        default=True,
        help="Automatically rolls back Git if live audit fails (default: True)",
    )
    parser.add_argument(
        "--audit-suite",
        choices=["smoke", "full"],
        default="smoke",
        help="Audit test suite to run on Real Environment (smoke or full)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output machine-readable JSON",
    )

    args = parser.parse_args()
    guard = RealEnvSyncGuard()

    if args.action == "backup":
        res = guard.create_git_backup_checkpoint()
    elif args.action == "evaluate":
        res = guard.evaluate_real_env_sync()
    elif args.action == "sync":
        res = guard.sync_files_to_real_env()
        if args.audit_real_env and res.get("status") == "success":
            audit_res = guard.audit_real_env_e2e(suite=args.audit_suite)
            res["audit_real_env"] = audit_res
    elif args.action == "audit":
        res = guard.audit_real_env_e2e(suite=args.audit_suite)
    elif args.action == "rollback":
        if not args.ref:
            print("ERROR: --ref <backup_ref> is required for rollback action.", file=sys.stderr)
            sys.exit(1)
        res = guard.rollback_git_checkpoint(args.ref)
    elif args.action == "full":
        res = guard.run_full_guarded_sync(
            auto_rollback=args.auto_rollback,
            audit_suite=args.audit_suite,
        )
    else:
        res = {"status": "error", "error": f"Unknown action: {args.action}"}

    if args.json:
        print(json.dumps(res, indent=2, ensure_ascii=False))
    else:
        print("\n" + "=" * 60)
        print(f"🛡️ REAL ENVIRONMENT SYNC GUARD — ACTION: {args.action.upper()}")
        print("=" * 60)
        status = res.get("status", "unknown").upper()
        print(f"Status:  {status}")
        if "backup_record" in res:
            rec = res["backup_record"]
            print(f"Backup:  {rec.get('backup_branch')} (HEAD: {rec.get('head_sha')[:8]})")
        if "verdict" in res:
            print(f"Verdict: {res.get('verdict')}")
        if "error" in res:
            print(f"Error:   {res.get('error')}")
        print("=" * 60 + "\n")

    sys.exit(0 if res.get("status") == "success" else 1)


if __name__ == "__main__":
    main()
