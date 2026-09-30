import base64
from io import BytesIO
from unittest.mock import patch

from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from PIL import Image
from rest_framework.test import APIClient

from apps.core.antivirus import ScanResult, ScanUnavailable
from .models import User, UserAvatar


class AvatarTests(TestCase):
    url = "/api/auth/me/avatar/"

    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(username="avatar", email="avatar@example.com", password="StrongPass123!")
        self.other = User.objects.create_user(username="other", email="other@example.com", password="StrongPass123!")
        self.api = APIClient()
        self.api.force_authenticate(self.user)
        self.scanner = patch("apps.accounts.avatars.scan_stream", return_value=ScanResult(True, "hash", 1, "test"))
        self.scan = self.scanner.start()
        self.addCleanup(self.scanner.stop)

    def file(self, format="PNG", size=(400, 300)):
        output = BytesIO()
        Image.new("RGB", size, "red").save(output, format=format)
        return SimpleUploadedFile("avatar.png", output.getvalue(), content_type="image/png")

    def test_upload_persist_replace_remove_and_strip_metadata(self):
        response = self.api.post(self.url, {"file": self.file()}, format="multipart")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.api.get(self.url).data, response.data)
        raw = base64.b64decode(response.data["image"].split(",")[1])
        with Image.open(BytesIO(raw)) as img:
            self.assertEqual(img.size, (256, 256))
            self.assertEqual(img.format, "JPEG")
            self.assertFalse(img.getexif())
        self.assertEqual(self.api.post(self.url, {"file": self.file("WEBP")}, format="multipart").status_code, 200)
        self.assertEqual(UserAvatar.objects.filter(user=self.user).count(), 1)
        self.assertEqual(self.api.delete(self.url).status_code, 200)
        self.assertIsNone(self.api.get(self.url).data["image"])

    def test_other_user_cannot_read_replace_or_remove_avatar(self):
        self.api.post(self.url, {"file": self.file()}, format="multipart")
        original = bytes(UserAvatar.objects.get(user=self.user).image)
        self.api.force_authenticate(self.other)
        self.assertIsNone(self.api.get(self.url + f"?user={self.user.pk}").data["image"])
        self.api.post(self.url, {"file": self.file(), "user": self.user.pk}, format="multipart")
        self.api.delete(self.url + f"?user={self.user.pk}")
        self.assertEqual(bytes(UserAvatar.objects.get(user=self.user).image), original)

    def test_auth_required(self):
        self.api.force_authenticate(None)
        for method in [self.api.get, self.api.post, self.api.delete]:
            self.assertEqual(method(self.url).status_code, 401)
        self.scan.assert_not_called()

    def test_blocked_or_unavailable_scanner_preserves_previous_photo(self):
        self.api.post(self.url, {"file": self.file()}, format="multipart")
        original = bytes(UserAvatar.objects.get(user=self.user).image)
        self.scan.return_value = ScanResult(False, "hash", 1, "test")
        self.assertEqual(self.api.post(self.url, {"file": self.file()}, format="multipart").status_code, 400)
        self.scan.side_effect = ScanUnavailable()
        self.assertEqual(self.api.post(self.url, {"file": self.file()}, format="multipart").status_code, 503)
        self.assertEqual(bytes(UserAvatar.objects.get(user=self.user).image), original)

    def test_invalid_image_and_svg_rejected(self):
        for data in [b"not an image", b'<svg xmlns="http://www.w3.org/2000/svg"></svg>']:
            response = self.api.post(self.url, {"file": SimpleUploadedFile("photo.png", data, content_type="image/png")}, format="multipart")
            self.assertEqual(response.status_code, 400)
        self.assertFalse(UserAvatar.objects.exists())

    def test_size_limit_before_scanning(self):
        response = self.api.post(self.url, {"file": SimpleUploadedFile("photo.png", b"x" * (5 * 1024 * 1024 + 1))}, format="multipart")
        self.assertEqual(response.status_code, 400)
        self.scan.assert_not_called()

    def test_disallowed_format_and_pixel_limit(self):
        for upload in [self.file("GIF"), self.file(size=(4001, 4000))]:
            self.assertEqual(self.api.post(self.url, {"file": upload}, format="multipart").status_code, 400)
        self.assertFalse(UserAvatar.objects.exists())

    def test_crop_selects_requested_region_and_rejects_invalid_bounds(self):
        image = Image.new("RGB", (600, 300), "red")
        image.paste("blue", (300, 0, 600, 300))
        output = BytesIO(); image.save(output, format="PNG")
        response = self.api.post(self.url, {"file": SimpleUploadedFile("regions.png", output.getvalue()), "x": 0.5, "y": 0, "size": 1}, format="multipart")
        self.assertEqual(response.status_code, 200)
        raw = base64.b64decode(response.data["image"].split(",")[1])
        with Image.open(BytesIO(raw)) as cropped:
            self.assertGreater(cropped.getpixel((128, 128))[2], 240)
            self.assertLess(cropped.getpixel((128, 128))[0], 10)
        for crop in ({"x": 1, "y": 0, "size": 1}, {"x": "nan", "y": 0, "size": 1}, {"x": 0}, {"x": 0, "y": 0, "size": 0}):
            response = self.api.post(self.url, {"file": self.file(), **crop}, format="multipart")
            self.assertEqual(response.status_code, 400)
