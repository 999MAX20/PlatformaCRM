from django.conf import settings
from django.db import transaction
from django.db.models import F
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.core.file_scanning import FileQuarantined, open_clean_attachment
from apps.core.domain_errors import InvalidTransition
from .audit import write_patient_audit
from .file_access import medical_file_context
from .file_content import read_file_metadata
from .file_policy import FILE_TYPES
from .file_services import medical_file_upload_target, assert_file_metadata_editable
from .identity_crypto import MedicalDataUnavailable
from .models import FDI_TOOTH_NUMBERS, MedicalAttachmentRevision, DentalMedicalRecord, MedicalEncounter


@transaction.atomic
def medical_file_workspace_access(*, actor, business_id, patient_id, record_id=None, encounter_id=None, **basis):
    context = medical_file_context(actor=actor, business_id=business_id, patient_id=patient_id, **basis)
    if context.correction is not None:
        if encounter_id is not None and encounter_id != context.correction.encounter_id:
            raise PermissionDenied()
        encounter_id = context.correction.encounter_id
    records = DentalMedicalRecord.objects.filter(business=context.business, patient=context.patient)
    if encounter_id is not None:
        encounters = MedicalEncounter.objects.filter(business=context.business, patient=context.patient)
        if context.head_scope:
            encounters = encounters.filter(branch=context.branch)
        encounter = encounters.filter(pk=encounter_id).first()
        if encounter is None or (record_id is not None and record_id != encounter.record_id):
            raise PermissionDenied()
        record_id = encounter.record_id
    record = records.filter(pk=record_id).first() if record_id is not None else records.filter(state="active").first()
    if record_id is not None and record is None:
        raise PermissionDenied()
    record_id = record.pk if record else None
    can_upload = False
    try:
        writer = medical_file_context(actor=actor, business_id=business_id, patient_id=patient_id,
                                      action="create", **basis)
        if record is not None:
            record, _ = medical_file_upload_target(actor=actor, context=writer,
                                                   record_id=record_id, encounter_id=encounter_id)
            can_upload = record.state == "active"
    except (PermissionDenied, InvalidTransition):
        pass
    can_export = False
    try:
        medical_file_context(actor=actor, business_id=business_id, patient_id=patient_id, action="export", **basis)
        can_export = True
    except PermissionDenied:
        pass
    write_patient_audit(actor=actor, business=context.business, patient=context.patient,
                        action="read", correction_access=context.correction)
    return {"patient_revision": context.patient.revision, "actor_id": actor.pk,
            "record_id": record_id, "encounter_id": encounter_id,
            "actions": {"upload": can_upload, "export": can_export},
            "allowed_extensions": list(FILE_TYPES), "max_bytes": settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024}


def versions_query():
    return MedicalAttachmentRevision.objects.select_related("author", "medical_file__patient__client",
        "medical_file__record", "medical_file__branch", "medical_file__encounter", "medical_file__attachment"
    ).prefetch_related("tooth_links")


def file_payload(version):
    item, blob = version.medical_file, version.medical_file.attachment
    metadata = read_file_metadata(version)
    return {"id": item.pk, "version_id": version.pk, "revision": version.revision,
        "record_id": item.record_id, "encounter_id": item.encounter_id,
        "branch_id": item.branch_id, "branch_name": item.branch.name,
        "author_name": version.author.full_name or version.author.username,
        "created_at": version.created_at, "name": metadata["name"], "description": metadata["description"],
        "teeth": metadata["teeth"], "reason": metadata["reason"], "size": blob.size,
        "content_type": blob.content_type, "scan_status": blob.scan_status}


@transaction.atomic
def list_medical_files(*, actor, business_id, patient_id, before_id=None, limit=20,
                       tooth=None, encounter_id=None, **basis):
    if type(limit) is not int or not 1 <= limit <= 50:
        raise ValidationError({"limit": "Select a limit from 1 to 50."})
    for value in (before_id, encounter_id):
        if value is not None and (type(value) is not int or value <= 0):
            raise ValidationError({"filter": "Provide positive file filter identifiers."})
    if tooth is not None and (type(tooth) is not int or tooth not in FDI_TOOTH_NUMBERS):
        raise ValidationError({"tooth": "Select a supported FDI tooth number."})
    context = medical_file_context(actor=actor, business_id=business_id, patient_id=patient_id, **basis)
    query = context.files()
    if encounter_id is not None:
        query = query.filter(encounter_id=encounter_id)
    if tooth is not None:
        query = query.filter(versions__revision=F("revision"), versions__tooth_links__tooth=tooth)
    if before_id is not None:
        query = query.filter(pk__lt=before_id)
    page = list(query.order_by("-pk")[:limit + 1])
    versions = {row.medical_file_id: row for row in versions_query().filter(
        medical_file_id__in=[item.pk for item in page[:limit]], revision=F("medical_file__revision"))}
    rows = []
    for item in page[:limit]:
        version = versions.get(item.pk)
        if version is None:
            raise MedicalDataUnavailable()
        write_patient_audit(actor=actor, business=context.business, patient=context.patient, action="read",
                            file_version=version, correction_access=context.correction)
        rows.append(file_payload(version))
    if not rows:
        write_patient_audit(actor=actor, business=context.business, patient=context.patient, action="read",
                            correction_access=context.correction)
    return {"results": rows, "next_before_id": page[limit - 1].pk if len(page) > limit else None}


def read_medical_file_version(*, actor, business_id, patient_id, file_id, version_id=None,
                              download=False, preview=False, **basis):
    if type(file_id) is not int or file_id <= 0 or (version_id is not None and
            (type(version_id) is not int or version_id <= 0)) or (download and preview):
        raise ValidationError({"file": "Select one valid file operation and version."})
    source = None
    try:
        with transaction.atomic():
            context = medical_file_context(actor=actor, business_id=business_id, patient_id=patient_id,
                                            action="export" if download else "view", **basis)
            item = context.files().filter(pk=file_id).first()
            if item is None:
                raise PermissionDenied()
            version = versions_query().filter(medical_file=item,
                **({"pk": version_id} if version_id is not None else {"revision": item.revision})).first()
            if version is None:
                raise PermissionDenied()
            payload = file_payload(version)
            if not download and not preview:
                can_edit = False
                if version.revision == item.revision:
                    try:
                        writer = medical_file_context(actor=actor, business_id=business_id, patient_id=patient_id,
                                                      action="create", **basis)
                        assert_file_metadata_editable(actor=actor, context=writer, item=version.medical_file)
                        can_edit = True
                    except (PermissionDenied, InvalidTransition):
                        pass
                payload["actions"] = {"edit_metadata": can_edit}
            quarantined = False
            if download or preview:
                try:
                    source = open_clean_attachment(version.medical_file.attachment, memory_only=True)
                except FileQuarantined:
                    # Commit the scanner's integrity quarantine before returning its denial.
                    quarantined = True
            if not quarantined:
                write_patient_audit(actor=actor, business=context.business, patient=context.patient,
                    action="file_downloaded" if download else "read", file_version=version, correction_access=context.correction)
        if quarantined:
            raise FileQuarantined()
        return payload, source
    except Exception:
        if source is not None:
            source.close()
        raise


@transaction.atomic
def list_medical_file_history(*, actor, business_id, patient_id, file_id,
                              before_revision=None, limit=20, **basis):
    if type(limit) is not int or not 1 <= limit <= 50 or type(file_id) is not int or file_id <= 0:
        raise ValidationError({"file": "Provide a valid file and page size."})
    if before_revision is not None and (type(before_revision) is not int or before_revision <= 0):
        raise ValidationError({"before_revision": "Provide a positive revision."})
    context = medical_file_context(actor=actor, business_id=business_id, patient_id=patient_id, **basis)
    item = context.files().filter(pk=file_id).first()
    if item is None:
        raise PermissionDenied()
    query = versions_query().filter(medical_file=item)
    if before_revision is not None:
        query = query.filter(revision__lt=before_revision)
    page = list(query.order_by("-revision")[:limit + 1])
    rows = []
    for version in page[:limit]:
        write_patient_audit(actor=actor, business=context.business, patient=context.patient,
            action="read", file_version=version, correction_access=context.correction)
        rows.append(file_payload(version))
    if not rows:
        write_patient_audit(actor=actor, business=context.business, patient=context.patient,
            action="read", correction_access=context.correction)
    return {"results": rows, "next_before_revision": page[limit - 1].revision if len(page) > limit else None}
