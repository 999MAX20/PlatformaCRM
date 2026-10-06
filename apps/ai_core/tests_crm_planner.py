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
            return self.api.post("/api/ai/crm/plan/", {"business": self.business.pk,
                "entity": "clients", "entity_id": self.person.pk, "message": "Change name to Reviewed", **values}, format="json")

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
