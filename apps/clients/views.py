from apps.core.custom_field_filters import filter_custom_field
from django.core.paginator import Paginator
from django.db import transaction
from django.utils.functional import cached_property
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination

from apps.activities.taxonomy import ActivityEvents
from apps.businesses.access import Actions, assert_can
from apps.clients.lifecycle import archive_client
from apps.clients.models import Client
from apps.clients.selectors import build_client_facets, build_client_summary, client_queryset_for_request
from apps.clients.serializers import ClientMergeDryRunSerializer, ClientMergeSerializer, ClientSerializer, DuplicateCheckSerializer
from apps.core.audit import write_audit_log
from apps.core.crm_cards import client_crm_card
from apps.core.models import AuditLog
from apps.core.viewsets import TenantModelViewSet


class ClientPaginator(Paginator):
    @cached_property
    def count(self):
        # List annotations enrich displayed rows; they are not needed to count
        # distinct clients. Keep all scope/filter predicates in the query.
        return self.object_list.order_by().values("pk").count()


class ClientPagination(PageNumberPagination):
    django_paginator_class = ClientPaginator
    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 100

    def paginate_queryset(self, queryset, request, view=None):
        identifiers = super().paginate_queryset(queryset.values_list("pk", flat=True), request, view)
        if identifiers is None:
            return None
        # Select the scoped page before evaluating its display-only subqueries.
        rows = {row.pk: row for row in queryset.filter(pk__in=identifiers)}
        return [rows[pk] for pk in identifiers if pk in rows]


class ClientViewSet(TenantModelViewSet):
    queryset = Client.objects.select_related("business")
    serializer_class = ClientSerializer
    pagination_class = ClientPagination
    action_permission_map = {
        **TenantModelViewSet.action_permission_map,
        "archive": Actions.DELETE,
        "restore": Actions.DELETE,
        "merge": Actions.DELETE,
        "merge_dry_run": Actions.DELETE,
        "check_duplicates": Actions.CREATE,
    }

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset(apply_quick_filter=False))
        summary = build_client_summary(queryset, user=request.user)
        response = super().list(request, *args, **kwargs)
        if isinstance(response.data, dict):
            response.data["summary"] = {
                "total": summary["total"],
                "active": summary["active"],
                "no_reply": summary["no_reply"],
                "repeat": summary["repeat"],
                "new": summary["new"],
                "vip": summary["vip"],
                "mine": summary["mine"],
            }
            response.data["facets"] = build_client_facets(queryset)
        return response

    def get_queryset(self, apply_quick_filter=True):
        queryset = super().get_queryset()
        if self.action == "crm_card":
            # The card builds its own scoped annotations after resolving the parent.
            return queryset
        if self.action == "list":
            queryset = filter_custom_field(queryset, actor=self.request.user, entity_type="client", params=self.request.query_params)
        client_ids = self.parse_query_id_list("client_ids")
        return client_queryset_for_request(queryset, self.request, client_ids=client_ids, apply_quick_filter=apply_quick_filter)

    @action(detail=True, methods=["get"], url_path="crm-card")
    def crm_card(self, request, pk=None):
        client = self.get_object()
        return Response(client_crm_card(client, actor=request.user))

    @action(detail=True, methods=["post"])
    def archive(self, request, pk=None):
        client = self.get_object()
        client = archive_client(request=request, client=client, reason=request.data.get("reason", ""))
        return Response(self.get_serializer(client).data)

    def destroy(self, request, *args, **kwargs):
        if request.query_params.get("hard_delete") == "true":
            return super().destroy(request, *args, **kwargs)
        archive_client(request=request, client=self.get_object(), reason=request.data.get("reason", ""))
        return Response(status=204)

    @action(detail=False, methods=["post"], url_path="check-duplicates")
    def check_duplicates(self, request):
        serializer = DuplicateCheckSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        assert_can(request.user, serializer.validated_data["business"], self.get_access_resource(), Actions.CREATE)
        return Response({"duplicates": serializer.duplicates()})

    @action(detail=True, methods=["post"])
    @transaction.atomic
    def merge(self, request, pk=None):
        # Keep the domain transfer and mandatory request audit in one commit.
        target_client = self.get_object()
        assert_can(request.user, target_client.business, self.get_access_resource(), Actions.DELETE, obj=target_client)
        serializer = ClientMergeSerializer(data=request.data, context={"request": request, "target_client": target_client})
        serializer.is_valid(raise_exception=True)
        result = serializer.save()
        write_audit_log(
            request,
            AuditLog.Actions.UPDATE,
            target_client,
            metadata={
                "kind": "merge",
                "event_type": ActivityEvents.CLIENT_MERGED,
                "merge": result,
                "merge_log_id": result.get("merge_log_id"),
                "duplicate_client_id": result.get("deleted_duplicate", {}).get("id"),
            },
        )
        return Response(result)

    @action(detail=True, methods=["post"], url_path="merge-dry-run")
    def merge_dry_run(self, request, pk=None):
        target_client = self.get_object()
        assert_can(request.user, target_client.business, self.get_access_resource(), Actions.DELETE, obj=target_client)
        serializer = ClientMergeDryRunSerializer(data=request.data, context={"request": request, "target_client": target_client})
        serializer.is_valid(raise_exception=True)
        return Response(serializer.save())
