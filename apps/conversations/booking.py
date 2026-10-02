from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from django.utils import timezone
from django.db import transaction

from apps.activities.services import create_activity_event
from apps.activities.taxonomy import ActivityEvents
from apps.bots.models import BotConversation, BotMessage
from apps.businesses.access import Resources
from apps.businesses.models import Business
from apps.businesses.capabilities import assert_resource_enabled
from apps.core.audit import write_actor_audit_log
from apps.core.models import AuditLog
from apps.leads.services import can_mark_lead_appointment_created, mark_lead_appointment_created
from apps.scheduling.models import Appointment, Resource
from apps.scheduling.services import schedule_appointment_followups, validate_appointment_availability
from apps.scheduling.availability import business_zone
from apps.services.models import Service


BOOKING_META_KEY = "auto_booking"


@dataclass
class BookingResult:
    status: str
    reason: str = ""
    appointment: Appointment | None = None
    confirmation_message: BotMessage | None = None


def store_offered_slots(*, conversation: BotConversation, scheduling_context: dict[str, Any], ai_log_id: int | None = None, runtime_fingerprint: str = "", offer_message_id: int | None = None) -> None:
    slots = scheduling_context.get("next_available_slots") or []
    if not slots:
        return
    metadata = dict(conversation.metadata_json or {})
    booking_meta = dict(metadata.get(BOOKING_META_KEY) or {})
    booking_meta.update(
        {
            "offered_slots": slots[:8],
            "ai_log_id": ai_log_id,
            "offered_at": timezone.now().isoformat(),
            "runtime_fingerprint": runtime_fingerprint,
            "offer_message_id": offer_message_id,
        }
    )
    metadata[BOOKING_META_KEY] = booking_meta
    conversation.metadata_json = metadata
    conversation.save(update_fields=["metadata_json", "updated_at"])


def maybe_create_appointment_from_reply(*, conversation: BotConversation, message: BotMessage) -> BookingResult:
    assert_resource_enabled(conversation.business, Resources.APPOINTMENTS)
    slot = _select_offered_slot(conversation=conversation, text=message.text)
    if not slot:
        return BookingResult(status="skipped", reason="No offered slot matched the client reply.")
    own = (conversation.bot.settings_json or {}).get("auto_crm_pipeline") or {}
    if own.get("creation_policy") == "automatic":
        return _commit_selected_slot(conversation=conversation, message=message, slot=slot)
    # A client reply selects a preference; only staff may commit a booking.
    _save_booking_meta(conversation, status="requires_staff", slot=slot,
                       reason="An authorized staff member must create the appointment.")
    return BookingResult(status="requires_staff", reason="Staff booking is required.")


@transaction.atomic
def create_appointment_from_conversation(*, conversation: BotConversation, service_id: int, start_at, actor=None, resource_id: int | None = None, notes: str = "", update_lead_status: bool = True) -> Appointment:
    assert_resource_enabled(conversation.business, Resources.APPOINTMENTS)
    Business.objects.select_for_update().get(pk=conversation.business_id)
    if not conversation.client_id:
        raise ValueError("Conversation must be linked to a client before booking an appointment.")

    service = Service.objects.filter(id=service_id, business=conversation.business, is_active=True).first()
    if service is None:
        raise ValueError("Service was not found in this business.")

    resource = None
    if resource_id:
        resource = Resource.objects.filter(id=resource_id, business=conversation.business, is_active=True).first()
        if resource is None:
            raise ValueError("Resource was not found in this business.")

    end_at = validate_appointment_availability(conversation.business, service, start_at, resource=resource)
    if conversation.lead_id:
        if conversation.lead.business_id != conversation.business_id:
            raise ValueError("Lead must belong to the conversation business.")
        if update_lead_status and not can_mark_lead_appointment_created(conversation.lead):
            raise ValueError(f"Cannot move lead from '{conversation.lead.status}' to appointment_created.")
    appointment = Appointment.objects.create(
        business=conversation.business,
        client=conversation.client,
        lead=conversation.lead,
        service=service,
        resource=resource,
        start_at=start_at,
        end_at=end_at,
        status=Appointment.Statuses.CREATED,
        source=_appointment_source(conversation.channel),
        notes=notes or f"Created from inbox conversation #{conversation.id}",
    )
    write_actor_audit_log(
        actor=actor,
        action=AuditLog.Actions.CREATE,
        instance=appointment,
        metadata={
            "event_type": ActivityEvents.APPOINTMENT_CREATED,
            "source": "inbox",
            "conversation_id": conversation.id,
            "service_id": service.id,
            "resource_id": resource.id if resource else None,
        },
    )
    if conversation.lead_id and update_lead_status:
        mark_lead_appointment_created(
            lead=conversation.lead,
            actor=actor if actor and getattr(actor, "is_authenticated", False) else None,
            service=service,
            appointment=appointment,
            resource=resource,
            source="inbox",
            activity_metadata={"conversation_id": conversation.id},
        )
    schedule_appointment_followups(
        appointment,
        responsible_user=conversation.lead.responsible_user if conversation.lead_id and conversation.lead.responsible_user_id else conversation.assigned_to,
    )
    create_activity_event(
        business=conversation.business,
        client=conversation.client,
        actor=actor if actor and getattr(actor, "is_authenticated", False) else None,
        instance=appointment,
        event_type=ActivityEvents.APPOINTMENT_CREATED,
        category="appointment",
        source="inbox",
        text=f"Appointment created from inbox conversation #{conversation.id}",
        metadata={
            "event_type": ActivityEvents.APPOINTMENT_CREATED,
            "conversation_id": conversation.id,
            "service_id": service.id,
            "resource_id": resource.id if resource else None,
        },
    )
    return appointment


def format_booking_offer(conversation, slots):
    """Only these server-rendered, unambiguous options can authorize a booking."""
    zone = business_zone(conversation.business)
    language = conversation.bot.default_language
    title = {"ru": "Для записи выберите номер варианта:", "kk": "Жазылу үшін нұсқа нөмірін таңдаңыз:", "en": "To book, choose an option number:"}.get(language, "To book, choose an option number:")
    lines = [title]
    for index, slot in enumerate(slots, 1):
        local = datetime.fromisoformat(slot["start_at"]).astimezone(zone)
        lines.append(f"{index}. {slot['service_name']} · {slot['resource_name']} · {local:%d.%m.%Y %H:%M}")
    return "\n".join(lines)


@transaction.atomic
def _commit_selected_slot(*, conversation, message, slot):
    from apps.bots.automation_policy import automatic_creation_actor
    from apps.bots.inbox_service import send_outbound_message
    from rest_framework.exceptions import APIException

    # Same business lock/order as availability writes; the conversation serializes replay.
    Business.objects.select_for_update().get(pk=conversation.business_id)
    conversation = BotConversation.objects.select_for_update().select_related("business", "bot", "client", "lead").get(pk=conversation.pk)
    meta = (conversation.metadata_json or {}).get(BOOKING_META_KEY) or {}
    fingerprint = meta.get("runtime_fingerprint")
    if not fingerprint or slot not in (meta.get("offered_slots") or []):
        return BookingResult(status="requires_staff", reason="Review current booking options before creating an appointment.")
    if not conversation.messages.filter(pk=meta.get("offer_message_id"), direction="outbound", status=BotMessage.Statuses.SENT).exists():
        return BookingResult(status="requires_staff", reason="Booking options have not been delivered.")
    try:
        actor = automatic_creation_actor(conversation, {"create_appointment"}, expected_fingerprint=fingerprint)
        start = datetime.fromisoformat(slot["start_at"])
        if timezone.is_naive(start) or start <= timezone.now() or not slot.get("resource_id") or not slot.get("service_id"):
            raise ValueError("The selected slot is no longer valid.")
        old_id = (meta.get("booked_slots") or {}).get(f"{slot['service_id']}:{slot['resource_id']}:{slot['start_at']}")
        if old_id:
            appointment = Appointment.objects.filter(pk=old_id, business=conversation.business, client=conversation.client).first()
            if appointment:
                return BookingResult(status="booked", reason="Previously created appointment.", appointment=appointment)
        appointment = create_appointment_from_conversation(
            conversation=conversation, service_id=slot["service_id"], resource_id=slot["resource_id"], start_at=start,
            actor=actor, update_lead_status=False, notes=f"Customer selected option in Inbox message #{message.id}",
        )
    except (ValueError, APIException) as exc:
        _save_booking_meta(conversation, status="requires_staff", slot=slot, reason=str(exc))
        return BookingResult(status="requires_staff", reason="The selected slot needs staff review.")
    meta = dict(meta)
    booked = dict(meta.get("booked_slots") or {})
    booked[f"{slot['service_id']}:{slot['resource_id']}:{slot['start_at']}"] = appointment.id
    meta["booked_slots"] = booked
    metadata = dict(conversation.metadata_json or {}); metadata[BOOKING_META_KEY] = meta
    conversation.metadata_json = metadata
    _save_booking_meta(conversation, status="booked", slot=slot, appointment=appointment)
    local = timezone.localtime(appointment.start_at, business_zone(conversation.business))
    label = {"ru": "Запись создана", "kk": "Жазылу жасалды", "en": "Appointment booked"}.get(conversation.bot.default_language, "Appointment booked")
    confirmation = send_outbound_message(conversation, f"{label}: {slot['service_name']} · {slot['resource_name']} · {local:%d.%m.%Y %H:%M}.", user=None,
        sender_type=BotMessage.SenderTypes.SYSTEM, idempotency_key=f"automatic-booking:{appointment.id}")
    return BookingResult(status="booked", appointment=appointment, confirmation_message=confirmation)


def _select_offered_slot(*, conversation: BotConversation, text: str) -> dict[str, Any] | None:
    slots = ((conversation.metadata_json or {}).get(BOOKING_META_KEY) or {}).get("offered_slots") or []
    if not slots:
        return None
    normalized = (text or "").strip().lower()
    own = (conversation.bot.settings_json or {}).get("auto_crm_pipeline") or {}
    if own.get("creation_policy") == "automatic":
        # A number in a price/date/question/negation is not consent to book.
        match = re.fullmatch(r"(?:вариант|выбираю|запишите|option|choose|book|нұсқа)?\s*([1-8])(?:\s*(?:вариант|нұсқа))?(?:\s*(?:подходит|пожалуйста|please))?[.!]?", normalized)
        if match and int(match.group(1)) <= len(slots):
            return slots[int(match.group(1)) - 1]
        return None
    index_match = re.search(r"\b(?:вариант\s*)?([1-8])\b", normalized)
    if index_match:
        index = int(index_match.group(1)) - 1
        if 0 <= index < len(slots):
            return slots[index]
    if any(word in normalized for word in ["первый", "первое", "1-й"]):
        return slots[0]
    if len(slots) == 1 and normalized in {"да", "ок", "окей", "подходит", "подтверждаю"}:
        return slots[0]

    time_matches = set(re.findall(r"\b([01]?\d|2[0-3])[:.]([0-5]\d)\b", normalized))
    if not time_matches:
        return None
    matched = []
    for slot in slots:
        try:
            start_at = datetime.fromisoformat(str(slot["start_at"]))
        except (KeyError, ValueError, TypeError):
            continue
        local_start = timezone.localtime(start_at)
        if (str(local_start.hour), f"{local_start.minute:02d}") in time_matches or (f"{local_start.hour:02d}", f"{local_start.minute:02d}") in time_matches:
            matched.append(slot)
    return matched[0] if len(matched) == 1 else None


def _save_booking_meta(conversation: BotConversation, *, status: str, appointment: Appointment | None = None, slot=None, reason: str = "") -> None:
    metadata = dict(conversation.metadata_json or {})
    booking_meta = dict(metadata.get(BOOKING_META_KEY) or {})
    booking_meta.update(
        {
            "status": status,
            "appointment_id": appointment.id if appointment else booking_meta.get("appointment_id"),
            "selected_slot": slot or booking_meta.get("selected_slot"),
            "reason": reason,
            "updated_at": timezone.now().isoformat(),
        }
    )
    metadata[BOOKING_META_KEY] = booking_meta
    conversation.metadata_json = metadata
    conversation.save(update_fields=["metadata_json", "updated_at"])


def _appointment_source(channel: str) -> str:
    allowed = {choice[0] for choice in Appointment.Sources.choices}
    return channel if channel in allowed else Appointment.Sources.BOT
