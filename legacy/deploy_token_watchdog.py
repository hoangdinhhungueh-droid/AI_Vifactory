import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from vps_runner import get_client

remote_script = """
import os
import re
import json
from datetime import datetime, timedelta

LOG_PATH = '/root/live_trade/quantflow_live_trade_cron.log'
STATE_PATH = '/root/live_trade/quantflow_live_trade_state.json'
INCIDENT_PATH = '/root/live_trade/data/token_leak_incident.json'

def audit_recent_activity(window_minutes=30):
    if not os.path.exists(LOG_PATH):
        return {"status": "ERROR", "error": "Log file not found"}

    try:
        with open(LOG_PATH, 'r', errors='replace') as f:
            lines = f.readlines()[-400:]
    except Exception as e:
        return {"status": "ERROR", "error": str(e)}

    cutoff = datetime.utcnow() - timedelta(minutes=window_minutes)
    
    anomalies = []
    llm_calls = []
    zero_token_syntheses = []
    runs_completed = 0

    for line in lines:
        m_time = re.search(r'\\[(\\d{4}-\\d{2}-\\d{2} \\d{2}:\\d{2}:\\d{2})\\]', line)
        if m_time:
            try:
                line_dt = datetime.strptime(m_time.group(1), '%Y-%m-%d %H:%M:%S')
                if line_dt < cutoff:
                    continue
            except Exception:
                pass

        if 'run completed successfully' in line:
            runs_completed += 1
        elif '[ZERO-TOKEN SYNTHESIS]' in line:
            zero_token_syntheses.append(line.strip())
        elif 'hard deadline exceeded' in line:
            anomalies.append({"type": "CASCADE_TIMEOUT", "line": line.strip()})
        elif 'Calling Claude Opus' in line or 'Calling GPT-6' in line or 'Calling Sonnet' in line:
            llm_calls.append(line.strip())

    # Check if any LLM call was illegitimate (e.g. from Forecast Oracle)
    for call in llm_calls:
        if 'FORECAST ORACLE' in call:
            anomalies.append({"type": "FORECAST_ORACLE_TOKEN_LEAK", "line": call})

    leak_detected = len(anomalies) > 0 or len(llm_calls) > 4

    result = {
        "timestamp_utc": datetime.utcnow().isoformat(),
        "window_minutes": window_minutes,
        "runs_completed": runs_completed,
        "zero_token_syntheses_count": len(zero_token_syntheses),
        "llm_calls_count": len(llm_calls),
        "llm_calls": llm_calls,
        "anomalies_count": len(anomalies),
        "anomalies": anomalies,
        "leak_detected": leak_detected,
        "status": "ANOMALY_DETECTED" if leak_detected else "ALL_CLEAR_ZERO_LEAK"
    }

    if leak_detected:
        os.makedirs(os.path.dirname(INCIDENT_PATH), exist_ok=True)
        with open(INCIDENT_PATH, 'w') as f:
            json.dump(result, f, indent=2)

    return result

if __name__ == "__main__":
    report = audit_recent_activity(window_minutes=30)
    print(json.dumps(report, indent=2))
"""

def main():
    client = get_client()
    try:
        import base64
        b64_script = base64.b64encode(remote_script.encode('utf-8')).decode('ascii')
        cmd = f"echo '{b64_script}' | base64 -d > /root/live_trade/scripts/token_leak_watchdog.py && python3 /root/live_trade/scripts/token_leak_watchdog.py"
        res = client.run_command(cmd, timeout=30)
        if isinstance(res, dict):
            print(res.get("stdout", ""))
            if res.get("stderr"):
                print("STDERR:", res.get("stderr"))
        else:
            print(res)
    finally:
        client.close()

if __name__ == "__main__":
    main()
