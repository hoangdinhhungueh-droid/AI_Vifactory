"""
Pure-PIL chroma-key background remover with Auto Backdrop Detection.
Supports Solid Lime Green (#00FF00), Pure Magenta (#FF00FF), or custom backdrops.
Zero external ML dependencies (safe for host without AVX2/X86_V2).
"""
import sys
import math
from PIL import Image, ImageFile

ImageFile.LOAD_TRUNCATED_IMAGES = True


def detect_backdrop_color(im: Image.Image) -> tuple:
    w, h = im.size
    samples = [
        im.getpixel((min(5, w-1), min(5, h-1))),
        im.getpixel((max(0, w-6), min(5, h-1))),
        im.getpixel((min(5, w-1), max(0, h-6))),
        im.getpixel((max(0, w-6), max(0, h-6))),
        im.getpixel((w // 2, min(5, h-1)))
    ]
    r_avg = sum(s[0] for s in samples) / len(samples)
    g_avg = sum(s[1] for s in samples) / len(samples)
    b_avg = sum(s[2] for s in samples) / len(samples)

    # Check for Lime Green (#00FF00) dominance
    if g_avg > 180 and r_avg < 100 and b_avg < 100:
        return (int(r_avg), int(g_avg), int(b_avg))
    # Check for Magenta (#FF00FF) dominance
    if r_avg > 180 and b_avg > 180 and g_avg < 100:
        return (int(r_avg), int(g_avg), int(b_avg))
    return (int(r_avg), int(g_avg), int(b_avg))


def remove_bg_chromakey(
    src_path: str,
    dst_path: str,
    bg_color=None,
    tol: float = 65.0,
    soft: float = 35.0,
):
    im = Image.open(src_path).convert("RGBA")
    if bg_color is None:
        bg_color = detect_backdrop_color(im)
    br, bgc, bb = bg_color[:3]
    data = im.getdata()
    out = [None] * len(data)
    for i, (r, g, b, a) in enumerate(data):
        d = math.sqrt((r - br) ** 2 + (g - bgc) ** 2 + (b - bb) ** 2)
        if d < tol:
            alpha = 0
        elif d < tol + soft:
            alpha = int(255 * (d - tol) / soft)
        else:
            alpha = a if a < 255 else 255
        out[i] = (r, g, b, alpha)
    im.putdata(out)
    im.save(dst_path, "PNG")
    return dst_path


def main():
    if len(sys.argv) < 3:
        print("usage: remove_bg_chromakey.py <src> <dst.png> [r g b tol soft]")
        sys.exit(1)
    src, dst = sys.argv[1], sys.argv[2]
    args = sys.argv[3:]
    kwargs = {}
    if len(args) >= 3:
        kwargs["bg_color"] = (int(args[0]), int(args[1]), int(args[2]))
    if len(args) >= 4:
        kwargs["tol"] = float(args[3])
    if len(args) >= 5:
        kwargs["soft"] = float(args[4])
    path = remove_bg_chromakey(src, dst, **kwargs)
    print("WROTE", path)


if __name__ == "__main__":
    main()
