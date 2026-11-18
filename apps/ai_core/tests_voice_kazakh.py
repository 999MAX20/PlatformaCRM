from django.test import SimpleTestCase, TestCase, TransactionTestCase, override_settings, skipUnlessDBFeature
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError

from apps.ai_core import tests_voice_schedule as scheduling
from apps.ai_core.speech_numbers import ambiguous_spoken_phone, normalize_spoken_phone
from apps.clients.models import Client
from apps.scheduling.models import Appointment


class KazakhPhoneTests(SimpleTestCase):
    def test_exact_mixed_digits_and_label_variants(self):
        for label in ("Телефон номер", "Телефон номері", "Телефон нөмірі"):
            text = label + " плюс жеті семь нөл бір два үш төрт пять алты жеті сегіз."
            self.assertEqual(normalize_spoken_phone(text), label + " +77012345678.")
            self.assertFalse(ambiguous_spoken_phone(text))

    def test_unrecognized_and_grouped_digits_require_clarification(self):
        for text in ("Телефон номер плюс жете, жете, нөл бір екі үш төрт бес алты жете сегіз на консультацию",
                     "Телефон плюс семь семь ноль екы екы екы екы екы екы екы екы.",
                     "Телефон плюс семь семьдесят один два три четыре пять шесть семь восемь",
                     "Телефон один два три"):
            self.assertTrue(ambiguous_spoken_phone(text), text)
        for text in ("Телефон +7 701 234-56-78", "Телефон не указан", "Задача: проверить телефон",
                     "Құжаттарды тексеру", "Әсел Қасымова"):
            self.assertFalse(ambiguous_spoken_phone(text), text)


@override_settings(AI_PROVIDER="mock", AI_ENABLED=True, VOICE_INPUT_ENABLED=True, AI_QUEUE_LIVE_REQUESTS=False)
class KazakhVoiceTests(TestCase):
    setUp = scheduling.VoiceScheduleConversationTests.setUp
    visit = scheduling.VoiceScheduleConversationTests.visit
    draft = scheduling.VoiceScheduleConversationTests.draft
    run_turn = scheduling.VoiceScheduleConversationTests.run_turn

    def test_existing_exact_client_booking_requires_review(self):
        from apps.ai_core.models import ApprovalRequest
        from apps.ai_core.conversation_actions import confirm_turn
        from apps.ai_core.tool_registry import tool_call_fingerprint
        client = Client.objects.create(business=self.business, full_name="Әсел Қасымова")
        turn = self.run_turn(self.draft(client_name=client.full_name), confirm_client=False)
        self.assertEqual(turn.status, "awaiting_confirmation", turn.error_code)
        self.assertFalse(Appointment.objects.exists())
        self.assertFalse(ApprovalRequest.objects.exists())
        log = turn.tool_calls.get()
        with self.assertRaises(PermissionDenied):
            confirm_turn(conversation_id=self.thread.pk, turn_id=turn.pk, user=self.owner,
                expected_revision=turn.sequence, actions=[{"id": log.pk, "fingerprint": tool_call_fingerprint(log)}], _direct=True)
        turn = scheduling.confirm_prepared_creation(turn, self.owner)
        self.assertEqual(turn.status, "completed", turn.error_code)
        self.assertEqual(Appointment.objects.get().client_id, client.pk)
        self.assertEqual(ApprovalRequest.objects.get().payload["authorization"], "review")

    def test_new_client_identity_review_cannot_be_bypassed_by_direct_mode(self):
        from apps.ai_core.conversation_actions import confirm_turn
        from apps.ai_core.models import ApprovalRequest
        from apps.ai_core.tool_registry import tool_call_fingerprint
        turn = self.run_turn(self.draft(client_name="Әсел Қасымова", client_phone="+77012345678"), confirm_client=False)
        self.assertEqual(turn.status, "awaiting_confirmation", turn.error_code)
        self.assertFalse(Client.objects.exists())
        self.assertFalse(Appointment.objects.exists())
        self.assertFalse(ApprovalRequest.objects.exists())
        log = turn.tool_calls.get()
        self.assertEqual(log.input_json["values"]["client"], {"full_name": "Әсел Қасымова", "phone": "+77012345678"})
        args = dict(conversation_id=self.thread.pk, turn_id=turn.pk, user=self.owner,
                    expected_revision=turn.sequence, actions=[{"id": log.pk, "fingerprint": tool_call_fingerprint(log)}])
        with self.assertRaises(PermissionDenied):
            confirm_turn(**args, _direct=True)
        done, _ = confirm_turn(**args)
        self.assertEqual(done.status, "completed")
        self.assertEqual(Client.objects.get().full_name, "Әсел Қасымова")
        self.assertEqual(Client.objects.get().phone, "+77012345678")
        self.assertEqual(ApprovalRequest.objects.get().payload["authorization"], "review")
        confirm_turn(**args)
        self.assertEqual(Client.objects.count(), 1)
        self.assertEqual(Appointment.objects.count(), 1)

    def test_editing_identity_supersedes_old_proposal_before_confirmation(self):
        from apps.ai_core.conversation_actions import confirm_turn
        from apps.ai_core.conversation_state import IdempotencyConflict
        from apps.ai_core.tool_registry import tool_call_fingerprint
        original = self.run_turn(self.draft(client_name="Асель Касымова", client_phone="+77011111111"), confirm_client=False)
        action = original.tool_calls.get()
        corrected = self.run_turn(self.draft(client_name="Әсел Қасымова", client_phone="+77012345678"),
                                  key="correction", confirm_client=False)
        self.assertFalse(Client.objects.exists())
        with self.assertRaises(IdempotencyConflict):
            confirm_turn(conversation_id=self.thread.pk, turn_id=original.pk, user=self.owner,
                         expected_revision=original.sequence, actions=[{"id": action.pk, "fingerprint": tool_call_fingerprint(action)}])
        scheduling.confirm_prepared_creation(corrected, self.owner)
        self.assertEqual(Client.objects.get().full_name, "Әсел Қасымова")
        self.assertEqual(Client.objects.get().phone, "+77012345678")

    def test_cancel_and_foreign_confirmation_never_create_client(self):
        from apps.ai_core.conversation_actions import confirm_turn
        from apps.ai_core.conversation_state import cancel_turn
        from apps.ai_core.tool_registry import tool_call_fingerprint
        turn = self.run_turn(self.draft(), confirm_client=False)
        log = turn.tool_calls.get()
        with self.assertRaises((PermissionDenied, NotFound)):
            confirm_turn(conversation_id=self.thread.pk, turn_id=turn.pk, user=self.other_owner,
                expected_revision=turn.sequence, actions=[{"id": log.pk, "fingerprint": tool_call_fingerprint(log)}])
        cancel_turn(conversation_id=self.thread.pk, turn_id=turn.pk, user=self.owner)
        turn.refresh_from_db()
        self.assertEqual(turn.status, "cancelled")
        self.assertFalse(Client.objects.exists())
        self.assertFalse(Appointment.objects.exists())

    def test_ambiguous_phone_no_writes_then_exact_command_and_replay(self):
        draft = self.draft(client_phone="+77701234567")
        message = "Запиши Ивана. Телефон номер плюс жете жете нөл бір екі үш төрт бес алты жеті сегіз."
        turn = self.run_turn(draft, message=message)
        self.assertEqual(turn.status, "clarifying", turn.error_code)
        self.assertEqual(self.generated.call_count, 1)
        self.assertFalse(turn.tool_calls.exists())
        self.assertFalse(Client.objects.exists())
        self.assertFalse(Appointment.objects.exists())
        corrected = self.draft(client_phone="+77012345678")
        message = "Book Иван Иванов November 7 2030 at noon, Consultation with Anna. Телефон +77012345678"
        done = self.run_turn(corrected, key="corrected", message=message)
        self.assertEqual(done.status, "completed", (done.error_code, done.response, done.plan_json))
        self.assertEqual(Client.objects.get().phone, "+77012345678")
        self.assertEqual(self.run_turn(corrected, key="corrected", message=message).pk, done.pk)
        self.assertEqual(Appointment.objects.count(), 1)

    def test_russified_client_requires_explicit_selection_even_with_matching_phone(self):
        client = Client.objects.create(business=self.business, full_name="Айгерім Нұрланова", phone="+77011111111")
        draft = self.draft(client_name="Айгерим Нурланова", client_phone=client.phone)
        turn = self.run_turn(draft)
        self.assertEqual(turn.status, "clarifying", turn.error_code)
        self.assertIn(f"#{client.pk}", turn.response)
        self.assertFalse(Appointment.objects.exists())
        done = self.run_turn({**draft, "client_id": client.pk}, key="selected", message=f"#{client.pk}")
        self.assertEqual(done.status, "completed", (done.error_code, done.response, done.plan_json))
        self.assertEqual(Appointment.objects.get().client_id, client.pk)
        self.assertEqual(Client.objects.count(), 1)

    def test_similar_foreign_client_not_disclosed_or_selected(self):
        foreign = Client.objects.create(business=self.other_business, full_name="Айгерім Нұрланова")
        turn = self.run_turn(self.draft(client_name="Айгерим Нурланова"))
        self.assertEqual(turn.status, "completed", turn.error_code)
        self.assertNotIn({"entity": "clients", "id": foreign.pk}, turn.references_json)
        self.assertNotEqual(Appointment.objects.get().client_id, foreign.pk)


@override_settings(AI_PROVIDER="mock", AI_ENABLED=True, VOICE_INPUT_ENABLED=True, AI_QUEUE_LIVE_REQUESTS=False)
class KazakhExecutionTests(TestCase):
    setUp = scheduling.VoiceScheduleCommandTests.setUp
    visit = scheduling.VoiceScheduleCommandTests.visit
    execute = scheduling.VoiceScheduleCommandTests.execute

    def test_similar_name_inserted_after_prepare_blocks_duplicate_at_execution(self):
        Client.objects.create(business=self.business, full_name="Айгерім Нұрланова")
        self.values["client"] = {"full_name": "Айгерим Нурланова", "phone": "+77022222222"}
        with self.assertRaises(ValidationError):
            self.execute()
        self.assertFalse(Appointment.objects.exists())
        self.assertEqual(Client.objects.count(), 1)


@skipUnlessDBFeature("has_select_for_update")
@override_settings(AI_PROVIDER="mock", AI_ENABLED=True, VOICE_INPUT_ENABLED=True, AI_QUEUE_LIVE_REQUESTS=False)
class VoiceReviewConcurrencyTests(TransactionTestCase):
    setUp = scheduling.VoiceScheduleConversationTests.setUp
    visit = scheduling.VoiceScheduleConversationTests.visit
    draft = scheduling.VoiceScheduleConversationTests.draft
    run_turn = scheduling.VoiceScheduleConversationTests.run_turn

    def test_simultaneous_review_clicks_create_once(self):
        from concurrent.futures import ThreadPoolExecutor
        from threading import Barrier
        from django.db import connections
        from apps.ai_core.conversation_actions import confirm_turn
        from apps.ai_core.models import ApprovalRequest
        from apps.ai_core.tool_registry import tool_call_fingerprint
        turn = self.run_turn(self.draft(), confirm_client=False)
        self.assertEqual(turn.status, "awaiting_confirmation")
        log = turn.tool_calls.get()
        barrier = Barrier(2)
        def confirm(_):
            connections.close_all()
            try:
                barrier.wait(timeout=15)
                result, _ = confirm_turn(conversation_id=self.thread.pk, turn_id=turn.pk, user=self.owner,
                    expected_revision=turn.sequence, actions=[{"id": log.pk, "fingerprint": tool_call_fingerprint(log)}])
                return result.status
            finally:
                connections.close_all()
        with ThreadPoolExecutor(max_workers=2) as pool:
            self.assertEqual(list(pool.map(confirm, range(2))), ["completed", "completed"])
        self.assertEqual(Client.objects.count(), 1)
        self.assertEqual(Appointment.objects.count(), 1)
        self.assertEqual(ApprovalRequest.objects.count(), 1)
