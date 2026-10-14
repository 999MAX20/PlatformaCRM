from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.support import serializers as inputs
from apps.support import services
from apps.support.access import active_platform_users, assert_platform_actor, get_case, get_case_business
from apps.support.messages import append_message, mark_read
from apps.support.selectors import case_projection, filtered_cases


class SupportView(APIView):
    permission_classes = [IsAuthenticated]
    platform = False

    def validate_input(self, serializer, data):
        parsed = serializer(data=data, context={"platform": self.platform})
        parsed.is_valid(raise_exception=True)
        return parsed.validated_data

    def scope(self, request, serializer=inputs.CaseContext):
        if self.platform:
            assert_platform_actor(request.user)
        params = self.validate_input(serializer, request.query_params)
        if params.get("business"):
            get_case_business(request.user, params["business"], platform=self.platform)
        return params

    def case(self, request, pk, params):
        case = get_case(request.user, pk, platform=self.platform)
        if params.get("business") and case.business_id != params["business"]:
            raise Http404
        return case

    def representation(self, request, pk):
        case = get_object_or_404(case_projection(request.user, platform=self.platform), pk=pk)
        return inputs.CaseSerializer(case, context={"platform": self.platform}).data

    def page(self, request, rows, params, serializer):
        paginator = PageNumberPagination()
        paginator.page_size = params["page_size"]
        page = paginator.paginate_queryset(rows, request)
        return paginator.get_paginated_response(serializer(page, many=True, context={"platform": self.platform}).data)


class CaseListView(SupportView):
    def get(self, request):
        params = self.scope(request, inputs.ListInput)
        return self.page(request, filtered_cases(request.user, params, platform=self.platform), params, inputs.CaseSerializer)

    def post(self, request):
        params = self.scope(request)
        data = self.validate_input(inputs.PlatformCreateInput if self.platform else inputs.CreateInput, request.data)
        business_id = data.pop("business", params.get("business"))
        if self.platform and params.get("business") and params["business"] != business_id:
            raise Http404
        result = services.create_case(
            actor=request.user, business_id=business_id, **data, platform=self.platform,
            idempotency_key=request.headers.get("Idempotency-Key", ""),
        )
        return Response(self.representation(request, result.data["case_id"]), status=result.status_code)


class CaseDetailView(SupportView):
    def get(self, request, pk):
        self.case(request, pk, self.scope(request))
        return Response(self.representation(request, pk))


class CaseMessagesView(SupportView):
    def get(self, request, pk):
        params = self.scope(request, inputs.PageInput)
        case = self.case(request, pk, params)
        return self.page(request, case.public_messages.select_related("author").order_by("-id"), params, inputs.PublicMessageSerializer)

    def post(self, request, pk):
        self.case(request, pk, self.scope(request))
        data = self.validate_input(inputs.MessageInput, request.data)
        result = append_message(
            actor=request.user, case_id=pk, platform=self.platform, **data,
            idempotency_key=request.headers.get("Idempotency-Key", ""),
        )
        # Re-check current access on replay and serialize only the public model.
        case = get_case(request.user, pk, platform=self.platform)
        message = get_object_or_404(case.public_messages.select_related("author"), pk=result.data["message_id"])
        return Response(inputs.PublicMessageSerializer(message).data, status=result.status_code)


class CaseNotesView(SupportView):
    platform = True

    def get(self, request, pk):
        params = self.scope(request, inputs.PageInput)
        case = self.case(request, pk, params)
        return self.page(request, case.internal_notes.select_related("author"), params, inputs.InternalNoteSerializer)

    def post(self, request, pk):
        self.case(request, pk, self.scope(request))
        data = self.validate_input(inputs.MessageInput, request.data)
        result = append_message(
            actor=request.user, case_id=pk, platform=True, internal=True, **data,
            idempotency_key=request.headers.get("Idempotency-Key", ""),
        )
        case = get_case(request.user, pk, platform=True)
        note = get_object_or_404(case.internal_notes.select_related("author"), pk=result.data["message_id"])
        return Response(inputs.InternalNoteSerializer(note).data, status=result.status_code)


class CaseEventsView(SupportView):
    def get(self, request, pk):
        params = self.scope(request, inputs.PageInput)
        case = self.case(request, pk, params)
        return self.page(request, case.events.select_related("actor"), params, inputs.CaseEventSerializer)


class CaseAssignView(SupportView):
    platform = True

    def post(self, request, pk):
        self.case(request, pk, self.scope(request))
        data = self.validate_input(inputs.AssignmentInput, request.data)
        services.assign_case(actor=request.user, case_id=pk, assignee_id=data["assigned_to"], version=data["version"])
        return Response(self.representation(request, pk))


class CaseTransitionView(SupportView):
    platform = True

    def post(self, request, pk):
        self.case(request, pk, self.scope(request))
        data = self.validate_input(inputs.TransitionInput, request.data)
        services.transition_case(actor=request.user, case_id=pk, **data)
        return Response(self.representation(request, pk))


class CaseReopenView(SupportView):
    def post(self, request, pk):
        self.case(request, pk, self.scope(request))
        data = self.validate_input(inputs.ReopenInput, request.data)
        services.reopen_case(actor=request.user, case_id=pk, platform=self.platform, **data)
        return Response(self.representation(request, pk))


class CaseReadView(SupportView):
    def post(self, request, pk):
        self.case(request, pk, self.scope(request))
        data = self.validate_input(inputs.ReadInput, request.data)
        state = mark_read(actor=request.user, case_id=pk, platform=self.platform, **data)
        return Response({"through_id": state.last_read_message_id})


class SupportStaffView(SupportView):
    platform = True

    def get(self, request):
        params = self.scope(request, inputs.StaffInput)
        users = active_platform_users().order_by("full_name", "pk")
        if params.get("search"):
            users = users.filter(Q(full_name__icontains=params["search"]) | Q(username__icontains=params["search"]))
        paginator = PageNumberPagination()
        paginator.page_size = params["page_size"]
        page = paginator.paginate_queryset(users, request)
        return paginator.get_paginated_response([inputs.actor_identity(user) for user in page])


class SupportIncidentView(SupportView):
    platform = True

    def get(self, request):
        from apps.support.incidents import get_incident
        params = self.scope(request, inputs.IncidentContext)
        incident = get_incident(actor=request.user, business_id=params["business"], component=params["component"], episode=params["episode"])
        cases = case_projection(request.user, platform=True).filter(
            business_id=params["business"], incident_links__component=params["component"], incident_links__episode=params["episode"],
        ).order_by("-updated_at", "-pk")
        response = self.page(request, cases, params, inputs.CaseSerializer)
        response.data["incident"] = incident
        return response


class CaseIncidentsView(SupportView):
    platform = True

    def get(self, request, pk):
        from apps.support.incidents import case_incidents
        params = self.scope(request, inputs.PageInput)
        case = self.case(request, pk, params)
        paginator = PageNumberPagination()
        paginator.page_size = params["page_size"]
        links = paginator.paginate_queryset(case.incident_links.order_by("-linked_at", "-pk"), request)
        return paginator.get_paginated_response(case_incidents(actor=request.user, case_id=pk, links=links))

    def post(self, request, pk):
        from apps.support.incidents import link_incident
        self.case(request, pk, self.scope(request))
        data = self.validate_input(inputs.IncidentLinkInput, request.data)
        link = link_incident(actor=request.user, case_id=pk, business_id=data["business"], component=data["component"], episode=data["episode"])
        return Response({"id": link.pk}, status=200)
