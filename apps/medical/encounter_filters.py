from datetime import date

from django.db.models import F, OuterRef, Q, Subquery
from rest_framework.exceptions import ValidationError

from apps.core.crm_filters import business_date_range
from .identity_crypto import MedicalDataUnavailable
from .models import MedicalEncounterRevision


def filter_encounters(query, *, branch_id=None, author_id=None, state=None, date_from=None, date_to=None):
    for field, value in (("branch_id", branch_id), ("author_id", author_id)):
        if value is not None and (type(value) is not int or value <= 0):
            raise ValidationError({field: "Select a valid identifier."})
    if state is not None and state not in ("draft", "finalized"):
        raise ValidationError({"state": "Select a valid encounter state."})
    query = business_date_range(query, {"started_from": date_from.isoformat() if type(date_from) is date else date_from,
        "started_to": date_to.isoformat() if type(date_to) is date else date_to}, prefix="started", field="started_at")
    if branch_id is not None:
        query = query.filter(branch_id=branch_id)
    if state is not None:
        query = query.filter(state=state)
    if author_id is not None:
        current = MedicalEncounterRevision.objects.filter(encounter_id=OuterRef("pk"), revision=OuterRef("revision"))
        query = query.annotate(_current_author=Subquery(current.values("author_id")[:1])).filter(_current_author=author_id)
    return query


def encounter_filter_options(query, *, business):
    if query.exclude(Q(branch__business=business) & Q(primary_clinician__business=business)).exists():
        raise MedicalDataUnavailable()
    branches = query.order_by("branch__name", "branch_id").values_list("branch_id", "branch__name").distinct()
    current = MedicalEncounterRevision.objects.filter(encounter_id__in=query.values("pk"), revision=F("encounter__revision"))
    authors = current.order_by("author__full_name", "author_id").values_list("author_id", "author__full_name").distinct()
    return {"branches": [{"id": pk, "name": name} for pk, name in branches],
            "authors": [{"id": pk, "name": name} for pk, name in authors]}
