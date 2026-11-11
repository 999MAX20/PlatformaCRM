from copy import deepcopy
from datetime import time
from types import SimpleNamespace
from unittest.mock import patch

from django.test import TestCase, override_settings
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.ai_core import tests as foundation
from apps.ai_core.voice_schedule_commands import execute_schedule, validate_schedule
from apps.clients.models import Client
from apps.scheduling.models import Appointment, Resource, VisitPlan, WorkingHours
from apps.services.models import Service


def confirm_prepared_creation(turn, user):
    """Domain fixtures continue after the owner's explicit creation-review click."""
    from apps.ai_core.conversation_actions import confirm_turn
    from apps.ai_core.tool_registry import tool_call_fingerprint
    if turn.status == "awaiting_confirmation":
        turn, _ = confirm_turn(conversation_id=turn.conversation_id, turn_id=turn.pk, user=user,
            expected_revision=turn.sequence, actions=[{"id": log.pk, "fingerprint": tool_call_fingerprint(log)}
                for log in turn.tool_calls.filter(status="suggested")])
    return turn


@override_settings(AI_PROVIDER="mock", AI_ENABLED=True, VOICE_INPUT_ENABLED=True, AI_QUEUE_LIVE_REQUESTS=False)
class VoiceScheduleCommandTests(TestCase):
    def setUp(self):
        foundation.AICoreFoundationTests.setUp(self)
        self.business.timezone = "UTC"
        self.business.save(update_fields=["timezone"])
        self.service = Service.objects.create(business=self.business, name="Consultation", duration_minutes=30, price_from=100)
        self.resource = Resource.objects.create(business=self.business, name="Anna")
        for day in range(7):
            WorkingHours.objects.create(business=self.business, weekday=day, start_time=time(9), end_time=time(18))
        self.values = {"client": {"full_name": "Иван Иванов"}, "plan": False, "visits": [self.visit()]}

    def visit(self, day=7, hour=12):
        return {"service": self.service.pk, "resource": self.resource.pk, "branch": None,
                "start_at": f"2030-11-{day:02d}T{hour:02d}:00:00Z", "expected_price": "100.00", "expected_duration_minutes": 30}

    def execute(self, values=None, user=None, pk=901):
        return execute_schedule(SimpleNamespace(pk=pk, business_id=self.business.pk,
            input_json={"values": values or self.values}), user or self.owner)

    def test_new_client_and_record_created_together(self):
        result = self.execute()
        self.assertEqual(Appointment.objects.get().client_id, Client.objects.get().pk)
        self.assertEqual(len(result["records"]), 2)
        self.assertTrue(result["records"][0]["created"])

    def test_existing_client_outside_recent_sample_is_reused(self):
        original = Client.objects.create(business=self.business, full_name="Иван Иванов")
        Client.objects.bulk_create([Client(business=self.business, full_name=f"Recent {i}") for i in range(70)])
        result = self.execute()
        self.assertEqual(Appointment.objects.get().client_id, original.pk)
        self.assertFalse(result["records"][0]["created"])
        self.assertEqual(Client.objects.count(), 71)

    def test_ambiguous_clients_never_selected_or_created(self):
        Client.objects.bulk_create([Client(business=self.business, full_name="Иван Иванов") for _ in range(2)])
        with self.assertRaises(ValidationError):
            self.execute()
        self.assertEqual(Client.objects.count(), 2)
        self.assertFalse(Appointment.objects.exists())

    def test_foreign_client_service_and_resource_denied(self):
        foreign = Client.objects.create(business=self.other_business, full_name="Foreign")
        values = deepcopy(self.values)
        values["client"] = {"id": foreign.pk}
        with self.assertRaises(PermissionDenied):
            self.execute(values)
        for model, field in ((Service, "service"), (Resource, "resource")):
            other = model.objects.create(business=self.other_business, name="Foreign")
            values = deepcopy(self.values)
            values["visits"][0][field] = other.pk
            with self.assertRaises(ValidationError):
                self.execute(values)
        self.assertFalse(Appointment.objects.exists())

    def test_plan_creates_all_visits_with_domain_links(self):
        self.values.update(plan=True, visits=[self.visit(7, 12), self.visit(8, 13), self.visit(9, 14)])
        result = self.execute()
        plan = VisitPlan.objects.get(pk=result["visit_plan_id"])
        self.assertEqual(plan.steps.filter(appointment__isnull=False).count(), 3)
        self.assertEqual(Appointment.objects.count(), 3)
        self.assertEqual(Client.objects.count(), 1)

    def test_late_plan_failure_rolls_back_client_plan_and_appointments(self):
        from apps.scheduling.plan_services import change_plan
        self.values.update(plan=True, visits=[self.visit(7), self.visit(8)])
        calls = []
        def change(**kwargs):
            calls.append(True)
            if len(calls) == 2:
                raise ValidationError("late conflict")
            return change_plan(**kwargs)
        with patch("apps.scheduling.plan_services.change_plan", side_effect=change):
            with self.assertRaises(ValidationError):
                self.execute()
        self.assertEqual(len(calls), 2)
        self.assertFalse(Client.objects.exists())
        self.assertFalse(VisitPlan.objects.exists())
        self.assertFalse(Appointment.objects.exists())

    def test_conflict_in_second_visit_does_not_create_partial_plan(self):
        self.values.update(plan=True, visits=[self.visit(), self.visit()])
        with self.assertRaises(ValidationError):
            self.execute()
        self.assertFalse(Client.objects.exists())
        self.assertFalse(VisitPlan.objects.exists())

    def test_changed_price_or_duration_requires_fresh_proposal(self):
        self.service.price_from = 200
        self.service.save(update_fields=["price_from"])
        with self.assertRaises(ValidationError):
            self.execute()
        self.assertFalse(Client.objects.exists())

    def test_inactive_specialist_and_missing_time_rejected(self):
        for value in (None, "2030-11-07T12:00:00", "2020-01-01T12:00:00Z"):
            self.values["visits"][0]["start_at"] = value
            with self.assertRaises(ValidationError):
                self.execute()
        self.values["visits"] = [self.visit()]
        self.resource.is_active = False
        self.resource.save(update_fields=["is_active"])
        with self.assertRaises(ValidationError):
            self.execute()
        self.assertFalse(Client.objects.exists())

    def test_preparation_has_no_writes(self):
        validate_schedule(business=self.business, user=self.owner, values=self.values)
        self.assertFalse(Client.objects.exists())
        self.assertFalse(Appointment.objects.exists())

    def test_actor_from_other_business_denied(self):
        with self.assertRaises(PermissionDenied):
            self.execute(user=self.other_owner)
        self.assertFalse(Client.objects.exists())


@override_settings(AI_PROVIDER="mock", AI_ENABLED=True, VOICE_INPUT_ENABLED=True, AI_QUEUE_LIVE_REQUESTS=False)
class VoiceScheduleConversationTests(TestCase):
    def setUp(self):
        VoiceScheduleCommandTests.setUp(self)
        from apps.ai_core.conversation_access import create_voice_conversation
        self.thread = create_voice_conversation(business=self.business, user=self.owner)

    visit = VoiceScheduleCommandTests.visit

    def draft(self, **changes):
        return {"client_name": "Иван Иванов", "client_phone": "", "client_id": None, "plan": False,
            "visits": [{"date": "2030-11-07", "time": "12:00", "time_text": "noon", "time_basis": "business", "service": "Consultation", "specialist": "Anna", "branch": "", "any_resource": False}], **changes}

    def run_turn(self, draft, *, key="schedule", message="Book Иван Иванов November 7 2030 at noon, Consultation with Anna", confirm_client=True):
        from apps.ai_core.conversation_state import start_turn
        from apps.ai_core.tests_conversation_execution import action_route, create_step, output
        from apps.ai_core.services import process_ai_job
        turn, job = start_turn(conversation_id=self.thread.pk, user=self.owner, message=message,
            idempotency_key=key, context={"execution": "direct"})
        if job:
            with patch("apps.ai_core.services.generate_text", side_effect=[action_route(create_step("appointments")), output(draft)]) as generate:
                process_ai_job(job.pk)
            self.generated = generate
        turn.refresh_from_db()
        if confirm_client:
            turn = confirm_prepared_creation(turn, self.owner)
        return turn

    def test_reviewed_new_client_schedule_and_replay_create_once(self):
        from apps.ai_core.models import ApprovalRequest
        turn = self.run_turn(self.draft())
        self.assertEqual(turn.status, "completed", turn.error_code)
        self.assertEqual(Appointment.objects.count(), 1)
        self.assertEqual(Client.objects.count(), 1)
        self.assertEqual(turn.tool_calls.get().tool_name, "crm_schedule")
        self.assertEqual(len(turn.references_json), 2)
        self.assertEqual(ApprovalRequest.objects.get().payload["authorization"], "review")
        self.assertEqual(self.run_turn(self.draft()).pk, turn.pk)
        self.assertEqual(Appointment.objects.count(), 1)

    def test_plan_links_all_created_entities_in_history(self):
        draft = self.draft(plan=True)
        draft["visits"] = [{**draft["visits"][0], "date": f"2030-11-0{day}"} for day in (7, 8, 9)]
        turn = self.run_turn(draft)
        self.assertEqual(turn.status, "completed", turn.error_code)
        self.assertEqual(len(turn.references_json), 4)
        self.assertEqual(VisitPlan.objects.get().steps.count(), 3)

    def test_missing_service_and_specialist_asked_together_without_client_write(self):
        Service.objects.create(business=self.business, name="Other service", duration_minutes=30)
        Resource.objects.create(business=self.business, name="Second specialist")
        draft = self.draft()
        draft["visits"][0].update(service="", specialist="")
        turn = self.run_turn(draft)
        self.assertEqual(turn.status, "clarifying", turn.error_code)
        self.assertIn("услугу", turn.response)
        self.assertIn("специалиста", turn.response)
        self.assertNotIn("имя клиента", turn.response)
        self.assertFalse(Client.objects.exists())
        self.assertFalse(turn.tool_calls.exists())
        completed = self.run_turn(self.draft(), key="answer", message="Consultation with Anna")
        self.assertEqual(completed.status, "completed", completed.error_code)
        # The model receives the unfinished request even when the answer is short.
        call_text = str(self.generated.call_args_list[-1])
        self.assertIn("2030-11-07", call_text)
        self.assertIn("latest_answer", call_text)

    def test_duplicate_name_clarifies_and_selected_id_completes(self):
        first = Client.objects.create(business=self.business, full_name="Иван Иванов")
        Client.objects.create(business=self.business, full_name="Иван Иванов")
        turn = self.run_turn(self.draft())
        self.assertEqual(turn.status, "clarifying", turn.error_code)
        self.assertEqual(len(turn.references_json), 2)
        self.assertFalse(Appointment.objects.exists())
        completed = self.run_turn(self.draft(client_id=first.pk), key="choice", message=f"#{first.pk}")
        self.assertEqual(completed.status, "completed", completed.error_code)
        self.assertEqual(Appointment.objects.get().client_id, first.pk)

    def test_any_specialist_chooses_free_one_after_busy_candidate(self):
        second = Resource.objects.create(business=self.business, name="Zara")
        from apps.ai_core.voice_schedule_commands import execute_schedule
        execute_schedule(SimpleNamespace(pk=991, business_id=self.business.pk, input_json={"values": self.values}), self.owner)
        draft = self.draft(client_name="New client")
        draft["visits"][0].update(specialist="", any_resource=True)
        turn = self.run_turn(draft)
        self.assertEqual(turn.status, "completed", turn.error_code)
        self.assertEqual(Appointment.objects.get(client__full_name="New client").resource_id, second.pk)

    def test_unspecified_specialist_does_not_choose_arbitrarily(self):
        Resource.objects.create(business=self.business, name="Zara")
        draft = self.draft()
        draft["visits"][0].update(specialist="", any_resource=False)
        turn = self.run_turn(draft)
        self.assertEqual(turn.status, "clarifying", turn.error_code)
        self.assertFalse(Client.objects.exists())

    def test_unavailable_time_clarifies_without_partial_records(self):
        draft = self.draft(plan=True)
        draft["visits"].append({**draft["visits"][0], "date": "2030-11-08", "time": "02:00"})
        turn = self.run_turn(draft)
        self.assertEqual(turn.status, "clarifying", turn.error_code)
        self.assertFalse(Client.objects.exists())
        self.assertFalse(VisitPlan.objects.exists())

    def test_invented_client_id_is_rejected_before_writes(self):
        client = Client.objects.create(business=self.business, full_name="Different")
        turn = self.run_turn(self.draft(client_id=client.pk))
        self.assertEqual(turn.status, "failed")
        self.assertFalse(Appointment.objects.exists())

    def test_plan_history_redacts_when_any_created_client_is_hidden(self):
        turn = self.run_turn(self.draft())
        self.assertEqual(turn.status, "completed", turn.error_code)
        from apps.ai_core.conversation_views import turn_payload
        with patch("apps.ai_core.conversation_views.references_visible", return_value=False):
            data = turn_payload(turn, self.owner)
        self.assertTrue(data["redacted"])
        self.assertEqual(data["actions"], [])

    def test_execution_requires_exact_approval(self):
        from apps.ai_core.agent_runtime import bind_thread, bind_command
        from apps.ai_core.crm_tools import prepare_command
        from apps.ai_core.models import AIToolCallLog
        from apps.ai_core.tool_registry import execute_tool_call_once
        with bind_thread(self.thread):
            payload = prepare_command(business=self.business, user=self.owner, tool="crm_schedule",
                payload={"entity": "appointments", "values": self.values})
            log = AIToolCallLog.objects.create(business=self.business, user=self.owner,
                tool_name="crm_schedule", input_json=bind_command(self.business, payload))
        with self.assertRaises(PermissionDenied):
            execute_tool_call_once(log.pk, self.owner)
        self.assertFalse(Client.objects.exists())

    def test_no_client_create_permission_allows_existing_but_not_new(self):
        from apps.accounts.models import User
        from apps.businesses.models import BusinessMember, BusinessRole, RolePermission
        from apps.ai_core.conversation_access import create_voice_conversation
        user = User.objects.create_user(username="scheduler", email="scheduler@example.test", password="pass", role="staff")
        role = BusinessRole.objects.create(business=self.business, name="Scheduler without client creation")
        for resource, actions in {"ai_assistant": ["suggest"], "ai_pipeline": ["suggest", "approve", "execute"],
                                  "clients": ["view"], "appointments": ["view", "create"]}.items():
            for action in actions:
                RolePermission.objects.create(business_role=role, resource=resource, action=action, scope="business", is_allowed=True)
        RolePermission.objects.create(business_role=role, resource="clients", action="create", scope="none", is_allowed=False)
        BusinessMember.objects.create(business=self.business, user=user, role="specialist", business_role=role)
        client = Client.objects.create(business=self.business, full_name="Иван Иванов")
        self.owner = user
        self.thread = create_voice_conversation(business=self.business, user=user)
        turn = self.run_turn(self.draft())
        self.assertEqual(turn.status, "completed", turn.error_code)
        self.assertEqual(Appointment.objects.get().client_id, client.pk)
        denied = self.run_turn(self.draft(client_name="New person"), key="new")
        self.assertEqual(denied.status, "failed")
        self.assertEqual(denied.error_code, "access_changed")
        self.assertEqual(Client.objects.count(), 1)

    def test_plain_date_is_not_silently_given_a_time(self):
        draft = self.draft()
        draft["visits"][0]["time"] = ""
        turn = self.run_turn(draft)
        self.assertEqual(turn.status, "clarifying", turn.error_code)
        self.assertFalse(Client.objects.exists())

    def test_model_cannot_invent_time_without_employee_time_evidence(self):
        draft = self.draft()
        draft["visits"][0]["time_text"] = "09:00"
        draft["visits"][0]["time"] = "09:00"
        turn = self.run_turn(draft, message="Book Иван Иванов on November 7, 2030, Consultation with Anna")
        self.assertEqual(turn.status, "clarifying", turn.error_code)
        self.assertIn("время посещения", turn.response)
        self.assertNotIn("дату посещения", turn.response)
        self.assertFalse(Appointment.objects.exists())

    def test_business_wall_time_is_resolved_by_server_timezone(self):
        self.business.timezone = "Asia/Almaty"
        self.business.save(update_fields=["timezone"])
        turn = self.run_turn(self.draft())
        self.assertEqual(turn.status, "completed", turn.error_code)
        self.assertEqual(Appointment.objects.get().start_at.hour, 7)

    def test_single_booking_does_not_create_unrequested_plan(self):
        turn = self.run_turn(self.draft(plan=True))
        self.assertEqual(turn.status, "completed", turn.error_code)
        self.assertFalse(VisitPlan.objects.exists())
