"""Operator opt-in for the confirmed +7 trunk-prefix bug in Meta's test list."""
import re

from django.conf import settings

from apps.integrations.providers.base import ProviderConfigurationError


def meta_test_recipient(phone_number_id, recipient_id):
    aliases = getattr(settings, "WHATSAPP_META_TEST_RECIPIENT_ALIASES", {})
    if not isinstance(aliases, dict):
        raise ProviderConfigurationError("Meta test recipient aliases must be an object.")
    sender_aliases = aliases.get(str(phone_number_id), {})
    if not isinstance(sender_aliases, dict):
        raise ProviderConfigurationError("Meta test sender aliases must be an object.")
    if recipient_id not in sender_aliases:
        return recipient_id
    alias = sender_aliases[recipient_id]
    if not re.fullmatch(r"7[67][0-9]{9}", recipient_id) or alias != "78" + recipient_id[1:]:
        raise ProviderConfigurationError("Meta test alias must preserve the verified recipient number.")
    return alias
