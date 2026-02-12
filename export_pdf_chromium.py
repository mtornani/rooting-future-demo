"""
Rooting Future Strategy Engine - Chromium PDF Export via Playwright
Engine: Playwright + Chromium (headless) - FASTEST & BEST QUALITY
Design: Native browser rendering for pixel-perfect PDF output

This module provides PDF generation using Playwright's Chromium browser,
which produces identical output to "Print to PDF" in Google Chrome.

Benefits over WeasyPrint/wkhtmltopdf:
- Full CSS3 support (variables, gradients, flexbox, grid)
- Perfect font rendering
- Fast: 2-5 seconds per PDF
- Identical to Chrome's native PDF output
"""

import logging
import time
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# Try to import Playwright
PLAYWRIGHT_AVAILABLE = False
try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
    PLAYWRIGHT_AVAILABLE = True
    logger.info("✅ Playwright disponibile per generazione PDF via Chromium")
except ImportError:
    logger.warning("⚠️ Playwright non installato. Installa con: pip install playwright && playwright install chromium")

from export_core import BaseExporter
from stw_matrix import generate_stw_matrix_html, get_stw_matrix_css
from config import OUTPUT_DIR


class ChromiumPdfExporter(BaseExporter):
    """
    Esporta piani strategici in PDF usando Playwright + Chromium.

    Vantaggi:
    - Rendering identico a Chrome (engine Blink/V8)
    - Supporto CSS completo (variabili, gradienti, flexbox, grid)
    - Velocità: 2-5 secondi per PDF
    - Output professionale e consistente
    """

    def __init__(self, output_dir: Path = None):
        super().__init__(output_dir)
        self._browser = None
        self._playwright = None

    def export(
        self,
        plan_data: Dict,
        club_name: str,
        sources: List[Dict] = None,
        metadata: Dict = None,
    ) -> Path:
        """
        Genera il file PDF usando Chromium headless.

        Args:
            plan_data: Dizionario con le sezioni del piano
            club_name: Nome del club
            sources: Lista delle fonti utilizzate
            metadata: Metadati aggiuntivi (colori, anno, etc.)

        Returns:
            Path al file PDF generato
        """
        if not PLAYWRIGHT_AVAILABLE:
            raise ImportError("Playwright non disponibile. Installa con: pip install playwright && playwright install chromium")

        start_time = time.time()

        # Estrazione metadati e colori standardizzati
        meta = self._extract_metadata(metadata)

        # Genera l'HTML completo
        html_content = self._generate_html(
            plan_data=plan_data,
            club_name=club_name,
            sources=sources or [],
            meta=meta
        )

        # Output path standardizzato
        filename = self._get_safe_filename(club_name, "pdf", prefix="PianoStrategico")
        filepath = self.output_dir / filename

        # Genera PDF con Playwright
        logger.info(f"🚀 Inizio generazione PDF per {club_name} via Playwright/Chromium...")

        try:
            with sync_playwright() as playwright:
                # Avvia Chromium in modalità headless
                browser = playwright.chromium.launch(
                    headless=True,
                    args=[
                        '--disable-gpu',
                        '--disable-dev-shm-usage',
                        '--no-sandbox',
                        '--disable-setuid-sandbox',
                    ]
                )

                # Crea pagina con viewport A4-like
                page = browser.new_page(
                    viewport={'width': 1240, 'height': 1754}  # ~A4 at 150dpi
                )

                # Carica l'HTML
                page.set_content(html_content, wait_until='networkidle', timeout=30000)

                # Attendi che i font siano caricati
                page.wait_for_timeout(500)

                # Genera PDF con impostazioni professionali
                page.pdf(
                    path=str(filepath),
                    format='A4',
                    margin={
                        'top': '20mm',
                        'right': '15mm',
                        'bottom': '20mm',
                        'left': '15mm'
                    },
                    print_background=True,
                    prefer_css_page_size=True,
                    display_header_footer=True,
                    header_template=self._get_header_template(club_name, meta),
                    footer_template=self._get_footer_template(),
                )

                browser.close()

            elapsed = time.time() - start_time
            logger.info(f"✅ PDF generato con Playwright/Chromium in {elapsed:.1f}s: {filepath}")

            return filepath

        except PlaywrightTimeout as e:
            logger.error(f"⏱️ TIMEOUT Playwright dopo 30s: {e}")
            raise
        except Exception as e:
            logger.error(f"❌ Errore Playwright: {e}", exc_info=True)
            raise

    def _get_header_template(self, club_name: str, meta: dict) -> str:
        """Template header per ogni pagina (esclusa la prima)"""
        current_year = meta.get('current_year', 2026)
        primary_color = meta.get('primary_color', '#1a365d')

        return f'''
        <div style="width: 100%; font-family: 'Montserrat', Arial, sans-serif; font-size: 8px;
                    padding: 5mm 15mm; border-bottom: 0.5px solid #e2e8f0; display: flex;
                    justify-content: space-between; color: #718096;">
            <span style="color: {primary_color}; font-weight: 700; letter-spacing: 1px;">
                {club_name.upper()}
            </span>
            <span style="letter-spacing: 0.5px;">
                PIANO STRATEGICO {current_year}—{current_year + 3}
            </span>
        </div>
        '''

    def _get_footer_template(self) -> str:
        """Template footer per ogni pagina"""
        return '''
        <div style="width: 100%; font-family: 'Inter', Arial, sans-serif; font-size: 8px;
                    padding: 5mm 15mm; border-top: 0.5px solid #e2e8f0; display: flex;
                    justify-content: space-between; color: #a0aec0;">
            <span>ROOTING FUTURE // STRATEGY ENGINE</span>
            <span style="font-weight: 600; color: #4a5568;">
                <span class="pageNumber"></span> / <span class="totalPages"></span>
            </span>
        </div>
        '''

    def _generate_html(self, plan_data: Dict, club_name: str, sources: List[Dict], meta: dict) -> str:
        """Genera l'HTML completo per il PDF"""

        # Colori dinamici
        club_primary = meta.get("primary_color", "#1a365d")
        club_secondary = meta.get("secondary_color", "#2E7D32")
        if club_secondary and club_secondary.lower() == "#ffffff":
            club_secondary = "#1a202c"
        contrast_color = meta.get("contrast_color", "#ffffff")
        current_year = meta.get("current_year", 2026)

        # Genera contenuto sezioni
        sections_html = self._generate_sections_html(plan_data, club_primary)

        # Genera matrice STW
        stw_matrix_html = generate_stw_matrix_html(club_primary)

        # Genera pagina metodologia
        methodology_html = self._generate_methodology_page(club_name, meta)

        return f'''
<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <title>Piano Strategico - {club_name}</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Montserrat:wght@600;700;800&display=swap" rel="stylesheet">
    <style>
        /* ===========================================
           CSS VARIABLES & RESET
           =========================================== */
        :root {{
            --club-primary: {club_primary};
            --club-secondary: {club_secondary};
            --contrast-color: {contrast_color};
            --text-color: #1a202c;
            --text-muted: #718096;
            --border-color: #e2e8f0;
            --bg-light: #f7fafc;
            --success: #38a169;
            --warning: #dd6b20;
            --info: #3182ce;
        }}

        *, *::before, *::after {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}

        /* ===========================================
           PAGE SETUP
           =========================================== */
        @page {{
            size: A4;
            margin: 20mm 15mm;
        }}

        @page :first {{
            margin: 0;
        }}

        body {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            font-size: 10pt;
            line-height: 1.6;
            color: var(--text-color);
            background: #ffffff;
        }}

        /* ===========================================
           TYPOGRAPHY
           =========================================== */
        h1, h2, h3, h4 {{
            font-family: 'Montserrat', sans-serif;
            font-weight: 700;
            line-height: 1.2;
            color: var(--club-primary);
        }}

        h1 {{
            font-size: 24pt;
            margin: 0 0 15px 0;
            padding-bottom: 10px;
            border-bottom: 3px solid var(--club-primary);
            page-break-before: always;
            page-break-after: avoid;
        }}

        h1:first-of-type {{
            page-break-before: avoid;
        }}

        h2 {{
            font-size: 16pt;
            margin: 25px 0 12px 0;
            padding-left: 12px;
            border-left: 4px solid var(--club-primary);
            page-break-after: avoid;
        }}

        h3 {{
            font-size: 12pt;
            margin: 18px 0 8px 0;
            color: var(--club-secondary);
            page-break-after: avoid;
        }}

        p {{
            margin-bottom: 10px;
            text-align: justify;
            orphans: 3;
            widows: 3;
        }}

        /* ===========================================
           COVER PAGE
           =========================================== */
        .cover {{
            width: 210mm;
            height: 297mm;
            background: linear-gradient(135deg, var(--club-primary) 0%, var(--club-secondary) 100%);
            color: var(--contrast-color);
            position: relative;
            overflow: hidden;
            page-break-after: always;
            display: flex;
            flex-direction: column;
            justify-content: center;
            padding: 40mm;
        }}

        .cover::before {{
            content: "";
            position: absolute;
            top: 0; left: 0; right: 0; bottom: 0;
            background: url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%23ffffff' fill-opacity='0.05'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E");
            opacity: 0.3;
        }}

        .cover-content {{
            position: relative;
            z-index: 10;
        }}

        .cover-brand {{
            font-family: 'Montserrat', sans-serif;
            font-size: 10pt;
            font-weight: 700;
            letter-spacing: 4px;
            background: rgba(0,0,0,0.3);
            color: #fff;
            padding: 8px 16px;
            display: inline-block;
            margin-bottom: 30px;
            text-transform: uppercase;
        }}

        .cover-club {{
            font-family: 'Montserrat', sans-serif;
            font-size: 52pt;
            font-weight: 800;
            line-height: 1.0;
            margin-bottom: 20px;
            text-transform: uppercase;
            letter-spacing: -1px;
        }}

        .cover-title {{
            font-family: 'Inter', sans-serif;
            font-size: 18pt;
            font-weight: 300;
            border-left: 3px solid var(--contrast-color);
            padding-left: 20px;
            margin-top: 30px;
            text-transform: uppercase;
            letter-spacing: 2px;
            opacity: 0.9;
        }}

        .cover-footer {{
            position: absolute;
            bottom: 40mm;
            left: 40mm;
            font-family: 'Montserrat', sans-serif;
            font-size: 8pt;
            letter-spacing: 2px;
            opacity: 0.6;
        }}

        /* ===========================================
           CONTENT SECTIONS
           =========================================== */
        .section-container {{
            margin-bottom: 20mm;
            page-break-inside: auto;
        }}

        .section-body {{
            text-align: justify;
        }}

        /* ===========================================
           BOXES & BADGES
           =========================================== */
        .kpi-box {{
            background: linear-gradient(135deg, #f7fafc 0%, #edf2f7 100%);
            border-left: 4px solid var(--club-primary);
            padding: 15px 20px;
            margin: 15px 0;
            border-radius: 0 8px 8px 0;
            page-break-inside: avoid;
        }}

        .kpi-box h4 {{
            font-size: 11pt;
            margin-bottom: 8px;
            color: var(--club-primary);
        }}

        .kpi-value {{
            font-size: 24pt;
            font-weight: 700;
            color: var(--club-primary);
        }}

        .insight-box {{
            background: #ebf8ff;
            border-left: 4px solid var(--info);
            padding: 12px 16px;
            margin: 12px 0;
            border-radius: 0 6px 6px 0;
            page-break-inside: avoid;
        }}

        .action-box {{
            background: #f0fff4;
            border-left: 4px solid var(--success);
            padding: 12px 16px;
            margin: 12px 0;
            border-radius: 0 6px 6px 0;
            page-break-inside: avoid;
        }}

        .warning-box {{
            background: #fffaf0;
            border-left: 4px solid var(--warning);
            padding: 12px 16px;
            margin: 12px 0;
            border-radius: 0 6px 6px 0;
            page-break-inside: avoid;
        }}

        /* Badges */
        .badge {{
            display: inline-block;
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 8pt;
            font-weight: 600;
            margin-right: 4px;
        }}

        .badge-success {{ background: #c6f6d5; color: #276749; }}
        .badge-warning {{ background: #feebc8; color: #c05621; }}
        .badge-info {{ background: #bee3f8; color: #2b6cb0; }}
        .badge-questionnaire {{ background: #e9d8fd; color: #6b46c1; }}
        .badge-research {{ background: #bee3f8; color: #2b6cb0; }}
        .badge-estimate {{ background: #feebc8; color: #c05621; }}

        /* ===========================================
           TABLES
           =========================================== */
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 15px 0;
            font-size: 9pt;
            page-break-inside: avoid;
        }}

        th, td {{
            border: 1px solid var(--border-color);
            padding: 10px 12px;
            text-align: left;
        }}

        th {{
            background: var(--club-primary);
            color: white;
            font-weight: 600;
            text-transform: uppercase;
            font-size: 8pt;
            letter-spacing: 0.5px;
        }}

        tr:nth-child(even) {{
            background: #f7fafc;
        }}

        /* ===========================================
           LISTS
           =========================================== */
        ul, ol {{
            margin: 10px 0 10px 20px;
            padding: 0;
        }}

        li {{
            margin-bottom: 6px;
            line-height: 1.5;
        }}

        li::marker {{
            color: var(--club-primary);
        }}

        /* ===========================================
           UTILITY CLASSES
           =========================================== */
        .text-center {{ text-align: center; }}
        .text-right {{ text-align: right; }}
        .mt-20 {{ margin-top: 20px; }}
        .mb-20 {{ margin-bottom: 20px; }}
        .page-break {{ page-break-before: always; }}

        /* ===========================================
           STW MATRIX STYLES
           =========================================== */
        {get_stw_matrix_css()}

        /* ===========================================
           CONFIDENCE TOOLTIP (hidden in PDF)
           =========================================== */
        .confidence-tooltip {{ display: none; }}
        .confidence-help {{ display: none; }}
        .tooltip-content {{ display: none; }}

        /* ===========================================
           PRINT OPTIMIZATIONS
           =========================================== */
        @media print {{
            body {{
                -webkit-print-color-adjust: exact !important;
                print-color-adjust: exact !important;
            }}

            .cover {{
                -webkit-print-color-adjust: exact !important;
                print-color-adjust: exact !important;
            }}
        }}
    </style>
</head>
<body>
    <!-- COVER PAGE -->
    <div class="cover">
        <div class="cover-content">
            <div class="cover-brand">STRATEGIC DOSSIER</div>
            <div class="cover-club">{club_name}</div>
            <div class="cover-title">
                Piano Strategico<br>
                Sviluppo {current_year}—{current_year + 3}
            </div>
        </div>
        <div class="cover-footer">
            GENERATED BY ROOTING FUTURE STRATEGY ENGINE v6.0
        </div>
    </div>

    <!-- METHODOLOGY PAGE -->
    {methodology_html}

    <!-- STW MATRIX -->
    {stw_matrix_html}

    <!-- CONTENT SECTIONS -->
    {sections_html}

    <!-- SOURCES -->
    {self._generate_sources_html(sources)}

</body>
</html>
'''

    def _generate_sections_html(self, plan_data: Dict, primary_color: str) -> str:
        """Genera HTML per tutte le sezioni del piano"""
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
                normalized_content = self._normalize_markdown(content)
                html.append(f'<div class="section-body">{self._markdown_to_html(normalized_content)}</div>')
                html.append(f"</div>")

        # Aggiungi eventuali sezioni non previste
        for key, content in plan_data.items():
            if key not in preferred_order and content:
                title = section_titles.get(key, key.replace("_", " ").title())
                html.append(f'<div class="section-container">')
                html.append(f"<h1>{title}</h1>")
                normalized_content = self._normalize_markdown(content)
                html.append(f'<div class="section-body">{self._markdown_to_html(normalized_content)}</div>')
                html.append(f"</div>")

        return "".join(html)

    def _generate_methodology_page(self, club_name: str, meta: dict) -> str:
        """Genera la pagina metodologia"""
        total_questionnaires = meta.get("total_questionnaires", 9)
        credibility_score = meta.get("credibility_score", 85)

        return f'''
    <div class="page-break" style="padding: 20mm;">
        <div style="text-align: center; margin-bottom: 30px;">
            <div style="display: inline-block; background: linear-gradient(135deg, #1a365d 0%, #2E7D32 100%);
                        padding: 20px 40px; border-radius: 10px;">
                <div style="font-family: 'Montserrat', sans-serif; font-size: 28pt; font-weight: 700;
                            color: white; letter-spacing: 3px; margin-bottom: 8px;">
                    ROOTING FUTURE
                </div>
                <div style="font-size: 11pt; color: rgba(255,255,255,0.9); letter-spacing: 1px;">
                    Strategic Planning Framework per il Calcio Italiano
                </div>
            </div>
        </div>

        <h2 style="font-size: 20pt; text-align: center; margin: 30px 0; border: none; padding: 0;">
            Metodologia & Dati di Input
        </h2>

        <div style="background: linear-gradient(135deg, #7B1FA2 0%, #9C27B0 100%);
                    padding: 20px; border-radius: 10px; margin: 20px 0; color: white;">
            <h3 style="margin: 0 0 15px 0; font-size: 14pt; color: white; border: none;">
                Questionari Compilati dai Membri del Board di {club_name}
            </h3>
            <div style="display: flex; justify-content: space-around; text-align: center;">
                <div>
                    <div style="font-size: 28pt; font-weight: 700;">{total_questionnaires}</div>
                    <div style="font-size: 9pt; opacity: 0.9;">Documenti Word</div>
                </div>
                <div>
                    <div style="font-size: 28pt; font-weight: 700;">{total_questionnaires * 15}+</div>
                    <div style="font-size: 9pt; opacity: 0.9;">Dati Forniti</div>
                </div>
                <div>
                    <div style="font-size: 28pt; font-weight: 700;">{credibility_score}%</div>
                    <div style="font-size: 9pt; opacity: 0.9;">Completezza</div>
                </div>
            </div>
        </div>

        <h3 style="font-size: 16pt; margin: 25px 0 15px 0;">Il Processo Rooting Future</h3>

        <div class="kpi-box" style="border-left-color: #7B1FA2;">
            <strong style="color: #7B1FA2;">1. Analisi Questionari Club</strong><br>
            Dati forniti direttamente da {club_name} tramite questionari Word strutturati.
        </div>

        <div class="kpi-box" style="border-left-color: #1565C0;">
            <strong style="color: #1565C0;">2. Web Research & Benchmark</strong><br>
            Integrazione dati da FIGC, Transfermarkt, Google, Visure Camerali.
        </div>

        <div class="kpi-box" style="border-left-color: #2E7D32;">
            <strong style="color: #2E7D32;">3. AI Multi-Agente STW-Aligned</strong><br>
            6 agenti specializzati elaborano il piano seguendo la matrice STW (21 obiettivi MACRO).
        </div>

        <div style="background: #f5f5f5; padding: 15px; border-left: 4px solid #1a365d; margin-top: 25px;">
            <h4 style="margin: 0 0 10px 0; font-size: 11pt; color: #1a365d;">Legenda Badge nei Dati:</h4>
            <div style="display: flex; gap: 20px; flex-wrap: wrap; font-size: 9pt;">
                <div><span class="badge badge-questionnaire">Da Questionario</span> Dati forniti da {club_name}</div>
                <div><span class="badge badge-research">Ricerca Web</span> Dati verificati online</div>
                <div><span class="badge badge-estimate">Stima AI</span> Elaborazione AI</div>
            </div>
        </div>
    </div>
'''

    def _generate_sources_html(self, sources: List[Dict]) -> str:
        """Genera HTML per le fonti"""
        if not sources:
            return ""

        html = ['<div class="section-container">', "<h1>Fonti e Metodologia</h1>", '<div class="section-body"><ul>']
        for s in sources[:20]:
            name = s.get("name", "Fonte esterna")
            url = s.get("url", "")
            html.append(f"<li><strong>{name}</strong><br><small style='color: #718096;'>{url}</small></li>")
        html.append("</ul></div></div>")
        return "".join(html)


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def generate_pdf_chromium(html_content: str, output_path: str, club_name: str = "Club") -> bool:
    """
    Funzione utility per generare PDF da HTML usando Chromium.

    Args:
        html_content: Contenuto HTML completo
        output_path: Path completo del file PDF di output
        club_name: Nome del club (per header)

    Returns:
        True se successo, False altrimenti
    """
    if not PLAYWRIGHT_AVAILABLE:
        logger.error("Playwright non disponibile")
        return False

    try:
        start_time = time.time()
        logger.info(f"🚀 Generazione PDF via Chromium: {output_path}")

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page()
            page.set_content(html_content, wait_until='networkidle', timeout=30000)
            page.wait_for_timeout(300)

            page.pdf(
                path=output_path,
                format='A4',
                margin={'top': '20mm', 'right': '15mm', 'bottom': '20mm', 'left': '15mm'},
                print_background=True,
            )

            browser.close()

        elapsed = time.time() - start_time
        logger.info(f"✅ PDF generato in {elapsed:.1f}s: {output_path}")
        return True

    except Exception as e:
        logger.error(f"❌ Errore generazione PDF Chromium: {e}", exc_info=True)
        return False


def is_playwright_available() -> bool:
    """Verifica se Playwright è disponibile"""
    return PLAYWRIGHT_AVAILABLE


def get_chromium_pdf_info() -> dict:
    """Restituisce info sul generatore PDF Chromium"""
    return {
        "engine": "Playwright + Chromium",
        "available": PLAYWRIGHT_AVAILABLE,
        "performance": "FAST (2-5s per PDF)",
        "quality": "HIGH (native Chrome rendering)",
        "css_support": "FULL (CSS3, variables, flexbox, grid)",
    }
