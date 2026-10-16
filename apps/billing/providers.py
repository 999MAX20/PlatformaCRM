"""Provider contract only: no unselected bank, default gateway or public fake mode.

An accepted adapter must use bounded timeouts, provider idempotency keyed by the
attempt UUID, authenticated notifications and server status queries. It must never
log/return raw payloads or credentials. Checkout URLs must be HTTPS on its allowlist.
Deployment registers an adapter instance in BILLING_CARD_ADAPTER after certification.
"""
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Protocol
from uuid import UUID
from urllib.parse import urlparse
from django.conf import settings
from apps.billing.commerce import CommerceUnavailable


@dataclass(frozen=True)
class Checkout:
    external_id: str
    url: str


@dataclass(frozen=True)
class PaymentResult:
    attempt_id: UUID
    order_id: UUID
    reference: str
    amount: Decimal
    currency: str
    status: str  # pending/failed/confirmed/refunded/disputed, not an AUTH hold
    received_at: datetime


class CardAdapter(Protocol):
    key: str
    merchant: str
    checkout_hosts: frozenset[str]

    def create_checkout(self, *, attempt_id: UUID, order_id: UUID, amount: Decimal, currency: str) -> Checkout: ...
    def lookup(self, *, attempt_id: UUID) -> PaymentResult: ...
    def authenticate_notification(self, *, body: bytes, headers: dict) -> UUID: ...


def adapter():
    instance = getattr(settings, "BILLING_CARD_ADAPTER", None)
    if instance is None:
        raise CommerceUnavailable()
    if not instance.key or instance.key == "bank" or not instance.merchant:
        raise CommerceUnavailable()
    return instance


def safe_checkout(value, gateway):
    url = urlparse(value.url)
    if (url.scheme != "https" or url.hostname not in gateway.checkout_hosts or url.username or url.password
            or url.port not in {None, 443} or not value.external_id or len(value.external_id) > 128 or len(value.url) > 2048):
        raise CommerceUnavailable()
    return value
