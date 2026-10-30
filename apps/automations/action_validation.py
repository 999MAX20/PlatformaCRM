"""One configuration contract for previews, writes and queued execution."""
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import URLValidator
from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.automations.condition_fields import ENTITY_TYPE_BY_TRIGGER
from apps.businesses.access import Actions, Resources, assert_can
from apps.businesses.assignment_policy import assert_assignment_allowed
from apps.businesses.capabilities import assert_resource_enabled
from apps.businesses.models import RolePermission
from apps.branches.access import assert_network_grant
from apps.notifications.models import Notification
from apps.tasks.models import Task


ACTION_FIELDS = {
    "create_task": {"title", "description", "priority", "assignee_id", "user_id", "due_at"},
    "create_follow_up": {"title", "description", "priority", "assignee_id", "user_id", "due_at", "due_in_days"},
    "create_notification": {"text", "channel", "category", "priority", "recipient_id", "user_id", "action_url", "action_label", "include_owner"},
    "assign_user": {"user_id", "assignee_id", "owner_id"},
    "add_note": {"text"},
    "wait": set(),
}
SUPPORTED_AUTOMATION_ACTION_TYPES = set(ACTION_FIELDS)
ENTITY_RESOURCES = {"Lead": Resources.LEADS, "Deal": Resources.DEALS, "Task": Resources.TASKS,
                    "BotConversation": Resources.CONVERSATIONS, "Appointment": Resources.APPOINTMENTS,
                    "Client": Resources.CLIENTS}


def _integer(value, field, *, minimum=1):
    if isinstance(value, bool) or not (isinstance(value, int) or isinstance(value, str) and value.isdecimal()):
        raise ValidationError({field: "Enter a whole number."})
    number = int(value)
    if number < minimum or number > 2147483647:
        raise ValidationError({field: "Value is outside the supported range."})
    return number


def _assert_action_authority(actor, business, resource, action, *, entity=None):
    permission = assert_can(actor, business, resource, action, obj=entity if action == Actions.UPDATE else None)
    if entity is None:
        # A persisted rule runs as owner on future events, not only on entities
        # currently assigned to its configurator or in their selected branches.
        if permission.scope != RolePermission.Scopes.BUSINESS:
            raise PermissionDenied("Configuring this automation action requires business-wide permission.")
        assert_network_grant(actor, business)


def validate_action_config(*, action_type, config, delay_seconds=0, business, trigger_type,
                           actor, entity=None):
    if action_type not in ACTION_FIELDS:
        raise ValidationError({"action_type": "This action is not supported by the current automation engine."})
    delay = _integer(delay_seconds, "delay_seconds", minimum=0)
    if action_type == "wait" and not delay:
        raise ValidationError({"delay_seconds": "Wait action requires a positive delay."})
    if not isinstance(config, dict):
        raise ValidationError({"config": "Action settings must be an object."})
    errors = {key: "This setting is not supported for the selected action." for key in config.keys() - ACTION_FIELDS[action_type]}
    result = dict(config)
    for field in ("title", "description", "text", "action_label", "action_url"):
        if field not in config:
            continue
        limit = {"title": 255, "action_label": 64, "action_url": 255}.get(field)
        value = config[field]
        if not isinstance(value, str) or limit is not None and len(value) > limit:
            errors[field] = "Enter text within the field length limit."
        elif field in {"title", "text"} and not value.strip():
            errors[field] = "Enter non-empty text or omit this setting to use the default."
    choices = {"priority": Notification.Priorities.values if action_type == "create_notification" else Task.Priorities.values,
               "channel": Notification.Channels.values, "category": Notification.Categories.values}
    for field, values in choices.items():
        if field in config and config[field] not in values:
            errors[field] = "Select a supported value."
    if "include_owner" in config and not isinstance(config["include_owner"], bool):
        errors["include_owner"] = "Use true or false."
    if "due_at" in config:
        try:
            result["due_at"] = serializers.DateTimeField().run_validation(config["due_at"]).isoformat()
        except (ValidationError, AttributeError):
            errors["due_at"] = "Enter a valid date and time."
    if "due_in_days" in config:
        try:
            result["due_in_days"] = _integer(config["due_in_days"], "due_in_days")
            timezone.now() + timezone.timedelta(days=result["due_in_days"])
        except (ValidationError, OverflowError):
            errors["due_in_days"] = "Enter a positive number of days within the supported date range."
    url = config.get("action_url")
    if isinstance(url, str) and url and not (url.startswith("/app/") and "\\" not in url):
        try:
            URLValidator(schemes=["http", "https"])(url)
        except DjangoValidationError:
            errors["action_url"] = "Use an app link or an HTTP(S) address."
    user_fields = [field for field in ("user_id", "assignee_id", "owner_id", "recipient_id") if field in config]
    for field in user_fields:
        try:
            result[field] = _integer(config[field], field)
        except ValidationError:
            errors[field] = "Select an active business member."
    if action_type == "assign_user" and not user_fields:
        errors["user_id"] = "Select the user to assign."
    if len({result[field] for field in user_fields if field not in errors}) > 1:
        errors["user_id"] = "Select one user for this action."
    if errors:
        raise ValidationError({"config": errors})

    entity_type = entity.__class__.__name__ if entity is not None else ENTITY_TYPE_BY_TRIGGER.get(trigger_type)
    if entity is not None and getattr(entity, "business_id", None) != business.pk:
        raise ValidationError({"entity": "The event must belong to the selected business."})
    if actor is None or not actor.is_active:
        raise ValidationError({"actor": "An active business user is required."})
    resource = ENTITY_RESOURCES.get(entity_type)
    assignment_resource = None
    if action_type == "assign_user":
        if entity_type not in {"Lead", "Deal", "Task", "BotConversation"}:
            raise ValidationError({"action_type": "Assignment is not supported for this trigger."})
        assignment_resource = resource
        assert_resource_enabled(business, resource)
        _assert_action_authority(actor, business, resource, Actions.UPDATE, entity=entity)
    elif action_type in {"create_task", "create_follow_up"}:
        assignment_resource = Resources.TASKS
        assert_resource_enabled(business, Resources.TASKS)
        _assert_action_authority(actor, business, Resources.TASKS, Actions.CREATE, entity=entity)
    elif action_type == "create_notification":
        _assert_action_authority(actor, business, Resources.NOTIFICATIONS, Actions.MANAGE, entity=entity)
    elif action_type == "add_note":
        _assert_action_authority(actor, business, Resources.CLIENTS, Actions.CREATE, entity=entity)
        if resource:
            _assert_action_authority(actor, business, resource, Actions.UPDATE, entity=entity)
    for field in user_fields:
        user = get_user_model().objects.filter(pk=result[field], is_active=True).first()
        if user is None or (user.pk != business.owner_id and not business.members.filter(user=user, is_active=True).exists()):
            raise ValidationError({"config": {field: "Select an active business member."}})
        if assignment_resource:
            assert_assignment_allowed(actor=actor, business=business, target_user=user, resource=assignment_resource)
    return result


def validate_action_list(actions, *, business, trigger_type, actor, entity=None):
    if not actions:
        raise ValidationError({"actions": "At least one action is required."})
    errors = {}
    for index, action in enumerate(actions):
        try:
            action["config"] = validate_action_config(
                action_type=action["action_type"], config=action.get("config", {}),
                delay_seconds=action.get("delay_seconds", 0), business=business,
                trigger_type=trigger_type, actor=actor, entity=entity,
            )
        except ValidationError as exc:
            errors[index] = exc.detail
    if errors:
        raise ValidationError({"actions": errors})
    return actions
