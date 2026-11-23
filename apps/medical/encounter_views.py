from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .appointment_context import read_appointment_clinical_context
from .encounter_reads import read_clinical_workspace, read_encounter_for_treating_clinician, read_encounter_history
from .encounter_services import open_primary_encounter, save_primary_encounter_draft
from .serializers import StrictSerializer


class EncounterScopeSerializer(StrictSerializer):
    business_id = serializers.IntegerField(min_value=1)
    patient_id = serializers.IntegerField(min_value=1)


class AppointmentClinicalContextSerializer(StrictSerializer):
    business_id = serializers.IntegerField(min_value=1)
    appointment_id = serializers.IntegerField(min_value=1)


class EncounterOpenSerializer(EncounterScopeSerializer):
    record_id = serializers.IntegerField(min_value=1)
    appointment_id = serializers.IntegerField(min_value=1)
    expected_patient_revision = serializers.IntegerField(min_value=1)
    expected_appointment_updated_at = serializers.DateTimeField()
    content = serializers.DictField(required=False)


class EncounterDraftSerializer(EncounterScopeSerializer):
    expected_revision = serializers.IntegerField(min_value=1)
    content = serializers.DictField()
    reason = serializers.CharField(required=False, allow_blank=True, max_length=2000, trim_whitespace=False)
    participation_id = serializers.IntegerField(min_value=1, required=False)


class EncounterReadSerializer(EncounterScopeSerializer):
    appointment_id = serializers.IntegerField(min_value=1, required=False)
    participation_id = serializers.IntegerField(min_value=1, required=False)


class ClinicalWorkspaceSerializer(EncounterReadSerializer):
    before_id = serializers.IntegerField(min_value=1, required=False)
    limit = serializers.IntegerField(min_value=1, max_value=50, required=False, default=20)


class ClinicalRepresentativesSerializer(EncounterReadSerializer):
    offset = serializers.IntegerField(min_value=0, required=False, default=0)
    limit = serializers.IntegerField(min_value=1, max_value=50, required=False, default=25)


class ClinicalHistoryWorkspaceSerializer(ClinicalWorkspaceSerializer):
    branch_id = serializers.IntegerField(min_value=1, required=False)
    author_id = serializers.IntegerField(min_value=1, required=False)
    state = serializers.ChoiceField(choices=("draft", "finalized"), required=False)
    date_from = serializers.DateField(required=False)
    date_to = serializers.DateField(required=False)


class ClientClinicalAppointmentsSerializer(StrictSerializer):
    business_id = serializers.IntegerField(min_value=1)
    branch_id = serializers.IntegerField(min_value=1)
    client_id = serializers.IntegerField(min_value=1)
    before_id = serializers.IntegerField(min_value=1, required=False)
    limit = serializers.IntegerField(min_value=1, max_value=50, required=False, default=20)


class EncounterHistorySerializer(EncounterReadSerializer):
    before_revision = serializers.IntegerField(min_value=1, required=False)
    limit = serializers.IntegerField(min_value=1, max_value=50, required=False, default=20)


class ClinicalVisitStepsSerializer(ClinicalWorkspaceSerializer):
    encounter_id = serializers.IntegerField(min_value=1)
    correction_access_id = serializers.IntegerField(min_value=1, required=False)


class ClinicalPatientPlansSerializer(ClinicalWorkspaceSerializer):
    archived = serializers.BooleanField(required=False, default=False)


class ToothPlanSerializer(ClinicalWorkspaceSerializer):
    tooth = serializers.IntegerField(min_value=1)
    as_of = serializers.DateTimeField(required=False)


class ClinicalPlanBookingSerializer(EncounterScopeSerializer):
    expected_revision = serializers.IntegerField(min_value=1)
    step_id = serializers.CharField(max_length=36)
    service_id = serializers.IntegerField(min_value=1)
    resource_id = serializers.IntegerField(min_value=1)
    branch_id = serializers.IntegerField(min_value=1)
    responsible_user_id = serializers.IntegerField(min_value=1, required=False)
    expected_plan_revision = serializers.IntegerField(min_value=1, required=False)
    participation_id = serializers.IntegerField(min_value=1, required=False)
    start_at = serializers.DateTimeField()
    expected_price = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=0, allow_null=True)
    expected_duration_minutes = serializers.IntegerField(min_value=1)
    confirmed = serializers.BooleanField()
    notes = serializers.CharField(max_length=10000, allow_blank=True, required=False, trim_whitespace=False)


class MedicalEncounterViewSet(viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    lookup_value_regex = r"[0-9]+"
    serializer_class = EncounterScopeSerializer
    http_method_names = ["get", "post", "head", "options"]

    def get_serializer_class(self):
        return {"create": EncounterOpenSerializer, "draft": EncounterDraftSerializer,
                "version": EncounterReadSerializer, "workspace": ClinicalHistoryWorkspaceSerializer,
                "overview": EncounterReadSerializer,
                "representatives": ClinicalRepresentativesSerializer,
                "client_appointments": ClientClinicalAppointmentsSerializer,
                "revisions": EncounterHistorySerializer,
                "visit_steps": ClinicalVisitStepsSerializer,
                "patient_plans": ClinicalPatientPlansSerializer,
                "tooth_plan": ToothPlanSerializer,
                "book_plan_step": ClinicalPlanBookingSerializer,
                "appointment_context": AppointmentClinicalContextSerializer}.get(self.action, EncounterScopeSerializer)

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        response["Cache-Control"] = "no-store, private"
        response["Pragma"] = "no-cache"
        return response

    def _command(self, request, service, *, encounter_id=None, created=False):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        identity = {"encounter_id": encounter_id} if encounter_id is not None else {}
        version, replayed = service(actor=request.user, **serializer.validated_data, **identity,
            idempotency_key=request.headers.get("Idempotency-Key"))
        return Response({"id": version.encounter_id, "version_id": version.pk,
                         "revision": version.revision, "replayed": replayed},
                        status=201 if created and not replayed else 200)

    def create(self, request):
        return self._command(request, open_primary_encounter, created=True)

    @action(detail=True, methods=["post"], url_path="book-plan-step")
    def book_plan_step(self, request, pk=None):
        from .clinical_plan_booking import book_clinical_plan_step
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = book_clinical_plan_step(actor=request.user, encounter_id=int(pk), **serializer.validated_data,
            idempotency_key=request.headers.get("Idempotency-Key"))
        return Response(result, status=200 if result["replayed"] else 201)

    @action(detail=False, methods=["get"], url_path="representatives")
    def representatives(self, request):
        from .representative_selectors import list_clinical_representatives
        serializer = self.get_serializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        return Response(list_clinical_representatives(actor=request.user, **serializer.validated_data))

    @action(detail=False, methods=["get"], url_path="visit-steps")
    def visit_steps(self, request):
        from .clinical_plan_reads import list_clinical_visit_steps
        serializer = self.get_serializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        return Response(list_clinical_visit_steps(actor=request.user, **serializer.validated_data))

    @action(detail=False, methods=["get"], url_path="patient-plans")
    def patient_plans(self, request):
        from .clinical_plan_reads import list_patient_visit_plans
        serializer = self.get_serializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        return Response(list_patient_visit_plans(actor=request.user, **serializer.validated_data))

    @action(detail=False, methods=["get"], url_path="tooth-plan")
    def tooth_plan(self, request):
        from .clinical_plan_teeth import read_tooth_plan_steps
        serializer = self.get_serializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        return Response(read_tooth_plan_steps(actor=request.user, **serializer.validated_data))

    @action(detail=False, methods=["get"], url_path="appointment-context")
    def appointment_context(self, request):
        serializer = self.get_serializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        return Response(read_appointment_clinical_context(actor=request.user, **serializer.validated_data))

    @action(detail=False, methods=["get"])
    def overview(self, request):
        from .clinical_overview import read_clinical_overview
        serializer = self.get_serializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        return Response(read_clinical_overview(actor=request.user, **serializer.validated_data))

    @action(detail=False, methods=["get"], url_path="client-appointments")
    def client_appointments(self, request):
        from .client_clinical_appointments import list_client_clinical_appointments
        serializer = self.get_serializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        return Response(list_client_clinical_appointments(actor=request.user, **serializer.validated_data))

    @action(detail=False, methods=["get"])
    def workspace(self, request):
        serializer = self.get_serializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        return Response(read_clinical_workspace(actor=request.user, **serializer.validated_data))

    @action(detail=True, methods=["post"])
    def draft(self, request, pk=None):
        return self._command(request, save_primary_encounter_draft, encounter_id=int(pk))

    @action(detail=True, methods=["get"])
    def revisions(self, request, pk=None):
        serializer = self.get_serializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        return Response(read_encounter_history(actor=request.user, encounter_id=int(pk), **serializer.validated_data))

    @action(detail=False, methods=["get"], url_path=r"versions/(?P<version_id>[0-9]+)")
    def version(self, request, version_id=None):
        serializer = self.get_serializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        return Response(read_encounter_for_treating_clinician(actor=request.user,
            version_id=int(version_id), **serializer.validated_data))
