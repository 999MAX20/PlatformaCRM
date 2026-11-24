from uuid import uuid4
from django.db import transaction

@transaction.atomic
def prepare():
    from completion_fixture import prepare_completion
    from django.contrib.auth import get_user_model
    from apps.businesses.models import BusinessMember,BusinessRole,RolePermission
    from apps.medical.models import MedicalRoleAssignment
    from apps.medical.template_services import save_personal_template_draft
    from apps.medical.template_reviews import submit_personal_template,decide_template_review
    from apps.scheduling.models import Appointment
    entry=prepare_completion()
    appointment=Appointment.objects.get(pk=entry["appointment_id"])
    business=appointment.business
    doctor=get_user_model().objects.get(email=entry["email"])
    assignment=MedicalRoleAssignment.objects.get(member__business=business,member__user=doctor)
    for action in ("view","create","update"):
        RolePermission.objects.get_or_create(business_role=assignment.business_role,resource="medical_prescriptions",action=action,defaults={"scope":"own","is_allowed":True})
    head_name="completion-head-"+uuid4().hex[:12]
    head_user=get_user_model().objects.create_user(username=head_name,email=head_name+"@example.test")
    member=BusinessMember.objects.create(business=business,user=head_user,role="manager")
    role=BusinessRole.objects.create(business=business,name="Synthetic head")
    head=MedicalRoleAssignment.objects.create(member=member,business_role=role,kind="head",granted_by=business.owner)
    head.branches.add(appointment.branch)
    for action in ("view","approve"):
        RolePermission.objects.create(business_role=role,resource="medical_documents",action=action,scope="business",is_allowed=True)
    title="Synthetic completion template "+uuid4().hex[:10]
    version,_=save_personal_template_draft(actor=doctor,business_id=business.pk,title=title,
        text="Synthetic approved instruction for {{patient.full_name}}",idempotency_key="template")
    submit_personal_template(actor=doctor,business_id=business.pk,version_id=version.pk,idempotency_key="submit")
    decide_template_review(actor=head_user,business_id=business.pk,version_id=version.pk,decision="approved",reason="Synthetic approval",idempotency_key="approve")
    return entry|{"title":title,"prefix":"Synthetic approved instruction for ","expected":"Synthetic approved instruction for "+appointment.client.full_name}
