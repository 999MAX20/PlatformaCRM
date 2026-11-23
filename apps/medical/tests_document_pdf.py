from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import datetime, timezone
from io import BytesIO
from unittest import TestCase
from unittest.mock import patch

from PIL import Image
from pypdf import PdfReader

from .document_pdf import DraftPrintData, DocumentRenderUnavailable, render_draft_pdf


class DraftPDFTests(TestCase):
    def data(self, **changes):
        return DraftPrintData(title="Учебный документ / Үлгі құжат", text="Русский текст. Қазақша: Ә Ғ Қ Ң Ө Ұ Ү Һ І.",
            clinic_lines=("Synthetic clinic", "БИН: 000000000000", "Учебный адрес"),
            identity_lines=("Пациент: Synthetic Patient", "Версия: 7"),
            created_at=datetime(2026, 11, 23, 8, 30, tzinfo=timezone.utc), language="kk", **changes)

    def test_unicode_metadata_and_stable_bytes(self):
        data = self.data()
        first = render_draft_pdf(data)
        self.assertEqual(first, render_draft_pdf(data))
        reader = PdfReader(BytesIO(first))
        text = "\n".join(page.extract_text() for page in reader.pages)
        for expected in (data.title, data.text, "Жоба", "Synthetic Patient", "Версия: 7"):
            self.assertIn(expected, text)
        self.assertEqual(reader.metadata.creation_date, data.created_at)
        self.assertNotIn("Synthetic Patient", str(reader.metadata))
        fonts = reader.pages[0]["/Resources"]["/Font"]
        embedded = [font.get_object().get("/FontDescriptor") for font in fonts.values()]
        self.assertTrue(any(item and "/FontFile2" in item.get_object() for item in embedded))

    def test_long_text_paginates_without_loss_or_page_actions(self):
        content = "\n".join(f"Строка {number}: Қазақша мәтін және русский текст." for number in range(240))
        pdf = render_draft_pdf(replace(self.data(), text=content, language="ru"))
        reader = PdfReader(BytesIO(pdf))
        self.assertGreater(len(reader.pages), 2)
        text = "\n".join(page.extract_text() for page in reader.pages)
        for number in range(240):
            self.assertIn(f"Строка {number}:", text)
        for number, page in enumerate(reader.pages, start=1):
            self.assertIn("Черновик", page.extract_text())
            self.assertIn(str(number), page.extract_text())
            self.assertFalse(page.get("/Annots"))
        self.assertNotIn("/OpenAction", reader.trailer["/Root"])

    def test_markup_is_literal_and_cannot_fetch_remote_or_local_resources(self):
        text = '<img src="https://example.test/private"/><a href="file:///secret">Текст</a> & {{x}}'
        with patch("urllib.request.urlopen", side_effect=AssertionError("No network")):
            pdf = render_draft_pdf(replace(self.data(), text=text, language="en"))
        reader = PdfReader(BytesIO(pdf))
        self.assertIn(text, reader.pages[0].extract_text().replace("\n", ""))
        self.assertFalse(reader.pages[0].get("/Annots"))
        self.assertNotIn("/JavaScript", reader.trailer["/Root"])

    def test_logo_pixels_are_embedded_and_metadata_is_removed(self):
        image = Image.new("RGB", (80, 40), "#006B50")
        output = BytesIO()
        image.save(output, format="PNG")
        pdf = render_draft_pdf(self.data(logo=output.getvalue()))
        reader = PdfReader(BytesIO(pdf))
        self.assertEqual(len(reader.pages[0].images), 1)
        self.assertEqual(reader.pages[0].images[0].image.size, (80, 40))

    def test_bad_logo_unsupported_glyph_and_invalid_input_fail_without_clinical_text(self):
        candidates = [replace(self.data(), logo=b'<svg><script/></svg>'), replace(self.data(), logo=b'x' * (2 * 1024 * 1024 + 1)),
            replace(self.data(), language="unknown"), replace(self.data(), title=""),
            replace(self.data(), text="Private medical text\x00"), replace(self.data(), text="Private medical text\U0001f600"),
            replace(self.data(), text="x" * 131073), replace(self.data(), created_at=datetime(2026, 1, 1))]
        for candidate in candidates:
            with self.subTest(language=candidate.language), self.assertRaises(DocumentRenderUnavailable) as error:
                render_draft_pdf(candidate)
            self.assertEqual(str(error.exception), "")

    def test_parallel_documents_keep_separate_text_and_stable_output(self):
        inputs = [replace(self.data(), text=f"Synthetic private document {index}") for index in range(4)]
        with ThreadPoolExecutor(max_workers=4) as executor:
            outputs = list(executor.map(render_draft_pdf, inputs))
        for index, (data, pdf) in enumerate(zip(inputs, outputs)):
            self.assertEqual(pdf, render_draft_pdf(data))
            self.assertIn(data.text, PdfReader(BytesIO(pdf)).pages[0].extract_text())
            for other in range(4):
                if other != index:
                    self.assertNotIn(inputs[other].text, PdfReader(BytesIO(pdf)).pages[0].extract_text())
