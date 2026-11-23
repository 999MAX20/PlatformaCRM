from django.conf import settings
from django.core.files.uploadhandler import MemoryFileUploadHandler
from rest_framework.exceptions import ValidationError

from apps.core.domain_errors import DomainAPIException


class MedicalUploadTooLarge(DomainAPIException):
    status_code = 413
    error_code = "medical_file_too_large"
    default_detail = "File exceeds the configured size limit."


class MedicalMemoryUploadHandler(MemoryFileUploadHandler):
    """Bounded uploads never spill clinical bytes into Django's temporary directory."""

    def __init__(self, request=None):
        super().__init__(request)
        self.received = 0
        self.files_seen = 0

    def handle_raw_input(self, input_data, META, content_length, boundary, encoding=None):
        self.activated = True

    def new_file(self, *args, **kwargs):
        self.files_seen += 1
        if self.files_seen > 1:
            raise ValidationError({"file": "Upload one medical file per request."})
        return super().new_file(*args, **kwargs)

    def receive_data_chunk(self, raw_data, start):
        self.received += len(raw_data)
        if self.received > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
            self.file.close()
            raise MedicalUploadTooLarge()
        return super().receive_data_chunk(raw_data, start)
