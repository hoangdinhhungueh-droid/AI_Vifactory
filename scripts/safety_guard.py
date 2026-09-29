#!/usr/bin/env python3
"""
Antigravity PreToolUse Safety Guard - Anti-Drive-Wipe Gate
Intercepts 'run_command' invocations before execution.
Vetoes any destructive commands attempting to wipe drive roots, recursively delete system directories,
format drives, or bypass safeguards.
"""

import sys
import json
import re

# Blacklisted dangerous regex patterns
DANGEROUS_PATTERNS = [
    # Drive wipes and root wipes (Linux & Windows)
    (r'\brm\s+(-[a-zA-Z]*f[a-zA-Z]*\s+)?(-[a-zA-Z]*r[a-zA-Z]*\s+)?(\/|[a-zA-Z]:[\\\/]|\~|\$HOME)(\s|$)', "Attempt to remove root filesystem or drive root!"),
    (r'\brmdir\s+\/[sS]\s+\/[qQ]\s+([a-zA-Z]:[\\\/]|\/)', "Attempt to rmdir root drive recursively!"),
    (r'\bRemove-Item\b.*(-Recurse|-r\b).*(-Force|-f\b).*([a-zA-Z]:[\\\/]|\/|\*|\.\.)', "Dangerous recursive Force deletion on drive root, wildcard, or parent!"),
    (r'\bRemove-Item\b.*(-Force|-f\b).*(-Recurse|-r\b).*([a-zA-Z]:[\\\/]|\/|\*|\.\.)', "Dangerous recursive Force deletion on drive root, wildcard, or parent!"),
    (r'\bdel\s+\/[fF]\s+\/[sS]\s+\/[qQ]\s+([a-zA-Z]:[\\\/]|\*)', "Dangerous CMD recursive force delete on drive or wildcard!"),
    # Direct drive root deletion targets
    (r'\b(rm|rmdir|Remove-Item|del)\b.*[a-zA-Z]:[\\\/]?(\s|$|\*)', "Direct deletion targeting drive root (e.g., C: or D:) is forbidden!"),
    (r'\b(rm|Remove-Item)\b.*(\/root|\/home|\/etc|\/var|\/usr|\/bin|\/boot)(\s|$|\*)', "Direct deletion targeting protected Linux system directory is forbidden!"),
    # Formatting and disk partitioning
    (r'\bformat\s+[a-zA-Z]:', "Disk format command detected!"),
    (r'\bFormat-Volume\b', "PowerShell Format-Volume command detected!"),
    (r'\bdiskpart\b', "Diskpart partition utility detected!"),
    (r'\bmkfs(\.[a-zA-Z0-9]+)?\b', "Linux filesystem creation command detected!"),
    (r'\bdd\s+if=.*of=\/dev\/', "Raw disk write with dd detected!"),
    # Dangerous top-level wildcards
    (r'\brm\s+-[a-zA-Z]*r[a-zA-Z]*f?[a-zA-Z]*\s+\/\*', "rm -rf /* wildcard wipe detected!"),
    (r'\brm\s+-[a-zA-Z]*r[a-zA-Z]*f?[a-zA-Z]*\s+\*', "rm -rf * unconstrained wipe detected!"),
    (r'\bRemove-Item\s+\*\s+-Recurse', "Remove-Item * -Recurse wildcard wipe detected!"),
]

def evaluate_command(cmd: str) -> tuple[str, str]:
    if not cmd or not cmd.strip():
        return "allow", ""
    
    cmd_clean = cmd.strip()
    
    for pattern, explanation in DANGEROUS_PATTERNS:
        if re.search(pattern, cmd_clean, re.IGNORECASE):
            return "deny", f"[ANTI-DRIVE-WIPE VETO] {explanation} (Matched pattern: {pattern})"
            
    if re.search(r'\b(Remove-Item|rm|rmdir)\b.*(-Path\s+)?(\"\"|\'\'|\s+)(\s+-Recurse|\s+-r)', cmd_clean, re.IGNORECASE):
        return "deny", "[ANTI-DRIVE-WIPE VETO] Attempt to delete empty or whitespace path recursively!"
        
    return "allow", ""

def main():
    try:
        raw_input = sys.stdin.read()
        if not raw_input:
            print(json.dumps({"decision": "allow"}))
            return
            
        payload = json.loads(raw_input)
        tool_call = payload.get("toolCall", {})
        tool_args = tool_call.get("args", {})
        command_line = tool_args.get("CommandLine", "")
        
        decision, reason = evaluate_command(command_line)
        output = {"decision": decision}
        if reason:
            output["reason"] = reason
            
        print(json.dumps(output))
    except Exception as e:
        sys.stderr.write(f"Safety guard error: {str(e)}\n")
        print(json.dumps({"decision": "allow"}))

if __name__ == "__main__":
    main()
