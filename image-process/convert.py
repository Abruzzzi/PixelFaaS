import argparse
from io import BytesIO

from PIL import Image, ImageOps


FORMATS = {"jpg": "JPEG", "jpeg": "JPEG", "png": "PNG", "webp": "WEBP"}


def convert_image(image, output_format="PNG", quality=90):
    """Return encoded image bytes in the selected output format.

    JPEG cannot store transparency, so transparent pixels are flattened onto white.
    The quality setting is used for JPEG/WebP, not PNG.
    """
    fmt = FORMATS.get(output_format.lower())
    if fmt is None:
        raise ValueError("Output format must be JPEG, PNG, or WebP.")
    if not 1 <= quality <= 95:
        raise ValueError("Quality must be between 1 and 95.")

    corrected = ImageOps.exif_transpose(image)
    # Retain transparency for PNG/WebP, when present in source.
    has_alpha = "A" in corrected.getbands() or "transparency" in corrected.info
    rgba_or_rgb = corrected.convert("RGBA" if has_alpha else "RGB")

    if fmt == "JPEG" and has_alpha:
        background = Image.new("RGB", corrected.size, "white")
        background.paste(rgba_or_rgb, mask=rgba_or_rgb.getchannel("A"))
        output_image = background
    else:
        output_image = rgba_or_rgb

    output = BytesIO()
    save_options = {"format": fmt}
    if fmt == "JPEG":
        save_options.update(quality=quality, optimize=True)
    elif fmt == "WEBP":
        save_options.update(quality=quality)
    else:
        save_options.update(optimize=True)
    output_image.save(output, **save_options)
    return output.getvalue()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert JPEG, PNG, or WebP images")
    parser.add_argument("input", help="Input image path")
    parser.add_argument("output", help="Output image path")
    parser.add_argument("--format", choices=["jpeg", "png", "webp"], required=True)
    parser.add_argument("--quality", type=int, default=90, help="JPEG/WebP quality: 1-95")
    args = parser.parse_args()

    extension_format = {".jpg": "JPEG", ".jpeg": "JPEG", ".png": "PNG", ".webp": "WEBP"}
    from pathlib import Path
    if extension_format.get(Path(args.output).suffix.lower()) != args.format.upper().replace("JPG", "JPEG"):
        parser.error("Output extension must match --format (e.g. output.webp for --format webp)")

    with Image.open(args.input) as source:
        data = convert_image(source, output_format=args.format, quality=args.quality)
    with open(args.output, "wb") as file:
        file.write(data)
    print(f"Converted image saved to {args.output} ({len(data):,} bytes)")
