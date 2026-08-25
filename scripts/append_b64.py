import sys
path = sys.argv[1]
data = sys.argv[2]
mode = sys.argv[3] if len(sys.argv) > 3 else "a"
with open(path, mode, encoding="utf-8") as f:
    f.write(data)
