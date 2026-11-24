from datetime import date, datetime
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.businesses.access import Actions, Resources, assert_can, scope_queryset
from apps.businesses.models import Business, BusinessMember
from apps.core.audit import write_actor_audit_log
from apps.core.domain_errors import InvalidTransition
from apps.core.idempotency import CRMCommandResult, run_idempotent_crm_command
from apps.core.models import AuditLog
from apps.scheduling.models import Appointment, Resource
from apps.services.models import Service
from .audit import write_patient_audit
from .identity_crypto import medical_request_digest
from .models import PatientProfile, ReceptionBookingRequest
from .patient_selectors import reception_context
from .reception_deadlines import reception_acceptance_deadline
from .reception_notifications import notify_reception
from .role_services import _key


def administration_context(actor, business_id, branch_id, client_id):
    if Business.objects.select_for_update().filter(pk=business_id).first() is None: raise PermissionDenied()
    actor,business,branch=reception_context(actor=actor,business_id=business_id,branch_id=branch_id,action="update")
    patient=PatientProfile.objects.select_related("client").filter(business=business,client_id=client_id,
        client__business=business,client__is_archived=False).first()
    if patient is None: raise PermissionDenied()
    assert_can(actor,business,Resources.CLIENTS,Actions.VIEW,obj=patient.client)
    assert_can(actor,business,Resources.APPOINTMENTS,Actions.VIEW)
    return actor,business,branch,patient


def source_appointments(actor,business,branch,patient):
    return scope_queryset(Appointment.objects.filter(business=business,branch=branch,client=patient.client,
        service__business=business,resource__business=business,resource__resource_type="staff",is_archived=False)
        .exclude(status="cancelled"),actor,business,Resources.APPOINTMENTS,Actions.VIEW)


@transaction.atomic
def read_administrative_follow_up(*,actor,business_id,branch_id,client_id,kind,after_id=0,search=""):
    actor,business,branch,patient=administration_context(actor,business_id,branch_id,client_id)
    if kind not in ("appointments","services","staff") or type(after_id) is not int or after_id<0 or len(search)>100:
        raise ValidationError({"options":"Select valid organizational options."})
    if kind=="appointments":
        query=source_appointments(actor,business,branch,patient).select_related("resource","service")
        rows=list(query.filter(pk__gt=after_id).order_by("pk")[:26])
        result=[{"id":r.pk,"start_at":r.start_at,"updated_at":r.updated_at,"name":r.resource.name,"service_name":r.service.name} for r in rows[:25]]
    else:
        query=(Service.objects.filter(business=business,is_active=True,is_archived=False) if kind=="services" else
            Resource.objects.filter(business=business,resource_type="staff",is_active=True,retired_at__isnull=True,archived_at__isnull=True))
        rows=list(query.filter(pk__gt=after_id,name__icontains=search).order_by("pk")[:26])
        result=[{"id":r.pk,"name":r.name} for r in rows[:25]]
    write_patient_audit(actor=actor,business=business,patient=patient,action="read")
    return {"results":result,"next_id":rows[24].pk if len(rows)>25 else None}


@transaction.atomic
def request_administrative_follow_up(*,actor,business_id,branch_id,client_id,source_appointment_id,
        expected_updated_at,service_id,preferred_resource_id,recommended_from,recommended_until,patient_in_clinic,
        reason,idempotency_key):
    _key(idempotency_key)
    if (any(type(v) is not int or v<=0 for v in (business_id,branch_id,client_id,source_appointment_id,service_id,preferred_resource_id))
            or not isinstance(expected_updated_at,datetime) or timezone.is_naive(expected_updated_at)
            or type(recommended_from) is not date or type(recommended_until) is not date or recommended_until<recommended_from
            or type(patient_in_clinic) is not bool or not isinstance(reason,str) or not reason.strip() or len(reason.strip())>1000):
        raise ValidationError({"request":"Provide the source appointment, recommended period and organizational reason."})
    actor,business,branch,patient=administration_context(actor,business_id,branch_id,client_id)
    source=source_appointments(actor,business,branch,patient).select_related("resource").filter(pk=source_appointment_id).first()
    if source is None: raise PermissionDenied()
    service=Service.objects.filter(pk=service_id,business=business,is_active=True,is_archived=False).first()
    preferred=Resource.objects.filter(pk=preferred_resource_id,business=business,resource_type="staff",is_active=True,
        retired_at__isnull=True,archived_at__isnull=True).first()
    if service is None or preferred is None: raise PermissionDenied()
    def operation():
        if source.updated_at != expected_updated_at: raise InvalidTransition("The source appointment changed; reload it.")
        existing=ReceptionBookingRequest.objects.filter(business=business,patient=patient,source_appointment=source,
            service=service,state__in=["new","pending"]).first()
        if existing: return CRMCommandResult(data={"existing":True},resource=existing)
        now=timezone.now()
        member=BusinessMember.objects.filter(business=business,user_id=source.resource.linked_user_id).first() if source.resource.linked_user_id else None
        item=ReceptionBookingRequest(business=business,patient=patient,branch=branch,source_appointment=source,
            referring_clinician=member,referring_resource=source.resource,created_by=actor,created_at=now,service=service,
            preferred_resource=preferred,recommended_from=recommended_from,recommended_until=recommended_until,
            patient_in_clinic=patient_in_clinic,acceptance_due_at=reception_acceptance_deadline(business=business,
                branch_id=branch.pk,requested_at=now,patient_in_clinic=patient_in_clinic))
        item.full_clean();item.save(force_insert=True)
        write_actor_audit_log(actor=actor,business=business,action=AuditLog.Actions.CREATE,instance=item,
            metadata={"kind":"medical_follow_up_requested","revision":item.revision,"state":item.state,
                "source":"administrator","referring_resource_id":source.resource_id,"referring_name":source.resource.name,"reason":reason.strip()})
        notify_reception(item,"new")
        return CRMCommandResult(data={"existing":False},resource=item)
    result=run_idempotent_crm_command(business=business,actor=actor,action="medical.reception.administrative_request",
        idempotency_key=medical_request_digest({"key":idempotency_key},business_id=business_id),
        payload={"branch":branch_id,"client":client_id,"source":source_appointment_id,"updated":expected_updated_at.isoformat(),
            "service":service_id,"preferred":preferred_resource_id,"from":recommended_from.isoformat(),
            "until":recommended_until.isoformat(),"onsite":patient_in_clinic,"reason":reason.strip()},operation=operation)
    item=ReceptionBookingRequest.objects.get(pk=result.resource_id if result.replayed else result.resource.pk,business=business)
    return item,result.replayed or result.data["existing"]
