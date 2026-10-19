"""Keep generic configuration CRUD inside the same domain write boundary."""
from apps.automations.configuration import configuration_write, validate_active_configuration
from apps.automations.models import AutomationRule


def _rule_id(instance):
    return instance.pk if isinstance(instance, AutomationRule) else instance.rule_id


class AtomicConfigurationMixin:
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self._enforce_business_access(serializer)
        business = self._business_from_serializer(serializer)
        with configuration_write(business):
            response = super().create(request, *args, **kwargs)
            rule_id = response.data["id"] if self.queryset.model is AutomationRule else response.data["rule"]
            validate_active_configuration(rule_id, request.user)
            return response

    def update(self, request, *args, **kwargs):
        original = self.get_object()
        with configuration_write(self._business_from_instance(original)):
            # super re-reads and validates after acquiring the lock.
            response = super().update(request, *args, **kwargs)
            validate_active_configuration(_rule_id(original), request.user)
            if not isinstance(original, AutomationRule):
                validate_active_configuration(response.data["rule"], request.user)
            return response

    def destroy(self, request, *args, **kwargs):
        original = self.get_object()
        with configuration_write(self._business_from_instance(original)):
            response = super().destroy(request, *args, **kwargs)
            validate_active_configuration(_rule_id(original), request.user)
            return response
