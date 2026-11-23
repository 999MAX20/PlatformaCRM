from .assistant_notifications import AssistantNotificationSource
from .participation_notifications import ParticipationNotificationSource


class MedicalNotificationSource:
    sources = (ParticipationNotificationSource, AssistantNotificationSource)
    related_paths = tuple(path for source in sources for path in source.related_paths)

    @classmethod
    def filter_ids(cls, **kwargs):
        claimed, allowed = set(), set()
        for source in cls.sources:
            source_claimed, source_allowed = source.filter_ids(**kwargs)
            claimed.update(source_claimed)
            allowed.update(source_allowed)
        return claimed, allowed

    @classmethod
    def presentation(cls, notification):
        for source in cls.sources:
            result = source.presentation(notification)
            if result is not None:
                return result
        return None
