from copy import deepcopy

from django.test import TestCase, override_settings
from django.utils.dateparse import parse_datetime
from rest_framework.exceptions import ValidationError

from apps.ai_core import tests_voice_schedule as fixtures
from apps.ai_core.voice_schedule_commands import validate_schedule
from apps.branches.physical_resources import save_resource_requirements
from apps.branches.tests_legacy_fixtures import ensure_legacy_initial_location as ensure_initial_location
from apps.clients.models import Client
from apps.scheduling.models import Appointment, Resource
from apps.scheduling.record_commands import create_record
from apps.scheduling.resource_services import create_resource


@override_settings(AI_PROVIDER="mock", AI_ENABLED=True, VOICE_INPUT_ENABLED=True, AI_QUEUE_LIVE_REQUESTS=False)
class AIResourceBookingTests(TestCase):
    visit = fixtures.VoiceScheduleCommandTests.visit
    draft = fixtures.VoiceScheduleConversationTests.draft
    run_turn = fixtures.VoiceScheduleConversationTests.run_turn

    def setUp(self):
        fixtures.VoiceScheduleConversationTests.setUp(self)
        self.branch = ensure_initial_location(self.business)
        self.device = create_resource(business=self.business, name="Device", resource_type="equipment")
        save_resource_requirements(branch=self.branch, actor=self.owner, service_id=self.service.pk, resource_ids=[self.device.pk])

    def test_voice_creates_joint_reservation_and_replays_without_duplicate(self):
        turn = self.run_turn(self.draft())
        self.assertEqual(turn.status, "completed", turn.error_code)
        visit = Appointment.objects.get()
        self.assertEqual(list(visit.reserved_resources.values_list("resource_id", flat=True)), [self.device.pk])
        self.assertEqual(self.run_turn(self.draft()).pk, turn.pk)
        self.assertEqual(Appointment.objects.count(), 1)

    def test_voice_asks_for_other_time_without_creating_client_when_equipment_busy(self):
        client = Client.objects.create(business=self.business, full_name="Already booked")
        other = Resource.objects.create(business=self.business, name="Other specialist")
        create_record(business=self.business, actor=self.owner, client=client, service=self.service,
            resource=other, branch=self.branch, start_at=parse_datetime(self.visit()["start_at"]))
        turn = self.run_turn(self.draft())
        self.assertEqual(turn.status, "clarifying", turn.error_code)
        self.assertEqual(Client.objects.count(), 1)
        self.assertEqual(Appointment.objects.count(), 1)

    def test_plan_checks_shared_equipment_between_different_specialists_before_writes(self):
        other = Resource.objects.create(business=self.business, name="Other specialist")
        values = deepcopy(self.values)
        values.update(plan=True, visits=[self.visit(), {**self.visit(), "resource": other.pk}])
        with self.assertRaises(ValidationError) as failure:
            validate_schedule(business=self.business, user=self.owner, values=values)
        self.assertIn("start_at", failure.exception.detail)
        self.assertFalse(Client.objects.exists())
        self.assertFalse(Appointment.objects.exists())
