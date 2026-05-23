"""
RAIYA Pipeline 3 Node — Report Generator.
Batch ranking + DB write + PDF generation.

Generates:
  1. JSON match result → saved to match_results table
  2. PDF report → saved to storage/reports/<batch_id>/
"""

import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

from langgraph.runtime import Runtime
from sqlalchemy import text

from app.agents import PipelineContext, PipelineState
from app.core.hashing import hash_json
from app.core.logging_config import get_logger
from app.db.database import AsyncSessionLocal

logger = get_logger("ReportGeneratorNode")

# ── PDF report output directory ──────────────────────────────────
REPORT_DIR = Path("storage/reports")


async def report_generator_node(
    state: PipelineState,
    runtime: Runtime[PipelineContext],
) -> dict:
    """
    Generate final report (JSON + PDF), update batch ranking, save to DB.

    Steps:
      1. Determine recommendation tier
      2. Save match result JSON to match_results table
      3. Generate PDF report with score breakdown + explanation
      4. Update batch counters
    """
    match_output = state.get("match_output", {})
    final_score = state.get("final_score", 0)
    batch_id = state.get("batch_id")
    resume_file_id = state.get("resume_file_id")
    jd_id = state.get("jd_id")

    try:
        # ── Step 1: Determine recommendation ─────────────────
        if final_score >= 85:
            recommendation = "excellent"
        elif final_score >= 70:
            recommendation = "good"
        elif final_score >= 55:
            recommendation = "average"
        elif final_score >= 40:
            recommendation = "poor"
        else:
            recommendation = "rejected"

        # ── Step 2: Save match result to DB ──────────────────
        async with AsyncSessionLocal() as session:
            await session.execute(
                text("""
                    INSERT INTO match_results 
                    (id, batch_id, resume_file_id, jd_id, output_hash,
                     final_result_json, final_score, deterministic_report,
                     mathematical_report, rule_based_evidence, rag_final_verdict,
                     reasoning_labels, reasoning_context, llm_explanation,
                     explanation_hash, guardrails_applied, recommendation,
                     is_valid, hallucinations_detected, is_confident,
                     math_accuracy, mae)
                    VALUES (:id, :bid, :rid, :jid, :ohash,
                            :frj, :fs, :dr, :mr, :rbe, :rfv,
                            :rl, :rc, :le, :eh, :ga, :rec,
                            :iv, :hd, :ic, :ma, :mae)
                """),
                {
                    "id": str(uuid.uuid4()),
                    "bid": batch_id, "rid": resume_file_id, "jid": jd_id,
                    "ohash": state.get("output_hash", ""),
                    "frj": str(match_output) if match_output else None,
                    "fs": final_score,
                    "dr": str(state.get("deterministic_report", {})),
                    "mr": str(state.get("mathematical_report", {})),
                    "rbe": str(state.get("rule_based_evidence", {})),
                    "rfv": str(state.get("rag_final_verdict", {})),
                    "rl": str(state.get("reasoning_labels", {})),
                    "rc": state.get("reasoning_context", ""),
                    "le": state.get("llm_explanation", ""),
                    "eh": state.get("explanation_hash", ""),
                    "ga": str(match_output.get("result", {}).get("guardrails_applied", [])),
                    "rec": recommendation,
                    "iv": state.get("agent_state") == "COMPLETED",
                    "hd": False, "ic": True,
                    "ma": state.get("mathematical_report", {}).get("global_metrics", {}).get("overall_accuracy", 0),
                    "mae": state.get("mathematical_report", {}).get("global_metrics", {}).get(
                        "importance_weighted_mae",
                        state.get("mathematical_report", {}).get("global_metrics", {}).get("mae", 0),
                    ),
                }
            )
            # Update batch counters
            if batch_id:
                await session.execute(
                    text("UPDATE batches SET completed = completed + 1 WHERE id = :bid"),
                    {"bid": batch_id}
                )
            await session.commit()

        # ── Step 3: Generate PDF Report ──────────────────────
        pdf_path = _generate_pdf_report(
            match_output=match_output,
            final_score=final_score,
            recommendation=recommendation,
            batch_id=batch_id,
            resume_file_id=resume_file_id,
            jd_id=jd_id,
            explanation=state.get("llm_explanation", ""),
            rag_verdict=state.get("rag_final_verdict", {}),
        )

        logger.info(
            f"Report saved: score={final_score}, recommendation={recommendation}, "
            f"pdf={pdf_path}"
        )

        return {
            "report_path": str(pdf_path) if pdf_path else "",
            "report_hash": state.get("output_hash", ""),
            "agent_state": "COMPLETED",
        }

    except Exception as e:
        logger.error(f"Report generation failed: {e}")
        return {
            "errors": state.get("errors", []) + [f"Report gen failed: {str(e)}"],
        }


# ═══════════════════════════════════════════════════════════════════════
# PDF Generation
# ═══════════════════════════════════════════════════════════════════════

def _generate_pdf_report(
    match_output: dict,
    final_score: float,
    recommendation: str,
    batch_id: str,
    resume_file_id: str,
    jd_id: str,
    explanation: str = "",
    rag_verdict: dict = None,
) -> str:
    """
    Generate a PDF report with score breakdown, explanation, and verdict.
    Uses ReportLab for PDF generation.

    Returns:
        Path to the generated PDF file.
    """
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import mm
        from reportlab.lib.colors import HexColor
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        )
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    except ImportError:
        logger.warning("ReportLab not installed — skipping PDF generation")
        return ""

    # ── Ensure output directory ──────────────────────────────
    batch_dir = REPORT_DIR / (batch_id or "unlinked")
    batch_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"report_{resume_file_id or 'unknown'}_{timestamp}.pdf"
    pdf_path = batch_dir / filename

    # ── Build PDF ────────────────────────────────────────────
    doc = SimpleDocTemplate(
        str(pdf_path), pagesize=A4,
        leftMargin=20*mm, rightMargin=20*mm,
        topMargin=20*mm, bottomMargin=20*mm,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "RAIYATitle", parent=styles["Title"],
        fontSize=18, textColor=HexColor("#1a1a2e"),
    )
    heading_style = ParagraphStyle(
        "RAIYAHeading", parent=styles["Heading2"],
        fontSize=14, textColor=HexColor("#16213e"),
        spaceAfter=6,
    )
    body_style = ParagraphStyle(
        "RAIYABody", parent=styles["Normal"],
        fontSize=10, leading=14,
    )

    elements = []

    # ── Header ───────────────────────────────────────────────
    elements.append(Paragraph("RAIYA — AI Resume Screening Report", title_style))
    elements.append(Spacer(1, 4*mm))

    # ── Summary table ────────────────────────────────────────
    rec_colors = {
        "excellent": "#27ae60", "good": "#2ecc71",
        "average": "#f39c12", "poor": "#e74c3c", "rejected": "#c0392b",
    }
    rec_color = rec_colors.get(recommendation, "#333333")

    summary_data = [
        ["Final Score", f"{final_score:.2f} / 100"],
        ["Recommendation", recommendation.upper()],
        ["Batch ID", str(batch_id or "N/A")[:36]],
        ["JD ID", str(jd_id or "N/A")[:36]],
        ["Resume ID", str(resume_file_id or "N/A")[:36]],
        ["Generated", datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")],
    ]
    summary_table = Table(summary_data, colWidths=[120, 340])
    summary_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), HexColor("#f0f0f5")),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("TEXTCOLOR", (1, 1), (1, 1), HexColor(rec_color)),
        ("FONTNAME", (1, 1), (1, 1), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#cccccc")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("PADDING", (0, 0), (-1, -1), 6),
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 6*mm))

    # ── Section Scores ───────────────────────────────────────
    result = match_output.get("result", {})
    scoring_trace = result.get("scoring_trace", {})

    if scoring_trace:
        elements.append(Paragraph("Section Score Breakdown", heading_style))
        score_data = [["Section", "Score", "Weight", "Notes"]]
        for section, trace in scoring_trace.items():
            score_data.append([
                section.replace("_", " ").title(),
                f"{trace.get('score_awarded', 0):.2f}",
                f"{trace.get('weight', 0)}",
                str(trace.get("notes", ""))[:60],
            ])
        score_table = Table(score_data, colWidths=[120, 60, 60, 220])
        score_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), HexColor("#1a1a2e")),
            ("TEXTCOLOR", (0, 0), (-1, 0), HexColor("#ffffff")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#cccccc")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [HexColor("#ffffff"), HexColor("#f8f8fc")]),
            ("PADDING", (0, 0), (-1, -1), 5),
        ]))
        elements.append(score_table)
        elements.append(Spacer(1, 6*mm))

    # ── RAG Verdict ──────────────────────────────────────────
    if rag_verdict:
        elements.append(Paragraph("Validation Verdict", heading_style))
        verdict_text = (
            f"Verdict: {rag_verdict.get('verdict', 'N/A')} | "
            f"Accuracy: {rag_verdict.get('overall_accuracy', 'N/A')}% | "
            f"Confidence: {rag_verdict.get('confidence', 'N/A')} | "
            f"Importance-MAE: {rag_verdict.get('importance_weighted_mae', 'N/A')}"
        )
        elements.append(Paragraph(verdict_text, body_style))
        if not rag_verdict.get("jd_weights_math_valid", True):
            elements.append(Paragraph(
                "Warning: JD weight pipeline math validation failed — "
                "section weights may be unreliable.",
                body_style,
            ))
        elements.append(Spacer(1, 4*mm))

    # ── Explanation ──────────────────────────────────────────
    if explanation:
        elements.append(Paragraph("AI Explanation", heading_style))
        # Truncate very long explanations
        display_explanation = explanation[:2000]
        if len(explanation) > 2000:
            display_explanation += "... [truncated]"
        elements.append(Paragraph(display_explanation, body_style))
        elements.append(Spacer(1, 4*mm))

    # ── Footer ───────────────────────────────────────────────
    elements.append(Spacer(1, 10*mm))
    footer_style = ParagraphStyle(
        "Footer", parent=styles["Normal"],
        fontSize=8, textColor=HexColor("#888888"),
    )
    elements.append(Paragraph(
        "Generated by RAIYA AI Resume Screening Platform | SpeedTech.ai",
        footer_style,
    ))

    # ── Build PDF ────────────────────────────────────────────
    doc.build(elements)
    logger.info(f"PDF report generated: {pdf_path}")

    return str(pdf_path)
