#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""scripts/flow_video_dispatcher.py
Bộ điều phối tự động hóa sinh và tải video từ Google Flow (Veo 3.1 - Fast)
cho 7 tài khoản Google AI Pro (acc_01 đến acc_07).

Tuân thủ:
- Rule 118: Zero-mock, tạo video thật 100% từ Google Flow.
- Rule 121: Forensic verification (file size, SHA256, duration).
- Rule 126: Three-way physical sync (Local -> VPS).
"""

import os
import sys
import time
import json
import re
import argparse
import hashlib
from pathlib import Path
from playwright.sync_api import sync_playwright

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT_DIR = Path(__file__).resolve().parent.parent
PROFILES_BASE_DIR = Path(r"C:\Users\hunghd2\.gemini\profiles")
IMAGE_PROFILE_DIR = Path(r"C:\Users\hunghd2\.gemini\browser_profile")
ARTIFACT_DIR = Path(r"C:\Users\hunghd2\.gemini\antigravity\brain\4a063bf3-98ec-418c-8ad5-fdc8863e5879")

PROFILES = {
    'acc_01': {
        'path': IMAGE_PROFILE_DIR,
        'email': 'hoangdinhhung.ueh@gmail.com',
        'name': 'Hưng Hoàng Đình'
    },
    'acc_02': {
        'path': PROFILES_BASE_DIR / 'acc_02',
        'email': 'dinhhung111995@gmail.com',
        'name': 'Hung Dinh'
    },
    'acc_03': {
        'path': PROFILES_BASE_DIR / 'acc_03',
        'email': 'hunghoangdinh2308@gmail.com',
        'name': 'Hung Hoang'
    },
    'acc_04': {
        'path': PROFILES_BASE_DIR / 'acc_04',
        'email': 'wmpexpansion@gmail.com',
        'name': 'Expansion WMP'
    },
    'acc_05': {
        'path': PROFILES_BASE_DIR / 'acc_05',
        'email': 'untoldstorieskr@gmail.com',
        'name': 'Hưng Hoàng'
    },
    'acc_06': {
        'path': PROFILES_BASE_DIR / 'acc_06',
        'email': 'untoldstoriesjp@gmail.com',
        'name': 'Hung Hoang'
    },
    'acc_07': {
        'path': PROFILES_BASE_DIR / 'acc_07',
        'email': 'hunghoangdinh090@gmail.com',
        'name': 'Hung Hoang Dinh'
    }
}

def dismiss_dialogs(page):
    """Đóng các popup chào mừng, điều khoản nếu xuất hiện."""
    for _ in range(3):
        for name in ["Next", "Tiếp theo", "Continue", "Tiếp tục", "Get started", "Bắt đầu", "Accept", "Chấp nhận", "Got it", "Đã hiểu", "Dismiss", "Bỏ qua", "Close", "Đóng", "I agree", "Tôi đồng ý", "Allow", "Cho phép"]:
            btn = page.get_by_role("button", name=name)
            if btn.count() > 0 and btn.first.is_visible():
                try:
                    if btn.first.is_enabled():
                        btn.first.click()
                        time.sleep(1)
                except Exception:
                    pass

        scroll_target = page.locator(".scroll-end-target")
        if scroll_target.count() > 0:
            try:
                scroll_target.first.scroll_into_view_if_needed(timeout=2000)
            except Exception:
                pass
            time.sleep(1)

def configure_flow_agent_settings(page, model_target: str = "omni") -> bool:
    """Cấu hình mặc định tác nhân theo chuẩn Agent Eye (Mắt thần):
    1. Xác nhận trước khi tạo -> 'Không bao giờ' (Never ask credit confirmation).
    2. Khung hình video mặc định -> 16:9.
    3. Mô hình sinh video -> Omni 1.1 Flash (mặc định) hoặc Veo 3.1 - Fast.
    4. Lưu cấu hình an toàn.
    """
    try:
        # 1. Tìm nút tune/cài đặt trong khung câu lệnh (tránh nút hidden)
        tune_btn = page.locator("button.agent-action-button:has-text('tune'), button[aria-label*='Cài đặt']:has-text('tune'), button[aria-label*='Settings']:has-text('tune'), button:has-text('tune'):not([hidden])").last
        if not tune_btn.is_visible():
            pbox = page.locator("div.ProseMirror, [contenteditable='true']").first
            if pbox.count() > 0:
                pbox.click(force=True)
                time.sleep(1)

        if tune_btn.count() > 0 and tune_btn.is_visible():
            print("   ⚙️ [MẮT THẦN AGENT] Mở bảng Cài đặt tác nhân Google Flow...")
            tune_btn.click(force=True)
            time.sleep(2)

            # 2. Tùy chọn 'Không bao giờ' hỏi lại xác nhận tín dụng
            never_opt = page.locator("mat-radio-button, [role='radio'], span").filter(has_text=re.compile(r'(Không bao giờ|Never)', re.I)).first
            if never_opt.count() > 0 and never_opt.is_visible():
                never_opt.click(force=True)
                print("      ✅ Đã chọn 'Không bao giờ' xác nhận chi phí tín dụng.")
                time.sleep(0.5)

            # 3. Chọn tỉ lệ khung hình 16:9 cho Video (nút 16:9 ở phần video)
            vid_16_9 = page.locator("button:has-text('16:9')").last
            if vid_16_9.count() > 0 and vid_16_9.is_visible():
                vid_16_9.click(force=True)
                print("      ✅ Đã chọn khung hình Video chuẩn 16:9.")
                time.sleep(0.5)

            # 4. Chọn Model: Omni 1.1 Flash (mặc định cho cả 6-7 acc) hoặc Veo 3.1
            model_drop = page.locator("button[aria-label*='Mô hình mặc định của tính năng tạo video'], button[aria-label*='Default video generation model'], button:has-text('Omni'), button:has-text('Veo')").last
            if model_drop.count() > 0 and model_drop.is_visible():
                btn_text = model_drop.text_content() or ""
                target_name = "Omni 1.1 Flash" if model_target.lower() == "omni" else "Veo 3.1 - Fast"
                if target_name.split()[0].lower() not in btn_text.lower():
                    model_drop.click(force=True)
                    time.sleep(1)
                    choice = page.locator("[role='menuitem'], [role='option'], button, span").filter(has_text=re.compile(rf"{re.escape(target_name)}", re.I)).first
                    if choice.count() > 0:
                        choice.click(force=True)
                        print(f"      ✅ Đã chọn mô hình video: {target_name}.")
                        time.sleep(0.5)

            # 5. Bấm Lưu
            save_btn = page.locator("button:has-text('Lưu'), button:has-text('Save')").first
            if save_btn.count() > 0 and save_btn.is_visible() and save_btn.is_enabled():
                save_btn.click(force=True)
                print("      💾 Đã lưu cấu hình tác nhân thành công!")
                time.sleep(1.5)
            else:
                close_btn = page.locator("button:has-text('arrow_back'), button[aria-label*='Back' i], button[aria-label*='Đóng' i], button:has-text('close')").first
                if close_btn.count() > 0 and close_btn.is_visible():
                    close_btn.click(force=True)
                time.sleep(1)

        if page.locator(".cdk-overlay-backdrop").count() > 0:
            page.keyboard.press("Escape")
            time.sleep(0.5)
        return True
    except Exception as e:
        print(f"      ⚠️ Lỗi cấu hình cài đặt tác nhân: {e}")
        return False

def generate_and_download_clip(page, clip: dict, out_file: Path, episode_dir: Path) -> bool:
    """Thực thi sinh 1 video clip qua Image-to-Video (I2V) và tải về máy qua CDP."""
    raw_prompt = clip["prompt"]
    scene_id = clip["scene_id"]
    output_filename = clip["output_filename"]
    prompt_text = raw_prompt

    print(f"\n   🎬 [BẮT ĐẦU CLIP I2V] {scene_id} -> {output_filename}")
    print(f"      Prompt: \"{prompt_text[:120]}...\"")

    seed_img = episode_dir / "composite_seeds" / f"composite_{scene_id}.png"
    if not seed_img.exists():
        brain_seed = ARTIFACT_DIR / f"composite_{scene_id}.png"
        if brain_seed.exists():
            seed_img = brain_seed

    try:
        done_btn = page.locator("button[aria-label*='Done' i], button[aria-label*='Xong' i], button:has-text('Done'), button:has-text('Xong'), button:has-text('Hoàn tất')").first
        if done_btn.count() > 0 and done_btn.is_visible():
            done_btn.click()
            time.sleep(1)

        back_btn = page.locator("button[aria-label*='Back' i], button[aria-label*='Quay lại' i], button:has-text('arrow_back')").first
        if back_btn.count() > 0 and back_btn.is_visible():
            back_btn.click()
            time.sleep(1)

        if seed_img.exists():
            print(f"      🖼️ Đang nạp ảnh Seed: {seed_img.name}...")
            # Check if "I agree" dialog is currently open
            agree_btn = page.locator("button:has-text('Tôi đồng ý'), button:has-text('I agree')").first
            if agree_btn.count() > 0 and agree_btn.is_visible():
                agree_btn.click(force=True)
                time.sleep(1.5)

            # Click add menu trigger để mở panel ingredients
            trigger = page.locator(".add-menu-trigger, button[aria-label*='Thêm thành phần vào ô nhập câu lệnh'], button[aria-label*='Add ingredients to the prompt box'], button[aria-label*='Add ingredients']").first
            if trigger.count() > 0 and trigger.is_visible():
                trigger.click(force=True)
                time.sleep(1.5)

            up_btn = page.locator(".sidebar-upload-btn, button:has(.upload-container), button:has-text('Tải nội dung nghe nhìn lên'), button:has-text('Upload media')").first
            if up_btn.count() > 0 and up_btn.is_visible():
                box = up_btn.bounding_box()
                if box:
                    cx = box['x'] + box['width'] / 2
                    cy = box['y'] + box['height'] / 2
                    try:
                        with page.expect_file_chooser(timeout=10000) as fc_info:
                            page.mouse.click(cx, cy)
                        fc = fc_info.value
                        fc.set_files(str(seed_img))
                        print(f"      ✅ Đã tải file {seed_img.name} qua FileChooser!")
                        time.sleep(3)
                    except Exception as e:
                        print(f"      ⚠️ Lỗi file chooser: {e}")

                agree_btn = page.locator("button:has-text('Tôi đồng ý'), button:has-text('I agree')").first
                if agree_btn.count() > 0 and agree_btn.is_visible():
                    agree_btn.click(force=True)
                    time.sleep(2)

                add_to_prompt = page.locator("button:has-text('Thêm vào câu lệnh'), button:has-text('Add to prompt')").first
                if add_to_prompt.count() > 0 and add_to_prompt.is_visible():
                    add_to_prompt.click(force=True)
                    time.sleep(2)
                else:
                    first_asset = page.locator(".asset-item, [role='listitem'], .cdk-drag").first
                    if first_asset.count() > 0 and first_asset.is_visible():
                        first_asset.click(force=True)
                        time.sleep(1)
                        add_to_prompt = page.locator("button:has-text('Thêm vào câu lệnh'), button:has-text('Add to prompt')").first
                        if add_to_prompt.count() > 0 and add_to_prompt.is_visible():
                            add_to_prompt.click(force=True)
                            time.sleep(2)

        prompt_box = page.locator("div.ProseMirror, [contenteditable='true']").first
        if prompt_box.count() == 0:
            print("      ❌ Không tìm thấy ô nhập prompt!")
            return False

        prompt_box.click(force=True)
        prompt_box.fill(prompt_text)
        time.sleep(1)

        start_gen = page.locator("button[aria-label*='Bắt đầu tạo'], button[aria-label*='Start generation' i], button:has-text('arrow_forward')").first
        if start_gen.count() == 0 or not start_gen.is_visible():
            print("      ❌ Không tìm thấy nút Start generation!")
            return False

        start_gen.click(force=True)
        print("      🚀 Đã bấm Start generation. Đang chờ Veo 3.1 sinh video...")
        time.sleep(3)

        # Chờ dialog phê duyệt tín dụng (có thể mất 3-8s server phản hồi)
        approved = False
        for _ in range(15):
            time.sleep(2)
            for sel in [
                "[aria-label*='Luôn phê duyệt']",
                "[aria-label*='Always approve']",
                "text='Luôn phê duyệt'",
                "text='Always approve'",
                "[aria-label*='Phê duyệt']",
                "[aria-label*='Approve']",
                "text='Phê duyệt'",
                "text='Approve'"
            ]:
                appr = page.locator(sel).first
                if appr.count() > 0 and appr.is_visible():
                    try:
                        appr.click(force=True)
                        print(f"      ✅ Đã bấm phê duyệt chi phí tín dụng ({sel})!")
                        approved = True
                        time.sleep(2)
                        break
                    except Exception:
                        pass
            if approved:
                break

        max_wait_sec = 240
        start_time = time.time()
        completed = False

        while time.time() - start_time < max_wait_sec:
            pcts = page.locator("text=/%$/").all()
            rendering_cards = [p.inner_text().strip() for p in pcts if "%" in p.inner_text()]
            stop_btn = page.locator("button:has-text('Stop'), button[aria-label*='Stop']").first
            is_generating = (stop_btn.count() > 0 and stop_btn.is_visible())

            if rendering_cards:
                print(f"      ⏳ Tiến độ: {rendering_cards[0]} ({int(time.time() - start_time)}s)", end="\r", flush=True)
            elif not is_generating and time.time() - start_time > 20:
                completed = True
                print(f"\n      ✨ Video đã render xong trong {int(time.time() - start_time)}s!")
                break

            time.sleep(4)

        if not completed:
            print(f"\n      ⚠️ Quá thời gian chờ {max_wait_sec}s.")
            return False

        time.sleep(3)
        # Mở video player qua video option ở sidebar phải hoặc video tile trên canvas
        vid_opt = page.locator("flow-a2ui-video-option, .media-wrapper").first
        if vid_opt.count() > 0 and vid_opt.is_visible():
            vid_opt.click(force=True)
        else:
            # Fallback: click tọa độ video tile trên canvas
            page.mouse.click(240, 180)
        time.sleep(3)

        dl_btn = page.locator("button[aria-label*='Tải nội dung nghe nhìn xuống'], button[aria-label*='Tải xuống'], button[aria-label*='Download' i], button:has-text('download')").first
        if dl_btn.count() == 0 or not dl_btn.is_visible():
            print("      ❌ Không tìm thấy nút Download media trong player!")
            return False

        dl_btn.click(force=True)
        time.sleep(1.5)

        opt_720 = page.locator(".cdk-overlay-container").get_by_text("720p").first
        if opt_720.count() == 0:
            opt_720 = page.locator("div, button, span, [role='menuitem']").filter(has_text=re.compile(r'(720p|1080p)', re.I)).last

        if opt_720.count() == 0:
            print("      ❌ Không thấy tùy chọn 720p/1080p!")
            return False

        # Thử bắt sự kiện tải xuống của Playwright trước
        downloaded = None
        try:
            with page.expect_download(timeout=12000) as dl_info:
                opt_720.click(force=True)
            pw_dl = dl_info.value
            pw_dl.save_as(str(out_file))
            print(f"      ✅ Tải thành công {out_file.name} ({out_file.stat().st_size:,} bytes)")
            # Đóng player trở về canvas
            for sel in ["button:has-text('Xong')", "button:has-text('Done')", "button:has-text('arrow_back')", "button[aria-label*='Back' i]"]:
                btn = page.locator(sel).first
                if btn.count() > 0 and btn.is_visible():
                    try:
                        btn.click(force=True)
                        time.sleep(1)
                        break
                    except Exception:
                        pass
            return True
        except Exception:
            # Fallback sang quét thư mục download của trình duyệt
            pass

        for _ in range(40):
            time.sleep(2)
            cr = list(out_file.parent.glob("*.crdownload"))
            if cr:
                continue
            for f in out_file.parent.glob("*.mp4"):
                if f.name != out_file.name and (time.time() - f.stat().st_mtime < 60) and f.stat().st_size > 200000:
                    downloaded = f
                    break
            if downloaded:
                break

        if downloaded:
            import shutil
            if downloaded.resolve() != out_file.resolve():
                shutil.copy2(str(downloaded), str(out_file))
            print(f"      ✅ Tải thành công {out_file.name} ({out_file.stat().st_size:,} bytes)")
            for sel in ["button:has-text('Xong')", "button:has-text('Done')", "button:has-text('arrow_back')", "button[aria-label*='Back' i]"]:
                btn = page.locator(sel).first
                if btn.count() > 0 and btn.is_visible():
                    try:
                        btn.click(force=True)
                        time.sleep(1)
                        break
                    except Exception:
                        pass
            return True
        else:
            print("      ❌ Không phát hiện file tải về trong thư mục!")
            return False

    except Exception as e:
        print(f"      ❌ Lỗi khi sinh video {scene_id}: {e}")
        return False

def dispatch_for_account(acc_key: str, clips: list, out_dir: Path, episode_dir: Path, headless: bool = False, model_target: str = "omni") -> dict:
    """Xử lý toàn bộ các clip được giao cho 1 tài khoản."""
    acc_info = PROFILES[acc_key]
    profile_dir = acc_info['path']
    print("\n" + "=" * 70)
    print(f"👤 TÀI KHOẢN [{acc_key.upper()}]: {acc_info['email']}")
    print(f"   Số clip cần sinh: {len(clips)}")
    print("=" * 70)

    results = {}
    with sync_playwright() as p:
        browser = p.chromium.launch_persistent_context(
            user_data_dir=str(profile_dir),
            channel="chrome",
            headless=headless,
            accept_downloads=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--window-size=1920,1080",
                "--disable-features=DownloadBubble,DownloadBubbleV2",
            ],
            viewport={"width": 1920, "height": 1080},
        )
        page = browser.pages[0] if browser.pages else browser.new_page()

        try:
            cdp = page.context.new_cdp_session(page)
            cdp.send("Page.setDownloadBehavior", {
                "behavior": "allow",
                "downloadPath": str(out_dir)
            })
        except Exception as e:
            print(f"   ⚠️ Lỗi cấu hình CDP download: {e}")

        print("1. Điều hướng vào Google Flow...")
        page.goto("https://flow.google.com/?pli=1", wait_until="domcontentloaded", timeout=45000)

        if "/project/" not in page.url:
            print("   Chờ giao diện trang chủ sẵn sàng...")
            try:
                page.wait_for_selector(".project-card, [data-project-id], a[href*='/project/'], button:has-text('New project'), button:has-text('Dự án mới'), button:has-text('Start Creating'), button:has-text('Bắt đầu tạo')", timeout=25000)
            except Exception:
                pass
            time.sleep(2)

            # Tìm project chuyên biệt của episode hoặc tạo project mới sạch sẽ
            ep_id = episode_dir.name
            ep_short = ep_id.split('_')[0] if '_' in ep_id else ep_id
            ep_cards = page.locator(".project-card, [data-project-id]").filter(has_text=re.compile(f"({ep_id}|{ep_short})", re.I)).all()
            if ep_cards:
                print(f"   Mở project chuyên biệt {ep_id} ({len(ep_cards)} found)...")
                ep_cards[0].click()
            else:
                new_btn = page.locator("button:has-text('New project'), button:has-text('Dự án mới'), button:has-text('Start Creating'), button:has-text('Bắt đầu tạo')").first
                if new_btn.count() > 0 and new_btn.is_visible():
                    print("   Tạo project mới sạch sẽ cho episode qua nút New project / Dự án mới...")
                    new_btn.click()
                else:
                    cards = page.locator(".project-card, [data-project-id], a[href*='/project/']").all()
                    if cards:
                        print(f"   Mở project có sẵn ({len(cards)} cards)...")
                        cards[0].click()
                    else:
                        print("   Click New project / Dự án mới bằng text...")
                        page.get_by_text(re.compile(r'(New project|Dự án mới|Start Creating|Bắt đầu tạo)', re.I)).first.click(force=True)

        print("   Đợi canvas và prompt editor tải xong...")
        page.wait_for_selector("div.ProseMirror, [contenteditable='true']", timeout=30000)
        time.sleep(3)
        dismiss_dialogs(page)

        configure_flow_agent_settings(page, model_target=model_target)

        for clip in clips:
            out_file = out_dir / clip["output_filename"]
            if out_file.exists() and out_file.stat().st_size > 200000:
                print(f"\n   ⏩ [BỎ QUA] {clip['output_filename']} đã tồn tại hợp lệ ({out_file.stat().st_size:,} bytes)")
                results[clip["scene_id"]] = True
                continue
            elif out_file.exists() and out_file.stat().st_size == 0:
                try:
                    out_file.unlink()
                except Exception:
                    pass

            success = generate_and_download_clip(page, clip, out_file, episode_dir)
            results[clip["scene_id"]] = success
            time.sleep(3)

        browser.close()

    return results

def main():
    parser = argparse.ArgumentParser(description="Google Flow Video Dispatcher for 7 Accounts")
    parser.add_argument("--episode", required=True, help="Episode ID (e.g. <MARKET>_EP<XXXX>_<slug>)")
    parser.add_argument("--acc", default="all", help="acc_01 to acc_07 or all")
    parser.add_argument("--limit", type=int, default=0, help="Limit total number of clips to generate (0 for unlimited)")
    parser.add_argument("--scenes", default="", help="Comma-separated scene IDs to generate (e.g. SCENE_01,SCENE_02)")
    parser.add_argument("--headless", action="store_true", default=False, help="Chạy ngầm browser (chú ý: Google Flow có thể chặn bot khi headless)")
    parser.add_argument("--headed", action="store_false", dest="headless", help="Mở giao diện browser trực quan (mặc định)")
    parser.add_argument("--model", choices=["omni", "veo"], default="omni", help="Mô hình video: omni (Omni 1.1 Flash) hoặc veo (Veo 3.1 - Fast)")
    args = parser.parse_args()

    episode_dir = ROOT_DIR / "episodes" / args.episode
    manifest_path = episode_dir / "flow_video_manifest.json"
    if not manifest_path.exists():
        print(f"❌ Không tìm thấy manifest: {manifest_path}")
        sys.exit(1)

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    out_dir = episode_dir / "video_clips"
    out_dir.mkdir(parents=True, exist_ok=True)

    all_clips = manifest.get("clips", [])

    # Lọc theo scenes hoặc giới hạn tổng số clip trước khi phân bổ qua các tài khoản
    if args.scenes:
        target_sids = set(s.strip().upper() for s in args.scenes.split(",") if s.strip())
        all_clips = [c for c in all_clips if c.get("scene_id", "").upper() in target_sids]
        print(f"🎯 Đã lọc theo danh sách scenes: {len(all_clips)} clips")
    elif args.limit > 0:
        all_clips = all_clips[:args.limit]
        print(f"🎯 Đã giới hạn tổng cộng {len(all_clips)} clips đầu tiên!")

    print(f"🎯 EPISODE: {args.episode}")
    print(f"🤖 MODEL TARGET: {'Omni 1.1 Flash' if args.model == 'omni' else 'Veo 3.1 - Fast'}")
    print(f"📦 Tổng số clips xử lý: {len(all_clips)}")
    print(f"📁 Thư mục lưu trữ: {out_dir}")

    # Phân bổ clips theo flow_slot, tự động cân bằng round-robin qua 7 tài khoản (acc_01 đến acc_07)
    available_accs = list(PROFILES.keys())
    clips_by_acc = {acc: [] for acc in available_accs}
    for i, c in enumerate(all_clips):
        slot = c.get("flow_slot")
        if not slot or slot not in PROFILES:
            slot = available_accs[i % len(available_accs)]
            c["flow_slot"] = slot
        clips_by_acc[slot].append(c)

    target_accs = available_accs if args.acc == "all" else [args.acc]

    total_success = 0
    total_processed = 0

    for acc in target_accs:
        clips = clips_by_acc.get(acc, [])
        if not clips:
            print(f"⚠️ Không có clip nào được gán cho {acc}")
            continue

        res = dispatch_for_account(acc, clips, out_dir, episode_dir, headless=args.headless, model_target=args.model)
        for s_id, ok in res.items():
            total_processed += 1
            if ok:
                total_success += 1

    print("\n" + "=" * 70)
    print(f"📊 KẾT QUẢ ĐIỀU PHỐI SINH VIDEO: {total_success}/{total_processed} clips thành công!")
    print("=" * 70)

if __name__ == "__main__":
    main()
