"""tests/test_orchestrator.py — Comprehensive Unit & Integration Tests for R1 Orchestrator Framework."""

import json
import os
import sys
import tempfile
import time
from pathlib import Path

import pytest

from scripts.orchestrator.lifecycle_manager import LifecycleManager, SubprocessWorker, WorkerResult
from scripts.orchestrator.resource_recycler import (
    ProcessLock,
    ProcessLockError,
    ResourceRecycler,
    ResourceSandbox,
    get_system_temp_dir,
)
from scripts.orchestrator.rule128_governor import (
    Rule128Governor,
    Rule128ViolationError,
    validate_generic_task_id,
)
from scripts.orchestrator.runner import build_parser, OrchestratorRunner
from scripts.orchestrator.task_partitioner import (
    PIPELINE_STAGES,
    STAGE_ORDER,
    PipelineStage,
    TaskPartitioner,
)


class TestRule128Governor:
    """Tests for Rule 128 Architectural Governance Guard."""

    def test_validate_generic_task_id(self):
        # Valid cases conforming to Rule 117 / 128
        assert validate_generic_task_id("EN_EP0260_macro_liquidity")
        assert validate_generic_task_id("KR_EP0001_pesticide_container_trust")
        assert validate_generic_task_id("JP_EP0999_semiconductor_embargo")
        assert validate_generic_task_id("VN_EP0010_coffee_supply_chain")

        # Invalid cases
        assert not validate_generic_task_id("")
        assert not validate_generic_task_id("EP0260_topic")
        assert not validate_generic_task_id("en_ep0260_topic")
        assert not validate_generic_task_id("EN_EP260_topic")
        assert not validate_generic_task_id("EN_EP0260")
        assert not validate_generic_task_id("EN-EP0260-topic")

    def test_governor_task_id_strict(self):
        gov = Rule128Governor(strict=True)
        assert gov.check_task_id("EN_EP0260_valid_task")
        with pytest.raises(Rule128ViolationError):
            gov.check_task_id("invalid_task_id")

    def test_prompts_cross_domain_bleed_detection(self):
        gov = Rule128Governor(strict=False)

        # Non-tech story (agriculture) leaking tech terms
        leaky_prompts = {
            "backgrounds": {
                "bg_1": {
                    "prompt": "16:9 cinematic shot of a rural farm with server rack in the barn, safe zone bottom 20%"
                }
            },
            "foregrounds": {
                "fg_1": {
                    "prompt": "1:1 stylized comic editorial illustration of farmer on #FF00FF magenta background"
                }
            },
        }
        passed, issues = gov.audit_prompts(leaky_prompts, topic_domain="agriculture")
        assert not passed
        assert any("server rack" in issue.lower() for issue in issues)

    def test_prompts_stuttering_detection(self):
        gov = Rule128Governor(strict=False)

        # Prompt with stuttering
        stutter_prompts = {
            "backgrounds": {"bg_1": "16:9 cinematic shot of countryside, safe zone bottom 20%"},
            "foregrounds": {
                "fg_1": "Stylized editorial graphic novel illustration of Stylized editorial graphic novel illustration of inspector on #FF00FF magenta"
            },
        }
        passed, issues = gov.audit_prompts(stutter_prompts, topic_domain="general")
        assert not passed
        assert any("stuttering" in issue.lower() for issue in issues)

    def test_prompts_chroma_key_enforcement(self):
        gov = Rule128Governor(strict=False)

        # Missing #FF00FF in foreground
        missing_chroma = {
            "backgrounds": {"bg_1": "16:9 cinematic shot of courtroom, safe zone bottom 20%"},
            "foregrounds": {"fg_1": "1:1 stylized portrait of judge on white background"},
        }
        passed, issues = gov.audit_prompts(missing_chroma, topic_domain="general")
        assert not passed
        assert any("chroma key" in issue.lower() or "#ff00ff" in issue.lower() for issue in issues)

    def test_prompts_clean_pass(self):
        gov = Rule128Governor(strict=True)

        clean_prompts = {
            "backgrounds": {
                "bg_1": "16:9 widescreen cinematic rural landscape under overcast sky, bottom 20% safe zone"
            },
            "foregrounds": {
                "fg_1": "1:1 stylized editorial graphic novel illustration of investigator on solid #FF00FF pure magenta background"
            },
        }
        passed, issues = gov.audit_prompts(clean_prompts, topic_domain="agriculture")
        assert passed
        assert len(issues) == 0

    def test_ast_scanner_flags_static_archetype_dict(self):
        gov = Rule128Governor(strict=False)
        code_with_violation = """
# Prohibited static dictionary
CINEMATIC_ARCHETYPES = {
    'agriculture': ['pesticide', 'farm'],
    'finance': ['wall street']
}
"""
        violations = gov.scan_code_ast(code_with_violation, filename="test_module.py")
        assert len(violations) >= 1
        assert "CINEMATIC_ARCHETYPES" in violations[0]


class TestResourceRecyclerAndSandbox:
    """Tests for Rule 119 Sandboxing and 100% Resource Cleanup."""

    def test_sandbox_lifecycle_and_cleanup(self):
        sandbox_path = None
        with ResourceSandbox(acquire_lock=False) as sandbox:
            sandbox_path = sandbox.sandbox_dir
            assert sandbox_path.exists()
            assert sandbox.logs_dir.exists()
            assert sandbox.scratch_dir.exists()
            assert sandbox.artifacts_dir.exists()

            # Create a file inside scratch
            temp_file = sandbox.create_scratch_file("test.txt", "ephemeral content")
            assert temp_file.exists()

            # Create log path
            log_p = sandbox.get_log_path("stage_1.0", stream="out")
            log_p.write_text("log data", encoding="utf-8")
            assert log_p.exists()

        # After exiting context manager, sandbox MUST be 100% deleted
        assert not sandbox_path.exists()

    def test_process_lock_acquisition_and_release(self):
        temp_dir = Path(tempfile.mkdtemp())
        lock_file = temp_dir / "test_orchestrator.lock"

        lock1 = ProcessLock(lock_file)
        assert lock1.acquire()
        assert lock_file.exists()

        # Second lock attempt should fail with ProcessLockError
        lock2 = ProcessLock(lock_file)
        with pytest.raises(ProcessLockError):
            lock2.acquire(timeout_sec=0.1)

        # Release first lock
        lock1.release()
        assert not lock_file.exists()

        # Now lock2 can acquire
        assert lock2.acquire()
        lock2.release()

    def test_resource_recycler_purge(self):
        base_dir = Path(tempfile.mkdtemp())
        # Create fake abandoned sandboxes
        dir1 = base_dir / "vf_orchestrator_old1"
        dir2 = base_dir / "vf_orchestrator_old2"
        dir1.mkdir()
        dir2.mkdir()

        recycler = ResourceRecycler(base_temp_dir=base_dir)
        purged = recycler.purge_all(max_age_seconds=0.0)
        assert purged >= 2
        assert not dir1.exists()
        assert not dir2.exists()


class TestLifecycleManager:
    """Tests for Subprocess Lifecycle, Watchdogs, and Stream Capture."""

    def test_worker_execution_and_stream_capture(self, tmp_path):
        out_log = tmp_path / "test.log"
        err_log = tmp_path / "test.err"

        # Python one-liner to write stdout and stderr
        cmd = [
            sys.executable,
            "-c",
            "import sys; sys.stdout.write('stdout test\\n'); sys.stderr.write('stderr test\\n')",
        ]

        worker = SubprocessWorker(
            stage_id="test_stage",
            command=cmd,
            stdout_log_path=out_log,
            stderr_log_path=err_log,
            timeout_sec=10.0,
        )

        lifecycle = LifecycleManager(max_parallel=1)
        res = lifecycle.run_worker(worker)

        assert res.success
        assert res.exit_code == 0
        assert not res.timed_out
        assert "stdout test" in out_log.read_text(encoding="utf-8")
        assert "stderr test" in err_log.read_text(encoding="utf-8")

    def test_worker_watchdog_timeout(self, tmp_path):
        out_log = tmp_path / "timeout.log"
        err_log = tmp_path / "timeout.err"

        # Python command that sleeps longer than timeout
        cmd = [sys.executable, "-c", "import time; time.sleep(5)"]

        worker = SubprocessWorker(
            stage_id="timeout_stage",
            command=cmd,
            stdout_log_path=out_log,
            stderr_log_path=err_log,
            timeout_sec=0.5,
        )

        lifecycle = LifecycleManager(max_parallel=1)
        res = lifecycle.run_worker(worker)

        assert not res.success
        assert res.timed_out
        assert res.exit_code == 124

    def test_parallel_worker_execution(self, tmp_path):
        workers = []
        for i in range(3):
            out_p = tmp_path / f"worker_{i}.log"
            cmd = [sys.executable, "-c", f"import time; time.sleep(0.1); print('worker_{i}')"]
            w = SubprocessWorker(
                stage_id=f"worker_{i}",
                command=cmd,
                stdout_log_path=out_p,
                timeout_sec=5.0,
            )
            workers.append(w)

        lifecycle = LifecycleManager(max_parallel=3)
        start_t = time.time()
        results = lifecycle.run_workers_parallel(workers)
        duration = time.time() - start_t

        assert len(results) == 3
        assert all(r.success for r in results)
        # Should run in parallel, taking ~0.2s rather than ~0.3s+ sequentially
        assert duration < 3.0


class TestTaskPartitioner:
    """Tests for Task Partitioner & Contract Validation."""

    def test_parse_blocks(self):
        partitioner = TaskPartitioner()

        # All
        assert partitioner.parse_blocks("all") == list(STAGE_ORDER)
        assert partitioner.parse_blocks(None) == list(STAGE_ORDER)

        # Range
        assert partitioner.parse_blocks("3.0..3.5") == ["3.0", "3.5"]
        assert partitioner.parse_blocks("1.0..1.5") == ["1.0", "1.5"]

        # Comma separated
        assert partitioner.parse_blocks("1.0,2.0,3.5") == ["1.0", "2.0", "3.5"]
        assert partitioner.parse_blocks("b1.5, b3") == ["1.5", "3.0"]

        # Invalid
        with pytest.raises(ValueError):
            partitioner.parse_blocks("3.0..1.0")
        with pytest.raises(ValueError):
            partitioner.parse_blocks("unknown_block")

    def test_build_execution_plan(self):
        partitioner = TaskPartitioner()
        blocks = ["1.0", "1.5", "2.0"]
        task_id = "EN_EP0260_macro_liquidity"
        plan = partitioner.build_execution_plan(blocks, task_id=task_id, market="EN", dry_run=True)

        assert len(plan) == 3
        assert plan[0].stage_id == "1.0"
        assert plan[1].stage_id == "1.5"
        assert plan[2].stage_id == "2.0"
        assert any("EN_EP0260_macro_liquidity" in str(p) for p in plan[0].output_paths)

    def test_validate_block_contract_schema(self, tmp_path):
        partitioner = TaskPartitioner(vf_var_dir=tmp_path)

        # Valid B1 pending task
        b1_file = tmp_path / "pending_tasks" / "EN_EP0260_topic.json"
        b1_file.parent.mkdir(parents=True, exist_ok=True)
        b1_file.write_text(
            json.dumps({
                "task_id": "EN_EP0260_topic",
                "market": "EN",
                "raw_term": "Macro Liquidity",
                "viability_score": 85.0,
            }),
            encoding="utf-8",
        )
        ok, issues = partitioner.validate_block_contract_schema("1.0", b1_file)
        assert ok
        assert len(issues) == 0

        # Invalid B1 pending task (missing required fields)
        bad_b1 = tmp_path / "pending_tasks" / "bad.json"
        bad_b1.write_text(json.dumps({"invalid": True}), encoding="utf-8")
        ok, issues = partitioner.validate_block_contract_schema("1.0", bad_b1)
        assert not ok
        assert len(issues) > 0

    def test_check_prerequisites(self, tmp_path):
        partitioner = TaskPartitioner(vf_var_dir=tmp_path)
        task_id = "EN_EP0260_test_topic"

        # B1 has no prerequisites
        ok, missing = partitioner.check_prerequisites("1.0", task_id, "EN")
        assert ok
        assert len(missing) == 0

        # B1.5 requires pending task file
        ok, missing = partitioner.check_prerequisites("1.5", task_id, "EN")
        assert not ok
        assert len(missing) > 0


class TestDirectorPlanAudit:
    """Tests for Rule 128 Director Plan auditing."""

    def test_valid_director_plan(self):
        gov = Rule128Governor(strict=False)
        plan = {
            "dynamic_context": {
                "era_anchor": "Late 1990s Asian Financial Crisis",
                "physical_environment": "Seoul financial district banking headquarters",
                "lighting_mood": "High contrast fluorescent and overcast gloom",
            },
            "character_ensemble": [
                {"role_name": "Senior Bank Examiner", "attire": "Dark wool coat, trench"},
                {"role_name": "Whistleblower Trader", "attire": "Disheveled shirt, loose tie"},
            ],
            "scenes": [
                {
                    "scene_id": "scene_001",
                    "setting_description": "Seoul commercial bank trading room with paperwork piled high",
                    "character_description": "Exhausted senior trader staring at ledger",
                }
            ],
        }
        passed, issues = gov.audit_director_plan(plan)
        assert passed
        assert len(issues) == 0

    def test_director_plan_with_stutter(self):
        gov = Rule128Governor(strict=False)
        plan = {
            "scenes": [
                {
                    "scene_id": "scene_001",
                    "setting_description": "Seoul bank trading room Seoul bank trading room in winter",
                    "character_description": "Trader staring",
                }
            ],
        }
        passed, issues = gov.audit_director_plan(plan)
        assert not passed
        assert any("stuttering" in i.lower() for i in issues)


class TestRunnerCLI:
    """Tests for Runner CLI parsing and dry-run execution."""

    def test_cli_dry_run_json_output(self, capsys):
        parser = build_parser()
        args = parser.parse_args([
            "--mode", "pipeline",
            "--blocks", "1.0..3.5",
            "--task-id", "EN_EP0260_macro_liquidity",
            "--dry-run",
            "--json-output",
        ])
        runner = OrchestratorRunner(args)
        ret = runner.run()

        assert ret == 0
        captured = capsys.readouterr()
        payload = json.loads(captured.out)
        assert payload["status"] == "success"
        assert payload["dry_run"] is True
        assert len(payload["planned_stages"]) >= 5

    def test_cli_single_block_dry_run(self, capsys):
        parser = build_parser()
        args = parser.parse_args([
            "--mode", "block",
            "--blocks", "2.0",
            "--task-id", "EN_EP0260_macro_liquidity",
            "--dry-run",
            "--json-output",
        ])
        runner = OrchestratorRunner(args)
        ret = runner.run()

        assert ret == 0
        captured = capsys.readouterr()
        payload = json.loads(captured.out)
        assert len(payload["planned_stages"]) == 1
        assert payload["planned_stages"][0]["stage_id"] == "2.0"

    def test_cli_cleanup_tmp(self, capsys):
        parser = build_parser()
        args = parser.parse_args(["--cleanup-tmp", "--json-output"])
        runner = OrchestratorRunner(args)
        ret = runner.run()

        assert ret == 0
        captured = capsys.readouterr()
        payload = json.loads(captured.out)
        assert payload["status"] == "success"
        assert "purged_items" in payload

    def test_cli_strict_rule128_rejection(self, capsys):
        parser = build_parser()
        args = parser.parse_args([
            "--task-id", "invalid-bad-id",
            "--strict-rule128",
            "--json-output",
        ])
        runner = OrchestratorRunner(args)
        ret = runner.run()

        assert ret == 1
        captured = capsys.readouterr()
        payload = json.loads(captured.out)
        assert payload["status"] == "error"
        assert "Rule 128" in payload["error"]
