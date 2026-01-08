"""
Export Package Module - Rooting Future Strategy Engine v5.4

Genera pacchetti ZIP contenenti tutti i formati di export:
- PDF (documento board-ready)
- DOCX (documento modificabile)
- JSON (dati strutturati per elaborazioni future)
"""

import io
import json
import zipfile
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional

from export_pdf_server import PdfServerExporter
from export_docx import DOCXExporter
from export_html import HTMLExporter

logger = logging.getLogger(__name__)


class StrategyPackageExporter:
    """
    Esportatore di pacchetti strategici completi.
    Genera un singolo ZIP con tutti i formati richiesti.
    """

    def __init__(self, output_dir: Path = None):
        self.output_dir = output_dir or Path("output")
        self.output_dir.mkdir(exist_ok=True)

        # Inizializza exporter singoli
        self.pdf_exporter = PdfServerExporter()
        self.pdf_exporter.output_dir = self.output_dir
        self.docx_exporter = DOCXExporter(output_dir)
        self.html_exporter = HTMLExporter(output_dir)

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

        Args:
            plan_data: Dati del piano strategico
            club_name: Nome del club
            sources: Lista fonti
            metadata: Metadati aggiuntivi
            formats: Lista formati da includere ['pdf', 'docx', 'html', 'json']
                    Default: ['pdf', 'docx']

        Returns:
            Path al file ZIP generato
        """
        formats = formats or ['pdf', 'docx']
        sources = sources or []
        metadata = metadata or {}

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = club_name.replace(" ", "_").replace("/", "_")
        zip_filename = f"{safe_name}_StrategyPack_{timestamp}.zip"
        zip_path = self.output_dir / zip_filename

        # Crea ZIP in memoria poi scrivi su disco
        zip_buffer = io.BytesIO()

        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            base_name = f"{safe_name}_PianoStrategico"

            # PDF (Server-side WeasyPrint)
            if 'pdf' in formats:
                try:
                    pdf_path = self.pdf_exporter.export(
                        plan_data, club_name, sources, metadata
                    )
                    with open(pdf_path, 'rb') as f:
                        zf.writestr(f"{base_name}.pdf", f.read())
                    logger.info("PDF added to package")
                except Exception as e:
                    logger.error(f"PDF generation failed: {e}")
                    # Aggiungi file di errore
                    zf.writestr(f"{base_name}_PDF_ERROR.txt",
                        f"Errore generazione PDF: {str(e)}")

            # DOCX
            if 'docx' in formats:
                try:
                    docx_bytes = self._generate_docx_bytes(
                        plan_data, club_name, sources, metadata
                    )
                    zf.writestr(f"{base_name}.docx", docx_bytes.getvalue())
                    logger.info("DOCX added to package")
                except Exception as e:
                    logger.error(f"DOCX generation failed: {e}")
                    zf.writestr(f"{base_name}_DOCX_ERROR.txt",
                        f"Errore generazione DOCX: {str(e)}")

            # HTML
            if 'html' in formats:
                try:
                    html_content = self._generate_html_content(
                        plan_data, club_name, sources, metadata
                    )
                    zf.writestr(f"{base_name}.html", html_content.encode('utf-8'))
                    logger.info("HTML added to package")
                except Exception as e:
                    logger.error(f"HTML generation failed: {e}")

            # JSON (dati strutturati)
            if 'json' in formats:
                try:
                    json_data = self._prepare_json_export(
                        plan_data, club_name, sources, metadata
                    )
                    zf.writestr(
                        f"{base_name}_data.json",
                        json.dumps(json_data, indent=2, ensure_ascii=False).encode('utf-8')
                    )
                    logger.info("JSON added to package")
                except Exception as e:
                    logger.error(f"JSON generation failed: {e}")

            # README
            readme_content = self._generate_readme(club_name, formats, metadata)
            zf.writestr("README.txt", readme_content.encode('utf-8'))

        # Scrivi ZIP su disco
        zip_buffer.seek(0)
        with open(zip_path, 'wb') as f:
            f.write(zip_buffer.getvalue())

        logger.info(f"Strategy package exported: {zip_path}")
        return zip_path

    def create_package_bytes(
        self,
        plan_data: Dict[str, Any],
        club_name: str,
        sources: List[Dict] = None,
        metadata: Dict = None,
        formats: List[str] = None
    ) -> io.BytesIO:
        """
        Crea pacchetto ZIP in memoria (per download diretto).

        Returns:
            BytesIO con contenuto ZIP
        """
        formats = formats or ['pdf', 'docx']
        sources = sources or []
        metadata = metadata or {}

        safe_name = club_name.replace(" ", "_").replace("/", "_")
        zip_buffer = io.BytesIO()

        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            base_name = f"{safe_name}_PianoStrategico"

            # PDF (Server-side WeasyPrint)
            if 'pdf' in formats:
                try:
                    pdf_path = self.pdf_exporter.export(
                        plan_data, club_name, sources, metadata
                    )
                    with open(pdf_path, 'rb') as f:
                        zf.writestr(f"{base_name}.pdf", f.read())
                except Exception as e:
                    logger.error(f"PDF generation failed: {e}")

            # DOCX
            if 'docx' in formats:
                try:
                    docx_bytes = self._generate_docx_bytes(
                        plan_data, club_name, sources, metadata
                    )
                    zf.writestr(f"{base_name}.docx", docx_bytes.getvalue())
                except Exception as e:
                    logger.error(f"DOCX generation failed: {e}")

            # HTML
            if 'html' in formats:
                try:
                    html_content = self._generate_html_content(
                        plan_data, club_name, sources, metadata
                    )
                    zf.writestr(f"{base_name}.html", html_content.encode('utf-8'))
                except Exception as e:
                    logger.error(f"HTML generation failed: {e}")

            # JSON
            if 'json' in formats:
                try:
                    json_data = self._prepare_json_export(
                        plan_data, club_name, sources, metadata
                    )
                    zf.writestr(
                        f"{base_name}_data.json",
                        json.dumps(json_data, indent=2, ensure_ascii=False).encode('utf-8')
                    )
                except Exception as e:
                    logger.error(f"JSON generation failed: {e}")

            # README
            readme_content = self._generate_readme(club_name, formats, metadata)
            zf.writestr("README.txt", readme_content.encode('utf-8'))

        zip_buffer.seek(0)
        return zip_buffer

    def _generate_docx_bytes(
        self,
        plan_data: Dict[str, Any],
        club_name: str,
        sources: List[Dict],
        metadata: Dict
    ) -> io.BytesIO:
        """Genera DOCX in memoria"""
        # Crea documento temporaneamente, poi leggi bytes
        docx_path = self.docx_exporter.create_document(
            plan_data, club_name, sources, metadata
        )

        docx_buffer = io.BytesIO()
        with open(docx_path, 'rb') as f:
            docx_buffer.write(f.read())

        # Rimuovi file temporaneo? No, teniamolo per riferimento
        docx_buffer.seek(0)
        return docx_buffer

    def _generate_html_content(
        self,
        plan_data: Dict[str, Any],
        club_name: str,
        sources: List[Dict],
        metadata: Dict
    ) -> str:
        """Genera contenuto HTML"""
        # L'HTML exporter scrive su file, quindi leggiamo il contenuto
        html_path = self.html_exporter.export(
            plan_data, club_name, sources, metadata
        )

        with open(html_path, 'r', encoding='utf-8') as f:
            return f.read()

    def _prepare_json_export(
        self,
        plan_data: Dict[str, Any],
        club_name: str,
        sources: List[Dict],
        metadata: Dict
    ) -> Dict:
        """Prepara dati JSON per export"""
        return {
            'meta': {
                'club_name': club_name,
                'export_date': datetime.now().isoformat(),
                'version': '5.4',
                **metadata
            },
            'sections': plan_data,
            'sources': sources
        }

    def _generate_readme(
        self,
        club_name: str,
        formats: List[str],
        metadata: Dict
    ) -> str:
        """Genera file README per il pacchetto"""
        date_str = datetime.now().strftime("%d/%m/%Y %H:%M")
        category = metadata.get('category', 'N/A')
        credibility = metadata.get('credibility_score', 0)

        format_descriptions = {
            'pdf': 'PDF - Documento ufficiale per presentazioni (layout fisso)',
            'docx': 'DOCX - Documento Word modificabile per uso interno',
            'html': 'HTML - Versione web per consultazione digitale',
            'json': 'JSON - Dati strutturati per elaborazioni future'
        }

        included_formats = '\n'.join(
            f'  - {format_descriptions.get(f, f)}'
            for f in formats
        )

        return f'''====================================================
PIANO STRATEGICO TRIENNALE
{club_name}
====================================================

Categoria: {category}
Data generazione: {date_str}
Credibilita dati: {credibility:.0f}%

----------------------------------------------------
CONTENUTO PACCHETTO
----------------------------------------------------
{included_formats}

----------------------------------------------------
NOTE
----------------------------------------------------
- Il PDF e il formato consigliato per presentazioni ufficiali
- Il DOCX puo essere modificato per personalizzazioni
- I dati JSON possono essere importati in altri sistemi

----------------------------------------------------
GENERATO DA
----------------------------------------------------
Rooting Future Strategy Engine v5.4
Sistema AI Multi-Agente per Piani Strategici
Societa Calcistiche Italiane

(c) 2025 - Tutti i diritti riservati
====================================================
'''
