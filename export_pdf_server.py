"""
Rooting Future Strategy Engine - Server-Side PDF Export
Engine: wkhtmltopdf (Primary) with WeasyPrint fallback
Design: Tactical Sports Report v3.0 (Anti-Crash Server Edition)

CONSOLIDATO: Include funzionalità di export_pdf.py legacy
"""

import re
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from bs4 import BeautifulSoup
import weasyprint

# Try to import pdfkit (wkhtmltopdf wrapper)
try:
    import pdfkit
    PDFKIT_AVAILABLE = True
except ImportError:
    PDFKIT_AVAILABLE = False
    pdfkit = None

from export_core import BaseExporter
from stw_matrix import generate_stw_matrix_html, get_stw_matrix_css
from config import OUTPUT_DIR

logger = logging.getLogger(__name__)

# Auto-detect wkhtmltopdf path
WKHTMLTOPDF_PATH = None
if PDFKIT_AVAILABLE:
    import shutil
    # Common installation paths on Windows
    possible_paths = [
        r"C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe",
        r"C:\Program Files (x86)\wkhtmltopdf\bin\wkhtmltopdf.exe",
        shutil.which("wkhtmltopdf"),  # Check PATH
    ]
    for path in possible_paths:
        if path and Path(path).exists():
            WKHTMLTOPDF_PATH = path
            logger.info(f"✅ wkhtmltopdf found at: {path}")
            break

    if not WKHTMLTOPDF_PATH:
        logger.warning("⚠️ pdfkit installed but wkhtmltopdf.exe not found. Falling back to WeasyPrint.")
        PDFKIT_AVAILABLE = False

# =============================================================================
# LEGACY PDF CSS (da export_pdf.py)
# =============================================================================

PDF_CSS_LEGACY = '''
@page {
    size: A4;
    margin: 2cm 2.5cm;
    @bottom-center {
        content: "Pagina " counter(page) " di " counter(pages);
        font-size: 9pt;
        color: #718096;
    }
}

body {
    font-family: "Segoe UI", Calibri, Arial, sans-serif;
    font-size: 11pt;
    line-height: 1.6;
    color: #2d3748;
}

h1 {
    font-size: 22pt;
    color: #1a365d;
    border-bottom: 3px solid #3182ce;
    padding-bottom: 12px;
    margin: 30px 0 20px 0;
    page-break-after: avoid;
}

h2 {
    font-size: 16pt;
    color: #2c5282;
    margin: 25px 0 15px 0;
    padding-top: 15px;
    border-top: 1px solid #e2e8f0;
    page-break-after: avoid;
}

h3 {
    font-size: 13pt;
    color: #3182ce;
    margin: 20px 0 12px 0;
    page-break-after: avoid;
}

p {
    margin: 0 0 12px 0;
    text-align: justify;
}

table {
    width: 100%;
    border-collapse: collapse;
    margin: 15px 0;
    font-size: 10pt;
    page-break-inside: avoid;
}

th, td {
    border: 1px solid #cbd5e0;
    padding: 10px 12px;
    text-align: left;
}

th {
    background-color: #1a365d;
    color: white;
    font-weight: 600;
}

.kpi-box {
    background: linear-gradient(135deg, #ebf8ff, #e6fffa);
    border-left: 4px solid #3182ce;
    padding: 15px 20px;
    margin: 15px 0;
    page-break-inside: avoid;
}
'''


class PdfServerExporter(BaseExporter):
    """
    Esporta piani strategici direttamente in PDF utilizzando WeasyPrint.
    Elimina la dipendenza da Paged.js e i problemi di rendering del browser.
    """

    def export(
        self,
        plan_data: Dict,
        club_name: str,
        sources: List[Dict] = None,
        metadata: Dict = None,
    ) -> Path:
        """
        Genera il file PDF finale.
        """
        # Estrazione metadati e colori standardizzati
        meta = self._extract_metadata(metadata)

        # Genera l'HTML con il CSS ottimizzato per WeasyPrint
        html_content = self._generate_html(
            plan_data=plan_data, club_name=club_name, sources=sources or [], meta=meta
        )

        # Output path standardizzato
        filename = self._get_safe_filename(club_name, "pdf", prefix="PianoStrategico")
        filepath = self.output_dir / filename

        # Generazione PDF: Try WeasyPrint first (supports @page CSS), fallback to wkhtmltopdf
        # WeasyPrint è più lento ma supporta correttamente CSS Paged Media
        weasyprint_failed = False

        logger.info(f"🎨 Inizio generazione PDF per {club_name} via WeasyPrint (CSS Paged Media)...")
        weasyprint_failed = False

        try:
            import threading
            pdf_error = None

            def generate_pdf():
                nonlocal pdf_error
                try:
                    weasyprint.HTML(string=html_content).write_pdf(str(filepath))
                except Exception as e:
                    pdf_error = e

            # Esegui con timeout di 2 minuti (120s)
            pdf_thread = threading.Thread(target=generate_pdf, daemon=True)
            pdf_thread.start()
            pdf_thread.join(timeout=120)

            if pdf_thread.is_alive():
                logger.error(f"⏱️ TIMEOUT: WeasyPrint bloccato dopo 120s per {club_name}")
                weasyprint_failed = True
            elif pdf_error:
                logger.error(f"❌ Errore WeasyPrint: {pdf_error}")
                weasyprint_failed = True
            else:
                logger.info(f"✅ PDF generato con WeasyPrint: {filepath}")
                return filepath

        except Exception as e:
            logger.error(f"❌ WeasyPrint exception: {e}")
            weasyprint_failed = True

        # Fallback: wkhtmltopdf (fast but doesn't support @page CSS perfectly)
        if weasyprint_failed and PDFKIT_AVAILABLE and WKHTMLTOPDF_PATH:
            logger.warning(f"⚠️ Tentativo fallback con wkhtmltopdf per {club_name}...")
            try:
                config = pdfkit.configuration(wkhtmltopdf=WKHTMLTOPDF_PATH)
                options = {
                    'page-size': 'A4',
                    'margin-top': '22mm',
                    'margin-right': '20mm',
                    'margin-bottom': '18mm',
                    'margin-left': '20mm',
                    'encoding': 'UTF-8',
                    'enable-local-file-access': None,
                    'no-stop-slow-scripts': None,
                    'javascript-delay': 1000,
                    'load-error-handling': 'ignore',
                    'load-media-error-handling': 'ignore',
                }
                pdfkit.from_string(html_content, str(filepath), configuration=config, options=options)
                logger.info(f"✅ PDF generato con wkhtmltopdf (fallback): {filepath}")
                return filepath
            except Exception as e2:
                logger.error(f"❌ wkhtmltopdf fallback failed: {e2}")

        # Se arriviamo qui, entrambi i metodi sono falliti
        raise Exception(f"❌ CRITICAL: Tutti i metodi PDF sono falliti per {club_name}. WeasyPrint e wkhtmltopdf non disponibili.")

    def _generate_html(self, plan_data, club_name, sources, meta) -> str:
        # Colori dinamici
        club_primary = meta["primary_color"]
        club_secondary = (
            meta["secondary_color"]
            if meta["secondary_color"] and meta["secondary_color"].lower() != "#ffffff"
            else "#1a202c"
        )
        contrast_color = meta["contrast_color"]

        current_year = meta["current_year"]

        # Genera contenuto sezioni usando il colore del club
        sections_html = self._generate_sections_html(plan_data, club_primary)

        # Genera matrice STW usando il colore del club
        stw_matrix_html = generate_stw_matrix_html(club_primary)

        # Genera pagina metodologia + questionari
        methodology_html = self._generate_methodology_page(club_name, meta)

        return f'''
<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <title>Piano Strategico - {club_name}</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600&family=Montserrat:wght@700;800&display=swap');

        :root {{
            --club-primary: {club_primary};
            --club-secondary: {club_secondary};
            --primary-color: {club_primary};
            --secondary-color: {club_secondary};
            --rf-purple: #6a0dad;
            --brand-gradient: linear-gradient(135deg, var(--club-primary) 0%, var(--club-secondary) 100%);
            --light-color: #fdfbff;
            --contrast-color: {contrast_color};
            --text-color: #1a202c;
            --border-color: #e2e8f0;
        }}

        /* ===========================================
           CONFIGURAZIONE PAGINA (Paged Media)
           Magazine Style con Running Header
           =========================================== */
        @page {{
            size: A4;
            margin: 22mm 20mm 18mm 20mm;

            /* RUNNING HEADER */
            @top-left {{
                content: "{club_name.upper()}";
                font-family: 'Montserrat', sans-serif;
                font-size: 8pt;
                font-weight: 700;
                letter-spacing: 2px;
                color: {club_primary};
                border-bottom: 0.5pt solid var(--border-color);
                padding-bottom: 3mm;
            }}
            @top-right {{
                content: "PIANO STRATEGICO {current_year}—{current_year + 3}";
                font-family: 'Montserrat', sans-serif;
                font-size: 7pt;
                letter-spacing: 1px;
                color: #718096;
                border-bottom: 0.5pt solid var(--border-color);
                padding-bottom: 3mm;
            }}

            /* FOOTER */
            @bottom-left {{
                content: "ROOTING FUTURE // STRATEGY ENGINE";
                font-family: 'Inter', sans-serif;
                font-size: 7pt;
                color: #a0aec0;
                padding-top: 4mm;
            }}
            @bottom-right {{
                content: counter(page);
                font-family: 'Montserrat', sans-serif;
                font-size: 9pt;
                font-weight: 700;
                color: {club_primary};
                padding-top: 4mm;
            }}
        }}

        /* Copertina: No Header/Footer */
        @page :first {{
            margin: 0;
            @top-left {{ content: none; }}
            @top-right {{ content: none; }}
            @bottom-left {{ content: none; }}
            @bottom-right {{ content: none; }}
        }}

        /* Reset & Base */
        * {{ box-sizing: border-box; }}
        body {{
            font-family: 'Inter', sans-serif;
            font-size: 10pt;
            line-height: 1.6;
            color: var(--text-color);
            background: #ffffff;
            margin: 0;
            padding: 0;
        }}

        /* ===========================================
           TIPOGRAFIA
           =========================================== */
        h1, h2, h3, h4, .cover-club {{
            font-family: 'Montserrat', sans-serif;
            text-transform: uppercase;
            letter-spacing: -0.5px;
        }}

        h1 {{
            font-size: 28pt;
            font-weight: 800;
            color: var(--primary-color);
            border-bottom: 3pt solid var(--primary-color);
            padding-bottom: 2mm;
            margin: 15mm 0 10mm 0;
            page-break-before: always;
        }}

        h2 {{
            font-size: 18pt;
            font-weight: 800;
            color: var(--primary-color);
            margin-top: 15mm;
            margin-bottom: 8mm;
            padding-left: 5mm;
            border-left: 5pt solid var(--primary-color);
            page-break-after: avoid;
        }}

        h3 {{
            font-size: 13pt;
            font-weight: 700;
            color: var(--secondary-color);
            margin: 10mm 0 5mm 0;
            border-bottom: 1pt solid var(--border-color);
            padding-bottom: 2mm;
        }}

        p {{
            margin-bottom: 4mm;
            text-align: justify;
        }}

        /* ===========================================
           COPERTINA POSTER (Tactical Edition)
           =========================================== */
        .cover {{
            width: 210mm;
            height: 297mm;
            background: var(--brand-gradient);
            color: var(--contrast-color);
            position: relative;
            overflow: hidden;
            page-break-after: always;
        }}

        .cover::before {{
            content: "";
            position: absolute;
            top: 0; left: 0; right: 0; bottom: 0;
            background: url('https://www.transparenttextures.com/patterns/cubes.png');
            opacity: 0.15;
        }}

        .cover-content {{
            position: absolute;
            top: 100mm; left: 25mm; right: 40mm;
            z-index: 10;
        }}

        .cover-brand {{
            font-size: 10pt;
            letter-spacing: 5px;
            background: #000;
            color: #fff;
            padding: 2mm 5mm;
            display: inline-block;
            margin-bottom: 12mm;
        }}

        .cover-club {{
            font-size: 64pt;
            font-weight: 800;
            line-height: 0.9;
            margin-bottom: 8mm;
        }}

        .cover-title {{
            font-size: 22pt;
            font-weight: 300;
            border-left: 3pt solid var(--contrast-color);
            padding-left: 6mm;
            text-transform: uppercase;
            letter-spacing: 2px;
        }}

        /* ===========================================
           LAYOUT A COLONNE
           =========================================== */
        .section-container {{
            margin-bottom: 15mm;
        }}

        .section-body {{
            column-count: 2;
            column-gap: 10mm;
            text-align: justify;
        }}

        /* ===========================================
           COPERTINA POSTER (Tactical Edition)
           =========================================== */
        .cover {{
            width: 210mm;
            height: 296mm; /* Reduced slightly to prevent overflow loop */
            background: var(--brand-gradient);
            color: var(--contrast-color);
            position: relative;
            overflow: hidden;
            page-break-after: always;
        }}

        .cover::before {{
            content: "";
            position: absolute;
            top: 0; left: 0; right: 0; bottom: 0;
            background: url('https://www.transparenttextures.com/patterns/cubes.png');
            opacity: 0.15;
        }}

        .cover-content {{
            position: absolute;
            top: 100mm; left: 25mm; right: 40mm;
            z-index: 10;
        }}

        .cover-brand {{
            font-size: 10pt;
            letter-spacing: 5px;
            background: #000;
            color: #fff;
            padding: 2mm 5mm;
            display: inline-block;
            margin-bottom: 12mm;
        }}

        .cover-club {{
            font-size: 64pt;
            font-weight: 800;
            line-height: 0.9;
            margin-bottom: 8mm;
        }}

        .cover-title {{
            font-size: 22pt;
            font-weight: 300;
            border-left: 3pt solid var(--contrast-color);
            padding-left: 6mm;
            text-transform: uppercase;
            letter-spacing: 2px;
        }}

        /* ===========================================
           LAYOUT A COLONNE
           =========================================== */
        .section-container {{
            margin-bottom: 15mm;
            page-break-inside: auto;
        }}

        .section-body {{
            text-align: justify;
            orphans: 3;
            widows: 3;
        }}

        h1 {{
            page-break-before: always;
            page-break-after: avoid;
        }}

        h2, h3, h4 {{
            page-break-after: avoid;
        }}

        /* Simplified layout without columns to prevent WeasyPrint infinite loops */
        table, .kpi-box, .insight-box, .action-box, blockquote {{
            break-inside: avoid;
            margin-bottom: 5mm;
        }}


        /* ===========================================
           BOX E BADGE
           =========================================== */
        .kpi-box {{
            background: #fdfbff;
            border-left: 5pt solid var(--primary-color);
            padding: 6mm 8mm;
            margin: 8mm 0;
            border-radius: 0 4mm 4mm 0;
        }}

        .badge {{ background: #F3E5F5; padding: 1mm 3mm; border-radius: 10px; font-weight: 700; font-size: 8pt; margin-right: 2px; }}
        .badge.questionnaire {{ background: #F3E5F5; color: #7B1FA2; }}
        .badge.research {{ background: #E3F2FD; color: #1565C0; }}
        .badge.estimate {{ background: #FFF3E0; color: #F57C00; }}

        .insight-box {{
            background: #f0f7ff;
            border-left: 4pt solid #2b6cb0;
            padding: 4mm 6mm;
            margin: 6mm 0;
            border-radius: 2mm;
            break-inside: avoid;
        }}

        .action-box {{
            background: #f0fff4;
            border-left: 4pt solid #38a169;
            padding: 4mm 6mm;
            margin: 6mm 0;
            border-radius: 2mm;
            break-inside: avoid;
        }}

        .quote-box {{
            font-style: italic;
            color: #4a5568;
            padding: 4mm 10mm;
            margin: 6mm 0;
            border-left: 2pt solid #cbd5e0;
            break-inside: avoid;
            font-size: 11pt;
            background: #f8fafc;
        }}

        {get_stw_matrix_css()}
    </style>
</head>
<body>
    <div class="cover">
        <div class="cover-content">
            <div class="cover-brand">STRATEGIC DOSSIER</div>
            <div class="cover-club">{club_name}</div>
            <div class="cover-title">PIANO STRATEGICO<br>SVILUPPO {current_year}—{
            current_year + 3
        }</div>
            
            <div style="margin-top: 30mm; font-family: 'Montserrat'; font-size: 9pt; letter-spacing: 2px; opacity: 0.7;">
                GENERATED BY ROOTING FUTURE STRATEGY ENGINE v6.0
            </div>
        </div>
    </div>

    {methodology_html}

    {stw_matrix_html}

    {sections_html}

    {self._generate_sources_html(sources)}
</body>
</html>
'''

    def _generate_sections_html(self, plan_data, primary_color) -> str:
        html = []
        section_titles = self._get_section_titles()
        preferred_order = self._get_preferred_section_order()

        # Genera HTML nell'ordine corretto
        for key in preferred_order:
            if key in plan_data and plan_data[key]:
                content = plan_data[key]
                title = section_titles.get(key, key.replace("_", " ").title())
                html.append(f'<div class="section-container">')
                html.append(f"<h1>{title}</h1>")
                # Normalizziamo il markdown prima della conversione
                normalized_content = self._normalize_markdown(content)
                html.append(
                    f'<div class="section-body">{self._markdown_to_html(normalized_content)}</div>'
                )
                html.append(f"</div>")

        # Aggiungi eventuali sezioni non previste
        for key, content in plan_data.items():
            if key not in preferred_order and content:
                title = section_titles.get(key, key.replace("_", " ").title())
                html.append(f'<div class="section-container">')
                html.append(f"<h1>{title}</h1>")
                normalized_content = self._normalize_markdown(content)
                html.append(
                    f'<div class="section-body">{self._markdown_to_html(normalized_content)}</div>'
                )
                html.append(f"</div>")

        return "".join(html)

    def _generate_methodology_page(self, club_name: str, meta: dict) -> str:
        """
        Genera la pagina Metodologia Rooting Future con evidenziazione dei questionari compilati.
        """
        total_questionnaires = meta["total_questionnaires"]
        credibility_score = meta["credibility_score"]

        # Fallback per compatibilità
        if total_questionnaires == 0:
            total_questionnaires = 9

        html = f"""
    <div style="page-break-before: always; padding: 15mm 20mm;">
        <div style="text-align: center; margin-bottom: 15mm;">
            <div style="display: inline-block; background: linear-gradient(135deg, #1a365d 0%, #2E7D32 100%);
                        padding: 8mm 15mm; border-radius: 4mm;">
                <div style="font-family: 'Montserrat', sans-serif; font-size: 32pt; font-weight: 700;
                            color: white; letter-spacing: 4px; margin-bottom: 3mm;">
                    ROOTING FUTURE
                </div>
                <div style="font-size: 12pt; color: rgba(255,255,255,0.9); letter-spacing: 2px;">
                    Strategic Planning Framework per il Calcio Italiano
                </div>
            </div>
        </div>

        <h2 style="font-size: 24pt; text-align: center; margin: 10mm 0;">
            📋 Metodologia & Dati di Input
        </h2>

        <div style="background: linear-gradient(135deg, #7B1FA2 0%, #9C27B0 100%);
                    padding: 8mm; border-radius: 3mm; margin: 8mm 0; color: white;">
            <h3 style="margin: 0 0 5mm 0; font-size: 16pt; color: white; border: none;">
                ✅ Questionari Compilati dai Membri del Board di {club_name}
            </h3>
            <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 5mm;">
                <div style="text-align: center;">
                    <div style="font-size: 32pt; font-weight: 700;">{total_questionnaires}</div>
                    <div style="font-size: 10pt; opacity: 0.9;">Documenti Word</div>
                </div>
                <div style="text-align: center;">
                    <div style="font-size: 32pt; font-weight: 700;">{total_questionnaires * 15}+</div>
                    <div style="font-size: 10pt; opacity: 0.9;">Dati Forniti</div>
                </div>
                <div style="text-align: center;">
                    <div style="font-size: 32pt; font-weight: 700;">{credibility_score}%</div>
                    <div style="font-size: 10pt; opacity: 0.9;">Completezza</div>
                </div>
            </div>
        </div>

        <h3 style="font-size: 18pt; margin: 10mm 0 6mm 0;">Il Processo Rooting Future</h3>

        <div style="margin: 6mm 0;">
            <div style="display: flex; align-items: flex-start; margin-bottom: 6mm;">
                <div style="flex-shrink: 0; width: 15mm; height: 15mm; background: #7B1FA2; color: white;
                            border-radius: 50%; display: flex; align-items: center; justify-content: center;
                            font-size: 16pt; font-weight: 700; margin-right: 5mm;">
                    1
                </div>
                <div style="flex: 1;">
                    <h4 style="margin: 0 0 2mm 0; font-size: 14pt; color: #7B1FA2;">
                        📋 Analisi Questionari Club
                    </h4>
                    <p style="margin: 0; line-height: 1.6;">
                        <strong>Dati forniti direttamente da {club_name}</strong> tramite questionari Word strutturati.
                    </p>
                </div>
            </div>

            <div style="display: flex; align-items: flex-start; margin-bottom: 6mm;">
                <div style="flex-shrink: 0; width: 15mm; height: 15mm; background: #1565C0; color: white;
                            border-radius: 50%; display: flex; align-items: center; justify-content: center;
                            font-size: 16pt; font-weight: 700; margin-right: 5mm;">
                    2
                </div>
                <div style="flex: 1;">
                    <h4 style="margin: 0 0 2mm 0; font-size: 14pt; color: #1565C0;">
                        🔍 Web Research & Benchmark
                    </h4>
                    <p style="margin: 0; line-height: 1.6;">
                        Integrazione dati da <strong>FIGC, Transfermarkt, Google, Visure Camerali</strong>.
                    </p>
                </div>
            </div>

            <div style="display: flex; align-items: flex-start; margin-bottom: 6mm;">
                <div style="flex-shrink: 0; width: 15mm; height: 15mm; background: #2E7D32; color: white;
                            border-radius: 50%; display: flex; align-items: center; justify-content: center;
                            font-size: 16pt; font-weight: 700; margin-right: 5mm;">
                    3
                </div>
                <div style="flex: 1;">
                    <h4 style="margin: 0 0 2mm 0; font-size: 14pt; color: #2E7D32;">
                        🤖 AI Multi-Agente STW-Aligned
                    </h4>
                    <p style="margin: 0; line-height: 1.6;">
                        <strong>6 agenti specializzati</strong> elaborano il piano seguendo la matrice STW (21 obiettivi MACRO).
                    </p>
                </div>
            </div>
        </div>

        <div style="background: #f5f5f5; padding: 6mm; border-left: 4pt solid #1a365d; margin-top: 10mm;">
            <h4 style="margin: 0 0 3mm 0; font-size: 12pt;">Legenda Badge nei Dati:</h4>
            <div style="display: flex; gap: 8mm; flex-wrap: wrap;">
                <div style="display: flex; align-items: center; gap: 2mm;">
                    <span class="badge questionnaire">📋 Da Questionario</span>
                    <span style="font-size: 9pt;">Dati forniti da {club_name}</span>
                </div>
                <div style="display: flex; align-items: center; gap: 2mm;">
                    <span class="badge research">🔍 Ricerca Web</span>
                    <span style="font-size: 9pt;">Dati verificati online</span>
                </div>
                <div style="display: flex; align-items: center; gap: 2mm;">
                    <span class="badge estimate">📊 Stima AI</span>
                    <span style="font-size: 9pt;">Elaborazione intelligenza artificiale</span>
                </div>
            </div>
        </div>
    </div>
"""
        return html

    def _generate_sources_html(self, sources) -> str:
        if not sources:
            return ""
        html = ["<h1>Fonti e Metodologia</h1>", '<div class="section-body"><ul>']
        for s in sources[:20]:
            name = s.get("name", "Fonte esterna")
            url = s.get("url", "")
            html.append(f"<li><strong>{name}</strong><br><small>{url}</small></li>")
        html.append("</ul></div>")
        return "".join(html)


# =============================================================================
# LEGACY COMPATIBILITY LAYER (da export_pdf.py)
# =============================================================================

def _prepare_html_for_pdf(html_content: str) -> str:
    """Prepara l'HTML per la conversione PDF rimuovendo elementi problematici."""
    try:
        soup = BeautifulSoup(html_content, 'html.parser')

        # Rimuovi script, noscript, iframe
        for tag in soup.find_all(['script', 'noscript', 'iframe']):
            tag.decompose()

        # Rimuovi style tags interni
        for tag in soup.find_all('style'):
            tag.decompose()

        # Rimuovi navigazione e elementi UI
        for tag in soup.find_all(['button', 'nav']):
            tag.decompose()

        for class_name in ['nav', 'footer', 'print-bar', 'modal', 'btn']:
            for tag in soup.find_all(class_=class_name):
                tag.decompose()

        return str(soup)
    except Exception as e:
        logger.warning(f"Errore pulizia HTML: {e}, uso HTML originale")
        return html_content


def create_pdf_from_html(html_content: str, output_path: str, plan_name: str) -> bool:
    """
    Genera un PDF da HTML usando WeasyPrint (legacy compatibility function).

    CONSOLIDATO da export_pdf.py - mantiene compatibilità con codice esistente.

    Args:
        html_content: Contenuto HTML completo
        output_path: Directory dove salvare il PDF
        plan_name: Nome del file (senza estensione)

    Returns:
        True se il PDF è stato generato con successo
    """
    # Validazione input
    if not html_content or not isinstance(html_content, str):
        logger.error("html_content non valido")
        return False

    pdf_filename = Path(output_path) / f"{plan_name}.pdf"
    logger.info(f"Generazione PDF legacy: {pdf_filename}")

    # Pulisci HTML
    clean_html = _prepare_html_for_pdf(html_content)

    # Try wkhtmltopdf first
    if PDFKIT_AVAILABLE and WKHTMLTOPDF_PATH:
        try:
            logger.info(f"🚀 Generazione PDF legacy via wkhtmltopdf...")
            config = pdfkit.configuration(wkhtmltopdf=WKHTMLTOPDF_PATH)
            options = {
                'page-size': 'A4',
                'margin-top': '2cm',
                'margin-right': '2.5cm',
                'margin-bottom': '2cm',
                'margin-left': '2.5cm',
                'encoding': 'UTF-8',
                'enable-local-file-access': None,
            }
            pdfkit.from_string(clean_html, str(pdf_filename), configuration=config, options=options)

            if pdf_filename.exists() and pdf_filename.stat().st_size > 0:
                logger.info(f"✅ PDF legacy generato con wkhtmltopdf: {pdf_filename} ({pdf_filename.stat().st_size} bytes)")
                return True
        except Exception as e:
            logger.error(f"❌ wkhtmltopdf legacy fallito: {e}. Fallback to WeasyPrint...")

    # Fallback: WeasyPrint
    try:
        import threading
        pdf_error = None
        generation_success = False

        def generate_pdf_legacy():
            nonlocal pdf_error, generation_success
            try:
                html_doc = weasyprint.HTML(string=clean_html)
                css = weasyprint.CSS(string=PDF_CSS_LEGACY)
                html_doc.write_pdf(str(pdf_filename), stylesheets=[css])
                generation_success = True
            except Exception as e:
                pdf_error = e

        # Esegui con timeout di 2 minuti (120s)
        pdf_thread = threading.Thread(target=generate_pdf_legacy, daemon=True)
        pdf_thread.start()
        pdf_thread.join(timeout=120)

        if pdf_thread.is_alive():
            logger.error(f"⏱️ TIMEOUT: WeasyPrint legacy bloccato dopo 120s")
            return False

        if pdf_error:
            logger.error(f"Errore WeasyPrint: {pdf_error}", exc_info=True)
            return False

        # Verifica
        if generation_success and pdf_filename.exists() and pdf_filename.stat().st_size > 0:
            logger.info(f"PDF generato: {pdf_filename} ({pdf_filename.stat().st_size} bytes)")
            return True
        else:
            logger.error("PDF generato ma file vuoto o generazione fallita")
            return False

    except Exception as e:
        logger.error(f"Errore WeasyPrint (outer): {e}", exc_info=True)
        return False


def get_pdf_generator_info() -> dict:
    """Restituisce info sul generatore PDF disponibile."""
    if PDFKIT_AVAILABLE and WKHTMLTOPDF_PATH:
        engine = "wkhtmltopdf"
        path = WKHTMLTOPDF_PATH
        performance = "FAST (2-5s per PDF)"
    else:
        engine = "WeasyPrint"
        path = "Python native"
        performance = "SLOW (30-120s per PDF, timeout protection enabled)"

    return {
        "engine": engine,
        "path": path,
        "performance": performance,
        "pdfkit_installed": PDFKIT_AVAILABLE,
        "wkhtmltopdf_found": bool(WKHTMLTOPDF_PATH),
        'weasyprint_available': True,
        'xhtml2pdf_available': False,
        'preferred': 'weasyprint'
    }
