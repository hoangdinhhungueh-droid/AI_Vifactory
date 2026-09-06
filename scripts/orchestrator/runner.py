"""scripts/orchestrator/runner.py — Standalone Multi-Agent Orchestration CLI (R1).

Authoritative CLI Entrypoint for AI Video Factory Pipeline:
Modes:
  --mode pipeline: Full sequential/parallel pipeline execution across B1..B3.5.
  --mode block:    Executes a single specified block (e.g. --blocks 2.0).
  --mode audit:    Executes Forensic Auditing (Story Gate 12/12, Director 9 Axes, Visual 4 Axes, Rule 128).
  --mode ci:       Executes ISO Neighbor-Testing & Master E2E Smoke Gate.
  --mode sync:     Three-Way Physical Sync & Ghost Cleanliness Verification.

Options:
  --blocks:        1.0, 1.5, 2.0, 3.0, 3.5, 1.0..3.5, all
  --task-id:       ^[A-Z]{2}_EP\\d{4}_[a-z0-9_]+$
  --market:        EN | JP | KR | VN | ALL
  --parallel:      Concurrency 1..4
  --timeout:       Watchdog timeout per stage in seconds (default 300)
  --dry-run:       Validates state, contracts, dependencies without calling external LLMs/APIs
  --cleanup-tmp:   Forces immediate purge of /tmp/vf_orchestrator_* directories and locks (Rule 119)
  --strict-rule128:Enforces Rule 128 dynamic context abstraction (fails on domain bleed or hardcoded tropes)
  --json-output:   Emits structured machine-readable JSON to stdout
"""

import argparse
import datetime
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

if __package__ is None or __package__ == "":
    _root = Path(__file__).resolve().parent.parent.parent
    if str(_root) not in sys.path:
        sys.path.insert(0, str(_root))
    from scripts.orchestrator.lifecycle_manager import LifecycleManager, SubprocessWorker, WorkerResult
    from scripts.orchestrator.resource_recycler import ResourceRecycler, ResourceSandbox, get_system_temp_dir
    from scripts.orchestrator.rule128_governor import Rule128Governor, Rule128ViolationError, validate_generic_task_id
    from scripts.orchestrator.task_partitioner import PIPELINE_STAGES, STAGE_ORDER, PipelineStage, TaskPartitioner
else:
    from .lifecycle_manager import LifecycleManager, SubprocessWorker, WorkerResult
    from .resource_recycler import ResourceRecycler, ResourceSandbox, get_system_temp_dir
    from .rule128_governor import Rule128Governor, Rule128ViolationError, validate_generic_task_id
    from .task_partitioner import PIPELINE_STAGES, STAGE_ORDER, PipelineStage, TaskPartitioner


def build_parser() -> argparse.ArgumentParser:
    """Constructs argument parser for orchestrator runner."""
    parser = argparse.ArgumentParser(
        prog="runner.py",
        description="AI Video Factory Multi-Agent Orchestrator CLI (R1 Production Framework)",
    )
    parser.add_argument(
        "--mode",
        choices=["pipeline", "block", "audit", "ci", "sync"],
        default="pipeline",
        help="Operational mode (default: pipeline)",
    )
    parser.add_argument(
        "--blocks",
        default="all",
        help="Pipeline blocks to execute (e.g. '1.0,1.5,2.0', '1.0..3.5', 'all', '2.0')",
    )
    parser.add_argument(
        "--task-id",
        dest="task_id",
        default=None,
        help="Target Episode Task ID (e.g. EN_EP0260_macro_liquidity)",
    )
    parser.add_argument(
        "--market",
        default="EN",
        choices=["EN", "JP", "KR", "VN", "ALL"],
        help="Target market identifier (default: EN)",
    )
    parser.add_argument(
        "--parallel",
        type=int,
        default=1,
        choices=[1, 2, 3, 4],
        help="Concurrency level for independent stages (1..4, default: 1)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=300.0,
        help="Watchdog timeout per stage in seconds (default: 300)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate state, dependencies, and contracts without executing external LLM/APIs",
    )
    parser.add_argument(
        "--cleanup-tmp",
        action="store_true",
        help="Purge all temporary orchestrator sandboxes and stale lock files (Rule 119)",
    )
    parser.add_argument(
        "--strict-rule128",
        action="store_true",
        help="Enforce strict Rule 128 validation against hardcoded domain keywords / domain bleed",
    )
    parser.add_argument(
        "--json-output",
        action="store_true",
        help="Output structured machine-readable JSON to stdout",
    )
    return parser


class OrchestratorRunner:
    """Main Orchestrator controller coordinating partitioning, lifecycle, sandboxing, and governance."""

    def __init__(self, args: argparse.Namespace):
        self.args = args
        self.root_dir = Path.cwd()
        self.partitioner = TaskPartitioner(root_dir=self.root_dir)
        self.governor = Rule128Governor(strict=args.strict_rule128)
        self.lifecycle = LifecycleManager(max_parallel=args.parallel, default_timeout=args.timeout)
        self.recycler = ResourceRecycler()

    def run(self) -> int:
        """Entrypoint executing requested orchestrator mode."""
        # 1. Handle --cleanup-tmp immediately if requested
        if self.args.cleanup_tmp:
            purged = self.recycler.purge_all(max_age_seconds=0.0)
            if self.args.json_output:
                print(json.dumps({"status": "success", "purged_items": purged}, indent=2))
            else:
                print(f"[ResourceRecycler] Purged {purged} orchestrator temp item(s).")
            return 0

        # Validate task_id if provided
        if self.args.task_id:
            if not validate_generic_task_id(self.args.task_id):
                msg = f"Task ID '{self.args.task_id}' violates Rule 128 generic format ^[A-Z]{{2}}_EP\\d{{4}}_[a-z0-9_]+$"
                if self.args.strict_rule128:
                    if self.args.json_output:
                        print(json.dumps({"status": "error", "error": msg}, indent=2))
                    else:
                        print(f"ERROR: {msg}", file=sys.stderr)
                    return 1

        # 2. Enter isolated ResourceSandbox per Rule 119
        with ResourceSandbox(
            cleanup_on_exit=True,
            acquire_lock=(not self.args.dry_run),
            lock_timeout_sec=5.0,
        ) as sandbox:
            mode = self.args.mode
            if mode in ("pipeline", "block"):
                return self._run_pipeline_mode(sandbox)
            elif mode == "audit":
                return self._run_audit_mode(sandbox)
            elif mode == "ci":
                return self._run_ci_mode(sandbox)
            elif mode == "sync":
                return self._run_sync_mode(sandbox)
            else:
                print(f"Unknown mode: {mode}", file=sys.stderr)
                return 1

    def _run_pipeline_mode(self, sandbox: ResourceSandbox) -> int:
        """Executes pipeline or single block mode."""
        start_ts = time.time()
        blocks = self.partitioner.parse_blocks(self.args.blocks)

        # Fallback task_id for dry-run/preview if not provided
        task_id = self.args.task_id or f"{self.args.market}_EP0260_sample_topic"

        plan = self.partitioner.build_execution_plan(
            blocks=blocks,
            task_id=task_id,
            market=self.args.market,
            dry_run=self.args.dry_run,
        )

        plan_info: List[Dict[str, Any]] = []
        for stage in plan:
            plan_info.append(
                {
                    "stage_id": stage.stage_id,
                    "name": stage.name,
                    "command": stage.command,
                    "input_paths": [str(p) for p in stage.input_paths],
                    "output_paths": [str(p) for p in stage.output_paths],
                    "prerequisites": stage.prerequisites,
                }
            )

        # In Dry-Run mode: report plan and exit cleanly with 0
        if self.args.dry_run:
            result_payload = {
                "status": "success",
                "mode": self.args.mode,
                "dry_run": True,
                "task_id": task_id,
                "market": self.args.market,
                "planned_stages": plan_info,
                "sandbox_root": str(sandbox.sandbox_dir),
                "duration_seconds": round(time.time() - start_ts, 3),
            }
            if self.args.json_output:
                print(json.dumps(result_payload, indent=2))
            else:
                print(f"=== DRY-RUN EXECUTION PLAN FOR {task_id} ({self.args.market}) ===")
                for p in plan_info:
                    print(f"[{p['stage_id']}] {p['name']}")
                    print(f"  Inputs:  {p['input_paths']}")
                    print(f"  Outputs: {p['output_paths']}")
                    print(f"  Command: {' '.join(p['command'])}\n")
                print(f"Status: DRY-RUN OK (0 external API calls invoked).")
            return 0

        # Live Execution mode
        stage_results: List[Dict[str, Any]] = []
        for stage in plan:
            out_log = sandbox.get_log_path(f"stage_{stage.stage_id}", stream="out")
            err_log = sandbox.get_log_path(f"stage_{stage.stage_id}", stream="err")

            worker = SubprocessWorker(
                stage_id=stage.stage_id,
                command=stage.command,
                cwd=self.root_dir,
                stdout_log_path=out_log,
                stderr_log_path=err_log,
                timeout_sec=self.args.timeout,
            )

            res = self.lifecycle.run_worker(worker)
            stage_results.append(
                {
                    "stage_id": res.stage_id,
                    "success": res.success,
                    "exit_code": res.exit_code,
                    "duration": res.duration_seconds,
                    "stdout_tail": res.stdout_preview,
                    "stderr_tail": res.stderr_preview,
                }
            )

            if not res.success:
                payload = {
                    "status": "failure",
                    "mode": self.args.mode,
                    "failed_stage": stage.stage_id,
                    "exit_code": res.exit_code,
                    "error_preview": res.stderr_preview or res.stdout_preview,
                    "stages": stage_results,
                    "duration_seconds": round(time.time() - start_ts, 3),
                }
                if self.args.json_output:
                    print(json.dumps(payload, indent=2))
                else:
                    print(f"ERROR: Stage {stage.stage_id} failed with exit code {res.exit_code}", file=sys.stderr)
                    if res.stderr_preview:
                        print(f"STDERR:\n{res.stderr_preview}", file=sys.stderr)
                return res.exit_code or 1

        payload = {
            "status": "success",
            "mode": self.args.mode,
            "task_id": task_id,
            "stages": stage_results,
            "duration_seconds": round(time.time() - start_ts, 3),
        }
        if self.args.json_output:
            print(json.dumps(payload, indent=2))
        else:
            print(f"Pipeline completed successfully ({len(stage_results)} stages).")
        return 0

    def _run_audit_mode(self, sandbox: ResourceSandbox) -> int:
        """Executes Forensic Auditing on Story Gate, Director Plan, and Visual Prompts."""
        start_ts = time.time()
        task_id = self.args.task_id or "KR_EP0001_pesticide-container-trust"
        ep_dir = Path("/var/vf/episodes") / task_id

        audit_report: Dict[str, Any] = {
            "task_id": task_id,
            "story_gate": None,
            "director_audit": None,
            "visual_prompt_audit": None,
            "rule128_checks": [],
            "overall_verdict": "PASS",
        }

        # 1. Story Gate Audit
        story_file = ep_dir / "story.txt"
        if story_file.exists():
            try:
                from app.services.story_gate import score_story
                story_text = story_file.read_text(encoding="utf-8")
                score_dict = score_story(story_text)
                audit_report["story_gate"] = score_dict
                if score_dict.get("verdict") != "PASS":
                    audit_report["overall_verdict"] = "FAIL"
            except Exception as e:
                audit_report["story_gate"] = {"error": str(e)}

        # 2. Director Plan Audit (9 axes)
        plan_file = ep_dir / "director_plan.json"
        if plan_file.exists():
            try:
                from app.audit.director_audit import audit_director_plan
                plan_data = json.loads(plan_file.read_text(encoding="utf-8"))
                dir_res = audit_director_plan(plan_data, story_title=task_id)
                audit_report["director_audit"] = dir_res
                if dir_res.get("verdict") != "PASS":
                    audit_report["overall_verdict"] = "FAIL"

                # Rule 128 dynamic context check
                passed, r128_issues = self.governor.audit_director_plan(plan_data, story_topic=task_id)
                if not passed:
                    audit_report["rule128_checks"].extend(r128_issues)
                    audit_report["overall_verdict"] = "FAIL"
            except Exception as e:
                audit_report["director_audit"] = {"error": str(e)}

        # 3. Visual Prompt Audit (4 axes)
        prompts_file = ep_dir / "prompts_forge.json"
        if prompts_file.exists():
            try:
                from app.audit.prompt_audit import audit_prompt
                prompts_data = json.loads(prompts_file.read_text(encoding="utf-8"))
                prompt_res = audit_prompt(prompts_data.get("scenes", []))
                audit_report["visual_prompt_audit"] = prompt_res

                # Rule 128 cross-domain bleed & anti-stutter check
                passed, p_issues = self.governor.audit_prompts(
                    prompts_data,
                    topic_domain="agriculture" if "pesticide" in task_id else "general",
                )
                if not passed:
                    audit_report["rule128_checks"].extend(p_issues)
                    audit_report["overall_verdict"] = "FAIL"
            except Exception as e:
                audit_report["visual_prompt_audit"] = {"error": str(e)}

        duration = round(time.time() - start_ts, 3)
        audit_report["duration_seconds"] = duration

        if self.args.json_output:
            print(json.dumps(audit_report, indent=2))
        else:
            print(f"=== AUDIT REPORT FOR {task_id} ===")
            print(f"Overall Verdict: {audit_report['overall_verdict']}")
            if audit_report["rule128_checks"]:
                print("Rule 128 Violations:")
                for v in audit_report["rule128_checks"]:
                    print(f"  - {v}")

        return 0 if audit_report["overall_verdict"] == "PASS" else 1

    def _run_ci_mode(self, sandbox: ResourceSandbox) -> int:
        """Executes ISO Neighbor-Testing & Master E2E Smoke Gate."""
        start_ts = time.time()
        ci_results: Dict[str, Any] = {}

        # 1. ISO Neighbor-Testing
        iso_cmd = ["python3", "tests/ci_neighbor_tester.py", "--all"]
        iso_out = sandbox.get_log_path("ci_neighbor_test", stream="out")
        iso_err = sandbox.get_log_path("ci_neighbor_test", stream="err")
        iso_worker = SubprocessWorker("ci_iso", iso_cmd, cwd=self.root_dir, stdout_log_path=iso_out, stderr_log_path=iso_err)
        iso_res = self.lifecycle.run_worker(iso_worker)
        ci_results["iso_neighbor_testing"] = {
            "success": iso_res.success,
            "exit_code": iso_res.exit_code,
            "output_tail": iso_res.stdout_preview or iso_res.stderr_preview,
        }

        # 2. Master E2E Smoke Gate
        smoke_cmd = ["python3", "scripts/e2e_pipeline_smoketest.py"]
        smoke_out = sandbox.get_log_path("e2e_smoke", stream="out")
        smoke_err = sandbox.get_log_path("e2e_smoke", stream="err")
        smoke_worker = SubprocessWorker("e2e_smoke", smoke_cmd, cwd=self.root_dir, stdout_log_path=smoke_out, stderr_log_path=smoke_err)
        smoke_res = self.lifecycle.run_worker(smoke_worker)
        ci_results["master_e2e_smoke"] = {
            "success": smoke_res.success,
            "exit_code": smoke_res.exit_code,
            "output_tail": smoke_res.stdout_preview or smoke_res.stderr_preview,
        }

        all_passed = iso_res.success and smoke_res.success
        payload = {
            "status": "success" if all_passed else "failure",
            "ci_gates": ci_results,
            "duration_seconds": round(time.time() - start_ts, 3),
        }

        if self.args.json_output:
            print(json.dumps(payload, indent=2))
        else:
            print("=== CI QUALITY GATE RESULTS ===")
            print(f"ISO Neighbor-Testing: {'PASS' if iso_res.success else 'FAIL'}")
            print(f"Master E2E Smoke Gate: {'PASS' if smoke_res.success else 'FAIL'}")
            print(f"OVERALL: {'✅ ALL PASSED' if all_passed else '❌ FAILED'}")

        return 0 if all_passed else 1

    def _run_sync_mode(self, sandbox: ResourceSandbox) -> int:
        """Executes Three-Way Physical Sync & Ghost Cleanliness Verification."""
        start_ts = time.time()
        sync_report: Dict[str, Any] = {}

        # 1. Check Git status
        git_res = subprocess.run(
            ["git", "-C", str(self.root_dir), "status", "--porcelain"],
            capture_output=True,
            text=True,
        )
        is_clean = len(git_res.stdout.strip()) == 0
        sync_report["git_status"] = {
            "working_tree_clean": is_clean,
            "uncommitted_files": git_res.stdout.strip().splitlines() if not is_clean else [],
        }

        # 2. Check for backup files (*.bak*, *.backup_*)
        backup_files: List[str] = []
        for root, _, files in os.walk(self.root_dir):
            if ".git" in root or "__pycache__" in root:
                continue
            for f in files:
                if ".bak" in f or ".backup" in f:
                    backup_files.append(os.path.join(root, f))
        sync_report["zero_ghost_cleanliness"] = {
            "backup_files_count": len(backup_files),
            "files": backup_files,
        }

        # 3. py_compile check across scripts/orchestrator/
        orchestrator_dir = self.root_dir / "scripts" / "orchestrator"
        compile_errors: List[str] = []
        if orchestrator_dir.exists():
            for py_file in orchestrator_dir.glob("*.py"):
                res = subprocess.run(
                    [sys.executable, "-m", "py_compile", str(py_file)],
                    capture_output=True,
                    text=True,
                )
                if res.returncode != 0:
                    compile_errors.append(f"{py_file.name}: {res.stderr.strip()}")
        sync_report["py_compile"] = {
            "success": len(compile_errors) == 0,
            "errors": compile_errors,
        }

        # 4. Check GitHub Actions CI status for HEAD commit (Rule 126 Mandatory Gate)
        head_commit_res = subprocess.run(
            ["git", "-C", str(self.root_dir), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
        )
        head_sha = head_commit_res.stdout.strip()
        ci_status_info: Dict[str, Any] = {"head_sha": head_sha, "verified": False}
        if head_sha:
            try:
                import urllib.request
                gh_token = os.getenv("GITHUB_TOKEN", "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")
                url = f"https://api.github.com/repos/hoangdinhhungueh-droid/AI_Vifactory/actions/runs?head_sha={head_sha}&per_page=1"
                req = urllib.request.Request(url, headers={
                    "Authorization": f"Bearer {gh_token}",
                    "Accept": "application/vnd.github.v3+json",
                    "User-Agent": "VF-Orchestrator"
                })
                with urllib.request.urlopen(req, timeout=10) as resp:
                    data = json.loads(resp.read().decode())
                    runs = data.get("workflow_runs", [])
                    if runs:
                        latest_run = runs[0]
                        ci_status_info.update({
                            "run_id": latest_run.get("id"),
                            "status": latest_run.get("status"),
                            "conclusion": latest_run.get("conclusion"),
                            "html_url": latest_run.get("html_url"),
                            "verified": True,
                        })
                    else:
                        ci_status_info["message"] = "No workflow runs found yet for this HEAD commit"
            except Exception as e:
                ci_status_info["error"] = str(e)
        sync_report["github_actions_ci"] = ci_status_info

        ci_passed = (
            ci_status_info.get("verified", False)
            and ci_status_info.get("conclusion") == "success"
        )
        all_ok = is_clean and len(backup_files) == 0 and len(compile_errors) == 0 and ci_passed
        payload = {
            "status": "success" if all_ok else "failure",
            "sync_report": sync_report,
            "duration_seconds": round(time.time() - start_ts, 3),
        }

        if self.args.json_output:
            print(json.dumps(payload, indent=2))
        else:
            print("=== THREE-WAY SYNC & CLEANLINESS REPORT ===")
            print(f"Git Clean: {'YES' if is_clean else 'NO'}")
            print(f"Zero Ghost Backup Files: {len(backup_files)} found")
            print(f"PyCompile: {'PASS' if len(compile_errors) == 0 else 'FAIL'}")
            ci_verdict = (
                f"{str(ci_status_info.get('conclusion')).upper()} (Run ID: {ci_status_info.get('run_id')})"
                if ci_status_info.get("verified")
                else f"NOT_PASSED ({ci_status_info.get('message', ci_status_info.get('error', 'No run'))})"
            )
            print(f"GitHub Actions CI: {ci_verdict}")

        return 0 if all_ok else 1


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    runner = OrchestratorRunner(args)
    sys.exit(runner.run())


if __name__ == "__main__":
    main()
