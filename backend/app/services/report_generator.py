"""Render an analysis payload to a PDF report."""

from html import escape
from io import BytesIO
from typing import Any, Dict, List

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

INK = colors.HexColor("#1C1917")
MUTED = colors.HexColor("#78716C")
RULE = colors.HexColor("#E7E5E4")
ACCENT = colors.HexColor("#166534")


def _as_text_list(value: Any) -> List[str]:
    """Coerce arbitrary JSON into a list of display strings."""
    if isinstance(value, str):
        return [value]
    if isinstance(value, (list, tuple)):
        return [str(item) for item in value if item is not None]
    if value is None:
        return []
    return [str(value)]


def _safe(value: Any) -> str:
    """Escape for ReportLab, which parses a mini-HTML markup in paragraphs."""
    return escape(str(value), quote=False)


def _join(values: Any, fallback: str = "None") -> str:
    items = _as_text_list(values)
    return _safe(", ".join(items)) if items else fallback


def _band(score: Any) -> str:
    try:
        value = float(score)
    except (TypeError, ValueError):
        return "Not scored"
    if value >= 85:
        return "Ready to send"
    if value >= 70:
        return "Competitive with a few fixes"
    if value >= 55:
        return "Needs work"
    return "Not yet screening-ready"


def build_report_pdf(analysis: Dict) -> bytes:
    """Generate a downloadable PDF report from JSON analysis data.

    The payload comes straight from a client, so every value is coerced and
    escaped rather than trusted to be the shape the analyzer produces.
    """
    if not isinstance(analysis, dict):
        raise ValueError("Analysis payload must be a JSON object.")

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        title="Resume Analysis Report",
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
    )
    styles = getSampleStyleSheet()
    body = ParagraphStyle("Body", parent=styles["BodyText"], fontSize=9.5, leading=14, textColor=INK)
    small = ParagraphStyle("Small", parent=body, fontSize=8.5, textColor=MUTED)
    h2 = ParagraphStyle("H2", parent=styles["Heading2"], fontSize=12, spaceBefore=14,
                        spaceAfter=6, textColor=INK)

    story: List[Any] = []
    score = analysis.get("resume_score", "N/A")

    story.append(Paragraph("Resume Analysis Report", styles["Title"]))
    story.append(Paragraph(
        f'<font size="26"><b>{_safe(score)}</b></font><font size="12" color="#78716C">/100</font>'
        f'  &nbsp;&nbsp;{_safe(_band(score))}',
        ParagraphStyle("Score", parent=body, fontSize=26, leading=30),
    ))
    story.append(Spacer(1, 10))

    # --- what to fix first --------------------------------------------------
    feedback = analysis.get("feedback")
    feedback = feedback if isinstance(feedback, dict) else {}

    actions = feedback.get("priority_actions")
    if isinstance(actions, list) and actions:
        story.append(Paragraph("Fix these first", h2))
        rows = [["#", "Action", "Worth"]]
        for index, action in enumerate(actions[:8], 1):
            if not isinstance(action, dict):
                continue
            title = _safe(action.get("title", ""))
            detail = _safe(action.get("detail", ""))
            impact = action.get("impact_points", 0)
            rows.append([
                str(index),
                Paragraph(f"<b>{title}</b><br/><font size='8.5' color='#78716C'>{detail}</font>", body),
                Paragraph(f"<b>+{_safe(impact)}</b>" if impact else "&mdash;", small),
            ])
        table = Table(rows, colWidths=[10 * mm, 130 * mm, 20 * mm], repeatRows=1)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F5F5F4")),
            ("TEXTCOLOR", (0, 0), (-1, 0), MUTED),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("LINEBELOW", (0, 0), (-1, -1), 0.5, RULE),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("TEXTCOLOR", (2, 1), (2, -1), ACCENT),
        ]))
        story.append(table)

    # --- score breakdown ----------------------------------------------------
    breakdown = analysis.get("score_breakdown")
    if isinstance(breakdown, dict) and breakdown:
        story.append(Paragraph("Score breakdown", h2))
        rows = [["Component", "Score", "Weight"]]
        ordered = sorted(
            ((name, data) for name, data in breakdown.items() if isinstance(data, dict)),
            key=lambda item: -(float(item[1].get("weight") or 0)),
        )
        for name, data in ordered:
            rows.append([
                Paragraph(f"<b>{_safe(name.replace('_', ' ').title())}</b><br/>"
                          f"<font size='8.5' color='#78716C'>{_safe(data.get('description', ''))}</font>", body),
                Paragraph(f"{_safe(data.get('score', 'N/A'))}/100", body),
                Paragraph(f"{round(float(data.get('weight') or 0) * 100)}%", small),
            ])
        table = Table(rows, colWidths=[120 * mm, 22 * mm, 18 * mm], repeatRows=1)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F5F5F4")),
            ("TEXTCOLOR", (0, 0), (-1, 0), MUTED),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("LINEBELOW", (0, 0), (-1, -1), 0.5, RULE),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(table)

    # --- skills -------------------------------------------------------------
    story.append(Paragraph("Skills", h2))
    skill_rows = [
        ["Detected", Paragraph(_join(analysis.get("detected_skills")), body)],
        ["Missing for this role", Paragraph(_join(analysis.get("missing_skills"), "None"), body)],
    ]
    disclaimed = _as_text_list(analysis.get("disclaimed_skills"))
    if disclaimed:
        skill_rows.append([
            "Disclaimed",
            Paragraph(_join(disclaimed) + " <font color='#78716C'>(mentioned negatively "
                      "or aspirationally, so not counted)</font>", body),
        ])
    table = Table(skill_rows, colWidths=[35 * mm, 125 * mm])
    table.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("TEXTCOLOR", (0, 0), (0, -1), MUTED),
        ("LINEBELOW", (0, 0), (-1, -1), 0.5, RULE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(table)

    # --- strengths and narrative -------------------------------------------
    strengths = _as_text_list(feedback.get("strengths"))
    if strengths:
        story.append(Paragraph("What is already working", h2))
        for item in strengths:
            story.append(Paragraph(f"&bull; {_safe(item)}", body))

    summary = _as_text_list(feedback.get("professional_summary"))
    if summary:
        story.append(Paragraph("Assessment", h2))
        for item in summary:
            story.append(Paragraph(_safe(item), body))

    ai = analysis.get("ai_insights")
    if isinstance(ai, dict):
        rewrites = ai.get("rewrite_suggestions")
        if isinstance(rewrites, list) and rewrites:
            story.append(Paragraph("Suggested rewrites", h2))
            for item in rewrites:
                if not isinstance(item, dict):
                    continue
                story.append(KeepTogether([
                    Paragraph(f"<font color='#78716C'>Before:</font> {_safe(item.get('original', ''))}", small),
                    Paragraph(f"<font color='#166534'>After:</font> {_safe(item.get('improved', ''))}", body),
                    Spacer(1, 6),
                ]))

    if len(story) <= 3:
        story.append(Paragraph("No analysis details were included in this report.", body))

    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
