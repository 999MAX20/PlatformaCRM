from datetime import datetime, time, timedelta
from unittest.mock import patch
from zoneinfo import ZoneInfo

from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.businesses.models import Business, BusinessMember
from apps.clients.models import Client
from apps.core.domain_errors import InvalidTransition
from apps.scheduling.availability import get_available_slots
from apps.scheduling.models import Appointment, Resource, WorkingHours
from apps.scheduling.record_commands import create_record
from apps.services.models import Service
from .access import accessible_branches
from .models import Branch, BranchAccess
from .services import create_branch
from .single_location import ensure_initial_location
from .staff_lifecycle import change_branch_state


class SingleLocationTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="one-point", role="business_owner")
        self.business = Business.objects.create(owner=self.owner, name="One point", slug="one-point", timezone="Asia/Almaty")
        self.service = Service.objects.create(business=self.business, name="Consultation", duration_minutes=30, price_from=12000)
        self.staff = Resource.objects.create(business=self.business, name="Anna")
        self.client_record = Client.objects.create(business=self.business, full_name="Client")
        self.start = datetime(2030, 1, 7, 10, tzinfo=ZoneInfo(self.business.timezone))
        WorkingHours.objects.create(business=self.business, weekday=0, start_time=time(9), end_time=time(18))
        self.api = APIClient()
        self.api.force_authenticate(self.owner)

    def test_initial_location_is_idempotent_and_uses_current_catalog_and_hours(self):
        before = get_available_slots(self.business, self.service, self.start.date(), resource=self.staff)
        branch = ensure_initial_location(self.business)
        self.assertEqual(ensure_initial_location(self.business).pk, branch.pk)
        self.assertTrue(branch.uses_business_defaults)
        self.assertEqual(before, get_available_slots(self.business, self.service, self.start.date(), resource=self.staff))
        self.service.price_from = 14000
        self.service.save()
        visit = create_record(business=self.business, actor=self.owner, client=self.client_record,
            service=self.service, resource=self.staff, start_at=self.start)
        self.assertEqual(visit.branch_id, branch.pk)
        self.assertEqual(visit.booked_price, 14000)
        self.assertFalse(branch.service_offers.exists())
        self.assertFalse(branch.specialist_assignments.exists())

    def test_second_branch_preserves_first_settings_and_starts_unconfigured(self):
        initial = ensure_initial_location(self.business)
        before = get_available_slots(self.business, self.service, self.start.date(), resource=self.staff)
        visit = create_record(business=self.business, actor=self.owner, client=self.client_record,
            service=self.service, resource=self.staff, start_at=self.start)
        second = create_branch(business=self.business, actor=self.owner, name="Second")
        initial.refresh_from_db()
        self.assertFalse(initial.uses_business_defaults)
        self.assertEqual(get_available_slots(self.business, self.service, self.start.date(), resource=self.staff,
            branch=initial, exclude_appointment=visit), before)
        self.assertTrue(initial.service_offers.filter(service=self.service).exists())
        self.assertFalse(second.service_offers.exists())
        self.assertFalse(second.specialist_assignments.exists())
        visit.refresh_from_db()
        self.assertEqual(visit.branch_id, initial.pk)

    def test_second_branch_failure_rolls_back_conversion(self):
        initial = ensure_initial_location(self.business)
        with patch("apps.branches.services.write_actor_audit_log", side_effect=RuntimeError("audit failure")):
            with self.assertRaises(RuntimeError):
                create_branch(business=self.business, actor=self.owner, name="Second")
        initial.refresh_from_db()
        self.assertTrue(initial.uses_business_defaults)
        self.assertEqual(Branch.objects.count(), 1)
        self.assertFalse(initial.service_offers.exists())

    def test_reschedule_retains_booked_terms_after_live_catalog_changes(self):
        from apps.scheduling.services import reschedule_appointment
        branch = ensure_initial_location(self.business)
        visit = create_record(business=self.business, actor=self.owner, client=self.client_record,
            service=self.service, resource=self.staff, start_at=self.start)
        self.service.price_from = 20000
        self.service.duration_minutes = 60
        self.service.save()
        late = self.start.replace(hour=17, minute=30)
        self.assertIn(late, get_available_slots(self.business, self.service, late.date(),
            resource=self.staff, branch=branch, exclude_appointment=visit))
        reschedule_appointment(appointment=visit, start_at=late, resource=self.staff, actor=self.owner)
        visit.refresh_from_db()
        self.assertEqual(visit.booked_price, 12000)
        self.assertEqual(visit.booked_duration_minutes, 30)
        self.assertEqual(visit.end_at - visit.start_at, timedelta(minutes=30))

    def test_last_active_cannot_be_archived_or_bypassed_by_pausing(self):
        branch = ensure_initial_location(self.business)
        for state in ("active", "paused"):
            change_branch_state(branch=branch, actor=self.owner, state=state)
            with self.assertRaises(InvalidTransition):
                change_branch_state(branch=branch, actor=self.owner, state="archived")
        branch.refresh_from_db()
        self.assertIsNone(branch.archived_at)

    def test_other_paused_or_foreign_branch_does_not_allow_archival(self):
        branch = ensure_initial_location(self.business)
        create_branch(business=self.business, actor=self.owner, name="Paused", is_active=False)
        other = Business.objects.create(owner=self.owner, name="Other", slug="other-point")
        ensure_initial_location(other)
        with self.assertRaises(InvalidTransition):
            change_branch_state(branch=branch, actor=self.owner, state="archived")

    def test_archiving_one_of_two_keeps_history_and_other_active(self):
        branch = ensure_initial_location(self.business)
        second = create_branch(business=self.business, actor=self.owner, name="Second")
        change_branch_state(branch=branch, actor=self.owner, state="archived")
        self.assertEqual(Branch.objects.filter(business=self.business).count(), 2)
        second.refresh_from_db()
        self.assertTrue(second.is_active)

    def test_all_archived_setup_is_not_silently_restored(self):
        branch = Branch.objects.create(business=self.business, name="Old", is_active=False,
            archived_at=self.start - timedelta(days=3650))
        self.assertEqual(ensure_initial_location(self.business).pk, branch.pk)
        self.assertFalse(Branch.objects.filter(business=self.business, is_active=True).exists())

    def test_members_inherit_only_initial_location_until_explicit_grant(self):
        user = User.objects.create_user(username="point-member", email="point-member@example.test")
        member = BusinessMember.objects.create(business=self.business, user=user, role="admin")
        initial = ensure_initial_location(self.business)
        self.assertEqual(list(accessible_branches(user, self.business)), [initial])
        second = create_branch(business=self.business, actor=self.owner, name="Second")
        self.assertEqual(list(accessible_branches(user, self.business)), [initial])
        self.assertFalse(accessible_branches(user, self.business).filter(pk=second.pk).exists())
        grant = BranchAccess.objects.get(member=member)
        grant.branches.clear()
        self.assertFalse(accessible_branches(user, self.business).exists())

    def test_business_api_creation_includes_automatic_location(self):
        response = self.api.post("/api/businesses/", {"name": "Created", "slug": "created-point"}, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertTrue(Branch.objects.get(business_id=response.data["id"]).uses_business_defaults)

    def test_catalog_exposes_new_services_and_specialists_without_branch_setup(self):
        branch = ensure_initial_location(self.business)
        service = Service.objects.create(business=self.business, name="New service", duration_minutes=45)
        resource = Resource.objects.create(business=self.business, name="New specialist")
        response = self.api.get(f"/api/branches/{branch.pk}/catalog/")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual({row["service"] for row in response.data["offers"]}, {self.service.pk, service.pk})
        assignment = next(row for row in response.data["assignments"] if row["resource"] == resource.pk)
        self.assertIn(service.pk, assignment["service_ids"])
        self.assertTrue(any(row["resource"] == resource.pk and row["weekday"] == 0 and row["intervals"]
            for row in response.data["days"]))
        self.assertFalse(branch.service_offers.exists())

    def test_primary_details_follow_business_but_explicit_location_does_not(self):
        branch = ensure_initial_location(self.business)
        self.business.address = "New address"
        self.business.save(update_fields=["address"])
        branch.refresh_from_db()
        self.assertEqual(branch.address, "New address")
        create_branch(business=self.business, actor=self.owner, name="Second")
        self.business.address = "Later address"
        self.business.save(update_fields=["address"])
        branch.refresh_from_db()
        self.assertEqual(branch.address, "New address")

    def test_branch_configuration_cannot_override_automatic_defaults(self):
        branch = ensure_initial_location(self.business)
        response = self.api.post(f"/api/branches/{branch.pk}/offers/", {
            "service": self.service.pk, "duration_minutes": 10, "price_from": "1", "is_active": True}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertFalse(branch.service_offers.exists())

    def test_public_booking_keeps_automatic_location_and_current_terms(self):
        from apps.bots.models import Bot, BotConversation, BotMessage
        from apps.bots.scheduling_context import build_bot_scheduling_context
        branch = ensure_initial_location(self.business)
        bot = Bot.objects.create(business=self.business, name="Booking")
        thread = BotConversation.objects.create(business=self.business, bot=bot, channel="telegram", external_thread_id="single-location")
        BotMessage.objects.create(conversation=thread, direction="inbound", text="Book Consultation with Anna")
        with patch("apps.branches.bot_context.timezone.now", return_value=self.start - timedelta(hours=2)):
            context = build_bot_scheduling_context(thread, days=1)
        self.assertEqual(context["branch_selection"], branch.pk)
        self.assertTrue(context["next_available_slots"], context)
        self.assertEqual(context["next_available_slots"][0]["branch_id"], branch.pk)
