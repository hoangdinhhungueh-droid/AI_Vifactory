#!/usr/bin/env python3
"""
foreground_batch_cutout.py

Batch chroma-key cutout tool for EP5+ foreground character images generated
externally (Google AI Studio / Nano Banana Pro) on a solid magenta (#FF00FF)
key-color background.

Handles two input shapes automatically:
  1) Clean single-panel image (16:9, magenta fills the canvas edge-to-edge
     around the centered character) -> uses the whole frame.
  2) Legacy 3-panel contact-sheet image (model added extra comparison views;
     magenta only in the middle band) -> auto-detects the magenta band on
     the horizontal centerline and crops to it before keying.

Usage:
  python3 foreground_batch_cutout.py --input_dir /path/to/raw --output_dir /path/to/out

Name input files in scene order, e.g. scene03.jpg, scene04.jpg, ...
Output: <name>_cutout.png (RGBA, transparent background) per input image.
"""
import argparse
import os
import sys
import numpy as np
from PIL import Image


def is_magenta_like(r, g, b):
    return (r > 150) and (b > 150) and (g < 120) and ((int(r) - int(g)) > 40) and ((int(b) - int(g)) > 40)


def detect_panel_bounds(arr):
    h, w, _ = arr.shape
    y = h // 2
    row = arr[y]

    left_edge = row[0]
    right_edge = row[-1]
    if is_magenta_like(*left_edge) and is_magenta_like(*right_edge):
        return 0, w

    mask = np.array([is_magenta_like(*row[x]) for x in range(w)])
    best_start, best_len = None, 0
    x = 0
    while x < w:
        if mask[x]:
            start = x
            while x < w and mask[x]:
                x += 1
            length = x - start
            if length > best_len:
                best_len, best_start = length, start
        else:
            x += 1

    if best_start is None:
        return None

    pad = 4
    x0 = max(0, best_start - pad)
    x1 = min(w, best_start + best_len + pad)
    return x0, x1


def chroma_key_despill(crop_rgb):
    carr = np.array(crop_rgb).astype(float)
    cr, cg, cb = carr[:, :, 0], carr[:, :, 1], carr[:, :, 2]

    dist = np.sqrt((cr - 255) ** 2 + (cg - 0) ** 2 + (cb - 255) ** 2)
    is_bg_like = (cr > 120) & (cb > 120) & ((cr - cg) > 30) & ((cb - cg) > 30)

    thresh_full = 90.0
    thresh_edge = 220.0
    alpha = np.clip((dist - thresh_full) / (thresh_edge - thresh_full), 0, 1) * 255
    alpha = np.where(is_bg_like, alpha, 255).astype(np.uint8)

    spill = np.maximum(0, np.minimum(cr, cb) - cg)
    new_r = np.clip(cr - spill, 0, 255)
    new_b = np.clip(cb - spill, 0, 255)

    rgba = np.dstack([new_r, cg, new_b, alpha]).astype(np.uint8)
    return Image.fromarray(rgba, mode='RGBA')


def process_image(path, output_dir):
    name = os.path.splitext(os.path.basename(path))[0]
    im = Image.open(path).convert('RGB')
    arr = np.array(im)

    bounds = detect_panel_bounds(arr)
    if bounds is None:
        print(f"[WARN] {name}: no magenta panel detected, skipping")
        return None

    x0, x1 = bounds
    crop = im.crop((x0, 0, x1, im.height))
    cutout = chroma_key_despill(crop)

    out_path = os.path.join(output_dir, f"{name}_cutout.png")
    cutout.save(out_path)
    print(f"[OK] {name}: cropped x[{x0}:{x1}] -> {out_path}")
    return out_path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--input_dir', required=True)
    ap.add_argument('--output_dir', required=True)
    args = ap.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)
    files = sorted(
        f for f in os.listdir(args.input_dir)
        if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp'))
    )
    if not files:
        print("No input images found.")
        sys.exit(1)

    results = []
    for f in files:
        r = process_image(os.path.join(args.input_dir, f), args.output_dir)
        if r:
            results.append(r)

    print(f"\nProcessed {len(results)}/{len(files)} images successfully.")


if __name__ == '__main__':
    main()
