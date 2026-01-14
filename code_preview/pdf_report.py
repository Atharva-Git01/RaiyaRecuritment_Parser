# app/pdf_report.py
"""
PDF Report generator (Phase 5.6) — Corporate Blue style.

Usage:
    from app.pdf_report import generate_pdf_report
    generate_pdf_report(matcher_out, "storage/reports/report.pdf")

Produces a polished one-page (or multi-page if needed) PDF containing:
 - Header with overall score
 - Recruiter summary + candidate feedback
 - Radar chart (skills/tech/etc)
 - Coverage bars chart
 - Project keyword heatmap (small table)
 - Matched items tables (skills, tools, projects, certificates)
"""
import os
from io import BytesIO
from typing import Any, Dict, List

import matplotlib
import matplotlib.pyplot as plt
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Frame,
    Image,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# Ensure fonts render consistently
matplotlib.rcParams["font.size"] = 10

# Layout constants
PAGE_SIZE = A4  # Portrait. Use landscape(PAGE_SIZE) if you prefer wide layout.

# ===== Corporate Blue Header Bar =====
from reportlab.platypus import Flowable


class BlueHeader(Flowable):
    def __init__(self, title, score):
        Flowable.__init__(self)
        self.title = title
        self.score = score

    def draw(self):
        canvas = self.canv
        width = canvas._pagesize[0]

        # Blue header bar
        canvas.setFillColor(colors.HexColor("#0f4a7e"))
        canvas.rect(0, 0, width, 28, fill=1, stroke=0)

        # Header text
        canvas.setFillColor(colors.white)
        canvas.setFont("Helvetica-Bold", 14)
        canvas.drawString(15, 9, self.title)
        canvas.drawRightString(width - 15, 9, f"{self.score}%")


def _safe(m, key, default=None):
    return m.get(key, default) if isinstance(m, dict) else default


def _render_radar_chart(scores: Dict[str, int]) -> BytesIO:
    labels = list(scores.keys())
    values = [float(v) for v in scores.values()]

    num_vars = len(labels)
    angles = [n / float(num_vars) * 2 * 3.14159265 for n in range(num_vars)]
    angles += angles[:1]
    values += values[:1]

    fig = plt.figure(figsize=(4, 4), dpi=200)  # HIGH DPI
    ax = fig.add_subplot(111, polar=True)

    ax.set_theta_offset(3.14159265 / 2)
    ax.set_theta_direction(-1)

    ax.plot(angles, values, color="#0f4a7e", linewidth=2.5)
    ax.fill(angles, values, color="#0f4a7e", alpha=0.22)

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels, fontsize=9)

    ax.set_yticks([20, 40, 60, 80, 100])
    ax.set_ylim(0, 100)
    ax.grid(color="#88aacc", linestyle="--", alpha=0.6)

    buf = BytesIO()
    fig.tight_layout()
    fig.savefig(buf, format="png", dpi=200)
    plt.close(fig)
    buf.seek(0)
    return buf


def _render_bar_chart(coverage: List[Dict[str, Any]]) -> BytesIO:
    labels = [c["category"] for c in coverage]
    matched = [float(c["matched"]) for c in coverage]
    total = [float(c["total"]) for c in coverage]

    pct = [(m / t * 100) if t else 0 for m, t in zip(matched, total)]
    pct = [min(100, max(0, p)) for p in pct]

    fig, ax = plt.subplots(figsize=(6, 3), dpi=200)

    y = range(len(labels))
    ax.barh(y, pct, color="#0f4a7e", edgecolor="#072f57", height=0.45)

    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=9)
    ax.set_xlim(0, 100)
    ax.set_xlabel("Coverage (%)", fontsize=9)

    ax.xaxis.grid(True, linestyle="--", color="#aac4dd", alpha=0.5)

    for i, v in enumerate(pct):
        ax.text(v + 1, i, f"{int(v)}%", va="center", fontsize=9)

    fig.tight_layout()
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=200)
    plt.close(fig)
    buf.seek(0)
    return buf


def _make_table_from_pairs(pairs: List[List[str]], col_widths=None) -> Table:
    t = Table(pairs, colWidths=col_widths)
    style = TableStyle(
        [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f4a7e")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("BACKGROUND", (0, 1), (-1, 1), colors.whitesmoke),
            # Alternating row colors
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.lightgrey]),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
            ("BOX", (0, 0), (-1, -1), 0.25, colors.grey),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]
    )

    t.setStyle(style)
    return t


def _shorten_list(items: List[str], limit=6) -> List[str]:
    if not items:
        return []
    out = [str(i) for i in items[:limit]]
    if len(items) > limit:
        out.append(f"... +{len(items)-limit} more")
    return out


def section_title(text: str):
    return Paragraph(
        f"<para alignment='left'><font color='#0f4a7e'><b>{text}</b></font></para>",
        ParagraphStyle(
            name="SectionTitle",
            fontSize=13,
            leading=16,
            leftIndent=0,
            spaceBefore=10,
            spaceAfter=4,
        ),
    )


def generate_pdf_report(matcher_out: Dict[str, Any], output_path: str) -> str:
    """
    Generate a multi-section Corporate Blue PDF using matcher_out payload.
    Returns the generated file path.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # Basic styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "Title",
        parent=styles["Heading1"],
        alignment=1,
        textColor=colors.HexColor("#0f4a7e"),
        fontSize=18,
        leading=22,
    )
    subtitle_style = ParagraphStyle(
        "Subtitle",
        parent=styles["Heading3"],
        alignment=1,
        textColor=colors.HexColor("#0f4a7e"),
        fontSize=10,
    )
    normal = styles["BodyText"]
    normal.spaceAfter = 6

    # Data extraction
    recruiter_text = matcher_out.get("recruiter_text_summary", "")
    candidate_feedback = matcher_out.get("candidate_feedback", "")
    structured = matcher_out.get("structured_explanation", {}) or {}
    visual = matcher_out.get("visual_payload", {}) or {}
    matched = matcher_out.get("matched_items", {}) or {}
    details = matcher_out.get("details", {}) or {}
    scores = structured.get("scores", matcher_out.get("summary_scores", {})) or {}

    # Radar source mapping (ensure order)
    radar_map = {
        "Experience": scores.get("experience_score", 0),
        "Skills": scores.get("skills_score", 0),
        "Technologies": scores.get("technologies_score", 0),
        "Tools": scores.get("tools_score", 0),
        "Projects": scores.get("projects_score", 0),
        "Certificates": scores.get("certificates_score", 0),
        "Responsibilities": scores.get("responsibilities_score", 0),
        "Relevant Exp": scores.get("relevant_experience_score", 0),
    }

    # Build document
    doc = SimpleDocTemplate(
        output_path,
        pagesize=PAGE_SIZE,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
    )

    story = []

    # Header
    overall = matcher_out.get(
        "final_score", matcher_out.get("summary_scores", {}).get("final_score", 0)
    )
    story.append(BlueHeader("Candidate Fit Report", overall))
    story.append(Spacer(1, 16))

    # Two-column top: recruiter summary + radar chart
    # Create radar image
    radar_buf = _render_radar_chart(radar_map)
    radar_img = Image(radar_buf, width=150, height=110)

    left_col = []
    left_col.append(section_title("Recruiter Summary"))
    left_col.append(Paragraph(recruiter_text, normal))
    left_col.append(Spacer(1, 6))
    left_col.append(section_title("Candidate Feedback"))
    left_col.append(Paragraph(candidate_feedback, normal))

    # Assemble a simple table with two columns
    left_flow = left_col

    # Table for two-column
    table_data = [[left_flow, radar_img]]

    t = Table(
        table_data,
        colWidths=[135 * mm, 45 * mm],  # more space on left
        style=[
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ],
    )

    story.append(t)
    story.append(Spacer(1, 10))

    # Coverage bars image
    coverage = visual.get("coverage_bars", [])
    if coverage:
        bar_buf = _render_bar_chart(coverage)
        story.append(section_title("Coverage Overview"))
        story.append(Image(bar_buf, width=390, height=110, hAlign="LEFT"))
        story.append(Spacer(1, 10))

    # Project keyword heatmap (table)
    pk = visual.get("project_keyword_heatmap", {}) or {}
    story.append(section_title("Project Keywords"))
    pk_matched = pk.get("matched", []) or []
    pk_missing = pk.get("missing", []) or []
    pk_pairs = [["Matched", "Missing"]]
    max_len = max(len(pk_matched), len(pk_missing))
    for i in range(max_len):
        a = pk_matched[i] if i < len(pk_matched) else ""
        b = pk_missing[i] if i < len(pk_missing) else ""
        pk_pairs.append([a, b])
    story.append(_make_table_from_pairs(pk_pairs, col_widths=[80 * mm, 80 * mm]))
    story.append(Spacer(1, 10))

    story.append(Spacer(1, 10))
    story.append(section_title("Matched Items"))

    # Skills table
    skills = matched.get("skills", {}) or {}
    sk_mat = _shorten_list(skills.get("matched", []))
    sk_mis = _shorten_list(skills.get("missing", []))
    pairs = [["Skills (matched)", "Skills (missing)"]]
    max_len = max(len(sk_mat), len(sk_mis))
    for i in range(max_len):
        a = sk_mat[i] if i < len(sk_mat) else ""
        b = sk_mis[i] if i < len(sk_mis) else ""
        pairs.append([a, b])
    story.append(_make_table_from_pairs(pairs, col_widths=[90 * mm, 90 * mm]))
    story.append(Spacer(1, 6))
    story.append(section_title("Technologies"))

    # Technologies table
    tech = matched.get("technologies", {}) or {}
    tech_mat = _shorten_list(tech.get("matched", []))
    tech_mis = _shorten_list(tech.get("missing", []))

    pairs = [["Technologies (matched)", "Technologies (missing)"]]
    max_len = max(len(tech_mat), len(tech_mis))
    for i in range(max_len):
        a = tech_mat[i] if i < len(tech_mat) else ""
        b = tech_mis[i] if i < len(tech_mis) else ""
        pairs.append([a, b])

    story.append(_make_table_from_pairs(pairs, col_widths=[90 * mm, 90 * mm]))
    story.append(Spacer(1, 6))

    # Tools table
    tools = matched.get("tools", {}) or {}
    tw_mat = _shorten_list(tools.get("matched", []))
    tw_mis = _shorten_list(tools.get("missing", []))
    pairs = [["Tools (matched)", "Tools (missing)"]]
    max_len = max(len(tw_mat), len(tw_mis))
    for i in range(max_len):
        a = tw_mat[i] if i < len(tw_mat) else ""
        b = tw_mis[i] if i < len(tw_mis) else ""
        pairs.append([a, b])
    story.append(_make_table_from_pairs(pairs, col_widths=[90 * mm, 90 * mm]))
    story.append(Spacer(1, 6))

    # Certificates
    certs = matched.get("certificates", {}) or {}
    c_mat = _shorten_list(certs.get("matched", []))
    c_mis = _shorten_list(certs.get("missing", []))
    pairs = [["Certificates (matched)", "Certificates (missing)"]]
    max_len = max(len(c_mat), len(c_mis))
    for i in range(max_len):
        a = c_mat[i] if i < len(c_mat) else ""
        b = c_mis[i] if i < len(c_mis) else ""
        pairs.append([a, b])
    story.append(_make_table_from_pairs(pairs, col_widths=[90 * mm, 90 * mm]))
    story.append(Spacer(1, 10))

    # Footer: scores table small
    story.append(section_title("Score Breakdown"))
    scores_pairs = [["Category", "Score (%)"]]
    for k, v in radar_map.items():
        scores_pairs.append([k, str(int(v))])
    scores_table = _make_table_from_pairs(scores_pairs, col_widths=[120 * mm, 60 * mm])
    story.append(scores_table)
    story.append(Spacer(1, 10))

    # Write PDF
    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.grey)
        canvas.drawString(
            18 * mm,
            12 * mm,
            "Generated by Raiya Recruitment Solutions • Intelligent Resume Fit Report",
        )
        canvas.restoreState()

    doc.build(story, onFirstPage=footer, onLaterPages=footer)

    return output_path
