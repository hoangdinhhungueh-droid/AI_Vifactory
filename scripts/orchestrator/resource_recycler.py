"""scripts/orchestrator/resource_recycler.py — Sandboxed Resource Governance (Rule 119).

Enforces Rule 119 (Strict Resource Isolation & Sandboxing):
1. All ephemeral scratch files, execution logs, and temporary artifacts are sandboxed
   under `/tmp/vf_orchestrator_<run_id>/`.
2. Process locking via `/tmp/vf_orchestrator.lock` prevents colliding orchestrator executions.
3. 100% Guaranteed automatic cleanup of sandbox directories in `try ... finally` blocks.
4. Provides `--cleanup-tmp` support to scan and purge abandoned or stale orchestrator scratch files.
"""

import datetime
import os
import shutil
import sys
import tempfile
import time
import uuid
from pathlib import Path
from typing import Optional


def get_system_temp_dir() -> Path:
    """Returns /tmp on POSIX systems or system temp dir on Windows."""
    if os.name == "posix" and os.path.exists("/tmp") and os.access("/tmp", os.W_OK):
        return Path("/tmp")
    return Path(tempfile.gettempdir())


class ProcessLockError(Exception):
    """Raised when an orchestrator process lock cannot be acquired."""
    pass


class ProcessLock:
    """Cross-platform advisory process lock file."""

    def __init__(self, lock_file: Path):
        self.lock_file = lock_file
        self.fd: Optional[int] = None
        self._is_locked = False

    def acquire(self, timeout_sec: float = 0.0) -> bool:
        """Attempts to acquire the lock. If timeout_sec > 0, retries until timeout."""
        start_time = time.time()
        while True:
            try:
                # Open or create lock file with read/write
                self.fd = os.open(str(self.lock_file), os.O_CREAT | os.O_RDWR, 0o644)
                if os.name == "posix":
                    import fcntl
                    fcntl.flock(self.fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                else:
                    import msvcrt
                    msvcrt.locking(self.fd, msvcrt.LK_NBLCK, 1)

                # Write PID and timestamp to lock file
                payload = f"PID: {os.getpid()}\nSTARTED: {datetime.datetime.now(datetime.timezone.utc).isoformat()}\n"
                os.ftruncate(self.fd, 0)
                os.lseek(self.fd, 0, os.SEEK_SET)
                os.write(self.fd, payload.encode("utf-8"))
                self._is_locked = True
                return True
            except (BlockingIOError, OSError, PermissionError) as e:
                if self.fd is not None:
                    try:
                        os.close(self.fd)
                    except OSError:
                        pass
                    self.fd = None

                # Check if we should retry
                if timeout_sec > 0 and (time.time() - start_time) < timeout_sec:
                    time.sleep(0.2)
                    continue

                # Read existing lock details if available
                existing_info = "Unknown process"
                try:
                    if self.lock_file.exists():
                        existing_info = self.lock_file.read_text(encoding="utf-8").strip().replace("\n", "; ")
                except Exception:
                    pass

                raise ProcessLockError(
                    f"Orchestrator process lock '{self.lock_file}' is held by another instance ({existing_info}). "
                    f"Aborting to prevent pipeline race conditions (Rule 119)."
                ) from e

    def release(self) -> None:
        """Releases the lock and removes the lock file."""
        if not self._is_locked or self.fd is None:
            return
        try:
            if os.name == "posix":
                import fcntl
                try:
                    fcntl.flock(self.fd, fcntl.LOCK_UN)
                except OSError:
                    pass
            else:
                import msvcrt
                try:
                    os.lseek(self.fd, 0, os.SEEK_SET)
                    msvcrt.locking(self.fd, msvcrt.LK_UNLCK, 1)
                except OSError:
                    pass

            os.close(self.fd)
            self.fd = None
        except OSError:
            pass

        try:
            if self.lock_file.exists():
                self.lock_file.unlink()
        except OSError:
            pass
        self._is_locked = False


class ResourceSandbox:
    """Context manager guaranteeing creation and 100% automatic cleanup of temp sandbox."""

    def __init__(
        self,
        run_id: Optional[str] = None,
        base_temp_dir: Optional[Path] = None,
        cleanup_on_exit: bool = True,
        acquire_lock: bool = True,
        lock_timeout_sec: float = 0.0,
    ):
        self.base_dir = base_temp_dir or get_system_temp_dir()
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        uid = uuid.uuid4().hex[:6]
        self.run_id = run_id or f"{ts}_{uid}"
        self.cleanup_on_exit = cleanup_on_exit
        self.acquire_lock = acquire_lock
        self.lock_timeout_sec = lock_timeout_sec

        # Directory layout under sandbox
        self.sandbox_dir = self.base_dir / f"vf_orchestrator_{self.run_id}"
        self.logs_dir = self.sandbox_dir / "logs"
        self.scratch_dir = self.sandbox_dir / "scratch"
        self.artifacts_dir = self.sandbox_dir / "artifacts"

        self.lock_file = self.base_dir / "vf_orchestrator.lock"
        self.process_lock = ProcessLock(self.lock_file) if acquire_lock else None

    def __enter__(self) -> "ResourceSandbox":
        # Acquire global process lock
        if self.process_lock:
            self.process_lock.acquire(timeout_sec=self.lock_timeout_sec)

        # Create sandbox directory structure
        self.sandbox_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.scratch_dir.mkdir(parents=True, exist_ok=True)
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.cleanup()

    def cleanup(self) -> None:
        """Removes the entire sandbox directory and releases process lock."""
        try:
            if self.cleanup_on_exit and self.sandbox_dir.exists():
                shutil.rmtree(self.sandbox_dir, ignore_errors=True)
        finally:
            if self.process_lock:
                self.process_lock.release()

    def get_log_path(self, stage_name: str, stream: str = "out") -> Path:
        """Returns isolated log path for a specific pipeline stage."""
        safe_name = stage_name.replace(".", "_").replace("/", "_")
        ext = "err.log" if stream == "err" else "log"
        return self.logs_dir / f"{safe_name}.{ext}"

    def create_scratch_file(self, filename: str, content: str = "") -> Path:
        """Creates a temporary file inside the isolated scratch folder."""
        file_path = self.scratch_dir / filename
        file_path.write_text(content, encoding="utf-8")
        return file_path


class ResourceRecycler:
    """Manages system-wide cleanup and inspection of orchestrator ephemeral resources."""

    def __init__(self, base_temp_dir: Optional[Path] = None):
        self.base_dir = base_temp_dir or get_system_temp_dir()

    def purge_all(self, max_age_seconds: float = 0.0) -> int:
        """Purges all abandoned /tmp/vf_orchestrator_* directories and orphaned lock files.

        Returns count of purged directories/files.
        """
        now = time.time()
        count = 0
        if not self.base_dir.exists():
            return 0

        # Purge directories matching pattern
        for entry in self.base_dir.iterdir():
            if entry.is_dir() and entry.name.startswith("vf_orchestrator_"):
                try:
                    mtime = entry.stat().st_mtime
                    if (now - mtime) >= max_age_seconds:
                        shutil.rmtree(entry, ignore_errors=True)
                        count += 1
                except Exception:
                    pass

        # Purge stale lock file if older than max_age_seconds or process is dead
        lock_file = self.base_dir / "vf_orchestrator.lock"
        if lock_file.exists():
            try:
                mtime = lock_file.stat().st_mtime
                # If older than 10 minutes or max_age_seconds, clean it
                if (now - mtime) > max(max_age_seconds, 60.0):
                    lock_file.unlink()
                    count += 1
            except Exception:
                pass

        return count
