from unittest.mock import patch

from django.db import DatabaseError, connection
from django.test import TestCase, override_settings
from django.utils import timezone
from django.test.utils import CaptureQueriesContext
from rest_framework.exceptions import NotFound
from rest_framework.test import APIClient

from apps.branches.models import BranchAccess
from apps.businesses.models import Business, BusinessCapability, RolePermission
from apps.clients.models import Client
from apps.notifications.models import Notification, NotificationPreference, NotificationRecipient
from apps.notifications.personal_selectors import personal_states
from apps.notifications.personal_services import change_personal_state, read_personal_feed
from apps.scheduling.models import Appointment
from . import tests_participation_services as fixtures
from .models import MedicalAuditEvent, MedicalParticipationNotice, MedicalRoleAssignment, PatientProfile, TreatmentParticipation
from .participation_notifications import MedicalNotificationUnavailable, notify_participation_event
from .participation_services import withdraw_treatment_participation
from .tests_patient_services import key


@override_settings(MEDICAL_DATA_KEYS={"test": key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=key(8))
class ParticipationNotificationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.ParticipationCommandTests.setUpTestData.__func__(cls)
        RolePermission.objects.create(business_role=cls.role, resource="medical_participation",
                                      action="view", scope="own")

    propose = fixtures.ParticipationCommandTests.propose
    respond = fixtures.ParticipationCommandTests.respond

    def visible(self, actor=None):
        return personal_states(actor=actor or self.recipient, business=self.business)

    def test_neutral_fixed_audience_and_idempotent_production(self):
        item, _ = self.propose()
        notice = Notification.objects.get()
        self.assertEqual(notice.recipient_id, self.recipient.pk)
        self.assertEqual(list(notice.recipient_states.values_list("user_id", flat=True)), [self.recipient.pk])
        self.assertEqual((notice.text, notice.client_id, notice.appointment_id, notice.author_id), ("", None, None, None))
        self.assertEqual(notice.channel, "system")
        self.propose()
        notify_participation_event(MedicalAuditEvent.objects.get(action="participation_proposed"))
        self.assertEqual(Notification.objects.count(), 1)
        self.respond(item)
        self.respond(item)
        self.assertEqual(Notification.objects.count(), 2)
        self.assertEqual(MedicalParticipationNotice.objects.count(), 2)
        self.assertEqual(self.visible(self.doctor).count(), 1)
        self.assertEqual(self.visible(self.owner).count(), 0)

    def test_preference_suppresses_without_owner_or_broadcast_fallback(self):
        NotificationPreference.objects.create(business=self.business, user=self.recipient,
            category="system", in_app_enabled=False)
        item, _ = self.propose()
        self.assertFalse(Notification.objects.exists())
        self.assertEqual(item.state, "pending")
        self.respond(item, decision="decline")
        self.assertEqual(Notification.objects.get().recipient_id, self.doctor.pk)

    def test_notification_failure_rolls_back_proposal_audit_and_command(self):
        with patch("apps.medical.participation_notifications.MedicalParticipationNotice.objects.create",
                   side_effect=DatabaseError("synthetic failure")), self.assertRaises(MedicalNotificationUnavailable):
            self.propose()
        self.assertFalse(TreatmentParticipation.objects.exists())
        self.assertFalse(MedicalAuditEvent.objects.exists())
        self.assertFalse(Notification.objects.exists())
        self.propose()
        self.assertEqual(Notification.objects.count(), 1)

    def test_invitation_and_withdrawal_are_visible_without_clinical_access(self):
        item, _ = self.propose()
        self.assertEqual(self.visible().count(), 1)
        withdraw_treatment_participation(actor=self.doctor, business_id=self.business.pk,
            patient_id=self.patient.pk, participation_id=item.pk, expected_revision=1, idempotency_key="withdraw")
        self.assertEqual(self.visible().count(), 2)
        self.assertFalse(TreatmentParticipation.objects.filter(state="active").exists())

    def test_current_role_module_and_branch_revoke_feed_access(self):
        self.propose()
        self.assertEqual(self.visible().count(), 1)
        self.target_role.branches.clear()
        self.assertEqual(self.visible().count(), 0)
        self.target_role.branches.add(self.first)
        grant = BranchAccess.objects.get(member=self.target)
        grant.all_branches = False
        grant.save()
        self.assertEqual(self.visible().count(), 0)
        grant.all_branches = True
        grant.save()
        MedicalRoleAssignment.objects.filter(pk=self.target_role.pk).update(revoked_at=timezone.now())
        self.assertEqual(self.visible().count(), 0)
        MedicalRoleAssignment.objects.filter(pk=self.target_role.pk).update(revoked_at=None)
        BusinessCapability.objects.filter(business=self.business, module_key="medical_records").update(is_enabled=False)
        self.assertEqual(self.visible().count(), 0)

    def test_reply_requires_original_current_basis(self):
        item, _ = self.propose()
        self.respond(item)
        self.assertEqual(self.visible(self.doctor).count(), 1)
        Appointment.objects.filter(pk=self.appointment.pk).update(status="completed")
        self.assertEqual(self.visible(self.doctor).count(), 0)
        self.assertEqual(read_personal_feed(actor=self.doctor, business=self.business), 0)
        reply = Notification.objects.get(recipient=self.doctor)
        with self.assertRaises(NotFound):
            change_personal_state(actor=self.doctor, business=self.business, notification_id=reply.pk, action="read")
        self.assertIsNone(NotificationRecipient.objects.get(notification=reply).read_at)

    def test_corrupt_url_cannot_fall_back_to_generic_source(self):
        self.propose()
        notification = Notification.objects.get()
        for url in ("", "/app/calendar", "/app/account", "/app/medical/participations?notification=99999"):
            with self.subTest(url=url):
                Notification.objects.filter(pk=notification.pk).update(action_url=url)
                self.assertEqual(self.visible().count(), 0)

    def test_mismatched_medical_event_is_hidden(self):
        self.propose()
        client = Client.objects.create(business=self.business, full_name="Another synthetic patient")
        patient = PatientProfile.objects.create(business=self.business, client=client, created_by=self.owner)
        MedicalAuditEvent.objects.filter(action="participation_proposed").update(patient_id=patient.pk)
        self.assertEqual(self.visible().count(), 0)

    def test_foreign_event_cannot_be_claimed_by_current_business_notification(self):
        self.propose()
        other = Business.objects.create(owner=self.owner, name="Other synthetic business", slug="notice-other")
        MedicalAuditEvent.objects.filter(action="participation_proposed").update(business=other)
        self.assertEqual(self.visible().count(), 0)

    def test_batch_access_does_not_add_permission_queries_per_notification(self):
        item, _ = self.propose()
        with CaptureQueriesContext(connection) as first:
            self.assertEqual(self.visible().count(), 1)
        for index in range(6):
            withdraw_treatment_participation(actor=self.doctor, business_id=self.business.pk,
                patient_id=self.patient.pk, participation_id=item.pk, expected_revision=1,
                idempotency_key=f"withdraw-{index}")
            item, _ = self.propose(idempotency_key=f"proposal-{index}")
        with CaptureQueriesContext(connection) as many:
            self.assertEqual(self.visible().count(), 13)
        self.assertLessEqual(len(many), len(first) + 1)

    def test_http_list_detail_counts_and_actions_share_medical_scope(self):
        self.propose()
        notification = Notification.objects.get()
        api = APIClient()
        api.force_authenticate(self.recipient)
        def url(suffix=""):
            return f"/api/notifications/{suffix}?business={self.business.pk}"
        response = api.get(url())
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["count"], 1)
        row = response.data["results"][0]
        self.assertEqual(row["message_key"], "medical.notifications.participation_proposed")
        self.assertEqual(row["action_url"], f"/app/medical/participations?notification={notification.pk}")
        for private in (self.patient_client.full_name, "Synthetic private reason"):
            self.assertNotIn(private, str(response.data))
        self.assertEqual(api.get(url("summary/")).data["unread"], 1)
        self.assertEqual(api.post(url(f"{notification.pk}/open/")).status_code, 200)
        self.assertEqual(api.post(url(f"{notification.pk}/mark-unread/")).status_code, 200)
        MedicalRoleAssignment.objects.filter(pk=self.target_role.pk).update(revoked_at=timezone.now())
        self.assertEqual(api.get(url()).data["count"], 0)
        self.assertEqual(api.get(url("summary/")).data["unread"], 0)
        self.assertEqual(api.get(url(f"{notification.pk}/")).status_code, 404)
        self.assertEqual(api.post(url(f"{notification.pk}/mark-read/")).status_code, 404)
        self.assertEqual(api.post(url("mark-all-read/")).data, {"updated": 0})
