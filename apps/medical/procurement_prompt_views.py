from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .serializers import StrictSerializer
from .procurement_prompt import claim_prompt, record_prompt_decision


class PromptClaimSerializer(StrictSerializer):
    business_id = serializers.IntegerField(min_value=1)
    encounter_id = serializers.IntegerField(min_value=1)


class PromptDecisionSerializer(StrictSerializer):
    business_id = serializers.IntegerField(min_value=1)
    token = serializers.UUIDField()
    decision = serializers.ChoiceField(choices=("ack","yes","no"))


class MedicalProcurementPromptViewSet(viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    def get_serializer_class(self):
        return PromptDecisionSerializer if self.action == "decision" else PromptClaimSerializer

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        response["Cache-Control"] = "no-store, private"
        return response

    @action(detail=False, methods=["post"])
    def claim(self, request):
        data=self.get_serializer(data=request.data);data.is_valid(raise_exception=True)
        return Response(claim_prompt(actor=request.user, **data.validated_data))

    @action(detail=False, methods=["post"])
    def decision(self, request):
        data=self.get_serializer(data=request.data);data.is_valid(raise_exception=True)
        return Response(record_prompt_decision(actor=request.user, **data.validated_data))
