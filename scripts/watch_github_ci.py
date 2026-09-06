#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GitHub Actions CI Watcher for AI Video Factory (Rule 126 Compliance).
Monitors GitHub Actions workflow runs after git push to verify CI passing status.
"""

import sys
import os
import time
import json
import argparse
import subprocess
import urllib.request
import urllib.error

try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

DEFAULT_REPO = "hoangdinhhungueh-droid/AI_Vifactory"
DEFAULT_TOKEN = "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"


class NoAuthRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        new_req = super().redirect_request(req, fp, code, msg, headers, newurl)
        if new_req and "github.com" not in newurl:
            if "Authorization" in new_req.headers:
                del new_req.headers["Authorization"]
            if "authorization" in new_req.headers:
                del new_req.headers["authorization"]
        return new_req


def get_head_sha(repo_dir: str = ".") -> str:
    try:
        res = subprocess.run(
            ["git", "-C", repo_dir, "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True
        )
        return res.stdout.strip()
    except Exception as e:
        print(f"[watch_github_ci] Error getting HEAD SHA: {e}", file=sys.stderr)
        return ""


def get_opener():
    return urllib.request.build_opener(NoAuthRedirect)


def fetch_run_for_commit(repo: str, token: str, commit_sha: str, opener):
    url = f"https://api.github.com/repos/{repo}/actions/runs?head_sha={commit_sha}&per_page=1"
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "Antigravity-CI-Watcher"
    })
    try:
        with opener.open(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
            runs = data.get("workflow_runs", [])
            return runs[0] if runs else None
    except Exception as e:
        print(f"[watch_github_ci] API request failed: {e}", file=sys.stderr)
        return None


def fetch_job_details(repo: str, token: str, run_id: int, opener):
    url = f"https://api.github.com/repos/{repo}/actions/runs/{run_id}/jobs"
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "Antigravity-CI-Watcher"
    })
    try:
        with opener.open(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
            return data.get("jobs", [])
    except Exception as e:
        print(f"[watch_github_ci] Error fetching jobs: {e}", file=sys.stderr)
        return []


def fetch_failed_log(repo: str, token: str, job_id: int, opener) -> str:
    url = f"https://api.github.com/repos/{repo}/actions/jobs/{job_id}/logs"
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {token}",
        "User-Agent": "Antigravity-CI-Watcher"
    })
    try:
        with opener.open(req, timeout=20) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        return f"Error downloading log: {e}"


def watch_ci(repo: str, token: str, commit_sha: str, timeout_sec: int = 600, poll_interval: int = 8) -> int:
    opener = get_opener()
    start_time = time.time()
    print(f"============================================================")
    print(f"🛡️  GITHUB ACTIONS CI WATCHER (Rule 126 Gate)")
    print(f"   Repo:   {repo}")
    print(f"   Commit: {commit_sha}")
    print(f"   Max Wait: {timeout_sec}s")
    print(f"============================================================")

    run_found = None
    waited_for_run = 0

    while time.time() - start_time < timeout_sec:
        run = fetch_run_for_commit(repo, token, commit_sha, opener)
        if run:
            run_found = run
            status = run.get("status")
            conclusion = run.get("conclusion")
            run_id = run.get("id")
            html_url = run.get("html_url")
            elapsed = int(time.time() - start_time)

            print(f"[{elapsed:03d}s] Run ID {run_id} | Status: {status} | Conclusion: {conclusion}")

            if status == "completed":
                print(f"\n🎯 Workflow completed in {elapsed}s with conclusion: {conclusion.upper()}")
                print(f"   Run URL: {html_url}")

                if conclusion == "success":
                    print("✅ GITHUB ACTIONS CI PASSED! (Three-Way Physical Sync Verified)")
                    return 0
                else:
                    print(f"❌ GITHUB ACTIONS CI FAILED ({conclusion})!")
                    # Fetch jobs and pinpoint failure
                    jobs = fetch_job_details(repo, token, run_id, opener)
                    for j in jobs:
                        print(f"   Job '{j['name']}': {j.get('conclusion')}")
                        for s in j.get("steps", []):
                            if s.get("conclusion") == "failure":
                                print(f"     -> Failed Step: {s['name']}")
                        if j.get("conclusion") == "failure":
                            log_text = fetch_failed_log(repo, token, j["id"], opener)
                            lines = log_text.splitlines()
                            err_lines = [l for l in lines if "FAILED" in l or "ERROR" in l or "Error" in l]
                            print("\n--- FAILURE LOG SNIPPET ---")
                            for el in err_lines[:20]:
                                print(" ", el)
                    return 1
        else:
            elapsed = int(time.time() - start_time)
            waited_for_run += poll_interval
            print(f"[{elapsed:03d}s] Waiting for GitHub Actions workflow to trigger on commit {commit_sha[:7]}...")
            if waited_for_run > 60:
                print(f"[watch_github_ci] Warning: No workflow run picked up after {waited_for_run}s.")

        time.sleep(poll_interval)

    print(f"❌ TIMEOUT: CI workflow did not finish within {timeout_sec}s.")
    return 2


def main():
    parser = argparse.ArgumentParser(description="Watch GitHub Actions CI status for a commit.")
    parser.add_argument("--commit", default="", help="Commit SHA to check (default: HEAD)")
    parser.add_argument("--repo", default=DEFAULT_REPO, help=f"GitHub repo (default: {DEFAULT_REPO})")
    parser.add_argument("--token", default=os.getenv("GITHUB_TOKEN", DEFAULT_TOKEN), help="GitHub PAT token")
    parser.add_argument("--timeout", type=int, default=450, help="Timeout in seconds (default: 450)")
    parser.add_argument("--repo-dir", default=".", help="Local repo dir to resolve HEAD SHA")

    args = parser.parse_args()

    commit_sha = args.commit
    if not commit_sha:
        commit_sha = get_head_sha(args.repo_dir)

    if not commit_sha:
        print("Error: Could not determine commit SHA.", file=sys.stderr)
        sys.exit(1)

    code = watch_ci(args.repo, args.token, commit_sha, timeout_sec=args.timeout)
    sys.exit(code)


if __name__ == "__main__":
    main()
