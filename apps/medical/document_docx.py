"""Editable draft bytes from a captured document version; no live data or URLs."""

from datetime import timezone
from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Mm, Pt, RGBColor
from PIL import Image

from .document_logo import normalize_document_logo
from .document_pdf import DRAFT_LABELS, FOOTER, DraftPrintData, DocumentRenderUnavailable, _validate


def render_draft_docx(data: DraftPrintData) -> bytes:
    try:
        _validate(data)
        document = Document()
        section = document.sections[0]
        section.page_width, section.page_height = Mm(210), Mm(297)
        section.left_margin = section.right_margin = Mm(20)
        section.top_margin = section.bottom_margin = Mm(22)
        section.header_distance = section.footer_distance = Mm(10)
        for name, size in (("Normal", 11), ("Title", 16), ("Header", 9), ("Footer", 8)):
            style = document.styles[name]
            style.font.name, style.font.size = "Noto Sans", Pt(size)
            style.font.color.rgb = RGBColor(0, 0, 0)
            style.paragraph_format.space_after = Pt(6)
        document.styles["Normal"].paragraph_format.widow_control = True
        document.styles["Title"].paragraph_format.keep_with_next = True
        header = section.header.paragraphs[0]
        header.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        header.add_run(DRAFT_LABELS[data.language])
        footer = section.footer.paragraphs[0]
        footer.add_run(FOOTER + " — ")
        field = OxmlElement("w:fldSimple")
        field.set(qn("w:instr"), "PAGE")
        footer._p.append(field)
        if data.logo is not None:
            logo = normalize_document_logo(data.logo)
            with Image.open(BytesIO(logo)) as source:
                width, height = source.size
            scale = min(38 / width, 18 / height)
            picture = document.add_paragraph().add_run().add_picture(
                BytesIO(logo), width=Mm(width * scale), height=Mm(height * scale))
            picture._inline.docPr.set("descr", "Clinic logo")
        for line in data.clinic_lines:
            document.add_paragraph(line)
        document.add_paragraph(data.title, style="Title")
        for line in data.identity_lines:
            document.add_paragraph(line)
        for line in data.text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
            document.add_paragraph(line)
        properties = document.core_properties
        properties.title = "Medical document draft"
        properties.author = properties.last_modified_by = "Platforma CRM"
        properties.comments = ""
        properties.created = properties.modified = data.created_at.astimezone(timezone.utc)
        output = BytesIO()
        document.save(output)
        # ZIP member dates otherwise depend on the render machine's wall clock.
        stable = BytesIO()
        with ZipFile(output) as source, ZipFile(stable, "w", ZIP_DEFLATED) as target:
            for name in sorted(source.namelist()):
                entry = ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
                entry.compress_type = ZIP_DEFLATED
                target.writestr(entry, source.read(name))
        body = stable.getvalue()
        if len(body) > 10 * 1024 * 1024:
            raise ValueError
        return body
    except Exception:
        raise DocumentRenderUnavailable() from None
