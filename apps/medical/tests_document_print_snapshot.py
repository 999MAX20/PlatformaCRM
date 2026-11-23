from copy import deepcopy
from datetime import datetime, timezone
from io import BytesIO
from unittest import TestCase
from unittest.mock import patch

from pypdf import PdfReader

from .document_pdf import DocumentRenderUnavailable, render_draft_pdf
from .document_print_snapshot import draft_print_snapshot


class SavedPrintSnapshotTests(TestCase):
    def snapshot(self):
        return {
            "business": {"name": "Saved clinic", "legal_name": "Saved legal name", "tax_id": "000000000000",
                "address": "Saved address", "phone": "+70000000000", "brand_logo_url": ""},
            "branch": {"name": "Saved branch", "address": "Branch address", "phone": ""},
            "patient_identity": {"full_name": "Saved patient", "iin": None},
            "encounter_source": {"record_number": "TEST-7", "timezone": "Asia/Qyzylorda"},
            "medical_credentials": {"clinic": {"content": {"license": "Synthetic license"}},
                "clinician": {"content": {"specialty": "Saved specialty", "position": "Saved position", "qualification": ""}}},
            "performed_by": {"name": "Saved doctor"}, "prepared_by": {"name": "Saved author"},
            "template": {"title": "Saved title", "text": "Do not render this template again"},
            "document_text": "Saved corrected text {{literal_token}}",
        }

    def build(self, snapshot, **changes):
        return draft_print_snapshot(snapshot=snapshot, **({"revision": 7,
            "created_at": datetime(2026, 11, 23, 8, 30, tzinfo=timezone.utc), "language": "ru"} | changes))

    def test_exact_saved_text_identity_and_credentials_survive_source_mutation(self):
        snapshot = self.snapshot()
        before = deepcopy(snapshot)
        data = self.build(snapshot)
        self.assertEqual(snapshot, before)
        snapshot["document_text"] = "New text"
        snapshot["business"]["name"] = "New clinic"
        snapshot["performed_by"]["name"] = "New doctor"
        pdf = render_draft_pdf(data)
        text = PdfReader(BytesIO(pdf)).pages[0].extract_text()
        for value in ("Saved corrected text {{literal_token}}", "Saved clinic", "Saved doctor", "Saved author",
                      "Synthetic license", "Saved specialty", "TEST-7", "13:30:00+05:00"):
            self.assertIn(value, text)
        for value in ("New text", "New clinic", "New doctor", "Do not render this template again"):
            self.assertNotIn(value, text)

    def test_legacy_snapshot_or_invalid_metadata_is_not_filled_from_live_data(self):
        for key in ("patient_identity", "medical_credentials", "document_text"):
            snapshot = self.snapshot()
            del snapshot[key]
            with self.subTest(key=key), self.assertRaises(DocumentRenderUnavailable):
                self.build(snapshot)
        for changes in ({"revision": True}, {"revision": 0}, {"language": "xx"},
                        {"created_at": datetime(2026, 1, 1)}):
            with self.subTest(changes=changes), self.assertRaises(DocumentRenderUnavailable):
                self.build(self.snapshot(), **changes)

    def test_configured_logo_requires_captured_bytes_and_never_fetches_url(self):
        snapshot = self.snapshot()
        snapshot["business"]["brand_logo_url"] = "http://127.0.0.1/private"
        with patch("urllib.request.urlopen", side_effect=AssertionError("No network")):
            with self.assertRaises(DocumentRenderUnavailable):
                self.build(snapshot)
            self.assertEqual(self.build(snapshot, captured_logo=b"captured").logo, b"captured")
        with self.assertRaises(DocumentRenderUnavailable):
            self.build(self.snapshot(), captured_logo=b"unbound")

    def test_missing_confirmations_are_not_presented_as_verified_credentials(self):
        snapshot = self.snapshot()
        snapshot["medical_credentials"] = {"clinic": None, "clinician": None}
        for language in ("ru", "kk", "en"):
            data = self.build(snapshot, language=language)
            text = PdfReader(BytesIO(render_draft_pdf(data))).pages[0].extract_text()
            self.assertIn("Saved patient", text)
            self.assertNotIn("Synthetic license", text)
            self.assertNotIn("Saved specialty", text)
