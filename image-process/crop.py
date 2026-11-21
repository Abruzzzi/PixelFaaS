
from PIL import Image, ImageOps

RATIOS = {
    "1:1": (1, 1),
    "4:3": (4, 3),
    "3:2": (3, 2),
    "16:9": (16, 9),
    "9:16": (9, 16),
}


def crop_image(image, mode="preset", ratio="1:1",
               *, left=None, top=None, right=None, bottom=None):

    base = ImageOps.exif_transpose(image)
    width, height = base.size

    if mode == "preset":
        if ratio not in RATIOS:
            raise ValueError("Invalid aspect ratio")

        rw, rh = RATIOS[ratio]
        target_ratio = rw / rh

        if width / height > target_ratio:
            crop_width = round(height * target_ratio)
            crop_height = height
        else:
            crop_width = width
            crop_height = round(width / target_ratio)

        crop_width = max(1, crop_width)
        crop_height = max(1, crop_height)

        x = (width - crop_width) // 2
        y = (height - crop_height) // 2

        box = (x, y, x + crop_width, y + crop_height)

    elif mode == "custom":
        if any(v is None for v in (left, top, right, bottom)):
            raise ValueError("Four crop coordinates are required")

        if not (0 <= left < right <= 100 and
                0 <= top < bottom <= 100):
            raise ValueError("Invalid crop percentages")

        box = (
            round(width * left / 100),
            round(height * top / 100),
            round(width * right / 100),
            round(height * bottom / 100)
        )

        if box[2] <= box[0] or box[3] <= box[1]:
            raise ValueError("Crop region is too small")

    else:
        raise ValueError("Mode must be preset or custom")

    return base.crop(box)


def main():
    import argparse
    from pathlib import Path

    parser = argparse.ArgumentParser(
        description="Crop an image using Pillow"
    )

    parser.add_argument("input", help="Input image path")
    parser.add_argument("output", help="Output image path")

    parser.add_argument(
        "--mode",
        required=True,
        choices=["preset", "custom"]
    )

    parser.add_argument(
        "--ratio",
        default="1:1",
        choices=RATIOS.keys(),
        help="Aspect ratio for preset mode"
    )

    parser.add_argument("--left", type=float)
    parser.add_argument("--top", type=float)
    parser.add_argument("--right", type=float)
    parser.add_argument("--bottom", type=float)

    args = parser.parse_args()

    # Open the input image
    with Image.open(args.input) as image:
        original_format = image.format

        # Apply cropping
        result = crop_image(
            image,
            mode=args.mode,
            ratio=args.ratio,
            left=args.left,
            top=args.top,
            right=args.right,
            bottom=args.bottom
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

    print(f"Cropped image saved to {args.output}")
    print(f"Crop mode: {args.mode}")
    print(f"Original format: {original_format}")
    print(f"New size: {result.width} x {result.height}")


if __name__ == "__main__":
    main()

