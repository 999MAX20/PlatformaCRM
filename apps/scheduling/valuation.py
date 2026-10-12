"""Appointment service estimates use agreed terms, with legacy catalog fallback."""
from django.db.models import Case, DecimalField, F, When


def appointment_price_expression():
    # A snapshot with an unknown price stays unknown; it is not today's catalog.
    return Case(When(booked_duration_minutes__isnull=False, then=F("booked_price")),
                default=F("service__price_from"), output_field=DecimalField(max_digits=12, decimal_places=2))
