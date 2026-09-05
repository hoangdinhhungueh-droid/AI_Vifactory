from mcp.server.fastmcp import FastMCP
import subprocess, os, json

mcp = FastMCP("VPS Video Factory Agent")

@mcp.tool()
def run_command(cmd: str, workdir: str = "/root/video_factory") -> str:
    """Chay shell command tren VPS."""
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=120, cwd=workdir)
    output = result.stdout + result.stderr
    return output[:8000] if len(output) > 8000 else output

@mcp.tool()
def read_file(path: str, tail_lines: int = 0) -> str:
    """Doc file. tail_lines > 0 thi chi doc N dong cuoi."""
    with open(path, "r", errors="replace") as f:
        if tail_lines > 0:
            lines = f.readlines()
            return "".join(lines[-tail_lines:])
        return f.read()[:10000]

@mcp.tool()
def write_file(path: str, content: str) -> str:
    """Ghi/tao file."""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w") as f:
        f.write(content)
    return f"OK: da ghi {len(content)} chars vao {path}"

@mcp.tool()
def append_file(path: str, content: str) -> str:
    """Append noi dung vao cuoi file."""
    with open(path, "a") as f:
        f.write(content)
    return f"OK: appended {len(content)} chars vao {path}"

@mcp.tool()
def list_files(directory: str = "/root/video_factory") -> str:
    """Liet ke files/folders."""
    result = subprocess.run(f"find {directory} -maxdepth 3 -ls 2>/dev/null | head -80", shell=True, capture_output=True, text=True)
    return result.stdout

@mcp.tool()
def check_services() -> str:
    """Kiem tra trang thai cac service chinh."""
    services = ["n8n", "postgresql", "aibot"]
    results = {}
    for svc in services:
        r = subprocess.run(f"systemctl is-active {svc} 2>/dev/null || echo unknown", shell=True, capture_output=True, text=True)
        results[svc] = r.stdout.strip()
    return json.dumps(results, indent=2)

if __name__ == "__main__":
    import uvicorn
    app = mcp.streamable_http_app()
    uvicorn.run(app, host="0.0.0.0", port=8765)
