from rest_framework import serializers

from .serializers import PatientScopeSerializer


class RepresentativeListSerializer(PatientScopeSerializer):
    offset = serializers.IntegerField(min_value=0, default=0)
    limit = serializers.IntegerField(min_value=1, max_value=50, default=25)


class RepresentativeVerifySerializer(PatientScopeSerializer):
    representative_client_id = serializers.IntegerField(min_value=1)
    expected_patient_revision = serializers.IntegerField(min_value=1)
    expected_client_updated_at = serializers.DateTimeField()
    protocol_reference = serializers.CharField(max_length=200)
    method = serializers.CharField(max_length=64)
    fields = serializers.DictField()
    permissions = serializers.ListField(child=serializers.CharField(max_length=64), min_length=1, max_length=30)
    valid_from = serializers.DateTimeField()
    valid_until = serializers.DateTimeField(allow_null=True)


class RepresentativeRevokeSerializer(PatientScopeSerializer):
    representative_client_id = serializers.IntegerField(min_value=1)
    expected_revision = serializers.IntegerField(min_value=1)
    reason = serializers.CharField(max_length=2000)
