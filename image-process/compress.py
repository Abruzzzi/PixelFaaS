
"""Compress images using Pillow."""

import argparse
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageOps


SUPPORTED_FORMATS = {
    "JPEG": {".jpg", ".jpeg"},
    "PNG": {".png"},
    "WEBP": {".webp"},
}


def compress_image(image, image_format, quality=80):
    """
    Return compressed image bytes.

    JPEG/WebP: lossy compression using quality (1-95).
    PNG: lossless compression with optimization.
    """

    image_format = image_format.upper()

    if image_format not in SUPPORTED_FORMATS:
        raise ValueError(
            "Only JPEG, PNG, and WebP are supported."
        )

    if not isinstance(quality, int) or not 1 <= quality <= 95:
        raise ValueError(
            "Quality must be an integer between 1 and 95."
        )

    output = BytesIO()

    if image_format == "JPEG":

        # JPEG does not support transparency.
        if (
            image.mode in ("RGBA", "LA")
            or "transparency" in image.info
        ):
            rgba = image.convert("RGBA")
            white = Image.new("RGB", rgba.size, "white")
            white.paste(
                rgba,
                mask=rgba.getchannel("A")
            )
            image = white

        elif image.mode not in ("RGB", "L"):
            image = image.convert("RGB")

        image.save(
            output,
            format="JPEG",
            quality=quality,
            optimize=True,
            progressive=True
        )

    elif image_format == "PNG":

        # Lossless optimization
        image.save(
            output,
            format="PNG",
            optimize=True
        )

    elif image_format == "WEBP":

        image.save(
            output,
            format="WEBP",
            quality=quality,
            method=6
        )

    return output.getvalue()


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description="Compress an image using Pillow"
    )

    parser.add_argument("input")
    parser.add_argument("output")
    parser.add_argument(
        "--quality",
        type=int,
        default=80,
        help="JPEG/WebP quality (1-95); ignored for PNG"
    )

    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)

    with Image.open(input_path) as source:

        image_format = source.format

        if image_format not in SUPPORTED_FORMATS:
            parser.error(
                "Input must be JPEG, PNG, or WebP."
            )

        if output_path.suffix.lower() not in SUPPORTED_FORMATS[image_format]:
            parser.error(
                "Output extension must match input format."
            )

        image = ImageOps.exif_transpose(source)

        result = compress_image(
            image,
            image_format,
            quality=args.quality
        )

    original_size = input_path.stat().st_size

    output_path.write_bytes(result)

    compressed_size = len(result)

    reduction = (
        (original_size - compressed_size)
        / original_size * 100
    )

    print(f"Saved: {output_path}")
    print(f"Original size: {original_size:,} bytes")
    print(f"Output size: {compressed_size:,} bytes")
    print(f"Size change: {reduction:.1f}% reduction")

