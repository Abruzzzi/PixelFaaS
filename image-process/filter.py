
import math

from PIL import Image, ImageEnhance, ImageFilter, ImageOps

FILTER_CHOICES = (
    "grayscale",
    "blur",
    "sharpen",
    "edges",
    "emboss",
    "sepia",
    "invert",
    "vivid",
)


def apply_filter(image, filter_name, radius=2.0, strength=2.0):
    """
    Apply a selected image filter.

    radius: Gaussian blur radius (0-20).
    strength: Sharpness or saturation factor (0-5).
              A value of 1.0 means unchanged.
    """

    filter_name = filter_name.strip().lower()

    if filter_name not in FILTER_CHOICES:
        raise ValueError("Invalid filter choice.")

    if not math.isfinite(radius) or not 0 <= radius <= 20:
        raise ValueError("radius must be between 0 and 20")

    if not math.isfinite(strength) or not 0 <= strength <= 5:
        raise ValueError("strength must be between 0 and 5")

    # Correct orientation and preserve transparency
    base = ImageOps.exif_transpose(image).convert("RGBA")
    alpha = base.getchannel("A")
    rgb = base.convert("RGB")

    if filter_name == "grayscale":
        result = ImageOps.grayscale(rgb).convert("RGB")

    elif filter_name == "blur":
        result = rgb.filter(
            ImageFilter.GaussianBlur(radius=radius)
        )

    elif filter_name == "sharpen":
        result = ImageEnhance.Sharpness(rgb).enhance(strength)

    elif filter_name == "edges":
        result = rgb.filter(ImageFilter.FIND_EDGES)

    elif filter_name == "emboss":
        result = rgb.filter(ImageFilter.EMBOSS)

    elif filter_name == "sepia":
        gray = ImageOps.grayscale(rgb)
        result = ImageOps.colorize(
            gray,
            black="#382315",
            white="#F3DFC1"
        )

    elif filter_name == "invert":
        result = ImageOps.invert(rgb)

    elif filter_name == "vivid":
        result = ImageEnhance.Color(rgb).enhance(strength)

    # Restore original transparency
    result = result.convert("RGBA")
    result.putalpha(alpha)

    return result


if __name__ == "__main__":
    import argparse
    from pathlib import Path

    parser = argparse.ArgumentParser(
        description="Apply an image filter using Pillow"
    )

    parser.add_argument("input", help="Input image path")
    parser.add_argument("output", help="Output image path")

    parser.add_argument(
        "--filter",
        required=True,
        choices=FILTER_CHOICES
    )

    parser.add_argument(
        "--radius",
        type=float,
        default=2.0,
        help="Blur radius (0-20)"
    )

    parser.add_argument(
        "--strength",
        type=float,
        default=2.0,
        help="Sharpen or vivid strength (0-5)"
    )

    args = parser.parse_args()

    # Open the input image
    with Image.open(args.input) as image:
        original_format = image.format

        # Apply the selected filter
        result = apply_filter(
            image,
            filter_name=args.filter,
            radius=args.radius,
            strength=args.strength
        )

    # Preserve the original image format
    formats = {
        "JPEG": (".jpg", ".jpeg"),
        "PNG": (".png",),
        "WEBP": (".webp",)
    }

    if original_format not in formats:
        parser.error("Input must be JPEG, PNG, or WebP.")

    if Path(args.output).suffix.lower() not in formats[original_format]:
        parser.error("Output extension must match input format.")

    if original_format == "JPEG":
        result.convert("RGB").save(
            args.output,
            format="JPEG",
            quality=95
        )

    elif original_format == "PNG":
        result.save(args.output, format="PNG")

    elif original_format == "WEBP":
        result.save(
            args.output,
            format="WEBP",
            quality=95
        )

    print(f"Filtered image saved to {args.output}")
    print(f"Filter: {args.filter}")
    print(f"Image size: {result.width} x {result.height}")

