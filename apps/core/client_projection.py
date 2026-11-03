"""Linked Client data follows the existing independent Client read boundary."""
from django.db.models import F, Q
from rest_framework import serializers

from apps.businesses.access import Resources
from apps.clients.models import Client
from apps.core.crm_read_scope import readable_across_businesses, readable_link, readable_queryset


def reader_actor(context):
    return getattr(context.get("request"), "user", None) or context.get("actor")


def visible_client(client, *, actor, business, context=None):
    if client is None or actor is None or client.business_id != business.pk:
        return None
    if context is not None:
        businesses = context.setdefault("client_projection_businesses", {})
        business = businesses.setdefault(business.pk, business)
        known = context.get("client_projection_visibility", {})
        key = (getattr(actor, "pk", None), business.pk, client.pk)
        if key in known:
            return client if known[key] else None
    return readable_link(client, actor=actor, business=business, resource=Resources.CLIENTS)


def client_label(client, *, actor, business, fallback="", context=None):
    client = visible_client(client, actor=actor, business=business, context=context)
    return client.full_name if client is not None else fallback


def client_search_q(actor, term, *, path="client", fields=("full_name", "phone", "email")):
    text = Q(pk__in=[])
    for field in fields:
        text |= Q(**{f"{path}__{field}__icontains": term})
    return client_relation_q(actor, path=path) & text


def client_relation_q(actor, *, path="client"):
    clients = readable_across_businesses(Client.objects.all(), actor=actor, resource=Resources.CLIENTS) if actor is not None else Client.objects.none()
    return Q(**{f"{path}__in": clients, f"{path}__business_id": F("business_id")})


def redact_client_metadata(value):
    if isinstance(value, list):
        return [redact_client_metadata(item) for item in value]
    if isinstance(value, dict):
        private = {"client", "client_id", "client_name", "client_phone", "client_email", "full_name", "phone", "email",
                   "normalized_phone", "normalized_email", "telegram_id", "whatsapp_id", "instagram_id", "recipient_id"}
        return {key: redact_client_metadata(item) for key, item in value.items() if str(key).casefold() not in private}
    return value


class ClientProjectionMixin:
    client_private_copies = ()

    def _prime_client_visibility(self):
        if not isinstance(self.parent, serializers.ListSerializer):
            return
        actor = reader_actor(self.context)
        if actor is None:
            return
        instances = self.parent.instance
        if instances is None:
            return
        primed = self.context.setdefault("client_projection_lists", set())
        if id(self.parent) in primed:
            return
        primed.add(id(self.parent))
        known = self.context.setdefault("client_projection_visibility", {})
        businesses = self.context.setdefault("client_projection_businesses", {})
        by_business = {}
        for item in instances:
            client_id = getattr(item, "client_id", None)
            key = (actor.pk, item.business_id, client_id)
            if client_id is not None and key not in known:
                by_business.setdefault(item.business_id, set()).add(client_id)
                businesses.setdefault(item.business_id, item.business)
        for business_id, ids in by_business.items():
            readable = readable_queryset(Client.objects.filter(pk__in=ids), actor=actor,
                                         business=businesses[business_id], resource=Resources.CLIENTS)
            allowed = set(readable.values_list("pk", flat=True))
            known.update({(actor.pk, business_id, pk): pk in allowed for pk in ids})

    def to_representation(self, instance):
        self._prime_client_visibility()
        data = super().to_representation(instance)
        client = getattr(instance, "client", None)
        if client is not None and visible_client(client, actor=reader_actor(self.context),
                                                 business=instance.business, context=self.context) is None:
            if "client" in data:
                data["client"] = None
            for key in list(data):
                if key.startswith("client_"):
                    data[key] = None if key == "client_id" else ""
            for key in self.client_private_copies:
                if key in data:
                    data[key] = {} if isinstance(data[key], dict) else [] if isinstance(data[key], list) else ""
            if str(data.get("action_url") or "").startswith("/app/clients"):
                data["action_url"] = ""
        return data
