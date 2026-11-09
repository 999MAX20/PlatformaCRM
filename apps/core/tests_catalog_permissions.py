"""OFFICIAL-09: catalog ingestion cannot bypass normal Service authority."""
import csv
import io
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework.exceptions import PermissionDenied
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.branches.models import Branch, BranchAccess
from apps.businesses.models import Business, BusinessMember, BusinessRole, RolePermission
from apps.core.import_export import create_manual_catalog_item, import_catalog_row
from apps.core.models import AuditLog, ImportJob
from apps.integrations.models import BusinessConnector, BusinessEvent, ConnectorSyncRun
from apps.services.models import Service


class CatalogPermissionTests(TestCase):
    def setUp(self):
        media = tempfile.TemporaryDirectory()
        self.addCleanup(media.cleanup)
        config = override_settings(MEDIA_ROOT=media.name)
        config.enable()
        self.addCleanup(config.disable)
        scanner = patch("apps.core.antivirus.scan_stream", return_value=SimpleNamespace(clean=True))
        scanner.start()
        self.addCleanup(scanner.stop)
        self.owner = User.objects.create_user(username="catalog-owner", email="catalog-owner@example.test")
        self.actor = User.objects.create_user(username="catalog-actor", email="catalog-actor@example.test")
        self.business = Business.objects.create(owner=self.owner, name="Catalog", slug="catalog-permissions")
        self.role = BusinessRole.objects.create(business=self.business, name="Catalog role")
        self.member = BusinessMember.objects.create(business=self.business, user=self.actor, role="admin", business_role=self.role)
        for action in ("view", "create", "manage"):
            RolePermission.objects.create(business_role=self.role, resource="integrations", action=action, is_allowed=True, scope="business")
        self.settings_permission = RolePermission.objects.create(business_role=self.role, resource="settings", action="update", is_allowed=False, scope="business")
        self.service = Service.objects.create(business=self.business, name="Existing", description="Original", duration_minutes=40, price_from="100")
        self.api = APIClient()
        self.api.force_authenticate(self.actor)

    def allow_settings(self):
        self.settings_permission.is_allowed = True
        self.settings_permission.save()

    def branches(self):
        first = Branch.objects.create(business=self.business, name="First")
        second = Branch.objects.create(business=self.business, name="Second")
        grant = BranchAccess.objects.create(member=self.member, all_branches=False)
        grant.branches.add(first)
        return grant, second

    def payload(self, **overrides):
        return {"business": self.business.pk, "name": "Existing", "item_type": "service", "price_from": "250", "duration_minutes": "50", **overrides}

    def upload(self, rows):
        stream = io.StringIO()
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
        response = self.api.post("/api/import-jobs/", {"business": self.business.pk, "entity_type": "catalog", "source_file": SimpleUploadedFile("catalog.csv", stream.getvalue().encode(), content_type="text/csv")}, format="multipart")
        self.assertEqual(response.status_code, 201, response.data)
        return ImportJob.objects.get(pk=response.data["id"])

    def confirm(self, job):
        return self.api.post(f"/api/import-jobs/{job.pk}/confirm/")

    def assert_service_unchanged(self):
        self.service.refresh_from_db()
        self.assertEqual(self.service.description, "Original")
        self.assertEqual(self.service.duration_minutes, 40)
        self.assertEqual(self.service.price_from, 100)
        self.assertEqual(Service.objects.count(), 1)
        self.assertFalse(BusinessEvent.objects.exists())

    def test_manual_service_denies_settings_override_for_new_and_existing(self):
        for name in ("Existing", "New"):
            with self.subTest(name=name):
                result = self.api.post("/api/data/catalog-items/", self.payload(name=name), format="json")
                self.assertEqual(result.status_code, 403, result.data)
                self.assert_service_unchanged()

    def test_import_service_denied_and_product_event_rolled_back(self):
        job = self.upload([self.payload(name="Product", item_type="product"), self.payload()])
        result = self.confirm(job)
        self.assertEqual(result.status_code, 403, result.data)
        self.assert_service_unchanged()
        job.refresh_from_db()
        self.assertEqual(job.status, ImportJob.Statuses.PREVIEWED)
        self.assertFalse(ConnectorSyncRun.objects.exists())
        self.assertFalse(BusinessConnector.objects.exists())

    def test_manual_partial_branch_access_denies_service_create_and_update(self):
        self.allow_settings()
        self.branches()
        for name in ("Existing", "New"):
            result = self.api.post("/api/data/catalog-items/", self.payload(name=name), format="json")
            self.assertEqual(result.status_code, 403, result.data)
        self.assert_service_unchanged()

    def test_import_uses_current_branch_grants_after_preview(self):
        self.allow_settings()
        grant, second = self.branches()
        grant.branches.add(second)
        job = self.upload([self.payload()])
        grant.branches.remove(second)
        self.assertEqual(self.confirm(job).status_code, 403)
        self.assert_service_unchanged()

    def test_import_uses_current_settings_after_preview(self):
        self.allow_settings()
        job = self.upload([self.payload()])
        self.settings_permission.is_allowed = False
        self.settings_permission.save()
        self.assertEqual(self.confirm(job).status_code, 403)
        self.assert_service_unchanged()

    def test_all_existing_branches_allow_import_without_future_branch_grant(self):
        self.allow_settings()
        grant, second = self.branches()
        grant.branches.add(second)
        job = self.upload([self.payload(), self.payload(name="New")])
        result = self.confirm(job)
        self.assertEqual(result.status_code, 200, result.data)
        self.service.refresh_from_db()
        self.assertEqual(self.service.price_from, 250)
        self.assertEqual(Service.objects.count(), 2)
        self.assertEqual(BusinessEvent.objects.count(), 2)

    def test_owner_can_manually_create_and_update(self):
        self.branches()
        self.api.force_authenticate(self.owner)
        for name in ("Existing", "New"):
            response = self.api.post("/api/data/catalog-items/", self.payload(name=name), format="json")
            self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(Service.objects.count(), 2)
        self.assertTrue(AuditLog.objects.filter(metadata__kind="manual_catalog_item_created").exists())

    def test_product_only_paths_do_not_require_service_settings(self):
        self.branches()
        result = self.api.post("/api/data/catalog-items/", self.payload(item_type="product", name="Stock"), format="json")
        self.assertEqual(result.status_code, 201, result.data)
        job = self.upload([self.payload(item_type="product", name="Imported stock")])
        self.assertEqual(self.confirm(job).status_code, 200)
        self.assertEqual(Service.objects.count(), 1)

    def test_foreign_business_manual_request_denied(self):
        other = Business.objects.create(owner=self.owner, name="Other", slug="catalog-other")
        result = self.api.post("/api/data/catalog-items/", self.payload(business=other.pk), format="json")
        self.assertEqual(result.status_code, 403)
        self.assert_service_unchanged()

    def test_direct_import_checks_job_actor_and_service_alias(self):
        job = ImportJob(business=self.business, actor=self.actor, entity_type="catalog")
        with self.assertRaises(PermissionDenied):
            import_catalog_row(job, self.payload(item_type="услуга"))
        self.assert_service_unchanged()

    def test_missing_actor_direct_service_mutations_fail_closed(self):
        for actor in (None,):
            with self.assertRaises(PermissionDenied):
                import_catalog_row(ImportJob(business=self.business, actor=actor), self.payload())
            with self.assertRaises(PermissionDenied):
                create_manual_catalog_item(self.business, self.payload(), None)
        self.assert_service_unchanged()

    def test_catalog_metadata_never_reactivates_inactive_or_archived_services(self):
        self.api.force_authenticate(self.owner)
        for archived in (False, True):
            for mode in ("manual", "import"):
                with self.subTest(archived=archived, mode=mode):
                    Service.objects.filter(pk=self.service.pk).update(is_active=False, is_archived=archived, archive_reason="Keep reason")
                    if mode == "manual":
                        result = self.api.post("/api/data/catalog-items/", self.payload(), format="json")
                        self.assertEqual(result.status_code, 201, result.data)
                    else:
                        result = self.confirm(self.upload([self.payload()]))
                        self.assertEqual(result.status_code, 200, result.data)
                    self.service.refresh_from_db()
                    self.assertFalse(self.service.is_active)
                    self.assertEqual(self.service.is_archived, archived)
                    self.assertEqual(self.service.archive_reason, "Keep reason")

    def test_other_actor_cannot_confirm_privileged_upload(self):
        self.api.force_authenticate(self.owner)
        job = self.upload([self.payload()])
        self.api.force_authenticate(self.actor)
        self.assertEqual(self.confirm(job).status_code, 404)
        self.assert_service_unchanged()

    def test_business_owner_cannot_confirm_other_users_upload(self):
        job = self.upload([self.payload()])
        self.api.force_authenticate(self.owner)
        result = self.confirm(job)
        self.assertEqual(result.status_code, 404, result.data)
        self.assert_service_unchanged()

    def test_direct_import_request_actor_overrides_job_actor(self):
        job = ImportJob(business=self.business, actor=self.owner)
        with self.assertRaises(PermissionDenied):
            import_catalog_row(job, self.payload(), request=SimpleNamespace(user=self.actor))
        self.assert_service_unchanged()

    def test_inactive_member_cannot_use_direct_import(self):
        self.allow_settings()
        self.member.is_active = False
        self.member.save()
        with self.assertRaises(PermissionDenied):
            import_catalog_row(ImportJob(business=self.business, actor=self.actor), self.payload())
        self.assert_service_unchanged()

    def test_manual_audit_failure_rolls_back_service_and_event(self):
        self.api.force_authenticate(self.owner)
        with patch("apps.core.import_export.write_audit_log", side_effect=RuntimeError("synthetic audit failure")):
            response = self.api.post("/api/data/catalog-items/", self.payload(), format="json")
        self.assertEqual(response.status_code, 500, response.data)
        self.assert_service_unchanged()

    def test_direct_import_event_failure_rolls_back_service(self):
        with patch("apps.core.import_export.normalize_business_event", side_effect=RuntimeError("synthetic event failure")):
            with self.assertRaises(RuntimeError):
                import_catalog_row(ImportJob(business=self.business, actor=self.owner), self.payload())
        self.assert_service_unchanged()

    def test_missing_catalog_name_has_no_side_effects(self):
        self.api.force_authenticate(self.owner)
        response = self.api.post("/api/data/catalog-items/", self.payload(name=" "), format="json")
        self.assertEqual(response.status_code, 400, response.data)
        self.assert_service_unchanged()
