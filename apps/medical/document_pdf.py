"""Internal draft rendering. Access and immutable storage belong to the caller."""

from dataclasses import dataclass
from datetime import datetime, timezone
from functools import lru_cache
from io import BytesIO
from pathlib import Path
from threading import Lock
from xml.sax.saxutils import escape

from PIL import Image
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import Image as PDFImage, Paragraph, SimpleDocTemplate, Spacer
from .document_logo import normalize_document_logo


class DocumentRenderUnavailable(Exception):
    pass


@dataclass(frozen=True)
class DraftPrintData:
    title: str
    text: str
    clinic_lines: tuple[str, ...]
    identity_lines: tuple[str, ...]
    created_at: datetime
    language: str
    logo: bytes | None = None


FONT_ROOT = Path(__file__).parent / "assets" / "fonts"
REGULAR = "MedicalNotoSans"
BOLD = "MedicalNotoSansBold"
FONT_LOCK = Lock()
MAX_TEXT = 131072
MAX_PAGES = 100
DRAFT_LABELS = {"ru": "Черновик", "kk": "Жоба", "en": "Draft"}
FOOTER = "Документ сформирован в Platforma CRM"


@lru_cache(maxsize=1)
def _fonts():
    with FONT_LOCK:
        for name, filename in ((REGULAR, "NotoSans-Regular.ttf"), (BOLD, "NotoSans-Bold.ttf")):
            if name not in pdfmetrics.getRegisteredFontNames():
                pdfmetrics.registerFont(TTFont(name, str(FONT_ROOT / filename)))
        return frozenset(pdfmetrics.getFont(REGULAR).face.charToGlyph), frozenset(pdfmetrics.getFont(BOLD).face.charToGlyph)


def _literal(value):
    return escape(value.replace("\r\n", "\n").replace("\r", "\n").replace("\t", "    ")).replace("\n", "<br/>")


def _validate(data):
    if not isinstance(data, DraftPrintData) or data.language not in DRAFT_LABELS:
        raise ValueError
    if not isinstance(data.created_at, datetime) or data.created_at.tzinfo is None or data.created_at.utcoffset() is None:
        raise ValueError
    if not isinstance(data.title, str) or not data.title.strip() or len(data.title) > 255:
        raise ValueError
    if not isinstance(data.text, str) or len(data.text) > MAX_TEXT:
        raise ValueError
    for lines in (data.clinic_lines, data.identity_lines):
        if not isinstance(lines, tuple) or len(lines) > 12:
            raise ValueError
        if any(not isinstance(line, str) or len(line) > 2000 for line in lines):
            raise ValueError
        if sum(len(line) for line in lines) > 6000:
            raise ValueError
    regular, bold = _fonts()
    for value, supported in ((data.title, bold), (data.text, regular),
            ("\n".join((*data.clinic_lines, *data.identity_lines, FOOTER, DRAFT_LABELS[data.language])), regular)):
        if any(character not in "\n\r\t" and (ord(character) < 32 or ord(character) not in supported) for character in value):
            raise ValueError


def _logo(source):
    if source is None:
        return None
    normalized = normalize_document_logo(source)
    with Image.open(BytesIO(normalized)) as image:
        width, height = image.size
    body = BytesIO(normalized)
    scale = min(38 * mm / width, 18 * mm / height)
    result = PDFImage(body, width=width * scale, height=height * scale)
    result.hAlign = "LEFT"
    return result


def render_draft_pdf(data: DraftPrintData) -> bytes:
    """Render captured data without fetching URLs, evaluating templates or reading the DB."""
    try:
        _validate(data)
        output = BytesIO()
        document = SimpleDocTemplate(output, pagesize=A4, leftMargin=20 * mm, rightMargin=20 * mm,
            topMargin=22 * mm, bottomMargin=22 * mm, title="Medical document draft", author="Platforma CRM")
        body_style = ParagraphStyle("MedicalBody", fontName=REGULAR, fontSize=10.5, leading=15,
            spaceAfter=4 * mm, splitLongWords=True, allowWidows=0, allowOrphans=0)
        detail_style = ParagraphStyle("MedicalDetails", parent=body_style, fontSize=9, leading=12,
            textColor=colors.HexColor("#374151"), spaceAfter=1.5 * mm)
        title_style = ParagraphStyle("MedicalTitle", parent=body_style, fontName=BOLD,
            fontSize=16, leading=21, spaceBefore=4 * mm, spaceAfter=5 * mm)
        story = []
        logo = _logo(data.logo)
        if logo is not None:
            story.extend((logo, Spacer(1, 3 * mm)))
        story.extend(Paragraph(_literal(line), detail_style) for line in data.clinic_lines if line.strip())
        story.append(Paragraph(_literal(data.title), title_style))
        story.extend(Paragraph(_literal(line), detail_style) for line in data.identity_lines if line.strip())
        story.append(Spacer(1, 4 * mm))
        story.append(Paragraph(_literal(data.text), body_style))

        def page_frame(canvas, doc):
            if doc.page > MAX_PAGES:
                raise ValueError
            canvas.saveState()
            canvas.setFont(REGULAR, 8)
            canvas.setFillColor(colors.HexColor("#374151"))
            canvas.drawRightString(A4[0] - 20 * mm, A4[1] - 13 * mm, DRAFT_LABELS[data.language])
            canvas.setFont(REGULAR, 7.5)
            canvas.drawString(20 * mm, 12 * mm, FOOTER)
            canvas.drawRightString(A4[0] - 20 * mm, 12 * mm, str(doc.page))
            canvas.restoreState()

        def stable_canvas(*args, **kwargs):
            canvas = Canvas(*args, **(kwargs | {"invariant": 1, "pageCompression": 1}))
            stamp = data.created_at.astimezone(timezone.utc).strftime("D:%Y%m%d%H%M%S+00'00'")
            canvas.setDateFormatter(lambda *unused: stamp)
            return canvas

        document.build(story, onFirstPage=page_frame, onLaterPages=page_frame, canvasmaker=stable_canvas)
        result = output.getvalue()
        if not result.startswith(b"%PDF-") or len(result) > 10 * 1024 * 1024:
            raise ValueError
        return result
    except Exception:
        # Library exceptions can contain clinical text; callers receive no partial PDF.
        raise DocumentRenderUnavailable() from None
