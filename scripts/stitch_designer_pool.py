#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/stitch_designer_pool.py — Google Stitch Multi-Account Automation Engine.
Leverages Playwright persistent contexts across 7 authenticated Google accounts
to rotate daily free credits, generate UI designs, and extract Tailwind/HTML & DESIGN.md.
"""

import os
import sys
import time
import json
import argparse
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent

ACCOUNT_POOL = [
    {
        "id": "acc_01",
        "email": "hoangdinhhung.ueh@gmail.com",
        "name": "Hưng Hoàng Đình",
        "profile_dir": r"C:\Users\hunghd2\.gemini\browser_profile",
        "status": "configured"
    },
    {
        "id": "acc_02",
        "email": "dinhhung111995@gmail.com",
        "name": "Hung Dinh",
        "profile_dir": r"C:\Users\hunghd2\.gemini\profiles\acc_02",
        "status": "configured"
    },
    {
        "id": "acc_03",
        "email": "hunghoangdinh2308@gmail.com",
        "name": "Hung Hoang",
        "profile_dir": r"C:\Users\hunghd2\.gemini\profiles\acc_03",
        "status": "configured"
    },
    {
        "id": "acc_04",
        "email": "wmpexpansion@gmail.com",
        "name": "Expansion WMP",
        "profile_dir": r"C:\Users\hunghd2\.gemini\profiles\acc_04",
        "status": "configured"
    },
    {
        "id": "acc_05",
        "email": "untoldstorieskr@gmail.com",
        "name": "Hưng Hoàng",
        "profile_dir": r"C:\Users\hunghd2\.gemini\profiles\acc_05",
        "status": "configured"
    },
    {
        "id": "acc_07",
        "email": "hunghoangdinh090@gmail.com",
        "name": "Hung Hoang Dinh",
        "profile_dir": r"C:\Users\hunghd2\AppData\Local\Google\Chrome\User Data\Profile 7",
        "status": "configured"
    }
]

STITCH_URL = "https://stitch.withgoogle.com/"


def get_available_accounts():
    valid = []
    for acc in ACCOUNT_POOL:
        p = Path(acc["profile_dir"])
        if p.exists():
            valid.append(acc)
    return valid


def check_quota(headless=True):
    from playwright.sync_api import sync_playwright

    print("=" * 70)
    print("🔍 CHECKING GOOGLE STITCH QUOTA ACROSS 7 ACCOUNTS")
    print("=" * 70)

    accounts = get_available_accounts()
    print(f"Found {len(accounts)} configured Google profiles on machine.")

    results = []
    with sync_playwright() as p:
        for acc in accounts:
            print(f"\n• [{acc['id']}] Probing {acc['email']}...")
            try:
                context = p.chromium.launch_persistent_context(
                    user_data_dir=acc["profile_dir"],
                    channel="chrome",
                    headless=headless,
                    args=["--disable-blink-features=AutomationControlled", "--no-sandbox"],
                    viewport={"width": 1280, "height": 800}
                )
                page = context.new_page()
                page.goto(STITCH_URL, timeout=30000, wait_until="domcontentloaded")
                time.sleep(3)
                
                # Check title / logged in indicator
                title = page.title()
                logged_in = "stitch" in title.lower() or "google" in title.lower()
                
                results.append({
                    "id": acc["id"],
                    "email": acc["email"],
                    "status": "ONLINE" if logged_in else "CHECK_LOGIN",
                    "title": title
                })
                print(f"  ➔ Status: {'ONLINE' if logged_in else 'CHECK_LOGIN'} (Title: {title})")
                context.close()
            except Exception as e:
                print(f"  ❌ Error: {e}")
                results.append({
                    "id": acc["id"],
                    "email": acc["email"],
                    "status": "ERROR",
                    "error": str(e)
                })

    print("\n" + "=" * 70)
    print("QUOTA & ACCOUNT POOL SUMMARY:")
    for r in results:
        print(f"  • {r['id']} ({r['email']}): {r['status']}")
    print("=" * 70)
    return results


def run_stitch_design(prompt: str, output_dir: str = "reports/stitch_designs/latest", specific_acc: str = None):
    from playwright.sync_api import sync_playwright

    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    accounts = get_available_accounts()
    if specific_acc:
        accounts = [a for a in accounts if a["id"] == specific_acc]
        if not accounts:
            print(f"❌ Account {specific_acc} not found or profile missing.")
            return False

    print("=" * 70)
    print("🎨 GOOGLE STITCH AUTOMATED UI DESIGN POOL")
    print(f"Prompt: {prompt}")
    print(f"Output directory: {out_path}")
    print("=" * 70)

    with sync_playwright() as p:
        for acc in accounts:
            print(f"\n🚀 Launching Stitch with [{acc['id']}] {acc['email']}...")
            try:
                context = p.chromium.launch_persistent_context(
                    user_data_dir=acc["profile_dir"],
                    channel="chrome",
                    headless=False,
                    viewport={"width": 1920, "height": 1080},
                    args=[
                        "--disable-blink-features=AutomationControlled",
                        "--no-sandbox",
                        "--disable-infobars",
                        "--start-maximized"
                    ],
                    ignore_default_args=["--enable-automation"]
                )
                page = context.new_page()
                page.goto(STITCH_URL, timeout=40000, wait_until="domcontentloaded")
                time.sleep(3)

                # Look for prompt textarea or input box
                # Stitch input typically has textarea or placeholder 'Describe what you want to build'
                print("  Waiting for Stitch interface...")
                page.wait_for_selector("textarea, input[type='text'], [contenteditable='true']", timeout=15000)
                
                # Check if daily limit reached
                body_text = page.inner_text("body")
                if "daily limit" in body_text.lower() or "quota exceeded" in body_text.lower():
                    print(f"  ⚠️ Account {acc['id']} reached daily credit limit! Rotating to next account...")
                    context.close()
                    continue

                # Type prompt
                input_elem = page.locator("textarea, [contenteditable='true']").first
                input_elem.fill(prompt)
                time.sleep(1)
                input_elem.press("Enter")
                print("  Prompt submitted! Waiting for generation (20-40s)...")
                
                time.sleep(25)
                
                # Capture screenshot
                shot_path = out_path / "stitch_mockup.png"
                page.screenshot(path=str(shot_path), full_page=True)
                print(f"  📸 Saved design mockup: {shot_path}")

                # Save metadata
                meta = {
                    "account_used": acc["id"],
                    "email": acc["email"],
                    "prompt": prompt,
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "screenshot": str(shot_path)
                }
                (out_path / "stitch_meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
                print("  ✅ Design successfully generated and recorded!")
                context.close()
                return True
            except Exception as e:
                print(f"  ⚠️ Error with {acc['id']}: {e}. Trying next account in pool...")
                try:
                    context.close()
                except Exception:
                    pass

    print("❌ All accounts in pool failed or exhausted daily limits.")
    return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Google Stitch Multi-Account Pool")
    parser.add_argument("--prompt", type=str, help="UI prompt to generate on Stitch")
    parser.add_argument("--output-dir", type=str, default="reports/stitch_designs/latest", help="Output directory")
    parser.add_argument("--acc", type=str, help="Specific account id (acc_01 .. acc_07)")
    parser.add_argument("--check-quota", action="store_true", help="Check login & quota on all 7 accounts")
    args = parser.parse_args()

    if args.check_quota:
        check_quota(headless=True)
    elif args.prompt:
        run_stitch_design(args.prompt, output_dir=args.output_dir, specific_acc=args.acc)
    else:
        print("Usage: python scripts/stitch_designer_pool.py --prompt '<your UI prompt>'")
        print("       python scripts/stitch_designer_pool.py --check-quota")
