from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.businesses.access import Actions, Resources, assert_can, scope_queryset
from .models import Branch, SpecialistAbsence
from .staff_lifecycle import add_absence, remove_absence, retire_specialist, pending_work, future_appointments


class AbsenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = SpecialistAbsence
        fields = ["id", "branch", "starts_on", "ends_on", "reason"]


class AbsenceInput(serializers.Serializer):
    starts_on = serializers.DateField()
    ends_on = serializers.DateField()
    branch = serializers.PrimaryKeyRelatedField(queryset=Branch.objects.all(), allow_null=True, required=False)
    reason = serializers.ChoiceField(choices=["unavailable", "vacation", "sick"], default="unavailable")


class ResourceLifecycleMixin:
    @action(detail=True, methods=["get", "post"])
    def absences(self, request, pk=None):
        resource = self.get_object()
        if request.method == "POST":
            data = AbsenceInput(data=request.data)
            data.is_valid(raise_exception=True)
            absence = add_absence(resource=resource, actor=request.user, **data.validated_data)
            return Response(AbsenceSerializer(absence).data, status=201)
        assert_can(request.user, resource.business, Resources.SETTINGS, Actions.VIEW)
        return Response(AbsenceSerializer(resource.absences.all(), many=True).data)

    @action(detail=True, methods=["post"], url_path="remove-absence")
    def remove_absence(self, request, pk=None):
        resource = self.get_object()
        absence_id = serializers.IntegerField(min_value=1).run_validation(request.data.get("absence"))
        remove_absence(resource=resource, actor=request.user, absence_id=absence_id)
        return Response({"removed": True})

    @action(detail=True, methods=["get"], url_path="retirement-preview")
    def retirement_preview(self, request, pk=None):
        resource = self.get_object()
        assert_can(request.user, resource.business, Resources.SETTINGS, Actions.VIEW)
        from apps.scheduling.serializers import AppointmentSerializer
        visits = scope_queryset(future_appointments(resource), request.user, resource.business, Resources.APPOINTMENTS)
        return Response({"pending": pending_work(resource),
                         "appointments": AppointmentSerializer(visits[:100], many=True, context={"request": request}).data,
                         "appointments_count": visits.count(), "appointments_truncated": visits.count() > 100})

    @action(detail=True, methods=["post"])
    def retire(self, request, pk=None):
        resource = self.get_object()
        disable_access = serializers.BooleanField().run_validation(request.data.get("disable_access", False))
        resource = retire_specialist(resource=resource, actor=request.user, disable_access=disable_access)
        return Response(self.get_serializer(resource).data)
