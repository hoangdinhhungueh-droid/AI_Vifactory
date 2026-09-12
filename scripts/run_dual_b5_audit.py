#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dual B5 Visual Audit Runner (Rule 122 + High-Level Multimodal Vision LLM).
Audits all 35 BG & FG assets of JP_EP0001_tada_shrine_debt against prompts_forge.json.
"""
import os
import sys
import json
import time
import io
import concurrent.futures
from pathlib import Path
from PIL import Image

sys.path.insert(0, "/root/video_factory")
from app.services.image_audit import audit_image_hhtech, compute_verdict

EPISODE_ID = "JP_EP0001_tada_shrine_debt"
EP_DIR = Path(f"/var/vf/episodes/{EPISODE_ID}")
IMAGES_DIR = EP_DIR / "images"
PROMPTS_PATH = EP_DIR / "prompts_forge.json"
OUTPUT_REPORT_PATH = EP_DIR / "b5_audit_report.json"

def run_pillow_tech_checks(im: Image.Image, layer_type: str) -> dict:
    w, h = im.size
    dim_pass = (w >= 1920 and h >= 1080)
    format_png = True
    total_pixels = w * h

    transparency_pct = None
    magenta_leak_pct = None
    transparency_ok = True
    magenta_leak_ok = True

    if layer_type.lower() == "foreground" and im.mode == "RGBA":
        raw = im.tobytes()
        trans_count = 0
        magenta_count = 0
        vis_count = 0
        vis_black_count = 0
        for i in range(0, len(raw), 4):
            r, g, b, a = raw[i], raw[i+1], raw[i+2], raw[i+3]
            if a < 10:
                trans_count += 1
            else:
                vis_count += 1
                if r < 15 and g < 15 and b < 15:
                    vis_black_count += 1
            if r > 220 and g < 35 and b > 220 and a > 20:
                magenta_count += 1

        transparency_pct = round((trans_count / total_pixels) * 100, 2)
        transparency_ok = (transparency_pct >= 20.0)
        magenta_leak_pct = round((magenta_count / total_pixels) * 100, 3)
        magenta_leak_ok = (magenta_leak_pct < 0.5)

        if vis_count > 0:
            black_pct = round((vis_black_count / vis_count) * 100, 2)
            not_black_frame = (black_pct < 85.0)
        else:
            black_pct = 100.0
            not_black_frame = False
    else:
        rgb_im = im.convert("RGB")
        raw = rgb_im.tobytes()
        black_count = 0
        for i in range(0, len(raw), 3):
            if raw[i] < 15 and raw[i+1] < 15 and raw[i+2] < 15:
                black_count += 1
        black_pct = round((black_count / total_pixels) * 100, 2)
        not_black_frame = (black_pct < 85.0)

    tech_pass = dim_pass and not_black_frame and transparency_ok and magenta_leak_ok

    return {
        "tech_pass": tech_pass,
        "dimensions": f"{w}x{h}",
        "black_pixel_pct": black_pct,
        "transparency_pct": transparency_pct,
        "magenta_leak_pct": magenta_leak_pct,
        "dim_pass": dim_pass,
        "not_black_frame": not_black_frame,
        "transparency_ok": transparency_ok,
        "magenta_leak_ok": magenta_leak_ok
    }

def prepare_opt_bytes(img_path: Path) -> bytes:
    with Image.open(img_path) as im:
        thumb = im.copy()
        thumb.thumbnail((1280, 720), Image.Resampling.LANCZOS)
        buf = io.BytesIO()
        if thumb.mode in ("RGBA", "LA"):
            thumb.save(buf, format="PNG", optimize=True)
        else:
            thumb.save(buf, format="JPEG", quality=85)
        return buf.getvalue()

def audit_single_asset(item_info: dict, prompts: dict) -> dict:
    key = item_info["key"]
    layer = item_info["layer"]
    img_path = IMAGES_DIR / f"{key}.png"

    if not img_path.exists():
        return {
            "reuse_key": key,
            "layer_type": layer.capitalize(),
            "status": "FILE_NOT_FOUND",
            "verdict": "REJECT",
            "score": 0.0
        }

    # 1. Tech checks
    with Image.open(img_path) as im:
        tech_res = run_pillow_tech_checks(im, layer)

    # 2. Get prompt
    prompt_dict = prompts.get("backgrounds" if layer == "background" else "foregrounds", {})
    prompt_text = prompt_dict.get(key, "")

    # 3. Vision LLM call
    opt_bytes = prepare_opt_bytes(img_path)
    t0 = time.time()
    try:
        llm_res = audit_image_hhtech(opt_bytes, prompt_text, layer=layer)
        elapsed = round(time.time() - t0, 2)
        v, final_score = compute_verdict(llm_res["d1"], llm_res["d2"], llm_res["d3"], llm_res["confidence"])
    except Exception as e:
        print(f"Error auditing {key}: {e}", file=sys.stderr)
        llm_res = {"d1": 0.0, "d2": 0.0, "d3": 0.0, "confidence": 0.0, "issues": [str(e)], "notes": "API call failed"}
        v, final_score = "REVIEW", 5.0
        elapsed = round(time.time() - t0, 2)

    return {
        "reuse_key": key,
        "layer_type": layer.capitalize(),
        "dimensions": tech_res["dimensions"],
        "technical_checks": {
            "format_png": True,
            "resolution_ok": tech_res["dim_pass"],
            "not_black_frame": tech_res["not_black_frame"],
            "transparency_ok": tech_res["transparency_ok"],
            "magenta_leak_ok": tech_res["magenta_leak_ok"],
            "metrics": tech_res
        },
        "vision_audit": {
            "model": "claude-haiku-4.5 (hhtech)",
            "d1_prompt_adherence": llm_res["d1"],
            "d2_object_accuracy": llm_res["d2"],
            "d3_visual_logic": llm_res["d3"],
            "confidence": llm_res["confidence"],
            "weighted_score": round(final_score, 2),
            "verdict": v,
            "issues": llm_res["issues"],
            "notes": llm_res["notes"],
            "latency_s": elapsed,
            "tokens_in": llm_res.get("_tok_in", 0),
            "tokens_out": llm_res.get("_tok_out", 0)
        },
        "verdict": "APPROVED" if (v == "APPROVED" and tech_res["tech_pass"]) else "REVIEW",
        "status": "Dual Audit Completed (Tech + Vision LLM)"
    }

def main():
    if not PROMPTS_PATH.exists():
        print(f"prompts_forge.json not found at {PROMPTS_PATH}", file=sys.stderr)
        sys.exit(1)

    with open(PROMPTS_PATH, "r", encoding="utf-8") as f:
        prompts = json.load(f)

    # Collect all image keys
    files = sorted(os.listdir(IMAGES_DIR))
    assets = []
    for f in files:
        if not f.endswith(".png"):
            continue
        key = f[:-4]
        if "_bg_" in key:
            assets.append({"key": key, "layer": "background"})
        elif "_fg_" in key:
            assets.append({"key": key, "layer": "foreground"})

    print(f"Starting Dual Visual Audit for {len(assets)} assets ({sum(1 for a in assets if a['layer']=='background')} BGs, {sum(1 for a in assets if a['layer']=='foreground')} FGs)...")

    results = []
    # Use max_workers=3 for polite rate limit and high throughput
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        futures = {executor.submit(audit_single_asset, item, prompts): item["key"] for item in assets}
        completed = 0
        for fut in concurrent.futures.as_completed(futures):
            k = futures[fut]
            try:
                res = fut.result()
                results.append(res)
                completed += 1
                va = res["vision_audit"]
                print(f"[{completed}/{len(assets)}] {k} ({res['layer_type']}): Score={va['weighted_score']}, Verdict={res['verdict']} ({va['latency_s']}s)")
            except Exception as e:
                print(f"[{completed}/{len(assets)}] {k} FAILED: {e}", file=sys.stderr)

    # Sort results by key
    results.sort(key=lambda x: x["reuse_key"])

    approved_count = sum(1 for r in results if r["verdict"] == "APPROVED")
    review_count = sum(1 for r in results if r["verdict"] == "REVIEW")

    report = {
        "episode_id": EPISODE_ID,
        "total_images": len(results),
        "approved_count": approved_count,
        "review_count": review_count,
        "overall_verdict": "APPROVED" if approved_count >= 28 else "REVIEW",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "audit_architecture": "Dual Parallel Audit (Rule 122 + claude-haiku-4.5 Multimodal Vision)",
        "items": results
    }

    with open(OUTPUT_REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"\n=======================================================")
    print(f"DUAL VISUAL AUDIT COMPLETE: {OUTPUT_REPORT_PATH}")
    print(f"Total: {len(results)} | Approved: {approved_count} | Review: {review_count}")
    print(f"Overall Verdict: {report['overall_verdict']}")
    print(f"=======================================================")

if __name__ == "__main__":
    main()
