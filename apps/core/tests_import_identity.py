from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest.mock import patch

from django.db import close_old_connections
from django.test import TestCase, TransactionTestCase, skipUnlessDBFeature
from rest_framework.test import APIClient

from apps.businesses.models import Business
from apps.clients.models import Client
from apps.core import tests_client_import_permissions as fixtures
from apps.core.models import ImportJob
from apps.integrations.models import BusinessEvent
from apps.integrations import tests_google_sheets as sheets_fixtures


class ImportIdentityTests(TestCase):
    setUp = fixtures.ClientImportPermissionTests.setUp
    upload = fixtures.ClientImportPermissionTests.upload
    confirm = fixtures.ClientImportPermissionTests.confirm
    permission = fixtures.ClientImportPermissionTests.permission

    def test_formatted_domestic_number_matches_without_overwriting(self):
        self.permission("update", True)
        job = self.upload([{"full_name": "Incoming name", "phone": "8 (701) 000-17-01",
                            "email": "new@example.test"}])
        self.assertEqual(self.confirm(job).status_code, 200)
        self.customer.refresh_from_db()
        self.assertEqual(Client.objects.count(), 1)
        self.assertEqual(self.customer.full_name, "Existing synthetic")
        self.assertEqual(self.customer.email, "new@example.test")
        self.assertEqual(self.customer.phone, "+77010001701")

    def test_normalized_email_matches(self):
        self.permission("update", True)
        self.customer.email = "Old@Example.test"
        self.customer.save()
        job = self.upload([{"full_name": "Incoming", "email": " old@example.test "}])
        self.assertEqual(self.confirm(job).status_code, 200)
        self.assertEqual(Client.objects.count(), 1)

    def test_split_identity_blocks_preview_and_confirmation(self):
        self.permission("update", True)
        other = Client.objects.create(business=self.business, full_name="Other", email="other@example.test")
        job = self.upload([{"full_name": "Incoming", "phone": "8 (701) 000-17-01", "email": other.email}])
        self.assertFalse(job.preview_json["import_summary"]["ready"])
        self.assertEqual(job.errors_json["rows"][0]["row"], 1)
        self.assertEqual(self.confirm(job).status_code, 400)
        self.assertFalse(BusinessEvent.objects.exists())
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.email, "")

    def test_multiple_phone_matches_including_archive_are_ambiguous(self):
        Client.objects.create(business=self.business, full_name="Archived", phone="8 (701) 000-17-01", is_archived=True)
        job = self.upload([{"phone": self.customer.phone}])
        self.assertFalse(job.preview_json["import_summary"]["ready"])
        self.assertEqual(self.confirm(job).status_code, 400)
        self.assertEqual(Client.objects.count(), 2)

    def test_match_added_after_preview_is_rechecked(self):
        self.permission("update", True)
        job = self.upload([{"phone": self.customer.phone, "email": "later@example.test"}])
        self.assertTrue(job.preview_json["import_summary"]["ready"])
        Client.objects.create(business=self.business, full_name="Later", email="later@example.test")
        self.assertEqual(self.confirm(job).status_code, 400)
        job.refresh_from_db()
        self.assertEqual(job.status, ImportJob.Statuses.PREVIEWED)

    def test_conflict_created_by_earlier_rows_rolls_back_whole_import(self):
        self.permission("update", True)
        job = self.upload([
            {"full_name": "First", "phone": "+77010000001", "email": "one@example.test"},
            {"full_name": "Second", "phone": "+77010000002", "email": "two@example.test"},
            {"full_name": "Conflict", "phone": "8 (701) 000-00-01", "email": "two@example.test"},
        ])
        self.assertEqual(self.confirm(job).status_code, 400)
        self.assertEqual(Client.objects.count(), 1)
        self.assertFalse(BusinessEvent.objects.exists())

    def test_repeated_rows_and_fresh_import_do_not_duplicate(self):
        self.permission("update", True)
        rows = [{"full_name": "New", "phone": "+77010000003"},
                {"full_name": "New", "phone": "8 (701) 000-00-03"}]
        self.assertEqual(self.confirm(self.upload(rows)).status_code, 200)
        self.assertEqual(self.confirm(self.upload(rows)).status_code, 200)
        self.assertEqual(Client.objects.filter(business=self.business, normalized_phone="77010000003").count(), 1)

    def test_foreign_business_identity_does_not_block_or_change(self):
        foreign = Business.objects.create(owner=self.owner, name="Foreign", slug="foreign-identity")
        peer = Client.objects.create(business=foreign, full_name="Foreign", phone="+77010000004")
        job = self.upload([{"full_name": "Local", "phone": "8 (701) 000-00-04"}])
        self.assertEqual(self.confirm(job).status_code, 200)
        peer.refresh_from_db()
        self.assertEqual(peer.full_name, "Foreign")
        self.assertEqual(Client.objects.filter(business=self.business, normalized_phone=peer.normalized_phone).count(), 1)

    def test_normalized_match_still_requires_update_permission(self):
        job = self.upload([{"phone": "8 (701) 000-17-01", "email": "denied@example.test"}])
        self.assertEqual(self.confirm(job).status_code, 403)
        self.assertEqual(Client.objects.count(), 1)


@skipUnlessDBFeature("has_select_for_update")
class ImportIdentityConcurrencyTests(TransactionTestCase):
    setUp = fixtures.ClientImportPermissionTests.setUp
    upload = fixtures.ClientImportPermissionTests.upload
    permission = fixtures.ClientImportPermissionTests.permission

    def test_separate_jobs_for_equivalent_phone_create_one_client(self):
        self.permission("update", True)
        jobs = [self.upload([{"full_name": "New", "phone": phone}]).pk
                for phone in ("+77010000005", "8 (701) 000-00-05")]
        barrier = Barrier(2)
        original = Business.objects.select_for_update

        def synchronize(*args, **kwargs):
            barrier.wait(timeout=20)
            return original(*args, **kwargs)

        def confirm(pk):
            close_old_connections()
            try:
                api = APIClient()
                api.force_authenticate(self.actor)
                return api.post(f"/api/import-jobs/{pk}/confirm/").status_code
            finally:
                close_old_connections()

        with patch.object(Business.objects, "select_for_update", side_effect=synchronize):
            with ThreadPoolExecutor(max_workers=2) as pool:
                futures = [pool.submit(confirm, pk) for pk in jobs]
                self.assertEqual([f.result(timeout=45) for f in futures], [200, 200])
        self.assertEqual(Client.objects.filter(business=self.business, normalized_phone="77010000005").count(), 1)


class GoogleSheetsIdentityTests(TestCase):
    setUp = sheets_fixtures.GoogleSheetsImportTests.setUp
    respond = sheets_fixtures.GoogleSheetsImportTests.respond
    submit = sheets_fixtures.GoogleSheetsImportTests.submit

    def test_google_snapshot_matches_formatted_phone_on_confirm(self):
        existing = Client.objects.create(business=self.business, full_name="Saved", phone="+77011112233")
        self.rows = [["full_name", "phone", "email"], ["Incoming", "8 (701) 111-22-33", "new@example.test"]]
        snapshot = self.submit()
        self.assertEqual(snapshot.status_code, 200)
        result = self.api.post(f'/api/import-jobs/{snapshot.data["id"]}/confirm/')
        self.assertEqual(result.status_code, 200)
        existing.refresh_from_db()
        self.assertEqual(existing.email, "new@example.test")
        self.assertEqual(Client.objects.count(), 1)

    def test_google_snapshot_exposes_conflict_and_recovery_after_mapping_change(self):
        first = Client.objects.create(business=self.business, full_name="First", phone="+77011112233")
        Client.objects.create(business=self.business, full_name="Second", email="second@example.test")
        self.rows = [["full_name", "phone", "email"], ["Incoming", "8 (701) 111-22-33", "second@example.test"]]
        snapshot = self.submit()
        self.assertEqual(snapshot.status_code, 200)
        job = ImportJob.objects.get(pk=snapshot.data["id"])
        self.assertFalse(job.preview_json["import_summary"]["ready"])
        errors = self.api.get(f'/api/import-jobs/{job.pk}/errors/')
        self.assertEqual(errors.status_code, 200)
        self.assertEqual(errors.data["count"], 1)
        self.assertEqual(self.api.post(f'/api/import-jobs/{job.pk}/confirm/').status_code, 400)
        preview = self.api.post(f'/api/import-jobs/{job.pk}/preview/',
            {"mapping": {"full_name": "full_name", "phone": "phone"}}, format="json")
        self.assertEqual(preview.status_code, 200)
        self.assertEqual(self.api.post(f'/api/import-jobs/{job.pk}/confirm/').status_code, 200)
        first.refresh_from_db()
        self.assertEqual(first.full_name, "First")
        self.assertEqual(Client.objects.count(), 2)
