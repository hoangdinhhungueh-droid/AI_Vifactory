#!/usr/bin/env python3
"""
Safe Trash Utility (Windows & Linux)
Moves files or directories to the system Recycle Bin / Trash instead of permanent deletion.
Prevents unrecoverable data loss.
"""

import os
import subprocess
import sys

FORBIDDEN_ZONES = {
    "/", "/root", "/home", "/etc", "/var", "/usr", "/bin", "/boot", "/sys", "/proc",
    "c:\\", "d:\\", "e:\\", "c:\\windows", "c:\\program files", "c:\\program files (x86)"
}


def validate_safe_disposal_target(path: str) -> tuple[bool, str]:
    """Validates that a path is safe to dispose, enforcing Rule 137 (Anti-Destructive Action).

    Guarantees:
    - Rejects wildcards (*, ?).
    - Rejects root directories and system-level forbidden zones.
    - Resolves traversal attacks (../).
    """
    if not path or not isinstance(path, str):
        return False, "Target path must be a non-empty string"

    stripped = path.strip()
    if not stripped:
        return False, "Target path cannot be empty"

    if "*" in stripped or "?" in stripped:
        return False, f"SECURITY ERROR: Wildcard deletion is strictly forbidden: '{path}'"

    # Normalize separators for cross-platform checking
    norm_raw = stripped.replace("\\", "/").rstrip("/")
    if not norm_raw or stripped in {"/", "\\", "\\\\"}:
        return False, f"SECURITY ERROR: Cannot trash drive root or forbidden zone: '{path}'"

    import re
    if re.match(r"^[a-zA-Z]:[\\/]?$", stripped):
        return False, f"SECURITY ERROR: Cannot trash drive root or forbidden zone: '{path}'"

    norm_lower = norm_raw.lower()
    for fz in ["/etc", "/var", "/usr", "/bin", "/boot", "/sys", "/proc", "/", "/root", "/home", "c:/windows", "c:/program files"]:
        if norm_lower == fz or norm_lower.startswith(fz + "/"):
            return False, f"SECURITY ERROR: Target is located in forbidden system root: '{path}'"

    abs_path = os.path.abspath(stripped)
    clean_norm = abs_path.rstrip("\\/").lower()

    # Check drive root (e.g. C:\ or /)
    if len(clean_norm) <= 3 or clean_norm in FORBIDDEN_ZONES:
        return False, f"SECURITY ERROR: Cannot trash drive root or forbidden zone: '{abs_path}'"

    for fz in FORBIDDEN_ZONES:
        if clean_norm == fz or clean_norm.startswith(fz + "\\") or clean_norm.startswith(fz + "/"):
            # If it's directly inside a forbidden system root without workspace isolation
            if fz in ["/etc", "/var", "/usr", "/bin", "/boot", "/sys", "/proc", "c:\\windows", "c:\\program files"]:
                return False, f"SECURITY ERROR: Target is located in forbidden system root: '{abs_path}'"

    return True, "Target path is valid for safe disposal"


def move_to_trash_windows(path: str) -> bool:
    is_valid, msg = validate_safe_disposal_target(path)
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

def move_to_trash_linux(path: str) -> bool:
    is_valid, msg = validate_safe_disposal_target(path)
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

def safe_trash(path: str) -> bool:
    if os.name == "nt":
        return move_to_trash_windows(path)
    else:
        return move_to_trash_linux(path)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python safe_trash.py <file_or_directory_path>")
        sys.exit(1)

    target = sys.argv[1]
    success = safe_trash(target)
    sys.exit(0 if success else 1)
