"""One current-access boundary for the personal feed, counts and state changes."""
from collections import defaultdict
from urllib.parse import parse_qs, unquote, urlsplit

from django.db.models import Q
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied

from apps.businesses.access import Actions, Resources, can
from apps.businesses.capabilities import resource_is_enabled
from apps.businesses.models import Business, BusinessMember
from apps.core.crm_read_scope import readable_queryset
from apps.notifications.models import Notification, NotificationRecipient


ENTITY_ROUTES = {
    "/app/tasks": (Resources.TASKS, "task"),
    "/app/leads": (Resources.LEADS, "lead"),
    "/app/deals": (Resources.DEALS, "deal"),
    "/app/clients": (Resources.CLIENTS, "client"),
    "/app/calendar": (Resources.APPOINTMENTS, "appointment"),
    "/app/conversations": (Resources.CONVERSATIONS, "conversation"),
    "/app/outreach": (Resources.NOTIFICATIONS, "campaign"),
}
SECTION_ROUTES = {
    "/app/settings": Resources.SETTINGS,
    "/app/account": Resources.NOTIFICATIONS,
    "/app/integrations": Resources.INTEGRATIONS,
    "/app/pricing": Resources.INTEGRATIONS,
}


def personal_business(*, actor, business_id):
    if not actor or not actor.is_authenticated or not actor.is_active:
        raise PermissionDenied("An active business member is required.")
    businesses = Business.objects.filter(pk=business_id).filter(
        Q(owner=actor, owner__is_active=True) | Q(members__user=actor, members__is_active=True, members__user__is_active=True)
    ).distinct()
    business = businesses.first()
    if business is None:
        raise PermissionDenied("An active business member is required.")
    return business


def can_manage_announcements(*, actor, business):
    active_admin = BusinessMember.objects.filter(
        business=business, user=actor, is_active=True, role=BusinessMember.Roles.ADMIN,
    ).exists()
    return bool(actor and actor.is_authenticated and actor.is_active
                and (business.owner_id == actor.pk or active_admin)
                and can(actor, business, Resources.NOTIFICATIONS, Actions.MANAGE).allowed)


def notification_subject(action_url):
    """Recognize existing producer routes; never echo arbitrary stored URLs."""
    if not action_url:
        return Resources.NOTIFICATIONS, None, ""
    try:
        parsed = urlsplit(action_url)
        path = unquote(parsed.path).rstrip("/")
        if parsed.scheme or parsed.netloc or parsed.fragment:
            return None
        if path and not path.startswith("/app/"):
            path = "/app" + path
        if path in SECTION_ROUTES:
            return SECTION_ROUTES[path], None, path
        if path.startswith("/app/appointments/"):
            appointment_id = path.removeprefix("/app/appointments/")
            if not appointment_id.isascii() or not appointment_id.isdigit() or int(appointment_id) <= 0:
                return None
            pk = int(appointment_id)
            return Resources.APPOINTMENTS, pk, f"/app/appointments/{pk}"
        route = ENTITY_ROUTES.get(path)
        if route is None:
            return None
        resource, key = route
        values = parse_qs(parsed.query, keep_blank_values=True)
        if key not in values:
            return resource, None, path
        ids = values[key]
        if len(ids) != 1 or not ids[0].isascii() or not ids[0].isdigit() or int(ids[0]) <= 0:
            return None
        pk = int(ids[0])
        return resource, pk, f"{path}?{key}={pk}"
    except (ValueError, UnicodeError):
        return None


def _subject_models():
    from apps.bots.models import BotConversation
    from apps.clients.models import Client
    from apps.crm.models import Deal
    from apps.leads.models import Lead
    from apps.outreach.models import OutreachCampaign
    from apps.scheduling.models import Appointment
    from apps.tasks.models import Task

    return {
        Resources.TASKS: Task, Resources.LEADS: Lead, Resources.DEALS: Deal,
        Resources.CLIENTS: Client, Resources.APPOINTMENTS: Appointment,
        Resources.CONVERSATIONS: BotConversation, Resources.NOTIFICATIONS: OutreachCampaign,
    }


def personal_states(*, actor, business, now=None):
    # Recheck membership for direct service callers, not only HTTP authentication.
    business = personal_business(actor=actor, business_id=business.pk)
    now = now or timezone.now()
    states = NotificationRecipient.objects.filter(
        user=actor, notification__business=business, notification__channel=Notification.Channels.SYSTEM,
        notification__revoked_at__isnull=True, notification__send_at__lte=now,
    ).exclude(notification__status=Notification.Statuses.CANCELLED)
    # A reassigned legacy row must not expose its new content to its old recipient.
    states = states.filter(Q(notification__recipient__isnull=True) | Q(notification__recipient=actor))
    announcements = states.filter(notification__kind=Notification.Kinds.ANNOUNCEMENT)
    work = states.filter(notification__kind=Notification.Kinds.WORK)
    from apps.clients.models import Client
    from apps.scheduling.models import Appointment

    for field, model, resource in (("client", Client, Resources.CLIENTS),
                                   ("appointment", Appointment, Resources.APPOINTMENTS)):
        readable = readable_queryset(model.objects.all(), actor=actor, business=business, resource=resource)
        work = work.filter(Q(**{f"notification__{field}__isnull": True}) | Q(**{f"notification__{field}__in": readable}))
    # Legacy producers encode the source in their navigation URL. Resolve these
    # in batches before pagination/counts; no per-notification permission queries.
    candidates = list(work.values_list("pk", "notification__action_url", "notification__category"))
    parsed = {}
    requested = defaultdict(set)
    for pk, url, category in candidates:
        subject = notification_subject(url)
        if subject is not None:
            parsed[pk] = (subject, category)
            if subject[1] is not None:
                requested[subject[0]].add(subject[1])
    models = _subject_models()
    visible = {
        resource: set(readable_queryset(models[resource].objects.filter(pk__in=ids), actor=actor,
                                       business=business, resource=resource).values_list("pk", flat=True))
        for resource, ids in requested.items()
    }
    section_access = {resource: resource_is_enabled(business, resource)
                      and can(actor, business, resource, Actions.VIEW).allowed
                      for resource in {item[0][0] for item in parsed.values()} | {Resources.BILLING}}
    allowed = [pk for pk, ((resource, subject_id, _), category) in parsed.items()
               if (subject_id in visible.get(resource, set()) if subject_id is not None else section_access[resource])
               and (category != Notification.Categories.FINANCE or section_access[Resources.BILLING])]
    return states.filter(Q(pk__in=announcements.values("pk")) | Q(pk__in=allowed)).select_related(
        "notification", "notification__author", "user",
    ).order_by("-received_at", "-pk")
