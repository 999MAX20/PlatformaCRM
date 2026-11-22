import json
import re

from django.conf import settings
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.core.domain_errors import DomainAPIException, InvalidTransition


class IdentityVerificationUnavailable(DomainAPIException):
    status_code = 503
    error_code = "identity_verification_unavailable"
    default_code = error_code
    default_detail = "The clinic identity verification protocol is not configured."
    category = "configuration"


_CODE = re.compile(r"[a-z][a-z0-9_]{0,63}")


def _localized_label(value):
    if (not isinstance(value, dict) or set(value) != {"ru", "kk", "en"} or
            any(not isinstance(label, str) or not label.strip() or len(label) > 300 for label in value.values())):
        raise ValueError


def _verification_policy(business_id, *, setting_name="MEDICAL_IDENTITY_VERIFICATION_POLICIES", extra_keys=frozenset(), optional_keys=frozenset()):
    try:
        policies = getattr(settings, setting_name)
        if isinstance(policies, str):
            policies = json.loads(policies)
        policy = policies[str(business_id)]
        required = {"reference", "approval_reference", "methods", "trained_member_ids"} | set(extra_keys)
        if not isinstance(policy, dict) or not required <= set(policy) or set(policy) - required - set(optional_keys):
            raise ValueError
        for key in ("reference", "approval_reference"):
            if not isinstance(policy[key], str) or not policy[key].strip() or len(policy[key]) > 200:
                raise ValueError
        members = policy["trained_member_ids"]
        if not isinstance(members, list) or any(type(pk) is not int or pk <= 0 for pk in members):
            raise ValueError
        methods = policy["methods"]
        if not isinstance(methods, dict) or not methods:
            raise ValueError
        for code, schema in methods.items():
            if not isinstance(code, str) or not _CODE.fullmatch(code):
                raise ValueError
            if (not isinstance(schema, dict) or
                    not {"required_fields", "optional_fields"} <= set(schema) or
                    set(schema) - {"required_fields", "optional_fields", "label", "field_labels"}):
                raise ValueError
            all_fields = []
            for key in ("required_fields", "optional_fields"):
                names = schema[key]
                if not isinstance(names, list) or any(not isinstance(name, str) or not _CODE.fullmatch(name) for name in names):
                    raise ValueError
                all_fields.extend(names)
            if len(all_fields) > 30 or len(set(all_fields)) != len(all_fields):
                raise ValueError
            if "label" in schema or "field_labels" in schema:
                _localized_label(schema.get("label"))
                labels = schema.get("field_labels")
                if not isinstance(labels, dict) or set(labels) != set(all_fields):
                    raise ValueError
                for label in labels.values():
                    _localized_label(label)
    except (AttributeError, KeyError, TypeError, ValueError):
        raise IdentityVerificationUnavailable() from None
    return policy


def _assert_training(policy, member_id):
    if member_id not in policy["trained_member_ids"]:
        raise PermissionDenied("Identity verification requires current training authorization.")


def verification_form(*, business_id, member_id):
    policy = _verification_policy(business_id)
    _assert_training(policy, member_id)
    return _form(policy)


def _form(policy):
    methods = []
    for code, schema in policy["methods"].items():
        if "label" not in schema or "field_labels" not in schema:
            raise IdentityVerificationUnavailable()
        methods.append({"code": code, "label": dict(schema["label"]), "fields": [
            {"code": name, "label": dict(schema["field_labels"][name]), "required": required, "max_length": 2000}
            for key, required in (("required_fields", True), ("optional_fields", False))
            for name in schema[key]
        ]})
    return {"reference": policy["reference"], "methods": methods}


def verification_evidence(*, business_id, member_id, protocol_reference, method, fields):
    """Validate against an externally approved clinic protocol, never a built-in document list."""
    policy = _verification_policy(business_id)
    return _evidence(policy, member_id=member_id, protocol_reference=protocol_reference, method=method, fields=fields)


def _evidence(policy, *, member_id, protocol_reference, method, fields):
    _assert_training(policy, member_id)
    methods = policy["methods"]
    if protocol_reference != policy["reference"]:
        raise InvalidTransition("The verification protocol changed; reload before verifying identity.")
    if not isinstance(method, str) or method not in methods:
        raise ValidationError({"method": "Select a method from the clinic protocol."})
    schema = methods[method]
    if not isinstance(fields, dict) or set(fields) - set(schema["required_fields"] + schema["optional_fields"]):
        raise ValidationError({"evidence": "Provide only the fields required by the clinic protocol."})
    if any(name not in fields or not isinstance(fields[name], str) or not fields[name].strip()
           for name in schema["required_fields"]):
        raise ValidationError({"evidence": "Complete the required verification fields."})
    if any(not isinstance(value, str) or len(value) > 2000 for value in fields.values()):
        raise ValidationError({"evidence": "Invalid verification field."})
    return {"protocol_reference": policy["reference"], "approval_reference": policy["approval_reference"],
            "method": method, "fields": dict(fields)}
