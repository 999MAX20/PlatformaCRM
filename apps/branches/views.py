from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from apps.businesses.access import Actions, Resources, assert_can
from apps.businesses.models import BusinessMember
from apps.core.viewsets import TenantModelViewSet
from apps.core.permissions import accessible_businesses
from .access import branch_grant_capabilities
from .models import Branch
from .serializers import BranchSerializer, BranchGrantSerializer, BranchGrantTargetSerializer
from .services import set_branch_access
from .config_views import BranchConfigurationMixin


class BranchViewSet(BranchConfigurationMixin, TenantModelViewSet):
    queryset = Branch.objects.select_related("business")
    serializer_class = BranchSerializer
    access_resource = Resources.APPOINTMENTS
    http_method_names = ["get", "post", "patch", "head", "options"]
    pagination_class = None

    def get_access_resource(self):
        return Resources.APPOINTMENTS if self.action in {"list", "retrieve", "catalog"} else Resources.SETTINGS

    def get_access_action(self):
        return Actions.VIEW if self.action in {"list", "retrieve", "catalog", "configuration"} else Actions.UPDATE

    def get_queryset(self):
        from .setup_state import with_setup_state
        queryset = super().get_queryset()
        if self.request.query_params.get("business"):
            queryset = queryset.filter(business_id=self.request.query_params["business"])
        return with_setup_state(queryset)

    def perform_create(self, serializer):
        serializer.save()

    def perform_update(self, serializer):
        serializer.save()

    @action(detail=False, methods=["get", "post"], url_path="member-access")
    def member_access(self, request):
        if request.method == "GET":
            query = BranchGrantTargetSerializer(data=request.query_params)
            query.is_valid(raise_exception=True)
            member = get_object_or_404(BusinessMember.objects.select_related("business").filter(
                business__in=accessible_businesses(request.user)), pk=query.validated_data["member"])
            return Response(branch_grant_capabilities(actor=request.user, member=member))
        data = BranchGrantSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        member = BusinessMember.objects.select_related("business").filter(pk=data.validated_data["member"]).first()
        if member is None:
            raise ValidationError({"member": "Member is not available."})
        assert_can(request.user, member.business, Resources.TEAM, Actions.MANAGE)
        grant = set_branch_access(member=member, actor=request.user,
                                  branch_ids=data.validated_data["branch_ids"], all_branches=data.validated_data["all_branches"])
        return Response({"member": member.pk, "all_branches": grant.all_branches, "branch_ids": list(grant.branches.values_list("pk", flat=True))})

    @action(detail=True, methods=["post"])
    def state(self, request, pk=None):
        from .staff_lifecycle import change_branch_state
        branch = change_branch_state(branch=self.get_object(), actor=request.user, state=request.data.get("state"))
        return Response(self.get_serializer(branch).data)
