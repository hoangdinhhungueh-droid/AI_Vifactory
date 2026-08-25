import sys, os, base64

if len(sys.argv) < 3:
    print("Usage: python3 receiver.py <target_path> <b64_chunk_or_full>")
    sys.exit(1)

target_path = sys.argv[1]
b64_data = sys.argv[2]
mode = sys.argv[3] if len(sys.argv) > 3 else "write"

os.makedirs(os.path.dirname(target_path), exist_ok=True)
raw_bytes = base64.b64decode(b64_data)

if mode == "append":
    with open(target_path, "ab") as f:
        f.write(raw_bytes)
else:
    with open(target_path, "wb") as f:
        f.write(raw_bytes)

print(f"WROTE {len(raw_bytes)} bytes to {target_path} (mode={mode})")
