from apps.core.permissions import IsTenantMember, user_can_access_business


class IsAutomationRuleMember(IsTenantMember):
    """Action/condition ownership is inherited from the rule."""
    def has_object_permission(self, request, view, obj):
        return user_can_access_business(request.user, obj.rule.business)
