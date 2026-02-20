#!/usr/bin/env python3
# Copyright (c) 2026 Veritas Aequitas Holdings LLC. All rights reserved.
# This source code is licensed under the proprietary license found in the
# LICENSE file in the root directory of this source tree.
#
# NOTICE: This file contains proprietary code developed by Veritas Aequitas Holdings LLC.
# Unauthorized use, reproduction, or distribution is strictly prohibited.
# For inquiries, contact: contact@veritasandaequitas.com
"""
PDF and CSV Report Generator for After Action Review exports.

Generates formatted PDF reports from AAR data using fpdf2, and CSV exports
from game session timelines for downstream analysis.
"""
import csv
import io
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from fpdf import FPDF

from api.utils.logger import setup_logger

logger = setup_logger(__name__)


class ReportGenerator:
    """Generates PDF and CSV reports from AAR and game session data."""

    PAGE_WIDTH = 190  # usable width in mm (A4 with 10mm margins)

    def __init__(self) -> None:
        """Initialize the report generator."""
        self.font_family = "Helvetica"

    def generate_pdf(
        self,
        aar_report: Dict[str, Any],
        game_state: Optional[Dict[str, Any]] = None,
    ) -> bytes:
        """Generate a PDF report from AAR data.

        Args:
            aar_report: Serialized AARReport dict.
            game_state: Optional serialized GameState dict for extra context.

        Returns:
            PDF file contents as bytes.
        """
        logger.info(
            f"Generating PDF report for session {aar_report.get('session_id', 'unknown')}"
        )

        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()

        # --- Header ---
        self._add_header(pdf, "After Action Review Report")
        pdf.set_font(self.font_family, size=10)
        pdf.cell(0, 6, f"Session ID: {aar_report.get('session_id', 'N/A')}", new_x="LMARGIN", new_y="NEXT")
        generated_at = aar_report.get("generated_at", "")
        if isinstance(generated_at, datetime):
            generated_at = generated_at.strftime("%Y-%m-%d %H:%M:%S UTC")
        pdf.cell(0, 6, f"Generated: {generated_at}", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(4)

        # --- Summary Section ---
        self._add_section(pdf, "Summary")
        grade = aar_report.get("overall_grade", "N/A")
        r, g, b = self._grade_color(grade)
        pdf.set_font(self.font_family, "B", 28)
        pdf.set_text_color(r, g, b)
        pdf.cell(30, 16, grade, new_x="END", new_y="LAST")
        pdf.set_text_color(0, 0, 0)
        pdf.set_font(self.font_family, size=10)
        pdf.multi_cell(0, 6, aar_report.get("summary", ""), new_x="LMARGIN", new_y="NEXT")
        pdf.ln(4)

        # --- Score Breakdown ---
        breakdown = aar_report.get("score_breakdown", {})
        if breakdown:
            self._add_section(pdf, "Score Breakdown")
            headers = ["Category", "Points"]
            rows = [[k.replace("_", " ").title(), str(v)] for k, v in breakdown.items()]
            self._add_table(pdf, headers, rows)
            pdf.ln(4)

        # --- Timeline Analysis ---
        timeline = aar_report.get("timeline_analysis", [])
        if timeline:
            self._add_section(pdf, "Timeline Analysis")
            headers = ["Action", "Category", "Score", "Impact"]
            rows = []
            for decision in timeline:
                action = decision.get("action", "")
                if len(action) > 60:
                    action = action[:57] + "..."
                rows.append([
                    action,
                    decision.get("category", ""),
                    str(decision.get("quality_score", "")),
                    decision.get("impact", ""),
                ])
            self._add_table(pdf, headers, rows)
            pdf.ln(4)

        # --- Strengths & Weaknesses ---
        strengths = aar_report.get("strengths", [])
        weaknesses = aar_report.get("weaknesses", [])
        if strengths or weaknesses:
            self._add_section(pdf, "Strengths & Weaknesses")
            col_width = self.PAGE_WIDTH / 2

            pdf.set_font(self.font_family, "B", 10)
            pdf.cell(col_width, 7, "Strengths", border="B")
            pdf.cell(col_width, 7, "Weaknesses", border="B", new_x="LMARGIN", new_y="NEXT")

            pdf.set_font(self.font_family, size=9)
            max_rows = max(len(strengths), len(weaknesses))
            for i in range(max_rows):
                s_text = f"  + {strengths[i]}" if i < len(strengths) else ""
                w_text = f"  - {weaknesses[i]}" if i < len(weaknesses) else ""
                if len(s_text) > 55:
                    s_text = s_text[:52] + "..."
                if len(w_text) > 55:
                    w_text = w_text[:52] + "..."
                pdf.cell(col_width, 6, s_text)
                pdf.cell(col_width, 6, w_text, new_x="LMARGIN", new_y="NEXT")
            pdf.ln(4)

        # --- Recommendations ---
        recommendations = aar_report.get("recommendations", [])
        if recommendations:
            self._add_section(pdf, "Recommendations")
            pdf.set_font(self.font_family, size=10)
            for idx, rec in enumerate(recommendations, 1):
                pdf.multi_cell(0, 6, f"{idx}. {rec}", new_x="LMARGIN", new_y="NEXT")
            pdf.ln(4)

        # --- Metrics ---
        metrics = aar_report.get("metrics", {})
        if metrics:
            self._add_section(pdf, "Performance Metrics")
            headers = ["Metric", "Value", "Benchmark", "Percentile"]
            rows = []
            for name, data in metrics.items():
                if isinstance(data, dict):
                    rows.append([
                        name.replace("_", " ").title(),
                        str(data.get("value", "")),
                        str(data.get("benchmark", "N/A")),
                        f"{data.get('percentile', 'N/A')}th" if data.get("percentile") is not None else "N/A",
                    ])
            self._add_table(pdf, headers, rows)

        pdf_bytes = pdf.output()
        logger.info(
            f"PDF generated: {len(pdf_bytes)} bytes for session "
            f"{aar_report.get('session_id', 'unknown')}"
        )
        return bytes(pdf_bytes)

    def generate_csv(self, game_state: Dict[str, Any]) -> str:
        """Generate a CSV string from the game state incident timeline.

        Args:
            game_state: Serialized GameState dict.

        Returns:
            CSV-formatted string with timeline events.
        """
        logger.info(
            f"Generating CSV for session {game_state.get('session_id', 'unknown')}"
        )
        output = io.StringIO()
        fieldnames = ["timestamp", "event_type", "description", "severity", "actor"]
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()

        for event in game_state.get("incident_timeline", []):
            timestamp = event.get("timestamp", "")
            if isinstance(timestamp, datetime):
                timestamp = timestamp.isoformat()
            writer.writerow({
                "timestamp": timestamp,
                "event_type": event.get("event_type", ""),
                "description": event.get("description", ""),
                "severity": event.get("severity", ""),
                "actor": event.get("actor", ""),
            })

        csv_str = output.getvalue()
        output.close()
        return csv_str

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _add_header(self, pdf: FPDF, title: str) -> None:
        """Add a page header with the given title."""
        pdf.set_font(self.font_family, "B", 18)
        pdf.set_text_color(30, 30, 80)
        pdf.cell(0, 12, title, new_x="LMARGIN", new_y="NEXT", align="C")
        pdf.set_draw_color(30, 30, 80)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(4)
        pdf.set_text_color(0, 0, 0)

    def _add_section(self, pdf: FPDF, title: str) -> None:
        """Add a section heading."""
        pdf.set_font(self.font_family, "B", 13)
        pdf.set_text_color(40, 40, 100)
        pdf.cell(0, 9, title, new_x="LMARGIN", new_y="NEXT")
        pdf.set_text_color(0, 0, 0)

    def _add_table(self, pdf: FPDF, headers: List[str], rows: List[List[str]]) -> None:
        """Add a simple table with headers and rows."""
        num_cols = len(headers)
        col_width = self.PAGE_WIDTH / num_cols

        # Header row
        pdf.set_font(self.font_family, "B", 9)
        pdf.set_fill_color(220, 220, 240)
        for header in headers:
            pdf.cell(col_width, 7, header, border=1, fill=True)
        pdf.ln()

        # Data rows
        pdf.set_font(self.font_family, size=9)
        for row in rows:
            for cell_val in row:
                pdf.cell(col_width, 6, cell_val, border=1)
            pdf.ln()

    @staticmethod
    def _grade_color(grade: str) -> Tuple[int, int, int]:
        """Return an RGB tuple for the given letter grade.

        A = green, B = blue, C = yellow, D = orange, F = red.
        """
        colors = {
            "A": (34, 139, 34),
            "B": (30, 90, 180),
            "C": (180, 160, 0),
            "D": (210, 120, 0),
            "F": (200, 30, 30),
        }
        return colors.get(grade.upper(), (100, 100, 100))
