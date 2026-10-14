from rest_framework import serializers

from apps.businesses.models import Business


class PlatformMerchantFilters(serializers.Serializer):
    search = serializers.CharField(required=False, allow_blank=True, max_length=200)
    status = serializers.ChoiceField(choices=Business.Statuses.choices, required=False)
    page_size = serializers.IntegerField(default=20, min_value=1, max_value=100)


class PlatformSupportNoteSerializer(serializers.Serializer):
    action_type = serializers.CharField(default="support_note", max_length=64)
    note = serializers.CharField(max_length=4000)
    status = serializers.CharField(default="logged", max_length=32)
