from io import BytesIO

from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.units import inch


def build_pdf(title: str, business_name: str, sections: list[tuple[str, str]]) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=LETTER,
        rightMargin=0.65 * inch,
        leftMargin=0.65 * inch,
        topMargin=0.65 * inch,
        bottomMargin=0.65 * inch,
    )

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="CenterTitle",
        parent=styles["Title"],
        alignment=TA_CENTER,
        spaceAfter=12,
    ))
    styles.add(ParagraphStyle(
        name="Section",
        parent=styles["Heading2"],
        spaceBefore=12,
        spaceAfter=8,
    ))
    styles.add(ParagraphStyle(
        name="BodyCustom",
        parent=styles["BodyText"],
        leading=15,
        spaceAfter=8,
    ))

    story = [
        Paragraph("Fitzery Marketing", styles["CenterTitle"]),
        Paragraph(title, styles["Heading1"]),
        Paragraph(f"Prepared for {business_name}", styles["BodyCustom"]),
        Spacer(1, 12),
    ]

    for heading, content in sections:
        story.append(Paragraph(heading, styles["Section"]))
        safe = (
            content.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace("\n", "<br/>")
        )
        story.append(Paragraph(safe, styles["BodyCustom"]))

    doc.build(story)
    return buffer.getvalue()
