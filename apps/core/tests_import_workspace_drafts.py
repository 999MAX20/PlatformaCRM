from copy import deepcopy

from django.test import TestCase, override_settings
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.accounts.models import User
from apps.businesses.models import Business
from apps.clients.models import Client
from apps.core.import_workspace.drafts import (
    StaleImportVersion, add_source, correct_source, create_workspace, prepared_rows,
)
from apps.core.models import CustomFieldDefinition, ImportWorkspace, ImportWorkspaceSource


class ImportWorkspaceDraftTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="workspace-owner", email="workspace-owner@example.test", role="business_owner")
        self.business = Business.objects.create(owner=self.owner, name="Workspace", slug="workspace")
        self.workspace = create_workspace(business=self.business, actor=self.owner)
        self.rows = [{"Name": "Original", "Phone": "+77010000001"}, {"Name": "Second", "Phone": ""}]

    def source(self):
        self.workspace, source = add_source(
            workspace_id=self.workspace.pk, actor=self.owner, version=self.workspace.version,
            rows=deepcopy(self.rows), filename="clients.csv", entity_type="clients",
        )
        return source

    def correct(self, source, **changes):
        return correct_source(
            workspace_id=self.workspace.pk, source_id=source.pk, actor=self.owner,
            version=self.workspace.version, corrections={"1": {"Name": "Corrected"}}, excluded=[2], **changes,
        )

    def test_corrections_preserve_source_and_do_not_create_business_entities(self):
        source = self.source()
        digest = source.digest
        self.workspace, source = self.correct(source)
        source.refresh_from_db()
        self.assertEqual(source.rows_json, self.rows)
        self.assertEqual(source.digest, digest)
        rows = list(prepared_rows(source))
        self.assertEqual(rows, [{"row": 1, "original": self.rows[0], "values": {**self.rows[0], "Name": "Corrected"}, "excluded": False}])
        self.assertEqual(len(list(prepared_rows(source, include_excluded=True))), 2)
        self.assertFalse(Client.objects.exists())
        self.assertFalse(CustomFieldDefinition.objects.exists())

    def test_edit_invalidates_ready_version_and_preserves_other_sources(self):
        source = self.source()
        self.workspace.state = "ready"
        self.workspace.validated_version = self.workspace.version
        self.workspace.report_json = {"ready": True}
        self.workspace.save()
        previous = self.workspace.version
        self.workspace, _ = self.correct(source)
        self.assertEqual(self.workspace.version, previous + 1)
        self.assertEqual(self.workspace.state, "draft")
        self.assertIsNone(self.workspace.validated_version)
        self.assertEqual(self.workspace.report_json, {})

    def test_stale_edit_cannot_overwrite_a_newer_edit(self):
        source = self.source()
        self.correct(source)
        with self.assertRaises(StaleImportVersion):
            self.correct(source)
        source.refresh_from_db()
        self.assertEqual(source.corrections_json, {"1": {"Name": "Corrected"}})

    def test_invalid_rows_columns_and_exclusions_do_not_change_draft(self):
        source = self.source()
        for corrections, excluded in [
            ({"0": {"Name": "X"}}, []), ({"01": {"Name": "X"}}, []),
            ({"3": {"Name": "X"}}, []), ({"1": {"unknown": "X"}}, []),
            ({"1": {"Name": 7}}, []), ({}, [True]), ({}, [1, 1]), ({}, [3]),
        ]:
            with self.subTest(corrections=corrections, excluded=excluded), self.assertRaises(ValidationError):
                correct_source(workspace_id=self.workspace.pk, source_id=source.pk, actor=self.owner,
                               version=self.workspace.version, corrections=corrections, excluded=excluded)
        source.refresh_from_db()
        self.workspace.refresh_from_db()
        self.assertEqual(source.corrections_json, {})
        self.assertEqual(self.workspace.version, 2)

    def test_other_actor_and_foreign_source_cannot_be_used(self):
        source = self.source()
        other = User.objects.create_user(username="workspace-other", email="workspace-other@example.test", role="business_owner")
        with self.assertRaises(PermissionDenied):
            correct_source(workspace_id=self.workspace.pk, source_id=source.pk, actor=other,
                           version=self.workspace.version, corrections={}, excluded=[])
        second = create_workspace(business=self.business, actor=self.owner)
        with self.assertRaises(ValidationError):
            correct_source(workspace_id=second.pk, source_id=source.pk, actor=self.owner,
                           version=second.version, corrections={}, excluded=[])

    def test_imported_and_cancelled_drafts_are_immutable(self):
        source = self.source()
        for state in [ImportWorkspace.States.IMPORTED, ImportWorkspace.States.CANCELLED]:
            self.workspace.state = state
            self.workspace.save()
            with self.assertRaises(ValidationError):
                self.correct(source)

    def test_exclusion_and_correction_can_be_undone(self):
        source = self.source()
        self.workspace, source = self.correct(source)
        self.workspace, source = correct_source(workspace_id=self.workspace.pk, source_id=source.pk,
            actor=self.owner, version=self.workspace.version, corrections={}, excluded=[])
        self.assertEqual([item["values"] for item in prepared_rows(source)], self.rows)

    @override_settings(IMPORT_MAX_ROWS=1)
    def test_invalid_upload_does_not_leave_partial_source_or_version(self):
        with self.assertRaises(ValidationError):
            self.source()
        self.workspace.refresh_from_db()
        self.assertEqual(self.workspace.version, 1)
        self.assertFalse(ImportWorkspaceSource.objects.exists())
