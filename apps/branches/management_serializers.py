from rest_framework import serializers


class EntityInput(serializers.Serializer):
    business = serializers.IntegerField(min_value=1)
    id = serializers.IntegerField(min_value=1, required=False)
    name = serializers.CharField(max_length=255)
    is_active = serializers.BooleanField(required=False)


class ServiceLocationInput(serializers.Serializer):
    branch = serializers.IntegerField(min_value=1)
    specialist_ids = serializers.ListField(child=serializers.IntegerField(min_value=1), max_length=1000)
    room_ids = serializers.ListField(child=serializers.IntegerField(min_value=1), max_length=1000)


class ManagementServiceInput(EntityInput):
    description = serializers.CharField(allow_blank=True, max_length=10000, default="")
    duration_minutes = serializers.IntegerField(min_value=1, max_value=1440)
    price_from = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=0, allow_null=True)
    requires_room = serializers.BooleanField(default=False)
    locations = ServiceLocationInput(many=True)


class SpecialistLocationInput(serializers.Serializer):
    branch = serializers.IntegerField(min_value=1)
    service_ids = serializers.ListField(child=serializers.IntegerField(min_value=1), max_length=1000)


class ManagementSpecialistInput(EntityInput):
    profession = serializers.CharField(allow_blank=True, max_length=120, default="")
    public_description = serializers.CharField(allow_blank=True, max_length=10000, default="")
    contact_phone = serializers.CharField(allow_blank=True, max_length=32, default="")
    locations = SpecialistLocationInput(many=True)


class ManagementRoomInput(EntityInput):
    branch = serializers.IntegerField(min_value=1)
    public_description = serializers.CharField(allow_blank=True, max_length=10000, default="")
    service_ids = serializers.ListField(child=serializers.IntegerField(min_value=1), max_length=1000)
    inherit_schedule = serializers.BooleanField(default=True)


class ManagementBranchInput(EntityInput):
    city = serializers.CharField(allow_blank=True, max_length=120, default="")
    address = serializers.CharField(allow_blank=True, max_length=10000, default="")
    phone = serializers.CharField(allow_blank=True, max_length=32, default="")
    service_ids = serializers.ListField(child=serializers.IntegerField(min_value=1), max_length=1000)
    specialist_ids = serializers.ListField(child=serializers.IntegerField(min_value=1), max_length=1000)


class ManagementLifecycleInput(serializers.Serializer):
    business = serializers.IntegerField(min_value=1)
    id = serializers.IntegerField(min_value=1)
    kind = serializers.ChoiceField(choices=["services", "staff", "rooms", "branches"])
    operation = serializers.ChoiceField(choices=["activate", "deactivate", "archive", "restore", "delete"])
