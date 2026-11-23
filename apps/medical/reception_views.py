from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .reception_booking import book_reception_request
from .reception_claims import claim_reception_request
from .reception_link import link_reception_appointment
from .reception_transfer import transfer_reception_request
from .reception_handover_selectors import list_reception_history, list_reception_recipients
from .reception_requests import request_primary_follow_up
from .reception_selectors import list_follow_up_options, list_primary_follow_ups, list_reception_candidates, list_reception_requests
from .reception_serializers import (ReceptionBookSerializer, ReceptionCommandSerializer, ReceptionCreateSerializer,
    ReceptionLinkSerializer, ReceptionOptionsSerializer, ReceptionPageSerializer, ReceptionPrimarySerializer, ReceptionQueueSerializer,
    ReceptionTransferSerializer, ReceptionRecipientsSerializer)


class ReceptionBookingRequestViewSet(viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    lookup_value_regex = r"[0-9]+"
    http_method_names = ["get", "post", "head", "options"]
    serializer_class = ReceptionCommandSerializer

    def get_serializer_class(self):
        return {"create": ReceptionCreateSerializer, "list": ReceptionQueueSerializer,
            "primary": ReceptionPrimarySerializer, "catalog": ReceptionOptionsSerializer, "book": ReceptionBookSerializer,
            "link": ReceptionLinkSerializer, "candidates": ReceptionPageSerializer,
            "transfer": ReceptionTransferSerializer, "recipients": ReceptionRecipientsSerializer,
            "history": ReceptionPageSerializer}.get(self.action, ReceptionCommandSerializer)

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        response["Cache-Control"] = "no-store, private"
        response["Pragma"] = "no-cache"
        return response

    def _read(self, request, service):
        serializer = self.get_serializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        return Response(service(actor=request.user, **serializer.validated_data))

    def list(self, request):
        return self._read(request, list_reception_requests)

    @action(detail=False, methods=["get"])
    def primary(self, request):
        return self._read(request, list_primary_follow_ups)

    @action(detail=False, methods=["get"])
    def catalog(self, request):
        return self._read(request, list_follow_up_options)

    @action(detail=True, methods=["get"])
    def candidates(self, request, pk=None):
        serializer = self.get_serializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        return Response(list_reception_candidates(actor=request.user, request_id=int(pk), **serializer.validated_data))

    @action(detail=True, methods=["get"])
    def recipients(self, request, pk=None):
        serializer = self.get_serializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        return Response(list_reception_recipients(actor=request.user, request_id=int(pk), **serializer.validated_data))

    @action(detail=True, methods=["get"])
    def history(self, request, pk=None):
        serializer = self.get_serializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        return Response(list_reception_history(actor=request.user, request_id=int(pk), **serializer.validated_data))

    def _command(self, request, service, pk=None):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = service(actor=request.user, **({"request_id": int(pk)} if pk is not None else {}),
            **serializer.validated_data, idempotency_key=request.headers.get("Idempotency-Key"))
        item, replayed = result[0], result[-1]
        data = {"id": item.pk, "state": item.state, "revision": item.revision, "replayed": replayed}
        if len(result) == 3:
            data["appointment_id"] = result[1].pk
        return Response(data, status=201 if self.action == "create" and not replayed else 200)

    def create(self, request):
        return self._command(request, request_primary_follow_up)

    @action(detail=True, methods=["post"])
    def claim(self, request, pk=None):
        return self._command(request, claim_reception_request, pk)

    @action(detail=True, methods=["post"])
    def transfer(self, request, pk=None):
        return self._command(request, transfer_reception_request, pk)

    @action(detail=True, methods=["post"])
    def book(self, request, pk=None):
        return self._command(request, book_reception_request, pk)

    @action(detail=True, methods=["post"])
    def link(self, request, pk=None):
        return self._command(request, link_reception_appointment, pk)
