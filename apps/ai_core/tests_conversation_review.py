from django.test import TestCase

from apps.ai_core import tests_conversation_execution as fixtures
from apps.ai_core.agent_runtime import bind_thread
from apps.ai_core.conversation_review import action_reviews
from apps.ai_core.models import AIToolCallLog, AgentProfile
from apps.ai_core.tool_registry import tool_call_fingerprint
from apps.clients.models import Client
from apps.services.models import Service
from apps.scheduling.models import Resource
from apps.branches.models import Branch


class ActionReviewTests(TestCase):
    def setUp(self):
        fixtures.ConversationExecutionTests.setUp(self)
        self.client = Client.objects.create(business=self.business, full_name="Review client")
        self.service = Service.objects.create(business=self.business, name="Review service")
        self.specialist = Resource.objects.create(business=self.business, name="Review specialist")
        self.branch = Branch.objects.create(business=self.business, name="Review branch")

    def review(self, values, before=None):
        log = AIToolCallLog.objects.create(business=self.business, user=self.owner, tool_name="crm_create",
            input_json={"entity": "appointments", "values": values, "before": before or {}})
        fingerprint = tool_call_fingerprint(log)
        with bind_thread(self.thread):
            result = action_reviews([log], business=self.business, user=self.owner)[log.pk]
        log.refresh_from_db()
        self.assertEqual(tool_call_fingerprint(log), fingerprint)
        self.assertEqual(log.input_json["values"], values)
        return result

    def test_review_uses_names_and_business_zone_without_changing_payload(self):
        self.business.timezone = "Asia/Qyzylorda"
        values = {"client": self.client.pk, "service": self.service.pk, "resource": self.specialist.pk,
                  "branch": self.branch.pk, "start_at": "2026-11-20T10:00:00+05:00"}
        result = self.review(values, {"client": self.client.pk})
        self.assertEqual(result["values"], {"client": "Review client", "service": "Review service",
                                           "resource": "Review specialist", "branch": "Review branch"})
        self.assertEqual(result["before"], {"client": "Review client"})
        self.assertEqual(result["timezone"], "Asia/Qyzylorda")

    def test_foreign_and_missing_relations_never_get_labels(self):
        foreign = Client.objects.create(business=self.other_business, full_name="FOREIGN_LABEL")
        branch = Branch.objects.create(business=self.other_business, name="FOREIGN_BRANCH")
        resource = Resource.objects.create(business=self.other_business, name="FOREIGN_RESOURCE")
        result = self.review({"client": foreign.pk, "resource": resource.pk, "branch": branch.pk,
                              "service": self.service.pk + 999})
        self.assertTrue(all(value is None for value in result["values"].values()))
        self.assertNotIn("FOREIGN", str(result))

    def test_disabled_client_source_hides_name_and_current_name_is_read_again(self):
        self.client.full_name = "Renamed client"
        self.client.save()
        self.assertEqual(self.review({"client": self.client.pk})["values"]["client"], "Renamed client")
        profile = AgentProfile.objects.get(bot=self.agent)
        profile.rules_json["sources"] = ["appointments"]
        profile.save()
        self.assertIsNone(self.review({"client": self.client.pk})["values"]["client"])
