"""Server slot/consent checks with real classification and reply generation."""
from django.utils.dateparse import parse_datetime
from apps.scheduling.models import Appointment


def run_booking(c):
    e, lab = c.e, c.lab
    for label in ("exact-replay", "became-busy", "no-consent", "staff-policy", "tool-disabled"):
        def scenario(mode=label):
            tools = ["create_client", "create_lead", "create_task", "create_deal", "handoff_to_manager"]
            options = {"tools": tools} if mode == "tool-disabled" else {}
            c.configure(booking=True, automatic=mode != "staff-policy", **options)
            conversation, message = c.fresh("Хочу записаться на консультацию Luma к Alex Birch. Предложите свободное время.", linked=True)
            initial_appointments = Appointment.objects.count()
            first = c.process(conversation, message)
            first_data = c.observe(conversation, first)
            assert Appointment.objects.count() == initial_appointments, "Appointment created before client selection"
            assert not conversation.handoff_required and first.reply_message, first_data
            slots = conversation.metadata_json.get("auto_booking", {}).get("offered_slots", [])
            if mode in {"exact-replay", "became-busy", "no-consent"}:
                assert slots and first.reply_message.status == "sent", first_data
            slot = slots[0] if slots else None
            if mode == "became-busy":
                Appointment.objects.create(business=lab.business, client=lab.client,
                    service_id=slot["service_id"], resource_id=slot["resource_id"],
                    start_at=parse_datetime(slot["start_at"]), end_at=parse_datetime(slot["end_at"]))
            before = Appointment.objects.count()
            selection = c.inbound(conversation, "Мне нужно подумать, пока не записывайте." if mode == "no-consent" else "1 вариант подходит")
            result = c.process(conversation, selection)
            data = c.observe(conversation, result)
            record = None
            if mode == "exact-replay":
                assert result.booking and result.booking.status == "booked", data
                assert Appointment.objects.count() == before + 1
                appointment = result.booking.appointment
                appointment.refresh_from_db()
                assert appointment.business_id == lab.business.pk and appointment.client_id == lab.client.pk
                assert appointment.service_id == slot["service_id"] and appointment.resource_id == slot["resource_id"]
                assert appointment.start_at == parse_datetime(slot["start_at"]) and appointment.end_at == parse_datetime(slot["end_at"])
                record = {"id": appointment.pk, "client": appointment.client_id, "service": appointment.service_id,
                          "resource": appointment.resource_id, "start_at": appointment.start_at.isoformat(), "end_at": appointment.end_at.isoformat()}
                counts, calls = lab.counts(), len(e.transport.calls)
                repeated = c.process(conversation, selection)
                assert lab.counts() == counts and len(e.transport.calls) == calls
                assert repeated.booking and repeated.booking.appointment.pk == appointment.pk
            else:
                assert Appointment.objects.count() == before, (mode, data)
                assert not result.booking or result.booking.status != "booked", data
                if mode != "no-consent":
                    assert result.booking and result.booking.status == "requires_staff", data
                    assert conversation.handoff_required and not conversation.bot_enabled, data
                    assert result.reply_message and result.reply_message.sender_type == "system", data
                    assert "администратор" in result.reply_message.text.casefold(), data
            return 200, {**data, "offer": first_data, "selected_slot": slot, "actual_record": record,
                         "booking": result.booking.status if result.booking else None,
                         "delivery_receipt": "controlled_synthetic_acknowledgement"}
        e.run("booking-"+label, scenario, rubric="No appointment before consent; exact same-business/client/service/resource/time; replay free and unique; busy/no consent/staff policy/disabled tool never auto-book")
    c.configure()
