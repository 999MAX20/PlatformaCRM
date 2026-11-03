from django.shortcuts import get_object_or_404
from rest_framework import serializers

from apps.businesses.access import Resources
from apps.core.crm_read_scope import readable_link, readable_queryset
from apps.core.crm_cards import lead_crm_card, deal_crm_card
from apps.crm.models import Deal
from apps.leads.models import Lead


class LegacyRecordQuery(serializers.Serializer):
    business = serializers.IntegerField(min_value=1)
    kind = serializers.ChoiceField(choices=("lead", "deal"))
    object_id = serializers.IntegerField(min_value=1)


def legacy_record_links(queryset, *, actor, business, kind, object_id):
    model, resource = (Lead, Resources.LEADS) if kind == "lead" else (Deal, Resources.DEALS)
    source = get_object_or_404(readable_queryset(model.objects.all(), actor=actor, business=business, resource=resource), pk=object_id)
    lead = source if kind == "lead" else readable_link(source.lead, actor=actor, business=business, resource=Resources.LEADS)
    # A shared client or equal numeric ID is never proof of a historical link.
    linked = queryset.filter(lead_id=lead.pk, client_id=source.client_id) if lead else queryset.none()
    client = readable_link(source.client, actor=actor, business=business, resource=Resources.CLIENTS)
    card = lead_crm_card(source, actor=actor) if kind == "lead" else deal_crm_card(source, actor=actor)
    return linked.order_by("-start_at", "-pk"), {"kind": kind, "id": source.pk, "client": client.pk if client else None, "card": card}
