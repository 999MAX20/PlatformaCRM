from datetime import time, timedelta
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone
from rest_framework.exceptions import APIException

from apps.accounts.models import User
from apps.businesses.models import Business
from apps.clients.models import Client
from apps.core.models import AuditLog
from apps.integrations.models import BusinessEvent
from apps.notifications.models import Notification
from apps.scheduling.import_commands import create_imported_record
from apps.scheduling.models import Appointment, Resource, WorkingHours
from apps.services.models import Service


class ImportedRecordTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="import-record", email="record@example.test", role="business_owner")
        self.business = Business.objects.create(owner=self.owner, name="Import record", slug="import-record", timezone="UTC")
        self.client_record = Client.objects.create(business=self.business, full_name="Client")
        self.service = Service.objects.create(business=self.business, name="Service", duration_minutes=30, price_from=0)
        self.specialist = Resource.objects.create(business=self.business, name="Specialist")
        for day in range(7):
            WorkingHours.objects.create(business=self.business, weekday=day, start_time=time(8), end_time=time(20))
        self.start = (timezone.now() + timedelta(days=2)).replace(hour=10, minute=0, second=0, microsecond=0)

    def create(self, **kwargs):
        values = dict(business=self.business, actor=self.owner, client=self.client_record, service=self.service,
            specialist=self.specialist, start_at=self.start, import_reference="workspace:1:row:1")
        values.update(kwargs)
        return create_imported_record(**values)

    @patch("apps.scheduling.services.handle_appointment_created")
    def test_future_import_preserves_price_audit_and_has_no_creation_effects(self, effects):
        record = self.create()
        self.assertEqual(record.booked_price, 0)
        self.assertEqual(record.responsible_user_id, self.owner.pk)
        self.assertEqual(record.end_at, self.start + timedelta(minutes=30))
        self.assertTrue(AuditLog.objects.filter(entity_id=str(record.pk), metadata__kind="import").exists())
        self.assertTrue(BusinessEvent.objects.filter(event_type="appointment.imported").exists())
        self.assertFalse(BusinessEvent.objects.filter(event_type="appointment.created").exists())
        self.assertFalse(Notification.objects.exists())
        effects.assert_not_called()

    def test_completed_history_is_preserved_without_payments_or_notifications(self):
        record = self.create(start_at=self.start - timedelta(days=4), status="completed")
        self.assertEqual(record.status, "completed")
        self.assertFalse(Notification.objects.exists())

    def test_invalid_status_reason_and_future_completion_have_no_partial_effect(self):
        for overrides in [{"status": "completed"}, {"status": "cancelled"}, {"status": "rescheduled"}, {"status": "unknown"}]:
            with self.subTest(overrides=overrides), self.assertRaises(APIException):
                self.create(**overrides)
        self.assertFalse(Appointment.objects.exists())
        self.assertFalse(BusinessEvent.objects.exists())

    def test_overlap_and_closed_hours_remain_blocked(self):
        self.create()
        with self.assertRaises(APIException):
            self.create(start_at=self.start + timedelta(minutes=10))
        with self.assertRaises(APIException):
            self.create(start_at=self.start.replace(hour=23))
        self.assertEqual(Appointment.objects.count(), 1)

    def test_cross_tenant_reference_rejected(self):
        other = Business.objects.create(owner=self.owner, name="Other", slug="other-import")
        foreign = Client.objects.create(business=other, full_name="Foreign")
        with self.assertRaises(APIException):
            self.create(client=foreign)
        self.assertFalse(Appointment.objects.exists())

    def test_inactive_specialist_cannot_be_reactivated_by_import(self):
        self.specialist.is_active = False
        self.specialist.save()
        with self.assertRaises(APIException):
            self.create()
        self.specialist.refresh_from_db()
        self.assertFalse(self.specialist.is_active)

    def test_import_rechecks_role_and_branch_scope(self):
        from apps.businesses.models import BusinessMember, BusinessRole
        from apps.branches.models import Branch, BranchService, SpecialistBranch
        staff = User.objects.create_user(username="import-scope", email="scope@example.test", role="staff")
        role = BusinessRole.objects.create(business=self.business, name="No import writes")
        membership = BusinessMember.objects.create(business=self.business, user=staff, role="specialist", business_role=role)
        with self.assertRaises(APIException):
            self.create(actor=staff)
        membership.role = "manager"
        membership.business_role = None
        membership.save(update_fields=["role", "business_role"])
        branch = Branch.objects.create(business=self.business, name="Restricted")
        BranchService.objects.create(business=self.business, branch=branch, service=self.service,
            duration_minutes=30, price_from=0)
        assignment = SpecialistBranch.objects.create(business=self.business, branch=branch, resource=self.specialist)
        assignment.services.add(self.service)
        with self.assertRaises(APIException) as denied:
            self.create(actor=staff)
        self.assertIn("branch", str(denied.exception).lower())
        self.assertFalse(Appointment.objects.exists())
        self.assertFalse(BusinessEvent.objects.exists())
