"""Own-account avatar normalization. Originals never persist or become public."""
from io import BytesIO
import math
import warnings

from PIL import Image, ImageOps, UnidentifiedImageError
from rest_framework.exceptions import ValidationError
from apps.core.domain_errors import TemporaryServiceFailure

from apps.core.antivirus import ScanUnavailable, scan_stream
from .models import UserAvatar

MAX_BYTES = 5 * 1024 * 1024
MAX_PIXELS = 16_000_000


class AvatarScannerUnavailable(TemporaryServiceFailure):
    status_code = 503
    default_detail = "File scanning is temporarily unavailable. Try again later."
    default_code = "scanner_unavailable"


def save_avatar(user, upload, crop=None):
    if upload is None or upload.size > MAX_BYTES:
        raise ValidationError({"file": "Choose a JPG, PNG or WebP image up to 5 MB."})
    raw = upload.read(MAX_BYTES + 1)
    if not raw or len(raw) > MAX_BYTES:
        raise ValidationError({"file": "Choose a JPG, PNG or WebP image up to 5 MB."})
    try:
        result = scan_stream(BytesIO(raw))
    except ScanUnavailable:
        raise AvatarScannerUnavailable() from None
    if not result.clean:
        raise ValidationError({"file": "The file was blocked by the antivirus."})
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(raw)) as source:
                if source.format not in {"JPEG", "PNG", "WEBP"} or source.width * source.height > MAX_PIXELS or getattr(source, "n_frames", 1) != 1:
                    raise ValueError("Unsupported image")
                source.load()
                oriented = ImageOps.exif_transpose(source)
                if crop is not None:
                    x, y, size = crop
                    side = size * min(oriented.size)
                    left, top = x * oriented.width, y * oriented.height
                    if not all(math.isfinite(value) for value in crop) or side < 1 or left < 0 or top < 0 or left + side > oriented.width + 0.01 or top + side > oriented.height + 0.01:
                        raise ValueError("Invalid crop")
                    oriented = oriented.crop((left, top, left + side, top + side))
                rgba = ImageOps.fit(oriented.convert("RGBA"), (256, 256), method=Image.Resampling.LANCZOS)
                # Fresh canvas drops EXIF, GPS, profiles and any appended source bytes.
                canvas = Image.new("RGB", (256, 256), "white")
                canvas.paste(rgba, mask=rgba.getchannel("A"))
                output = BytesIO()
                canvas.save(output, format="JPEG", quality=85, optimize=True)
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise ValidationError({"file": "Choose a valid, non-animated JPG, PNG or WebP image (up to 16 megapixels)."}) from None
    data = output.getvalue()
    if len(data) > 128 * 1024:
        raise ValidationError({"file": "Image could not be resized. Choose another image."})
    avatar, _ = UserAvatar.objects.update_or_create(user=user, defaults={"image": data})
    return avatar
