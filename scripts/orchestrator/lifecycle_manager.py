"""scripts/orchestrator/lifecycle_manager.py — Process Lifecycle & Stream Isolation.

Manages:
1. Subprocess spawning with isolated stdout/stderr stream routing to /tmp/vf_orchestrator_<run_id>/logs/.
2. Concurrency control (pool execution up to --parallel [1..4]).
3. Per-stage watchdog timeouts (--timeout) with graceful SIGTERM and forced SIGKILL escalation.
4. Graceful signal handling (SIGINT/SIGTERM) ensuring zero orphaned subprocesses.
5. Structured result tracking (WorkerResult) with execution timing and error capture.
"""

import concurrent.futures
import os
import signal
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set


@dataclass
class WorkerResult:
    """Structured result of a single stage or task execution."""
    stage_id: str
    command: List[str]
    exit_code: int
    duration_seconds: float
    stdout_log_path: Optional[str]
    stderr_log_path: Optional[str]
    stdout_preview: str
    stderr_preview: str
    timed_out: bool = False

    @property
    def success(self) -> bool:
        return self.exit_code == 0 and not self.timed_out


class SubprocessWorker:
    """Executes a single command in an isolated subprocess with watchdog and stream logging."""

    def __init__(
        self,
        stage_id: str,
        command: List[str],
        cwd: Optional[Path] = None,
        stdout_log_path: Optional[Path] = None,
        stderr_log_path: Optional[Path] = None,
        timeout_sec: float = 300.0,
        env_overrides: Optional[Dict[str, str]] = None,
        on_output_line: Optional[Callable[[str], None]] = None,
    ):
        self.stage_id = stage_id
        self.command = command
        self.cwd = cwd or Path.cwd()
        self.stdout_log_path = stdout_log_path
        self.stderr_log_path = stderr_log_path
        self.timeout_sec = timeout_sec
        self.env_overrides = env_overrides or {}
        self.on_output_line = on_output_line

        self.process: Optional[subprocess.Popen] = None
        self._timed_out = False
        self._lock = threading.Lock()

    def run(self) -> WorkerResult:
        """Runs the subprocess synchronously with watchdog timeout and stream isolation."""
        start_time = time.time()

        # Prepare environment
        env = os.environ.copy()
        # Ensure project root is in PYTHONPATH
        root_path = str(self.cwd)
        if "PYTHONPATH" in env:
            env["PYTHONPATH"] = f"{root_path}{os.pathsep}{env['PYTHONPATH']}"
        else:
            env["PYTHONPATH"] = root_path
        env["PYTHONUNBUFFERED"] = "1"
        env.update(self.env_overrides)

        # Ensure parent log directories exist
        if self.stdout_log_path:
            self.stdout_log_path.parent.mkdir(parents=True, exist_ok=True)
        if self.stderr_log_path:
            self.stderr_log_path.parent.mkdir(parents=True, exist_ok=True)

        stdout_file = (
            open(self.stdout_log_path, "w", encoding="utf-8", errors="replace")
            if self.stdout_log_path
            else subprocess.PIPE
        )
        stderr_file = (
            open(self.stderr_log_path, "w", encoding="utf-8", errors="replace")
            if self.stderr_log_path
            else subprocess.PIPE
        )

        stdout_preview_chunks: List[str] = []
        stderr_preview_chunks: List[str] = []

        try:
            # POSIX preexec_fn for process group handling if supported
            preexec_fn = None
            if os.name == "posix":
                preexec_fn = os.setsid

            with self._lock:
                self.process = subprocess.Popen(
                    self.command,
                    cwd=str(self.cwd),
                    env=env,
                    stdout=stdout_file,
                    stderr=stderr_file,
                    text=True,
                    preexec_fn=preexec_fn,
                )

            # Wait for completion with timeout
            try:
                self.process.wait(timeout=self.timeout_sec)
            except subprocess.TimeoutExpired:
                self._timed_out = True
                self.terminate()
                # Wait briefly for process to die after termination
                try:
                    self.process.wait(timeout=5.0)
                except subprocess.TimeoutExpired:
                    self.kill()

        finally:
            if stdout_file != subprocess.PIPE and not stdout_file.closed:
                stdout_file.close()
            if stderr_file != subprocess.PIPE and not stderr_file.closed:
                stderr_file.close()

        duration = round(time.time() - start_time, 3)
        exit_code = self.process.returncode if self.process else -1
        if self._timed_out:
            exit_code = 124  # Standard timeout exit code

        # Read tail previews from log files
        stdout_preview = ""
        stderr_preview = ""
        try:
            if self.stdout_log_path and self.stdout_log_path.exists():
                lines = self.stdout_log_path.read_text(encoding="utf-8", errors="replace").splitlines()
                stdout_preview = "\n".join(lines[-20:]) if lines else ""
            if self.stderr_log_path and self.stderr_log_path.exists():
                lines = self.stderr_log_path.read_text(encoding="utf-8", errors="replace").splitlines()
                stderr_preview = "\n".join(lines[-20:]) if lines else ""
        except Exception:
            pass

        return WorkerResult(
            stage_id=self.stage_id,
            command=self.command,
            exit_code=exit_code,
            duration_seconds=duration,
            stdout_log_path=str(self.stdout_log_path) if self.stdout_log_path else None,
            stderr_log_path=str(self.stderr_log_path) if self.stderr_log_path else None,
            stdout_preview=stdout_preview,
            stderr_preview=stderr_preview,
            timed_out=self._timed_out,
        )

    def terminate(self) -> None:
        """Sends SIGTERM to process group or process."""
        with self._lock:
            if not self.process or self.process.poll() is not None:
                return
            try:
                if os.name == "posix":
                    os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
                else:
                    self.process.terminate()
            except OSError:
                pass

    def kill(self) -> None:
        """Sends SIGKILL / hard kill to process group or process."""
        with self._lock:
            if not self.process or self.process.poll() is not None:
                return
            try:
                if os.name == "posix":
                    os.killpg(os.getpgid(self.process.pid), signal.SIGKILL)
                else:
                    self.process.kill()
            except OSError:
                pass


class LifecycleManager:
    """Manages pool of concurrent workers, watchdog timers, and signal handling."""

    def __init__(self, max_parallel: int = 1, default_timeout: float = 300.0):
        self.max_parallel = max(1, min(max_parallel, 4))
        self.default_timeout = default_timeout
        self.active_workers: Set[SubprocessWorker] = set()
        self._workers_lock = threading.Lock()
        self._interrupted = False

        # Register signal handlers for clean process tree shutdown
        self._setup_signals()

    def _setup_signals(self) -> None:
        def _signal_handler(signum, frame):
            self._interrupted = True
            self.terminate_all()
            sys.exit(128 + signum)

        try:
            signal.signal(signal.SIGINT, _signal_handler)
            if hasattr(signal, "SIGTERM"):
                signal.signal(signal.SIGTERM, _signal_handler)
        except (ValueError, AttributeError):
            # Signal handling may fail if not in main thread (e.g. testing)
            pass

    def register_worker(self, worker: SubprocessWorker) -> None:
        with self._workers_lock:
            self.active_workers.add(worker)

    def unregister_worker(self, worker: SubprocessWorker) -> None:
        with self._workers_lock:
            self.active_workers.discard(worker)

    def terminate_all(self) -> None:
        """Gracefully terminates all active subprocesses."""
        with self._workers_lock:
            for w in list(self.active_workers):
                try:
                    w.terminate()
                except Exception:
                    pass

    def run_worker(self, worker: SubprocessWorker) -> WorkerResult:
        """Runs a single worker synchronously with registration."""
        self.register_worker(worker)
        try:
            return worker.run()
        finally:
            self.unregister_worker(worker)

    def run_workers_parallel(self, workers: List[SubprocessWorker]) -> List[WorkerResult]:
        """Runs workers across a pool with concurrency up to max_parallel."""
        if not workers:
            return []

        results: List[WorkerResult] = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_parallel) as executor:
            future_to_worker = {executor.submit(self.run_worker, w): w for w in workers}
            for future in concurrent.futures.as_completed(future_to_worker):
                w = future_to_worker[future]
                try:
                    res = future.result()
                    results.append(res)
                except Exception as e:
                    results.append(
                        WorkerResult(
                            stage_id=w.stage_id,
                            command=w.command,
                            exit_code=1,
                            duration_seconds=0.0,
                            stdout_log_path=str(w.stdout_log_path) if w.stdout_log_path else None,
                            stderr_log_path=str(w.stderr_log_path) if w.stderr_log_path else None,
                            stdout_preview="",
                            stderr_preview=f"Worker execution exception: {e}",
                            timed_out=False,
                        )
                    )
        return results
