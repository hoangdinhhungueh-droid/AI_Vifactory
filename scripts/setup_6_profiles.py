#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""scripts/setup_6_profiles.py
Quản lý và khởi tạo 6 Profile Chrome độc lập cho 6 tài khoản Google AI Pro (Google Flow / Veo).
- Mỗi tài khoản lưu trong một thư mục User Data riêng biệt tại C:\\Users\\hunghd2\\.gemini\\profiles\\acc_XX
- Mở cửa sổ Chrome thật (có giao diện) và CHỜ BẠN ĐĂNG NHẬP, XÁC MINH 2 BƯỚC ĐẦY ĐỦ.
- Chỉ đóng trình duyệt và lưu phiên khi bạn nhấn ENTER xác nhận đã xong!
"""

import os
import sys
import json
import time
import re
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

from playwright.sync_api import sync_playwright

PROFILES_BASE_DIR = Path(r"C:\Users\hunghd2\.gemini\profiles")
STATUS_FILE = PROFILES_BASE_DIR / "profiles_status.json"
IMAGE_PROFILE_DIR = Path(r"C:\Users\hunghd2\.gemini\browser_profile")
IMAGE_ACCOUNT_EMAIL = "hoangdinhhung.ueh@gmail.com"
TARGET_LOGIN_URL = "https://accounts.google.com/ServiceLogin?continue=https://flow.google/"
ADD_ACCOUNT_URL = "https://accounts.google.com/AddSession?continue=https://flow.google/"


def load_status() -> dict:
    status = {}
    if STATUS_FILE.exists():
        try:
            with open(STATUS_FILE, "r", encoding="utf-8") as f:
                status = json.load(f)
        except Exception:
            pass

    status["acc_01"] = {
        "index": 1,
        "profile_dir": str(IMAGE_PROFILE_DIR),
        "email": IMAGE_ACCOUNT_EMAIL,
        "last_setup": status.get("acc_01", {}).get("last_setup", time.strftime("%Y-%m-%d %H:%M:%S")),
        "status": "configured",
        "info": f"{IMAGE_ACCOUNT_EMAIL} (Dùng chung profile sinh ảnh có sẵn)"
    }
    save_status(status)
    return status


def save_status(status_data: dict):
    PROFILES_BASE_DIR.mkdir(parents=True, exist_ok=True)
    with open(STATUS_FILE, "w", encoding="utf-8") as f:
        json.dump(status_data, f, ensure_ascii=False, indent=2)


def check_account_logged_in(page) -> tuple[bool, str]:
    """Kiểm tra xem trang hiện tại đã đăng nhập Google thành công chưa."""
    try:
        url = page.url
        if "accounts.google.com/v3/signin" in url or "accounts.google.com/signin" in url:
            return False, "Đang ở trang đăng nhập"

        avatar = page.query_selector('a[aria-label*="Google Account"], img[alt*="Google Account"], [data-test-id="user-avatar"]')
        if avatar or ("flow.google" in url):
            email_el = page.query_selector('[data-email], [aria-label*="@"]')
            email = "Đã đăng nhập"
            if email_el:
                raw_email = email_el.get_attribute("data-email") or email_el.get_attribute("aria-label") or ""
                match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", raw_email)
                if match:
                    email = match.group(0)
                elif raw_email:
                    email = raw_email
            return True, email
        return False, "Chưa xác định"
    except Exception as e:
        return False, str(e)


def wait_for_user_confirmation(acc_key: str, acc_index: int) -> str:
    """Chờ người dùng hoàn tất đăng nhập thông qua hộp thoại Windows hoặc Console.
    Trả về: 'save' (đã đăng nhập), 'skip' (bỏ qua slot này), 'cancel' (dừng toàn bộ).
    """
    print("\n⏳ TRÌNH DUYỆT ĐANG MỞ VÀ CHỜ BẠN THAO TÁC TRÊN MÀN HÌNH...")
    print(f"👉 Hãy đăng nhập tài khoản Google AI Pro cho [{acc_key.upper()}] và hoàn tất xác minh 2 bước.")
    print("👉 Trình duyệt sẽ GIỮ NGUYÊN trạng thái mở, không bao giờ tự đóng.")
    print("👉 Khi hoàn tất, chọn phản hồi trên hộp thoại thông báo:\n"
          "   • [YES]    : Đã đăng nhập xong -> Lưu phiên an toàn.\n"
          "   • [NO]     : Bỏ qua slot này (nếu bạn không dùng đến).\n"
          "   • [CANCEL] : Dừng toàn bộ quá trình thiết lập.\n")

    try:
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        res = messagebox.askyesnocancel(
            title=f"AI Video Factory - Cấu hình {acc_key.upper()}",
            message=f"Đang mở trình duyệt cho Slot Video {acc_index} ({acc_key.upper()}).\n\n"
                    f"1. Vui lòng đăng nhập tài khoản Google AI Pro mới cho Video.\n"
                    f"2. Hoàn tất xác minh 2 bước (SMS / Authenticator / Prompt).\n"
                    f"3. Sau khi vào được Google Flow thành công:\n\n"
                    f"   • Chọn [YES] để lưu phiên đăng nhập.\n"
                    f"   • Chọn [NO] để bỏ qua slot này.\n"
                    f"   • Chọn [CANCEL] để dừng thiết lập.\n\n"
                    f"(Trình duyệt sẽ KHÔNG tự động đóng cho đến khi bạn bấm)."
        )
        root.destroy()
        if res is True:
            return "save"
        elif res is False:
            return "skip"
        else:
            return "cancel"
    except Exception:
        pass

    try:
        ans = input(f"\n👉 [Nhấn ENTER để lưu {acc_key.upper()} / Gõ 's' để bỏ qua / Gõ 'q' để thoát]: ").strip().lower()
        if ans == "s":
            return "skip"
        if ans == "q":
            return "cancel"
        return "save"
    except (KeyboardInterrupt, EOFError):
        return "cancel"


def login_single_profile(acc_index: int) -> str:
    """Mở 1 Profile Chrome cụ thể để người dùng đăng nhập và chờ người dùng xác nhận.
    Trả về 'save', 'skip', hoặc 'cancel'.
    """
    acc_key = f"acc_{acc_index:02d}"
    profile_dir = PROFILES_BASE_DIR / acc_key
    profile_dir.mkdir(parents=True, exist_ok=True)

    print("\n" + "=" * 75)
    print(f"🚀 KHỞI CHẠY GOOGLE CHROME THẬT CHO: TÀI KHOẢN [{acc_key.upper()}]")
    print(f"📁 Thư mục lưu trữ phiên: {profile_dir}")
    print("=" * 75)
    print("📋 HƯỚNG DẪN DÀNH CHO BẠN:")
    print("  1. Cửa sổ Google Chrome thật sẽ mở ra trên màn hình.")
    print(f"  2. Hãy đăng nhập tài khoản Google AI Pro số {acc_index} của bạn.")
    print("  3. Hoàn tất xác minh 2 bước (SMS / Authenticator / Prompt điện thoại).")
    print("  4. Trình duyệt SẼ KHÔNG TỰ ĐỘNG ĐÓNG. Bạn có toàn bộ thời gian bạn cần!")
    print("  5. Sau khi đăng nhập thành công và thấy giao diện Google Flow,")
    print("     chọn YES trên hộp thoại thông báo để lưu phiên vĩnh viễn!")
    print("-" * 75)

    with sync_playwright() as p:
        browser = p.chromium.launch_persistent_context(
            user_data_dir=str(profile_dir),
            channel="chrome",
            headless=False,
            args=[
                "--start-maximized",
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox"
            ],
            no_viewport=True
        )

        page = browser.pages[0] if browser.pages else browser.new_page()
        # Open Google Login / AddSession so user can directly login with new account
        target_url = TARGET_LOGIN_URL
        print(f"🌐 Đang điều hướng đến: {target_url}")
        try:
            page.goto(target_url, wait_until="domcontentloaded", timeout=60000)
        except Exception:
            pass

        action = wait_for_user_confirmation(acc_key, acc_index)

        if action == "save":
            time.sleep(2)
            is_logged, info = check_account_logged_in(page)
            status = load_status()
            
            detected_email = info if ("@" in info) else ""
            acc_entry = {
                "index": acc_index,
                "profile_dir": str(profile_dir),
                "last_setup": time.strftime("%Y-%m-%d %H:%M:%S"),
                "status": "configured" if is_logged else "configured_pending_check",
                "info": info
            }
            if detected_email:
                acc_entry["email"] = detected_email
            
            if acc_key in status:
                for k in ["name", "flow_status", "pro_verified", "settings_saved", "generation_triggered"]:
                    if k in status[acc_key]:
                        acc_entry[k] = status[acc_key][k]
                if detected_email:
                    acc_entry["email"] = detected_email
            
            status[acc_key] = acc_entry
            save_status(status)

            print(f"\n✅ ĐÃ LƯU THÀNH CÔNG PHIÊN ĐĂNG NHẬP CHO [{acc_key.upper()}]!")
            print(f"💾 Cookie và chứng thực đã được đóng gói an toàn tại: {profile_dir}")
            if detected_email:
                print(f"📧 Tài khoản nhận diện: {detected_email}")
        elif action == "skip":
            print(f"\n⏭️ ĐÃ BỎ QUA [{acc_key.upper()}].")
        else:
            print(f"\n🛑 ĐÃ DỪNG THIẾT LẬP TẠI [{acc_key.upper()}].")

        browser.close()
        time.sleep(1)
        return action


def show_all_status():
    """Hiển thị trạng thái hiện tại của các tài khoản Google AI Pro."""
    status = load_status()
    print("\n" + "=" * 75)
    print("📌 [XÁC THỰC BỘ TÀI KHOẢN GOOGLE AI PRO CHO PIPELINE]:")
    print("  🎨 TÀI KHOẢN SINH ẢNH & SLOT VIDEO 01 (ĐÃ SẴN SÀNG):")
    print(f"     -> Email: {IMAGE_ACCOUNT_EMAIL} (Thư mục: .gemini/browser_profile)")
    print("     -> Slot Video 1 (acc_01): ĐÃ TỰ ĐỘNG LIÊN KẾT XONG, KHÔNG CẦN ĐĂNG NHẬP LẠI!")
    print("-" * 75)
    print("  🎬 CÁC TÀI KHOẢN PHỤ CẦN THIẾT LẬP (SLOT 02 -> 07):")
    for i in range(2, 8):
        key = f"acc_{i:02d}"
        dir_path = PROFILES_BASE_DIR / key
        exists = dir_path.exists()
        acc_info = status.get(key, {})
        cfg = "Đã tạo thư mục" if exists else acc_info.get("status", "Chưa cấu hình")
        last_t = acc_info.get("last_setup", "Chưa có")
        detail = acc_info.get("email", acc_info.get("info", ""))
        detail_str = f" [{detail}]" if detail else ""
        print(f"     • Slot Video {i} ({key}): {cfg}{detail_str} (Cập nhật: {last_t})")
    print("=" * 75)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Thiết lập các Profile Google AI Pro cho Video Flow")
    parser.add_argument("--slot", type=int, choices=range(1, 8), help="Chỉ định slot tài khoản cần đăng nhập (1-7)")
    parser.add_argument("--all", action="store_true", help="Đăng nhập tuần tự các slot còn lại (2 -> 7)")
    args = parser.parse_args()

    if args.slot:
        show_all_status()
        login_single_profile(args.slot)
        return

    if args.all:
        show_all_status()
        for i in range(2, 8):
            act = login_single_profile(i)
            if act == "cancel":
                print("\n🛑 Đã dừng thiết lập theo yêu cầu của bạn.")
                return
            if i < 7:
                print(f"\nChuẩn bị chuyển sang tài khoản tiếp theo ({i + 1})...")
                time.sleep(2)
        print("\n🎉 CHÚC MỪNG! BẠN ĐÃ THIẾT LẬP THÀNH CÔNG CÁC TÀI KHOẢN GOOGLE AI PRO (SLOT 02 -> 07)!")
        return

    while True:
        show_all_status()
        print("\nCHỌN CHỨC NĂNG BẠN MUỐN THỰC HIỆN:")
        print("  1 - Đăng nhập tuần tự các tài khoản phụ còn lại (Slot 02 -> 07)")
        print("  2 - Đăng nhập cho 1 tài khoản cụ thể (Chọn 2, 3, 4, 5, 6 hoặc 7)")
        print("  0 - Thoát")
        try:
            choice = input("\nNhập lựa chọn của bạn (1/2/0): ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nThoát chương trình.")
            return

        if choice == "1":
            for i in range(2, 8):
                act = login_single_profile(i)
                if act == "cancel":
                    print("\n🛑 Đã dừng thiết lập theo yêu cầu của bạn.")
                    break
                if i < 7:
                    print(f"\nChuẩn bị chuyển sang tài khoản tiếp theo ({i + 1})...")
                    time.sleep(2)
            print("\n🎉 HOÀN TẤT THIẾT LẬP CÁC TÀI KHOẢN!")
            return
        elif choice == "2":
            try:
                acc_num = int(input("Nhập số thứ tự tài khoản bạn muốn đăng nhập (1-7): ").strip())
                if acc_num == 1:
                    confirm = input(f"⚠️ Slot 1 đã liên kết với {IMAGE_ACCOUNT_EMAIL}. Bạn có muốn ghi đè? (y/N): ").strip().lower()
                    if confirm == "y":
                        login_single_profile(1)
                    else:
                        print("Đã giữ nguyên Slot 1.")
                elif 2 <= acc_num <= 7:
                    login_single_profile(acc_num)
                else:
                    print("Số tài khoản không hợp lệ. Vui lòng nhập từ 2 đến 7.")
            except ValueError:
                print("Vui lòng nhập một số hợp lệ.")
        elif choice == "0":
            print("Đã thoát.")
            return
        else:
            print("Lựa chọn không hợp lệ, vui lòng chọn lại.")


if __name__ == "__main__":
    main()
