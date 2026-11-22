import json
import re

from django.conf import settings
from rest_framework.exceptions import ValidationError
from apps.core.domain_errors import DomainAPIException, InvalidTransition
from .models import FDI_TOOTH_NUMBERS


class ToothNotationUnavailable(DomainAPIException):
    status_code = 503
    error_code = "tooth_notation_unavailable"
    default_code = error_code
    default_detail = "The approved tooth surface vocabulary is not configured."
    category = "configuration"


def surface_evidence(*, business_id, tooth, surface, reference):
    if not isinstance(surface, str) or (surface and not re.fullmatch(r"[a-z][a-z0-9_]{0,31}", surface)):
        raise ValidationError({"surface": "Provide a valid surface identifier."})
    if not isinstance(reference, str) or len(reference) > 200:
        raise ValidationError({"surface_reference": "Provide the current vocabulary reference."})
    if not surface:
        if reference:
            raise ValidationError({"surface_reference": "Whole-tooth observations do not select a surface vocabulary."})
        return None
    policy = configured_surface_policy(business_id)
    if policy is None:
        raise ToothNotationUnavailable()
    teeth = policy["teeth"]
    if reference != policy["reference"]:
        raise InvalidTransition("The surface vocabulary changed; reload before saving.")
    if surface not in teeth.get(str(tooth), []):
        raise ValidationError({"surface": "Select a configured surface for this tooth."})
    return {field: policy[field] for field in ("reference", "approval_reference")}


def configured_surface_policy(business_id):
    try:
        policies = settings.MEDICAL_TOOTH_SURFACE_POLICIES
        if policies == "":
            return None
        if isinstance(policies, str):
            policies = json.loads(policies)
        if not isinstance(policies, dict):
            raise ValueError
        if str(business_id) not in policies:
            return None
        policy = policies[str(business_id)]
        if not isinstance(policy, dict) or not {"reference", "approval_reference", "teeth"} <= set(policy) or set(policy) - {"reference", "approval_reference", "teeth", "labels"}:
            raise ValueError
        for field in ("reference", "approval_reference"):
            if not isinstance(policy[field], str) or not policy[field].strip() or len(policy[field]) > 200:
                raise ValueError
        teeth = policy["teeth"]
        if not isinstance(teeth, dict) or not teeth:
            raise ValueError
        for number, codes in teeth.items():
            if number not in {str(value) for value in FDI_TOOTH_NUMBERS} or not isinstance(codes, list) or not codes:
                raise ValueError
            if any(not isinstance(code, str) or not re.fullmatch(r"[a-z][a-z0-9_]{0,31}", code) for code in codes):
                raise ValueError
            if len(codes) != len(set(codes)):
                raise ValueError
        if "labels" in policy:
            labels = policy["labels"]
            codes = {code for values in teeth.values() for code in values}
            if not isinstance(labels, dict) or set(labels) != codes:
                raise ValueError
            for translations in labels.values():
                if not isinstance(translations, dict) or set(translations) != {"ru", "kk", "en"}:
                    raise ValueError
                if any(not isinstance(text, str) or not text.strip() or len(text) > 200 for text in translations.values()):
                    raise ValueError
    except (AttributeError, KeyError, TypeError, ValueError):
        raise ToothNotationUnavailable() from None
    return policy
