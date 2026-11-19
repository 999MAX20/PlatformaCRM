from copy import deepcopy
from unittest.mock import patch

from django.test import SimpleTestCase, TestCase, override_settings

from apps.ai_core import tests_voice_schedule as fixtures
from apps.ai_core.conversation_actions import confirm_turn
from apps.ai_core.conversation_state import cancel_turn, reset_memory, start_turn
from apps.ai_core.services import process_ai_job
from apps.ai_core.tests_conversation_execution import action_route, create_step, output
from apps.ai_core.tool_registry import tool_call_fingerprint
from apps.ai_core.voice_schedule_patch import apply_schedule_patch, unchanged_correction, uncertain_kazakh_name
from apps.clients.models import Client
from apps.core.domain_errors import IdempotencyConflict
from apps.scheduling.models import Appointment


class SchedulePatchTests(SimpleTestCase):
    def test_uncertain_time_can_still_be_cleared_for_clarification(self):
        previous = {"visits": [{"time": "12:00", "time_text": "noon", "time_basis": "business"}]}
        result = apply_schedule_patch(previous, {"patch": {}, "visits": [{"index": 1, "time": "", "time_text": ""}]}, "Время пока неизвестно")
        self.assertEqual(result["visits"][0]["time"], "")

    def test_case_ending_is_only_a_clarification_signal_not_a_name_rewrite(self):
        self.assertTrue(uncertain_kazakh_name("Айжан Қасымованы", "Жаңа клиент Айжан Қасымованы қабылдауға жаз"))
        self.assertTrue(uncertain_kazakh_name("Марат Алтынды", "Жаңа клиент Марат Алтынды қабылдауға жаз"))
        self.assertFalse(uncertain_kazakh_name("Айжан Қасымова", "Жаңа клиент Айжан Қасымованы қабылдауға жаз"))
        self.assertFalse(uncertain_kazakh_name("Марат Алтынды", "Book Марат Алтынды at noon"))
        self.assertFalse(uncertain_kazakh_name("Әсел", "Жаңа клиент Әсел Сынақты жаз"))

    def test_repeated_time_evidence_is_allowed_only_for_unchanged_time(self):
        previous = {"client_phone": "+77012345678", "visits": [{"time": "12:00", "time_text": "noon", "time_basis": "business"}]}
        patch = {"patch": {"client_phone": "+77012345679"}, "visits": [{"index": 1, **previous["visits"][0]}]}
        self.assertEqual(apply_schedule_patch(previous, patch, "last digit nine")["client_phone"], "+77012345679")
        for field, changed in (("time", "13:00"), ("time_basis", "utc")):
            with self.subTest(field=field), self.assertRaises(ValueError):
                invalid = deepcopy(patch)
                invalid["visits"][0][field] = changed
                apply_schedule_patch(previous, invalid, "last digit nine")

    def test_changed_phone_cannot_hide_ignored_name_in_same_answer(self):
        previous = {"client_name": "Әсел Сынақ", "client_phone": "+77012345678", "visits": []}
        changed = {**previous, "client_phone": "+77012345679"}
        self.assertEqual(unchanged_correction(previous, changed, "Фамилия Тестова, телефон +77012345679"), "client_name")
        self.assertEqual(unchanged_correction(previous, changed, "Әсел емес, Әсем, телефон +77012345679"), "client_name")
        both = {**changed, "client_name": "Әсел Тестова"}
        self.assertEqual(unchanged_correction(previous, both, "Фамилия Тестова, телефон +77012345679"), "")
        self.assertEqual(unchanged_correction(previous, {**both, "client_phone": previous["client_phone"]},
                                            "Фамилия Тестова, телефон +77012345679"), "client_phone")

    def test_ignored_surname_correction_is_not_hidden_by_time_change(self):
        previous = {"client_name": "Әсел Сынақ", "client_phone": "", "visits": [{"time": "12:00"}]}
        changed = {**previous, "visits": [{"time": "13:00"}]}
        for message in ("Фамилия Тестова, время 13:00", "Тегі Тестова, сағат 13:00",
                        "Surname Testova, time 13:00", "Last name Testova, time 13:00"):
            with self.subTest(message=message):
                self.assertEqual(unchanged_correction(previous, changed, message), "client_name")

    def test_kazakh_time_negation_is_not_a_name_correction(self):
        previous = {"client_name": "Әсел Сынақ", "client_phone": "", "visits": [{"time": "12:00"}]}
        corrected = {**previous, "visits": [{"time": "13:00"}]}
        self.assertEqual(unchanged_correction(previous, corrected, "Он екі емес, он үш"), "")
        self.assertEqual(unchanged_correction(previous, previous, "Әсел емес, Әсем"), "client_name")

    def test_patch_preserves_other_fields_and_does_not_mutate_prior_draft(self):
        previous = {"client_name": "Әсел", "client_phone": "+77012345678", "client_id": 5,
                    "visits": [{"date": "2030-11-07", "time": "12:00", "time_text": "noon",
                                "specialist": "Anna", "any_resource": True}]}
        original = deepcopy(previous)
        result = apply_schedule_patch(previous, {"patch": {"client_name": "Әсем"}, "visits": []}, "Әсел емес, Әсем")
        self.assertEqual(result["client_id"], None)
        self.assertEqual(result["client_phone"], previous["client_phone"])
        self.assertEqual(result["visits"], previous["visits"])
        self.assertEqual(previous, original)
        result = apply_schedule_patch(previous, {"patch": {}, "visits": [{"index": 1, "specialist": ""}]}, "Другой специалист")
        self.assertFalse(result["visits"][0]["any_resource"])

    def test_invalid_patch_cannot_add_reorder_or_change_unrelated_fields(self):
        previous = {"visits": [{"time": "12:00", "time_text": "noon"}]}
        for value in ({"patch": {"plan": True}, "visits": []},
                      {"patch": {}, "visits": [{"index": True, "time": "13:00"}]},
                      {"patch": {}, "visits": [{"index": 2}]},
                      {"patch": {}, "visits": [{"index": 1, "price": 0}]},
                      {"patch": {}, "visits": [{"index": 1, "time": "13:00", "time_text": "noon"}]}):
            with self.subTest(value=value), self.assertRaises(ValueError):
                apply_schedule_patch(previous, value, "Нет, в 13:00")


@override_settings(AI_PROVIDER="mock", AI_ENABLED=True, VOICE_INPUT_ENABLED=True, AI_QUEUE_LIVE_REQUESTS=False)
class VoiceCorrectionTests(TestCase):
    setUp = fixtures.VoiceScheduleConversationTests.setUp
    visit = fixtures.VoiceScheduleConversationTests.visit
    draft = fixtures.VoiceScheduleConversationTests.draft
    run_turn = fixtures.VoiceScheduleConversationTests.run_turn

    def correct(self, message, change, key="correction"):
        turn, job = start_turn(conversation_id=self.thread.pk, user=self.owner, message=message,
            idempotency_key=key, context={"execution": "direct"})
        if job:
            with patch("apps.ai_core.services.generate_text", side_effect=[
                    action_route(create_step("appointments", request=message)), output(change)]):
                process_ai_job(job.pk)
        turn.refresh_from_db()
        return turn

    def test_initial_kazakh_case_form_asks_full_name_and_preserves_booking(self):
        draft = self.draft(client_name="Әсел Сынақты", client_phone="+77012345678")
        draft["visits"][0]["time_text"] = "сағат он екіге"
        initial = self.run_turn(draft, confirm_client=False, message=
            "Жаңа клиент Әсел Сынақты екі мың отызыншы жылғы жетінші қарашада сағат он екіге Консультация қызметіне Аннаға жаз.")
        self.assertEqual(initial.status, "clarifying", initial.error_code)
        self.assertFalse(initial.tool_calls.exists())
        self.assertEqual(initial.context_json["schedule_draft"]["client_name"], "")
        self.assertEqual(initial.context_json["schedule_draft"]["visits"], draft["visits"])
        self.assertEqual(initial.context_json["schedule_draft"]["client_phone"], draft["client_phone"])
        recovered = self.correct("Әсел Сынақ", {"patch": {"client_name": "Әсел Сынақ"}, "visits": []})
        self.assertEqual(recovered.status, "awaiting_confirmation", recovered.error_code)
        self.assertFalse(Client.objects.exists())
        fixtures.confirm_prepared_creation(recovered, self.owner)
        self.assertEqual(Client.objects.get().full_name, "Әсел Сынақ")
        self.assertEqual(Appointment.objects.count(), 1)

    def test_explicit_full_name_reply_keeps_a_real_name_ending_in_case_letters(self):
        draft = self.draft(client_name="Марат Алтынды")
        self.run_turn(draft, confirm_client=False, message="Жаңа клиент Марат Алтынды at noon November 7 2030, Consultation with Anna, жаз")
        recovered = self.correct("Толық аты-жөні Марат Алтынды", {"patch": {"client_name": "Марат Алтынды"}, "visits": []})
        self.assertEqual(recovered.status, "awaiting_confirmation", recovered.error_code)
        self.assertEqual(recovered.context_json["schedule_draft"]["client_name"], "Марат Алтынды")

    def test_live_pilot_unchanged_phone_requires_clarification_and_recovery(self):
        initial = self.run_turn(self.draft(client_phone="+77012345678"), confirm_client=False)
        corrected = self.correct("Соңғы сан сегіз емес, тоғыз. Остальные цифры не меняй.",
                                 initial.context_json["schedule_draft"])
        self.assertEqual(corrected.status, "clarifying", corrected.error_code)
        self.assertFalse(corrected.tool_calls.exists())
        self.assertEqual(corrected.context_json["schedule_draft"], initial.context_json["schedule_draft"])
        self.assertFalse(Appointment.objects.exists())
        recovered = self.correct("Телефон +77012345679", {"patch": {"client_phone": "+77012345679"}, "visits": []}, key="recovered")
        self.assertEqual(recovered.status, "awaiting_confirmation", recovered.error_code)
        self.assertEqual(recovered.context_json["schedule_draft"]["client_phone"], "+77012345679")

    def test_live_corrected_phone_with_repeated_visit_fields_requires_review(self):
        initial = self.run_turn(self.draft(client_name="Әсел Сынақ", client_phone="+77012345678"), confirm_client=False)
        repeated = deepcopy(initial.context_json["schedule_draft"]["visits"][0])
        corrected = self.correct("Соңғы сан сегіз емес, тоғыз. Остальные цифры не меняй.", {"schedule": {
            "patch": {"client_name": "Әсел Сынақ", "client_phone": "+77012345679", "client_id": None},
            "visits": [{"index": 1, **repeated}]}})
        self.assertEqual(corrected.status, "awaiting_confirmation", corrected.error_code)
        self.assertEqual(corrected.context_json["schedule_draft"]["visits"], initial.context_json["schedule_draft"]["visits"])
        self.assertEqual(corrected.context_json["schedule_draft"]["client_phone"], "+77012345679")
        self.assertFalse(Client.objects.exists())
        self.assertFalse(Appointment.objects.exists())
        fixtures.confirm_prepared_creation(corrected, self.owner)
        self.assertEqual(Client.objects.get().phone, "+77012345679")
        self.assertEqual(Appointment.objects.count(), 1)

    def test_ignored_surname_requires_full_name_and_fresh_approval(self):
        initial = self.run_turn(self.draft(client_name="Әсел Сынақ"), confirm_client=False)
        old = initial.tool_calls.get()
        ignored = self.correct("Фамилия Тестова, время 13:00", {"patch": {}, "visits": [
            {"index": 1, "time": "13:00", "time_text": "13:00"}]})
        self.assertEqual(ignored.status, "clarifying", ignored.error_code)
        self.assertEqual(ignored.context_json["schedule_correction_field"], "client_name")
        self.assertFalse(ignored.tool_calls.exists())
        self.assertFalse(Client.objects.exists())
        bypass = self.correct("В 14:00", {"patch": {}, "visits": [
            {"index": 1, "time": "14:00", "time_text": "14:00"}]}, key="bypass-name")
        self.assertEqual(bypass.status, "clarifying", bypass.error_code)
        self.assertFalse(bypass.tool_calls.exists())
        recovered = self.correct("Әсел Тестова", {"patch": {"client_name": "Әсел Тестова"}, "visits": []}, key="full-name")
        self.assertEqual(recovered.status, "awaiting_confirmation", recovered.error_code)
        self.assertEqual(recovered.context_json["schedule_draft"]["visits"], initial.context_json["schedule_draft"]["visits"])
        with self.assertRaises(IdempotencyConflict):
            confirm_turn(conversation_id=self.thread.pk, turn_id=initial.pk, user=self.owner,
                expected_revision=initial.sequence, actions=[{"id": old.pk, "fingerprint": tool_call_fingerprint(old)}])
        fixtures.confirm_prepared_creation(recovered, self.owner)
        self.assertEqual(Client.objects.get().full_name, "Әсел Тестова")
        self.assertEqual(Appointment.objects.count(), 1)

    def test_unresolved_phone_correction_cannot_be_bypassed_by_name_change(self):
        initial = self.run_turn(self.draft(client_phone="+77012345678"), confirm_client=False)
        self.correct("Исправь последнюю цифру телефона", initial.context_json["schedule_draft"])
        turn = self.correct("Имя Әсем", {"patch": {"client_name": "Әсем"}, "visits": []}, key="other-field")
        self.assertEqual(turn.status, "clarifying", turn.error_code)
        self.assertFalse(turn.tool_calls.exists())
        self.assertEqual(turn.context_json["schedule_correction_field"], "client_phone")

    @override_settings(AI_FAST_MODEL="openai/gpt-4o-mini", AI_DEFAULT_MODEL_TIER="fast", AI_PROMPT_MODEL_TIERS="{}")
    def test_structured_schedule_and_nullable_patch_preserve_other_fields(self):
        initial = self.run_turn({"schedule": self.draft(client_name="Әсел")}, confirm_client=False)
        schema = self.generated.call_args_list[-1].args[0].response_format
        self.assertEqual(schema["type"], "json_schema")
        self.assertEqual(schema["json_schema"]["name"], "voice_schedule")
        self.assertTrue(schema["json_schema"]["strict"])
        corrected = self.correct("Әсел емес, Әсем Сынақ", {"schedule": {
            "patch": {"client_name": "Әсем Сынақ", "client_phone": None, "client_id": None}, "visits": []}})
        self.assertEqual(corrected.status, "awaiting_confirmation", corrected.error_code)
        self.assertEqual(corrected.context_json["schedule_draft"]["visits"], initial.context_json["schedule_draft"]["visits"])

    def test_live_pilot_malformed_patch_is_still_rejected_without_proposal(self):
        self.run_turn(self.draft(client_name="Әсел Сынақ"), confirm_client=False)
        turn = self.correct("Әсел емес, Әсем Сынақ.", {"patch": {"client_name": "Әсем Сынақ"},
            "visits": [{"index": 1, "client_name": "Әсем Сынақ"}]})
        self.assertEqual(turn.error_code, "invalid_action_plan")
        self.assertFalse(turn.tool_calls.exists())
        self.assertFalse(Client.objects.exists())

    def test_new_booking_can_use_same_phone_and_time_correction_is_not_negated(self):
        self.run_turn(self.draft(client_phone="+77012345678"), confirm_client=False)
        draft = self.draft(client_phone="+77012345678")
        draft["visits"][0].update(date="2030-11-08", time="13:00", time_text="13:00")
        turn = self.correct("Создай новую запись на 8 ноября 2030 в 13:00, телефон +77012345678", draft)
        self.assertEqual(turn.status, "awaiting_confirmation", turn.error_code)
        turn = self.correct("Не в 13:00, а в 14:00", {"patch": {}, "visits": [{"index": 1, "time": "14:00", "time_text": "14:00"}]}, key="time")
        self.assertEqual(turn.status, "awaiting_confirmation", turn.error_code)

    def test_live_pilot_negation_cannot_prepare_main_router_booking(self):
        for index, message in enumerate((
            "Әсел Сынақты ертең сағат он екіге қабылдауға жазып жіберме.",
            "Әселді қабылдауға жаз деп айтқан жоқпын.",
            "Не записывай клиента на завтра.", "Do not book an appointment.")):
            with self.subTest(message=message):
                turn = self.correct(message, self.draft(), key=f"negative-{index}")
                self.assertEqual(turn.status, "clarifying", turn.error_code)
                self.assertNotIn("schedule_draft", turn.context_json)
                self.assertFalse(turn.tool_calls.exists())
        self.assertFalse(Client.objects.exists())
        self.assertFalse(Appointment.objects.exists())

    def test_short_kazakh_name_correction_preserves_visit_and_requires_new_approval(self):
        initial = self.run_turn(self.draft(client_name="Әсел"), confirm_client=False)
        old = initial.tool_calls.get()
        corrected = self.correct("Әсел емес, Әсем", {"patch": {"client_name": "Әсем"}, "visits": []})
        self.assertEqual(corrected.status, "awaiting_confirmation", corrected.error_code)
        self.assertEqual(corrected.context_json["schedule_draft"]["visits"], initial.context_json["schedule_draft"]["visits"])
        self.assertFalse(Client.objects.exists())
        self.assertFalse(Appointment.objects.exists())
        with self.assertRaises(IdempotencyConflict):
            confirm_turn(conversation_id=self.thread.pk, turn_id=initial.pk, user=self.owner,
                expected_revision=initial.sequence, actions=[{"id": old.pk, "fingerprint": tool_call_fingerprint(old)}])
        fixtures.confirm_prepared_creation(corrected, self.owner)
        self.assertEqual(Client.objects.get().full_name, "Әсем")
        self.assertEqual(Appointment.objects.get().start_at.hour, 12)

    def test_time_correction_and_replay_preserve_date_service_and_client(self):
        initial = self.run_turn(self.draft(), confirm_client=False)
        change = {"patch": {}, "visits": [{"index": 1, "time": "13:00", "time_text": "13:00"}]}
        corrected = self.correct("Нет, в 13:00", change)
        self.assertEqual(corrected.status, "awaiting_confirmation", corrected.error_code)
        expected = deepcopy(initial.context_json["schedule_draft"])
        expected["visits"][0].update(time="13:00", time_text="13:00")
        self.assertEqual(corrected.context_json["schedule_draft"], expected)
        self.assertEqual(self.correct("Нет, в 13:00", change).pk, corrected.pk)
        self.assertFalse(Appointment.objects.exists())

    def test_unspecified_replacement_specialist_asks_only_that_field(self):
        initial = self.run_turn(self.draft(), confirm_client=False)
        clarified = self.correct("Другой специалист", {"patch": {}, "visits": [{"index": 1, "specialist": ""}]})
        self.assertEqual(clarified.status, "clarifying", clarified.error_code)
        self.assertIn("специалист", clarified.response)
        self.assertNotIn("дату", clarified.response)
        self.assertEqual(clarified.context_json["schedule_draft"]["visits"][0]["date"], "2030-11-07")
        self.assertFalse(clarified.tool_calls.exists())
        corrected = self.correct("Anna", {"patch": {}, "visits": [{"index": 1, "specialist": "Anna"}]}, key="answer")
        self.assertEqual(corrected.status, "awaiting_confirmation", corrected.error_code)
        self.assertEqual(corrected.context_json["schedule_draft"], initial.context_json["schedule_draft"])

    def test_cancelled_schedule_cannot_supply_patch_context(self):
        initial = self.run_turn(self.draft(), confirm_client=False)
        cancel_turn(conversation_id=self.thread.pk, turn_id=initial.pk, user=self.owner)
        corrected = self.correct("Нет, на завтра", {"patch": {}, "visits": [{"index": 1, "date": "2030-11-08"}]})
        self.assertEqual(corrected.status, "failed")
        self.assertEqual(corrected.error_code, "invalid_action_plan")
        self.assertNotIn("schedule_parent", corrected.context_json)
        self.assertFalse(Appointment.objects.exists())

    def test_date_correction_changes_only_selected_visit_in_plan(self):
        draft = self.draft(plan=True)
        draft["visits"].append({**draft["visits"][0], "date": "2030-11-08"})
        initial = self.run_turn(draft, confirm_client=False)
        corrected = self.correct("Екінші қабылдау 9 қарашада", {"patch": {}, "visits": [{"index": 2, "date": "2030-11-09"}]})
        self.assertEqual(corrected.status, "awaiting_confirmation", corrected.error_code)
        expected = deepcopy(initial.context_json["schedule_draft"])
        expected["visits"][1]["date"] = "2030-11-09"
        self.assertEqual(corrected.context_json["schedule_draft"], expected)
        self.assertFalse(Appointment.objects.exists())

    def test_completed_schedule_and_reset_memory_cannot_supply_patch_context(self):
        initial = self.run_turn(self.draft(), confirm_client=False)
        fixtures.confirm_prepared_creation(initial, self.owner)
        corrected = self.correct("Нет, на завтра", {"patch": {}, "visits": [{"index": 1, "date": "2030-11-08"}]})
        self.assertEqual(corrected.error_code, "invalid_action_plan")
        self.assertNotIn("schedule_parent", corrected.context_json)
        self.assertEqual(Appointment.objects.count(), 1)
        self.run_turn(self.draft(), key="next", confirm_client=False)
        reset_memory(conversation_id=self.thread.pk, user=self.owner)
        corrected = self.correct("В 13:00", {"patch": {}, "visits": [{"index": 1, "time": "13:00", "time_text": "13:00"}]}, key="after-reset")
        self.assertEqual(corrected.error_code, "invalid_action_plan")
        self.assertNotIn("schedule_parent", corrected.context_json)
        self.assertEqual(Appointment.objects.count(), 1)

    def test_foreign_client_patch_and_changed_access_cannot_reuse_draft(self):
        initial = self.run_turn(self.draft(), confirm_client=False)
        foreign = Client.objects.create(business=self.other_business, full_name="Foreign")
        corrected = self.correct("Другой клиент", {"patch": {"client_id": foreign.pk}, "visits": []})
        self.assertEqual(corrected.error_code, "invalid_action_plan")
        self.assertFalse(Appointment.objects.exists())
        initial = self.run_turn(self.draft(), key="next", confirm_client=False)
        initial.access_fingerprint = "obsolete-access"
        initial.save(update_fields=["access_fingerprint"])
        corrected = self.correct("Нет, на завтра", {"patch": {}, "visits": [{"index": 1, "date": "2030-11-08"}]}, key="changed-access")
        self.assertEqual(corrected.error_code, "invalid_action_plan")
        self.assertFalse(Appointment.objects.exists())
