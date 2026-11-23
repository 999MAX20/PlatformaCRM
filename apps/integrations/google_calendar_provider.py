"""Bounded Google Calendar transport; no CRM writes or stored event descriptions."""
from datetime import datetime, time
from urllib.parse import quote, urlencode
from zoneinfo import ZoneInfo

from django.utils.dateparse import parse_date, parse_datetime
from rest_framework.exceptions import ValidationError

from apps.integrations.google_http import GoogleError, google_request


BASE = "https://www.googleapis.com/calendar/v3"
MAX_PAGES = 20


def calendar_path(calendar_id):
    if not isinstance(calendar_id, str) or not calendar_id or len(calendar_id) > 1024:
        raise ValidationError("Select an existing Google calendar.")
    return BASE + "/calendars/" + quote(calendar_id, safe="")


def pages(url, token, params):
    seen = set()
    for _ in range(MAX_PAGES):
        result = google_request(url + "?" + urlencode(params), token=token)
        items = result.get("items", [])
        if not isinstance(items, list) or any(not isinstance(item, dict) for item in items):
            raise GoogleError()
        yield from items
        next_page = result.get("nextPageToken")
        if not next_page:
            return
        if not isinstance(next_page, str) or next_page in seen:
            raise GoogleError()
        seen.add(next_page)
        params = {**params, "pageToken": next_page}
    # Never treat an incomplete snapshot as proof that a specialist is free.
    raise GoogleError()


def calendars(token):
    return [item for item in pages(BASE + "/users/me/calendarList", token, {
        "maxResults": 250, "minAccessRole": "writer",
        "fields": "nextPageToken,items(id,summary,timeZone,accessRole,deleted)",
    }) if not item.get("deleted") and item.get("accessRole") in {"owner", "writer"}]


def calendar_info(token, calendar_id):
    item = google_request(BASE + "/users/me/calendarList/" + quote(calendar_id, safe=""), token=token)
    if item.get("deleted") or item.get("accessRole") not in {"owner", "writer"}:
        raise ValidationError("Google calendar write access is required. Reconnect or choose another calendar.")
    try:
        ZoneInfo(item["timeZone"])
    except (KeyError, ValueError, TypeError):
        raise GoogleError() from None
    return item


def events(token, calendar_id, start, end):
    return list(pages(calendar_path(calendar_id) + "/events", token, {
        "timeMin": start.isoformat(), "timeMax": end.isoformat(),
        "singleEvents": "true", "showDeleted": "false", "maxResults": 2500,
        "fields": "nextPageToken,items(id,etag,status,transparency,start,end,extendedProperties,attendees(self,responseStatus))",
    }))


def event_interval(event, zone):
    if event.get("status") == "cancelled" or event.get("transparency") == "transparent":
        return None
    if any(person.get("self") and person.get("responseStatus") == "declined"
           for person in event.get("attendees", [])):
        return None
    endpoints = []
    try:
        for key in ("start", "end"):
            value = event[key]
            if "dateTime" in value:
                instant = parse_datetime(value["dateTime"])
                if instant is None or instant.tzinfo is None:
                    raise ValueError()
            else:
                day = parse_date(value["date"])
                instant = datetime.combine(day, time.min, ZoneInfo(zone))
            endpoints.append(instant)
        if endpoints[0] >= endpoints[1]:
            raise ValueError()
    except (KeyError, TypeError, ValueError):
        raise GoogleError() from None
    return tuple(endpoints)


def get_event(token, calendar_id, event_id):
    try:
        return google_request(calendar_path(calendar_id) + "/events/" + quote(event_id, safe=""), token=token)
    except GoogleError as exc:
        if exc.remote_status == 410:
            return {"id": event_id, "status": "cancelled"}
        if exc.remote_status == 404:
            return None
        raise


def write_event(token, calendar_id, event_id, payload, existing=None):
    url = calendar_path(calendar_id) + "/events"
    if existing:
        if not existing.get("etag"):
            raise GoogleError()
        return google_request(url + "/" + quote(event_id, safe="") + "?sendUpdates=none",
            token=token, method="PUT", payload=payload, if_match=existing["etag"])
    return google_request(url + "?sendUpdates=none", token=token, method="POST",
                          payload={**payload, "id": event_id})


def delete_event(token, calendar_id, event_id, existing):
    if not existing.get("etag"):
        raise GoogleError()
    try:
        google_request(calendar_path(calendar_id) + "/events/" + quote(event_id, safe="") + "?sendUpdates=none",
                       token=token, method="DELETE", if_match=existing["etag"])
    except GoogleError as exc:
        if exc.remote_status not in {404, 410}:
            raise
