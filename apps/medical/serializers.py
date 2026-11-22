from collections.abc import Mapping

from rest_framework import serializers


class StrictSerializer(serializers.Serializer):
    def to_internal_value(self, data):
        if not isinstance(data, Mapping) or set(data) - set(self.fields):
            raise serializers.ValidationError({"request": "Unsupported request fields."})
        return super().to_internal_value(data)


class PatientScopeSerializer(StrictSerializer):
    business_id = serializers.IntegerField(min_value=1)
    branch_id = serializers.IntegerField(min_value=1)


class PatientCreateSerializer(PatientScopeSerializer):
    client_id = serializers.IntegerField(min_value=1)
    demographics = serializers.DictField()
    iin = serializers.CharField(required=False, allow_null=True, allow_blank=True, default=None, max_length=12)


class PatientPreliminarySerializer(PatientScopeSerializer):
    expected_revision = serializers.IntegerField(min_value=1)
    demographics = serializers.DictField()
    iin = serializers.CharField(allow_null=True, allow_blank=True, max_length=12)
    reason = serializers.CharField(max_length=2000)


class PatientVerifySerializer(PatientScopeSerializer):
    expected_revision = serializers.IntegerField(min_value=1)
    expected_client_updated_at = serializers.DateTimeField()
    protocol_reference = serializers.CharField(max_length=200)
    method = serializers.CharField(max_length=64)
    fields = serializers.DictField()


class PatientCorrectionSerializer(PatientVerifySerializer):
    full_name = serializers.CharField(max_length=255)
    demographics = serializers.DictField()
    reason = serializers.CharField(max_length=2000)
