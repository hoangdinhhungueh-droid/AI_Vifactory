#!/usr/bin/env python3
# scripts/groq_toolcap_probe.py
# Tim NGUONG: groq qwen-32b chiu duoc bao nhieu tool truoc khi 413 (TPM free 6K) + co tool-call dung khong.
import os, time, json
import urllib.request, urllib.error

KEY   = os.getenv("GROQ_API_KEY", "")
MODEL = os.getenv("GROQ_MODEL", "qwen/qwen3-32b")
BASE  = "https://api.groq.com/openai/v1"
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
SWEEP = [int(x) for x in os.getenv("SWEEP", "3,5,8,12,16,20").split(",")]

def _tool(name, desc, props, required):
    return {"type": "function", "function": {"name": name, "description": desc,
            "parameters": {"type": "object", "properties": props, "required": required}}}

CORE = [
    _tool("run_shell", "Run a shell command on the VPS and return stdout.", {"command": {"type": "string"}}, ["command"]),
    _tool("notion_search", "Search the Notion workspace for pages.", {"query": {"type": "string"}}, ["query"]),
]
def make_tools(n):
    tools = list(CORE)
    while len(tools) < n:
        i = len(tools)
        tools.append(_tool("tool_%d" % i, "Auxiliary tool number %d for the agent." % i,
                     {"arg": {"type": "string", "description": "input for tool %d" % i}}, []))
    return tools[:n]

PROMPT = "Kiem tra deploy: chay lenh 'pm2 status' tren VPS giup toi."

def probe(n):
    tools = make_tools(n)
    payload = {"model": MODEL, "messages": [{"role": "user", "content": PROMPT}],
               "tools": tools, "tool_choice": "auto", "temperature": 0.3, "max_tokens": 300, "stream": False}
    data = json.dumps(payload).encode()
    headers = {"Authorization": "Bearer " + KEY, "User-Agent": UA, "Content-Type": "application/json"}
    req = urllib.request.Request(BASE + "/chat/completions", data=data, headers=headers, method="POST")
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            body = r.read().decode(); dt = time.time() - t0
        j = json.loads(body)
        calls = ((j.get("choices") or [{}])[0].get("message") or {}).get("tool_calls") or []
        fn = (calls[0].get("function") or {}).get("name", "") if calls else ""
        return "OK %.2fs tool=%s" % (dt, fn or "NONE")
    except urllib.error.HTTPError as e:
        return "HTTP %d %s" % (e.code, e.read()[:90].decode(errors="ignore").replace(chr(10), " "))
    except Exception as e:
        return type(e).__name__ + ": " + str(e)[:80]

def main():
    if not KEY:
        print("[FATAL] missing GROQ_API_KEY"); return
    print("== GROQ TOOL-CAP PROBE == model=" + MODEL + "\n")
    for n in SWEEP:
        est = len(json.dumps(make_tools(n))) // 4
        print("tools=%-3d (~%5d tok tools) -> %s" % (n, est, probe(n)))
        time.sleep(2)

if __name__ == "__main__":
    main()
