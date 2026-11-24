from rest_framework import serializers

from .models import ReceptionBookingRequest
from .serializers import StrictSerializer


class ReceptionBusinessSerializer(StrictSerializer):
    business_id = serializers.IntegerField(min_value=1)


class ReceptionPageSerializer(ReceptionBusinessSerializer):
    offset = serializers.IntegerField(min_value=0, max_value=10000, default=0)
    limit = serializers.IntegerField(min_value=1, max_value=50, default=25)


class ReceptionQueueSerializer(ReceptionPageSerializer):
    branch_id = serializers.IntegerField(min_value=1)
    request_id = serializers.IntegerField(min_value=1, required=False)
    state = serializers.ChoiceField(choices=ReceptionBookingRequest.States.values, required=False)


class ReceptionRecipientsSerializer(ReceptionPageSerializer):
    search = serializers.CharField(max_length=120, required=False, default="", allow_blank=True)


class ReceptionPrimarySerializer(ReceptionPageSerializer):
    patient_id = serializers.IntegerField(min_value=1)
    encounter_id = serializers.IntegerField(min_value=1)
    participation_id = serializers.IntegerField(min_value=1, required=False)


class ReceptionOptionsSerializer(ReceptionPrimarySerializer):
    kind = serializers.ChoiceField(choices=("service", "staff"))
    search = serializers.CharField(max_length=120, required=False, default="", allow_blank=True)


class ReceptionCreateSerializer(ReceptionBusinessSerializer):
    patient_id = serializers.IntegerField(min_value=1)
    encounter_id = serializers.IntegerField(min_value=1)
    expected_revision = serializers.IntegerField(min_value=1)
    participation_id = serializers.IntegerField(min_value=1, required=False)
    service_id = serializers.IntegerField(min_value=1)
    preferred_resource_id = serializers.IntegerField(min_value=1)
    recommended_from = serializers.DateField()
    recommended_until = serializers.DateField()
    patient_in_clinic = serializers.BooleanField()
    duration_minutes = serializers.IntegerField(min_value=1, required=False, allow_null=True)


class ReceptionCommandSerializer(ReceptionBusinessSerializer):
    expected_revision = serializers.IntegerField(min_value=1)


class ReceptionTransferSerializer(ReceptionCommandSerializer):
    assignee_id = serializers.IntegerField(min_value=1, allow_null=True)
    reason = serializers.CharField(max_length=1000, allow_blank=False)


class ReceptionContactSerializer(ReceptionCommandSerializer):
    action = serializers.ChoiceField(choices=("no_answer", "contacted", "declined", "expired", "cancelled", "reopen"))
    reason = serializers.CharField(max_length=1000, allow_blank=False)


class ReceptionBookSerializer(ReceptionCommandSerializer):
    resource_id = serializers.IntegerField(min_value=1)
    start_at = serializers.DateTimeField()
    expected_price = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=0, allow_null=True)
    expected_duration_minutes = serializers.IntegerField(min_value=1)
    confirmed = serializers.BooleanField()


class ReceptionLinkSerializer(ReceptionCommandSerializer):
    appointment_id = serializers.IntegerField(min_value=1)
    expected_updated_at = serializers.DateTimeField()
    confirmed = serializers.BooleanField()
