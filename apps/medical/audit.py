from django.core.exceptions import ValidationError as ModelValidationError
from django.db import DatabaseError, transaction
from django.db.models import Q

from apps.core.domain_errors import DomainAPIException
from .models import DentalToothHistory, DentalMedicalRecord, MedicalAuditEvent, PatientProfile, PatientRepresentative, TreatmentParticipation, MedicalEncounterRevision
from .models import MedicalDocumentRevision, MedicalOrderRevision, PatientIdentityCorrection, MedicalCorrectionAccess, MedicalAttachmentRevision


class MedicalAuditUnavailable(DomainAPIException):
    status_code = 503
    error_code = "medical_audit_unavailable"
    default_code = error_code
    default_detail = "Medical audit is unavailable. The operation was not completed."
    category = "temporary"


def write_patient_audit(*, actor, business, patient, action, representative=None, participation=None, encounter_version=None, record=None, tooth_history=None, document_version=None, identity_correction=None, correction_access=None, order_version=None, file_version=None):
    if action not in MedicalAuditEvent.Actions.values or action == MedicalAuditEvent.Actions.ACCESS_DENIED:
        raise ValueError("Select a supported successful patient action.")
    if not patient.pk or not PatientProfile.objects.filter(pk=patient.pk, business_id=business.pk).exists():
        raise ValueError("Audit patient must belong to this business.")
    if action.startswith("correction_access_") and correction_access is None:
        raise ValueError("A correction access action requires its request.")
    if correction_access is not None:
        states = {"requested": "pending", "approved": "active", "rejected": "rejected", "withdrawn": "withdrawn",
                  "completed": "completed", "revoked": "revoked", "expired": "expired"}
        expected = states.get(action.removeprefix("correction_access_"))
        if not MedicalCorrectionAccess.objects.filter(pk=correction_access.pk, patient=patient,
                encounter__business=business, requester__business=business).exists():
            raise ValueError("Correction access must belong to the audited patient and business.")
        if expected is not None and correction_access.state != expected:
            raise ValueError("Correction access state must match its audit action.")
        if expected is None and action not in {"read", "encounter_draft_saved", "document_draft_saved",
                                               "file_uploaded", "file_metadata_updated", "file_downloaded",
                                               "document_exported", "document_print_requested"}:
            raise ValueError("Select a correction access read or draft update action.")
        if action in {"encounter_draft_saved", "document_draft_saved"} and correction_access.state != "active":
            raise ValueError("A correction write requires active access.")
        if any(item is not None for item in (representative, participation, record, tooth_history, identity_correction)):
            raise ValueError("Correction access audit cannot mix unrelated entities.")
        if encounter_version is not None and (correction_access.document_id is not None or
                encounter_version.encounter_id != correction_access.encounter_id):
            raise ValueError("Correction access does not authorize this encounter version.")
        if document_version is not None and document_version.document_id != correction_access.document_id:
            raise ValueError("Correction access does not authorize this document version.")
        if file_version is not None and (correction_access.document_id is not None or
                file_version.medical_file.encounter_id != correction_access.encounter_id or correction_access.state != "active"):
            raise ValueError("Correction access does not authorize this file version.")
    if action.startswith("identity_correction_") and identity_correction is None:
        raise ValueError("An identity correction action requires its correction.")
    if identity_correction is not None:
        expected_state = {"identity_correction_requested": "pending", "identity_correction_applied": "applied",
                          "identity_correction_rejected": "rejected"}.get(action)
        if any(item is not None for item in (representative, participation, encounter_version, record, tooth_history, document_version)):
            raise ValueError("Identity correction audit cannot mix entity references.")
        if not PatientIdentityCorrection.objects.filter(pk=identity_correction.pk, patient=patient,
                branch__business=business).exists() or (action != "read" and identity_correction.state != expected_state):
            raise ValueError("Audit identity correction must match the patient and action.")
    if representative is not None and not PatientRepresentative.objects.filter(
            pk=representative.pk, patient=patient, representative_client__business_id=business.pk).exists():
        raise ValueError("Audit representative must belong to this patient and business.")
    if action in {MedicalAuditEvent.Actions.REPRESENTATIVE_VERIFIED, MedicalAuditEvent.Actions.REPRESENTATIVE_REVOKED} and representative is None:
        raise ValueError("A representative action requires its representation.")
    if participation is not None:
        if representative is not None or not TreatmentParticipation.objects.filter(
                pk=participation.pk, patient=patient, patient__client__business_id=business.pk,
                member__business_id=business.pk, branch__business_id=business.pk).exists():
            raise ValueError("Audit participation must belong to this patient and business.")
    if action.startswith("participation_") and participation is None:
        raise ValueError("A participation action requires its participation.")
    if action == MedicalAuditEvent.Actions.PARTICIPATION_ENDED and not TreatmentParticipation.objects.filter(
            pk=participation.pk, state="ended", revision=participation.revision, closed_by=actor,
            ).filter(Q(remaining_responsible__business_id=business.pk) |
                     Q(remaining_responsible__isnull=True, member__user=actor)).exclude(closure_reason_encrypted="").exists():
        raise ValueError("A participation end event requires current closure and own completion or a responsible member.")
    if action.startswith("encounter_") and encounter_version is None:
        raise ValueError("An encounter action requires its clinical version.")
    if encounter_version is not None:
        version = MedicalEncounterRevision.objects.select_related("encounter").filter(
            pk=encounter_version.pk, encounter__business_id=business.pk, encounter__patient=patient).first()
        if version is None or representative is not None or participation is not None:
            raise ValueError("Audit clinical version must belong to this patient and business.")
        try:
            version.encounter.clean()
        except ModelValidationError:
            raise ValueError("Audit encounter links must be consistent.") from None
        if version.revision > version.encounter.revision:
            raise ValueError("Audit clinical version exceeds the encounter revision.")
        if action.startswith("encounter_") and (version.encounter.state != "draft" or version.revision != version.encounter.revision):
            raise ValueError("A draft write event requires the current draft version.")
    if action == MedicalAuditEvent.Actions.RECORD_OPENED and record is None:
        raise ValueError("A record action requires its medical record.")
    if record is not None:
        if any(item is not None for item in (representative, participation, encounter_version)) or not DentalMedicalRecord.objects.filter(
                pk=record.pk, business=business, patient=patient, patient__client__business_id=business.pk).exists():
            raise ValueError("Audit record must belong to this patient and business.")
    if action == MedicalAuditEvent.Actions.TOOTH_OBSERVATION_SAVED and tooth_history is None:
        raise ValueError("A tooth write action requires its observation version.")
    if tooth_history is not None:
        if any(item is not None for item in (representative, participation, encounter_version, record)):
            raise ValueError("Audit tooth history cannot be mixed with other entity references.")
        if action not in {MedicalAuditEvent.Actions.READ, MedicalAuditEvent.Actions.TOOTH_OBSERVATION_SAVED}:
            raise ValueError("Select a tooth observation read or write action.")
        history = DentalToothHistory.objects.select_related("tooth_state", "encounter").filter(
            pk=tooth_history.pk, tooth_state__business=business, tooth_state__patient=patient,
            encounter__business=business, encounter__patient=patient).first()
        if history is None:
            raise ValueError("Audit tooth history must belong to this patient and business.")
        try:
            history.full_clean()
        except ModelValidationError:
            raise ValueError("Audit tooth history links must be consistent.") from None
        if action == MedicalAuditEvent.Actions.TOOTH_OBSERVATION_SAVED and (
                history.revision != history.tooth_state.revision or history.encounter.state != "draft"):
            raise ValueError("A tooth write event requires the current revision in a draft encounter.")
    if action.startswith("document_") and document_version is None:
        raise ValueError("A document action requires its document version.")
    if document_version is not None:
        if any(item is not None for item in (representative, participation, encounter_version, record, tooth_history)):
            raise ValueError("Audit document history cannot be mixed with other entity references.")
        if action not in {MedicalAuditEvent.Actions.READ, MedicalAuditEvent.Actions.DOCUMENT_DRAFT_CREATED,
                          MedicalAuditEvent.Actions.DOCUMENT_DRAFT_SAVED,
                          MedicalAuditEvent.Actions.DOCUMENT_EXPORTED,
                          MedicalAuditEvent.Actions.DOCUMENT_PRINT_REQUESTED,
                          MedicalAuditEvent.Actions.DOCUMENT_REVIEW_SUBMITTED,
                          MedicalAuditEvent.Actions.DOCUMENT_REVIEW_WITHDRAWN,
                          MedicalAuditEvent.Actions.DOCUMENT_REVIEW_CONFIRMED}:
            raise ValueError("Select a document read or draft action.")
        version = MedicalDocumentRevision.objects.select_related("document", "source_version").filter(
            pk=document_version.pk, document__business=business, document__encounter__business=business,
            document__encounter__patient=patient).first()
        if version is None or version.source_version.encounter_id != version.document.encounter_id:
            raise ValueError("Audit document must belong to this patient and business.")
        try:
            version.document.clean()
        except ModelValidationError:
            raise ValueError("Audit document links must be consistent.") from None
        if version.revision > version.document.revision:
            raise ValueError("Audit document version exceeds the current revision.")
        if action in {"document_draft_created", "document_draft_saved"} and (version.document.state != "draft" or
                version.revision != version.document.revision or version.author_id != actor.pk):
            raise ValueError("A document write event requires the actor's current draft version.")
        if action in {"document_review_submitted", "document_review_withdrawn", "document_review_confirmed"}:
            from .models import MedicalDocumentReviewTransition
            expected_state = {"document_review_submitted": "ready_for_review",
                "document_review_withdrawn": "draft", "document_review_confirmed": "reviewed"}[action]
            if (version.document.state != expected_state or version.revision != version.document.revision
                    or not MedicalDocumentReviewTransition.objects.filter(version=version, actor=actor,
                        state=expected_state, state_revision=version.document.state_revision).exists()):
                raise ValueError("A review event requires the current exact-version transition.")
        if action == MedicalAuditEvent.Actions.DOCUMENT_DRAFT_CREATED and version.revision != 1:
            raise ValueError("A document creation event requires its first version.")
        if action == MedicalAuditEvent.Actions.DOCUMENT_DRAFT_SAVED and version.revision <= 1:
            raise ValueError("A document update event requires a later version.")
    if action.startswith("order_") and order_version is None:
        raise ValueError("An order action requires its version.")
    if order_version is not None:
        if any(item is not None for item in (representative, participation, encounter_version, record,
                                             tooth_history, document_version, identity_correction, correction_access)):
            raise ValueError("Order audit cannot mix entity references.")
        if action not in {"read", "order_draft_created", "order_draft_saved"}:
            raise ValueError("Select an order read or draft action.")
        version = MedicalOrderRevision.objects.select_related("order").filter(pk=order_version.pk,
            order__business=business, order__encounter__business=business,
            order__encounter__patient=patient).first()
        if version is None:
            raise ValueError("Order audit must belong to this patient and business.")
        try:
            version.order.clean()
        except ModelValidationError:
            raise ValueError("Order audit links must be consistent.") from None
        if version.revision > version.order.revision:
            raise ValueError("Order version exceeds the current revision.")
        if action.startswith("order_") and (version.order.state != "draft" or
                version.revision != version.order.revision or version.author_id != actor.pk or
                version.order.author_id != actor.pk):
            raise ValueError("Order write audit requires the author's current draft.")
        if (action == "order_draft_created" and version.revision != 1 or
                action == "order_draft_saved" and version.revision <= 1):
            raise ValueError("Order action does not match the version.")
    if action.startswith("file_") and file_version is None:
        raise ValueError("A medical file action requires its version.")
    if file_version is not None:
        if any(item is not None for item in (representative, participation, encounter_version, record,
                                             tooth_history, document_version, identity_correction, order_version)):
            raise ValueError("Medical file audit cannot mix entity references.")
        if action not in {"read", "file_uploaded", "file_metadata_updated", "file_downloaded"}:
            raise ValueError("Select a medical file action.")
        version = MedicalAttachmentRevision.objects.select_related("medical_file").filter(
            pk=file_version.pk, medical_file__business=business, medical_file__patient=patient).first()
        if version is None:
            raise ValueError("Medical file version must belong to the audited patient and business.")
        try:
            version.clean()
        except ModelValidationError:
            raise ValueError("Medical file links must be consistent.") from None
        if action in {"file_uploaded", "file_metadata_updated"} and (
                version.author_id != actor.pk or version.revision != version.medical_file.revision):
            raise ValueError("A medical file write requires the author's current version.")
        if (action == "file_uploaded" and version.revision != 1 or
                action == "file_metadata_updated" and version.revision <= 1):
            raise ValueError("Medical file action does not match its version.")
    fields = dict(business=business, actor=actor, patient=patient,
            patient_revision=patient.revision, action=action, result="success", representative=representative,
            representative_revision=representative.revision if representative else None,
            participation=participation, participation_revision=participation.revision if participation else None,
            encounter_version=encounter_version, record=record, tooth_history=tooth_history,
            document_version=document_version, order_version=order_version, file_version=file_version,
            identity_correction=identity_correction, correction_access=correction_access,
            correction_access_revision=correction_access.revision if correction_access else None)
    try:
        with transaction.atomic():
            event = MedicalAuditEvent.objects.create(**fields)
            if event is None or event.pk is None:
                raise MedicalAuditUnavailable()
        return event
    except (DatabaseError, MedicalAuditUnavailable):
        if action == MedicalAuditEvent.Actions.READ:
            from .audit_reserve import ReserveUnavailable, write_reserved_read
            try:
                return write_reserved_read(fields)
            except ReserveUnavailable:
                pass
        raise MedicalAuditUnavailable() from None
