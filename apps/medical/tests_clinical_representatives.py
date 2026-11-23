import json
from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework.exceptions import PermissionDenied

from apps.businesses.models import Business
from apps.clients.models import Client
from . import tests_encounter_open as fixtures
from . import tests_encounter_reads as reads
from . import tests_patient_services as crypto
from .audit import MedicalAuditUnavailable
from .identity_crypto import encrypt_medical_value
from .models import MedicalAuditEvent, PatientRepresentative


@override_settings(MEDICAL_DATA_KEYS={"test": crypto.key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=crypto.key(8))
class ClinicalRepresentativeTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.OpenPrimaryEncounterTests.setUpTestData.__func__(cls)

    participation = reads.TreatingClinicianReadTests.participation

    def setUp(self):
        self.api = APIClient()
        self.api.force_authenticate(self.doctor)
        self.scope = dict(business_id=self.business.pk, patient_id=self.patient.pk, appointment_id=self.appointment.pk)

    def read(self, **changes):
        response = self.api.get("/api/medical/encounters/representatives/", self.scope | changes)
        self.assertEqual(response["Cache-Control"], "no-store, private")
        return response

    def relation(self, state="active"):
        now = timezone.now()
        start = now + timedelta(days=1) if state == "scheduled" else now - timedelta(days=2)
        end = now - timedelta(days=1) if state == "expired" else now + timedelta(days=2)
        client = Client.objects.create(business=self.business, full_name=f"Synthetic {state} representative",
            phone="+77010000000", email="private@example.test")
        relation = PatientRepresentative.objects.create(patient=self.patient, representative_client=client,
            authority_encrypted="pending", verified_by=self.owner, verified_at=now - timedelta(days=3),
            valid_from=start, valid_until=end)
        authority = {"patient_id": self.patient.pk, "representative_client_id": client.pk,
            "valid_from": start.isoformat(), "valid_until": end.isoformat(), "permissions": ["give_consent"],
            "permission_labels": {"give_consent": {"ru": "Согласие", "kk": "Келісім", "en": "Consent"}},
            "fields": {"basis": "Private evidence"}}
        relation.authority_encrypted = encrypt_medical_value(json.dumps(authority), business_id=self.business.pk,
            subject_id=relation.pk, purpose="representative_authority")
        if state == "revoked":
            relation.revoked_at, relation.revoked_by, relation.revocation_encrypted = now, self.owner, "synthetic-revocation"
        relation.save()
        return relation

    def test_empty_audited_and_page_projects_only_existing_authority(self):
        self.assertEqual(self.read().data, {"results": [], "next_offset": None})
        self.assertEqual(MedicalAuditEvent.objects.filter(action="read").count(), 1)
        for state in ("active", "expired", "scheduled", "revoked"):
            self.relation(state)
        first = self.read(limit=2)
        self.assertEqual(first.status_code, 200, first.data)
        self.assertEqual([row["status"] for row in first.data["results"]], ["revoked", "scheduled"])
        self.assertEqual(first.data["next_offset"], 2)
        second = self.read(offset=2, limit=2)
        self.assertEqual([row["status"] for row in second.data["results"]], ["expired", "active"])
        self.assertIsNone(second.data["next_offset"])
        self.assertEqual(MedicalAuditEvent.objects.filter(action="read", representative__isnull=False).count(), 4)
        for private in ("Private evidence", "private@example.test", "+77010000000", "synthetic-revocation"):
            self.assertNotIn(private, first.content.decode() + second.content.decode())

    def test_participation_and_current_basis_revocation(self):
        self.relation()
        participation = self.participation()
        self.scope.pop("appointment_id")
        self.scope["participation_id"] = participation.pk
        self.assertEqual(self.read().status_code, 200)
        participation.state, participation.closed_at, participation.closed_by = "ended", timezone.now(), self.owner
        participation.save(update_fields=["state", "closed_at", "closed_by"])
        count = MedicalAuditEvent.objects.count()
        self.assertEqual(self.read().status_code, 403)
        self.assertEqual(MedicalAuditEvent.objects.count(), count)

    def test_tenant_owner_branch_and_client_denial(self):
        relation = self.relation()
        other = Business.objects.create(owner=self.owner, name="Other", slug="clinical-rep-other")
        self.assertEqual(self.read(business_id=other.pk).status_code, 403)
        self.api.force_authenticate(self.owner)
        self.assertEqual(self.read().status_code, 403)
        self.api.force_authenticate(self.doctor)
        from apps.businesses.access import assert_can
        def client_access(actor, business, resource, action, **kwargs):
            if kwargs.get("obj").pk == relation.representative_client_id:
                raise PermissionDenied()
            return assert_can(actor, business, resource, action, **kwargs)
        with patch("apps.medical.representative_selectors.assert_can", side_effect=client_access):
            self.assertEqual(self.read().status_code, 403)
        self.assignment.branches.clear()
        self.assertEqual(self.read().status_code, 403)

    def test_audit_failure_corruption_and_strict_input(self):
        relation = self.relation()
        with patch("apps.medical.representative_selectors.write_patient_audit", side_effect=MedicalAuditUnavailable):
            self.assertEqual(self.read().status_code, 503)
        self.assertFalse(MedicalAuditEvent.objects.exists())
        PatientRepresentative.objects.filter(pk=relation.pk).update(authority_encrypted="corrupt")
        self.assertEqual(self.read().status_code, 503)
        for query in ({"offset": -1}, {"limit": 51}, {"approve": True}, {"participation_id": 1}):
            self.assertEqual(self.read(**query).status_code, 400)
        self.assertFalse(MedicalAuditEvent.objects.exists())
