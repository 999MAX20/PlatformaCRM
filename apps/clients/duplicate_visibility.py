"""Read projection for duplicate warnings; matching and write policy stay separate."""
import re

from apps.businesses.access import Resources
from apps.clients.models import Client
from apps.core.crm_read_scope import readable_queryset


def _client_id(value):
    if isinstance(value, bool) or not isinstance(value, (str, int)):
        return None
    if isinstance(value, str) and not value.isdecimal():
        return None
    try:
        value = int(value)
    except (ValueError, OverflowError):
        return None
    return value if 0 < value <= 2**63 - 1 else None


def readable_duplicate_ids(ids, *, actor, business):
    if actor is None:
        return set()
    ids = {pk for value in ids if (pk := _client_id(value)) is not None}
    return set(readable_queryset(Client.objects.filter(pk__in=ids), actor=actor,
                                 business=business, resource=Resources.CLIENTS).values_list("pk", flat=True))


def project_duplicate_rows(rows, *, actor, business):
    """Keep a warning for hidden matches without an identity or actionable Client ID.

    Call on every read, including stored import snapshots after policy changes.
    One restricted marker preserves duplicate confirmation without exposing how many
    inaccessible Client records matched. Never mutate the stored/input rows.
    """
    rows = list(rows or [])
    allowed = readable_duplicate_ids((row.get("id") for row in rows if isinstance(row, dict)),
                                     actor=actor, business=business)
    result = []
    restricted = False
    for row in rows:
        if not isinstance(row, dict):
            restricted = True
            continue
        pk = _client_id(row.get("id"))
        if pk in allowed:
            result.append({"id": pk, **{key: row.get(key, [] if key == "matched_fields" else "")
                                       for key in ("full_name", "phone", "email", "matched_fields")}})
        elif (row.get("id") == "" and row.get("matched_fields") == ["file_row"]
              and re.fullmatch(r"Duplicate row [1-9]\d*", str(row.get("full_name", "")))
              and not row.get("phone") and not row.get("email")):
            # Existing preview marker derives only from rows in the uploaded file.
            result.append({"id": "", "full_name": row["full_name"], "matched_fields": ["file_row"]})
        else:
            restricted = True
    if restricted:
        result.append({"id": None, "full_name": "", "phone": "", "email": "", "matched_fields": []})
    return result
