from rest_framework.exceptions import ValidationError

from .identity_policy import (IdentityVerificationUnavailable, _CODE, _assert_training, _evidence,
                              _form, _localized_label, _verification_policy)


def _policy(business_id):
    policy = _verification_policy(business_id, setting_name="MEDICAL_REPRESENTATIVE_POLICIES",
                                  extra_keys={"permissions", "requires_expiry"}, optional_keys={"permission_labels"})
    allowed = policy["permissions"]
    if (not isinstance(allowed, list) or not allowed or len(allowed) > 30 or
            any(not isinstance(code, str) or not _CODE.fullmatch(code) for code in allowed) or
            len(set(allowed)) != len(allowed) or type(policy["requires_expiry"]) is not bool):
        raise IdentityVerificationUnavailable()
    if "permission_labels" in policy:
        try:
            labels = policy["permission_labels"]
            if not isinstance(labels, dict) or set(labels) != set(allowed):
                raise ValueError
            for label in labels.values():
                _localized_label(label)
        except (TypeError, ValueError):
            raise IdentityVerificationUnavailable() from None
    return policy


def representative_form(*, business_id, member_id):
    policy = _policy(business_id)
    _assert_training(policy, member_id)
    if "permission_labels" not in policy:
        raise IdentityVerificationUnavailable()
    return {**_form(policy), "requires_expiry": policy["requires_expiry"], "permissions": [
        {"code": code, "label": dict(policy["permission_labels"][code])} for code in policy["permissions"]]}


def representative_evidence(*, business_id, member_id, protocol_reference, method, fields, permissions, valid_until):
    policy = _policy(business_id)
    allowed = policy["permissions"]
    evidence = _evidence(policy, member_id=member_id, protocol_reference=protocol_reference, method=method, fields=fields)
    if (not isinstance(permissions, list) or not permissions or
            any(not isinstance(code, str) or code not in allowed for code in permissions) or
            len(set(permissions)) != len(permissions)):
        raise ValidationError({"permissions": "Select explicit permissions from the representation protocol."})
    if policy["requires_expiry"] and valid_until is None:
        raise ValidationError({"valid_until": "The representation protocol requires an expiry date."})
    labels = policy.get("permission_labels")
    return {**evidence, "permissions": sorted(permissions),
            "permission_labels": {code: dict(labels[code]) for code in permissions} if labels else None}
