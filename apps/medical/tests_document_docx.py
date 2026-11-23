from dataclasses import replace
from datetime import datetime, timezone
from io import BytesIO
from unittest import TestCase
from zipfile import ZipFile

from docx import Document
from lxml import etree
from PIL import Image

from .document_docx import render_draft_docx
from .document_pdf import DraftPrintData, DocumentRenderUnavailable


class DraftDOCXTests(TestCase):
    def data(self):
        return DraftPrintData(title="Учебный документ / Үлгі құжат",
            text="Русский текст. Қазақша: Ә Ғ Қ Ң Ө Ұ Ү Һ І.\nSecond line",
            clinic_lines=("Synthetic clinic",), identity_lines=("Patient: Synthetic Patient", "Revision: 7"),
            created_at=datetime(2026, 11, 23, 8, 30, tzinfo=timezone.utc), language="kk")

    def test_exact_saved_text_and_localized_draft_in_stable_package(self):
        for language, label in (("ru", "Черновик"), ("kk", "Жоба"), ("en", "Draft")):
            data = replace(self.data(), language=language)
            body = render_draft_docx(data)
            self.assertEqual(body, render_draft_docx(data))
            document = Document(BytesIO(body))
            text = "\n".join(paragraph.text for paragraph in document.paragraphs)
            for expected in (data.title, data.text, *data.clinic_lines, *data.identity_lines):
                self.assertIn(expected, text)
            self.assertEqual(document.sections[0].header.paragraphs[0].text, label)
            self.assertEqual(document.core_properties.created, data.created_at)
            self.assertNotIn("Synthetic Patient", document.core_properties.title)
            self.assertEqual(document.core_properties.author, "Platforma CRM")

    def test_user_markup_is_literal_and_no_external_relationships_or_macros(self):
        text = '<w:fldSimple w:instr="INCLUDETEXT https://invalid.test/private"/> {{patient}} <script>&'
        body = render_draft_docx(replace(self.data(), text=text))
        self.assertEqual(Document(BytesIO(body)).paragraphs[-1].text, text)
        with ZipFile(BytesIO(body)) as archive:
            self.assertFalse(any("vba" in name.lower() for name in archive.namelist()))
            for name in archive.namelist():
                if name.endswith(".rels"):
                    root = etree.fromstring(archive.read(name))
                    self.assertFalse(root.xpath('//*[local-name()="Relationship"][@TargetMode="External"]'))
            root = etree.fromstring(archive.read("word/document.xml"))
            self.assertFalse(root.xpath('//*[local-name()="fldSimple" or local-name()="instrText"]'))

    def test_long_text_preserved_and_logo_captured_locally(self):
        output = BytesIO()
        Image.new("RGB", (80, 40), "#006B50").save(output, format="PNG")
        text = "\n".join(f"Строка {number}: Қазақша мәтін" for number in range(240))
        body = render_draft_docx(replace(self.data(), text=text, logo=output.getvalue()))
        document = Document(BytesIO(body))
        self.assertEqual(len(document.inline_shapes), 1)
        self.assertEqual("\n".join(p.text for p in document.paragraphs[-240:]), text)
        self.assertLessEqual(document.inline_shapes[0].width.mm, 38)

    def test_invalid_input_is_opaque(self):
        for data in (replace(self.data(), text="private\x00"), replace(self.data(), text="x" * 131073),
                     replace(self.data(), language="unknown"), replace(self.data(), logo=b"<svg/>"),
                     replace(self.data(), created_at=datetime(2026, 1, 1))):
            with self.assertRaises(DocumentRenderUnavailable) as caught:
                render_draft_docx(data)
            self.assertEqual(str(caught.exception), "")
