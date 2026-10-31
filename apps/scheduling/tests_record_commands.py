from datetime import time, timedelta
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.activities.models import ActivityEvent
from apps.bots.models import Bot, BotConversation
from apps.businesses.access import Actions, Resources, can, ensure_default_roles
from apps.businesses.models import Business, BusinessMember, BusinessRole, RolePermission
from apps.clients.models import Client
from apps.core.models import AuditLog
from apps.notifications.models import Notification
from apps.leads.models import Lead
from apps.scheduling.models import Appointment, Resource, WorkingHours
from apps.scheduling.services import appointment_responsible_user
from apps.services.models import Service


class RecordCommandTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create_user(username="record-owner", email="record-owner@example.test", full_name="Record Owner", role="business_owner")
        cls.staff = User.objects.create_user(username="record-staff", email="record-staff@example.test", role="staff")
        cls.business = Business.objects.create(owner=cls.owner, name="Record", slug="record", timezone="UTC")
        ensure_default_roles(cls.business)
        for user, role in ((cls.owner, "owner"), (cls.staff, "specialist")):
            BusinessMember.objects.create(business=cls.business, user=user, role=role,
                business_role=BusinessRole.objects.get(business=cls.business, preset_key=role))
        cls.client_record = Client.objects.create(business=cls.business, full_name="Client")
        cls.service = Service.objects.create(business=cls.business, name="Consultation", duration_minutes=30, price_from=1000)
        cls.resource = Resource.objects.create(business=cls.business, name="Specialist", linked_user=cls.owner)
        for day in range(7):
            WorkingHours.objects.create(business=cls.business, weekday=day, start_time=time(8), end_time=time(20))
        cls.lead = Lead.objects.create(business=cls.business, client=cls.client_record, status="lost", lost_reason="Historical closure")
        cls.bot = Bot.objects.create(business=cls.business, name="Inbox")
        cls.conversation = BotConversation.objects.create(business=cls.business, bot=cls.bot,
            client=cls.client_record, lead=cls.lead, external_user_id="record-source")

    def setUp(self):
        self.api = APIClient()
        self.api.force_authenticate(self.owner)
        self.start = (timezone.now() + timedelta(days=2)).replace(hour=10, minute=0, second=0, microsecond=0)
        self.payload = {"business": self.business.pk, "client": self.client_record.pk,
            "service": self.service.pk, "resource": self.resource.pk, "start_at": self.start.isoformat()}

    def create(self, **overrides):
        return self.api.post("/api/appointments/create-record/", {**self.payload, **overrides}, format="json")

    def test_default_responsible_and_shared_identity(self):
        response = self.create()
        self.assertEqual(response.status_code, 201, response.data)
        record = Appointment.objects.get(pk=response.data["id"])
        self.assertEqual(record.responsible_user, self.owner)
        self.assertEqual(record.end_at, self.start + timedelta(minutes=30))
        detail = self.api.get(f"/api/appointments/{record.pk}/")
        self.assertEqual(detail.data["responsible_user"], self.owner.pk)
        self.assertEqual(detail.data["responsible_user_name"], "Record Owner")
        self.assertEqual(detail.data["id"], response.data["id"])

    def test_closed_source_is_provenance_without_transition(self):
        response = self.create(source_conversation=self.conversation.pk, responsible_user=self.staff.pk)
        self.assertEqual(response.status_code, 201, response.data)
        record = Appointment.objects.get(pk=response.data["id"])
        self.lead.refresh_from_db()
        self.assertEqual(self.lead.status, "lost")
        self.assertEqual(record.lead_id, self.lead.pk)
        self.assertEqual(record.source_conversation_id, self.conversation.pk)
        self.assertEqual(appointment_responsible_user(record), self.staff)

    def test_assignment_does_not_grant_view(self):
        response = self.create(responsible_user=self.staff.pk)
        self.assertEqual(response.status_code, 201, response.data)
        record = Appointment.objects.get(pk=response.data["id"])
        role = BusinessRole.objects.get(business=self.business, preset_key="specialist")
        RolePermission.objects.update_or_create(business_role=role, resource=Resources.APPOINTMENTS, action=Actions.VIEW,
            defaults={"is_allowed": True, "scope": RolePermission.Scopes.OWN})
        self.assertFalse(can(self.staff, self.business, Resources.APPOINTMENTS, Actions.VIEW, obj=record).allowed)
        self.api.force_authenticate(self.staff)
        self.assertEqual(self.api.get(f"/api/appointments/{record.pk}/").status_code, 404)

    def test_disabled_responsible_rejected_and_no_fallback_after_disable(self):
        response = self.create(responsible_user=self.staff.pk)
        self.assertEqual(response.status_code, 201, response.data)
        record = Appointment.objects.get(pk=response.data["id"])
        BusinessMember.objects.filter(business=self.business, user=self.staff).update(is_active=False)
        self.assertIsNone(appointment_responsible_user(record))
        response = self.create(responsible_user=self.staff.pk, start_at=(self.start + timedelta(hours=1)).isoformat())
        self.assertEqual(response.status_code, 400, response.data)
        self.assertEqual(Appointment.objects.count(), 1)

    def test_specialist_required_and_room_rejected(self):
        for value in (None, 0):
            self.assertEqual(self.create(resource=value).status_code, 400)
        self.resource.resource_type = "room"
        self.resource.save(update_fields=["resource_type"])
        self.assertEqual(self.create().status_code, 400)
        self.assertFalse(Appointment.objects.exists())

    def test_tenant_and_mismatched_source_denial(self):
        other = Business.objects.create(owner=self.staff, name="Other", slug="record-other")
        foreign = Client.objects.create(business=other, full_name="Foreign")
        self.assertEqual(self.create(client=foreign.pk).status_code, 400)
        local = Client.objects.create(business=self.business, full_name="Another")
        self.assertEqual(self.create(client=local.pk, source_conversation=self.conversation.pk).status_code, 400)
        self.assertFalse(Appointment.objects.exists())

    def test_slot_conflict_and_retry_new_slot(self):
        self.assertEqual(self.create().status_code, 201)
        self.assertEqual(self.create().status_code, 409)
        self.assertEqual(self.create(start_at=(self.start + timedelta(hours=1)).isoformat()).status_code, 201)

    def test_idempotent_replay_reads_current_record(self):
        url = "/api/appointments/create-record/"
        response = self.api.post(url, self.payload, format="json", HTTP_IDEMPOTENCY_KEY="record-replay")
        self.assertEqual(response.status_code, 201, response.data)
        record = Appointment.objects.get(pk=response.data["id"])
        record.notes = "Current note"
        record.save(update_fields=["notes"])
        replay = self.api.post(url, self.payload, format="json", HTTP_IDEMPOTENCY_KEY="record-replay")
        self.assertEqual(replay.status_code, 201, replay.data)
        self.assertEqual(replay.data["notes"], "Current note")
        self.assertEqual(Appointment.objects.count(), 1)
        conflict = self.api.post(url, {**self.payload, "notes": "Changed"}, format="json", HTTP_IDEMPOTENCY_KEY="record-replay")
        self.assertEqual(conflict.status_code, 409)

    def test_audit_failure_rolls_back_record_and_activity(self):
        before = ActivityEvent.objects.count()
        with patch("apps.scheduling.record_commands.write_actor_audit_log", side_effect=RuntimeError("synthetic audit failure")):
            self.assertEqual(self.create().status_code, 500)
        self.assertFalse(Appointment.objects.exists())
        self.assertEqual(ActivityEvent.objects.count(), before)
        self.assertEqual(self.create().status_code, 201)

    def test_inbox_command_repeats_closed_lead_without_reopening(self):
        payload = {**self.payload, "source_conversation": self.conversation.pk, "responsible_user": self.staff.pk}
        url = "/api/appointments/create-record/"
        response = self.api.post(url, payload, format="json", HTTP_IDEMPOTENCY_KEY="closed-source")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["source_conversation"], self.conversation.pk)
        self.lead.refresh_from_db()
        self.assertEqual(self.lead.status, "lost")
        replay = self.api.post(url, payload, format="json", HTTP_IDEMPOTENCY_KEY="closed-source")
        self.assertEqual(replay.data["id"], response.data["id"])
        context = self.api.get(f"/api/inbox/conversations/{self.conversation.pk}/context/")
        self.assertEqual(context.data["appointments"]["kind"], "conversation")
        self.assertEqual(context.data["appointments"]["items"][0]["id"], response.data["id"])

    def test_stale_price_and_duration_require_review(self):
        self.assertEqual(self.create(expected_price="900.00", expected_duration_minutes=30).status_code, 409)
        self.assertEqual(self.create(expected_price="1000.00", expected_duration_minutes=60).status_code, 409)
        self.assertFalse(Appointment.objects.exists())
        self.assertEqual(self.create(expected_price="1000.00", expected_duration_minutes=30).status_code, 201)

    def test_stale_actions_cannot_overwrite_current_record(self):
        created = self.create()
        self.assertEqual(created.status_code, 201, created.data)
        pk, version = created.data["id"], created.data["updated_at"]
        confirmed = self.api.post(f"/api/appointments/{pk}/confirm/", {"expected_updated_at": version}, format="json")
        self.assertEqual(confirmed.status_code, 200, confirmed.data)
        for action, payload in (("cancel", {"reason": "Changed plan"}), ("complete", {}),
                                ("reschedule", {"start_at": (self.start + timedelta(hours=1)).isoformat()})):
            with self.subTest(action=action):
                response = self.api.post(f"/api/appointments/{pk}/{action}/", {"expected_updated_at": version, **payload}, format="json")
                self.assertEqual(response.status_code, 409, response.data)
        record = Appointment.objects.get(pk=pk)
        self.assertEqual(record.status, "confirmed")
        self.assertEqual(record.start_at, self.start)
        cancelled = self.api.post(f"/api/appointments/{pk}/cancel/",
            {"reason": "Changed plan", "expected_updated_at": confirmed.data["updated_at"]}, format="json")
        self.assertEqual(cancelled.status_code, 200, cancelled.data)
        self.assertEqual(cancelled.data["id"], pk)
        self.assertEqual(cancelled.data["responsible_user"], self.owner.pk)

    def test_current_create_permission_and_source_update_are_required(self):
        role = BusinessRole.objects.get(business=self.business, preset_key="specialist")
        RolePermission.objects.update_or_create(business_role=role, resource=Resources.APPOINTMENTS, action=Actions.CREATE,
            defaults={"is_allowed": False, "scope": "business"})
        self.api.force_authenticate(self.staff)
        self.assertEqual(self.create().status_code, 403)
        RolePermission.objects.filter(business_role=role, resource=Resources.APPOINTMENTS, action=Actions.CREATE).update(is_allowed=True)
        RolePermission.objects.update_or_create(business_role=role, resource=Resources.CONVERSATIONS, action=Actions.UPDATE,
            defaults={"is_allowed": False, "scope": "business"})
        self.assertEqual(self.create(source_conversation=self.conversation.pk).status_code, 403)
        self.assertFalse(Appointment.objects.exists())

    def test_post_creation_failure_rolls_back_all_effects(self):
        before = ActivityEvent.objects.count()
        audits, notifications = AuditLog.objects.count(), Notification.objects.count()
        with patch("apps.scheduling.services.run_automations_for_event", side_effect=RuntimeError("synthetic automation failure")):
            self.assertEqual(self.create().status_code, 500)
        self.assertFalse(Appointment.objects.exists())
        self.assertEqual(ActivityEvent.objects.count(), before)
        self.assertEqual(AuditLog.objects.count(), audits)
        self.assertEqual(Notification.objects.count(), notifications)

    def test_past_time_rejected_and_legacy_lead_link_preserved(self):
        self.assertEqual(self.create(start_at=(self.start - timedelta(days=5)).isoformat()).status_code, 400)
        response = self.create(lead=self.lead.pk)
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["lead"], self.lead.pk)
        self.lead.refresh_from_db()
        self.assertEqual(self.lead.status, "lost")

    def test_owner_without_legacy_membership_can_be_default_responsible(self):
        BusinessMember.objects.filter(business=self.business, user=self.owner).delete()
        response = self.create()
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["responsible_user"], self.owner.pk)

    def test_create_and_replay_obey_current_read_and_client_permissions(self):
        role = BusinessRole.objects.get(business=self.business, preset_key="specialist")
        for resource, action, allowed in ((Resources.APPOINTMENTS, Actions.CREATE, True),
                                          (Resources.APPOINTMENTS, Actions.VIEW, False),
                                          (Resources.CLIENTS, Actions.VIEW, True)):
            RolePermission.objects.update_or_create(business_role=role, resource=resource, action=action,
                defaults={"is_allowed": allowed, "scope": "business"})
        self.api.force_authenticate(self.staff)
        url = "/api/appointments/create-record/"
        result = self.api.post(url, self.payload, format="json", HTTP_IDEMPOTENCY_KEY="read-denied")
        self.assertEqual(result.status_code, 201, result.data)
        self.assertEqual(result.data, {"read_restricted": True})
        replay = self.api.post(url, self.payload, format="json", HTTP_IDEMPOTENCY_KEY="read-denied")
        self.assertEqual(replay.data, {"read_restricted": True})
        RolePermission.objects.filter(business_role=role, resource=Resources.CLIENTS, action=Actions.VIEW).update(is_allowed=False)
        denied = self.api.post(url, self.payload, format="json", HTTP_IDEMPOTENCY_KEY="read-denied")
        self.assertEqual(denied.status_code, 403, denied.data)
        self.assertEqual(Appointment.objects.count(), 1)
