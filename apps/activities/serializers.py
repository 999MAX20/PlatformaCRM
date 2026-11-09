from rest_framework import serializers

from apps.activities.models import ActivityEvent, Note, Segment, SegmentFilter, Tag, TaggedObject
from apps.activities.write_validation import CLIENT_LINK_ERROR, HistoryWriteValidationMixin
from apps.activities.segments import assert_segment_filter_visible
from apps.integrations.sanitization import sanitize_error_payload
from apps.crm.field_policy import deal_amount_visible, redact_amount_metadata
from apps.core.client_projection import ClientProjectionMixin, reader_actor, redact_client_metadata, visible_client
from apps.activities.taxonomy import event_label
from apps.clients.duplicate_visibility import project_duplicate_rows


class ActivityEventSerializer(ClientProjectionMixin, HistoryWriteValidationMixin, serializers.ModelSerializer):
    attribution_field = "actor"

    class Meta:
        model = ActivityEvent
        fields = [
            "id",
            "business",
            "client",
            "actor",
            "category",
            "event_type",
            "source",
            "entity_type",
            "entity_id",
            "text",
            "metadata",
            "created_at",
        ]
        read_only_fields = ("actor", "created_at")
        extra_kwargs = {"client": {"error_messages": {"does_not_exist": CLIENT_LINK_ERROR}}}

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["metadata"] = sanitize_error_payload(data.get("metadata") or {})
        request = self.context.get("request")
        actor = getattr(request, "user", None) or self.context.get("actor")
        if instance.event_type == "form_submitted" and isinstance(data["metadata"].get("duplicates"), list):
            data["metadata"] = {**data["metadata"], "duplicates": project_duplicate_rows(
                data["metadata"]["duplicates"], actor=actor, business=instance.business,
            )}
        if (instance.entity_type.casefold() == "deal" or instance.event_type.casefold().startswith("deal.")) and not deal_amount_visible(actor, instance.business):
            data["metadata"] = redact_amount_metadata(data["metadata"])
        if instance.client_id and visible_client(instance.client, actor=actor, business=instance.business, context=self.context) is None:
            data["metadata"] = redact_client_metadata(data["metadata"])
            data["text"] = event_label(instance.event_type) or ""
        return data


class ActivityTimelineSerializer(ActivityEventSerializer):
    """Labels for already-authorized event reads; no account emails or raw metadata UI."""
    actor_name = serializers.SerializerMethodField()
    client_name = serializers.SerializerMethodField()

    class Meta(ActivityEventSerializer.Meta):
        fields = [*ActivityEventSerializer.Meta.fields, "actor_name", "client_name"]

    def get_actor_name(self, event):
        if not event.actor or not (event.actor_id == event.business.owner_id or getattr(event, "actor_is_member", False)):
            return ""
        return event.actor.full_name or event.actor.get_full_name()

    def get_client_name(self, event):
        client = visible_client(event.client, actor=reader_actor(self.context), business=event.business, context=self.context)
        return client.full_name if client is not None else ""


class NoteSerializer(ClientProjectionMixin, HistoryWriteValidationMixin, serializers.ModelSerializer):
    attribution_field = "author"

    class Meta:
        model = Note
        fields = [
            "id",
            "business",
            "client",
            "author",
            "entity_type",
            "entity_id",
            "text",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ("author", "created_at", "updated_at")
        extra_kwargs = {"client": {"error_messages": {"does_not_exist": CLIENT_LINK_ERROR}}}


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = [
            "id",
            "business",
            "name",
            "color",
            "source",
            "created_at",
            "updated_at",
        ]


class TaggedObjectSerializer(serializers.ModelSerializer):
    tag_name = serializers.CharField(source="tag.name", read_only=True)
    tag_color = serializers.CharField(source="tag.color", read_only=True)

    class Meta:
        model = TaggedObject
        fields = [
            "id",
            "business",
            "tag",
            "tag_name",
            "tag_color",
            "entity_type",
            "entity_id",
            "created_at",
        ]
        read_only_fields = ("created_at",)

    def validate(self, attrs):
        business = attrs.get("business") or getattr(self.instance, "business", None)
        tag = attrs.get("tag") or getattr(self.instance, "tag", None)
        if business and tag and tag.business_id != business.id:
            raise serializers.ValidationError("Tag must belong to the selected business.")
        return attrs


class SegmentFilterSerializer(serializers.ModelSerializer):
    class Meta:
        model = SegmentFilter
        fields = [
            "id",
            "business",
            "segment",
            "field",
            "operator",
            "value_json",
            "sort_order",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]

    def validate(self, attrs):
        business = attrs.get("business") or getattr(self.instance, "business", None)
        segment = attrs.get("segment") or getattr(self.instance, "segment", None)
        if business and segment and segment.business_id != business.id:
            raise serializers.ValidationError("Segment must belong to the selected business.")
        if business is None and segment is not None:
            attrs["business"] = segment.business
        if segment is not None:
            assert_segment_filter_visible(
                segment=segment, field=attrs.get("field", getattr(self.instance, "field", None)),
                actor=getattr(self.context.get("request"), "user", None),
            )
        return attrs


class SegmentSerializer(serializers.ModelSerializer):
    filters = SegmentFilterSerializer(many=True, read_only=True)

    class Meta:
        model = Segment
        fields = [
            "id",
            "business",
            "name",
            "description",
            "entity_type",
            "is_active",
            "cached_count",
            "last_evaluated_at",
            "filters",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["cached_count", "last_evaluated_at", "created_at", "updated_at"]
