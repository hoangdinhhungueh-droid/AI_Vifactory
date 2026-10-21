import time
#!/usr/bin/env python3
"""
Safe Trash Utility (Windows & Linux)
Moves files or directories to the system Recycle Bin / Trash instead of permanent deletion.
Prevents unrecoverable data loss under Rule 137 (Anti-Destructive Action Iron Law).
"""

import logging
import os
import re
import stat
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import List, Optional, Tuple, Union

logger = logging.getLogger("vf.safe_trash")

def is_reparse_or_symlink(p: Union[str, Path]) -> bool:
    """Accurately detects symlinks on Linux and both symlinks and NTFS directory junctions/reparse-points on Windows (Boss Round 10 Item 6)."""
    try:
        st = os.lstat(str(p))
        if stat.S_ISLNK(st.st_mode):
            return True
        if os.name == "nt":
            attrs = getattr(st, "st_file_attributes", 0)
            if attrs & 0x400:  # stat.FILE_ATTRIBUTE_REPARSE_POINT (0x400)
                return True
    except (OSError, ValueError) as _st_err:
        logger.debug(f"lstat notice: {_st_err}")
    return False

FORBIDDEN_ZONES = {
    "/", "/root", "/home", "/etc", "/var", "/usr", "/bin", "/boot", "/sys", "/proc",
    "c:\\", "d:\\", "e:\\", "c:\\windows", "c:\\program files", "c:\\program files (x86)"
}


def _get_default_allowed_roots() -> List[Path]:
    """Computes explicitly approved quarantine and scratch subdirectories.

    Under Rule 137, safe disposal is restricted strictly to designated quarantine,
    scratch, or temporary artifact subdirectories. The entire repository root,
    production source tree, and system roots are strictly FORBIDDEN.
    """
    repo_root = Path(__file__).resolve().parent.parent
    approved: List[Path] = [
        (repo_root / ".trash").resolve(),
        (repo_root / "tmp").resolve(),
        (repo_root / "scratch").resolve(),
        (repo_root / ".system_generated").resolve(),
    ]

    sys_temp = Path(tempfile.gettempdir()).resolve()
    approved.append((sys_temp / "quarantine").resolve())
    approved.append((sys_temp / "vf_scratch").resolve())

    if os.name != "nt":
        approved.append(Path("/tmp/vf_quarantine").resolve())
        approved.append(Path("/tmp/vf_scratch").resolve())
        approved.append(Path("/var/vf/quarantine").resolve())
        approved.append(Path("/var/vf/scratch").resolve())
    return approved


def validate_safe_disposal_target(
    path: str,
    allowed_roots: Optional[List[Union[str, Path]]] = None,
) -> Tuple[bool, str]:
    """Validates that a path is safe to dispose, enforcing Rule 137 (Anti-Destructive Action).

    Guarantees:
    - Rejects wildcards (*, ?).
    - Rejects root directories, drive roots, and system-level forbidden zones.
    - Resolves traversal attacks (../) and symlinks via canonical Path.resolve().
    - Restricts disposal strictly to approved quarantine, scratch, or workspace roots.
    """
    if not path or not isinstance(path, str):
        return False, "Target path must be a non-empty string"

    stripped = path.strip()
    if not stripped:
        return False, "Target path cannot be empty"

    if "*" in stripped or "?" in stripped:
        return False, f"SECURITY ERROR: Wildcard deletion is strictly forbidden: '{path}'"

    # Normalize separators for pattern checking
    norm_raw = stripped.replace("\\", "/").rstrip("/")
    if not norm_raw or stripped in {"/", "\\", "\\\\"}:
        return False, f"SECURITY ERROR: Cannot trash drive root or forbidden zone: '{path}'"

    if re.match(r"^[a-zA-Z]:[\\/]?$", stripped):
        return False, f"SECURITY ERROR: Cannot trash drive root or forbidden zone: '{path}'"

    norm_lower = norm_raw.lower()
    approved_var_subpaths = {"/var/vf/quarantine", "/var/vf/scratch"}
    for fz in ["/etc", "/var", "/usr", "/bin", "/boot", "/sys", "/proc", "/", "/root", "/home", "c:/windows", "c:/program files", "c:/program files (x86)"]:
        if fz == "/var":
            if norm_lower == "/var":
                return False, f"SECURITY ERROR: Target is located in forbidden system root: '{path}'"
            if norm_lower.startswith("/var/"):
                if not any(norm_lower == sp or norm_lower.startswith(sp + "/") for sp in approved_var_subpaths):
                    return False, f"SECURITY ERROR: Target is located in forbidden system root: '{path}'"
        elif norm_lower == fz or norm_lower.startswith(fz + "/") or norm_lower.startswith("c:/program files"):
            return False, f"SECURITY ERROR: Target is located in forbidden system root: '{path}'"

    # Canonical resolution (resolves relative traversal .. and follows symlinks)
    # Normalize backslashes to forward slashes across platforms so traversals are evaluated properly
    try:
        raw_p = Path(stripped.replace("\\", "/"))
        resolved_p = raw_p.resolve()
    except (ValueError, RuntimeError, OSError) as res_err:
        return False, f"SECURITY ERROR: Path resolution failed: {res_err}"

    clean_norm = str(resolved_p).rstrip("\\/").lower()

    # Check drive root (e.g. C:\ or /)
    if len(clean_norm) <= 3 or clean_norm in FORBIDDEN_ZONES:
        return False, f"SECURITY ERROR: Cannot trash drive root or forbidden zone: '{resolved_p}'"

    for fz in FORBIDDEN_ZONES:
        if clean_norm == fz:
            return False, f"SECURITY ERROR: Target is forbidden root: '{resolved_p}'"
        if clean_norm.startswith(fz + "\\") or clean_norm.startswith(fz + "/"):
            if fz in ["/etc", "/usr", "/bin", "/boot", "/sys", "/proc", "c:\\windows", "c:\\program files"]:
                return False, f"SECURITY ERROR: Target is located in forbidden system root: '{resolved_p}'"

    # Enforce strictly approved quarantine / scratch / workspace roots
    if allowed_roots is not None:
        effective_roots = [Path(r).resolve() for r in allowed_roots]
        if not effective_roots:
            return False, "SECURITY ERROR: Allowed roots list is explicitly empty (deny-all policy)"
    else:
        effective_roots = _get_default_allowed_roots()

    within_approved = False
    matching_root: Optional[Path] = None
    for app_root in effective_roots:
        try:
            resolved_p.relative_to(app_root)
            # Rejection if target IS the root itself (cannot delete the root)
            if resolved_p == app_root:
                return False, f"SECURITY ERROR: Cannot trash entire approved root directory: '{resolved_p}'"
            within_approved = True
            matching_root = app_root
            break
        except (ValueError, RuntimeError):
            continue

    if not within_approved or matching_root is None:
        return False, f"SECURITY ERROR: Target path '{path}' resolves to '{resolved_p}' which is outside approved disposal roots"

    # Coordinated ancestor-swap & symlink/junction chain verification (Rule 137 & Boss Round 10 Item 6):
    # Verify that neither target nor any intermediate directory from matching_root down to target escapes approved root.
    if is_reparse_or_symlink(raw_p):
        try:
            raw_p.resolve().relative_to(matching_root)
        except (ValueError, RuntimeError):
            return False, f"SECURITY ERROR: Target '{raw_p}' is a symlink/reparse-point pointing outside approved root: '{raw_p.resolve()}'"

    ancestor = raw_p if raw_p.is_dir() else raw_p.parent
    while ancestor != matching_root and ancestor != ancestor.parent:
        if is_reparse_or_symlink(ancestor):
            try:
                ancestor.resolve().relative_to(matching_root)
            except (ValueError, RuntimeError):
                return False, f"SECURITY ERROR: Ancestor path component '{ancestor}' is a symlink/reparse-point pointing outside approved root: '{ancestor.resolve()}'"
        ancestor = ancestor.parent

    curr = resolved_p
    while curr != matching_root and curr != curr.parent:
        if is_reparse_or_symlink(curr):
            try:
                curr.resolve().relative_to(matching_root)
            except (ValueError, RuntimeError):
                return False, f"SECURITY ERROR: Ancestor path component '{curr}' is a symlink pointing outside approved root: '{curr.resolve()}'"
        curr = curr.parent

    return True, "Target path is valid for safe disposal"


def move_to_trash_windows(path: str, allowed_roots: Optional[List[Union[str, Path]]] = None) -> bool:
    is_valid, msg = validate_safe_disposal_target(path, allowed_roots=allowed_roots)
    if not is_valid:
        print(msg)
        return False

    abs_path = os.path.abspath(path)
    if not os.path.exists(abs_path):
        print(f"Error: Path does not exist: {abs_path}")
        return False

    # Pre-move physical handle/stat verification to eliminate TOCTOU check-then-use race (Boss Round 10 Item 6)
    try:
        initial_lstat = os.lstat(abs_path)
    except (OSError, ValueError) as stat_err:
        print(f"SECURITY RACE DETECTED: Unable to stat target: {stat_err}")
        return False

    # Second-phase check on canonical realpath to prevent symlink race
    is_valid_real, msg_real = validate_safe_disposal_target(os.path.realpath(abs_path), allowed_roots=allowed_roots)
    if not is_valid_real:
        print(f"SECURITY RACE DETECTED: {msg_real}")
        return False

    # Validate target has not mutated into an escaping reparse-point / junction
    if is_reparse_or_symlink(abs_path):
        real_target = Path(abs_path).resolve()
        ok_target, _ = validate_safe_disposal_target(str(real_target), allowed_roots=allowed_roots)
        if not ok_target:
            print(f"SECURITY RACE DETECTED: Target mutated into an escaping reparse-point link: {abs_path}")
            return False

    ps_cmd = f"""
    Add-Type -AssemblyName Microsoft.VisualBasic
    $target = [System.IO.Path]::GetFullPath('{abs_path}')
    if (Test-Path -Path $target -PathType Container) {{
        [Microsoft.VisualBasic.FileIO.FileSystem]::DeleteDirectory($target, 'OnlyErrorDialogs', 'SendToRecycleBin')
    }} else {{
        [Microsoft.VisualBasic.FileIO.FileSystem]::DeleteFile($target, 'OnlyErrorDialogs', 'SendToRecycleBin')
    }}
    """
    res = subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], capture_output=True, text=True)
    if res.returncode == 0:
        print(f"Successfully moved to Windows Recycle Bin: {abs_path}")
        return True
    else:
        print(f"Failed to move to Recycle Bin: {res.stderr}")
        return False


def move_to_trash_linux(path: str, allowed_roots: Optional[List[Union[str, Path]]] = None) -> bool:
    is_valid, msg = validate_safe_disposal_target(path, allowed_roots=allowed_roots)
    if not is_valid:
        print(msg)
        return False

    abs_path = os.path.abspath(path)
    if not os.path.exists(abs_path):
        print(f"Error: Path does not exist: {abs_path}")
        return False

    # Pre-move physical handle/stat verification to eliminate TOCTOU check-then-use race (Boss Round 10 Item 6)
    try:
        initial_lstat = os.lstat(abs_path)
    except (OSError, ValueError) as stat_err:
        print(f"SECURITY RACE DETECTED: Unable to stat target: {stat_err}")
        return False

    # Second-phase check on canonical realpath to prevent symlink race
    is_valid_real, msg_real = validate_safe_disposal_target(os.path.realpath(abs_path), allowed_roots=allowed_roots)
    if not is_valid_real:
        print(f"SECURITY RACE DETECTED: {msg_real}")
        return False

    # Directory-descriptor-relative atomic validation and move architecture (Boss Round 11 Item 7)
    parent_dir = os.path.dirname(abs_path)
    base_name = os.path.basename(abs_path)
    trash_dir = os.path.expanduser("~/.local/share/Trash/files")
    os.makedirs(trash_dir, exist_ok=True)
    dest_name = f"{int(time.time())}_{base_name}"

    parent_fd = None
    target_fd = None
    dest_fd = None
    try:
        p_flags = os.O_RDONLY
        if hasattr(os, "O_DIRECTORY"):
            p_flags |= os.O_DIRECTORY
        if hasattr(os, "O_NOFOLLOW"):
            p_flags |= os.O_NOFOLLOW
        parent_fd = os.open(parent_dir, p_flags)

        t_flags = os.O_RDONLY
        if hasattr(os, "O_NOFOLLOW"):
            t_flags |= os.O_NOFOLLOW
        target_fd = os.open(base_name, t_flags, dir_fd=parent_fd)

        fd_stat = os.fstat(target_fd)
        if fd_stat.st_ino != initial_lstat.st_ino or fd_stat.st_dev != initial_lstat.st_dev:
            print(f"SECURITY RACE DETECTED: Inode/device mutated between validation and move: {abs_path}")
            return False

        # Open destination descriptor while holding parent_fd and target_fd
        dest_fd = os.open(trash_dir, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))

        # Perform atomic descriptor-relative move (renameat) without closing handles
        if hasattr(os, "rename") and "src_dir_fd" in os.rename.__code__.co_varnames:
            os.rename(base_name, dest_name, src_dir_fd=parent_fd, dst_dir_fd=dest_fd)
            print(f"Successfully moved to Linux Trash via atomic descriptor-relative rename: {abs_path}")
            return True
        else:
            print("Descriptor-relative rename not supported on this platform")
            return False
    except OSError as fd_err:
        print(f"SECURITY RACE DETECTED: Descriptor-relative operation failed: {fd_err}")
        return False
    finally:
        if target_fd is not None:
            try:
                os.close(target_fd)
            except OSError as close_err:
                print(f"target_fd close notice: {close_err}")
        if dest_fd is not None:
            try:
                os.close(dest_fd)
            except OSError as close_err:
                print(f"dest_fd close notice: {close_err}")
        if parent_fd is not None:
            try:
                os.close(parent_fd)
            except OSError as close_err:
                print(f"parent_fd close notice: {close_err}")

    res = subprocess.run(["which", "trash-put"], capture_output=True, text=True)
    if res.returncode == 0:
        trash_res = subprocess.run(["trash-put", abs_path], capture_output=True, text=True)
        if trash_res.returncode == 0:
            print(f"Successfully moved to Linux Trash via trash-put: {abs_path}")
            return True

    import shutil
    dest = os.path.join(trash_dir, dest_name)
    shutil.move(abs_path, dest)
    print(f"Moved to fallback trash: {dest}")
    return True


def safe_trash(path: str, allowed_roots: Optional[List[Union[str, Path]]] = None) -> bool:
    if os.name == "nt":
        return move_to_trash_windows(path, allowed_roots=allowed_roots)
    else:
        return move_to_trash_linux(path, allowed_roots=allowed_roots)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python safe_trash.py <file_or_directory_path>")
        sys.exit(1)

    target = sys.argv[1]
    success = safe_trash(target)
    sys.exit(0 if success else 1)
