import os
import io
import math
import logging

from flask import Response
from PIL import Image, ImageOps, UnidentifiedImageError

from .resize import resize_image
from .watermark import add_watermark
from .convert import convert_image


MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_PIXELS = 20_000_000

Image.MAX_IMAGE_PIXELS = MAX_PIXELS

MIME_TYPES = {
    "JPEG": "image/jpeg",
    "PNG": "image/png",
    "WEBP": "image/webp"
}

EXTENSIONS = {
    "JPEG": "jpg",
    "PNG": "png",
    "WEBP": "webp"
}


def error(message, status=400):
    return {
        "statusCode": status,
        "body": {"error": message}
    }


def query_int(query, name, default=None):
    raw = query.get(name)

    if raw is None:
        if default is not None:
            return default
        raise ValueError(f"Missing parameter: {name}")

    try:
        return int(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"{name} must be an integer"
        ) from exc


def handle(event, context):

    # Only accept HTTP POST requests
    if event.method != "POST":
        return {
            "statusCode": 405,
            "body": {
                "error": "Use POST with raw image bytes"
            },
            "headers": {"Allow": "POST"}
        }

    # Select the operation configured in stack.yml
    operation = os.getenv("OPERATION", "").lower()

    if operation not in ("resize", "watermark", "convert"):
        return error(
            "Server configuration error: invalid OPERATION",
            500
        )

    # Read the uploaded image
    data = event.body

    if not isinstance(data, bytes) or not data:
        return error("Upload a JPEG, PNG, or WebP image")

    if len(data) > MAX_UPLOAD_BYTES:
        return error("Image upload exceeds 10 MB", 413)

    try:
        with Image.open(io.BytesIO(data)) as source:

            original_format = source.format

            if original_format not in MIME_TYPES:
                raise ValueError(
                    "Input must be JPEG, PNG, or WebP"
                )

            if source.width * source.height > MAX_PIXELS:
                return error(
                    "Image exceeds 20 megapixels", 413
                )

            source.load()
            params = event.query

            # -----------------------------------
            # 1. RESIZE
            # -----------------------------------
            if operation == "resize":

                mode = params.get("mode", "scale").lower()

                if mode == "scale":
                    scale = float(
                        params.get("scale", "1.0")
                    )

                    if not math.isfinite(scale) or not 0 < scale <= 10:
                        raise ValueError(
                            "scale must be greater than 0 "
                            "and at most 10"
                        )

                    target_width = max(
                        1, round(source.width * scale)
                    )
                    target_height = max(
                        1, round(source.height * scale)
                    )

                    if target_width * target_height > MAX_PIXELS:
                        raise ValueError(
                            "Resized image exceeds 20 megapixels"
                        )

                    result = resize_image(
                        ImageOps.exif_transpose(source),
                        "scale",
                        scale=scale
                    )

                elif mode == "dimensions":
                    width = query_int(params, "width")
                    height = query_int(params, "height")

                    if (
                        width <= 0
                        or height <= 0
                        or width * height > MAX_PIXELS
                    ):
                        raise ValueError(
                            "Width and height must be positive "
                            "and <= 20 megapixels total"
                        )

                    result = resize_image(
                        ImageOps.exif_transpose(source),
                        "dimensions",
                        width=width,
                        height=height
                    )

                else:
                    raise ValueError(
                        "mode must be scale or dimensions"
                    )

                # Preserve original image format
                output_format = original_format

                result_bytes = convert_image(
                    result, output_format, quality=95
                )

            # -----------------------------------
            # 2. WATERMARK
            # -----------------------------------
            elif operation == "watermark":

                text = params.get("text", "")

                if len(text) > 200:
                    raise ValueError(
                        "Watermark text is too long"
                    )

                position = params.get(
                    "position", "bottom-right"
                )
                opacity = query_int(
                    params, "opacity", default=60
                )

                raw_font_size = params.get("font_size")
                font_size = (
                    query_int(params, "font_size")
                    if raw_font_size is not None
                    else None
                )

                if font_size is not None and not 1 <= font_size <= 500:
                    raise ValueError(
                        "font_size must be between 1 and 500"
                    )

                result = add_watermark(
                    source,
                    text,
                    position,
                    opacity,
                    font_size
                )

                # Preserve original image format
                output_format = original_format

                result_bytes = convert_image(
                    result, output_format, quality=95
                )

            # -----------------------------------
            # 3. FORMAT CONVERSION
            # -----------------------------------
            else:

                requested_format = params.get(
                    "format", ""
                ).lower()

                if requested_format not in (
                    "jpg", "jpeg", "png", "webp"
                ):
                    raise ValueError(
                        "format must be jpeg, png, or webp"
                    )

                output_format = (
                    "JPEG"
                    if requested_format in ("jpg", "jpeg")
                    else requested_format.upper()
                )

                quality = query_int(
                    params, "quality", default=90
                )

                result_bytes = convert_image(
                    source,
                    output_format,
                    quality=quality
                )

        # -----------------------------------
        # 4. RETURN PROCESSED IMAGE
        # -----------------------------------
        extension = EXTENSIONS[output_format]

        return Response(
            result_bytes,
            status=200,
            mimetype=MIME_TYPES[output_format],
            headers={
                "Content-Disposition":
                    f'attachment; filename="{operation}.{extension}"',
                "Cache-Control": "no-store"
            }
        )

    except (
        ValueError,
        TypeError,
        UnidentifiedImageError,
        Image.DecompressionBombError
    ) as exc:
        return error(str(exc), 400)

    except OSError:
        return error(
            "Cannot read or encode the uploaded image",
            400
        )

    except Exception:
        logging.exception(
            "Unexpected image processing error"
        )
        return error("Image processing failed", 500)

