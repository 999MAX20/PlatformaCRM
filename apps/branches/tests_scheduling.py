from datetime import datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.businesses.models import Business, BusinessMember
from apps.clients.models import Client
from apps.scheduling.models import Appointment, Resource
from apps.services.models import Service
from .models import BranchService, ScheduleDay, SpecialistBranch
from .services import create_branch


class BranchSchedulingTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="multi-owner")
        self.business = Business.objects.create(owner=self.owner, name="Network", slug="network", timezone="Asia/Almaty")
        self.client_record = Client.objects.create(business=self.business, full_name="Patient")
        self.service = Service.objects.create(business=self.business, name="Visit", duration_minutes=30, price_from=10000)
        self.staff = Resource.objects.create(business=self.business, name="Doctor")
        self.first = create_branch(business=self.business, actor=self.owner, name="A", address="Address A")
        self.second = create_branch(business=self.business, actor=self.owner, name="B", address="Address B")
        self.api = APIClient()
        self.api.force_authenticate(self.owner)
        self.start = datetime(2030, 1, 7, 10, tzinfo=ZoneInfo(self.business.timezone))
        self.offer(self.second, 60, "15000.00")
        response = self.post(self.second, "assignments", {"resource": self.staff.pk, "service_ids": [self.service.pk]})
        self.assertEqual(response.status_code, 200, response.data)
        for branch in [self.first, self.second]:
            self.day(branch, None, "09:00", "18:00")
        self.day(self.first, self.staff, "09:00", "12:00")
        self.assertEqual(self.post(self.first, "travel", {"other_branch": self.second.pk, "minutes": 45}).status_code, 200)
        self.day(self.second, self.staff, "13:00", "18:00")

    def post(self, branch, action, values):
        return self.api.post(f"/api/branches/{branch.pk}/{action}/", values, format="json")

    def offer(self, branch, duration, price):
        result = self.post(branch, "offers", {"service": self.service.pk, "duration_minutes": duration, "price_from": price})
        self.assertEqual(result.status_code, 200, result.data)
        return result

    def day(self, branch, staff, start, end, **extra):
        result = self.post(branch, "schedule", {"resource": staff.pk if staff else None, "weekday": 0,
            "intervals": [{"start": start, "end": end}], **extra})
        self.assertEqual(result.status_code, 200, result.data)
        return result

    def book(self, branch, hour=10, **extra):
        data = {"business": self.business.pk, "client": self.client_record.pk, "service": self.service.pk,
                "resource": self.staff.pk, "start_at": self.start.replace(hour=hour).isoformat(), **extra}
        if branch:
            data["branch"] = branch.pk
        return self.api.post("/api/appointments/", data, format="json")

    def test_price_duration_and_location_are_snapshots(self):
        first, second = self.book(self.first), self.book(self.second, 13)
        self.assertEqual(first.status_code, 201, first.data)
        self.assertEqual(second.status_code, 201, second.data)
        visit = Appointment.objects.get(pk=second.data["id"])
        self.assertEqual(visit.end_at - visit.start_at, timedelta(minutes=60))
        self.assertEqual(visit.booked_price, Decimal("15000"))
        self.assertEqual(visit.branch_address, "Address B")
        self.offer(self.second, 90, "22000")
        visit.refresh_from_db()
        self.assertEqual(visit.booked_price, Decimal("15000"))

        response = self.api.post(f"/api/appointments/{visit.pk}/reschedule/", {"start_at": self.start.replace(hour=15).isoformat(), "branch": self.second.pk, "resource": self.staff.pk}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        visit.refresh_from_db()
        self.assertEqual(visit.end_at - visit.start_at, timedelta(minutes=60))
        self.assertEqual(visit.booked_price, Decimal("15000"))

    def test_terms_are_reloaded_after_prevalidation_before_saving(self):
        from unittest.mock import patch
        from apps.scheduling.views import AppointmentViewSet
        from .models import Branch
        original = AppointmentViewSet.perform_create

        def update_terms_then_save(view, serializer):
            BranchService.objects.filter(branch=self.first, service=self.service).update(
                duration_minutes=45, price_from=17000)
            Branch.objects.filter(pk=self.first.pk).update(address="Updated address")
            return original(view, serializer)

        with patch.object(AppointmentViewSet, "perform_create", update_terms_then_save):
            result = self.book(self.first)
        self.assertEqual(result.status_code, 201, result.data)
        visit = Appointment.objects.get(pk=result.data["id"])
        self.assertEqual(visit.booked_price, Decimal("17000"))
        self.assertEqual(visit.booked_duration_minutes, 45)
        self.assertEqual(visit.end_at - visit.start_at, timedelta(minutes=45))
        self.assertEqual(visit.branch_address, "Updated address")

    def test_removing_assignment_requires_future_visit_resolution(self):
        visit = self.book(self.second, 13)
        self.assertEqual(visit.status_code, 201, visit.data)
        for values in [{"is_active": False, "service_ids": [self.service.pk]}, {"service_ids": []}]:
            response = self.post(self.second, "assignments", {"resource": self.staff.pk, **values})
            self.assertEqual(response.status_code, 409, response.data)
        assignment = SpecialistBranch.objects.get(branch=self.second, resource=self.staff)
        self.assertTrue(assignment.is_active)
        self.assertTrue(assignment.services.filter(pk=self.service.pk).exists())
        self.api.post(f'/api/appointments/{visit.data["id"]}/cancel/', {"reason": "Reassigned manually"})
        self.assertEqual(self.post(self.second, "assignments", {"resource": self.staff.pk, "is_active": False, "service_ids": []}).status_code, 200)

    def test_requires_branch_qualified_specialist_and_permission(self):
        self.assertEqual(self.book(None).status_code, 400)
        stranger = Resource.objects.create(business=self.business, name="Unassigned")
        self.assertEqual(self.book(self.first, resource=stranger.pk).status_code, 400)
        admin = User.objects.create_user(username="branch-limited", email="branch-limited@example.test")
        member = BusinessMember.objects.create(business=self.business, user=admin, role="admin")
        grant = self.api.post("/api/branches/member-access/", {"member": member.pk, "branch_ids": [self.first.pk]}, format="json")
        self.assertEqual(grant.status_code, 200)
        self.api.force_authenticate(admin)
        self.assertEqual(self.book(self.second, 13).status_code, 403)
        result = self.book(self.first)
        self.assertEqual(result.status_code, 201, result.data)
        self.assertEqual(self.api.post(f'/api/appointments/{result.data["id"]}/reschedule/', {"branch": self.second.pk, "resource": self.staff.pk, "start_at": self.start.replace(hour=13).isoformat()}, format="json").status_code, 403)

    def test_intervals_travel_and_invalid_update_rollback(self):
        response = self.post(self.second, "schedule", {"resource": self.staff.pk, "weekday": 0,
            "intervals": [{"start": "12:30", "end": "18:00"}]})
        self.assertEqual(response.status_code, 409, response.data)
        row = ScheduleDay.objects.get(branch=self.second, resource=self.staff, weekday=0)
        self.assertEqual(row.intervals[0]["start"], "13:00")
        response = self.post(self.first, "schedule", {"resource": self.staff.pk, "weekday": 0,
            "intervals": [{"start": "09:00", "end": "10:00"}, {"start": "10:30", "end": "12:00"}]})
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(self.book(self.first).status_code, 409)
        self.assertEqual(self.book(self.first, start_at=self.start.replace(minute=30).isoformat()).status_code, 201)
        self.assertEqual(self.book(self.first, start_at=self.start.replace(minute=30).isoformat()).status_code, 409)

    def test_date_override_and_closed_branch(self):
        response = self.post(self.first, "schedule", {"resource": self.staff.pk, "date": "2030-01-07", "intervals": []})
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(self.book(self.first).status_code, 409)
        self.assertEqual(self.post(self.first, "schedule", {"resource": self.staff.pk, "date": "2030-01-07", "remove": True}).status_code, 200)
        self.assertEqual(self.book(self.first).status_code, 201)
        self.second.is_active = False
        self.second.save()
        self.assertEqual(self.book(self.second, 13).status_code, 400)

    def test_cross_branch_busy_time_cannot_be_hidden_by_scope(self):
        # Imported/legacy appointment can outlive a schedule change. It must
        # still block another branch, including the configured travel buffer.
        Appointment.objects.create(business=self.business, branch=self.first, client=self.client_record,
            service=self.service, resource=self.staff, start_at=self.start.replace(hour=12), end_at=self.start.replace(hour=12, minute=30))
        self.assertEqual(self.book(self.second, 13).status_code, 409)
        result = self.book(self.second, 14)
        self.assertEqual(result.status_code, 201, result.data)

    def test_bad_payloads_and_foreign_links_rejected(self):
        self.assertEqual(self.post(self.first, "schedule", {"weekday": 0, "intervals": [{"start": "15:00", "end": "14:00"}]}).status_code, 400)
        self.assertEqual(self.post(self.first, "schedule", {"weekday": 0, "date": "2030-01-07", "intervals": []}).status_code, 400)
        other = Business.objects.create(owner=self.owner, name="Other", slug="other-network")
        service = Service.objects.create(business=other, name="Foreign")
        self.assertEqual(self.post(self.first, "offers", {"service": service.pk, "duration_minutes": 30, "price_from": "0"}).status_code, 400)
        self.assertEqual(BranchService.objects.filter(branch=self.first).count(), 1)

    def test_lead_and_inbox_booking_use_branch_terms_and_reject_scope(self):
        from apps.leads.models import Lead
        from apps.bots.models import Bot, BotConversation
        lead = Lead.objects.create(business=self.business, client=self.client_record)
        result = self.api.post(f"/api/leads/{lead.pk}/create-appointment/", {
            "service": self.service.pk, "resource": self.staff.pk, "branch": self.second.pk,
            "start_at": self.start.replace(hour=13).isoformat()}, format="json")
        self.assertEqual(result.status_code, 201, result.data)
        self.assertEqual(result.data["booked_price"], "15000.00")
        bot = Bot.objects.create(business=self.business, name="Reception")
        conversation = BotConversation.objects.create(business=self.business, bot=bot,
            channel="website", client=self.client_record)
        payload = {"service_id": self.service.pk, "resource_id": self.staff.pk,
                   "branch_id": self.second.pk, "start_at": self.start.replace(hour=15).isoformat()}
        endpoint = f"/api/inbox/conversations/{conversation.pk}/create-appointment/"
        result = self.api.post(endpoint, payload, format="json")
        self.assertEqual(result.status_code, 201, result.data)
        self.assertEqual(result.data["booked_duration_minutes"], 60)
        admin = User.objects.create_user(username="inbox-limited", email="inbox-limited@example.test")
        member = BusinessMember.objects.create(business=self.business, user=admin, role="admin")
        self.api.post("/api/branches/member-access/", {"member": member.pk, "branch_ids": [self.first.pk]}, format="json")
        self.api.force_authenticate(admin)
        self.assertEqual(self.api.post(endpoint, {**payload, "start_at": self.start.replace(hour=16).isoformat()}, format="json").status_code, 403)

    def test_service_value_uses_snapshot_and_preserves_unknown_price(self):
        from django.db.models import Sum
        from apps.scheduling.valuation import appointment_price_expression
        first = self.book(self.first)
        second = self.book(self.second, 13)
        self.assertEqual(first.status_code, 201, first.data)
        self.assertEqual(second.status_code, 201, second.data)
        self.service.price_from = 99999
        self.service.save()
        query = Appointment.objects.filter(business=self.business)
        self.assertEqual(query.aggregate(value=Sum(appointment_price_expression()))["value"], Decimal("25000"))
        query.filter(pk=second.data["id"]).update(booked_price=None)
        self.assertEqual(query.aggregate(value=Sum(appointment_price_expression()))["value"], Decimal("10000"))
