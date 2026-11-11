import json
from types import SimpleNamespace
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied

from apps.ai_core import tests_conversation_execution as fixtures
from apps.ai_core.agent_runtime import bind_thread
from apps.ai_core.ai_client import AIClientError
from apps.ai_core.conversation_preparation import prepare_answer
from apps.ai_core.conversation_router import parse_route
from apps.ai_core.crm_tools import read_entities
from apps.ai_core.models import AgentProfile
from apps.accounts.models import User
from apps.businesses.models import BusinessMember, BusinessRole, RolePermission
from apps.tasks.models import Task


@override_settings(AI_PROVIDER="mock", AI_ENABLED=True, AI_QUEUE_LIVE_REQUESTS=False)
class ArchivedReadTests(TestCase):
    def setUp(self):
        fixtures.ConversationExecutionTests.setUp(self)
        self.archived = Task.objects.create(business=self.business, title="Archived contract",
            description="ARCHIVED_DETAIL", is_archived=True, archived_at=timezone.now(), created_by=self.owner)
        self.active = Task.objects.create(business=self.business, title="Active contract", created_by=self.owner)
        self.foreign = Task.objects.create(business=self.other_business, title="FOREIGN_ARCHIVE",
            is_archived=True, archived_at=timezone.now())

    def answer(self, *, archive="archived", message=None, user=None, query=""):
        turn = SimpleNamespace(conversation=self.thread, message=message or f"Show archived task #{self.archived.pk}")
        result = SimpleNamespace(output_text="ARCHIVED_DETAIL", sources=[{"id": f"TASK-{self.archived.pk}"}], provider_state="ready")
        with bind_thread(self.thread), patch("apps.ai_core.conversation_preparation.run_ai_request",
                return_value=(result, SimpleNamespace(pk=1))) as provider:
            if user:
                self.thread.owner = user
            reply = prepare_answer(turn, {"intent": "answer", "read": {"entity": "tasks", "query": query, "archive": archive}}, {}, "en")
        return reply, provider

    def test_explicit_archive_id_uses_scoped_record_and_citable_details(self):
        reply, provider = self.answer(query=f"#{self.archived.pk}")
        context = provider.call_args.kwargs["input_json"]["crm_context"]
        self.assertEqual([r["id"] for r in context["tasks"]], [self.archived.pk])
        self.assertEqual(context["tasks"][0]["description"], "ARCHIVED_DETAIL")
        self.assertTrue(context["tasks"][0]["is_archived"])
        self.assertEqual(context["summary"]["search"]["coverage"], "permitted_archived_records")
        self.assertEqual(reply["references"], [{"entity": "tasks", "id": self.archived.pk}])

    def test_active_archived_and_all_keep_separate_counts(self):
        with bind_thread(self.thread):
            for included, only, expected in ((False, False, {self.active.pk}), (True, True, {self.archived.pk}),
                                              (True, False, {self.active.pk, self.archived.pk})):
                result = read_entities(business=self.business, user=self.owner, entity="tasks",
                                       include_archived=included, archived_only=only)
                self.assertEqual({r["id"] for r in result["results"]}, expected)
                self.assertEqual(result["count"], len(expected))

    def test_foreign_and_missing_ids_return_neutral_no_data_without_answer_model(self):
        for pk in (self.foreign.pk, self.foreign.pk + 100):
            reply, provider = self.answer(message=f"Show archived task #{pk}")
            provider.assert_not_called()
            self.assertEqual(reply["context"]["provider_state"], "no_data")
            self.assertNotIn("disabled", reply["response"])
            self.assertNotIn("FOREIGN_ARCHIVE", str(reply))

    def test_own_scope_excludes_other_owners_archive(self):
        user = User.objects.create_user(username="archive-reader", email="archive-reader@example.com")
        role = BusinessRole.objects.create(business=self.business, name="Own archive")
        RolePermission.objects.create(business_role=role, resource="tasks", action="view", scope="own", is_allowed=True)
        BusinessMember.objects.create(business=self.business, user=user, role="manager", business_role=role)
        reply, provider = self.answer(user=user)
        provider.assert_not_called()
        self.assertEqual(reply["context"]["provider_state"], "no_data")
        self.assertNotIn("ARCHIVED_DETAIL", str(reply))

    def test_disabled_source_still_denies_archive(self):
        profile = AgentProfile.objects.get(bot=self.agent)
        profile.rules_json["sources"] = ["clients"]
        profile.save()
        with self.assertRaises(PermissionDenied):
            self.answer()

    def test_read_archive_schema_is_bounded_and_backward_compatible(self):
        route = {"intent": "answer", "steps": [], "read": {"entity": "tasks", "query": "contract"}}
        self.assertNotIn("archive", parse_route(json.dumps(route), {"available_records": {}, "fresh_references": []})["read"])
        for value in ("active", "archived", "all"):
            route["read"]["archive"] = value
            self.assertEqual(parse_route(json.dumps(route), {"available_records": {}, "fresh_references": []})["read"]["archive"], value)
        for value in (True, "deleted", {"sql": "select all"}):
            route["read"]["archive"] = value
            with self.assertRaises(AIClientError):
                parse_route(json.dumps(route), {"available_records": {}, "fresh_references": []})
