"""Client workspace predicates; conversation evidence is permission scoped by caller."""
from django.db.models import CharField, DateTimeField, Exists, F, OuterRef, Q, Subquery
from django.db.models.functions import Cast, Coalesce
from rest_framework.exceptions import ValidationError

from apps.activities.models import TaggedObject
from apps.bots.models import BotMessage
from apps.core.crm_filters import archive_filter, business_date_range, choice, values


def waiting_conversations(queryset):
    messages = BotMessage.objects.filter(conversation_id=OuterRef("pk"))
    inbound = messages.filter(direction="inbound", sender_type="client").order_by("-created_at", "-pk")
    sent = messages.filter(
        direction="outbound", status="sent", sender_type__in=["manager", "ai", "bot"],
    ).annotate(effective_sent_at=Coalesce("sent_at", "delivered_at", "created_at")).order_by("-effective_sent_at", "-pk")
    return queryset.filter(status="open", is_archived=False).annotate(
        last_question=Coalesce(Subquery(inbound.values("created_at")[:1]), "last_inbound_at", output_field=DateTimeField()),
        last_answer=Subquery(sent.values("effective_sent_at")[:1], output_field=DateTimeField()),
    ).filter(last_question__isnull=False).filter(Q(last_answer__isnull=True) | Q(last_answer__lt=F("last_question")))


def client_workspace_filters(queryset, params):
    queryset = archive_filter(queryset, params)
    queryset = business_date_range(queryset, params)
    sources = values(params, "source")
    if sources:
        queryset = queryset.filter(source__in=sources)
    tags = values(params, "tag", ids=True)
    mode = choice(params, "tag_mode", ("any", "all"), "any")
    # Cast is needed because tagged entity IDs are strings on PostgreSQL.
    queryset = queryset.annotate(workspace_entity_id=Cast("pk", CharField()))
    tagged = TaggedObject.objects.filter(
        business_id=OuterRef("business_id"), entity_type="client", entity_id=OuterRef("workspace_entity_id"),
    )
    if tags and mode == "any":
        queryset = queryset.filter(Exists(tagged.filter(tag_id__in=tags)))
    elif tags:
        for tag in tags:
            queryset = queryset.filter(Exists(tagged.filter(tag_id=tag)))
    if len(values(params, "segment", ids=True)) > 1:
        raise ValidationError({"segment": "Select one segment."})
    choice(params, "quick_filter", ("all", "no_reply"), "all")
    choice(params, "handoff", ("", "true"), "")
    return queryset
