import hashlib

from django.conf import settings
from rest_framework.exceptions import ValidationError

from apps.core.file_validation import normalize_extension, validate_file_upload


FILE_TYPES = {"pdf": "application/pdf", "jpg": "image/jpeg", "jpeg": "image/jpeg",
              "png": "image/png", "webp": "image/webp"}


def checked_upload(uploaded_file):
    extension = normalize_extension(getattr(uploaded_file, "name", ""))
    content_type = FILE_TYPES.get(extension)
    if content_type is None or getattr(uploaded_file, "content_type", None) != content_type:
        raise ValidationError({"file": "Choose a supported file with a matching content type."})
    validate_file_upload(uploaded_file, allowed_extensions=FILE_TYPES,
                         allowed_content_types=set(FILE_TYPES.values()))
    if extension == "webp":
        uploaded_file.seek(0)
        header = uploaded_file.read(12)
        if len(header) != 12 or header[8:] != b"WEBP":
            raise ValidationError({"file": "File content does not match its type."})
    uploaded_file.seek(0)
    digest, size = hashlib.sha256(), 0
    for chunk in uploaded_file.chunks(64 * 1024):
        size += len(chunk)
        if size > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
            raise ValidationError({"file": "File exceeds the configured size limit."})
        digest.update(chunk)
    if size == 0 or size != uploaded_file.size:
        raise ValidationError({"file": "File size could not be verified."})
    uploaded_file.seek(0)
    return extension, content_type, digest.hexdigest(), size
