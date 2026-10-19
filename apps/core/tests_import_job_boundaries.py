import tempfile
from types import SimpleNamespace
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework.exceptions import ValidationError
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.businesses.models import Business, BusinessMember, BusinessRole, RolePermission
from apps.clients.models import Client
from apps.core.import_export import build_import_preview, confirm_import
from apps.core.models import ImportJob
from apps.integrations.models import BusinessEvent, ConnectorSyncRun


class ImportJobBoundaryTests(TestCase):
    def setUp(self):
        media = tempfile.TemporaryDirectory()
        self.addCleanup(media.cleanup)
        settings = override_settings(MEDIA_ROOT=media.name)
        settings.enable()
        self.addCleanup(settings.disable)
        scanner = patch("apps.core.antivirus.scan_stream", return_value=SimpleNamespace(clean=True))
        scanner.start()
        self.addCleanup(scanner.stop)
        self.owner = User.objects.create_user(username="import-boundary", email="import-boundary@example.test", role="business_owner")
        self.business = Business.objects.create(owner=self.owner, name="Import", slug="import-boundary")
        self.api = APIClient()
        self.api.force_authenticate(self.owner)
        self.request = SimpleNamespace(user=self.owner, META={})

    def upload(self, **extra):
        return self.api.post("/api/import-jobs/", {
            "business": self.business.pk, "entity_type": "clients",
            "source_file": SimpleUploadedFile("clients.csv", b"full_name,phone\nOriginal,+77010001601\n", content_type="text/csv"),
            **extra,
        }, format="multipart")

    def job(self):
        response = self.upload()
        self.assertEqual(response.status_code, 201, response.data)
        return ImportJob.objects.get(pk=response.data["id"])

    def test_create_rejects_server_fields_without_persisting_job(self):
        for field, value in {"status": "imported", "actor": self.owner.pk,
                             "total_rows": 999, "imported_count": 999,
                             "preview_json": "{}", "mapping_json": "{}",
                             "errors_json": "{}", "original_filename": "forged.csv"}.items():
            with self.subTest(field=field):
                response = self.upload(**{field: value})
                self.assertEqual(response.status_code, 400, response.data)
                self.assertFalse(ImportJob.objects.exists())

    def test_generic_mutation_cannot_change_or_delete_import(self):
        job = self.job()
        before = ImportJob.objects.values().get(pk=job.pk)
        for method in ("patch", "put", "delete"):
            response = getattr(self.api, method)(f"/api/import-jobs/{job.pk}/", {"status": "imported", "actor": None}, format="json")
            self.assertEqual(response.status_code, 405, response.data)
            self.assertEqual(ImportJob.objects.values().get(pk=job.pk), before)

    def test_preview_mapping_is_validated_and_bad_request_keeps_saved_preview(self):
        job = self.job()
        for mapping in ([], "bad", {"full_name": "absent"}, {"unsupported": "full_name"}, {"full_name": ["full_name"]}, {}):
            with self.subTest(mapping=mapping):
                response = self.api.post(f"/api/import-jobs/{job.pk}/preview/", {"mapping": mapping}, format="json")
                self.assertEqual(response.status_code, 400, response.data)
                saved = ImportJob.objects.get(pk=job.pk)
                self.assertEqual(saved.mapping_json, job.mapping_json)
        response = self.api.post(f"/api/import-jobs/{job.pk}/preview/", {"mapping": {"full_name": "full_name"}}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["mapping_json"], {"full_name": "full_name"})

    def test_confirmed_job_cannot_be_reopened_or_reconfirmed_from_stale_instance(self):
        job = self.job()
        response = self.api.post(f"/api/import-jobs/{job.pk}/confirm/")
        self.assertEqual(response.status_code, 200, response.data)
        with self.assertRaises(ValidationError):
            build_import_preview(job)
        with self.assertRaises(ValidationError):
            confirm_import(job, self.request)
        self.assertEqual(ConnectorSyncRun.objects.count(), 1)
        self.assertEqual(BusinessEvent.objects.count(), 1)

    def test_confirm_revalidates_current_rows_instead_of_trusting_preview_errors(self):
        job = self.job()
        ImportJob.objects.filter(pk=job.pk).update(entity_type="sales", mapping_json={"amount": "phone"}, errors_json={})
        with patch("apps.core.import_export.read_tabular_file", return_value=[{"phone": "not-money"}]):
            with self.assertRaises(ValidationError):
                confirm_import(job, self.request)
        self.assertFalse(ConnectorSyncRun.objects.exists())
        self.assertFalse(BusinessEvent.objects.exists())
        self.assertFalse(Client.objects.exists())

    def test_confirm_failure_rolls_back_earlier_rows_and_history(self):
        job = self.job()
        from apps.core.import_export import import_client_row
        def fail_second(current_job, payload, connector=None):
            if payload["full_name"] == "Second":
                raise RuntimeError("Injected row failure")
            return import_client_row(current_job, payload, connector=connector)
        with patch("apps.core.import_export.read_tabular_file", return_value=[{"full_name": "First", "phone": ""}, {"full_name": "Second", "phone": ""}]), patch("apps.core.import_export.import_client_row", side_effect=fail_second):
            with self.assertRaises(RuntimeError):
                confirm_import(job, self.request)
        self.assertFalse(Client.objects.exists())
        self.assertFalse(BusinessEvent.objects.exists())
        self.assertFalse(ConnectorSyncRun.objects.exists())
        self.assertEqual(ImportJob.objects.get(pk=job.pk).status, "previewed")

    def test_foreign_actor_cannot_preview_confirm_or_read_job(self):
        job = self.job()
        other = User.objects.create_user(username="other-import", email="other-import@example.test", role="business_owner")
        Business.objects.create(owner=other, name="Other", slug="other-import")
        self.api.force_authenticate(other)
        for suffix in ("preview/", "confirm/"):
            self.assertEqual(self.api.post(f"/api/import-jobs/{job.pk}/{suffix}").status_code, 404)
        self.assertEqual(self.api.get(f"/api/import-jobs/{job.pk}/").status_code, 404)

    def test_happy_create_preview_confirm_keeps_actor_and_server_counts(self):
        job = self.job()
        self.assertEqual(job.actor_id, self.owner.pk)
        self.assertEqual(job.total_rows, 1)
        response = self.api.post(f"/api/import-jobs/{job.pk}/confirm/")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["imported_count"], 1)
        self.assertEqual(Client.objects.get().full_name, "Original")

    def test_unrecognized_columns_can_be_mapped_and_repreviewed(self):
        response = self.upload(source_file=SimpleUploadedFile("custom.csv", b"custom_name\nMapped client\n", content_type="text/csv"))
        self.assertEqual(response.status_code, 201, response.data)
        pk = response.data["id"]
        self.assertFalse(response.data["summary_json"]["ready"])
        self.assertEqual(self.api.post(f"/api/import-jobs/{pk}/confirm/").status_code, 400)
        response = self.api.post(f"/api/import-jobs/{pk}/preview/", {"mapping": {"full_name": "custom_name"}}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertTrue(response.data["summary_json"]["ready"])
        # Empty-body refresh preserves explicitly selected mapping.
        response = self.api.post(f"/api/import-jobs/{pk}/preview/")
        self.assertEqual(response.data["mapping_json"], {"full_name": "custom_name"})
        self.assertEqual(self.api.post(f"/api/import-jobs/{pk}/confirm/").status_code, 200)
        self.assertEqual(Client.objects.get().full_name, "Mapped client")

    def test_revoked_create_permission_blocks_preview_and_confirm(self):
        member = User.objects.create_user(username="import-member", email="import-member@example.test", role="business_operator")
        role = BusinessRole.objects.create(business=self.business, name="Importer")
        for action in ("view", "create"):
            RolePermission.objects.create(business_role=role, resource="clients", action=action, scope="business")
        BusinessMember.objects.create(business=self.business, user=member, role="operator", business_role=role)
        self.api.force_authenticate(member)
        job = self.job()
        RolePermission.objects.filter(business_role=role, action="create").update(is_allowed=False)
        for suffix in ("preview/", "confirm/"):
            self.assertEqual(self.api.post(f"/api/import-jobs/{job.pk}/{suffix}").status_code, 403)
        self.assertFalse(Client.objects.exists())

    def test_confirm_rechecks_file_security_and_size_without_changing_state(self):
        from apps.core.antivirus import ScanUnavailable
        job = self.job()
        with patch("apps.core.antivirus.scan_stream", return_value=SimpleNamespace(clean=False)):
            self.assertEqual(self.api.post(f"/api/import-jobs/{job.pk}/confirm/").status_code, 400)
        with patch("apps.core.antivirus.scan_stream", side_effect=ScanUnavailable("scanner_unavailable")):
            self.assertEqual(self.api.post(f"/api/import-jobs/{job.pk}/confirm/").status_code, 503)
        with override_settings(MAX_UPLOAD_SIZE_MB=0):
            self.assertEqual(self.api.post(f"/api/import-jobs/{job.pk}/confirm/").status_code, 400)
        self.assertEqual(ImportJob.objects.get(pk=job.pk).status, "previewed")
        self.assertFalse(Client.objects.exists())
        self.assertFalse(ConnectorSyncRun.objects.exists())

    def test_changed_source_is_revalidated_before_any_effect(self):
        response = self.upload(entity_type="sales", source_file=SimpleUploadedFile("sales.csv", b"amount\n12\n", content_type="text/csv"))
        self.assertEqual(response.status_code, 201, response.data)
        job = ImportJob.objects.get(pk=response.data["id"])
        with job.source_file.storage.open(job.source_file.name, "wb") as source:
            source.write(b"amount\n12\ninvalid\n")
        response = self.api.post(f"/api/import-jobs/{job.pk}/confirm/")
        self.assertEqual(response.status_code, 400, response.data)
        self.assertFalse(BusinessEvent.objects.exists())
        self.assertFalse(ConnectorSyncRun.objects.exists())

    def test_admin_cannot_rewrite_or_remove_import_history(self):
        from django.contrib.admin import site
        from django.test import RequestFactory
        job = self.job()
        self.owner.is_staff = self.owner.is_superuser = True
        request = RequestFactory().get("/admin/")
        request.user = self.owner
        admin = site._registry[ImportJob]
        self.assertFalse(admin.has_add_permission(request))
        self.assertFalse(admin.has_change_permission(request, job))
        self.assertFalse(admin.has_delete_permission(request, job))
        self.assertNotIn("source_file", admin.get_fields(request, job))

    def test_malformed_request_shapes_are_validation_errors(self):
        job = self.job()
        for data in ([{"status": "imported"}], "invalid"):
            self.assertEqual(self.api.post("/api/import-jobs/", data, format="json").status_code, 400)
            self.assertEqual(self.api.post(f"/api/import-jobs/{job.pk}/preview/", data, format="json").status_code, 400)

    def test_non_previewed_states_cannot_confirm_and_cancelled_cannot_preview(self):
        job = self.job()
        for status in ("uploaded", "failed", "cancelled"):
            ImportJob.objects.filter(pk=job.pk).update(status=status)
            self.assertEqual(self.api.post(f"/api/import-jobs/{job.pk}/confirm/").status_code, 400)
        self.assertEqual(self.api.post(f"/api/import-jobs/{job.pk}/preview/").status_code, 400)
        self.assertFalse(Client.objects.exists())
