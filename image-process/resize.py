
from PIL import Image, ImageOps
import argparse


def resize_image(image, mode, scale=None, width=None, height=None):
    """
    Resize an image using one of two modes:

    1. scale: Resize proportionally by a scale factor.
    2. dimensions: Resize to the specified width and height.
    """

    original_width, original_height = image.size

    if mode == "scale":
        if scale is None or scale <= 0:
            raise ValueError("Scale must be greater than 0.")

        new_width = max(1, round(original_width * scale))
        new_height = max(1, round(original_height * scale))

    elif mode == "dimensions":
        if width is None or height is None:
            raise ValueError("Width and height are required.")

        if width <= 0 or height <= 0:
            raise ValueError("Width and height must be positive.")

        new_width = width
        new_height = height

    else:
        raise ValueError("Invalid resize mode.")

    resized = image.resize(
        (new_width, new_height),
        Image.Resampling.LANCZOS
    )

    return resized


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument("input")
    parser.add_argument("output")
    parser.add_argument(
        "--mode",
        required=True,
        choices=["scale", "dimensions"]
    )
    parser.add_argument("--scale", type=float)
    parser.add_argument("--width", type=int)
    parser.add_argument("--height", type=int)

    args = parser.parse_args()

    with Image.open(args.input) as image:
        image = ImageOps.exif_transpose(image)
        original_size = image.size

        result = resize_image(
            image,
            mode=args.mode,
            scale=args.scale,
            width=args.width,
            height=args.height
        )

        # JPEG does not support transparency
        if args.output.lower().endswith((".jpg", ".jpeg")):
            result = result.convert("RGB")

        result.save(args.output)

        print("Original size:", original_size)
        print("New size:", result.size)
        print("Saved to:", args.output)

