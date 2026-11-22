from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .encounter_views import EncounterReadSerializer, EncounterScopeSerializer
from .tooth_reads import read_tooth_observation, read_tooth_snapshot, read_tooth_revision_history, read_tooth_surface_options
from .tooth_services import save_primary_tooth_observation


class ToothObservationSerializer(EncounterScopeSerializer):
    encounter_id = serializers.IntegerField(min_value=1)
    tooth = serializers.IntegerField(min_value=1)
    surface = serializers.CharField(required=False, allow_blank=True, max_length=32, trim_whitespace=False)
    surface_reference = serializers.CharField(required=False, allow_blank=True, max_length=200, trim_whitespace=False)
    expected_patient_revision = serializers.IntegerField(min_value=1)
    expected_encounter_revision = serializers.IntegerField(min_value=1)
    expected_tooth_revision = serializers.IntegerField(min_value=0)
    observation = serializers.CharField(max_length=32768, trim_whitespace=False)
    reason = serializers.CharField(required=False, allow_blank=True, max_length=2000, trim_whitespace=False)
    participation_id = serializers.IntegerField(required=False, min_value=1)


class ToothSnapshotSerializer(EncounterReadSerializer):
    as_of = serializers.DateTimeField(required=False)
    after_state_id = serializers.IntegerField(min_value=1, required=False)
    limit = serializers.IntegerField(min_value=1, max_value=50, required=False, default=50)


class ToothHistorySerializer(EncounterReadSerializer):
    tooth_state_id = serializers.IntegerField(min_value=1)
    before_revision = serializers.IntegerField(min_value=1, required=False)
    limit = serializers.IntegerField(min_value=1, max_value=50, required=False, default=20)


class ToothSurfaceOptionsSerializer(EncounterReadSerializer):
    tooth = serializers.IntegerField(min_value=1)


class ToothObservationViewSet(viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    lookup_value_regex = r"[0-9]+"
    http_method_names = ["get", "post", "head", "options"]

    def get_serializer_class(self):
        return {"create": ToothObservationSerializer, "snapshot": ToothSnapshotSerializer,
                "history": ToothHistorySerializer, "surface_options": ToothSurfaceOptionsSerializer}.get(self.action, EncounterReadSerializer)

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        response["Cache-Control"] = "no-store, private"
        response["Pragma"] = "no-cache"
        return response

    def create(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        history, replayed = save_primary_tooth_observation(actor=request.user,
            **serializer.validated_data, idempotency_key=request.headers.get("Idempotency-Key"))
        return Response({"history_id": history.pk, "tooth_state_id": history.tooth_state_id,
            "revision": history.revision, "replayed": replayed}, status=200 if replayed else 201)

    def retrieve(self, request, pk=None):
        serializer = self.get_serializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        return Response(read_tooth_observation(actor=request.user, history_id=int(pk), **serializer.validated_data))

    @action(detail=False, methods=["get"])
    def snapshot(self, request):
        serializer = self.get_serializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        return Response(read_tooth_snapshot(actor=request.user, **serializer.validated_data))

    @action(detail=False, methods=["get"])
    def history(self, request):
        serializer = self.get_serializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        return Response(read_tooth_revision_history(actor=request.user, **serializer.validated_data))

    @action(detail=False, methods=["get"], url_path="surface-options")
    def surface_options(self, request):
        serializer = self.get_serializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        return Response(read_tooth_surface_options(actor=request.user, **serializer.validated_data))
