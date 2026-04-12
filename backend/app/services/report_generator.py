from io import BytesIO
from typing import Dict

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def build_report_pdf(analysis: Dict) -> bytes:
    """Generate a downloadable PDF report from JSON analysis data."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, title="Smart Resume Analyzer Report")
    styles = getSampleStyleSheet()

    story = []
    story.append(Paragraph("Smart Resume Analyzer - Report", styles["Title"]))
    story.append(Spacer(1, 12))

    score = analysis.get("resume_score", "N/A")
    story.append(Paragraph(f"Resume Score: <b>{score}/100</b>", styles["Heading2"]))
    story.append(Spacer(1, 12))

    detected = ", ".join(analysis.get("detected_skills", [])) or "None"
    missing = ", ".join(analysis.get("missing_skills", [])) or "None"

    table_data = [
        ["Section", "Details"],
        ["Detected Skills", detected],
        ["Missing Skills", missing],
    ]

    table = Table(table_data, colWidths=[130, 380])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#12343B")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.8, colors.HexColor("#D9E4E8")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.HexColor("#F7FAFC")]),
            ]
        )
    )

    story.append(table)
    story.append(Spacer(1, 14))

    feedback = analysis.get("feedback", {})
    summary = feedback.get("professional_summary", [])
    suggestions = feedback.get("suggestions", [])

    story.append(Paragraph("Professional Feedback", styles["Heading2"]))
    for item in summary:
        story.append(Paragraph(f"- {item}", styles["BodyText"]))

    story.append(Spacer(1, 8))
    story.append(Paragraph("Suggestions", styles["Heading2"]))
    for item in suggestions:
        story.append(Paragraph(f"- {item}", styles["BodyText"]))

    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
