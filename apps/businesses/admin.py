from django.contrib import admin
from django.db import transaction
from django.core.exceptions import ValidationError
from apps.businesses.profiles import (
    PROFILE_FIELDS, profile_spec, assert_business_type_change_allowed, initialize_business_profile,
)

from apps.businesses.models import Business, BusinessInvitation, BusinessMember, BusinessRole, RolePermission, RolePreset, Team, TeamMember


@admin.register(Business)
class BusinessAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "business_type", "city", "status", "created_at")
    list_filter = ("business_type", "status", "city")
    search_fields = ("name", "slug", "owner__email", "phone", "whatsapp", "telegram", "instagram")
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ("profile_key", "profile_version", "profile_assigned_at")

    def get_readonly_fields(self, request, obj=None):
        if obj is not None and profile_spec(obj) is not None:
            return (*self.readonly_fields, "business_type")
        return self.readonly_fields

    @transaction.atomic
    def save_model(self, request, obj, form, change):
        if change:
            current = Business.objects.select_for_update().get(pk=obj.pk)
            if any(getattr(obj, key) != getattr(current, key) for key in PROFILE_FIELDS):
                raise ValidationError("The assigned business profile cannot be changed.")
            assert_business_type_change_allowed(current, obj.business_type)
        elif any(getattr(obj, key) is not None for key in PROFILE_FIELDS):
            raise ValidationError("The business profile is assigned by the server.")
        if not change:
            initialize_business_profile(obj, actor=request.user)
            return
        super().save_model(request, obj, form, change)


@admin.register(BusinessMember)
class BusinessMemberAdmin(admin.ModelAdmin):
    list_display = ("business", "user", "role", "business_role", "is_active", "created_at")
    list_filter = ("role", "is_active")
    search_fields = ("business__name", "user__email", "user__full_name")


@admin.register(BusinessInvitation)
class BusinessInvitationAdmin(admin.ModelAdmin):
    list_display = ("email", "business", "role", "delivery_channel", "status", "expires_at", "created_at")
    list_filter = ("role", "delivery_channel", "accepted_at", "revoked_at")
    search_fields = ("business__name", "email", "phone", "telegram", "full_name")
    readonly_fields = ("token", "accepted_at", "revoked_at", "created_at", "updated_at")


@admin.register(RolePreset)
class RolePresetAdmin(admin.ModelAdmin):
    list_display = ("key", "name", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("key", "name")


class RolePermissionInline(admin.TabularInline):
    model = RolePermission
    extra = 0


@admin.register(BusinessRole)
class BusinessRoleAdmin(admin.ModelAdmin):
    list_display = ("business", "name", "preset_key", "is_system", "is_active", "created_at")
    list_filter = ("preset_key", "is_system", "is_active")
    search_fields = ("business__name", "name", "preset_key")
    inlines = [RolePermissionInline]


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ("business", "name", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("business__name", "name")


@admin.register(TeamMember)
class TeamMemberAdmin(admin.ModelAdmin):
    list_display = ("team", "member", "is_lead", "created_at")
    list_filter = ("is_lead",)
    search_fields = ("team__name", "member__user__email", "member__user__full_name")
