import json
from unittest.mock import patch

from django.test import TestCase

from apps.ai_core import tests as fixtures
from apps.ai_core.ai_client import AIClientResult, AIClientError
from apps.ai_core.models import AIToolCallLog
from apps.clients.models import Client


class CRMPlannerTests(TestCase):
    def setUp(self):
        fixtures.AICoreFoundationTests.setUp(self)
        self.api.force_authenticate(self.owner)
        self.person = Client.objects.create(business=self.business, full_name="Selected")

    def plan(self, output, **values):
        with patch("apps.ai_core.services.generate_text", return_value=AIClientResult(output_text=json.dumps(output), model="test", provider="test")):
            payload = {"business": self.business.pk, "entity": "clients", "entity_id": self.person.pk,
                       "message": "Change name to Reviewed", **values}
            return self.api.post("/api/ai/crm/plan/", {key: value for key, value in payload.items() if value is not None}, format="json")

    def test_natural_request_only_prepares_validated_reviewable_command(self):
        response = self.plan({"tool": "crm_update", "arguments": {"entity": "clients", "entity_id": self.person.pk, "values": {"full_name": "Reviewed"}}, "question": ""})
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["suggested_actions"][0]["input_json"]["before"]["full_name"], "Selected")
        self.person.refresh_from_db()
        self.assertEqual(self.person.full_name, "Selected")

    def test_invented_target_or_protected_field_never_becomes_action(self):
        for arguments in ({"entity": "clients", "entity_id": self.person.pk + 99, "values": {"full_name": "Bad"}},
                          {"entity": "clients", "entity_id": self.person.pk, "values": {"business": self.other_business.pk}}):
            response = self.plan({"tool": "crm_update", "arguments": arguments})
            self.assertIn(response.status_code, (400, 503))
        self.assertFalse(AIToolCallLog.objects.exists())

    def test_missing_details_question_has_no_mutation_or_tool(self):
        response = self.plan({"tool": None, "arguments": {}, "question": "What is the new name?"})
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["suggested_actions"], [])
        self.assertFalse(AIToolCallLog.objects.exists())

    def test_provider_failure_is_visible_without_fabricated_plan(self):
        with patch("apps.ai_core.services.generate_text", side_effect=AIClientError()):
            response = self.api.post("/api/ai/crm/plan/", {"business": self.business.pk, "entity": "clients", "message": "Create client"}, format="json")
        self.assertEqual(response.status_code, 503)
        self.assertFalse(AIToolCallLog.objects.exists())

    def test_dated_task_can_be_planned_and_logged_without_mutation(self):
        from django.utils import timezone
        from apps.tasks.models import Task
        task = Task.objects.create(business=self.business, title="Original", due_at=timezone.now())
        response = self.plan({"tool": "crm_update", "arguments": {"entity": "tasks", "entity_id": task.pk,
            "values": {"title": "Reviewed"}}, "question": ""}, entity="tasks", entity_id=task.pk)
        self.assertEqual(response.status_code, 200, response.data)
        task.refresh_from_db()
        self.assertEqual(task.title, "Original")

    def test_lead_envelope_question_cannot_break_valid_create_or_update(self):
        from apps.leads.models import Lead
        lead = Lead.objects.create(business=self.business, client=self.person, message="Before")
        for tool in ("crm_create", "crm_update"):
            arguments = {"entity": "leads", "question": "", "values": {"message": "Requested"}}
            if tool == "crm_create":
                arguments["values"]["client"] = self.person.pk
            else:
                arguments["entity_id"] = lead.pk
            response = self.plan({"tool": tool, "arguments": arguments, "question": ""}, entity="leads", entity_id=lead.pk)
            self.assertEqual(response.status_code, 200, response.data)
            self.assertEqual(len(response.data["suggested_actions"]), 1)
            self.assertNotIn("question", response.data["suggested_actions"][0]["input_json"])
        lead.refresh_from_db()
        self.assertEqual(lead.message, "Before")
        self.assertEqual(Lead.objects.count(), 1)

    def test_blank_required_field_becomes_clarification_without_proposal(self):
        response = self.plan({"tool": "crm_create", "arguments": {"entity": "tasks", "values": {"title": ""}}, "question": ""}, entity="tasks", entity_id=None)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["missing_fields"], ["title"])
        self.assertTrue(response.data["question"])
        self.assertEqual(response.data["suggested_actions"], [])
        self.assertFalse(AIToolCallLog.objects.exists())

    def test_question_never_coexists_with_an_executable_proposal(self):
        response = self.plan({"tool": "crm_update", "arguments": {"entity": "clients", "entity_id": self.person.pk,
            "values": {"full_name": "Invented"}, "question": "Какое имя сохранить?"}})
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["question"], "Какое имя сохранить?")
        self.assertFalse(AIToolCallLog.objects.exists())

    def test_unknown_arguments_are_not_silently_removed(self):
        response = self.plan({"tool": "crm_update", "arguments": {"entity": "clients", "entity_id": self.person.pk,
            "values": {"full_name": "Invalid"}, "approved": True}})
        self.assertEqual(response.status_code, 503, response.data)
        self.assertFalse(AIToolCallLog.objects.exists())
