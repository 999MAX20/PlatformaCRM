from rest_framework import serializers

from .models import BranchService, BranchTravelTime, ScheduleDay, SpecialistBranch


class OfferSerializer(serializers.ModelSerializer):
    service_name = serializers.CharField(source="service.name", read_only=True)

    class Meta:
        model = BranchService
        fields = ["id", "branch", "service", "service_name", "duration_minutes", "price_from", "is_active", "updated_at"]


class AssignmentSerializer(serializers.ModelSerializer):
    resource_name = serializers.CharField(source="resource.name", read_only=True)
    service_ids = serializers.PrimaryKeyRelatedField(source="services", many=True, read_only=True)

    class Meta:
        model = SpecialistBranch
        fields = ["id", "branch", "resource", "resource_name", "service_ids", "is_active"]


class DaySerializer(serializers.ModelSerializer):
    class Meta:
        model = ScheduleDay
        fields = ["id", "branch", "resource", "weekday", "date", "intervals", "updated_at"]


class TravelSerializer(serializers.ModelSerializer):
    class Meta:
        model = BranchTravelTime
        fields = ["id", "from_branch", "to_branch", "minutes"]


class OfferInput(serializers.Serializer):
    service = serializers.IntegerField(min_value=1)
    duration_minutes = serializers.IntegerField(min_value=1, max_value=1440)
    price_from = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=0, allow_null=True)
    is_active = serializers.BooleanField(default=True)


class AssignmentInput(serializers.Serializer):
    resource = serializers.IntegerField(min_value=1)
    service_ids = serializers.ListField(child=serializers.IntegerField(min_value=1), allow_empty=True)
    is_active = serializers.BooleanField(default=True)


class IntervalInput(serializers.Serializer):
    start = serializers.RegexField(r"^\d{2}:\d{2}$")
    end = serializers.RegexField(r"^\d{2}:\d{2}$")


class DayInput(serializers.Serializer):
    resource = serializers.IntegerField(min_value=1, allow_null=True, required=False)
    weekday = serializers.IntegerField(min_value=0, max_value=6, allow_null=True, required=False)
    date = serializers.DateField(allow_null=True, required=False)
    intervals = IntervalInput(many=True, required=False, default=list)
    remove = serializers.BooleanField(default=False)


class TravelInput(serializers.Serializer):
    other_branch = serializers.IntegerField(min_value=1)
    minutes = serializers.IntegerField(min_value=0, max_value=1440)
