from django.contrib.admin.sites import AdminSite
from django.test import RequestFactory, TestCase, override_settings
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.businesses.models import Business, BusinessMember
from apps.clients.models import Client
from apps.core.admin import FileAttachmentAdmin
from apps.core.models import FileAttachment


@override_settings(SUPPORT_REQUIRES_GRANT=False)
class FileModuleIsolationTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="module-file-owner", email="file-owner@example.test")
        self.admin = User.objects.create_user(username="module-file-admin", email="file-admin@example.test",
                                              is_staff=True, is_superuser=True)
        self.business = Business.objects.create(owner=self.owner, name="Synthetic files", slug="module-files")
        BusinessMember.objects.create(business=self.business, user=self.owner, role="owner")
        client = Client.objects.create(business=self.business, full_name="Synthetic client")
        common = dict(business=self.business, uploaded_by=self.owner, size=10,
                      file="private/attachments/synthetic.pdf", content_type="application/pdf")
        self.crm = FileAttachment.objects.create(**common, original_name="crm.pdf",
                                                 entity_type="client", entity_id=str(client.pk))
        self.medical = FileAttachment.objects.create(**common, original_name="opaque.pdf",
            entity_type="medical_attachment", entity_id="opaque-module-reference")
        self.document = FileAttachment.objects.create(**common, original_name="document.pdf",
            entity_type="medical_document_artifact", entity_id="opaque-version-reference")
        self.api = APIClient()

    def test_generic_lists_exclude_module_objects_for_owner_and_platform_admin(self):
        for user in (self.owner, self.admin):
            self.api.force_authenticate(user)
            for params in ({}, {"business": self.business.pk}, {"entity_type": "medical_attachment"}):
                with self.subTest(user=user.pk, params=params):
                    response = self.api.get("/api/file-attachments/", params)
                    self.assertEqual(response.status_code, 200)
                    rows = response.data.get("results", []) if isinstance(response.data, dict) else response.data
                    self.assertNotIn(self.medical.pk, [row["id"] for row in rows])
                    self.assertNotIn(self.document.pk, [row["id"] for row in rows])
                    if "entity_type" not in params:
                        self.assertIn(self.crm.pk, [row["id"] for row in rows])

    def test_generic_details_download_and_rename_do_not_resolve_module_objects(self):
        for user in (self.owner, self.admin):
            self.api.force_authenticate(user)
            for suffix in ("", "download/"):
                with self.subTest(user=user.pk, suffix=suffix):
                    response = self.api.get(f"/api/file-attachments/{self.medical.pk}/{suffix}")
                    self.assertEqual(response.status_code, 404)
            response = self.api.post(f"/api/file-attachments/{self.medical.pk}/rename/",
                                     {"original_name": "changed.pdf"}, format="json")
            self.assertEqual(response.status_code, 404)
        self.medical.refresh_from_db()
        self.assertEqual(self.medical.original_name, "opaque.pdf")

    def test_generic_admin_cannot_list_or_resolve_module_objects(self):
        request = RequestFactory().get("/admin/core/fileattachment/")
        request.user = self.admin
        admin = FileAttachmentAdmin(FileAttachment, AdminSite())
        self.assertEqual(list(admin.get_queryset(request)), [self.crm])
        self.assertIsNone(admin.get_object(request, str(self.medical.pk)))
        self.assertEqual(admin.get_object(request, str(self.crm.pk)), self.crm)

    def test_document_artifact_is_not_exposed_by_generic_download_or_admin(self):
        for user in (self.owner, self.admin):
            self.api.force_authenticate(user)
            for suffix in ("", "download/"):
                response = self.api.get(f"/api/file-attachments/{self.document.pk}/{suffix}")
                self.assertEqual(response.status_code, 404)
            response = self.api.post(f"/api/file-attachments/{self.document.pk}/rename/",
                                     {"original_name": "changed.pdf"}, format="json")
            self.assertEqual(response.status_code, 404)
        request = RequestFactory().get("/admin/core/fileattachment/")
        request.user = self.admin
        self.assertIsNone(FileAttachmentAdmin(FileAttachment, AdminSite()).get_object(request, str(self.document.pk)))
