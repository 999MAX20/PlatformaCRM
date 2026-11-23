"""Build print input from an authorized, decrypted document revision only."""

from datetime import datetime
from zoneinfo import ZoneInfo

from .document_pdf import DraftPrintData, DocumentRenderUnavailable


LABELS = {
    "ru": ("БИН", "Лицензия", "Пациент", "ИИН", "Медицинская карта", "Врач", "Подготовил", "Версия"),
    "kk": ("БСН", "Лицензия", "Пациент", "ЖСН", "Медициналық карта", "Дәрігер", "Дайындаған", "Нұсқа"),
    "en": ("Business ID", "License", "Patient", "IIN", "Medical record", "Doctor", "Prepared by", "Revision"),
}


def _text(value):
    if not isinstance(value, str):
        raise ValueError
    return value


def draft_print_snapshot(*, snapshot, revision, created_at, language, captured_logo=None):
    """No live models or URLs. Caller must bind captured logo bytes to this revision."""
    try:
        if type(revision) is not int or revision < 1 or language not in LABELS:
            raise ValueError
        if not isinstance(created_at, datetime) or created_at.utcoffset() is None:
            raise ValueError
        tax, license_label, patient_label, iin_label, record_label, doctor_label, author_label, version_label = LABELS[language]
        business = snapshot["business"]
        branch = snapshot["branch"]
        patient = snapshot["patient_identity"]
        source = snapshot["encounter_source"]
        credentials = snapshot["medical_credentials"]
        clinic_credentials = credentials["clinic"]
        doctor_credentials = credentials["clinician"]
        logo_url = _text(business["brand_logo_url"])
        # Omitting a configured logo would silently change the saved print identity.
        if logo_url and captured_logo is None:
            raise ValueError
        if captured_logo is not None and (not logo_url or not isinstance(captured_logo, bytes)):
            raise ValueError
        clinic = []

        def add(lines, value, label=None):
            value = _text(value)
            if value.strip():
                lines.append(f"{label}: {value}" if label else value)

        name = _text(business["name"])
        legal_name = _text(business["legal_name"])
        add(clinic, legal_name or name)
        if legal_name and name != legal_name:
            add(clinic, name)
        add(clinic, business["tax_id"], tax)
        if clinic_credentials is not None:
            add(clinic, clinic_credentials["content"]["license"], license_label)
        add(clinic, business["address"])
        add(clinic, business["phone"])
        add(clinic, branch["name"])
        add(clinic, branch["address"])
        add(clinic, branch["phone"])
        identity = []
        add(identity, patient["full_name"], patient_label)
        if patient["iin"] is not None:
            add(identity, patient["iin"], iin_label)
        add(identity, source["record_number"], record_label)
        add(identity, snapshot["performed_by"]["name"], doctor_label)
        if doctor_credentials is not None:
            content = doctor_credentials["content"]
            add(identity, ", ".join(_text(content[key]) for key in ("specialty", "position", "qualification") if content[key]))
        add(identity, snapshot["prepared_by"]["name"], author_label)
        local = created_at.astimezone(ZoneInfo(source["timezone"]))
        identity.append(f"{version_label}: {revision} / {local.isoformat(timespec='seconds')}")
        return DraftPrintData(title=_text(snapshot["template"]["title"]),
            text=_text(snapshot["document_text"]), clinic_lines=tuple(clinic), identity_lines=tuple(identity),
            created_at=created_at, language=language, logo=captured_logo)
    except (KeyError, TypeError, ValueError):
        # Missing legacy data must not be reconstructed from today's patient or clinic.
        raise DocumentRenderUnavailable() from None
