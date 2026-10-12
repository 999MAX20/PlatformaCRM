from rest_framework import serializers

from .models import Branch
from .services import create_branch, update_branch


class BranchSerializer(serializers.ModelSerializer):
    can_manage = serializers.SerializerMethodField()
    can_book = serializers.SerializerMethodField()
    can_work = serializers.SerializerMethodField()

    class Meta:
        model = Branch
        fields = ["id", "business", "name", "address", "phone", "is_active", "archived_at", "can_manage", "can_book", "can_work", "created_at", "updated_at"]
        read_only_fields = ["is_active", "archived_at", "created_at", "updated_at"]

    def get_can_manage(self, obj):
        from apps.businesses.access import Actions, Resources, can
        from .access import accessible_branches
        actor = self.context["request"].user
        return can(actor, obj.business, Resources.SETTINGS, Actions.UPDATE).allowed and accessible_branches(actor, obj.business).filter(pk=obj.pk).exists()

    def get_can_book(self, obj):
        from .access import accessible_branches
        return accessible_branches(self.context["request"].user, obj.business, active_only=True).filter(pk=obj.pk).exists()

    def get_can_work(self, obj):
        from .access import accessible_branches
        return accessible_branches(self.context["request"].user, obj.business).filter(pk=obj.pk).exists()

    def create(self, validated_data):
        return create_branch(actor=self.context["request"].user, **validated_data)

    def update(self, instance, validated_data):
        business = validated_data.pop("business", instance.business)
        if business.pk != instance.business_id:
            raise serializers.ValidationError({"business": "Business cannot be changed."})
        return update_branch(branch=instance, actor=self.context["request"].user, changes=validated_data)


class BranchGrantSerializer(serializers.Serializer):
    member = serializers.IntegerField(min_value=1)
    branch_ids = serializers.ListField(child=serializers.IntegerField(min_value=1), allow_empty=True)
    all_branches = serializers.BooleanField(default=False)
