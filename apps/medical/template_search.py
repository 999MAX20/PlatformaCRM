import unicodedata

from rest_framework.exceptions import ValidationError


def _text(value):
    return unicodedata.normalize("NFKC", value).strip().casefold()


def template_search_filters(*, q="", language="", category="", specialty="", service_id=None):
    for value in (q, category, specialty):
        if not isinstance(value, str) or len(value) > 255:
            raise ValidationError({"search": "Provide search text of at most 255 characters."})
    if language not in ("", "ru", "kk", "en"):
        raise ValidationError({"language": "Select a supported template language."})
    if service_id is not None and (type(service_id) is not int or service_id <= 0):
        raise ValidationError({"service_id": "Select a valid service identifier."})
    return {"q": _text(q), "language": language, "category": _text(category),
            "specialty": _text(specialty), "service_id": service_id}


def _matches(payload, filters):
    metadata = payload.get("metadata", {"language": "", "category": "", "specialty": "", "services": []})
    if filters["language"] and metadata["language"] != filters["language"]:
        return False
    if any(filters[field] and filters[field] not in _text(metadata[field]) for field in ("category", "specialty")):
        return False
    if filters["service_id"] is not None and all(item["id"] != filters["service_id"] for item in metadata["services"]):
        return False
    values = [payload["template"]["title"], metadata["category"], metadata["specialty"],
              *[item["name"] for item in metadata["services"]]]
    return not filters["q"] or any(filters["q"] in _text(value) for value in values)


def search_template_page(*, actor, business, versions, filters, before_id, limit):
    """Search authorized versions only; retain encrypted storage and audit each decrypted candidate."""
    from .template_services import read_template_version_payload

    if before_id is not None and (type(before_id) is not int or before_id <= 0):
        raise ValidationError({"before_id": "Provide a valid cursor."})
    if type(limit) is not int or not 1 <= limit <= 50:
        raise ValidationError({"limit": "Select a page size from 1 to 50."})
    rows = []
    cursor = before_id
    while True:
        candidates = versions.filter(template_id__lt=cursor) if cursor is not None else versions
        batch = list(candidates.order_by("-template_id")[:50])
        if not batch:
            return {"results": rows, "next_before_id": None}
        for version in batch:
            payload = read_template_version_payload(actor=actor, business=business, version=version)
            if not _matches(payload, filters):
                continue
            if len(rows) == limit:
                return {"results": rows, "next_before_id": rows[-1]["template_id"]}
            rows.append({"template_id": version.template_id, "version_id": version.pk,
                "revision": version.revision, "current_revision": version.template.revision,
                "title": payload["template"]["title"], "created_at": version.created_at,
                "review": payload["review"], "availability": payload["availability"],
                **({"metadata": payload["metadata"]} if "metadata" in payload else {})})
        if len(batch) < 50:
            return {"results": rows, "next_before_id": None}
        cursor = batch[-1].template_id
