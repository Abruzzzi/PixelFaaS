"""Add a customizable text watermark to an image using Pillow."""

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps


POSITIONS = ("bottom-right", "top-left", "center")


def add_watermark(image, text, position="bottom-right", opacity=60, font_size=None):
    """Return a Pillow image with a semi-transparent text watermark.

    opacity is a percentage from 0 (invisible) to 100 (opaque).
    """
    if not text.strip():
        raise ValueError("Watermark text cannot be empty.")
    if position not in POSITIONS:
        raise ValueError(f"Position must be one of: {', '.join(POSITIONS)}")
    if not 0 <= opacity <= 100:
        raise ValueError("Opacity must be between 0 and 100.")

    base = ImageOps.exif_transpose(image).convert("RGBA")
    width, height = base.size
    margin = max(4, round(min(width, height) * 0.025))
    size = font_size if font_size is not None else max(12, round(min(width, height) * 0.05))
    if size <= 0:
        raise ValueError("Font size must be positive.")

    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)

    # Shrink text when necessary to fit inside the image.
    while True:
        font = ImageFont.load_default(size=size)
        left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
        text_width, text_height = right - left, bottom - top
        if (text_width <= width - 2 * margin and text_height <= height - 2 * margin) or size <= 8:
            break
        size = max(8, size - 2)

    if position == "bottom-right":
        x, y = width - margin - right, height - margin - bottom
    elif position == "top-left":
        x, y = margin - left, margin - top
    else:
        x = (width - text_width) // 2 - left
        y = (height - text_height) // 2 - top

    alpha = round(255 * opacity / 100)
    draw.text(
        (x, y),
        text,
        font=font,
        fill=(255, 255, 255, alpha),
        stroke_width=max(1, size // 28),
        stroke_fill=(0, 0, 0, round(alpha * 0.75)),
    )
    return Image.alpha_composite(base, layer)


def save_image(image, input_path, output_path):
    """Save the watermarked image in the same format as the original input image."""

    # Get the original image format
    input_suffix = Path(input_path).suffix.lower()
    output_path = Path(output_path).with_suffix(input_suffix)
    if input_suffix in (".jpg", ".jpeg"):
        # JPEG doesn't support transparency
        image = image.convert("RGBA")
        white = Image.new("RGB", image.size, "white")
        white.paste(image, mask=image.getchannel("A"))
        white.save(output_path, quality=95)
    elif input_suffix == ".png":
        image.save(output_path, format="PNG")
    elif input_suffix == ".webp":
        image.save(output_path, format="WEBP", quality=95)
    else:
        raise ValueError("Output filename must end in .png, .jpg, .jpeg, or .webp")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Add a text watermark to an image")
    parser.add_argument("input", help="Input image path")
    parser.add_argument("output", help="Output image path (.png, .jpg, or .webp)")
    parser.add_argument("--text", required=True, help="Watermark text")
    parser.add_argument("--position", choices=POSITIONS, default="bottom-right")
    parser.add_argument("--opacity", type=int, default=60, help="0-100 (default: 60)")
    parser.add_argument("--font-size", type=int, default=None, help="Font size in pixels")
    args = parser.parse_args()

    with Image.open(args.input) as source:  
        result = add_watermark(source, args.text, args.position, args.opacity, args.font_size)
        saved_path = save_image(result, args.input, args.output)
    print(f"Watermarked image saved to {args.output}")