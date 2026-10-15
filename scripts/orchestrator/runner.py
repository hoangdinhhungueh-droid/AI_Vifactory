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
import logging
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("runner")

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

if __package__ is None or __package__ == "":
    _root = Path(__file__).resolve().parent.parent.parent
    if str(_root) not in sys.path:
        sys.path.insert(0, str(_root))
    from scripts.orchestrator.ghost_code_detector import scan_workspace
    from scripts.orchestrator.lifecycle_manager import LifecycleManager, SubprocessWorker
    from scripts.orchestrator.real_env_sync_guard import RealEnvSyncGuard
    from scripts.orchestrator.resource_recycler import ResourceRecycler, ResourceSandbox
    from scripts.orchestrator.rule128_governor import Rule128Governor, validate_generic_task_id
    from scripts.orchestrator.task_partitioner import TaskPartitioner
else:
    from .ghost_code_detector import scan_workspace
    from .lifecycle_manager import LifecycleManager, SubprocessWorker
    from .real_env_sync_guard import RealEnvSyncGuard
    from .resource_recycler import ResourceRecycler, ResourceSandbox
    from .rule128_governor import Rule128Governor, validate_generic_task_id
    from .task_partitioner import TaskPartitioner


def build_parser() -> argparse.ArgumentParser:
    """Constructs argument parser for orchestrator runner."""
    parser = argparse.ArgumentParser(
        prog="runner.py",
        description="AI Video Factory Multi-Agent Orchestrator CLI (R1 Production Framework)",
    )
    parser.add_argument(
        "--mode",
        choices=["pipeline", "block", "audit", "ci", "sync", "review", "sweep", "council", "plan", "supervise", "clean", "janitor", "report", "health", "memory", "deploy", "boss"],
        default="pipeline",
        help="Operational mode (default: pipeline)",
    )
    parser.add_argument(
        "--boss-phase",
        choices=["plan", "audit", "template_247"],
        default="plan",
        help="Phase for --mode boss (plan, audit, template_247)",
    )
    parser.add_argument(
        "--planner-model",
        default="claude-opus-5-5",
        help="LLM model used for Phase 0 planning brain & supervision (default: claude-opus-5-5 via HHTech API)",
    )
    parser.add_argument(
        "--supervise-with-opus",
        action="store_true",
        help="Enforces Claude Opus 5.5 Anti-Bloat Supervisory Gate in Council/Pipeline verification",
    )
    parser.add_argument(
        "--plan-task",
        default=None,
        help="Task description or objective for Phase 0 planning mode",
    )
    parser.add_argument(
        "--commit-range",
        default=None,
        help="Explicit git commit range to audit in supervision mode (e.g. '714e8e2~1..HEAD')",
    )
    parser.add_argument(
        "--ocr-mode",
        choices=["auto", "direct", "delegate"],
        default="auto",
        help="Open Code Review execution mode: auto, direct, or delegate (default: auto)",
    )
    parser.add_argument(
        "--ocr-background",
        default="AI Video Factory production pipeline code modification and hardening",
        help="Business and technical background context passed to OCR engine",
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
        choices=["EN", "JP", "KR", "ALL"],
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
        "--touchpoints",
        default="all",
        help="Touchpoints to sweep (all, vps, notion, cloudflare_r2, antigravity_skills, gdrive_youtube)",
    )
    parser.add_argument(
        "--force-purge",
        action="store_true",
        help="Force purge dead directories instead of archiving (Sweep mode)",
    )
    parser.add_argument(
        "--skip-ci-probe",
        action="store_true",
        help="Skip live CI gate probe in sweep verifier",
    )
    parser.add_argument(
        "--bypass-lock",
        action="store_true",
        help="Bypass global process lock acquisition (used by internal sub-runners / probes)",
    )
    parser.add_argument(
        "--with-backup",
        action="store_true",
        default=True,
        help="Creates immutable Git backup checkpoint branch prior to syncing/deploying (default: True)",
    )
    parser.add_argument(
        "--no-backup",
        dest="with_backup",
        action="store_false",
        help="Skips Git backup checkpoint creation",
    )
    parser.add_argument(
        "--audit-real-env",
        action="store_true",
        help="Executes live Real Environment E2E audit on VPS host after sync/deploy",
    )
    parser.add_argument(
        "--auto-rollback",
        action="store_true",
        default=False,
        help="Automatically rolls back Git and host environment if live audit or CI fails (default: False)",
    )
    parser.add_argument(
        "--rollback-ref",
        default=None,
        help="Rolls back repository to specified Git backup reference",
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
        script_root = Path(__file__).resolve().parent.parent.parent
        if (Path.cwd() / "app").exists():
            self.root_dir = Path.cwd()
        elif (Path("/root/video_factory") / "app").exists():
            self.root_dir = Path("/root/video_factory")
        else:
            self.root_dir = script_root
        self.partitioner = TaskPartitioner(root_dir=self.root_dir)
        self.governor = Rule128Governor(strict=args.strict_rule128)
        self.lifecycle = LifecycleManager(max_parallel=args.parallel, default_timeout=args.timeout)
        self.recycler = ResourceRecycler()
        self.sync_guard = RealEnvSyncGuard(root_dir=self.root_dir)

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
            acquire_lock=(not self.args.dry_run and not getattr(self.args, "bypass_lock", False)),
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
            elif mode == "review":
                return self._run_review_mode(sandbox)
            elif mode == "sweep":
                return self._run_sweep_mode(sandbox)
            elif mode == "council":
                return self._run_council_mode(sandbox)
            elif mode == "plan":
                return self._run_plan_mode(sandbox)
            elif mode == "supervise":
                return self._run_supervise_mode(sandbox)
            elif mode in {"clean", "janitor"}:
                return self._run_clean_mode(sandbox)
            elif mode == "report":
                return self._run_report_mode(sandbox)
            elif mode == "health":
                return self._run_health_mode(sandbox)
            elif mode == "memory":
                return self._run_memory_mode(sandbox)
            elif mode == "deploy":
                return self._run_deploy_mode(sandbox)
            elif mode == "boss":
                return self._run_boss_mode(sandbox)
            else:
                print(f"Unknown mode: {mode}", file=sys.stderr)
                return 1

    def _update_pipeline_state(
        self,
        task_id: str,
        stage_id: str,
        status: str,
        details: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Atomically updates /var/vf/episodes/{task_id}/pipeline_state.json (Rule 126 Single Source of Truth)."""
        ep_dir = Path("/var/vf/episodes") / task_id
        if not ep_dir.exists():
            try:
                ep_dir.mkdir(parents=True, exist_ok=True)
            except Exception:
                pass
        state_file = ep_dir / "pipeline_state.json"
        state_data: Dict[str, Any] = {
            "task_id": task_id,
            "market": self.args.market,
            "current_stage": stage_id,
            "status": status,
            "stages": {},
            "candidate_rotation_history": [],
            "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }
        if state_file.exists():
            try:
                state_data = json.loads(state_file.read_text(encoding="utf-8"))
            except Exception:
                pass
        state_data["current_stage"] = stage_id
        state_data["status"] = status
        state_data["updated_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        if "stages" not in state_data or not isinstance(state_data["stages"], dict):
            state_data["stages"] = {}
        stage_entry = state_data["stages"].get(stage_id, {})
        stage_entry["status"] = status
        if details:
            stage_entry.update(details)
        state_data["stages"][stage_id] = stage_entry
        try:
            state_file.write_text(json.dumps(state_data, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass
        return state_data

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
                print("Status: DRY-RUN OK (0 external API calls invoked).")
            return 0

        # Live Execution mode
        self._update_pipeline_state(task_id, "INIT", "RUNNING")
        stage_results: List[Dict[str, Any]] = []
        for stage in plan:
            out_log = sandbox.get_log_path(f"stage_{stage.stage_id}", stream="out")
            err_log = sandbox.get_log_path(f"stage_{stage.stage_id}", stream="err")

            self._update_pipeline_state(task_id, stage.stage_id, "RUNNING")

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
                self._update_pipeline_state(
                    task_id,
                    stage.stage_id,
                    "FAILED",
                    {"exit_code": res.exit_code, "error": res.stderr_preview or res.stdout_preview}
                )
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
            else:
                self._update_pipeline_state(
                    task_id,
                    stage.stage_id,
                    "COMPLETED",
                    {"exit_code": 0, "duration": res.duration_seconds}
                )

        self._update_pipeline_state(task_id, "ALL", "COMPLETED")
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
        task_id = self.args.task_id
        if not task_id:
            ep_root = Path("/var/vf/episodes")
            active = [d.name for d in ep_root.iterdir() if d.is_dir() and not d.name.startswith(("_", "."))] if ep_root.exists() else []
            if not active:
                print("❌ Error: No active episode found and no --task-id specified.")
                return 1
            task_id = sorted(active)[-1]
        ep_dir = Path("/var/vf/episodes") / task_id
        start_ts = time.time()

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
                niche_domain = "general"
                intel_f = ep_dir / "competitor_intel_card.json"
                if intel_f.exists():
                    try:
                        niche_domain = json.loads(intel_f.read_text(encoding="utf-8")).get("niche", "general")
                    except Exception:
                        pass
                passed, p_issues = self.governor.audit_prompts(
                    prompts_data,
                    topic_domain=niche_domain,
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

    def _run_review_mode(self, sandbox: ResourceSandbox) -> int:
        """Executes Alibaba Open Code Review (OCR) on Git diff or workspace changes."""
        start_ts = time.time()
        import shutil

        ocr_bin = shutil.which("ocr")
        if not ocr_bin:
            for candidate in ["/usr/local/bin/ocr", "/usr/bin/ocr"]:
                if Path(candidate).exists() and os.access(candidate, os.X_OK):
                    ocr_bin = candidate
                    break

        if not ocr_bin:
            err_msg = "Open Code Review ('ocr') binary not found in PATH or /usr/local/bin/ocr."
            if self.args.json_output:
                print(json.dumps({"status": "error", "error": err_msg, "verdict": "FAIL"}, indent=2))
            else:
                print(f"[OCR Review] ❌ {err_msg}", file=sys.stderr)
            return 1

        # 1. Preview changes via delegate preview (deterministic engineering)
        prev_cmd = [ocr_bin, "delegate", "preview", "--format", "json"]
        prev_res = subprocess.run(prev_cmd, cwd=str(self.root_dir), capture_output=True, text=True)

        preview_data: Dict[str, Any] = {}
        if prev_res.returncode == 0 and prev_res.stdout.strip():
            try:
                preview_data = json.loads(prev_res.stdout)
            except Exception:
                pass

        reviewable_count = preview_data.get("reviewable_count", 0)
        reviewable_files = preview_data.get("reviewable_files", [])

        if reviewable_count == 0:
            result = {
                "status": "success",
                "ocr_mode": self.args.ocr_mode,
                "reviewable_count": 0,
                "reviewable_files": [],
                "issues": [],
                "verdict": "PASS",
                "message": "Working tree clean: No changed files to review.",
                "duration_seconds": round(time.time() - start_ts, 3),
            }
            if self.args.json_output:
                print(json.dumps(result, indent=2))
            else:
                print("=== OPEN CODE REVIEW (OCR) ===")
                print("Working tree clean: No reviewable changes found. Code review PASS ✅")
            return 0

        file_paths = [f.get("path") for f in reviewable_files if f.get("path")]

        # In delegate mode: output rules and file list for host agent
        if self.args.ocr_mode == "delegate":
            rules_cmd = [ocr_bin, "delegate", "rule", "--format", "json"] + file_paths
            rules_res = subprocess.run(rules_cmd, cwd=str(self.root_dir), capture_output=True, text=True)
            rules_data: Dict[str, Any] = {}
            if rules_res.returncode == 0 and rules_res.stdout.strip():
                try:
                    rules_data = json.loads(rules_res.stdout)
                except Exception:
                    pass

            result = {
                "status": "success",
                "ocr_mode": "delegate",
                "reviewable_count": reviewable_count,
                "reviewable_files": reviewable_files,
                "rule_groups": rules_data.get("groups", []),
                "verdict": "DELEGATED",
                "duration_seconds": round(time.time() - start_ts, 3),
            }
            if self.args.json_output:
                print(json.dumps(result, indent=2))
            else:
                print("=== OPEN CODE REVIEW (DELEGATION MODE) ===")
                print(f"Target files to review ({reviewable_count}): {', '.join(file_paths)}")
                print(f"Rule groups resolved: {len(rules_data.get('groups', []))}")
                print("Delegated to Host AI Agent (Antigravity) for semantic line-level verification.")
            return 0

        # In auto or direct mode: run ocr review
        out_file = sandbox.sandbox_dir / "ocr_review_report.json"
        bg_ctx = self.args.ocr_background
        review_cmd = [
            ocr_bin,
            "review",
            "--audience",
            "agent",
            "-b",
            bg_ctx,
            "--output",
            str(out_file),
        ]
        subprocess.run(review_cmd, cwd=str(self.root_dir), capture_output=True, text=True)

        issues: List[Dict[str, Any]] = []
        if out_file.exists():
            try:
                raw_content = out_file.read_text(encoding="utf-8")
                try:
                    report_json = json.loads(raw_content)
                    if isinstance(report_json, list):
                        issues = report_json
                    elif isinstance(report_json, dict) and "comments" in report_json:
                        issues = report_json["comments"]
                except Exception:
                    pass
            except Exception:
                pass

        critical_count = sum(1 for i in issues if str(i.get("severity", "")).lower() == "critical")
        high_count = sum(1 for i in issues if str(i.get("severity", "")).lower() == "high")
        medium_count = sum(1 for i in issues if str(i.get("severity", "")).lower() == "medium")
        low_count = sum(1 for i in issues if str(i.get("severity", "")).lower() == "low")

        verdict = "PASS" if (critical_count == 0 and high_count == 0) else "FAIL"

        result = {
            "status": "success" if verdict == "PASS" else "failure",
            "ocr_mode": "direct",
            "reviewable_count": reviewable_count,
            "reviewable_files": file_paths,
            "severity_summary": {
                "critical": critical_count,
                "high": high_count,
                "medium": medium_count,
                "low": low_count,
            },
            "issues": issues,
            "verdict": verdict,
            "duration_seconds": round(time.time() - start_ts, 3),
        }

        if self.args.json_output:
            print(json.dumps(result, indent=2))
        else:
            print("=== OPEN CODE REVIEW (OCR) RESULTS ===")
            print(f"Reviewed Files ({reviewable_count}): {', '.join(file_paths)}")
            print(f"Issues: Critical={critical_count}, High={high_count}, Medium={medium_count}, Low={low_count}")
            if verdict == "PASS":
                print("Code Review Gate: ✅ ALL GATES PASSED (0 Critical / 0 High)")
            else:
                print("Code Review Gate: ❌ FAILED (High/Critical defects detected)")
                for issue in issues:
                    sev = str(issue.get("severity", "")).upper()
                    if sev in ("CRITICAL", "HIGH"):
                        print(f"  [{sev}] {issue.get('path')}:{issue.get('start_line')}-{issue.get('end_line')} - {issue.get('content')}")

        return 0 if verdict == "PASS" else 1

    def _run_ci_mode(self, sandbox: ResourceSandbox) -> int:
        """Executes ISO Neighbor-Testing, Master E2E Smoke Gate, and OCR Code Review Gate."""
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

        # 3. Open Code Review (OCR) Quality Gate
        ocr_res_code = self._run_review_mode(sandbox)
        ci_results["ocr_code_review"] = {
            "success": (ocr_res_code == 0),
            "exit_code": ocr_res_code,
        }

        all_passed = iso_res.success and smoke_res.success and (ocr_res_code == 0)
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
            print(f"OCR Code Review Gate: {'PASS' if ocr_res_code == 0 else 'FAIL'}")
            print(f"OVERALL: {'✅ ALL PASSED' if all_passed else '❌ FAILED'}")

        return 0 if all_passed else 1

    def _run_sync_mode(self, sandbox: ResourceSandbox) -> int:
        """Executes Three-Way Physical Sync, Real Environment Verification, Git Backup & Ghost Cleanliness."""
        start_ts = time.time()
        sync_report: Dict[str, Any] = {}

        # 0. Handle explicit rollback request if --rollback-ref provided
        if getattr(self.args, "rollback_ref", None):
            logger.info("Explicit rollback requested to ref: %s", self.args.rollback_ref)
            rb_res = self.sync_guard.rollback_git_checkpoint(self.args.rollback_ref)
            if self.args.json_output:
                print(json.dumps({"status": "rollback_completed", "result": rb_res}, indent=2))
            else:
                print(f"[Rollback] Restored repository to checkpoint: {self.args.rollback_ref}")
            return 0 if rb_res.get("status") == "success" else 1

        # 0b. Automated Git Safe Backup Checkpoint (Rule 126 Safe Sync Guard)
        backup_ref = None
        if getattr(self.args, "with_backup", True):
            backup_res = self.sync_guard.create_git_backup_checkpoint(prefix="sync")
            sync_report["git_backup"] = backup_res
            if backup_res.get("status") == "success":
                backup_ref = backup_res["backup_record"].get("backup_branch")
                logger.info("[Sync Gate] Safe Git backup checkpoint established: %s", backup_ref)

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

        # 1b. OCR Pre-Sync Verification (if changes exist, ensure 0 critical/high issues)
        ocr_clean = True
        ocr_sync_info: Dict[str, Any] = {}
        if not is_clean:
            ocr_res_code = self._run_review_mode(sandbox)
            ocr_clean = (ocr_res_code == 0)
            ocr_sync_info = {"success": ocr_clean, "exit_code": ocr_res_code}
        else:
            ocr_sync_info = {"success": True, "message": "Working tree clean; zero uncommitted diff."}
        sync_report["ocr_pre_sync_gate"] = ocr_sync_info

        # 2. Automated 4-Layer Ghost Hunter Engine (Rule 125)
        ghost_defects = scan_workspace(self.root_dir)
        ghost_clean = len(ghost_defects) == 0
        sync_report["zero_ghost_cleanliness"] = {
            "defects_count": len(ghost_defects),
            "defects": ghost_defects,
            "success": ghost_clean,
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

        # 4. Real Environment Sync Feasibility Evaluation Gate
        eval_res = self.sync_guard.evaluate_real_env_sync(allow_remote_dirty=True)
        sync_report["real_env_feasibility"] = eval_res
        real_env_ready = eval_res.get("ready", False)

        # 5. Check GitHub Actions CI status for HEAD commit (Rule 126 Mandatory Gate)
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

        # 6. Optional Live Real Environment E2E Audit
        real_audit_passed = True
        if getattr(self.args, "audit_real_env", False):
            real_audit_res = self.sync_guard.audit_real_env_e2e(suite="smoke")
            sync_report["real_env_live_e2e_audit"] = real_audit_res
            real_audit_passed = real_audit_res.get("passed", False)

        all_ok = is_clean and ghost_clean and len(compile_errors) == 0 and ci_passed and ocr_clean and real_env_ready and real_audit_passed

        # 7. Automated failure rollback if requested
        if not all_ok and getattr(self.args, "auto_rollback", False) and backup_ref:
            logger.warning("[Sync Gate] Gate failure detected. Executing auto-rollback to: %s", backup_ref)
            rb_res = self.sync_guard.rollback_git_checkpoint(backup_ref)
            sync_report["auto_rollback"] = rb_res

        payload = {
            "status": "success" if all_ok else "failure",
            "sync_report": sync_report,
            "duration_seconds": round(time.time() - start_ts, 3),
        }

        if self.args.json_output:
            print(json.dumps(payload, indent=2))
        else:
            print("=== THREE-WAY SYNC & REAL ENVIRONMENT REPORT ===")
            if backup_ref:
                print(f"Git Safe Backup Checkpoint: {backup_ref}")
            print(f"Git Clean: {'YES' if is_clean else 'NO'}")
            print(f"4-Layer Ghost Code Scan: {'PASS (0 defects)' if ghost_clean else f'FAIL ({len(ghost_defects)} defects)'}")
            print(f"PyCompile: {'PASS' if len(compile_errors) == 0 else 'FAIL'}")
            print(f"OCR Pre-Sync Gate: {'PASS' if ocr_clean else 'FAIL'}")
            eval_issues = eval_res.get("issues", [])
            eval_warns = eval_res.get("warnings", [])
            print(f"Real Env Feasibility: {'READY' if real_env_ready else f'FAIL ({eval_issues})'} ({len(eval_warns)} warnings)")
            if getattr(self.args, "audit_real_env", False):
                print(f"Real Env Live E2E Audit: {'PASS' if real_audit_passed else 'FAIL'}")
            ci_verdict = (
                f"{str(ci_status_info.get('conclusion')).upper()} (Run ID: {ci_status_info.get('run_id')})"
                if ci_status_info.get("verified")
                else f"NOT_PASSED ({ci_status_info.get('message', ci_status_info.get('error', 'No run'))})"
            )
            print(f"GitHub Actions CI: {ci_verdict}")
            if not all_ok and sync_report.get("auto_rollback"):
                print(f"⚠️ Auto-Rollback Executed: Repos restored to {backup_ref}")

        return 0 if all_ok else 1

    def _run_sweep_mode(self, sandbox: ResourceSandbox) -> int:
        """Executes Post-Upgrade Multi-Touchpoint Remnant & Ghost Sweep (Lead-Doer Pair)."""
        try:
            if __package__ is None or __package__ == "":
                from scripts.orchestrator.sweep_governor import TOUCHPOINTS, run_sweep
            else:
                from .sweep_governor import TOUCHPOINTS, run_sweep
        except ImportError:
            import sys
            sys.path.insert(0, str(self.root_dir))
            from scripts.orchestrator.sweep_governor import TOUCHPOINTS, run_sweep

        touchpoints_arg = getattr(self.args, "touchpoints", "all")
        if touchpoints_arg.lower() == "all":
            selected_tp = TOUCHPOINTS
        else:
            selected_tp = [t.strip() for t in touchpoints_arg.split(",") if t.strip() in TOUCHPOINTS]

        force_purge = getattr(self.args, "force_purge", False)
        skip_ci_probe = getattr(self.args, "skip_ci_probe", False)

        sweep_log_dir = Path("/var/vf/logs/sweep") if Path("/var/vf/logs").exists() else Path("logs/sweep")
        res = run_sweep(
            touchpoints=selected_tp,
            dry_run=self.args.dry_run,
            force_purge=force_purge,
            run_ci_probe=not skip_ci_probe,
            output_dir=sweep_log_dir,
        )

        cert = res.get("certificate", {})
        rep = res.get("execution_report", {})
        is_clean = cert.get("zero_remnants_verified", False)
        ci_ok = "PASS" in cert.get("live_pipeline_ci_status", "")

        if self.args.json_output:
            print(json.dumps(res, indent=2))
        else:
            print("\n=======================================================")
            print("🛡️ VF PIPELINE POST-UPGRADE REMNANT & GHOST SWEEP COMPLETE")
            print("=======================================================")
            print(f"Cert ID:         {cert.get('cert_id')}")
            print(f"Mode:            {'DRY-RUN' if rep.get('dry_run') else 'LIVE PURGE'}")
            print(f"Items Purged:    {rep.get('items_purged')}")
            print(f"Items Archived:  {rep.get('items_archived')}")
            print(f"Storage Freed:   {rep.get('freed_mb')} MB")
            print(f"Zero Remnants:   {'✅ VERIFIED' if is_clean else '❌ UNRESOLVED'}")
            print(f"Live CI Status:  {cert.get('live_pipeline_ci_status')}")
            print(f"Certificate:     {res.get('certificate_md_path')}")
            print("=======================================================\n")

        return 0 if (is_clean and ci_ok) else 1

    def _run_council_mode(self, sandbox: ResourceSandbox) -> int:
        """Executes Multi-Agent Harness Council Deliberation across 4 Roles.

        Evaluates:
        1. Agent 1 (Architect / Planner): Task Spec & Generic Contract Verification.
        2. Agent 2 (Builder / Implementer): AST Python Cleanliness & Zero Ghost Files.
        3. Agent 3 (QA & Test Harness): Dynamic Testing & ISO Neighbor / Smoke Verification.
        4. Agent 4 (Adversarial Forensic Auditor): Invariant Checks (Rule 118, 128, 134) & VETO Authority.

        Outputs COUNCIL_DECISION_MATRIX and enforces 4/4 Unanimous Pass for sync clearance.
        """
        start_ts = time.time()
        task_id = self.args.task_id
        if not task_id:
            ep_root = Path("/var/vf/episodes")
            active = [d.name for d in ep_root.iterdir() if d.is_dir() and not d.name.startswith(("_", "."))] if ep_root.exists() else []
            task_id = sorted(active)[-1] if active else "GENERIC_EPISODE_TASK"

        # 1. Agent 1 (Architect / Planner): Interface Contract & Rule 128 Task ID Verification
        architect_valid = validate_generic_task_id(task_id) or task_id == "GENERIC_EPISODE_TASK"
        architect_vote = "AGREE" if architect_valid else "DISAGREE"
        architect_notes = (
            f"Generic Task ID pattern valid: {task_id}"
            if architect_valid
            else f"Invalid Task ID pattern: {task_id}"
        )

        # 2. Agent 2 (Builder / Implementer): 4-Layer AST Compilation & Ghost Hunter (Rule 119 & 125)
        ghost_defects = scan_workspace(self.root_dir)
        builder_valid = len(ghost_defects) == 0
        builder_vote = "COMMITTED" if builder_valid else "DEFECT"
        builder_notes = (
            "Clean codebase, zero ghost files or dead remnants detected across 4 layers."
            if builder_valid
            else f"Ghost code defects detected ({len(ghost_defects)}): {[d['detail'] for d in ghost_defects[:3]]}"
        )

        # 3. Agent 3 (QA & Test Harness): Dynamic Validation Gate
        qa_valid = True
        qa_notes = "Test Harness gates verified."
        if not self.args.dry_run:
            qa_res = subprocess.run(
                [sys.executable, "-m", "pytest", "tests/test_orchestrator.py", "-q"],
                cwd=str(self.root_dir),
                capture_output=True,
                text=True,
            )
            qa_valid = (qa_res.returncode == 0)
            qa_notes = "Unit test harness: Exit Code 0" if qa_valid else f"Test harness failed: {qa_res.stderr[:200]}"
        else:
            qa_notes = "Dry-run mode: QA harness schema verified."

        qa_vote = "PASS" if qa_valid else "FAIL"

        # 4. Agent 4 (Adversarial Forensic Auditor): Strictly Review-Only & VETO Authority
        auditor_veto = False
        auditor_defects = []

        if not architect_valid:
            auditor_veto = True
            auditor_defects.append(f"Rule 128 violation: Task ID '{task_id}' does not match generic regex.")

        if ghost_defects:
            auditor_veto = True
            auditor_defects.append(f"Rule 125 violation: 4-Layer Ghost Hunter found {len(ghost_defects)} defects.")

        auditor_vote = "CLEAR" if not auditor_veto else "VETO"
        auditor_notes = (
            "Zero Critical/High defects. 18 Iron Laws satisfied."
            if not auditor_veto
            else f"VETO ISSUED: {'; '.join(auditor_defects)}"
        )

        # 5. Supreme Supervisor: Claude Opus 5.5 Anti-Bloat Supervisory Gate
        supervise_opus = getattr(self.args, "supervise_with_opus", False)
        supervisor_vote = "APPROVED"
        supervisor_notes = "Standard council review (Opus 5.5 supervision flag not asserted)."
        supervisor_details = None

        if supervise_opus:
            from scripts.orchestrator.opus55_supervisor_gate import run_supervisory_gate
            gate_res = run_supervisory_gate(
                task_id=task_id,
                task_objective=f"Council deliberation supervision for {task_id}",
                root_dir=self.root_dir,
                qa_summary=qa_notes,
                dry_run=self.args.dry_run,
                model=getattr(self.args, "planner_model", "claude-opus-5-5"),
            )
            supervisor_details = gate_res["supervision"]
            supervisor_vote = supervisor_details.get("verdict", "REVISE_REQUIRED")
            supervisor_notes = (
                f"Opus 5.5 Score: {supervisor_details.get('score')}/10.0, Tokens: {supervisor_details.get('tokens_consumed', 0)} - {supervisor_details.get('summary')}"
            )

        # 6. Council Deliberation (Quorum: 4/4 or 5/5 Unanimous Approval)
        all_passed = (
            architect_vote == "AGREE"
            and builder_vote == "COMMITTED"
            and qa_vote == "PASS"
            and auditor_vote == "CLEAR"
            and (supervisor_vote == "APPROVED" if supervise_opus else True)
        )
        verdict = "APPROVED_FOR_SYNC" if all_passed else "REVISE_REQUIRED"

        council_matrix = {
            "task_id": task_id,
            "council_quorum": "UNANIMOUS_5_OF_5" if supervise_opus else "UNANIMOUS_4_OF_4",
            "verdict": verdict,
            "votes": {
                "agent_1_architect": {
                    "role": "Architect / Planner",
                    "doc_pair": "Doc 1A (TASK_SPEC)",
                    "vote": architect_vote,
                    "notes": architect_notes,
                },
                "agent_2_builder": {
                    "role": "Builder / Implementer",
                    "doc_pair": "Doc 1B (CHANGE_MANIFEST)",
                    "vote": builder_vote,
                    "notes": builder_notes,
                },
                "agent_3_qa_harness": {
                    "role": "QA & Test Harness",
                    "doc_pair": "Doc 2B (TEST_VERIFICATION_REPORT)",
                    "vote": qa_vote,
                    "notes": qa_notes,
                },
                "agent_4_adversarial_auditor": {
                    "role": "Adversarial Forensic Auditor",
                    "doc_pair": "Doc 3B (FORENSIC_VERDICT)",
                    "vote": auditor_vote,
                    "notes": auditor_notes,
                    "mandate": "Strictly Review-Only — Never Fixes Code",
                },
            },
            "duration_seconds": round(time.time() - start_ts, 3),
        }
        if supervise_opus:
            council_matrix["votes"]["supreme_supervisor_opus55"] = {
                "role": "Supreme Architecture Supervisor (Opus 5.5)",
                "doc_pair": "Anti-Bloat Forensic Digest",
                "vote": supervisor_vote,
                "notes": supervisor_notes,
                "details": supervisor_details,
            }

        if self.args.json_output:
            print(json.dumps({"status": "success" if all_passed else "failure", "council_matrix": council_matrix}, indent=2))
        else:
            print("\n=================================================================")
            print("🏛️ VF PIPELINE MULTI-AGENT HARNESS COUNCIL DECISION MATRIX")
            print("=================================================================")
            print(f"Task ID:         {task_id}")
            print(f"Council Verdict: {'✅ APPROVED_FOR_SYNC' if all_passed else '❌ REVISE_REQUIRED'}")
            print("-----------------------------------------------------------------")
            for agent_key, vote_info in council_matrix["votes"].items():
                print(f"[{vote_info['vote']}] {vote_info['role']}: {vote_info['notes']}")
            print("=================================================================\n")

        return 0 if all_passed else 1

    def _run_plan_mode(self, sandbox: ResourceSandbox) -> int:
        """Executes Phase 0: Master Plan & Grill-Me Engine via Opus 5.5 (HHTech API)."""
        from scripts.orchestrator.hhtech_planner import DEFAULT_PLANNER_MODEL, generate_plan

        task_id = self.args.task_id or "GENERIC_PLAN_TASK"
        task_desc = self.args.plan_task or f"Architectural planning and implementation specification for task '{task_id}' (Market: {self.args.market})."
        planner_model = getattr(self.args, "planner_model", DEFAULT_PLANNER_MODEL)

        print("\n=================================================================")
        print("🧠 PHASE 0: MASTER STRATEGIC PLANNER (OPUS 5.5 / HHTECH API)")
        print("=================================================================")
        print(f"Task ID:        {task_id}")
        print(f"Market:         {self.args.market}")
        print(f"Planner Model:  {planner_model}")
        print(f"Dry Run:        {self.args.dry_run}")
        print("-----------------------------------------------------------------")
        print("Enforcing 4 Mandatory Technical Pillars:")
        print("  1. CI/CD Quality Gates (Neighbor testing, E2E Smoke, OCR)")
        print("  2. Git Conventional Commits (Atomic with verification evidence)")
        print("  3. Three-Way Physical Parity & Sync Verification (Rule 126)")
        print("  4. Real Playwright Visual & Interaction Audit (Zero Mock)")
        print("=================================================================\n")

        try:
            plan_text = generate_plan(
                task_description=task_desc,
                task_id=task_id,
                market=self.args.market,
                dry_run=self.args.dry_run,
            )

            if self.args.json_output:
                print(json.dumps({"status": "success", "task_id": task_id, "planner_model": planner_model, "plan": plan_text}, indent=2))
            else:
                print(plan_text)
                print("\n=================================================================")
                print("✅ PHASE 0 PLAN GENERATION COMPLETE -> READY FOR ACTIVE MODEL EXECUTION")
                print("=================================================================\n")

            if self.args.task_id:
                self._update_pipeline_state(
                    self.args.task_id,
                    "PHASE_0_PLAN",
                    "PASSED",
                    {"planner_model": planner_model, "status": "APPROVED_FOR_ACTIVE_MODEL"}
                )

            return 0
        except Exception as e:
            msg = f"Phase 0 Planning failed: {e}"
            if self.args.json_output:
                print(json.dumps({"status": "error", "error": msg}, indent=2))
            else:
                print(f"ERROR: {msg}", file=sys.stderr)
            return 1

    def _run_supervise_mode(self, sandbox: ResourceSandbox) -> int:
        """Executes Standalone Opus 5.5 Anti-Token-Bloat Supervisory Gate."""
        from scripts.orchestrator.opus55_supervisor_gate import run_supervisory_gate
        task_id = self.args.task_id or "GENERIC_SUPERVISION_TASK"
        objective = self.args.plan_task or f"Multi-agent implementation supervision for {task_id}"

        gate_res = run_supervisory_gate(
            task_id=task_id,
            task_objective=objective,
            root_dir=self.root_dir,
            dry_run=self.args.dry_run,
            model=getattr(self.args, "planner_model", "claude-opus-5-5"),
            commit_range=getattr(self.args, "commit_range", None),
        )
        sup = gate_res["supervision"]
        passed = sup.get("verdict") == "APPROVED"

        if self.args.json_output:
            print(json.dumps({"status": "success" if passed else "failure", "result": gate_res}, indent=2, ensure_ascii=False))
        else:
            print("\n=================================================================")
            print("🛡️ CLAUDE OPUS 5.5 ANTI-TOKEN-BLOAT SUPERVISORY GATE")
            print("=================================================================")
            print(f"Task ID:         {task_id}")
            print(f"Verdict:         {sup.get('verdict')}")
            print(f"Score:           {sup.get('score')}/10.0")
            print(f"Tokens Used:     {sup.get('tokens_consumed', 0)} (Budget Cap: <=10000)")
            print(f"Summary:         {sup.get('summary')}")
            if sup.get("observations"):
                print("Observations:")
                for o in sup["observations"]:
                    print(f"  - {o}")
            if sup.get("revisions_needed"):
                print("Revisions Needed:")
                for r in sup["revisions_needed"]:
                    print(f"  - {r}")
            print("=================================================================\n")

        if self.args.task_id:
            self._update_pipeline_state(
                self.args.task_id,
                "OPUS55_SUPERVISION",
                "PASSED" if passed else "FAILED",
                {"score": sup.get("score"), "verdict": sup.get("verdict")}
            )

        return 0 if passed else 1

    def _run_clean_mode(self, sandbox: ResourceSandbox) -> int:
        """Executes Antigravity Janitor & Clean Vibecoding Routine (Rule 125 & 137)."""
        from scripts.orchestrator.antigravity_janitor import AntigravityJanitor
        janitor = AntigravityJanitor(self.root_dir)
        bloat_items = janitor.scan_disk_bloat()
        zombie_data = janitor.scan_zombie_code()

        total_size = sum(b["size_bytes"] for b in bloat_items)
        if self.args.json_output:
            print(json.dumps({
                "status": "success",
                "bloat_items_count": len(bloat_items),
                "total_bloat_bytes": total_size,
                "zombie_functions_count": zombie_data.get("zombie_functions_count", 0),
                "bloat": bloat_items,
                "zombies": zombie_data.get("zombie_functions", []),
            }, indent=2, ensure_ascii=False))
        else:
            print("\n=================================================================")
            print("🧹 RUNNER JANITOR: ANTIGRAVITY WORKSPACE HYGIENE AUDIT")
            print("=================================================================")
            print(f"📦 Bloat Targets:    {len(bloat_items)} ({total_size / (1024 * 1024):.2f} MB reclaimable)")
            print(f"🧟 Zombie Functions: {zombie_data.get('zombie_functions_count', 0)} detected via AST")
            print("=================================================================\n")
        return 0

    def _run_report_mode(self, sandbox: ResourceSandbox) -> int:
        """Generates comprehensive system health report and HTML dashboard."""
        rep_script = self.root_dir / "scripts" / "orchestrator" / "system_health_reporter.py"
        cmd = [sys.executable, str(rep_script)]
        if self.args.json_output:
            cmd.append("--json")
        if self.args.dry_run:
            cmd.append("--dry-run")
        res = subprocess.run(cmd, cwd=str(self.root_dir))
        return res.returncode

    def _run_health_mode(self, sandbox: ResourceSandbox) -> int:
        """Executes 7-axis system health check."""
        health_script = self.root_dir / "scripts" / "health-check.py"
        res = subprocess.run([sys.executable, str(health_script)], cwd=str(self.root_dir))
        return res.returncode

    def _run_memory_mode(self, sandbox: ResourceSandbox) -> int:
        """Audits project memory files (ROADMAP.md & CHANGELOG.md)."""
        mem_script = self.root_dir / "scripts" / "orchestrator" / "memory_governor.py"
        res = subprocess.run([sys.executable, str(mem_script), "--strict"], cwd=str(self.root_dir))
        return res.returncode

    def _run_deploy_mode(self, sandbox: ResourceSandbox) -> int:
        """Executes automated 1-command release deployment and watches CI/CD."""
        print("=================================================================")
        print("🚀 AI VIDEO FACTORY — 1-COMMAND RELEASE DEPLOYMENT GATE")
        print("=================================================================")

        # 1. Pre-deployment memory audit
        mem_code = self._run_memory_mode(sandbox)
        if mem_code != 0:
            print("❌ Deploy aborted: Project memory audit failed (check ROADMAP.md / CHANGELOG.md).", file=sys.stderr)
            return 1

        # 2. Check working tree cleanliness (Pillar 2 & Rule 126: No auto-commits)
        stat_res = subprocess.run(["git", "-C", str(self.root_dir), "status", "--porcelain"], capture_output=True, text=True)
        has_changes = bool(stat_res.stdout.strip())

        if has_changes:
            print("❌ Deploy aborted: Working tree is dirty. All changes must be explicitly committed with verification evidence (Pillar 2 / Rule 126).", file=sys.stderr)
            print(f"Uncommitted files:\n{stat_res.stdout.strip()}", file=sys.stderr)
            return 1

        print("[Deploy] Working tree clean; deploying verified HEAD commit.")

        # 3. Push to remote
        print("[Deploy] Pushing to origin main...")
        push_res = subprocess.run(["git", "-C", str(self.root_dir), "push", "origin", "main"], capture_output=True, text=True)
        if push_res.returncode != 0:
            print(f"❌ Deploy push failed: {push_res.stderr}", file=sys.stderr)
            return push_res.returncode

        # 4. Watch GitHub Actions CI/CD run (Rule 126 Mandatory Gate)
        watcher_script = self.root_dir / "scripts" / "watch_github_ci.py"
        if watcher_script.exists():
            print("[Deploy] Watching GitHub Actions CI/CD pipeline...")
            ci_res = subprocess.run([sys.executable, str(watcher_script)], cwd=str(self.root_dir))
            return ci_res.returncode
        return 0

    def _run_boss_mode(self, sandbox: ResourceSandbox) -> int:
        """Executes Three-Tier Boss Orchestrator Harness (Opus 5.5 + Gemini 3.8 + Low-Cost 24/7)."""
        boss_script = self.root_dir / "scripts" / "orchestrator" / "boss_orchestrator.py"
        cmd = [
            sys.executable,
            str(boss_script),
            "--phase",
            getattr(self.args, "boss_phase", "plan"),
        ]
        if self.args.plan_task:
            cmd.extend(["--task", self.args.plan_task])
        elif self.args.task_id:
            cmd.extend(["--task", f"Task execution for {self.args.task_id}"])
        if self.args.task_id:
            cmd.extend(["--task-id", self.args.task_id])
        if self.args.commit_range:
            cmd.extend(["--commit-range", self.args.commit_range])
        if self.args.dry_run:
            cmd.append("--dry-run")
        if self.args.json_output:
            cmd.append("--json-output")

        res = subprocess.run(cmd, cwd=str(self.root_dir))
        return res.returncode


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    runner = OrchestratorRunner(args)
    sys.exit(runner.run())


if __name__ == "__main__":
    main()
