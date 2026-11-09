"""Shared Client write-field semantics for API and import mutations."""
from rest_framework.exceptions import PermissionDenied


def validate_client_write_fields(attrs, *, notes_allowed):
    if "notes" in attrs and not notes_allowed:
        if attrs["notes"]:
            raise PermissionDenied("This field is not available to your role.")
        # A masked empty round-trip cannot clear a private note.
        attrs.pop("notes")
    return attrs
