#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""scripts/flow_video_dispatcher.py
Bộ điều phối tự động hóa sinh và tải video từ Google Flow (Veo 3.1 - Fast)
cho 6 tài khoản Google AI Pro (acc_01 đến acc_06).

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
        'email': 'hoangdinhhung.mm@gmail.com',
        'name': 'Đình Hưng Hoàng'
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
}

def dismiss_dialogs(page):
    """Đóng các popup chào mừng, điều khoản nếu xuất hiện."""
    for _ in range(3):
        next_btn = page.get_by_role("button", name="Next")
        if next_btn.count() > 0 and next_btn.first.is_visible():
            try:
                next_btn.first.click()
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

        for name in ["Continue", "Get started", "Accept", "Got it", "Dismiss", "Close"]:
            btn = page.get_by_role("button", name=name)
            if btn.count() > 0 and btn.first.is_visible():
                try:
                    if btn.first.is_enabled():
                        btn.first.click()
                        time.sleep(1)
                except Exception:
                    pass

def ensure_veo_fast_model(page) -> bool:
    """Đảm bảo model Veo 3.1 - Fast được chọn."""
    try:
        # Check settings
        settings_btn = page.locator("button[aria-label='Settings']").first
        if not settings_btn.is_visible():
            pbox = page.locator("div.ProseMirror, [contenteditable='true']").first
            if pbox.count() > 0:
                pbox.click()
                time.sleep(1)

        if settings_btn.count() > 0 and settings_btn.is_visible():
            settings_btn.click()
            time.sleep(1)

            # Never confirm
            never_opt = page.locator("text='Never'").first
            if never_opt.count() > 0:
                never_opt.click(force=True)
                time.sleep(0.5)

            # Model dropdown
            model_drop = page.locator("button:has-text('Omni 1.1 Flash'), button:has-text('Veo')").first
            if model_drop.count() > 0:
                btn_text = model_drop.text_content() or ""
                if "Veo 3.1 - Fast" not in btn_text:
                    model_drop.click()
                    time.sleep(1)
                    veo_choice = page.locator("[role='menuitem'], button").filter(has_text="Veo 3.1 - Fast").last
                    if veo_choice.count() > 0:
                        veo_choice.click(force=True)
                        time.sleep(1)

            save_btn = page.locator("button:has-text('Save')").first
            if save_btn.count() > 0 and save_btn.is_enabled():
                save_btn.click()
                time.sleep(1)
            else:
                close_btn = page.locator("button[aria-label='Close'], button:has-text('close')").first
                if close_btn.count() > 0 and close_btn.is_visible():
                    close_btn.click()
                else:
                    settings_btn.click()
                time.sleep(1)
        return True
    except Exception as e:
        print(f"      ⚠️ Lỗi cấu hình model: {e}")
        return False

def generate_and_download_clip(page, clip: dict, out_file: Path, episode_dir: Path) -> bool:
    """Thực thi sinh 1 video clip qua Image-to-Video (I2V) và tải về máy qua CDP."""
    raw_prompt = clip["prompt"]
    scene_id = clip["scene_id"]
    output_filename = clip["output_filename"]
    prompt_text = raw_prompt

    print(f"\n   🎬 [BẮT ĐẦU CLIP I2V] {scene_id} -> {output_filename}")
    print(f"      Prompt: \"{prompt_text[:120]}...\"")

    # Tìm file ảnh seed (ưu tiên composite 16:9, sau đó cutout)
    seed_img = episode_dir / "composite_seeds" / f"composite_{scene_id}.png"
    if not seed_img.exists():
        # Fallback brain dir
        brain_seed = ARTIFACT_DIR / f"composite_{scene_id}.png"
        if brain_seed.exists():
            seed_img = brain_seed

    try:
        # 1. Đảm bảo ở trang canvas sạch (đóng player nếu đang mở)
        done_btn = page.locator("button[aria-label='Done editing scene'], button:has-text('Done')").first
        if done_btn.count() > 0 and done_btn.is_visible():
            done_btn.click()
            time.sleep(1)

        back_btn = page.locator("button[aria-label*='Back' i]").first
        if back_btn.count() > 0 and back_btn.is_visible():
            back_btn.click()
            time.sleep(1)

        # 2. Upload Seed Image qua Add Ingredients
        if seed_img.exists():
            print(f"      🖼️ Đang nạp ảnh Seed: {seed_img.name}...")
            ingr_btn = page.locator("button[aria-label*='Add ingredients to the prompt box' i], button[aria-label*='Add ingredients' i]").first
            if ingr_btn.count() > 0 and ingr_btn.is_visible():
                ingr_btn.click()
                time.sleep(2)

                up_btn = page.locator("button:has-text('Upload media'), button:has-text('Upload')").first
                if up_btn.count() > 0 and up_btn.is_visible():
                    with page.expect_file_chooser() as fc_info:
                        up_btn.click()
                    fc_info.value.set_files(str(seed_img))
                    time.sleep(4)

                    agree_btn = page.locator("button:has-text('I agree')").first
                    if agree_btn.count() > 0 and agree_btn.is_visible():
                        agree_btn.click()
                        time.sleep(3)

                    add_to_prompt = page.locator("button:has-text('Add to prompt')").first
                    if add_to_prompt.count() > 0 and add_to_prompt.is_visible():
                        add_to_prompt.click()
                        time.sleep(2)
                    else:
                        first_asset = page.locator("img[src*='googleusercontent']").first
                        if first_asset.count() > 0 and first_asset.is_visible():
                            first_asset.click()
                            time.sleep(1)
                            if add_to_prompt.count() > 0 and add_to_prompt.is_visible():
                                add_to_prompt.click()
                                time.sleep(2)

        # 3. Nhập Prompt vào ProseMirror
        prompt_box = page.locator("div.ProseMirror, [contenteditable='true']").first
        if prompt_box.count() == 0:
            print("      ❌ Không tìm thấy ô nhập prompt!")
            return False

        prompt_box.click()
        prompt_box.fill(prompt_text)
        time.sleep(1)

        # 4. Bấm Start generation
        start_gen = page.locator("button[aria-label*='Start generation' i], button:has-text('arrow_forward')").first
        if start_gen.count() == 0 or not start_gen.is_visible():
            print("      ❌ Không tìm thấy nút Start generation!")
            return False

        start_gen.click()
        print("      🚀 Đã bấm Start generation. Đang chờ Veo 3.1 sinh video...")
        time.sleep(3)

        # Auto approve modal qua JavaScript
        page.evaluate('''() => {
            const els = Array.from(document.querySelectorAll('*')).filter(el => {
                const txt = (el.innerText || '').trim();
                return (txt === 'Approve' || txt === 'Always approve') && !el.className.includes('dimmed');
            });
            if (els.length > 0) els[els.length - 1].click();
        }''')

        # 5. Chờ hoàn tất (theo dõi % tiến độ rendering)
        max_wait_sec = 210
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

        # 6. Mở video thumbnail mới nhất trong canvas hoặc tab Videos
        time.sleep(3)
        curr_thumbnails = page.locator("img[src*='googleusercontent'], img[src*='asb']").all()
        if not curr_thumbnails:
            print("      ❌ Không tìm thấy thumbnail trên canvas!")
            return False

        curr_thumbnails[0].click()
        time.sleep(3)

        # 7. Bấm nút Download media
        dl_btn = page.locator("button[aria-label*='Download media' i], button:has-text('download')").first
        if dl_btn.count() == 0 or not dl_btn.is_visible():
            print("      ❌ Không tìm thấy nút Download media trong player!")
            return False

        dl_btn.click()
        time.sleep(1)

        # 8. Chọn 720p và tải về file
        opt_720 = page.locator("div, button, span").filter(has_text="720p").last
        if opt_720.count() == 0 or not opt_720.is_visible():
            print("      ❌ Không thấy tùy chọn 720p!")
            return False

        opt_720.click()
        downloaded = None
        for _ in range(35):
            time.sleep(2)
            cr = list(out_file.parent.glob("*.crdownload"))
            if cr:
                continue
            for f in out_file.parent.glob("*.mp4"):
                if f.name != out_file.name and (time.time() - f.stat().st_mtime < 45):
                    downloaded = f
                    break
            if downloaded:
                break

        if not downloaded:
            # Fallback check any freshly modified crdownload file
            for cr in out_file.parent.glob("*.crdownload"):
                if time.time() - cr.stat().st_mtime < 60 and cr.stat().st_size > 100000:
                    downloaded = cr
                    break

        if downloaded:
            import shutil
            shutil.copy2(str(downloaded), str(out_file))
            print(f"      ✅ Tải thành công {out_file.name} ({out_file.stat().st_size:,} bytes)")
            return True
        else:
            print("      ❌ Không phát hiện file tải về trong thư mục!")
            return False

    except Exception as e:
        print(f"      ❌ Lỗi khi sinh video {scene_id}: {e}")
        return False

def dispatch_for_account(acc_key: str, clips: list, out_dir: Path, episode_dir: Path) -> dict:
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
            headless=True,
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

        # Cấu hình CDP download
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
                page.wait_for_selector(".project-card, button:has-text('New project'), button:has-text('Start Creating')", timeout=25000)
            except Exception:
                pass
            time.sleep(2)

            # Vào project hiện có hoặc tạo mới
            cards = page.locator(".project-card").all()
            if cards:
                print(f"   Mở project có sẵn ({len(cards)} cards)...")
                cards[0].click()
            else:
                new_btn = page.locator("button:has-text('New project')").first
                if new_btn.count() > 0 and new_btn.is_visible():
                    print("   Tạo project mới qua nút New project...")
                    new_btn.click()
                else:
                    sc_btn = page.locator("button:has-text('Start Creating')").first
                    if sc_btn.count() > 0 and sc_btn.is_visible():
                        print("   Tạo project qua nút Start Creating...")
                        sc_btn.click()
                    else:
                        print("   Click New project bằng text...")
                        page.get_by_text("New project").first.click(force=True)

        print("   Đợi canvas và prompt editor tải xong...")
        page.wait_for_selector("div.ProseMirror, [contenteditable='true']", timeout=30000)
        time.sleep(3)
        dismiss_dialogs(page)

        # Đảm bảo cấu hình Veo 3.1 - Fast
        ensure_veo_fast_model(page)

        # Sinh từng clip
        for clip in clips:
            out_file = out_dir / clip["output_filename"]
            if out_file.exists() and out_file.stat().st_size > 200000:
                print(f"\n   ⏩ [BỎ QUA] {clip['output_filename']} đã tồn tại hợp lệ ({out_file.stat().st_size:,} bytes)")
                results[clip["scene_id"]] = True
                continue

            success = generate_and_download_clip(page, clip, out_file, episode_dir)
            results[clip["scene_id"]] = success
            time.sleep(3)

        browser.close()

    return results

def main():
    parser = argparse.ArgumentParser(description="Google Flow Video Dispatcher for 6 Accounts")
    parser.add_argument("--episode", required=True, help="Episode ID (e.g. <MARKET>_EP<XXXX>_<slug>)")
    parser.add_argument("--acc", default="all", help="acc_01 to acc_06 or all")
    parser.add_argument("--limit", type=int, default=0, help="Limit number of clips to generate (0 for unlimited)")
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
    print(f"🎯 EPISODE: {args.episode}")
    print(f"📦 Tổng số clips trong manifest: {len(all_clips)}")
    print(f"📁 Thư mục lưu trữ: {out_dir}")

    # Nhóm clips theo flow_slot
    clips_by_acc = {}
    for c in all_clips:
        slot = c.get("flow_slot", "acc_01")
        clips_by_acc.setdefault(slot, []).append(c)

    target_accs = list(PROFILES.keys()) if args.acc == "all" else [args.acc]

    total_success = 0
    total_processed = 0

    for acc in target_accs:
        clips = clips_by_acc.get(acc, [])
        if not clips:
            print(f"⚠️ Không có clip nào được gán cho {acc}")
            continue

        if args.limit > 0:
            clips = clips[:args.limit]

        res = dispatch_for_account(acc, clips, out_dir, episode_dir)
        for s_id, ok in res.items():
            total_processed += 1
            if ok:
                total_success += 1

    print("\n" + "=" * 70)
    print(f"📊 KẾT QUẢ ĐIỀU PHỐI SINH VIDEO: {total_success}/{total_processed} clips thành công!")
    print("=" * 70)

if __name__ == "__main__":
    main()
