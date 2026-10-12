"""Public, database-backed location selection and qualified appointment offers."""
import re
from datetime import timedelta

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import APIException, ValidationError

from apps.scheduling.availability import business_zone, get_available_slots
from .models import Branch, BranchService, SpecialistBranch


def public_branches(conversation):
    query = Branch.objects.filter(business=conversation.business, is_active=True, archived_at__isnull=True)
    ids = (conversation.bot.settings_json or {}).get("branch_ids")
    return query.filter(pk__in=ids) if ids is not None else query


def validate_agent_branches(business, settings, actor):
    from .access import accessible_branches, assert_network_grant
    ids = settings.get("branch_ids")
    if ids is None:
        if Branch.objects.filter(business=business).exists():
            assert_network_grant(actor, business)
        return
    if not isinstance(ids, list) or any(type(value) is not int or value <= 0 for value in ids):
        raise ValidationError({"branch_ids": "Select branch identifiers."})
    if accessible_branches(actor, business).filter(pk__in=ids).count() != len(set(ids)):
        raise ValidationError({"branch_ids": "Select branches within your permitted business scope."})


def selection_from_text(text, branches):
    """Only explicit names/addresses or an explicit any-location choice select a branch."""
    text = (text or "").casefold()
    if re.search(r"любо[йм].{0,12}филиал|any (?:branch|location)|кез келген филиал", text):
        return "any"
    matches = [branch.pk for branch in branches if any(
        value and len(value.strip()) >= 2 and re.search(r"(?<!\w)" + re.escape(value.casefold()) + r"(?!\w)", text)
        for value in [branch.name, branch.address])]
    if matches:
        if len(matches) == 1 and not re.search(r"\bне\b|\bnot\b|емес", text):
            return matches[0]
        return "choose"
    if re.search(r"друг.{0,10}филиал|(?:change|another).{0,12}(?:branch|location)|басқа филиал", text):
        return "choose"
    return None


def selected_branch(conversation, branches, messages):
    for text in messages:
        selected = selection_from_text(text, branches)
        if selected is not None:
            return selected
    remembered = (conversation.metadata_json or {}).get("branch_selection", {}).get("value")
    if remembered == "any" or remembered in [branch.pk for branch in branches]:
        return remembered
    return branches[0].pk if len(branches) == 1 else "choose"


@transaction.atomic
def remember_branch_reply(conversation, message):
    from apps.bots.models import BotConversation
    branches = list(public_branches(conversation))
    selected = selection_from_text(message.text, branches)
    if selected is None:
        return
    locked = BotConversation.objects.select_for_update().get(pk=conversation.pk)
    metadata = dict(locked.metadata_json or {})
    old = metadata.get("branch_selection") or {}
    if old.get("message_id", 0) > message.pk:
        return
    metadata["branch_selection"] = {"value": selected, "message_id": message.pk}
    # A new location choice always needs a fresh, explicitly numbered offer.
    booking = dict(metadata.get("auto_booking") or {})
    booking["offered_slots"] = []
    metadata["auto_booking"] = booking
    locked.metadata_json = metadata
    locked.save(update_fields=["metadata_json", "updated_at"])
    conversation.metadata_json = metadata


def build_branch_context(conversation, *, qualification=None, days=5, slots_per_resource=3, message_context=None, booking_only=False):
    from apps.bots.scheduling_context import _match_service, _remembered_resource, _required_questions
    branches = list(public_branches(conversation).order_by("name", "id"))
    messages = ([item["text"] for item in reversed(message_context) if item["direction"] == "inbound"]
                if message_context is not None else list(conversation.messages.filter(direction="inbound")
                    .order_by("-created_at", "-id").values_list("text", flat=True)[:100]))
    selection = selected_branch(conversation, branches, messages)
    selected = branches if selection == "any" else [branch for branch in branches if branch.pk == selection]
    business = conversation.business
    today = timezone.localtime(timezone.now(), business_zone(business)).date()
    intent = getattr(qualification, "intent", None) == "appointment_request" if qualification else any(
        re.search(r"запис|брон|слот|вариант|жазыл|book|appointment", text.casefold()) for text in messages[:3])
    offers = list(BranchService.objects.filter(branch__in=selected or branches, is_active=True,
        service__is_active=True, service__is_archived=False).select_related("service", "branch"))
    service_data = lambda offer: {"id": offer.service_id, "name": offer.service.name,
        "branch_id": offer.branch_id, "branch_name": offer.branch.name,
        "duration_minutes": offer.duration_minutes, "price_from": str(offer.price_from) if offer.price_from is not None else None}
    matched = _match_service(list({offer.service_id: offer.service for offer in offers}.values()),
        " ".join(messages[:8]).casefold(), qualification=qualification)
    assignments = list(SpecialistBranch.objects.filter(branch__in=selected, is_active=True,
        resource__is_active=True, resource__retired_at__isnull=True, resource__resource_type="staff")
        .select_related("resource", "branch").prefetch_related("services"))
    if matched:
        assignments = [row for row in assignments if matched.pk in [service.pk for service in row.services.all()]]
    resources = list({row.resource_id: row.resource for row in assignments}.values())
    resource = _remembered_resource(resources, messages[:8])
    public_resource = lambda item: {"id": item.pk, "name": item.name, "resource_type": item.resource_type,
                                  "profession": item.profession, "description": item.public_description}
    context = {"currency": business.currency, "timezone": business.timezone, "local_date": today.isoformat(),
        "branches": [{"id": branch.pk, "name": branch.name, "address": branch.address, "phone": branch.phone} for branch in branches],
        "branch_selection": selection, "services": [service_data(offer) for offer in offers],
        "resources": [public_resource(item) for item in resources],
        "matched_service": {"id": matched.pk, "name": matched.name} if matched else None,
        "matched_resource": public_resource(resource) if resource else None,
        "next_available_slots": [], "required_questions": [], "booking_intent": intent}
    if booking_only and not intent:
        return context
    if not branches:
        context["required_questions"] = ["Передать администратору: нет доступного филиала."]
        return context
    if not selected:
        context["required_questions"] = ["Уточнить филиал по названию или адресу; клиент может явно выбрать любой филиал. Не предлагать время до выбора филиала."]
        return context
    context["required_questions"] = _required_questions(matched_service=matched, matched_resource=resource, resources=resources)
    if not matched:
        return context
    latest = (messages[0] if messages else "").casefold()
    offsets = [2] if "послезавтра" in latest else [1] if "завтра" in latest else [0] if "сегодня" in latest else range(days)
    context["searched_dates"] = [(today + timedelta(days=offset)).isoformat() for offset in offsets]
    for offset in offsets:
        for assignment in assignments:
            if resource and assignment.resource_id != resource.pk:
                continue
            offer = next((item for item in offers if item.branch_id == assignment.branch_id and item.service_id == matched.pk), None)
            if offer is None:
                continue
            try:
                slots = get_available_slots(business, matched, today + timedelta(days=offset),
                    resource=assignment.resource, branch=assignment.branch)
            except (ValueError, APIException):
                continue
            for start in [slot for slot in slots if slot > timezone.now()][:slots_per_resource]:
                context["next_available_slots"].append({"service_id": matched.pk, "service_name": matched.name,
                    "resource_id": assignment.resource_id, "resource_name": assignment.resource.name,
                    "branch_id": assignment.branch_id, "branch_name": assignment.branch.name, "branch_address": assignment.branch.address,
                    "price_from": str(offer.price_from) if offer.price_from is not None else None, "duration_minutes": offer.duration_minutes,
                    "start_at": start.isoformat(), "end_at": (start + timedelta(minutes=offer.duration_minutes)).isoformat()})
    context["next_available_slots"] = sorted(context["next_available_slots"], key=lambda slot: slot["start_at"])[:8]
    if not context["next_available_slots"]:
        context["required_questions"].append("Свободных окон нет: предложить другой день или, с согласия клиента, другой филиал.")
    return context
