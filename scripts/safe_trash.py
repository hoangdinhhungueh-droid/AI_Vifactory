#!/usr/bin/env python3
"""
Safe Trash Utility (Windows & Linux)
Moves files or directories to the system Recycle Bin / Trash instead of permanent deletion.
Prevents unrecoverable data loss under Rule 137 (Anti-Destructive Action Iron Law).
"""

import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import List, Optional, Tuple, Union

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
    for fz in ["/etc", "/var", "/usr", "/bin", "/boot", "/sys", "/proc", "/", "/root", "/home", "c:/windows", "c:/program files", "c:/program files (x86)"]:
        if norm_lower == fz or norm_lower.startswith(fz + "/") or norm_lower.startswith("c:/program files"):
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
    effective_roots = [Path(r).resolve() for r in (allowed_roots or _get_default_allowed_roots())]

    within_approved = False
    for app_root in effective_roots:
        try:
            resolved_p.relative_to(app_root)
            # Rejection if target IS the root itself (cannot delete the root)
            if resolved_p == app_root:
                return False, f"SECURITY ERROR: Cannot trash entire approved root directory: '{resolved_p}'"
            within_approved = True
            break
        except (ValueError, RuntimeError):
            continue

    if not within_approved:
        return False, f"SECURITY ERROR: Target path '{path}' resolves to '{resolved_p}' which is outside approved disposal roots"

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

    res = subprocess.run(["which", "trash-put"], capture_output=True, text=True)
    if res.returncode == 0:
        trash_res = subprocess.run(["trash-put", abs_path], capture_output=True, text=True)
        if trash_res.returncode == 0:
            print(f"Successfully moved to Linux Trash via trash-put: {abs_path}")
            return True

    trash_dir = os.path.expanduser("~/.local/share/Trash/files")
    os.makedirs(trash_dir, exist_ok=True)
    import shutil
    dest = os.path.join(trash_dir, os.path.basename(abs_path))
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
