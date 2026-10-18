"""Private local photos: actual format validation, <=5 MiB, <=24 million pixels.

Normalize JPEG/PNG/WebP to metadata-free PNG. Paths are server generated and
always resolved within PRIVATE_MEDIA_ROOT. Never expose this root publicly.
"""
import io
import uuid
import warnings
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError
from django.conf import settings

from school_app.accounts.services import AccountError

MAX_PHOTO_BYTES = 5 * 1024 * 1024
MAX_IMAGE_PIXELS = 24_000_000
ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}


def normalize_photo(upload):
    if upload is None or upload.size > MAX_PHOTO_BYTES:
        raise AccountError("VALIDATION_ERROR", "Photo must be at most 5 MiB.", 422)
    raw = upload.read(MAX_PHOTO_BYTES + 1)
    if len(raw) > MAX_PHOTO_BYTES:
        raise AccountError("VALIDATION_ERROR", "Photo must be at most 5 MiB.", 422)
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(raw)) as image:
                if image.format not in ALLOWED_FORMATS or image.width * image.height > MAX_IMAGE_PIXELS:
                    raise ValueError("Unsupported image or excessive pixels")
                image.verify()
            with Image.open(io.BytesIO(raw)) as image:
                image.load()
                image = ImageOps.exif_transpose(image)
                mode = "RGBA" if "A" in image.getbands() else "RGB"
                converted = image.convert(mode)
                # A fresh image drops EXIF, comments, ICC and other source metadata.
                clean = Image.frombytes(mode, converted.size, converted.tobytes())
                output = io.BytesIO()
                clean.save(output, format="PNG")
                return output.getvalue()
    except (UnidentifiedImageError, OSError, ValueError, SyntaxError,
            Image.DecompressionBombWarning, Image.DecompressionBombError):
        raise AccountError("VALIDATION_ERROR", "Upload a valid JPEG, PNG or WebP within the pixel limit.", 422) from None


def photo_file(relative):
    root = Path(settings.PRIVATE_MEDIA_ROOT).resolve()
    target = (root / relative).resolve()
    if target == root or not target.is_relative_to(root):
        raise AccountError("NOT_FOUND", "Photo was not found.", 404)
    return target


def store_photo(student_id, normalized):
    relative = f"students/{student_id}/{uuid.uuid4().hex}.png"
    target = photo_file(relative)
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        with target.open("xb") as handle:
            handle.write(normalized)
    except Exception:
        target.unlink(missing_ok=True)
        raise
    return relative


def remove_photo(relative):
    photo_file(relative).unlink(missing_ok=True)
