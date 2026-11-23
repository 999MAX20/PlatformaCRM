from django.conf import settings
from django.shortcuts import get_object_or_404
from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from rest_framework.exceptions import NotFound
from apps.core.permissions import accessible_businesses
from apps.integrations import google_oauth
from apps.integrations.google_models import GoogleConnection


class StartInput(serializers.Serializer):
    business = serializers.IntegerField(min_value=1)
    provider = serializers.ChoiceField(choices=["google_sheets", "google_calendar"], default="google_sheets")


class CompleteInput(serializers.Serializer):
    code = serializers.CharField(max_length=4096, trim_whitespace=False)
    state = serializers.CharField(max_length=4096, trim_whitespace=False)


class GoogleOAuthView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        data = StartInput(data=request.query_params)
        data.is_valid(raise_exception=True)
        business = get_object_or_404(accessible_businesses(request.user), pk=data.validated_data["business"])
        google_oauth.assert_access(request.user, business)
        connection = GoogleConnection.objects.filter(business=business, actor=request.user,
            provider=data.validated_data["provider"]).first()
        result = google_oauth.status(connection) if connection else {"status": "disconnected", "id": None, "email": ""}
        if data.validated_data["provider"] == "google_calendar":
            result["enabled"] = settings.GOOGLE_CALENDAR_ENABLED
        response = Response(result)
        response["Cache-Control"] = "no-store"
        return response

    def post(self, request, operation):
        if operation == "start":
            data = StartInput(data=request.data)
            data.is_valid(raise_exception=True)
            business = get_object_or_404(accessible_businesses(request.user), pk=data.validated_data["business"])
            result = google_oauth.start(actor=request.user, business=business, provider=data.validated_data["provider"])
        elif operation == "complete":
            data = CompleteInput(data=request.data)
            data.is_valid(raise_exception=True)
            result = google_oauth.complete(actor=request.user, **data.validated_data)
        else:
            raise NotFound()
        response = Response(result)
        response["Cache-Control"] = "no-store"
        return response


def owned_connection(request, pk, *, provider="google_sheets"):
    connection = get_object_or_404(GoogleConnection.objects.select_related("business"), pk=pk, actor=request.user,
                                  business__in=accessible_businesses(request.user))
    if provider is not None and connection.provider != provider:
        raise NotFound()
    google_oauth.assert_access(request.user, connection.business)
    return connection


class GoogleDisconnectView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        return Response(google_oauth.disconnect(owned_connection(request, pk, provider=None), request.user))


class SheetInput(serializers.Serializer):
    file_id = serializers.RegexField(r"^[A-Za-z0-9_-]{10,255}$")


class SheetImportInput(SheetInput):
    sheet_id = serializers.IntegerField(min_value=0)
    request_key = serializers.UUIDField()


class SheetExportInput(serializers.Serializer):
    request_key = serializers.UUIDField()
    refresh = serializers.BooleanField(default=False)


class GoogleSheetsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk, operation):
        from apps.businesses.access import Actions
        from apps.integrations.google_sheets import assert_clients
        from apps.integrations.google_sheets_export import transfer_status
        from apps.integrations.google_models import GoogleSheetTransfer

        connection = owned_connection(request, pk)
        if operation != "exports":
            raise NotFound()
        assert_clients(connection, request.user, Actions.VIEW)
        response = Response([transfer_status(item) for item in GoogleSheetTransfer.objects.filter(
            connection=connection, kind="export").exclude(status="expired").order_by("-created_at")[:20]])
        response["Cache-Control"] = "no-store"
        return response

    def post(self, request, pk, operation):
        from apps.integrations import google_sheets
        from apps.core.serializers import ImportJobSerializer

        connection = owned_connection(request, pk)
        if operation == "metadata":
            data = SheetInput(data=request.data)
            data.is_valid(raise_exception=True)
            result = google_sheets.metadata(connection, request.user, **data.validated_data)
        elif operation == "import":
            data = SheetImportInput(data=request.data)
            data.is_valid(raise_exception=True)
            job = google_sheets.import_snapshot(connection, request.user, request=request, **data.validated_data)
            result = ImportJobSerializer(job, context={"request": request}).data
        elif operation == "export":
            from apps.integrations.google_sheets_export import export_clients
            data = SheetExportInput(data=request.data)
            data.is_valid(raise_exception=True)
            result = export_clients(connection, request.user, **data.validated_data)
        elif operation == "picker":
            from django.conf import settings
            from apps.businesses.access import Actions
            from rest_framework.exceptions import ValidationError
            google_sheets.assert_clients(connection, request.user, Actions.CREATE)
            if not settings.GOOGLE_PICKER_API_KEY or not settings.GOOGLE_CLOUD_PROJECT_NUMBER:
                raise ValidationError("Google file selection is not configured.")
            result = {"access_token": google_oauth.access_token(connection, request.user),
                      "api_key": settings.GOOGLE_PICKER_API_KEY, "app_id": settings.GOOGLE_CLOUD_PROJECT_NUMBER}
        else:
            raise NotFound()
        response = Response(result)
        response["Cache-Control"] = "no-store"
        return response
