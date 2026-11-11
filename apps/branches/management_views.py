from django.shortcuts import get_object_or_404
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet
from rest_framework.exceptions import ValidationError

from apps.businesses.access import Actions, Resources, assert_can
from apps.businesses.capabilities import assert_resource_enabled
from apps.core.permissions import IsTenantMember, accessible_businesses
from . import management_commands as commands
from .management_lifecycle import change_state
from .management_selectors import management_catalog
from .management_serializers import (ManagementBranchInput, ManagementLifecycleInput,
    ManagementRoomInput, ManagementServiceInput, ManagementSpecialistInput)


class ManagementViewSet(ViewSet):
    permission_classes = [IsTenantMember]

    def business(self, identifier, action):
        if not str(identifier).isdecimal() or int(identifier) < 1:
            raise ValidationError({"business": "Select a business."})
        business = get_object_or_404(accessible_businesses(self.request.user), pk=identifier)
        assert_resource_enabled(business, Resources.SETTINGS)
        assert_can(self.request.user, business, Resources.SETTINGS, action)
        return business

    def list(self, request):
        business = self.business(request.query_params.get("business"), Actions.VIEW)
        return Response(management_catalog(business=business, request=request))

    def save(self, request, serializer_class, command):
        serializer = serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        business = self.business(serializer.validated_data["business"], Actions.UPDATE)
        item = command(business=business, request=request, values=serializer.validated_data)
        return Response({"id": item.pk}, status=200 if serializer.validated_data.get("id") else 201)

    @action(detail=False, methods=["post"])
    def services(self, request):
        return self.save(request, ManagementServiceInput, commands.save_service)

    @action(detail=False, methods=["post"])
    def staff(self, request):
        return self.save(request, ManagementSpecialistInput, commands.save_specialist)

    @action(detail=False, methods=["post"])
    def rooms(self, request):
        return self.save(request, ManagementRoomInput, commands.save_room)

    @action(detail=False, methods=["post"])
    def branches(self, request):
        return self.save(request, ManagementBranchInput, commands.save_branch)

    @action(detail=False, methods=["post"])
    def lifecycle(self, request):
        serializer = ManagementLifecycleInput(data=request.data)
        serializer.is_valid(raise_exception=True)
        values = serializer.validated_data
        business = self.business(values["business"], Actions.UPDATE)
        change_state(business=business, request=request, kind=values["kind"], identifier=values["id"], operation=values["operation"])
        return Response({"id": values["id"], "operation": values["operation"]})
