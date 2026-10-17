from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied

from apps.businesses.access import Resources, can_view_sensitive_field
from apps.clients.models import Client
from apps.clients.services import duplicate_payload, find_duplicate_clients, merge_clients, merge_clients_dry_run
from apps.core.permissions import accessible_businesses


class ClientSerializer(serializers.ModelSerializer):
    manager_user_id = serializers.IntegerField(read_only=True, allow_null=True)
    manager_name = serializers.CharField(read_only=True, allow_null=True, allow_blank=True)
    is_active = serializers.BooleanField(read_only=True)
    has_no_reply = serializers.BooleanField(read_only=True)
    is_vip = serializers.BooleanField(read_only=True)
    leads_count = serializers.IntegerField(read_only=True)
    deals_count = serializers.IntegerField(read_only=True)
    appointments_count = serializers.IntegerField(read_only=True)
    tasks_count = serializers.IntegerField(read_only=True)
    conversations_count = serializers.IntegerField(read_only=True)
    last_activity_at = serializers.DateTimeField(read_only=True, allow_null=True)
    next_step_title = serializers.CharField(read_only=True, allow_blank=True)
    next_step_kind = serializers.CharField(read_only=True)
    next_step_date = serializers.DateTimeField(read_only=True, allow_null=True)
    next_step_priority = serializers.CharField(read_only=True, allow_blank=True)

    class Meta:
        model = Client
        fields = [
            "id",
            "business",
            "full_name",
            "phone",
            "email",
            "whatsapp_id",
            "telegram_id",
            "instagram_id",
            "source",
            "source_detail",
            "source_context_json",
            "notes",
            "is_archived",
            "archived_at",
            "archived_by",
            "archive_reason",
            "created_at",
            "updated_at",
            "manager_user_id",
            "manager_name",
            "is_active",
            "has_no_reply",
            "is_vip",
            "leads_count",
            "deals_count",
            "appointments_count",
            "tasks_count",
            "conversations_count",
            "last_activity_at",
            "next_step_title",
            "next_step_kind",
            "next_step_date",
            "next_step_priority",
        ]
        read_only_fields = ["created_at", "updated_at", "is_archived", "archived_at", "archived_by", "archive_reason"]

    def notes_visible(self, business):
        actor = getattr(self.context.get("request"), "user", None) or self.context.get("actor")
        # A list can contain different Business roles for the same user.
        cache = getattr(self, "_notes_visibility", None)
        if cache is None:
            cache = self._notes_visibility = {}
        if business.pk not in cache:
            cache[business.pk] = bool(actor and can_view_sensitive_field(actor, business, Resources.CLIENTS, "notes"))
        return cache[business.pk]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        visibility = getattr(self, "_notes_visibility", {})
        if instance.business_id not in visibility:
            self.notes_visible(instance.business)
        if not self._notes_visibility[instance.business_id]:
            data["notes"] = ""
        return data

    def validate(self, attrs):
        attrs = super().validate(attrs)
        business = attrs.get("business", getattr(self.instance, "business", None))
        if "notes" in attrs and business and not self.notes_visible(business):
            if attrs["notes"]:
                raise PermissionDenied("This field is not available to your role.")
            # Existing clients submit the masked empty value during ordinary edits.
            # It must not become a request to clear the stored private note.
            attrs.pop("notes")
        return attrs


class DuplicateCheckSerializer(serializers.Serializer):
    business = serializers.IntegerField()
    phone = serializers.CharField(required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_blank=True)
    whatsapp_id = serializers.CharField(required=False, allow_blank=True)
    telegram_id = serializers.CharField(required=False, allow_blank=True)
    instagram_id = serializers.CharField(required=False, allow_blank=True)
    exclude_client_id = serializers.IntegerField(required=False, allow_null=True)

    def validate_business(self, value):
        request = self.context["request"]
        business = accessible_businesses(request.user).filter(id=value).first()
        if business is None and getattr(request.user, "is_platform_user", False):
            from apps.businesses.models import Business

            business = Business.objects.filter(id=value).first()
        if business is None:
            raise serializers.ValidationError("Business is not available.")
        return business

    def duplicates(self):
        business = self.validated_data["business"]
        clients = find_duplicate_clients(
            business,
            phone=self.validated_data.get("phone"),
            email=self.validated_data.get("email"),
            whatsapp_id=self.validated_data.get("whatsapp_id"),
            telegram_id=self.validated_data.get("telegram_id"),
            instagram_id=self.validated_data.get("instagram_id"),
            exclude_client_id=self.validated_data.get("exclude_client_id"),
        )
        return duplicate_payload(
            clients,
            phone=self.validated_data.get("phone"),
            email=self.validated_data.get("email"),
            whatsapp_id=self.validated_data.get("whatsapp_id"),
            telegram_id=self.validated_data.get("telegram_id"),
            instagram_id=self.validated_data.get("instagram_id"),
        )


class ClientMergeSerializer(serializers.Serializer):
    duplicate_client_id = serializers.IntegerField()

    def validate_duplicate_client_id(self, value):
        target_client = self.context["target_client"]
        duplicate = Client.objects.filter(id=value, business=target_client.business).first()
        if duplicate is None:
            raise serializers.ValidationError("Duplicate client was not found in this business.")
        if duplicate.id == target_client.id:
            raise serializers.ValidationError("Cannot merge client into itself.")
        return duplicate

    def save(self, **kwargs):
        return merge_clients(
            target_client=self.context["target_client"],
            duplicate_client=self.validated_data["duplicate_client_id"],
            actor=self.context["request"].user,
        )


class ClientMergeDryRunSerializer(ClientMergeSerializer):
    def save(self, **kwargs):
        return merge_clients_dry_run(
            target_client=self.context["target_client"],
            duplicate_client=self.validated_data["duplicate_client_id"],
        )
