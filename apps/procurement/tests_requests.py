from datetime import timedelta
from unittest.mock import patch
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.test import APIClient
from apps.core.domain_errors import InvalidTransition
from apps.businesses.models import RolePermission
from apps.core.idempotency import CRMCommandConflict
from apps.medical import tests_reception_requests as fixtures
from apps.medical.tests_patient_services import key
from .models import PurchaseRequest, PurchaseRequestHistory
from .services import create_request, change_own_request, list_own_requests, own_history
from .services import request_context


@override_settings(MEDICAL_DATA_KEYS={"test": key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test", MEDICAL_IDENTITY_INDEX_KEY=key(8))
class PurchaseRequestTests(TestCase):
    setUpTestData = classmethod(fixtures.ReceptionCreationTests.setUpTestData.__func__)

    def setUp(self):
        RolePermission.objects.get_or_create(business_role=self.role, resource="medical_records", action="create", defaults={"scope":"own", "is_allowed":True})
        self.scope = dict(actor=self.doctor, business_id=self.business.pk, branch_id=self.first.pk)
        self.fields = dict(material="Synthetic material", specification="Size 12", quantity="10", unit="piece",
            urgent=True, needed_by=timezone.localdate()+timedelta(days=7), comment="Synthetic request")

    def create(self, **changes):
        return create_request(**(self.scope | dict(fields=self.fields, idempotency_key="create") | changes))

    def change(self, item, **changes):
        return change_own_request(**(self.scope | dict(request_id=item.pk, expected_revision=item.revision,
            action="edit", reason="Synthetic correction", fields=self.fields | {"quantity":"12"}, idempotency_key="edit") | changes))

    def test_create_edit_cancel_preserves_history_and_replay(self):
        item, replay = self.create(); self.assertFalse(replay)
        self.assertEqual(self.create()[0].pk, item.pk)
        item, _ = self.change(item)
        self.assertEqual(str(item.line.quantity), "12.000")
        item, _ = self.change(item, action="cancel", fields={}, idempotency_key="cancel")
        self.assertEqual(item.state, "cancelled")
        history = own_history(**self.scope, request_id=item.pk)["results"]
        self.assertEqual([row["action"] for row in history], ["created", "edit", "cancel"])
        self.assertEqual(history[0]["snapshot"]["quantity"], "10")
        self.assertEqual(PurchaseRequest.objects.count(), 1)
        with self.assertRaises(InvalidTransition): self.change(item, idempotency_key="after-cancel")

    def test_invalid_quantity_unit_date_and_forged_fields(self):
        for fields in ({"quantity":"0"}, {"quantity":"1.5"}, {"quantity":"NaN"}, {"quantity":"1.0001", "unit":"ml"},
                {"needed_by":None}, {"unit":"unknown"}, {"author_id":self.owner.pk}, {"patient_id":self.patient.pk}):
            with self.subTest(fields=fields), self.assertRaises(ValidationError):
                self.create(fields=self.fields | fields)
        self.assertFalse(PurchaseRequest.objects.exists())

    def test_tenant_branch_role_revocation_and_no_patient_access_dependency(self):
        for changes in ({"actor":self.owner}, {"branch_id":self.second.pk}, {"business_id":999999}):
            with self.assertRaises(PermissionDenied): self.create(**changes)
        item,_=self.create()
        with self.assertRaises(PermissionDenied): self.change(item, actor=self.owner)
        self.assignment.revoked_at=timezone.now(); self.assignment.save(update_fields=["revoked_at"])
        for fn in (lambda:self.create(), lambda:list_own_requests(**self.scope), lambda:own_history(**self.scope,request_id=item.pk)):
            with self.assertRaises(PermissionDenied): fn()

    def test_stale_changed_payload_accepted_and_atomic_audit(self):
        with patch("apps.procurement.services.write_actor_audit_log", side_effect=RuntimeError("audit")):
            with self.assertRaises(RuntimeError): self.create()
        self.assertFalse(PurchaseRequest.objects.exists()); self.assertFalse(PurchaseRequestHistory.objects.exists())
        item,_=self.create()
        with self.assertRaises(CRMCommandConflict): self.create(fields=self.fields | {"quantity":"11"})
        with self.assertRaises(InvalidTransition): self.change(item, expected_revision=9)
        PurchaseRequest.objects.filter(pk=item.pk).update(state="in_review")
        with self.assertRaises(InvalidTransition): self.change(item)
        self.assertEqual(PurchaseRequestHistory.objects.count(),1)

    def test_strict_http_private_projection(self):
        api=APIClient();api.force_authenticate(self.doctor)
        scope={k:v for k,v in self.scope.items() if k!="actor"}
        payload=scope | {"fields":self.fields | {"needed_by":self.fields["needed_by"].isoformat()}}
        result=api.post("/api/procurement/requests/",payload,format="json",HTTP_IDEMPOTENCY_KEY="http")
        self.assertEqual(result.status_code,200,result.data)
        self.assertEqual(result["Cache-Control"],"no-store, private")
        self.assertTrue(set(result.data).isdisjoint({"patient_id","client_id","appointment_id"}))
        forged=api.post("/api/procurement/requests/",payload|{"author_id":self.owner.pk},format="json",HTTP_IDEMPOTENCY_KEY="forged")
        self.assertEqual(forged.status_code,400)
        self.assertEqual(api.get("/api/procurement/requests/",scope).data["results"][0]["id"],result.data["id"])

    def test_current_context_and_other_author_isolation(self):
        from django.contrib.auth import get_user_model
        from apps.businesses.models import BusinessMember, BusinessRole
        from apps.branches.models import BranchAccess
        from apps.medical.models import MedicalRoleAssignment
        self.doctor.full_name="";self.doctor.first_name="Synthetic";self.doctor.last_name="Author";self.doctor.save()
        item,_=self.create()
        self.assertEqual(own_history(**self.scope,request_id=item.pk)["results"][0]["actor_name"],"Synthetic Author")
        other=get_user_model().objects.create_user(username="other-purchase-author",email="other-purchase@example.test")
        member=BusinessMember.objects.create(user=other,business=self.business,role="specialist")
        role=BusinessRole.objects.create(business=self.business,name="Synthetic separate author")
        assignment=MedicalRoleAssignment.objects.create(member=member,business_role=role,kind="doctor",granted_by=self.owner)
        assignment.branches.add(self.first);BranchAccess.objects.create(member=member,all_branches=True)
        RolePermission.objects.create(business_role=role,resource="medical_records",action="create",scope="own",is_allowed=True)
        other_scope=self.scope|{"actor":other}
        self.assertEqual(list_own_requests(**other_scope)["results"],[])
        with self.assertRaises(PermissionDenied):own_history(**other_scope,request_id=item.pk)
        with self.assertRaises(PermissionDenied):self.change(item,actor=other)
        self.assertEqual([row["id"] for row in request_context(actor=other,business_id=self.business.pk)["branches"]],[self.first.pk])
