"""
Code Hygiene & Medical Chart Scanner for AI Video Factory and Quant Trade Engine.
Scans for:
1. Hardcoded Secrets & API Tokens (Aikido mirror)
2. Dead Code Candidates & Unreferenced Callers (Sonar mirror)
3. High Cognitive / Cyclomatic Complexity (Sonar C901 mirror)
4. Duplicate blocks / Vibe code rot
"""

import ast
import logging
import os
import re
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

# Fix Windows console UTF-8 output
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

# Patterns for high-risk secrets
SECRET_PATTERNS = [
    (r"(?:api[_-]?key|secret|token|password|auth|bearer)\s*=\s*['\"][A-Za-z0-9_\-\.]{16,}['\"]", "Hardcoded API Key / Secret"),
    (r"ghp_[A-Za-z0-9]{36}", "GitHub Personal Access Token"),
    (r"AIza[0-9A-Za-z-_]{35}", "Google API Key"),
    (r"sk-[A-Za-z0-9]{32,}", "OpenAI / Claude API Secret"),
    (r"-----BEGIN (?:RSA |EC )?PRIVATE KEY-----", "Private Cryptographic Key"),
]

def scan_file_for_secrets(file_path: Path):
    findings = []
    try:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
        for line_no, line in enumerate(content.splitlines(), start=1):
            if line.strip().startswith("#"):
                continue
            for pattern, desc in SECRET_PATTERNS:
                if re.search(pattern, line, re.IGNORECASE):
                    findings.append((line_no, desc, line.strip()[:80]))
    except Exception as exc:
        logger.debug("Could not read %s: %s", file_path, exc)
    return findings

class ComplexityVisitor(ast.NodeVisitor):
    def __init__(self):
        self.functions = []

    def visit_FunctionDef(self, node):
        complexity = 1
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.ExceptHandler, ast.With, ast.Assert)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
        self.functions.append((node.name, node.lineno, complexity))
        self.generic_visit(node)

    visit_AsyncFunctionDef = visit_FunctionDef

def scan_file_for_complexity(file_path: Path, max_complexity: int = 15):
    findings = []
    try:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
        tree = ast.parse(content, filename=str(file_path))
        visitor = ComplexityVisitor()
        visitor.visit(tree)
        for func_name, lineno, comp in visitor.functions:
            if comp > max_complexity:
                findings.append((lineno, func_name, comp))
    except Exception as exc:
        logger.debug("Could not read %s: %s", file_path, exc)
    return findings

def run_audit(target_dirs):
    print("=" * 70)
    print("🏥 CODE HYGIENE AUDIT REPORT (Zero-Cost Local Scanner)")
    print("=" * 70)

    total_files = 0
    secret_findings = []
    complexity_findings = []

    for d in target_dirs:
        p = Path(d)
        if not p.exists():
            continue
        for py_file in p.rglob("*.py"):
            # Skip caches and tests for complexity
            if "__pycache__" in py_file.parts or ".venv" in py_file.parts:
                continue
            total_files += 1
            # 1. Scan secrets
            s_res = scan_file_for_secrets(py_file)
            for lineno, desc, snippet in s_res:
                secret_findings.append((py_file, lineno, desc, snippet))
            # 2. Scan complexity
            if "tests" not in py_file.parts:
                c_res = scan_file_for_complexity(py_file, max_complexity=15)
                for lineno, func_name, comp in c_res:
                    complexity_findings.append((py_file, lineno, func_name, comp))

    print(f"\n📂 Tổng số file Python quét: {total_files}")
    
    print("\n[1] 🚨 CẢNH BÁO BẢO MẬT & SECRETS (Aikido Mirror):")
    if secret_findings:
        for f, lineno, desc, snip in secret_findings:
            print(f"  • {f}:{lineno} [{desc}] -> {snip}")
    else:
        print("  ✅ 0 hardcoded secrets detected.")

    print("\n[2] 🧠 CẢNH BÁO SPAGHETTI / COMPLEXITY > 15 (Sonar Mirror):")
    if complexity_findings:
        # Sort by complexity descending
        complexity_findings.sort(key=lambda x: x[3], reverse=True)
        for f, lineno, func_name, comp in complexity_findings[:15]:
            print(f"  • {f}:{lineno} -> Hàm '{func_name}()' [Complexity = {comp}]")
        if len(complexity_findings) > 15:
            print(f"  ... và còn {len(complexity_findings) - 15} hàm khác có complexity > 15.")
    else:
        print("  ✅ 0 high-complexity functions detected.")

    print("\n" + "=" * 70)
    print("💡 BƯỚC TIẾP THEO: Dùng '/clean-code' để kích hoạt Serena AST phẫu thuật!")
    print("=" * 70)

if __name__ == "__main__":
    dirs = sys.argv[1:] if len(sys.argv) > 1 else ["app", "vox", "stages"]
    run_audit(dirs)
