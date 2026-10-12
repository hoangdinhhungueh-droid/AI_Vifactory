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
    # Check for Pure Solid White (#FFFFFF) dominance
    if min(r_avg, g_avg, b_avg) > 235:
        return (255, 255, 255)
    return (int(r_avg), int(g_avg), int(b_avg))


def remove_bg_white_floodfill(im: Image.Image, tol: float = 30.0) -> Image.Image:
    """Border-connected flood-fill alpha extraction for pure solid white (#FFFFFF) backdrops.
    Guarantees zero hole punching into interior white document memos, statements, or paper.
    """
    w, h = im.size
    pixels = im.load()
    visited = bytearray(w * h)
    queue = []

    # Seed BFS from all 4 image borders
    for x in range(w):
        r, g, b, _ = pixels[x, 0]
        if min(r, g, b) >= 255 - tol:
            visited[x] = 1
            queue.append((x, 0))
        r, g, b, _ = pixels[x, h - 1]
        if min(r, g, b) >= 255 - tol:
            visited[(h - 1) * w + x] = 1
            queue.append((x, h - 1))

    for y in range(h):
        r, g, b, _ = pixels[0, y]
        if min(r, g, b) >= 255 - tol:
            visited[y * w] = 1
            queue.append((0, y))
        r, g, b, _ = pixels[w - 1, y]
        if min(r, g, b) >= 255 - tol:
            visited[y * w + (w - 1)] = 1
            queue.append((w - 1, y))

    # BFS traversal
    head = 0
    while head < len(queue):
        cx, cy = queue[head]
        head += 1
        for nx, ny in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
            if 0 <= nx < w and 0 <= ny < h:
                idx = ny * w + nx
                if not visited[idx]:
                    r, g, b, _ = pixels[nx, ny]
                    if min(r, g, b) >= 255 - tol:
                        visited[idx] = 1
                        queue.append((nx, ny))

    # Apply alpha: border-connected exterior pixels -> transparent (alpha 0)
    for y in range(h):
        for x in range(w):
            if visited[y * w + x]:
                r, g, b, _ = pixels[x, y]
                pixels[x, y] = (r, g, b, 0)

    return im


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

    # Special handling for pure solid white (#FFFFFF) backdrops (Rule 120 / B4 Evidence Isolation)
    if min(br, bgc, bb) >= 235:
        white_tol = tol if tol < 50 else 30.0
        im = remove_bg_white_floodfill(im, tol=white_tol)
        im.save(dst_path, "PNG")
        return dst_path

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
