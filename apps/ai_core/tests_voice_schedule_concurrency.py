from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from django.db import connections
from django.test import TransactionTestCase, override_settings, skipUnlessDBFeature

from apps.ai_core.agent_runtime import bind_command, bind_thread
from apps.ai_core.conversation_access import create_voice_conversation
from apps.ai_core.conversation_actions import _approve
from apps.ai_core.crm_tools import prepare_command, request_context
from apps.ai_core.models import AIToolCallLog
from apps.ai_core.tests_voice_schedule import VoiceScheduleCommandTests
from apps.ai_core.tool_registry import execute_tool_call_once
from apps.clients.models import Client
from apps.scheduling.models import Appointment


@skipUnlessDBFeature("has_select_for_update")
@override_settings(AI_PROVIDER="mock", AI_ENABLED=True, VOICE_INPUT_ENABLED=True, AI_QUEUE_LIVE_REQUESTS=False)
class VoiceScheduleConcurrencyTests(TransactionTestCase):
    visit = VoiceScheduleCommandTests.visit

    def setUp(self):
        VoiceScheduleCommandTests.setUp(self)
        self.thread = create_voice_conversation(business=self.business, user=self.owner)

    def proposal(self, hour=12):
        with bind_thread(self.thread):
            payload = prepare_command(business=self.business, user=self.owner, tool="crm_schedule",
                payload={"entity": "appointments", "values": {**self.values, "visits": [self.visit(hour=hour)]}})
            log = AIToolCallLog.objects.create(business=self.business, user=self.owner,
                tool_name="crm_schedule", input_json=bind_command(self.business, payload))
        approval = _approve(log, self.owner, request_context(self.owner), authorization="voice_direct_submission")
        return log.pk, approval.pk

    def parallel(self, proposals):
        barrier = Barrier(len(proposals))
        def run(proposal):
            connections.close_all()
            try:
                barrier.wait(timeout=15)
                result, duplicate = execute_tool_call_once(proposal[0], self.owner, approval_id=proposal[1])
                return result.status, duplicate
            finally:
                connections.close_all()
        with ThreadPoolExecutor(max_workers=len(proposals)) as pool:
            return list(pool.map(run, proposals))

    def test_same_approved_command_executes_once(self):
        proposal = self.proposal()
        results = self.parallel([proposal, proposal])
        self.assertEqual(sorted(results), [("executed", False), ("executed", True)], list(AIToolCallLog.objects.values_list("error", flat=True)))
        self.assertEqual(Client.objects.count(), 1)
        self.assertEqual(Appointment.objects.count(), 1)

    def test_two_bookings_for_new_name_reuse_one_client(self):
        results = self.parallel([self.proposal(12), self.proposal(13)])
        self.assertTrue(all(status == "executed" for status, _ in results), (results, list(AIToolCallLog.objects.values_list("error", flat=True))))
        self.assertEqual(Client.objects.count(), 1)
        self.assertEqual(Appointment.objects.count(), 2)
        self.assertEqual(Appointment.objects.values("client_id").distinct().count(), 1)

    def test_competing_slot_has_one_winner_and_no_orphan_client(self):
        first = self.proposal()
        self.values["client"] = {"full_name": "Second client"}
        results = self.parallel([first, self.proposal()])
        self.assertEqual(sorted(status for status, _ in results), ["executed", "failed"], list(AIToolCallLog.objects.values_list("error", flat=True)))
        self.assertEqual(Client.objects.count(), 1)
        self.assertEqual(Appointment.objects.count(), 1)
