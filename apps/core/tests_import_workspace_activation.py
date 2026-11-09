from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase
from rest_framework.exceptions import APIException

from apps.core import tests_import_workspace_engine as fixtures
from apps.core.import_workspace.activation import activation_preview, activate_records
from apps.integrations.models import BusinessEvent
from apps.notifications.models import Notification
from apps.scheduling.models import Appointment


class ImportActivationTests(TestCase):
    setUp = fixtures.ImportWorkspaceEngineTests.setUp
    source = fixtures.ImportWorkspaceEngineTests.source
    four_sources = fixtures.ImportWorkspaceEngineTests.four_sources
    preview = fixtures.ImportWorkspaceEngineTests.preview
    confirm = fixtures.ImportWorkspaceEngineTests.confirm

    def prepared(self):
        self.four_sources()
        self.assertTrue(self.preview()["ready"])
        self.confirm()
        return activation_preview(self.workspace, self.owner)

    def test_explicit_future_activation_runs_once_and_replay_is_safe(self):
        preview = self.prepared()
        self.assertFalse(Notification.objects.exists())
        self.assertEqual(len(preview["records"]), 1)
        pk = preview["records"][0]["id"]
        result = activate_records(workspace_id=self.workspace.pk, actor=self.owner, token=preview["token"], ids=[pk])
        self.assertEqual(result["activated"], [pk])
        self.assertEqual(BusinessEvent.objects.filter(event_type="appointment.created").count(), 1)
        count = Notification.objects.count()
        self.assertGreater(count, 0)
        activate_records(workspace_id=self.workspace.pk, actor=self.owner, token=preview["token"], ids=[pk])
        self.assertEqual(Notification.objects.count(), count)
        self.assertEqual(activation_preview(self.workspace, self.owner)["records"], [])

    def test_changed_or_historical_record_cannot_activate(self):
        preview = self.prepared()
        record = Appointment.objects.get()
        record.start_at -= timedelta(days=10)
        record.end_at -= timedelta(days=10)
        record.save()
        with self.assertRaises(APIException):
            activate_records(workspace_id=self.workspace.pk, actor=self.owner, token=preview["token"], ids=[record.pk])
        self.assertFalse(Notification.objects.exists())
        self.assertEqual(activation_preview(self.workspace, self.owner)["records"], [])

    def test_unseen_record_and_tampered_token_rejected(self):
        preview = self.prepared()
        for token, ids in [(preview["token"], [999999]), (preview["token"] + "tampered", [Appointment.objects.get().pk])]:
            with self.assertRaises(APIException):
                activate_records(workspace_id=self.workspace.pk, actor=self.owner, token=token, ids=ids)
        self.assertFalse(Notification.objects.exists())

    def test_effect_failure_rolls_back_activation_and_retry_can_recover(self):
        preview = self.prepared()
        pk = Appointment.objects.get().pk
        with patch("apps.scheduling.services.run_automations_for_event", side_effect=RuntimeError("isolated fault")), self.assertRaises(RuntimeError):
            activate_records(workspace_id=self.workspace.pk, actor=self.owner, token=preview["token"], ids=[pk])
        self.assertFalse(Notification.objects.exists())
        self.assertFalse(BusinessEvent.objects.filter(event_type="appointment.created").exists())
        activate_records(workspace_id=self.workspace.pk, actor=self.owner, token=preview["token"], ids=[pk])
        self.assertEqual(BusinessEvent.objects.filter(event_type="appointment.created").count(), 1)
