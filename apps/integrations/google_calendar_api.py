from django.conf import settings
from django.db import transaction
from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.integrations.google_api import owned_connection
from apps.integrations import google_calendar_service as service, google_oauth
from apps.integrations.google_calendar_access import assert_connection
from apps.integrations.google_calendar_models import GoogleCalendarBinding
from apps.scheduling.models import Resource


class BindInput(serializers.Serializer):
    resource_id = serializers.IntegerField(min_value=1)
    calendar_id = serializers.CharField(max_length=1024)
    confirm_data_export = serializers.BooleanField()

    def validate_confirm_data_export(self, value):
        if not value:
            raise serializers.ValidationError("Confirm sharing appointment times, client names and service names with Google.")
        return value


class BindingInput(serializers.Serializer):
    binding_id = serializers.UUIDField()


class EnableInput(BindingInput):
    enabled = serializers.BooleanField()


class GoogleCalendarView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk, operation):
        connection = owned_connection(request, pk, provider="google_calendar")
        assert_connection(connection, request.user)
        if operation == "bindings":
            result = {"enabled": settings.GOOGLE_CALENDAR_ENABLED,
                "bindings": [service.binding_status(item) for item in connection.calendar_bindings.select_related("resource").order_by("created_at")],
                "specialists": list(Resource.objects.filter(business=connection.business, is_active=True,
                    retired_at__isnull=True, resource_type="staff").order_by("name").values("id", "name"))}
        elif operation == "calendars":
            if not settings.GOOGLE_CALENDAR_ENABLED:
                raise ValidationError("Google Calendar synchronization is not enabled.")
            result = service.list_calendars(connection, request.user)
        else:
            raise NotFound()
        response = Response(result)
        response["Cache-Control"] = "no-store"
        return response

    def post(self, request, pk, operation):
        connection = owned_connection(request, pk, provider="google_calendar")
        assert_connection(connection, request.user)
        if not settings.GOOGLE_CALENDAR_ENABLED and operation != "enabled":
            raise ValidationError("Google Calendar synchronization is not enabled.")
        if operation == "bind":
            data = BindInput(data=request.data)
            data.is_valid(raise_exception=True)
            values = dict(data.validated_data)
            values.pop("confirm_data_export")
            result = service.bind(connection, request.user, **values)
        elif operation == "enabled":
            data = EnableInput(data=request.data)
            data.is_valid(raise_exception=True)
            if data.validated_data["enabled"] and not settings.GOOGLE_CALENDAR_ENABLED:
                raise ValidationError("Google Calendar synchronization is not enabled.")
            result = service.set_enabled(connection, request.user, **data.validated_data)
        elif operation == "sync":
            data = BindingInput(data=request.data)
            data.is_valid(raise_exception=True)
            with transaction.atomic():
                binding = GoogleCalendarBinding.objects.select_for_update().filter(
                    pk=data.validated_data["binding_id"], connection=connection, enabled=True).first()
                if binding is None:
                    raise NotFound()
                if connection.status != "connected":
                    raise ValidationError("Reconnect Google before retrying synchronization.")
                binding.next_sync_at = timezone.now()
                binding.save(update_fields=["next_sync_at"])
                google_oauth.audit(connection, request.user, "google_calendar_sync_requested")
                result = {"queued": True}
        else:
            raise NotFound()
        response = Response(result)
        response["Cache-Control"] = "no-store"
        return response
