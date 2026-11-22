from unittest.mock import patch

from django.db import connection
from django.test import TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.businesses.models import Business, RolePermission
from . import tests_template_metadata as fixtures
from .audit import MedicalAuditUnavailable
from .common_template_services import list_approved_templates, list_common_template_drafts, save_common_template_draft, submit_common_template
from .models import MedicalAuditEvent, MedicalDocumentTemplate, MedicalDocumentTemplateRevision, MedicalTemplateReview
from .template_reviews import decide_template_review, submit_personal_template
from .template_services import list_personal_template_drafts, save_personal_template_draft
from .tests_patient_services import key


@override_settings(MEDICAL_DATA_KEYS={"test": key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=key(8))
class TemplateSearchTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.TemplateMetadataTests.setUpTestData.__func__(cls)
        for action in ("create", "update"):
            RolePermission.objects.get_or_create(business_role=cls.head_role, resource="medical_documents",
                action=action, defaults={"scope": "business", "is_allowed": True})

    def create(self, key, *, common=False, approved=True, actor=None, **overrides):
        actor = actor or (self.head if common else self.doctor)
        save = save_common_template_draft if common else save_personal_template_draft
        version, _ = save(**(dict(actor=actor, business_id=self.business.pk, title="Synthetic " + key,
            text="Private clinical body must not be searched", idempotency_key=key,
            metadata={"language": "kk", "category": "Учебная категория", "specialty": "Оқу мамандығы",
                      "service_ids": [self.service.pk]}) | overrides))
        if approved:
            submit = submit_common_template if common else submit_personal_template
            submit(actor=actor, business_id=self.business.pk, version_id=version.pk, idempotency_key="submit-"+key)
            decide_template_review(actor=self.head, business_id=self.business.pk, version_id=version.pk,
                decision="approved", reason="", idempotency_key="approve-"+key)
        return version

    def search(self, **filters):
        return list_approved_templates(actor=self.doctor, business_id=self.business.pk, **filters)

    def test_unicode_procedure_category_specialty_and_combined_filters(self):
        version = self.create("one")
        for query in ("КАТЕГОРИЯ", "ОҚУ", "private procedure", "  SYNTHETIC ONE  ", "ＳＹＮＴＨＥＴＩＣ"):
            with self.subTest(q=query):
                self.assertEqual(self.search(q=query)["results"][0]["version_id"], version.pk)
        self.assertEqual(len(self.search(language="kk", category="катег", specialty="МАМАН", service_id=self.service.pk)["results"]), 1)
        for filters in ({"language": "ru"}, {"category": "absent"}, {"specialty": "absent"},
                        {"service_id": self.service.pk + 100}, {"q": "clinical body"}):
            self.assertEqual(self.search(**filters)["results"], [])

    def test_visibility_excludes_other_personal_unapproved_and_foreign_before_decryption(self):
        own = self.create("own")
        shared = self.create("shared", common=True)
        self.create("head-private", actor=self.head)
        self.create("draft", approved=False)
        other = Business.objects.create(owner=self.owner, name="Other", slug="search-other")
        foreign = MedicalDocumentTemplate.objects.create(business=other, code="foreign", revision=1)
        foreign_version = MedicalDocumentTemplateRevision.objects.create(template=foreign, revision=1, author=self.owner,
                                                        snapshot_encrypted="must-never-be-decrypted")
        MedicalTemplateReview.objects.create(version=foreign_version, state="approved", submitted_by=self.owner,
            submitted_at=timezone.now(), decided_by=self.owner, decided_at=timezone.now(), decision_encrypted="foreign-receipt")
        self.assertEqual({row["version_id"] for row in self.search(q="synthetic")["results"]}, {own.pk, shared.pk})
        self.assertEqual([row["version_id"] for row in self.search(q="synthetic", scope="personal")["results"]], [own.pk])
        self.assertEqual([row["version_id"] for row in self.search(q="synthetic", scope="common")["results"]], [shared.pk])

    def test_matching_pagination_does_not_skip_between_nonmatching_candidates(self):
        first = self.create("match-first")
        self.create("ignored")
        last = self.create("match-last")
        page = self.search(q="match", limit=1)
        self.assertEqual(page["results"][0]["version_id"], last.pk)
        second = self.search(q="match", limit=1, before_id=page["next_before_id"])
        self.assertEqual(second["results"][0]["version_id"], first.pk)
        self.assertIsNone(second["next_before_id"])

    def test_latest_approved_version_metadata_not_a_new_unapproved_draft(self):
        first = self.create("old")
        second = self.create("new", approved=False, template_id=first.template_id, expected_revision=1,
            metadata={"language": "ru", "category": "New category", "specialty": "", "service_ids": []})
        self.assertEqual(self.search(q="категория")["results"][0]["version_id"], first.pk)
        self.assertEqual(self.search(q="New category")["results"], [])
        personal = list_personal_template_drafts(actor=self.doctor, business_id=self.business.pk, q="New category")
        self.assertEqual(personal["results"][0]["version_id"], second.pk)

    def test_search_crosses_sql_batches_without_truncating_matches(self):
        first = self.create("needle-first", approved=False)
        for index in range(52):
            self.create(f"filler-{index}", approved=False)
        last = self.create("needle-last", approved=False)
        args = {"actor": self.doctor, "business_id": self.business.pk, "q": "needle", "limit": 1}
        page = list_personal_template_drafts(**args)
        self.assertEqual(page["results"][0]["version_id"], last.pk)
        second = list_personal_template_drafts(**args, before_id=page["next_before_id"])
        self.assertEqual(second["results"][0]["version_id"], first.pk)
        self.assertIsNone(second["next_before_id"])

    def test_common_management_search_requires_head_and_preserves_unfiltered_contract(self):
        version = self.create("shared", common=True, approved=False)
        page = list_common_template_drafts(actor=self.head, business_id=self.business.pk, q="категория")
        self.assertEqual(page["results"][0]["version_id"], version.pk)
        self.assertEqual(self.search()["results"], [])
        with self.assertRaises(PermissionDenied):
            list_common_template_drafts(actor=self.doctor, business_id=self.business.pk, q="shared")

    def test_invalid_filters_and_revocation(self):
        for filters in ({"q": True}, {"q": "x"*256}, {"language": "xx"}, {"category": []},
                        {"service_id": True}, {"scope": "all_businesses"}, {"limit": 51}, {"before_id": 0}):
            with self.subTest(filters=filters), self.assertRaises(ValidationError):
                self.search(**filters)
        RolePermission.objects.filter(business_role=self.role, resource="medical_documents", action="view").update(is_allowed=False)
        with self.assertRaises(PermissionDenied):
            self.search(q="Synthetic")

    def test_search_audit_atomic_and_plaintext_not_in_sql(self):
        self.create("audit")
        with CaptureQueriesContext(connection) as queries:
            self.search(q="private procedure")
        self.assertNotIn("private procedure", "\n".join(row["sql"] for row in queries))
        before = MedicalAuditEvent.objects.count()
        with patch("apps.medical.template_services.write_template_audit", side_effect=MedicalAuditUnavailable()):
            with self.assertRaises(MedicalAuditUnavailable):
                self.search(q="Synthetic")
        self.assertEqual(MedicalAuditEvent.objects.count(), before)
