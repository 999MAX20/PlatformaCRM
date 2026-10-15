from rest_framework import serializers

from apps.support.access import PLATFORM_ROLES
from apps.support.models import CaseEvent, InternalNote, PublicMessage, SupportCase
from apps.support.services import TRANSITIONS


class StrictInput(serializers.Serializer):
    def to_internal_value(self, data):
        if not hasattr(data, "keys"):
            raise serializers.ValidationError({"non_field_errors": "Expected an object."})
        unexpected = set(data.keys()) - set(self.fields)
        if unexpected:
            raise serializers.ValidationError({key: "Unknown field." for key in sorted(unexpected)})
        return super().to_internal_value(data)


class CaseContext(StrictInput):
    business = serializers.IntegerField(min_value=1, required=False)

    def validate(self, attrs):
        if not self.context.get("platform") and not attrs.get("business"):
            raise serializers.ValidationError({"business": "Select a business."})
        return attrs


class PageInput(CaseContext):
    page = serializers.IntegerField(min_value=1, default=1)
    page_size = serializers.IntegerField(min_value=1, max_value=100, default=20)


class ListInput(PageInput):
    search = serializers.CharField(max_length=200, allow_blank=True, required=False)
    status = serializers.ChoiceField(choices=[*SupportCase.Statuses.values, "active", ""], required=False)
    assignee = serializers.CharField(max_length=20, allow_blank=True, required=False)
    unread = serializers.BooleanField(required=False)

    def validate_assignee(self, value):
        if value and not self.context.get("platform"):
            raise serializers.ValidationError("This filter is for platform employees.")
        if value not in {"", "me", "unassigned", "unavailable"} and not (value.isascii() and value.isdecimal() and 0 < int(value) < 2**63):
            raise serializers.ValidationError("Select a valid assignee.")
        return value


class StaffInput(PageInput):
    search = serializers.CharField(max_length=200, allow_blank=True, required=False)


class CreateInput(StrictInput):
    subject = serializers.CharField(max_length=200, trim_whitespace=True)
    text = serializers.CharField(max_length=6000, trim_whitespace=True)


class IncidentInput(StrictInput):
    component = serializers.ChoiceField(choices=["automations", "notifications", "exports", "files"])
    episode = serializers.IntegerField(min_value=1)


class IncidentLinkInput(IncidentInput):
    business = serializers.IntegerField(min_value=1)


class IncidentContext(IncidentLinkInput):
    page = serializers.IntegerField(min_value=1, default=1)
    page_size = serializers.IntegerField(min_value=1, max_value=100, default=20)


class PlatformCreateInput(CreateInput):
    business = serializers.IntegerField(min_value=1)
    incident = IncidentInput(required=False)


class MessageInput(StrictInput):
    text = serializers.CharField(max_length=6000, trim_whitespace=True)


class AssignmentInput(StrictInput):
    assigned_to = serializers.IntegerField(min_value=1, allow_null=True)
    version = serializers.IntegerField(min_value=1)


class ReopenInput(StrictInput):
    reason = serializers.CharField(max_length=4000, trim_whitespace=True)
    version = serializers.IntegerField(min_value=1)


class TransitionInput(StrictInput):
    status = serializers.ChoiceField(choices=SupportCase.Statuses.choices)
    reason = serializers.CharField(max_length=4000, trim_whitespace=True, allow_blank=True, default="")
    version = serializers.IntegerField(min_value=1)


class ReadInput(StrictInput):
    through_id = serializers.IntegerField(min_value=1)


def actor_identity(user):
    return {"id": user.pk, "name": user.full_name or user.username}


class CaseSerializer(serializers.ModelSerializer):
    number = serializers.SerializerMethodField()
    business_name = serializers.CharField(source="business.name", read_only=True)
    business_timezone = serializers.CharField(source="business.timezone", read_only=True)
    author = serializers.SerializerMethodField()
    contact = serializers.SerializerMethodField()
    assignee = serializers.SerializerMethodField()
    unread_count = serializers.IntegerField(read_only=True)
    available_actions = serializers.SerializerMethodField()

    class Meta:
        model = SupportCase
        fields = ["id", "number", "business", "business_name", "business_timezone", "subject", "source", "status", "author", "contact", "assignee", "version", "created_at", "updated_at", "last_public_message_at", "resolved_at", "unread_count", "available_actions"]
        read_only_fields = fields

    def get_number(self, case):
        return f"SUP-{case.pk:06d}"

    def get_author(self, case):
        return actor_identity(case.created_by)

    def get_contact(self, case):
        return actor_identity(case.requester)

    def get_assignee(self, case):
        if not case.assigned_to_id:
            return None
        result = actor_identity(case.assigned_to)
        if self.context.get("platform"):
            result["available"] = case.assigned_to.is_active and (case.assigned_to.is_superuser or case.assigned_to.role in PLATFORM_ROLES)
        return result

    def get_available_actions(self, case):
        platform = self.context.get("platform", False)
        return {
            "reply": True, "assign": platform, "internal_note": platform,
            "reopen": case.status == "resolved",
            "transitions": sorted(TRANSITIONS[case.status]) if platform else [],
        }


class PublicMessageSerializer(serializers.ModelSerializer):
    author = serializers.SerializerMethodField()

    class Meta:
        model = PublicMessage
        fields = ["id", "author", "source", "text", "created_at"]
        read_only_fields = fields

    def get_author(self, message):
        return actor_identity(message.author)


class InternalNoteSerializer(serializers.ModelSerializer):
    author = serializers.SerializerMethodField()

    class Meta:
        model = InternalNote
        fields = ["id", "author", "text", "created_at"]
        read_only_fields = fields

    def get_author(self, note):
        return actor_identity(note.author)


class CaseEventSerializer(serializers.ModelSerializer):
    actor = serializers.SerializerMethodField()

    class Meta:
        model = CaseEvent
        fields = ["id", "actor", "kind", "old_value", "new_value", "reason", "created_at"]
        read_only_fields = fields

    def get_actor(self, event):
        return actor_identity(event.actor)
