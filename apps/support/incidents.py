"""Explicit, platform-only associations with a specific observed episode."""
from datetime import timedelta

from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.exceptions import NotFound, ValidationError

from apps.businesses.models import Business
from apps.core.models import ServiceComponentState
from apps.core.service_status import OBSERVATION_MAX_AGE_SECONDS
from apps.support.access import get_case, get_case_business
from apps.support.models import IncidentLink
from apps.support.services import SupportVersionConflict, audit_case


def validate_incident(component, episode):
    if component not in ServiceComponentState.Components.values:
        raise ValidationError({"component": "Select a monitored component."})
    if isinstance(episode, bool) or not isinstance(episode, int) or episode < 1:
        raise ValidationError({"episode": "A positive incident episode is required."})


def observation(row, *, now):
    fresh = now - timedelta(seconds=OBSERVATION_MAX_AGE_SECONDS) <= row.observed_at <= now
    return {"state": row.state if fresh else "unknown", "last_state": row.state,
            "observed_at": row.observed_at, "affected_count": row.affected_count,
            "recovered_at": row.recovered_at, "fresh": fresh}


def incident_description(business_id, component, episode, *, snapshot=None, row=None):
    # A newer episode is not evidence of the old episode's recovery time.
    if row is None:
        row = ServiceComponentState.objects.filter(business_id=business_id, component=component).first()
    same = row is not None and row.episode == episode and row.started_at is not None
    if not same and snapshot is None:
        raise NotFound("The incident is unavailable. Refresh diagnostics.")
    source = row if same else snapshot
    return {
        "business": business_id, "component": component, "episode": episode,
        "source": "background_processing", "started_at": source.started_at,
        "current": observation(row, now=timezone.now()) if same else None,
        "historical": not same,
        "snapshot": {"state": snapshot.state, "observed_at": snapshot.observed_at,
                     "affected_count": snapshot.affected_count, "recovered_at": snapshot.recovered_at}
                    if snapshot else None,
    }


def get_incident(*, actor, business_id, component, episode):
    business = get_case_business(actor, business_id, platform=True)
    validate_incident(component, episode)
    snapshot = IncidentLink.objects.filter(case__business_id=business_id, component=component, episode=episode).order_by("linked_at", "pk").first()
    return {**incident_description(business_id, component, episode, snapshot=snapshot), "business_name": business.name}


@transaction.atomic
def link_incident(*, actor, case_id, business_id, component, episode):
    case = get_case(actor, case_id, platform=True, lock=True)
    if case.business_id != business_id:
        raise NotFound()
    validate_incident(component, episode)
    # Same lock as the collector prevents a transition between lookup and snapshot.
    Business.objects.select_for_update().get(pk=case.business_id)
    existing = IncidentLink.objects.filter(case=case, component=component, episode=episode).first()
    if existing:
        return existing
    row = get_object_or_404(ServiceComponentState, business_id=case.business_id, component=component)
    if row.episode != episode or row.started_at is None:
        raise SupportVersionConflict()
    link = IncidentLink.objects.create(
        case=case, component=component, episode=episode, started_at=row.started_at,
        observed_at=row.observed_at, state=row.state, affected_count=row.affected_count,
        recovered_at=row.recovered_at, linked_by=actor,
    )
    audit_case(actor, case, "incident_linked", component=component, episode=episode)
    return link


def case_incidents(*, actor, case_id, links):
    case = get_case(actor, case_id, platform=True)
    rows = {row.component: row for row in ServiceComponentState.objects.filter(business=case.business)}
    return [{**incident_description(case.business_id, link.component, link.episode,
                                   snapshot=link, row=rows.get(link.component)),
             "id": link.pk, "linked_at": link.linked_at}
            for link in links]
