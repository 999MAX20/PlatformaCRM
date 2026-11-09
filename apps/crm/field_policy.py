"""Deal projections use the existing sensitive-field policy, with explicit actors."""
from rest_framework.exceptions import PermissionDenied

from apps.businesses.access import Resources, can_view_sensitive_field
from apps.businesses.models import Business


def deal_amount_visible(actor, business):
    return bool(actor and getattr(actor, "is_authenticated", False)
                and can_view_sensitive_field(actor, business, Resources.DEALS, "amount"))


def queryset_amount_visible(queryset, actor):
    if not actor or not getattr(actor, "is_authenticated", False):
        return False
    businesses = Business.objects.filter(pk__in=queryset.order_by().values("business_id"))
    return all(deal_amount_visible(actor, business) for business in businesses)


def assert_amount_query_visible(queryset, actor, params):
    monetary_query = any(params.get(key) not in (None, "") for key in ("amount_min", "amount_max", "min", "max"))
    monetary_query |= params.get("ordering") in {"amount", "-amount"}
    if monetary_query and not queryset_amount_visible(queryset, actor):
        raise PermissionDenied("Deal amounts are not available.")


def redact_amount_metadata(value):
    """Remove structured monetary copies without changing stored history."""
    if isinstance(value, list):
        return [redact_amount_metadata(item) for item in value]
    if isinstance(value, dict):
        return {key: redact_amount_metadata(item) for key, item in value.items()
                if not _money_key(key)}
    return value


def _money_key(key):
    key = str(key).casefold()
    return (key in {"amount", "currency", "pipeline_value", "expected_revenue", "open_value", "won_value", "lost_value"}
            or key.startswith(("amount_", "currency_")) or key.endswith(("_amount", "_currency")))
