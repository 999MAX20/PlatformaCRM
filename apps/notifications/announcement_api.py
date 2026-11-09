from django.conf import settings
from django.db.models import Count, Q
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.response import Response

from apps.notifications.announcements import assert_announcement_manager, publish_announcement, revoke_announcement
from apps.notifications.models import Notification
from apps.notifications.personal_services import change_personal_state


class AnnouncementInput(serializers.Serializer):
    text = serializers.CharField(max_length=4000, trim_whitespace=True)
    priority = serializers.ChoiceField(choices=Notification.Priorities.choices, default="normal")
    publication_key = serializers.UUIDField()

    def to_internal_value(self, data):
        extra = set(data) - set(self.fields)
        if extra:
            raise ValidationError({"fields": sorted(extra), "detail": "Unexpected announcement fields."})
        return super().to_internal_value(data)


class AnnouncementSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source="author.full_name", read_only=True, default="")
    recipient_count = serializers.IntegerField(read_only=True)
    opened_count = serializers.IntegerField(read_only=True)
    read_count = serializers.IntegerField(read_only=True)
    acknowledged_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Notification
        fields = ["id", "business", "text", "priority", "author_name", "created_at", "revoked_at",
                  "recipient_count", "opened_count", "read_count", "acknowledged_count"]


def announcement_rows(business):
    return Notification.objects.filter(business=business, kind=Notification.Kinds.ANNOUNCEMENT).annotate(
        recipient_count=Count("recipient_states"),
        opened_count=Count("recipient_states", filter=Q(recipient_states__opened_at__isnull=False)),
        read_count=Count("recipient_states", filter=Q(recipient_states__read_at__isnull=False)),
        acknowledged_count=Count("recipient_states", filter=Q(recipient_states__acknowledged_at__isnull=False)),
    ).select_related("author").order_by("-created_at", "-pk")


def reject_state_payload(request):
    if request.data:
        raise ValidationError("Personal state actions do not accept recipient or timestamp fields.")


class AnnouncementActions:
    @action(detail=False, methods=["get", "post"])
    def announcements(self, request):
        business = self.selected_personal_business()
        assert_announcement_manager(actor=request.user, business=business)
        if request.method == "POST":
            serializer = AnnouncementInput(data=request.data)
            serializer.is_valid(raise_exception=True)
            notification, created = publish_announcement(actor=request.user, business=business, **serializer.validated_data)
            row = announcement_rows(business).get(pk=notification.pk)
            return Response(AnnouncementSerializer(row).data, status=201 if created else 200)
        page = self.paginate_queryset(announcement_rows(business))
        response = self.get_paginated_response(AnnouncementSerializer(page, many=True).data)
        response.data["events_enabled"] = settings.NOTIFICATION_EVENTS_ENABLED
        return response

    @action(detail=True, methods=["get"], url_path="announcement-recipients")
    def announcement_recipients(self, request, pk=None):
        business = self.selected_personal_business()
        assert_announcement_manager(actor=request.user, business=business)
        notification = announcement_rows(business).filter(pk=pk).first()
        if notification is None:
            raise NotFound()
        states = notification.recipient_states.select_related("user").order_by("user__full_name", "pk")
        page = self.paginate_queryset(states)
        rows = [{"id": row.pk, "user": row.user_id, "name": row.user.full_name or row.user.email,
                 "received_at": row.received_at, "opened_at": row.opened_at, "read_at": row.read_at,
                 "acknowledged_at": row.acknowledged_at} for row in page]
        response = self.get_paginated_response(rows)
        response.data["announcement"] = AnnouncementSerializer(notification).data
        return response

    @action(detail=True, methods=["post"], url_path="revoke-announcement")
    def revoke_announcement(self, request, pk=None):
        reject_state_payload(request)
        business = self.selected_personal_business()
        notification = revoke_announcement(actor=request.user, business=business, notification_id=pk)
        return Response(AnnouncementSerializer(announcement_rows(business).get(pk=notification.pk)).data)

    @action(detail=True, methods=["post"], url_path="open")
    def open_notification(self, request, pk=None):
        return self.personal_state_response(request, pk, "open")

    @action(detail=True, methods=["post"], url_path="acknowledge")
    def acknowledge(self, request, pk=None):
        return self.personal_state_response(request, pk, "acknowledge")

    def personal_state_response(self, request, pk, state_action):
        reject_state_payload(request)
        business = self.selected_personal_business()
        state = change_personal_state(actor=request.user, business=business, notification_id=pk, action=state_action)
        context = self.get_serializer_context()
        context["recipient_state"] = state
        return Response(self.get_serializer(state.notification, context=context).data)
