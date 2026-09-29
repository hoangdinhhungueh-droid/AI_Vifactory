#!/usr/bin/env python3
"""
scripts/orchestrator/hhtech_planner.py — Master Architecture & Planning Engine via Opus 5.5 (HHTech API).

Serves as the Strategic Planning Brain (Phase 0: /plan + /grill-me) for:
  - /vf-pipeline-teamwork (AI Video Factory Orchestrator)
  - /sdlc-enterprise-reporter (Enterprise Delivery Engine)

Key Capabilities:
  1. Primary Model: claude-opus-5-5 via HHTech API (https://hhtechapi.com/v1)
  2. Multi-tier Fallback: claude-sonnet-5 -> claude-3-5-sonnet-20241022
  3. Hybrid Execution: Direct API call if key available locally/VPS, or auto-route via VPS runner from Windows
  4. 4 Mandatory Technical Pillars Enforced:
     - CI/CD Quality Gates
     - Git Conventional Commits
     - Three-Way Physical Parity & Sync Verification
     - Real Playwright Visual & Interaction Audit
  5. Handoff: Generates structured Implementation Plan Artifact for Antigravity active model execution
"""

import os
import sys
import json
import argparse
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] [%(levelname)s] [PLANNER] %(message)s")
logger = logging.getLogger("hhtech_planner")

DEFAULT_HHTECH_URL = os.getenv("HHTECH_BASE_URL", "https://hhtechapi.com/v1")
DEFAULT_PLANNER_MODEL = os.getenv("HHTECH_PLANNER_MODEL", "claude-opus-5-5")
FALLBACK_MODELS = ["claude-sonnet-5", "claude-3-5-sonnet-20241022"]

FOUR_PILLARS_PROMPT = """
You are the Principal Solution Architect & Master Strategic Planner.
Your mission is to produce an authoritative, forensic, and actionable IMPLEMENTATION PLAN for the user's task.
You MUST rigorously structure and enforce the following FOUR MANDATORY TECHNICAL PILLARS:

1. CI/CD QUALITY GATES:
   - Identify every automated test gate (Unit, ISO Neighbor-testing, Master Smoke Gate, Lint, OCR defect gate, GitHub Actions CI).
   - Define exact entry/exit criteria for each gate (zero-tolerance for regressions).

2. GIT CONVENTIONAL COMMITS:
   - Enforce Conventional Commits specification (feat, fix, refactor, ci, test, docs, chore).
   - Require atomic commits on agreement with verification evidence (test outputs, diff stats) in commit messages.
   - Maintain strict working tree cleanliness (git status clean).

3. THREE-WAY PHYSICAL PARITY & SYNC VERIFICATION:
   - Ensure complete bit-for-bit physical parity: VPS (/root/video_factory) <-> GitHub (main) <-> Local Workspace.
   - Enforce Rule 126 & Rule 127: Python AST compile (py_compile) AND live runtime test execution (exit code 0) before sync.
   - Monitor GitHub Actions CI watcher until conclusion: success.

4. REAL PLAYWRIGHT VISUAL & INTERACTION AUDIT:
   - Mandate real browser execution (Chromium headless/headful, actual viewport rendering at Desktop 1920x1080, Tablet 768x1024, Mobile 375x812).
   - Capture real screenshots, trap JavaScript console errors/unhandled rejections, and verify responsive layout.
   - ZERO synthetic mock screenshots or dummy visual data.

Deliver the plan with:
- Executive Summary & Problem Framing
- Open Questions / Trade-offs for Grill-Me Protocol (interactive decision points)
- Component-by-Component Proposed Changes with diff specifications
- Step-by-step Execution Roadmap for the Antigravity Default Active Model
- Comprehensive Verification Protocol across all 4 Pillars
"""

def resolve_api_key() -> str:
    """Finds HHTech API key from environment, VPS secrets, or config."""
    key = os.getenv("HHTECH_API_KEY", "")
    if key and not key.startswith("••"):
        return key

    # VPS secrets location
    secrets_path = Path("/root/secrets/.env")
    if secrets_path.exists():
        try:
            with open(secrets_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("HHTECH_API_KEY="):
                        val = line.split("=", 1)[1].strip().strip('"').strip("'")
                        if val:
                            os.environ["HHTECH_API_KEY"] = val
                            return val
        except Exception as e:
            logger.debug(f"Could not read VPS secrets: {e}")

    return ""

def call_opus55_direct(
    prompt: str,
    system_prompt: Optional[str] = None,
    model: str = DEFAULT_PLANNER_MODEL,
    max_tokens: int = 750,
    temperature: float = 0.3,
    timeout: float = 60.0,
    api_key: Optional[str] = None,
    base_url: str = DEFAULT_HHTECH_URL,
) -> str:
    """Performs call to HHTech API for Opus 5.5, preferring model_gateway with streaming."""
    sys_content = (system_prompt or "") + "\n" + FOUR_PILLARS_PROMPT

    # 1. Try centralized Model Gateway if in workspace (has streaming & prompt caching)
    try:
        from app.services.model_gateway import get_global_gateway
        gw = get_global_gateway()
        if gw.hhtech_key:
            logger.info(f"Routing call through ModelGateway: model='{model}'...")
            return gw.call_llm(
                prompt=prompt,
                model=model,
                system_prompt=sys_content.strip(),
                max_tokens=max_tokens,
                temperature=temperature,
                timeout=timeout,
                fallback="claude-sonnet-5"
            )
    except Exception as e:
        logger.debug(f"ModelGateway bypass/fallback: {e}")

    # 2. Direct HTTP call fallback
    key = api_key or resolve_api_key()
    if not key:
        raise ValueError("HHTECH_API_KEY not found in environment or secrets file.")

    url = f"{base_url.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "User-Agent": "Antigravity-Planner/2.0",
    }
    if "claude" in model.lower():
        headers["anthropic-beta"] = "prompt-caching-2024-07-31"

    messages = [
        {"role": "system", "content": sys_content.strip()},
        {"role": "user", "content": prompt}
    ]

    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "stream": True,
    }

    try:
        import httpx
        with httpx.Client(timeout=httpx.Timeout(timeout=timeout, connect=30.0, read=timeout, write=30.0)) as client:
            with client.stream("POST", url, json=payload, headers=headers) as resp:
                if resp.status_code != 200:
                    err_body = resp.read().decode("utf-8", errors="replace")
                    raise RuntimeError(f"HHTech API error HTTP {resp.status_code}: {err_body}")
                full_chunks = []
                for line in resp.iter_lines():
                    line = line.strip()
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str == "[DONE]":
                            break
                        try:
                            d = json.loads(data_str)
                            chunk = d.get("choices", [{}])[0].get("delta", {}).get("content", "")
                            if chunk:
                                full_chunks.append(chunk)
                        except Exception:
                            pass
                return "".join(full_chunks).strip()
    except ImportError:
        pass

    import urllib.request
    import urllib.error
    payload["stream"] = False
    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")

    logger.info(f"Calling HHTech API (urllib) model='{model}' at {url}...")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            if response.status != 200:
                body = response.read().decode("utf-8", errors="replace")
                raise RuntimeError(f"HHTech API error HTTP {response.status}: {body}")
            raw = response.read().decode("utf-8")
            data = json.loads(raw)
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            return content.strip()
    except urllib.error.HTTPError as e:
        err_msg = e.read().decode("utf-8", errors="replace")
        logger.warning(f"Direct call to {model} failed (HTTP {e.code}): {err_msg}")
        raise RuntimeError(f"HTTPError {e.code}: {err_msg}")
    except Exception as e:
        logger.warning(f"Direct call to {model} failed: {e}")
        raise

def call_opus55_with_fallbacks(
    prompt: str,
    system_prompt: Optional[str] = None,
    primary_model: str = DEFAULT_PLANNER_MODEL,
    max_tokens: int = 750,
) -> str:
    """Tries primary Opus 5.5, then cascades down fallback models."""
    models_to_try = [primary_model] + [m for m in FALLBACK_MODELS if m != primary_model]
    last_error = None

    for model_name in models_to_try:
        try:
            logger.info(f"Attempting planning generation via model: {model_name}")
            return call_opus55_direct(
                prompt=prompt,
                system_prompt=system_prompt,
                model=model_name,
                max_tokens=max_tokens,
            )
        except Exception as e:
            last_error = e
            logger.warning(f"Model {model_name} failed: {e}. Trying next fallback...")

    raise RuntimeError(f"All planner models failed. Last error: {last_error}")

def call_via_vps_runner(prompt: str, task_id: Optional[str] = None) -> str:
    """Routes planning request through VPS runner if running locally without local API key."""
    from scripts.vps_runner import FastVPSClient
    client = FastVPSClient()
    escaped_prompt = json.dumps(prompt)
    cmd = (
        f"PYTHONPATH=/root/video_factory python3 -c \""
        f"from scripts.orchestrator.hhtech_planner import generate_plan; "
        f"p = generate_plan({escaped_prompt}, task_id='{task_id or ''}'); "
        f"print(json.dumps({{'plan': p}}))\""
    )
    logger.info("Routing planning request through VPS runner to use secure VPS credentials...")
    res = client.run_command(cmd)
    client.close()

    if res.get("status") == "ok" and res.get("stdout"):
        try:
            parsed = json.loads(res["stdout"])
            return parsed.get("plan", res["stdout"])
        except Exception:
            return res["stdout"]
    raise RuntimeError(f"VPS runner planning failed: {res.get('stderr') or res.get('error')}")

def generate_plan(
    task_description: str,
    task_id: Optional[str] = None,
    market: str = "EN",
    additional_context: Optional[str] = None,
    dry_run: bool = False,
) -> str:
    """High-level function to generate an architectural plan using Opus 5.5."""
    if dry_run:
        return (
            f"# [DRY-RUN] ARCHITECTURAL IMPLEMENTATION PLAN\n\n"
            f"**Task ID**: {task_id or 'GENERAL_TASK'}\n"
            f"**Market**: {market}\n"
            f"**Planner Model**: {DEFAULT_PLANNER_MODEL} (via HHTech API)\n\n"
            f"## 1. CI/CD Quality Gates\n- Configured ISO Neighbor testing and smoke gates.\n\n"
            f"## 2. Git Conventional Commits\n- Enforced atomic commits with verification proof.\n\n"
            f"## 3. Three-Way Physical Parity\n- Bit-for-bit sync between VPS, GitHub, and Local.\n\n"
            f"## 4. Real Playwright Visual Audit\n- Responsive rendering tests on Chromium (Desktop/Tablet/Mobile).\n\n"
            f"*(Generated in dry-run mode)*"
        )

    # Check if local or VPS has key
    key = resolve_api_key()
    if not key and sys.platform == "win32":
        try:
            return call_via_vps_runner(task_description, task_id=task_id)
        except Exception as e:
            logger.warning(f"VPS runner route failed ({e}), attempting direct call with fallback...")

    # Direct call with fallbacks
    user_prompt = f"Task Description:\n{task_description}\n"
    if task_id:
        user_prompt += f"\nTarget Task ID / Episode: {task_id}"
    if market:
        user_prompt += f"\nTarget Market: {market}"
    if additional_context:
        user_prompt += f"\nAdditional Context:\n{additional_context}"

    return call_opus55_with_fallbacks(prompt=user_prompt)

def main():
    parser = argparse.ArgumentParser(description="HHTech Opus 5.5 Architectural Planner for Antigravity")
    parser.add_argument("--task", required=True, help="Task description or requirement summary")
    parser.add_argument("--task-id", default=None, help="Optional Task ID (e.g. EN_EP0260_macro_liquidity)")
    parser.add_argument("--market", default="EN", help="Market identifier (default EN)")
    parser.add_argument("--model", default=DEFAULT_PLANNER_MODEL, help=f"Planner model (default: {DEFAULT_PLANNER_MODEL})")
    parser.add_argument("--output", default=None, help="Optional output file path to write Markdown plan")
    parser.add_argument("--dry-run", action="store_true", help="Validate logic without external API call")

    args = parser.parse_args()

    try:
        plan_content = generate_plan(
            task_description=args.task,
            task_id=args.task_id,
            market=args.market,
            dry_run=args.dry_run,
        )

        if args.output:
            out_path = Path(args.output)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(plan_content)
            logger.info(f"Plan written successfully to: {out_path}")
        else:
            print("\n" + plan_content + "\n")

    except Exception as e:
        logger.error(f"Planning failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
