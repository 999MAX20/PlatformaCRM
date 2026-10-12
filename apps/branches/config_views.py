from django.db.models import Q
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.businesses.access import Actions, Resources, assert_can
from .configuration import save_offer, save_assignment, save_schedule_day, save_travel_time
from .config_serializers import (OfferSerializer, AssignmentSerializer, DaySerializer, TravelSerializer,
                                 OfferInput, AssignmentInput, DayInput, TravelInput)
from .models import BranchTravelTime, SpecialistAbsence


class BranchConfigurationMixin:
    @action(detail=True, methods=["get"])
    def configuration(self, request, pk=None):
        branch = self.get_object()
        assert_can(request.user, branch.business, Resources.SETTINGS, Actions.VIEW)
        return Response({
            "offers": OfferSerializer(branch.service_offers.select_related("service"), many=True).data,
            "assignments": AssignmentSerializer(branch.specialist_assignments.select_related("resource").prefetch_related("services"), many=True).data,
            "days": DaySerializer(branch.schedule_days.all(), many=True).data,
            "travel": TravelSerializer(BranchTravelTime.objects.filter(business=branch.business)
                                       .filter(Q(from_branch=branch) | Q(to_branch=branch)), many=True).data,
        })

    @action(detail=True, methods=["get"])
    def catalog(self, request, pk=None):
        branch = self.get_object()
        offers = branch.service_offers.filter(is_active=True, service__is_active=True, service__is_archived=False).select_related("service")
        assignments = branch.specialist_assignments.filter(is_active=True, resource__is_active=True, resource__retired_at__isnull=True).select_related("resource").prefetch_related("services")
        if not branch.is_active or branch.archived_at:
            offers, assignments = offers.none(), assignments.none()
        return Response({"offers": OfferSerializer(offers, many=True).data,
                         "assignments": AssignmentSerializer(assignments, many=True).data,
                         "days": DaySerializer(branch.schedule_days.all(), many=True).data,
                         "absences": list(SpecialistAbsence.objects.filter(business=branch.business,
                             resource_id__in=assignments.values("resource_id")).filter(Q(branch=branch) | Q(branch__isnull=True))
                             .values("resource_id", "starts_on", "ends_on"))})

    @action(detail=True, methods=["post"])
    def offers(self, request, pk=None):
        branch = self.get_object()
        data = OfferInput(data=request.data)
        data.is_valid(raise_exception=True)
        values = dict(data.validated_data)
        values["service_id"] = values.pop("service")
        return Response(OfferSerializer(save_offer(branch=branch, actor=request.user, **values)).data)

    @action(detail=True, methods=["post"])
    def assignments(self, request, pk=None):
        branch = self.get_object()
        data = AssignmentInput(data=request.data)
        data.is_valid(raise_exception=True)
        values = dict(data.validated_data)
        values["resource_id"] = values.pop("resource")
        return Response(AssignmentSerializer(save_assignment(branch=branch, actor=request.user, **values)).data)

    @action(detail=True, methods=["post"])
    def schedule(self, request, pk=None):
        branch = self.get_object()
        data = DayInput(data=request.data)
        data.is_valid(raise_exception=True)
        values = dict(data.validated_data)
        values["resource_id"] = values.pop("resource", None)
        day = save_schedule_day(branch=branch, actor=request.user, **values)
        return Response(DaySerializer(day).data if day else {"removed": True})

    @action(detail=True, methods=["post"])
    def travel(self, request, pk=None):
        branch = self.get_object()
        data = TravelInput(data=request.data)
        data.is_valid(raise_exception=True)
        return Response(TravelSerializer(save_travel_time(branch=branch, actor=request.user,
            other_id=data.validated_data["other_branch"], minutes=data.validated_data["minutes"])).data)
