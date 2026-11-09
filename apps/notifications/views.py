from django.utils import timezone
from django.db.models import Case, DateTimeField, F, OuterRef, Q, Subquery, When
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.businesses.access import Actions, assert_can
from apps.core.viewsets import TenantModelViewSet
from apps.notifications.delivery import deliver_notification
from apps.notifications.models import Notification, NotificationPreference, NotificationRecipient
from apps.businesses.models import Business
from apps.notifications.announcement_api import AnnouncementActions, reject_state_payload
from apps.notifications.personal_selectors import can_manage_announcements, personal_business, personal_states
from apps.notifications.personal_services import read_personal_feed
from apps.notifications.serializers import NotificationPreferenceSerializer, NotificationSerializer


class NotificationViewSet(AnnouncementActions, TenantModelViewSet):
    queryset = Notification.objects.select_related("business", "client", "appointment", "recipient", "author")
    serializer_class = NotificationSerializer
    action_permission_map = {
        **TenantModelViewSet.action_permission_map,
        "mark_read": Actions.UPDATE,
        "mark_unread": Actions.UPDATE,
        "mark_all_read": Actions.UPDATE,
        "mark_sent": Actions.MANAGE,
        "cancel": Actions.MANAGE,
        "retry": Actions.MANAGE,
        "summary": Actions.VIEW,
    }

    def selected_personal_business(self):
        value = self.request.query_params.get("business")
        if value is None:
            ids = list(Business.objects.filter(
                Q(owner=self.request.user) | Q(members__user=self.request.user, members__is_active=True),
            ).distinct().values_list("pk", flat=True)[:2])
            if len(ids) != 1:
                raise ValidationError({"business": "Select one business."})
            value = ids[0]
        business_id = serializers.IntegerField(min_value=1).run_validation(value)
        return personal_business(actor=self.request.user, business_id=business_id)

    def get_serializer_context(self):
        return {**super().get_serializer_context(), "personal_feed": True}

    def get_queryset(self):
        business = self.selected_personal_business()
        states = personal_states(actor=self.request.user, business=business)
        external = super().get_queryset().filter(business=business).exclude(channel=Notification.Channels.SYSTEM)
        queryset = self.queryset.filter(Q(pk__in=external.values("pk")) | Q(pk__in=states.values("notification_id")))
        state = NotificationRecipient.objects.filter(notification_id=OuterRef("pk"), user=self.request.user)
        queryset = queryset.annotate(
            personal_read_at=Subquery(state.values("read_at")[:1]),
            personal_opened_at=Subquery(state.values("opened_at")[:1]),
            personal_acknowledged_at=Subquery(state.values("acknowledged_at")[:1]),
            effective_read_at=Case(When(channel=Notification.Channels.SYSTEM, then=Subquery(state.values("read_at")[:1])),
                                   default=F("read_at"), output_field=DateTimeField()),
        )
        status_filter = self.request.query_params.get("status")
        channel_filter = self.request.query_params.get("channel")
        category_filter = self.request.query_params.get("category")
        priority_filter = self.request.query_params.get("priority")
        unread_filter = self.request.query_params.get("unread")
        due_filter = self.request.query_params.get("due")
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        if channel_filter:
            queryset = queryset.filter(channel=channel_filter)
        if category_filter:
            queryset = queryset.filter(category=category_filter)
        if priority_filter:
            queryset = queryset.filter(priority=priority_filter)
        if unread_filter in {"1", "true", "yes"}:
            queryset = queryset.filter(effective_read_at__isnull=True)
        if unread_filter in {"0", "false", "no"}:
            queryset = queryset.filter(effective_read_at__isnull=False)
        if due_filter in {"1", "true", "yes"}:
            queryset = queryset.filter(status=Notification.Statuses.PENDING, send_at__lte=timezone.now())
        if self.request.query_params.get("surface") == "bell":
            queryset = queryset.filter(
                channel=Notification.Channels.SYSTEM, send_at__lte=timezone.now(),
            ).exclude(status=Notification.Statuses.CANCELLED)
        return queryset

    @action(detail=True, methods=["post"], url_path="mark-sent")
    def mark_sent(self, request, pk=None):
        notification = self.get_object()
        self.reject_announcement_delivery_action(notification)
        assert_can(request.user, notification.business, self.get_access_resource(), Actions.MANAGE, obj=notification)
        notification.status = Notification.Statuses.SENT
        notification.delivered_at = timezone.now()
        notification.locked_at = None
        notification.save(update_fields=["status", "delivered_at", "locked_at", "updated_at"])
        return Response(self.get_serializer(notification).data)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        notification = self.get_object()
        self.reject_announcement_delivery_action(notification)
        assert_can(request.user, notification.business, self.get_access_resource(), Actions.MANAGE, obj=notification)
        notification.status = Notification.Statuses.CANCELLED
        notification.locked_at = None
        notification.next_retry_at = None
        notification.save(update_fields=["status", "locked_at", "next_retry_at", "updated_at"])
        return Response(self.get_serializer(notification).data)

    @action(detail=True, methods=["post"])
    def retry(self, request, pk=None):
        notification = self.get_object()
        self.reject_announcement_delivery_action(notification)
        assert_can(request.user, notification.business, self.get_access_resource(), Actions.MANAGE, obj=notification)
        if notification.status != Notification.Statuses.FAILED:
            return Response({"detail": "Only failed notifications can be retried.", "notification": self.get_serializer(notification).data}, status=400)
        notification.status = Notification.Statuses.PENDING
        notification.send_at = timezone.now()
        notification.attempts = 0
        notification.next_retry_at = None
        notification.failed_at = None
        notification.last_error = ""
        notification.save(
            update_fields=["status", "send_at", "attempts", "next_retry_at", "failed_at", "last_error", "updated_at"]
        )
        result = deliver_notification(notification)
        notification.refresh_from_db()
        return Response({"result": result, "notification": self.get_serializer(notification).data})

    @staticmethod
    def reject_announcement_delivery_action(notification):
        if notification.kind == Notification.Kinds.ANNOUNCEMENT:
            raise ValidationError("Use the announcement revoke action; published content is immutable.")

    @action(detail=True, methods=["post"], url_path="mark-read")
    def mark_read(self, request, pk=None):
        notification = self.get_object()
        if notification.channel == Notification.Channels.SYSTEM:
            return self.personal_state_response(request, pk, "read")
        assert_can(request.user, notification.business, self.get_access_resource(), Actions.UPDATE, obj=notification)
        notification.mark_read()
        return Response(NotificationSerializer(notification, context={"request": request}).data)

    @action(detail=True, methods=["post"], url_path="mark-unread")
    def mark_unread(self, request, pk=None):
        notification = self.get_object()
        if notification.channel == Notification.Channels.SYSTEM:
            return self.personal_state_response(request, pk, "unread")
        assert_can(request.user, notification.business, self.get_access_resource(), Actions.UPDATE, obj=notification)
        notification.mark_unread()
        return Response(NotificationSerializer(notification, context={"request": request}).data)

    @action(detail=False, methods=["post"], url_path="mark-all-read")
    def mark_all_read(self, request):
        reject_state_payload(request)
        updated = read_personal_feed(actor=request.user, business=self.selected_personal_business())
        return Response({"updated": updated})

    @action(detail=False, methods=["get"])
    def summary(self, request):
        queryset = self.get_queryset()
        now = timezone.now()
        unread = queryset.filter(effective_read_at__isnull=True)
        return Response(
            {
                "pending": queryset.filter(status=Notification.Statuses.PENDING).count(),
                "sending": queryset.filter(status=Notification.Statuses.SENDING).count(),
                "retry_scheduled": queryset.filter(status=Notification.Statuses.RETRY_SCHEDULED).count(),
                "failed": queryset.filter(status=Notification.Statuses.FAILED).count(),
                "due": queryset.filter(status=Notification.Statuses.PENDING, send_at__lte=now).count(),
                "unread": unread.count(),
                "can_manage_announcements": can_manage_announcements(actor=request.user, business=self.selected_personal_business()),
                "urgent": unread.filter(priority=Notification.Priorities.URGENT).count(),
                "by_category": {
                    category: unread.filter(category=category).count()
                    for category in Notification.Categories.values
                },
            }
        )

    def destroy(self, request, *args, **kwargs):
        if self.get_object().channel == Notification.Channels.SYSTEM:
            raise ValidationError("Internal notification history cannot be deleted. Revoke announcements instead.")
        return super().destroy(request, *args, **kwargs)


class NotificationPreferenceViewSet(TenantModelViewSet):
    queryset = NotificationPreference.objects.select_related("business", "user")
    serializer_class = NotificationPreferenceSerializer
    access_resource = "notifications"
    action_permission_map = {
        **TenantModelViewSet.action_permission_map,
        "create": Actions.UPDATE,
        "update": Actions.UPDATE,
        "partial_update": Actions.UPDATE,
        "destroy": Actions.UPDATE,
    }

    def get_queryset(self):
        queryset = super().get_queryset()
        if "business" in self.request.query_params:
            from rest_framework.fields import IntegerField

            queryset = queryset.filter(business_id=IntegerField(min_value=1).run_validation(self.request.query_params["business"]))
        user_filter = self.request.query_params.get("user")
        category_filter = self.request.query_params.get("category")
        if user_filter == "me":
            queryset = queryset.filter(user=self.request.user)
        elif user_filter:
            queryset = queryset.filter(user_id=user_filter)
        if category_filter:
            queryset = queryset.filter(category=category_filter)
        return queryset
