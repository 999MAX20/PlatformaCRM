"""Shared platform diagnostics; setup attention is distinct from a failure."""
from apps.integrations.models import BusinessConnector


CONNECTOR_FAILURES = (
    BusinessConnector.Statuses.ERROR,
    BusinessConnector.Statuses.FAILED,
    BusinessConnector.Statuses.EXPIRED_CREDENTIALS,
)
CONNECTOR_SETUP = (BusinessConnector.Statuses.NEEDS_ATTENTION,)
CONNECTOR_ATTENTION = (*CONNECTOR_FAILURES, *CONNECTOR_SETUP)
