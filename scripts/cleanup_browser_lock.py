import subprocess
import json
import sys

ps_cmd = (
    "Get-CimInstance Win32_Process -Filter \"Name = 'chrome.exe'\" | "
    "Select-Object ProcessId, CommandLine | "
    "ConvertTo-Json -Compress"
)

try:
    res = subprocess.run(
        ["powershell", "-NoProfile", "-Command", ps_cmd],
        capture_output=True, text=True, encoding="utf-8"
    )
    if not res.stdout.strip():
        print("No chrome processes found.")
        sys.exit(0)

    data = json.loads(res.stdout)
    if isinstance(data, dict):
        data = [data]

    pids = []
    for proc in data:
        cmd = proc.get("CommandLine") or ""
        if any(term in cmd for term in ["browser_profile", "profiles\\acc_"]):
            pids.append(proc["ProcessId"])

    if not pids:
        print("No lingering automated Chrome processes found.")
    else:
        for pid in pids:
            print(f"Terminating lingering Chrome PID {pid}...")
            subprocess.run(["taskkill", "/F", "/PID", str(pid)], capture_output=True)
        print("Cleaned up lingering automated Chrome processes.")
except Exception as e:
    print(f"Error checking processes: {e}")
