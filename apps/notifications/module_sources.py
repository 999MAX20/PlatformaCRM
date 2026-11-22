"""Installed modules own their notification subjects and current-access checks."""
from django.apps import apps
from django.utils.module_loading import import_string


def notification_sources():
    for config in apps.get_app_configs():
        source = getattr(config, "personal_notification_source", None)
        if source:
            yield import_string(source)


def source_relations():
    return [relation for source in notification_sources() for relation in source.related_paths]


def source_projection(notification):
    for source in notification_sources():
        projection = source.presentation(notification)
        if projection is not None:
            return projection
    return None
