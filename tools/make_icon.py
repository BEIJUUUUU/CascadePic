"""Generate the application icon (packaging/icon.ico) with Pillow."""

from pathlib import Path

from PIL import Image, ImageDraw

SIZES = [16, 24, 32, 48, 64, 128, 256]


def _gradient(size: int) -> Image.Image:
    image = Image.new("RGB", (size, size))
    pixels = image.load()
    top = (96, 165, 250)
    bottom = (29, 78, 216)
    for y in range(size):
        ratio = y / max(1, size - 1)
        color = tuple(round(a + (b - a) * ratio) for a, b in zip(top, bottom, strict=True))
        for x in range(size):
            pixels[x, y] = color
    return image


def _rounded(image: Image.Image, radius_ratio: float = 0.24) -> Image.Image:
    size = image.size[0]
    radius = max(1, round(size * radius_ratio))
    mask = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle((0, 0, size - 1, size - 1), radius=radius, fill=255)
    result = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    result.paste(image, (0, 0), mask)
    return result


def _waterfall_bars(size: int) -> Image.Image:
    base = _rounded(_gradient(size))
    draw = ImageDraw.Draw(base)
    white = (247, 250, 255, 235)
    bar_width = max(2, size // 12)
    gap = max(2, size // 9)
    margin = max(3, round(size * 0.18))
    heights = [0.55, 0.8, 0.62, 0.42]
    for index, height_ratio in enumerate(heights):
        x = margin + index * (bar_width + gap)
        top = round(size * (1 - margin / size - height_ratio * 0.66))
        bottom = size - margin
        draw.rounded_rectangle((x, top, x + bar_width, bottom), radius=bar_width // 2, fill=white)
    return base


def main() -> None:
    output = Path(__file__).resolve().parent.parent / "packaging" / "icon.ico"
    source = _waterfall_bars(max(SIZES))
    source.save(output, format="ICO", sizes=[(s, s) for s in SIZES])
    print(f"wrote {output} ({len(SIZES)} sizes)")


if __name__ == "__main__":
    main()
