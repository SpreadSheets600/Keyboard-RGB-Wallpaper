import argparse
import colorsys
from PIL import Image
from pathlib import Path
from collections import Counter


def quantize_channel(x: int, step: int = 12):
    return max(0, min(255, round(x / step) * step))


def rgb_to_hsv(rgb: tuple[int, int, int]):
    r, g, b = rgb
    return colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)


def rgb_to_luma(rgb: tuple[int, int, int]):
    r, g, b = rgb
    return 0.2126 * (r / 255.0) + 0.7152 * (g / 255.0) + 0.0722 * (b / 255.0)


def color_distance(a: tuple[int, int, int], b: tuple[int, int, int]):
    return ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2) ** 0.5


def is_unusable(rgb: tuple[int, int, int]):
    h, s, v = rgb_to_hsv(rgb)
    l = rgb_to_luma(rgb)

    if v < 0.16:
        return True

    if l > 0.95 and s < 0.12:
        return True

    if s < 0.12:
        return True

    return False


def keyboard_score(
    rgb: tuple[int, int, int],
    count: int,
    avg_rgb: tuple[int, int, int],
):
    h, s, v = rgb_to_hsv(rgb)
    l = rgb_to_luma(rgb)
    contrast = color_distance(rgb, avg_rgb) / 255.0

    # Prefer colors that:
    # - appear enough to feel related to the wallpaper
    # - are saturated enough to look good on LEDs
    # - are bright enough to be visible
    # - stand out from the average image color
    # - are not too close to white or black
    pop_score = count**0.85
    sat_score = 0.3 + (s * 2.4)
    bright_score = 0.4 + (v * 1.8)
    contrast_score = 0.6 + (contrast * 1.8)
    luma_penalty = 1.0 - abs(l - 0.60) * 0.7

    return (
        pop_score * sat_score * bright_score * contrast_score * max(0.35, luma_penalty)
    )


def brighten_for_keyboard(rgb: tuple[int, int, int]):
    h, s, v = rgb_to_hsv(rgb)

    s = min(1.0, max(0.72, s * 1.18))
    v = min(0.98, max(0.78, v * 1.15))

    r, g, b = colorsys.hsv_to_rgb(h, s, v)
    return round(r * 255), round(g * 255), round(b * 255)


def weighted_average(pixels: list[tuple[int, int, int]]):
    n = max(1, len(pixels))
    return (
        sum(p[0] for p in pixels) // n,
        sum(p[1] for p in pixels) // n,
        sum(p[2] for p in pixels) // n,
    )


def merge_similar_colors(
    counts: Counter[tuple[int, int, int]],
    threshold: float = 28.0,
):
    merged: list[list[object]] = []

    for rgb, count in counts.most_common():
        placed = False
        for item in merged:
            existing_rgb = item[0]
            if color_distance(rgb, existing_rgb) <= threshold:
                total = item[1] + count
                nr = round((existing_rgb[0] * item[1] + rgb[0] * count) / total)
                ng = round((existing_rgb[1] * item[1] + rgb[1] * count) / total)
                nb = round((existing_rgb[2] * item[1] + rgb[2] * count) / total)
                item[0] = (nr, ng, nb)
                item[1] = total
                placed = True
                break
        if not placed:
            merged.append([rgb, count])

    return [(item[0], item[1]) for item in merged]


def extract_keyboard_color(path: Path):
    img = Image.open(path).convert("RGB")
    img.thumbnail((320, 320))

    pixels = list(img.getdata())
    if not pixels:
        return (0, 200, 255)

    quantized = [
        (
            quantize_channel(r),
            quantize_channel(g),
            quantize_channel(b),
        )
        for r, g, b in pixels
    ]

    counts = Counter(quantized)
    avg_rgb = weighted_average(pixels)
    candidates = merge_similar_colors(counts)

    scored: list[tuple[float, tuple[int, int, int], int]] = []
    for rgb, count in candidates:
        if is_unusable(rgb):
            continue
        score = keyboard_score(rgb, count, avg_rgb)
        scored.append((score, rgb, count))

    if not scored:
        return brighten_for_keyboard(avg_rgb)

    scored.sort(reverse=True, key=lambda x: x[0])

    best_score, best_rgb, _ = scored[0]

    for score, rgb, _ in scored[1:5]:
        h1, s1, v1 = rgb_to_hsv(best_rgb)
        h2, s2, v2 = rgb_to_hsv(rgb)

        if score >= best_score * 0.72 and s2 > s1 + 0.18 and v2 > 0.35:
            best_rgb = rgb
            best_score = score
            break

    return brighten_for_keyboard(best_rgb)


def to_hex(rgb: tuple[int, int, int]):
    return "#{:02x}{:02x}{:02x}".format(*rgb)


def main():
    parser = argparse.ArgumentParser(
        description="Extract a dominant wallpaper color that looks good on an RGB keyboard"
    )
    parser.add_argument("image", type=Path)
    parser.add_argument("--format", choices=("hex", "rgb"), default="hex")
    args = parser.parse_args()

    rgb = extract_keyboard_color(args.image)

    if args.format == "rgb":
        print(rgb[0], rgb[1], rgb[2])
    else:
        print(to_hex(rgb))


if __name__ == "__main__":
    main()
