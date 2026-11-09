from contextlib import contextmanager
from datetime import datetime
from io import BytesIO
from unittest.mock import MagicMock, patch
from zipfile import ZipFile, ZIP_DEFLATED

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, TestCase, override_settings
from openpyxl import Workbook
from rest_framework.exceptions import ValidationError
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.businesses.models import Business, BusinessMember
from apps.clients.models import Client
from apps.core.tests_xlsx_reader import workbook_bytes
from apps.outreach.imports import read_consent_upload
from apps.outreach.models import OutreachConsent


MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def consent_book(rows=None, **kwargs):
    return workbook_bytes(rows or [["phone", "channel", "status"], ["+77010001111", "whatsapp", "opted_in"]], **kwargs)


@contextmanager
def loader_probe(book=None):
    book = book or MagicMock()
    if book.active.iter_rows.side_effect is None:
        book.active.iter_rows.side_effect = lambda **kwargs: iter([("phone", "channel", "status"), ("+77010001111", "whatsapp", "opted_in")])
    # Probe old frozen import and new lazy import without loading crafted dimensions.
    with patch("apps.outreach.imports.load_workbook", return_value=book, create=True) as old, patch("openpyxl.load_workbook", return_value=book) as shared:
        yield old, shared, book


class ConsentXlsxLimitTests(SimpleTestCase):
    def parse(self, content):
        return read_consent_upload(SimpleUploadedFile("consents.xlsx", content, content_type=MIME))

    def reject_before_loader(self, content):
        with loader_probe() as (old, shared, _):
            with self.assertRaises(ValidationError) as caught:
                self.parse(content)
            self.assertIn("file", caught.exception.detail)
            old.assert_not_called()
            shared.assert_not_called()

    @override_settings(IMPORT_MAX_ROWS=2, IMPORT_MAX_COLUMNS=7)
    def test_valid_aliases_values_and_exact_limits(self):
        data = consent_book([["crm_id", "mobile", "e-mail", "source_channel", "consent", "evidence_source", "notes"],
            [42, "+77010001111", "synthetic@example.test", "whatsapp", "opted_in", "paper", " proof "],
            [43, None, "other@example.test", "telegram", "opted_out", 0, True]])
        self.assertEqual(self.parse(data), [
            {"client_id": "42", "phone": "+77010001111", "email": "synthetic@example.test", "channel": "whatsapp", "status": "opted_in", "source": "paper", "note": "proof"},
            {"client_id": "43", "phone": "", "email": "other@example.test", "channel": "telegram", "status": "opted_out", "source": "0", "note": "True"},
        ])

    def test_dates_unknown_columns_and_blank_rows_keep_normalization(self):
        data = consent_book([["phone", "note", "ignored"], ["+77010001111", datetime(2026, 1, 2), "unused"], [None, None, None]])
        self.assertEqual(self.parse(data), [{"phone": "+77010001111", "note": "2026-01-02 00:00:00"}])

    def test_active_sheet_and_cached_formula_values_are_unchanged(self):
        book = Workbook()
        book.active.append(["unrelated"])
        active = book.create_sheet("Consent")
        active.append(["phone", "note"])
        active.append(["+77010001111", "=1+1"])
        book.active = 1
        stream = BytesIO()
        book.save(stream)
        book.close()
        self.assertEqual(self.parse(stream.getvalue()), [{"phone": "+77010001111", "note": ""}])

    def test_underreported_dimensions_preserve_all_actual_rows(self):
        data = consent_book(transform=lambda xml: xml.replace('ref="A1:C2"', 'ref="A1:A1"'))
        self.assertEqual(self.parse(data)[0]["phone"], "+77010001111")

    @override_settings(IMPORT_MAX_ROWS=2, IMPORT_MAX_COLUMNS=3)
    def test_dimensions_and_coordinates_rejected_before_loading(self):
        fixtures = [
            consent_book(transform=lambda xml: xml.replace('ref="A1:C2"', 'ref="A1:XFD1048576"')),
            consent_book(transform=lambda xml: xml.replace('r="2"', 'r="4"')),
            consent_book(transform=lambda xml: xml.replace('r="C2"', 'r="D2"')),
        ]
        for data in fixtures:
            with self.subTest(size=len(data)):
                self.reject_before_loader(data)

    @override_settings(IMPORT_MAX_ROWS=1, IMPORT_MAX_COLUMNS=3)
    def test_actual_rows_bypass_of_small_dimension_is_rejected_early(self):
        data = consent_book([["phone"], ["one"], ["two"]], transform=lambda xml: xml.replace('ref="A1:A3"', 'ref="A1:A1"'))
        self.reject_before_loader(data)

    def test_archive_entry_expansion_and_ratio_limits_before_loading(self):
        for limits in ({"IMPORT_XLSX_MAX_ENTRIES": 1}, {"IMPORT_XLSX_MAX_EXPANDED_MB": 0.001}, {"IMPORT_XLSX_MAX_COMPRESSION_RATIO": 1}):
            with self.subTest(limits=limits), override_settings(**limits):
                self.reject_before_loader(consent_book())

    def test_xml_doctype_rejected_before_loading(self):
        self.reject_before_loader(consent_book(transform=lambda xml: '<!DOCTYPE worksheet [<!ENTITY small "tiny">]>' + xml))

    def test_duplicate_archive_entries_rejected_before_loading(self):
        original = consent_book()
        output = BytesIO()
        with ZipFile(BytesIO(original)) as source, ZipFile(output, "w", ZIP_DEFLATED) as target:
            for entry in source.infolist():
                target.writestr(entry.filename, source.read(entry.filename))
            target.writestr("duplicate.bin", b"a")
            target.writestr("duplicate.bin", b"b")
        self.reject_before_loader(output.getvalue())

    @override_settings(MAX_UPLOAD_SIZE_MB=8/(1024*1024))
    def test_actual_bytes_read_is_bounded_even_if_size_metadata_is_wrong(self):
        class Upload(BytesIO):
            name = "consents.xlsx"
            size = 1

            def read(self, size=-1):
                self.requested_size = size
                return super().read(size)

        upload = Upload(b"PK\x03\x04synthetic")
        with loader_probe() as (old, shared, _):
            with self.assertRaises(ValidationError) as caught:
                read_consent_upload(upload)
            self.assertIn("file", caught.exception.detail)
            self.assertEqual(upload.requested_size, 9)
            old.assert_not_called()
            shared.assert_not_called()

    @override_settings(IMPORT_MAX_ROWS=1)
    def test_fallback_iteration_stops_at_first_overflow_and_closes(self):
        consumed, closed = [], []
        def rows(**kwargs):
            try:
                yield ("phone",)
                for i in range(3):
                    consumed.append(i)
                    yield (str(i),)
            finally:
                closed.append(True)
        book = MagicMock()
        book.active.iter_rows.side_effect = rows
        with loader_probe(book):
            with self.assertRaises(ValidationError):
                self.parse(consent_book([["phone"], ["one"]]))
        self.assertEqual(len(consumed), 2)
        self.assertEqual(closed, [True])
        book.close.assert_called_once()

    def test_iterator_failure_is_file_validation_error_and_closes_book(self):
        def rows(**kwargs):
            yield ("phone",)
            raise ValueError("synthetic parser failure")
        book = MagicMock()
        book.active.iter_rows.side_effect = rows
        with loader_probe(book):
            try:
                self.parse(consent_book())
            except Exception as exc:
                self.assertIsInstance(exc, ValidationError)
                self.assertIn("file", exc.detail)
            else:
                self.fail("Malformed workbook was accepted")
        book.close.assert_called_once()

    def test_empty_headers_and_header_only_are_clear_file_errors(self):
        for data in (consent_book([["phone"]]), consent_book([[None], [None]]), b"PK\x03\x04invalid"):
            with self.subTest(size=len(data)):
                try:
                    self.parse(data)
                except Exception as exc:
                    self.assertIsInstance(exc, ValidationError)
                    self.assertIn("file", exc.detail)
                else:
                    self.fail("Empty or invalid workbook was accepted")

    def test_csv_compatibility_is_unchanged(self):
        upload = SimpleUploadedFile("consents.csv", b"phone,channel,status,note\n+77010001111,whatsapp,opted_out,paper\n", content_type="text/csv")
        self.assertEqual(read_consent_upload(upload), [{"phone": "+77010001111", "channel": "whatsapp", "status": "opted_out", "note": "paper"}])


class ConsentXlsxApiTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="consent-xlsx-owner", email="consent-xlsx-owner@example.test")
        self.operator = User.objects.create_user(username="consent-xlsx-op", email="consent-xlsx-op@example.test")
        self.business = Business.objects.create(owner=self.owner, name="Consent fixtures", slug="consent-fixtures")
        BusinessMember.objects.create(business=self.business, user=self.operator, role="operator")
        self.customer = Client.objects.create(business=self.business, full_name="Synthetic consent client", phone="+77010001111")
        self.api = APIClient(raise_request_exception=False)
        self.api.force_authenticate(self.owner)

    def upload(self, content, business=None):
        return self.api.post("/api/outreach/consents/bulk-import-file/", {
            "business": (business or self.business).pk, "channel": "whatsapp", "status": "opted_in", "source": "synthetic_excel",
            "file": SimpleUploadedFile("consents.xlsx", content, content_type=MIME),
        }, format="multipart")

    def test_owner_import_preserves_status_and_evidence_contract(self):
        response = self.upload(consent_book([["phone", "status", "note"], [self.customer.phone, "opted_out", "paper proof"]]))
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["imported"], 1)
        consent = OutreachConsent.objects.get(client=self.customer, channel="whatsapp")
        self.assertEqual(consent.status, "opted_out")
        self.assertEqual(consent.source, "synthetic_excel")
        self.assertEqual(consent.evidence_json["filename"], "consents.xlsx")
        self.assertEqual(consent.evidence_json["import_row"]["note"], "paper proof")

    @override_settings(IMPORT_MAX_ROWS=1)
    def test_overflow_does_not_partially_update_existing_consent(self):
        consent = OutreachConsent.objects.create(business=self.business, client=self.customer, channel="whatsapp", status="opted_out", source="original")
        data = consent_book([["phone", "status"], [self.customer.phone, "opted_in"], [self.customer.phone, "opted_in"]])
        response = self.upload(data)
        self.assertEqual(response.status_code, 400, response.data)
        self.assertIn("file", response.data)
        consent.refresh_from_db()
        self.assertEqual((consent.status, consent.source), ("opted_out", "original"))
        self.assertEqual(OutreachConsent.objects.count(), 1)

    def test_invalid_zip_returns400_instead_of_uncaught_error(self):
        response = self.upload(b"PK\x03\x04invalid")
        self.assertEqual(response.status_code, 400)
        self.assertIn("file", response.data)
        self.assertFalse(OutreachConsent.objects.exists())

    def test_role_and_foreign_business_denial_remain(self):
        self.api.force_authenticate(self.operator)
        self.assertEqual(self.upload(consent_book()).status_code, 403)
        foreign = Business.objects.create(owner=self.operator, name="Other consent", slug="other-consent")
        self.api.force_authenticate(self.owner)
        self.assertIn(self.upload(consent_book(), business=foreign).status_code, (400, 403))
        self.assertFalse(OutreachConsent.objects.exists())
