#!/usr/bin/env python3
"""
End-to-end demo script for Rooting Future
Generates a plan for a sample club and exports PDF/DOCX/HTML/OnePager.
"""

import logging
import sys
import os

# Ensure root of repo is on PYTHONPATH for script imports when run from scripts/
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
from pathlib import Path

from agents import MultiAgentOrchestrator

# Optional exporters (may be missing in some envs); guard imports so the script can run in minimal setups
try:
    from export_pdf_server import PdfServerExporter
except Exception:
    PdfServerExporter = None
try:
    from export_docx import ProfessionalDocxExporter
except Exception:
    ProfessionalDocxExporter = None
try:
    from export_html import ChunkedHTMLExporter
except Exception:
    ChunkedHTMLExporter = None
try:
    from export_onepager import OnePagerExporter
except Exception:
    OnePagerExporter = None


def main():
    logging.basicConfig(level=logging.INFO)
    club_data = {
        "club_name": "Demo FC",
        "category": "Eccellenza",
        "primary_color": "#1a365d",
        "secondary_color": "#ffffff",
        "dimensione_rosa": 24,
        "capienza_stadio": 15000,
    }

    orchestrator = MultiAgentOrchestrator(knowledge_store=None)
    result = orchestrator.generate_strategic_plan(club_data, parallel=True)
    plan = result.get("plan", {})
    sources = result.get("sources", [])
    metadata = result.get("metadata", {})

    out = Path("output_demo")
    out.mkdir(exist_ok=True)

    # PDF export
    if PdfServerExporter:
        pdf = PdfServerExporter(out)
        try:
            pdf_path = pdf.export(
                plan, club_data["club_name"], sources=sources, metadata=metadata
            )
            logging.info(f"PDF exported: {pdf_path}")
        except Exception as e:
            logging.error(f"PDF export failed: {e}")

    # DOCX export
    if ProfessionalDocxExporter:
        docx = ProfessionalDocxExporter(out)
        try:
            docx_path = docx.export(
                plan, club_data["club_name"], sources=sources, metadata=metadata
            )
            logging.info(f"DOCX exported: {docx_path}")
        except Exception as e:
            logging.error(f"DOCX export failed: {e}")

    # HTML export
    if ChunkedHTMLExporter:
        html = ChunkedHTMLExporter(out)
        try:
            html_path = html.export(
                plan, club_data["club_name"], sources=sources, metadata=metadata
            )
            logging.info(f"HTML exported: {html_path}")
        except Exception as e:
            logging.error(f"HTML export failed: {e}")

    # OnePager export
    if OnePagerExporter:
        op = OnePagerExporter(out)
        try:
            op_path = op.export(
                plan, club_data["club_name"], metadata=metadata, stw_progress={}
            )
            logging.info(f"OnePager exported: {op_path}")
        except Exception as e:
            logging.error(f"OnePager export failed: {e}")


if __name__ == "__main__":
    main()
