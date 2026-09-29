#!/usr/bin/env python3
"""
Safe Trash Utility (Windows & Linux)
Moves files or directories to the system Recycle Bin / Trash instead of permanent deletion.
Prevents unrecoverable data loss.
"""

import sys
import os
import subprocess

def move_to_trash_windows(path: str) -> bool:
    abs_path = os.path.abspath(path)
    if not os.path.exists(abs_path):
        print(f"Error: Path does not exist: {abs_path}")
        return False
        
    if len(abs_path.rstrip("\\/")) <= 3:
        print(f"SECURITY ERROR: Cannot trash a drive root: {abs_path}")
        return False

    is_dir = os.path.isdir(abs_path)
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
    abs_path = os.path.abspath(path)
    if not os.path.exists(abs_path):
        print(f"Error: Path does not exist: {abs_path}")
        return False
        
    if abs_path in ["/", "/root", "/home", "/etc", "/var", "/usr"]:
        print(f"SECURITY ERROR: Cannot trash system directory: {abs_path}")
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
