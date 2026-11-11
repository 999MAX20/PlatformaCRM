from copy import deepcopy

from django.test import TestCase, override_settings
from django.utils import timezone

from apps.ai_core.agent_runtime import bind_thread
from apps.ai_core import tests_voice_schedule as fixtures
from apps.ai_core.voice_schedule_planner import COPY, resolve_schedule
from apps.branches.configuration import save_assignment, save_offer
from apps.branches.models import Branch, BranchService, SpecialistBranch
from apps.branches.services import create_branch
from apps.branches.tests_legacy_fixtures import ensure_legacy_initial_location as ensure_initial_location
from apps.clients.models import Client
from apps.scheduling.models import Appointment


@override_settings(AI_PROVIDER="mock", AI_ENABLED=True, VOICE_INPUT_ENABLED=True, AI_QUEUE_LIVE_REQUESTS=False)
class VoiceLocationTests(TestCase):
    setUp = fixtures.VoiceScheduleConversationTests.setUp
    visit = fixtures.VoiceScheduleCommandTests.visit
    draft = fixtures.VoiceScheduleConversationTests.draft
    run_turn = fixtures.VoiceScheduleConversationTests.run_turn

    def test_single_automatic_location_books_without_extra_setup(self):
        branch = ensure_initial_location(self.business)
        turn = self.run_turn(self.draft())
        self.assertEqual(turn.status, "completed", turn.error_code)
        self.assertEqual(Appointment.objects.get().branch_id, branch.pk)
        self.assertFalse(branch.service_offers.exists())

    def test_archived_only_branch_and_past_date_have_specific_messages(self):
        Branch.objects.create(business=self.business, name="Old", is_active=False, archived_at=timezone.now())
        draft = self.draft()
        draft["visits"][0]["date"] = "2020-10-07"
        turn = self.run_turn(draft)
        self.assertEqual(turn.status, "clarifying", turn.error_code)
        self.assertIn("Нет действующего филиала", turn.response)
        self.assertIn("07.10.2020 12:00", turn.response)
        self.assertNotIn("выбранные условия недоступны", turn.response)
        self.assertEqual(turn.context_json["schedule_draft"]["client_name"], draft["client_name"])
        self.assertFalse(Client.objects.exists())
        self.assertFalse(Appointment.objects.exists())

    def test_explicit_branch_without_service_reports_service_mapping(self):
        branch = create_branch(business=self.business, actor=self.owner, name="North")
        BranchService.objects.filter(branch=branch).delete()
        turn = self.run_turn(self.draft())
        self.assertIn("услуга недоступна в выбранном филиале", turn.response)
        self.assertFalse(Appointment.objects.exists())

    def test_explicit_branch_without_assignment_reports_specialist_mapping(self):
        branch = create_branch(business=self.business, actor=self.owner, name="North")
        SpecialistBranch.objects.filter(branch=branch).delete()
        turn = self.run_turn(self.draft())
        self.assertIn("специалист не оказывает эту услугу", turn.response)

    def test_multiple_suitable_branches_ask_only_for_branch(self):
        first = create_branch(business=self.business, actor=self.owner, name="North")
        second = create_branch(business=self.business, actor=self.owner, name="South")
        save_offer(branch=second, actor=self.owner, service_id=self.service.pk, duration_minutes=30, price_from=100)
        save_assignment(branch=second, actor=self.owner, resource_id=self.resource.pk, service_ids=[self.service.pk])
        turn = self.run_turn(self.draft())
        self.assertEqual(turn.status, "clarifying", turn.error_code)
        self.assertIn("Уточните филиал", turn.response)
        self.assertIn("North", turn.response)
        self.assertIn("South", turn.response)
        draft = deepcopy(turn.context_json["schedule_draft"])
        draft["visits"][0]["branch"] = "North"
        followup = self.run_turn(draft, key="branch-answer", message="North")
        self.assertEqual(followup.status, "completed", followup.response)
        self.assertEqual(Appointment.objects.get().branch_id, first.pk)
        self.assertEqual(Client.objects.count(), 1)

    def test_unique_service_specialist_branch_is_selected(self):
        first = create_branch(business=self.business, actor=self.owner, name="North")
        create_branch(business=self.business, actor=self.owner, name="South")
        turn = self.run_turn(self.draft())
        self.assertEqual(turn.status, "completed", turn.response)
        self.assertEqual(Appointment.objects.get().branch_id, first.pk)

    def test_unavailable_slot_does_not_ask_again_for_service(self):
        draft = self.draft()
        draft["visits"][0].update(time="03:00", time_text="03:00")
        turn = self.run_turn(draft, message="Book Иван Иванов November 7 2030 at 03:00, Consultation with Anna")
        self.assertEqual(turn.status, "clarifying", turn.error_code)
        self.assertIn("Укажите другое время", turn.response)
        self.assertFalse(Client.objects.exists())

    def test_past_and_inactive_messages_are_localized_without_writes(self):
        Branch.objects.create(business=self.business, name="Old", is_active=False, archived_at=timezone.now())
        draft = self.draft()
        draft["visits"][0]["date"] = "2020-10-07"
        with bind_thread(self.thread):
            for language in ("ru", "en", "kk"):
                payload, question, _ = resolve_schedule(business=self.business, user=self.owner, draft=draft, language=language)
                self.assertIsNone(payload)
                self.assertIn(COPY[language]["inactive_branches"], question)
                self.assertIn(COPY[language]["past"].format(visit=1, when="07.10.2020 12:00"), question)
        self.assertFalse(Client.objects.exists())

    def test_invalid_calendar_date_asks_for_date(self):
        draft = self.draft()
        draft["visits"][0]["date"] = "2030-02-30"
        turn = self.run_turn(draft)
        self.assertEqual(turn.status, "clarifying")
        self.assertIn("дату посещения", turn.response)

    def test_calendar_branch_context_is_authorized_and_used(self):
        from unittest.mock import patch
        from rest_framework.test import APIClient
        from apps.ai_core.tests_conversation_execution import action_route, create_step, output
        first = create_branch(business=self.business, actor=self.owner, name="North")
        second = create_branch(business=self.business, actor=self.owner, name="South")
        save_offer(branch=second, actor=self.owner, service_id=self.service.pk, duration_minutes=30, price_from=100)
        save_assignment(branch=second, actor=self.owner, resource_id=self.resource.pk, service_ids=[self.service.pk])
        api = APIClient(); api.force_authenticate(self.owner)
        with patch("apps.ai_core.services.generate_text", side_effect=[action_route(create_step("appointments")), output(self.draft())]):
            response = api.post(f"/api/ai/conversations/{self.thread.pk}/turns/", {
                "message": "Book Иван Иванов November 7 2030 at noon, Consultation with Anna",
                "idempotency_key": "selected-location", "origin": "voice", "execution": "direct",
                "current_branch": first.pk}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["status"], "awaiting_confirmation", response.data)
        self.assertFalse(Appointment.objects.exists())
        response = api.post(f"/api/ai/conversations/{self.thread.pk}/turns/{response.data['id']}/confirm/", {
            "expected_revision": response.data["sequence"],
            "actions": [{"id": item["id"], "fingerprint": item["fingerprint"]} for item in response.data["actions"]],
        }, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["status"], "completed", response.data)
        self.assertEqual(Appointment.objects.get().branch_id, first.pk)
        self.assertEqual(response.data["actions"][0]["output_json"]["records"][1]["record"]["branch_name"], "North")

    def test_foreign_branch_context_is_rejected_before_model_or_writes(self):
        from unittest.mock import patch
        from rest_framework.test import APIClient
        from apps.businesses.models import Business
        other = Business.objects.create(owner=self.owner, name="Other", slug="voice-foreign-branch")
        foreign = Branch.objects.create(business=other, name="Hidden location")
        api = APIClient(); api.force_authenticate(self.owner)
        with patch("apps.ai_core.services.generate_text") as generate:
            response = api.post(f"/api/ai/conversations/{self.thread.pk}/turns/", {
                "message": "Book a visit", "idempotency_key": "foreign-location", "origin": "voice",
                "execution": "direct", "current_branch": foreign.pk}, format="json")
        self.assertEqual(response.status_code, 403, response.data)
        generate.assert_not_called()
        self.assertNotIn("Hidden location", str(response.data))
        self.assertFalse(self.thread.turns.exists())
