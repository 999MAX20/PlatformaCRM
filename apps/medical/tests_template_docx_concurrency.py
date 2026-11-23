from concurrent.futures import ThreadPoolExecutor
from threading import Event
from unittest import skipUnless
from unittest.mock import patch

from django.db import close_old_connections, connection, connections
from django.test import TransactionTestCase, override_settings
from rest_framework.exceptions import PermissionDenied

from apps.core.domain_errors import InvalidTransition
from apps.core.models import AuditLog
from . import tests_template_docx as fixtures
from .document_rule_services import save_document_rules
from .role_services import revoke_medical_role
from .tests_document_rules import default_rule
from .tests_patient_services import key


@skipUnless(connection.vendor == "postgresql", "Template export races require PostgreSQL connections and row locks")
@override_settings(MEDICAL_DATA_KEYS={"test": key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=key(8))
class TemplateDocxConcurrencyTests(TransactionTestCase):
    def setUp(self):
        fixtures.TemplateDocxTests.setUpTestData.__func__(self)
        fixtures.TemplateDocxTests.setUp(self)

    save = fixtures.TemplateDocxTests.save
    configure = fixtures.TemplateDocxTests.configure
    download = fixtures.TemplateDocxTests.download

    def during_scan(self, mutation, expected_error):
        started, release = Event(), Event()

        def scan(stream):
            started.set()
            if not release.wait(20):
                raise AssertionError("The concurrent mutation did not finish before scan release")
            return fixtures.clean(stream)

        def execute(command):
            close_old_connections()
            try:
                return command()
            finally:
                connections.close_all()

        with patch("apps.medical.template_docx.scan_stream", side_effect=scan), ThreadPoolExecutor(max_workers=2) as pool:
            export = pool.submit(execute, self.download)
            try:
                self.assertTrue(started.wait(10), "Export did not reach the scanner")
                pool.submit(execute, mutation).result(timeout=10)
            finally:
                release.set()
            with self.assertRaises(expected_error):
                export.result(timeout=10)
        self.assertFalse(AuditLog.objects.filter(entity_type="medical_template_version", action="download").exists())

    def change_rules(self, allowed):
        save_document_rules(actor=self.head, business_id=self.business.pk,
            kind_id=self.rules.kind_id, expected_revision=1, template_ids=[self.version.template_id],
            reason="Synthetic concurrent policy", idempotency_key="changed-policy",
            content={"name": "Changed policy", "docx_allowed": allowed,
                "default": default_rule(), "services": []})

    def test_rule_revision_can_commit_during_scan_and_invalidates_export(self):
        self.during_scan(lambda: self.change_rules(True), InvalidTransition)

    def test_opt_out_can_commit_during_scan_and_denies_export(self):
        self.during_scan(lambda: self.change_rules(False), PermissionDenied)

    def test_role_revocation_can_commit_during_scan_and_denies_export(self):
        self.during_scan(lambda: revoke_medical_role(actor=self.owner, business_id=self.business.pk,
            member_id=self.head_member.pk, expected_revision=self.head_assignment.revision,
            idempotency_key="revoke-during-export", reason="Synthetic export revocation"), PermissionDenied)
