#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""scripts/login_acc07.py
Công cụ mở trình duyệt Chrome với Profile tài khoản thứ 7 (acc_07)
để người dùng đăng nhập tài khoản Google AI Pro một lần duy nhất.
"""

import sys
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

ACC_07_PROFILE = Path(r"C:\Users\hunghd2\AppData\Local\Google\Chrome\User Data\Profile 7")
FLOW_URL = "https://labs.google/fx/tools/video-fx"  # Google Flow / VideoFX URL

def main():
    print("=" * 70)
    print("🚀 KHỞI ĐỘNG CHROME ĐĂNG NHẬP GOOGLE CHO TÀI KHOẢN ACC_07")
    print(f"📁 Thư mục Profile: {ACC_07_PROFILE}")
    print("=" * 70)

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
        page.goto("https://accounts.google.com/", wait_until="domcontentloaded")
        print("\n👉 Trình duyệt đã mở. Hãy đăng nhập tài khoản Gmail của bạn trên cửa sổ Chrome.")
        print("👉 Sau khi đăng nhập xong, bạn có thể truy cập Google Flow để kiểm tra.")
        print("\n⚠️ Nhấn Enter tại đây hoặc đóng cửa sổ trình duyệt khi bạn đã đăng nhập thành công.")

        try:
            input("\n[Nhấn ENTER sau khi hoàn tất đăng nhập để đóng trình duyệt]...")
        except KeyboardInterrupt:
            pass

        context.close()
        print("\n✅ Đã lưu phiên đăng nhập của Profile 7 thành công!")

if __name__ == "__main__":
    main()
