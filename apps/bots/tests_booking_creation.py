from unittest.mock import patch

from django.test import TestCase, override_settings

from apps.bots import tests_automatic_booking as fixtures
from apps.automations.models import AutomationRule, AutomationAction, AutomationRun
from apps.integrations.models import BusinessEvent
from apps.notifications.models import Notification
from apps.scheduling.models import Appointment
from apps.scheduling.services import handle_appointment_created
from apps.tasks.models import Task
from apps.accounts.models import User
from apps.businesses.models import BusinessMember, BusinessRole
from apps.businesses.access import ensure_default_roles


@override_settings(AUTOMATIONS_RUN_INLINE=True)
class BookingCreationTests(TestCase):
    def setUp(self):
        fixtures.AutomaticBookingTests.setUp(self)
        self.business.ai_booking_responsible_user = self.business.owner
        self.business.save(update_fields=["ai_booking_responsible_user"])
        self.rule = AutomationRule.objects.create(business=self.business, name="Booking preparation",
            trigger_type="appointment_created", is_active=True)
        AutomationAction.objects.create(rule=self.rule, order=1, action_type="create_task",
            config={"title": "Prepare this appointment"})

    def book(self):
        with patch("apps.bots.inbox_service.send_outbound_message", return_value=None):
            return fixtures.AutomaticBookingTests.book(self)

    def test_automatic_booking_keeps_context_and_runs_creation_once(self):
        result = self.book()
        self.assertEqual(result.status, "booked", result.reason)
        self.assertEqual(result.appointment.responsible_user_id, self.business.owner_id)
        self.assertEqual(result.appointment.source_conversation_id, self.conversation.pk)
        self.assertEqual(AutomationRun.objects.filter(rule=self.rule, status="success").count(), 1)
        self.assertEqual(Task.objects.filter(title="Prepare this appointment").count(), 1)
        self.assertEqual(BusinessEvent.objects.filter(business=self.business, event_type="appointment.created").count(), 1)
        count = Notification.objects.filter(appointment=result.appointment).count()
        self.conversation.refresh_from_db()
        self.assertEqual(self.book().appointment.pk, result.appointment.pk)
        handle_appointment_created(result.appointment)
        self.assertEqual(Notification.objects.filter(appointment=result.appointment).count(), count)
        self.assertEqual(AutomationRun.objects.filter(rule=self.rule).count(), 1)

    def test_missing_setting_requires_staff_without_owner_fallback(self):
        self.business.ai_booking_responsible_user = None
        self.business.save(update_fields=["ai_booking_responsible_user"])
        self.assertEqual(self.book().status, "requires_staff")
        self.assertFalse(Appointment.objects.exists())
        self.assertFalse(AutomationRun.objects.filter(rule=self.rule).exists())

    def test_creation_handler_failure_rolls_back_all_creation_state(self):
        with patch("apps.scheduling.services.run_automations_for_event", side_effect=RuntimeError("synthetic orchestration failure")):
            with self.assertRaisesRegex(RuntimeError, "synthetic orchestration"):
                self.book()
        self.assertFalse(Appointment.objects.exists())
        self.assertFalse(BusinessEvent.objects.filter(event_type="appointment.created").exists())
        self.assertFalse(Notification.objects.filter(appointment__isnull=False).exists())
        self.conversation.refresh_from_db()
        self.assertFalse(self.conversation.metadata_json["auto_booking"].get("booked_slots"))

    def assignee(self):
        user = User.objects.create_user(username="booking-assignee", email="assignee@example.test")
        ensure_default_roles(self.business)
        member = BusinessMember.objects.create(business=self.business, user=user, role="specialist",
            business_role=BusinessRole.objects.get(business=self.business, preset_key="specialist"))
        self.business.ai_booking_responsible_user = user
        self.business.save(update_fields=["ai_booking_responsible_user"])
        return user, member

    def test_current_default_is_distinct_from_actor_and_replay_preserves_original(self):
        user, member = self.assignee()
        result = self.book()
        self.assertEqual(result.status, "booked", result.reason)
        self.assertEqual(result.appointment.responsible_user_id, user.pk)
        self.assertNotEqual(user.pk, self.bot.settings_json["_automatic_actor_id"])
        self.business.ai_booking_responsible_user = None
        self.business.save(update_fields=["ai_booking_responsible_user"])
        self.conversation.refresh_from_db()
        again = self.book()
        self.assertEqual(again.appointment.pk, result.appointment.pk)
        self.assertEqual(again.appointment.responsible_user_id, user.pk)
        self.assertEqual(Task.objects.filter(title="Prepare this appointment").count(), 1)

    def test_revoked_unavailable_foreign_and_disabled_default_refuse_without_effects(self):
        user, member = self.assignee()
        for state in ("membership", "availability", "foreign", "login"):
            with self.subTest(state=state):
                member.is_active = state != "membership"
                member.availability_status = "unavailable" if state == "availability" else "available"
                member.save()
                user.is_active = state != "login"
                user.save(update_fields=["is_active"])
                if state == "foreign":
                    self.business.ai_booking_responsible_user = User.objects.create_user(
                        username="foreign-assignee", email="foreign-assignee@example.test")
                else:
                    self.business.ai_booking_responsible_user = user
                self.business.save(update_fields=["ai_booking_responsible_user"])
                result = self.book()
                self.assertEqual(result.status, "requires_staff", result.reason)
                self.assertFalse(Appointment.objects.exists())
                self.assertFalse(BusinessEvent.objects.filter(event_type="appointment.created").exists())
                self.assertFalse(AutomationRun.objects.filter(rule=self.rule).exists())

    def test_assignee_branch_grant_is_required(self):
        from apps.branches.services import create_branch
        from apps.conversations.booking import create_appointment_from_conversation
        from rest_framework.exceptions import PermissionDenied
        user, member = self.assignee()
        branch = create_branch(business=self.business, actor=self.business.owner, name="North", address="North address")
        from apps.branches.models import BranchAccess
        BranchAccess.objects.get(member=member).branches.clear()
        with self.assertRaises(PermissionDenied):
            create_appointment_from_conversation(conversation=self.conversation, actor=self.business.owner,
                service_id=self.service.pk, resource_id=self.resource.pk, branch_id=branch.pk,
                start_at=self.start, expected_terms={"price_from": None, "duration_minutes": 30})
        self.assertFalse(Appointment.objects.exists())
        self.assertFalse(AutomationRun.objects.exists())

    def test_authorizing_actor_own_scope_cannot_assign_default_to_another_user(self):
        from apps.businesses.access import Actions, Resources
        from apps.businesses.models import RolePermission
        from apps.conversations.booking import create_appointment_from_conversation
        from rest_framework.exceptions import PermissionDenied
        user, member = self.assignee()
        self.business.ai_booking_responsible_user = self.business.owner
        self.business.save(update_fields=["ai_booking_responsible_user"])
        RolePermission.objects.update_or_create(business_role=member.business_role,
            resource=Resources.APPOINTMENTS, action=Actions.CREATE,
            defaults={"is_allowed": True, "scope": RolePermission.Scopes.OWN})
        with self.assertRaises(PermissionDenied):
            create_appointment_from_conversation(conversation=self.conversation, actor=user,
                service_id=self.service.pk, resource_id=self.resource.pk, start_at=self.start,
                expected_terms={"price_from": None, "duration_minutes": 30})
        self.assertFalse(Appointment.objects.exists())
