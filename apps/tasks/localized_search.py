from django.db.models import Case, CharField, Exists, OuterRef, Q, Value, When
from django.db.models.functions import Cast, Concat, JSONObject
from django.db.models.fields.json import KeyTransform

from apps.activities.models import ActivityEvent
from apps.activities.taxonomy import ActivityEvents


FOLLOW_UP_TITLES = {
    "en": {
        "cancelled": "Follow up cancelled appointment #{id}",
        "no_show": "Follow up no-show appointment #{id}",
        "completed": "Follow up completed appointment #{id}",
    },
    "ru": {
        "cancelled": "Связаться после отмены записи #{id}",
        "no_show": "Связаться после пропущенной записи #{id}",
        "completed": "Связаться после завершённой записи #{id}",
    },
    "kk": {
        "cancelled": "Бас тартылған #{id} жазбадан кейін хабарласу",
        "no_show": "Клиент келмеген #{id} жазбадан кейін хабарласу",
        "completed": "Аяқталған #{id} жазбадан кейін хабарласу",
    },
}


def _title_expression(template):
    before, after = template.split("{id}")
    return Concat(Value(before), Cast("appointment_id", CharField()), Value(after), output_field=CharField())


def with_localized_search_title(queryset, locale):
    titles = FOLLOW_UP_TITLES.get(locale, FOLLOW_UP_TITLES["en"])
    events = ActivityEvent.objects.filter(
        business_id=OuterRef("business_id"), entity_type="Task",
        entity_id=Cast(OuterRef("pk"), CharField()), event_type=ActivityEvents.TASK_CREATED,
        metadata__appointment_id=KeyTransform("id", JSONObject(id=OuterRef("appointment_id"))),
    )
    cases = []
    for status, template in titles.items():
        provenance = Exists(events.filter(metadata__appointment_status=status))
        canonical = Q(title=_title_expression(FOLLOW_UP_TITLES["en"][status]))
        # Fold static Unicode copy in Python; SQLite LOWER only handles ASCII.
        cases.append(When(canonical & provenance, then=_title_expression(template.casefold())))
    return queryset.alias(localized_search_title=Case(*cases, default=Value(""), output_field=CharField()))
