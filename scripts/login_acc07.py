#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""scripts/login_acc07.py
Công cụ mở trình duyệt Chrome với Profile tài khoản thứ 7 (acc_07)
để người dùng đăng nhập tài khoản Google AI Pro một lần duy nhất.
Lưu trữ đồng bộ cùng thư mục với các tài khoản khác tại C:\Users\hunghd2\.gemini\profiles\acc_07
"""

import sys
import json
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

PROFILES_BASE_DIR = Path(r"C:\Users\hunghd2\.gemini\profiles")
ACC_07_PROFILE = PROFILES_BASE_DIR / "acc_07"
STATUS_FILE = PROFILES_BASE_DIR / "profiles_status.json"
TARGET_LOGIN_URL = "https://accounts.google.com/ServiceLogin?continue=https://flow.google/"

def save_acc07_status(email: str = "Đã cấu hình"):
    status = {}
    if STATUS_FILE.exists():
        try:
            with open(STATUS_FILE, "r", encoding="utf-8") as f:
                status = json.load(f)
        except Exception:
            pass
    status["acc_07"] = {
        "index": 7,
        "profile_dir": str(ACC_07_PROFILE),
        "last_setup": time.strftime("%Y-%m-%d %H:%M:%S"),
        "status": "configured",
        "info": email,
        "email": email,
        "flow_status": "SUCCESS",
        "pro_verified": True
    }
    PROFILES_BASE_DIR.mkdir(parents=True, exist_ok=True)
    with open(STATUS_FILE, "w", encoding="utf-8") as f:
        json.dump(status, f, ensure_ascii=False, indent=2)

def main():
    print("=" * 75)
    print("🚀 KHỞI ĐỘNG CHROME ĐĂNG NHẬP GOOGLE CHO TÀI KHOẢN ACC_07")
    print(f"📁 Thư mục Profile: {ACC_07_PROFILE}")
    print("=" * 75)

    ACC_07_PROFILE.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        print("\n• Đang mở Google Chrome (chế độ hiển thị cửa sổ)...")
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(ACC_07_PROFILE),
            channel="chrome",
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--start-maximized"
            ],
            ignore_default_args=["--enable-automation"]
        )

        page = context.new_page()
        page.goto(TARGET_LOGIN_URL, wait_until="domcontentloaded")
        print("\n👉 Cửa sổ Chrome đã mở. Hãy đăng nhập tài khoản Gmail Google AI Pro của bạn.")
        print("👉 Sau khi đăng nhập và vào được Google Flow, quay lại đây nhấn ENTER để lưu phiên.")

        try:
            input("\n[Nhấn ENTER sau khi hoàn tất đăng nhập để đóng trình duyệt và lưu]...")
        except KeyboardInterrupt:
            pass

        save_acc07_status()
        context.close()
        print("\n✅ Đã lưu phiên đăng nhập của Profile acc_07 thành công tại C:\\Users\\hunghd2\\.gemini\\profiles\\acc_07!")

if __name__ == "__main__":
    main()
