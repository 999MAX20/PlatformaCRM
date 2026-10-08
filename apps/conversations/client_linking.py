"""Confirmed client replacement; CRM records themselves are never reassigned."""
import hashlib
import json

from django.core import signing
from django.db import transaction
from rest_framework.exceptions import ValidationError

from apps.activities.taxonomy import ActivityEvents
from apps.bots.inbox_service import record_inbox_crm_activity
from apps.bots.models import BotConversation
from apps.businesses.access import Actions, Resources, assert_can
from apps.businesses.capabilities import assert_resource_enabled
from apps.clients.models import Client
from apps.conversations.inbox_helpers import QUALIFICATION_PREVIEW_META_KEY
from apps.core.audit import write_actor_audit_log
from apps.core.crm_read_scope import readable_link
from apps.core.models import AuditLog
from apps.crm.models import Deal
from apps.leads.models import Lead

SALT = "inbox-client-replacement-v1"


def _visible(entity, *, actor, business, resource, title):
    if readable_link(entity, actor=actor, business=business, resource=resource) is None:
        return None
    return {"id": entity.id, "title": getattr(entity, title)}


@transaction.atomic
def link_conversation_client(conversation, *, actor, client_id, confirmation_token=""):
    conversation = BotConversation.objects.select_for_update().get(
        pk=conversation.pk, business_id=conversation.business_id,
    )
    business = conversation.business
    assert_resource_enabled(business, Resources.CONVERSATIONS)
    assert_can(actor, business, Resources.CONVERSATIONS, Actions.UPDATE, obj=conversation)
    assert_resource_enabled(business, Resources.CLIENTS)
    client = Client.objects.filter(pk=client_id, business=business).first()
    if client is None:
        raise ValidationError({"client_id": "Client was not found in this business."})
    assert_can(actor, business, Resources.CLIENTS, Actions.VIEW, obj=client)
    if conversation.client_id == client.id:
        return conversation, None

    # Lock affected records while comparing their current client relationships.
    links = {
        "lead": Lead.objects.select_for_update().filter(pk=conversation.lead_id).first(),
        "deal": Deal.objects.select_for_update().filter(pk=conversation.deal_id).first(),
    }
    conflicts = {kind: entity for kind, entity in links.items()
                 if entity and (entity.business_id != business.id or entity.client_id != client.id)}
    snapshot = {
        "actor": actor.pk, "business": business.pk, "conversation": conversation.pk,
        "before": conversation.client_id, "target": client.pk,
        "links": {kind: [entity.pk, entity.client_id, entity.business_id,
                          entity.message if kind == "lead" else entity.title] if entity else None
                  for kind, entity in links.items()},
    }
    # Only an opaque digest is signed: hidden child IDs/names never enter the token.
    digest = hashlib.sha256(json.dumps(snapshot, sort_keys=True).encode()).hexdigest()
    confirmed = False
    if confirmation_token:
        try:
            confirmed = signing.loads(confirmation_token, salt=SALT, max_age=600) == digest
        except signing.BadSignature:
            pass
    if (conflicts or confirmation_token) and not confirmed:
        return conversation, {
            "requires_confirmation": True,
            "confirmation_token": signing.dumps(digest, salt=SALT),
            "previous_client": _visible(conversation.client, actor=actor, business=business,
                                        resource=Resources.CLIENTS, title="full_name"),
            "next_client": {"id": client.id, "title": client.full_name},
            "conflicts": [{"kind": kind, "entity": _visible(
                entity, actor=actor, business=business,
                resource=Resources.LEADS if kind == "lead" else Resources.DEALS,
                title="message" if kind == "lead" else "title",
            )} for kind, entity in conflicts.items()],
        }

    previous_client_id = conversation.client_id
    conversation.client = client
    for kind in conflicts:
        setattr(conversation, kind, None)
    # A CRM proposal reviewed for the previous client cannot authorize new-client work.
    conversation.metadata_json = dict(conversation.metadata_json or {})
    conversation.metadata_json.pop(QUALIFICATION_PREVIEW_META_KEY, None)
    conversation.save(update_fields=["client", *conflicts, "metadata_json", "updated_at"])
    metadata = {
        "kind": "conversation_client_relinked", "previous_client_id": previous_client_id,
        "client_id": client.id, "detached": {kind: entity.pk for kind, entity in conflicts.items()},
    }
    record_inbox_crm_activity(
        conversation, entity=client, event_type=ActivityEvents.CONVERSATION_CLIENT_LINKED,
        actor=actor, text="Conversation linked to client.",
        metadata={"client_id": client.id, "detached_kinds": list(conflicts)},
    )
    write_actor_audit_log(actor=actor, action=AuditLog.Actions.UPDATE,
                          instance=conversation, business=business, metadata=metadata)
    return conversation, None
