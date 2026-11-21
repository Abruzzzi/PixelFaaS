"""Shared PixelFaaS OpenFaaS handler for six image-processing operations.

Template: python3-http-debian
HTTP: POST raw JPEG/PNG/WebP bytes; options from URL query parameters.
Each OpenFaaS deployment selects its operation using OPERATION.
"""

import io
import logging
import math
import os

from flask import Response
from PIL import Image, ImageOps, UnidentifiedImageError

from .resize import resize_image
from .watermark import add_watermark
from .convert import convert_image
from .compress import compress_image
from .filter import apply_filter
from .crop import crop_image

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_PIXELS = 20_000_000
Image.MAX_IMAGE_PIXELS = MAX_PIXELS

MIME_TYPES = {
    "JPEG": "image/jpeg",
    "PNG": "image/png",
    "WEBP": "image/webp",
}
EXTENSIONS = {
    "JPEG": "jpg",
    "PNG": "png",
    "WEBP": "webp",
}
OPERATIONS = {"resize", "watermark", "convert", "compress", "filter", "crop"}


def error(message, status=400):
    """Return a JSON error response in the OpenFaaS HTTP template format."""
    return {
        "statusCode": status,
        "body": {"error": message},
        "headers": {"Content-Type": "application/json"},
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
        raise ValueError(f"{name} must be an integer") from exc


def query_float(query, name, default=None):
    raw = query.get(name)
    if raw is None:
        if default is not None:
            return default
        raise ValueError(f"Missing parameter: {name}")
    try:
        value = float(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a number") from exc
    if not math.isfinite(value):
        raise ValueError(f"{name} must be a finite number")
    return value


def handle(event, context):
    """Process an uploaded image based on the function's OPERATION setting."""
    if event.method != "POST":
        result = error("Use POST with raw image bytes", 405)
        result["headers"]["Allow"] = "POST"
        return result

    operation = os.getenv("OPERATION", "").strip().lower()
    if operation not in OPERATIONS:
        return error("Server configuration error: invalid OPERATION", 500)

    data = event.body
    if not isinstance(data, (bytes, bytearray)) or not data:
        return error("Upload a JPEG, PNG, or WebP image as raw bytes")
    if len(data) > MAX_UPLOAD_BYTES:
        return error("Image upload exceeds 10 MB", 413)

    try:
        with Image.open(io.BytesIO(data)) as source:
            original_format = source.format
            if original_format not in MIME_TYPES:
                raise ValueError("Input must be JPEG, PNG, or WebP")
            if source.width * source.height > MAX_PIXELS:
                return error("Image exceeds 20 megapixels", 413)

            source.load()
            # Apply EXIF orientation before using dimensions or crop percentages.
            image = ImageOps.exif_transpose(source)
            params = event.query or {}
            output_format = original_format

            if operation == "resize":
                mode = params.get("mode", "scale").lower()
                if mode == "scale":
                    scale = query_float(params, "scale", default=1.0)
                    if not 0 < scale <= 10:
                        raise ValueError("scale must be greater than 0 and at most 10")
                    target_w = max(1, round(image.width * scale))
                    target_h = max(1, round(image.height * scale))
                    if target_w * target_h > MAX_PIXELS:
                        raise ValueError("Resized image exceeds 20 megapixels")
                    result = resize_image(image, "scale", scale=scale)

                elif mode == "dimensions":
                    width = query_int(params, "width")
                    height = query_int(params, "height")
                    if width <= 0 or height <= 0 or width * height > MAX_PIXELS:
                        raise ValueError("Width and height must be positive and total at most 20 megapixels")
                    result = resize_image(image, "dimensions", width=width, height=height)
                else:
                    raise ValueError("mode must be scale or dimensions")
                result_bytes = convert_image(result, original_format, quality=95)

            elif operation == "watermark":
                text = params.get("text", "")
                if len(text) > 200:
                    raise ValueError("Watermark text must be at most 200 characters")
                position = params.get("position", "bottom-right")
                opacity = query_int(params, "opacity", default=60)
                font_size = (query_int(params, "font_size")
                             if params.get("font_size") is not None else None)
                if font_size is not None and not 1 <= font_size <= 500:
                    raise ValueError("font_size must be between 1 and 500")
                result = add_watermark(image, text, position, opacity, font_size)
                result_bytes = convert_image(result, original_format, quality=95)

            elif operation == "convert":
                requested = params.get("format", "").lower()
                if requested not in ("jpg", "jpeg", "png", "webp"):
                    raise ValueError("format must be jpeg, png, or webp")
                output_format = "JPEG" if requested in ("jpg", "jpeg") else requested.upper()
                quality = query_int(params, "quality", default=90)
                result_bytes = convert_image(image, output_format, quality=quality)

            elif operation == "compress":
                quality = query_int(params, "quality", default=80)
                result_bytes = compress_image(image, original_format, quality=quality)

            elif operation == "filter":
                filter_name = params.get("filter", "grayscale")
                radius = query_float(params, "radius", default=2.0)
                strength = query_float(params, "strength", default=2.0)
                result = apply_filter(image, filter_name, radius=radius, strength=strength)
                result_bytes = convert_image(result, original_format, quality=95)

            else:  # crop
                mode = params.get("mode", "preset").lower()
                if mode == "preset":
                    result = crop_image(image, mode="preset", ratio=params.get("ratio", "1:1"))
                elif mode == "custom":
                    coordinates = {
                        name: query_float(params, name)
                        for name in ("left", "top", "right", "bottom")
                    }
                    result = crop_image(image, mode="custom", **coordinates)
                else:
                    raise ValueError("mode must be preset or custom")
                result_bytes = convert_image(result, original_format, quality=95)

        extension = EXTENSIONS[output_format]
        return Response(
            result_bytes,
            status=200,
            mimetype=MIME_TYPES[output_format],
            headers={
                "Content-Disposition": f'attachment; filename="{operation}.{extension}"',
                "Cache-Control": "no-store",
            },
        )

    except (ValueError, TypeError, UnidentifiedImageError, Image.DecompressionBombError) as exc:
        return error(str(exc), 400)
    except OSError:
        return error("Cannot read or encode the uploaded image", 400)
    except Exception:
        logging.exception("Unexpected image processing error")
        return error("Image processing failed", 500)
