"""
Export Package Module - Rooting Future Strategy Engine v6.0

Genera pacchetti ZIP contenenti tutti i formati di export.
"""

import io
import json
import zipfile
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
import re

from export_pdf_server import PdfServerExporter
from export_docx import ProfessionalDocxExporter
from export_html import ChunkedHTMLExporter
from config import OUTPUT_DIR

logger = logging.getLogger(__name__)

class StrategyPackageExporter:
    """
    Esportatore di pacchetti strategici completi.
    Genera un singolo ZIP con tutti i formati richiesti.
    """

    def __init__(self, output_dir: Optional[Path] = None):
        self.output_dir = Path(output_dir) if output_dir else OUTPUT_DIR
        self.output_dir.mkdir(exist_ok=True, parents=True)

        # Inizializza exporter singoli
        self.pdf_exporter = PdfServerExporter(self.output_dir)
        self.docx_exporter = ProfessionalDocxExporter(self.output_dir)
        self.html_exporter = ChunkedHTMLExporter(self.output_dir)

    def create_package(
        self,
        plan_data: Dict[str, Any],
        club_name: str,
        sources: List[Dict] = None,
        metadata: Dict = None,
        formats: List[str] = None
    ) -> Path:
        """
        Crea pacchetto ZIP con tutti i formati richiesti.
        """
        formats = formats or ['pdf', 'docx']
        sources = sources or []
        metadata = metadata or {}

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = re.sub(r'[^\w\s-]', '', club_name).strip().replace(' ', '_')
        zip_filename = f"{safe_name}_StrategyPack_{timestamp}.zip"
        zip_path = self.output_dir / zip_filename

        zip_buffer = io.BytesIO()

        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            base_name = f"{safe_name}_PianoStrategico"

            # PDF
            if 'pdf' in formats:
                try:
                    pdf_path = self.pdf_exporter.export(plan_data, club_name, sources, metadata)
                    with open(pdf_path, 'rb') as f:
                        zf.writestr(f"{base_name}.pdf", f.read())
                    logger.info("PDF added to package")
                except Exception as e:
                    logger.error(f"PDF generation failed: {e}")

            # DOCX
            if 'docx' in formats:
                try:
                    docx_path = self.docx_exporter.export(plan_data, club_name, sources, metadata)
                    with open(docx_path, 'rb') as f:
                        zf.writestr(f"{base_name}.docx", f.read())
                    logger.info("DOCX added to package")
                except Exception as e:
                    logger.error(f"DOCX generation failed: {e}")

            # HTML
            if 'html' in formats:
                try:
                    html_path = self.html_exporter.export(plan_data, club_name, sources, metadata)
                    with open(html_path, 'rb') as f:
                        zf.writestr(f"{base_name}.html", f.read())
                    logger.info("HTML added to package")
                except Exception as e:
                    logger.error(f"HTML generation failed: {e}")

            # JSON
            if 'json' in formats:
                json_data = {
                    'meta': {'club_name': club_name, 'export_date': datetime.now().isoformat(), 'version': '6.0', **metadata},
                    'sections': plan_data,
                    'sources': sources
                }
                zf.writestr(f"{base_name}_data.json", json.dumps(json_data, indent=2, ensure_ascii=False).encode('utf-8'))

            # README
            readme_content = f"Strategy Package for {club_name}\nGenerated on {datetime.now().strftime('%d/%m/%Y %H:%M')}"
            zf.writestr("README.txt", readme_content.encode('utf-8'))

        with open(zip_path, 'wb') as f:
            f.write(zip_buffer.getvalue())

        logger.info(f"Strategy package exported: {zip_path}")
        return zip_path