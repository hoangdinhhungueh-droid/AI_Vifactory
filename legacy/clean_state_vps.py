import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from vps_runner import get_client

remote_script = """
import json

path = '/root/live_trade/quantflow_live_trade_state.json'
with open(path, 'r') as f:
    s = json.load(f)

changed = False
for stream in ['LINK_15M', 'XRP_15M']:
    if stream in s.get('streams', {}):
        pos = s['streams'][stream].get('position')
        if pos and pos.get('state') == 'REJECTED_TIGHT_SL':
            s['streams'][stream]['position'] = None
            changed = True
            print(f'Cleared rejected position from {stream}')

if changed:
    with open(path, 'w') as f:
        json.dump(s, f, indent=2)
    print('State file updated successfully.')
else:
    print('No changes needed.')
"""

def main():
    client = get_client()
    try:
        import base64
        b64_script = base64.b64encode(remote_script.encode('utf-8')).decode('ascii')
        cmd = f"echo '{b64_script}' | base64 -d > /tmp/clean_state.py && python3 /tmp/clean_state.py"
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
