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


class PatientResolveSerializer(PatientScopeSerializer):
    kind = serializers.ChoiceField(choices=("name", "phone", "email", "birth", "iin"))
    query = serializers.CharField(min_length=2, max_length=255)
    include_archived = serializers.BooleanField(default=False)
    offset = serializers.IntegerField(min_value=0, default=0)
    limit = serializers.IntegerField(min_value=1, max_value=50, default=25)


class PatientSearchAccessSerializer(StrictSerializer):
    business_id = serializers.IntegerField(min_value=1)


class PatientListProjectionSerializer(PatientScopeSerializer):
    client_ids = serializers.ListField(child=serializers.IntegerField(min_value=1), min_length=1, max_length=100)


class PatientCreateSerializer(PatientScopeSerializer):
    client_id = serializers.IntegerField(min_value=1)
    demographics = serializers.DictField()
    iin = serializers.CharField(required=False, allow_null=True, allow_blank=True, default=None, max_length=12)


class PatientRegistrationSerializer(PatientScopeSerializer):
    full_name = serializers.CharField(max_length=255)
    phone = serializers.CharField(max_length=32, allow_blank=True, default="")
    email = serializers.EmailField(allow_blank=True, default="")
    demographics = serializers.DictField()
    iin = serializers.CharField(allow_null=True, allow_blank=True, default=None, max_length=12)
    confirmed_separate_person = serializers.BooleanField(default=False)


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


class PatientIINCorrectionSerializer(PatientVerifySerializer):
    iin = serializers.CharField(allow_null=True, allow_blank=True, max_length=12)
    reason = serializers.CharField(max_length=2000)


class IdentityCorrectionListSerializer(PatientScopeSerializer):
    client_id = serializers.IntegerField(min_value=1)
    offset = serializers.IntegerField(min_value=0, default=0)
    limit = serializers.IntegerField(min_value=1, max_value=50, default=25)


class IdentityCorrectionDecisionSerializer(StrictSerializer):
    business_id = serializers.IntegerField(min_value=1)
    approve = serializers.BooleanField()
    reason = serializers.CharField(max_length=2000)
