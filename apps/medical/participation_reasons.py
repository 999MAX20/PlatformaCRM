import json

from .identity_crypto import MedicalDataUnavailable, decrypt_medical_value


def work_direction_for_reader(item):
    if not item.work_direction_encrypted:
        return None
    try:
        value = json.loads(decrypt_medical_value(item.work_direction_encrypted,
            business_id=item.patient.business_id, subject_id=item.pk, purpose="participation_work_direction"))
        if (not isinstance(value, dict) or set(value) != {"work_direction"}
                or not isinstance(value["work_direction"], str) or not value["work_direction"].strip()
                or len(value["work_direction"]) > 2000):
            raise ValueError
        return value["work_direction"]
    except (ValueError, TypeError):
        raise MedicalDataUnavailable() from None


def decline_reason_for_initiator(item, actor):
    if item.state != "declined" or item.proposed_by_id != actor.pk or not item.decline_reason_encrypted:
        return None
    try:
        value = json.loads(decrypt_medical_value(item.decline_reason_encrypted,
            business_id=item.patient.business_id, subject_id=item.pk, purpose="participation_decline"))
        if (not isinstance(value, dict) or set(value) != {"reason", "revision"}
                or type(value["revision"]) is not int or value["revision"] != item.revision
                or not isinstance(value["reason"], str) or not value["reason"].strip()
                or len(value["reason"]) > 2000):
            raise ValueError
        return value["reason"]
    except (ValueError, TypeError):
        raise MedicalDataUnavailable() from None
