"""
Rooting Future Strategy Engine
Export HTML Print-First con Paged.js

Genera documenti HTML pronti per stampa/PDF con:
- Layout A4 paginato visibile nel browser
- Header/footer automatici su ogni pagina
- Gestione page-break intelligente
- Branding dinamico con colori del club
"""

import re
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from config import OUTPUT_DIR
from stw_matrix import generate_stw_matrix_html, get_stw_matrix_css

logger = logging.getLogger(__name__)


class PagedHtmlExporter:
    """
    Esporta piani strategici in HTML Print-First usando Paged.js.
    Il documento appare già paginato nel browser, pronto per Stampa -> PDF.
    """

    def __init__(self):
        OUTPUT_DIR.mkdir(exist_ok=True)
        self._output_dir = OUTPUT_DIR

    @property
    def output_dir(self):
        return self._output_dir

    @output_dir.setter
    def output_dir(self, value):
        self._output_dir = Path(value) if value else OUTPUT_DIR

    def export(
        self,
        plan_data: Dict,
        club_name: str,
        sources: List[Dict] = None,
        metadata: Dict = None
    ) -> Path:
        """
        Genera documento HTML print-first.

        Args:
            plan_data: Dict con sezioni del piano
            club_name: Nome del club
            sources: Lista fonti
            metadata: Metadati (include primary_color, secondary_color)

        Returns:
            Path del file generato
        """
        # Colori brand
        primary_color = metadata.get('primary_color', '#1a365d') if metadata else '#1a365d'
        secondary_color = metadata.get('secondary_color', '#000000') if metadata else '#000000'
        category = metadata.get('category', '') if metadata else ''

        # Genera HTML
        html = self._generate_html(
            plan_data=plan_data,
            club_name=club_name,
            sources=sources or [],
            primary_color=primary_color,
            secondary_color=secondary_color,
            category=category
        )

        # Salva
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = re.sub(r'[^\w\s-]', '', club_name).strip().replace(' ', '_')
        filename = f"{safe_name}_PianoStrategico_{timestamp}_print.html"
        filepath = self._output_dir / filename

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html)

        logger.info(f"Paged HTML exported: {filepath}")
        return filepath

    def _generate_html(
        self,
        plan_data: Dict,
        club_name: str,
        sources: List[Dict],
        primary_color: str,
        secondary_color: str,
        category: str
    ) -> str:
        """Genera l'HTML completo con Paged.js"""

        # Calcola colore chiaro per sfondi
        light_color = self._lighten_color(primary_color, 0.9)
        contrast_color = self._get_contrast_color(primary_color)

        current_year = datetime.now().year
        generation_date = datetime.now().strftime("%d/%m/%Y")

        # Genera contenuto sezioni
        sections_html = self._generate_sections(plan_data, primary_color)
        sources_html = self._generate_sources(sources) if sources else ""

        html = f'''<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Piano Strategico - {club_name}</title>

    <!-- Google Fonts: Oswald (Tactical) & Inter (Body) -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&family=Oswald:wght@400;500;600;700&display=swap" rel="stylesheet">

    <!-- Paged.js - Safe Manual Start (Anti-Crash Mode) -->
    <script>window.PagedConfig = {{ auto: false }};</script>
    <script src="https://unpkg.com/pagedjs/dist/paged.polyfill.js"></script>
    <script>
        document.addEventListener("DOMContentLoaded", function() {{
            // Wait for fonts to load
            document.fonts.ready.then(function() {{
                var isMobile = window.innerWidth <= 768 ||
                               /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
                
                if (isMobile) {{
                    console.log("Mobile view detected");
                    document.documentElement.classList.add('mobile-view');
                    document.body.classList.add('mobile-view');
                }} else {{
                    console.log("Fonts loaded. Starting Paged.js with delay...");
                    // 500ms Delay to ensure DOM stability causing WSOD
                    setTimeout(() => {{ 
                        window.PagedPolyfill.preview(); 
                    }}, 500);
                }}
            }});
        }});
    </script>

    <style>
        /* ===========================================
           CSS VARIABLES - TACTICAL THEME
           =========================================== */
        :root {{
            --primary-color: {primary_color};
            --secondary-color: {secondary_color};
            --light-color: #{light_color};
            --contrast-color: {contrast_color};
            --text-color: #111111;
            --text-light: #555555;
            --border-color: #eeeeee;
            --page-width: 210mm;
            --page-height: 290mm; /* SAFE HEIGHT */
            --margin-top: 20mm;
            --margin-bottom: 25mm;
            --margin-left: 20mm;
            --margin-right: 20mm;
        }}

        /* ===========================================
           SAFETY WRAPPER & VISIBILITY
           =========================================== */
        * {{ 
            box-sizing: border-box !important; 
            break-inside: auto;
        }}

        body {{
            font-family: 'Inter', sans-serif;
            font-size: 10pt;
            line-height: 1.6;
            color: var(--text-color);
            background: #ffffff;
            visibility: visible !important;
            opacity: 1 !important;
            -webkit-print-color-adjust: exact !important;
            print-color-adjust: exact !important;
        }}

        .pagedjs_pages {{
            display: flex !important;
            flex-direction: column !important;
        }}

        /* ===========================================
           PAGE ROOTS - ANTI-CRASH GEOMETRY
           =========================================== */
        .cover, .editorial-spread, .chapter-cover {{
            display: block !important; /* KILL FLEX ON ROOTS */
            position: relative !important;
            width: var(--page-width) !important;
            height: 290mm !important; /* 7mm Safety Margin */
            max-height: 290mm !important;
            overflow: hidden !important; /* NO MERCY */
            page-break-after: always !important;
            break-after: page !important;
            margin: 0 auto !important;
        }}

        /* INNER WRAPPERS FOR FLEX LAYOUT */
        .cover-inner, .editorial-inner, .chapter-inner {{
            display: flex;
            flex-direction: column;
            height: 100%;
            width: 100%;
            position: relative;
            z-index: 2;
        }}

        /* AGGRESSIVE HEADERS - OSWALD */
        h1, h2, h3, h4, 
        .cover-title, .chapter-title, 
        .toc-title, .kpi-value {{
            font-family: 'Oswald', sans-serif;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}

        h1 {{
            font-size: 32pt;
            font-weight: 700;
            color: var(--primary-color);
            border-bottom: 4px solid var(--primary-color);
            padding-bottom: 2mm;
            margin: 10mm 0 6mm 0;
            line-height: 1;
        }}

        h2 {{
            font-size: 18pt;
            font-weight: 600;
            color: #000;
            margin: 8mm 0 4mm 0;
            border-left: 6px solid var(--primary-color);
            padding-left: 3mm;
        }}

        /* ===========================================
           COPERTINA POSTER RE-DESIGN (NO FLEX ROOT)
           =========================================== */
        .cover-bg {{
            position: absolute;
            top: 0; left: 0; right: 0; bottom: 0;
            background-color: var(--primary-color);
            background-image: repeating-linear-gradient(
                135deg,
                var(--primary-color),
                var(--primary-color) 20px,
                {self._darken_color(primary_color, 0.1)} 20px,
                {self._darken_color(primary_color, 0.1)} 21px
            );
            z-index: 0;
        }}

        .cover-datastrip {{
            position: absolute;
            top: 0; right: 0; bottom: 0; width: 15mm;
            background: #000; z-index: 2;
            display: flex; flex-direction: column; justify-content: space-between;
            align-items: center; padding: 10mm 0;
            border-left: 1px solid rgba(255,255,255,0.2);
        }}

        .datastrip-text {{
            writing-mode: vertical-rl; transform: rotate(180deg);
            color: rgba(255,255,255,0.6); font-family: 'Inter', monospace;
            font-size: 8pt; letter-spacing: 2px; text-transform: uppercase;
        }}

        .cover-inner {{
            padding: 20mm;
            padding-right: 40mm;
            justify-content: center;
        }}

        .cover-brand {{
            font-family: 'Inter', monospace; font-size: 9pt; letter-spacing: 4px;
            background: #000; color: #fff; padding: 2mm 4mm;
            margin-bottom: 20mm; align-self: flex-start;
        }}

        .cover-club {{
            font-family: 'Oswald', sans-serif; font-size: 72pt; font-weight: 700;
            line-height: 0.85; text-transform: uppercase;
            margin-left: -5mm; margin-bottom: 10mm;
            text-shadow: 5px 5px 0px rgba(0,0,0,0.2);
        }}

        .cover-footer {{
            margin-top: auto; display: flex; gap: 10mm;
            font-family: 'Inter', monospace; font-size: 9pt;
            border-top: 1px solid rgba(255,255,255,0.3); padding-top: 5mm;
        }}

        /* ===========================================
           EDITORIAL SPREAD (NO FLEX ROOT)
           =========================================== */
        .editorial-inner {{
            display: grid;
            grid-template-columns: 1fr 2fr;
        }}

        .editorial-toc {{
            background: var(--secondary-color);
            color: #fff;
            padding: 20mm 10mm;
        }}

        .editorial-summary {{
            background: #fff;
            padding: 20mm 15mm;
        }}

        /* ===========================================
           CHAPTER COVERS
           =========================================== */
        .chapter-inner {{
            justify-content: center;
            padding: 30mm 20mm;
            background: linear-gradient(135deg, var(--primary-color) 0%, var(--secondary-color) 100%);
            color: var(--contrast-color);
        }}

        .chapter-number-big {{
            font-size: 120pt; font-weight: 800; opacity: 0.15;
            position: absolute; top: 20mm; right: 20mm;
        }}

        /* ===========================================
           CONTENT & TABLES
           =========================================== */
        .chapter-content {{
            column-count: 2; column-gap: 10mm;
            text-align: justify;
        }}

        img, .bento-grid, table, .kpi-box {{
            break-inside: avoid !important;
        }}

        @page {{
            size: A4;
            margin: var(--margin-top) var(--margin-right) var(--margin-bottom) var(--margin-left);
        }}


        /* ===========================================
           LAYOUT GENERALE
           =========================================== */
        .chapter-content {{
            column-count: 2;
            column-gap: 10mm;
            column-rule: 1px solid #eee;
            text-align: justify;
        }}

        /* Full width elements */
        .chapter-content h2, h3, table, figure, .bento-grid, blockquote {{
            column-span: all;
        }}

        /* Paged.js Setup */
        @page {{
            size: A4;
            margin: var(--margin-top) var(--margin-right) var(--margin-bottom) var(--margin-left);
            
            @bottom-left {{
                content: "{club_name} // STRATEGY";
                font-family: 'Oswald', sans-serif;
                font-size: 8pt;
                color: #999;
            }}
            
            @bottom-right {{
                content: counter(page);
                font-family: 'Oswald', sans-serif;
                font-weight: 700;
                font-size: 12pt;
                color: var(--primary-color);
            }}
        }}

        @page:first {{ margin: 0; @bottom-left {{ content: none; }} @bottom-right {{ content: none; }} }}
        @page cover {{ margin: 0; }}

            page-break-before: always !important;
            break-before: page !important;
        }}

        .chapter:first-of-type {{
            page-break-before: auto !important;
            break-before: auto !important;
        }}

        /* ===========================================
           CHAPTER COVER - COPERTINE CAPITOLO
           =========================================== */
        .chapter-cover {{
            height: 100%;
            min-height: 250mm;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: flex-start;
            padding: 30mm 20mm;
            background: linear-gradient(135deg, var(--primary-color) 0%, var(--secondary-color) 100%);
            color: var(--contrast-color);
            position: relative;
        }}

        .chapter-cover::before {{
            content: "";
            position: absolute;
            top: 0;
            right: 0;
            width: 40%;
            height: 100%;
            background: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='100' height='100' viewBox='0 0 100 100'%3E%3Cg fill='%23ffffff' fill-opacity='0.03'%3E%3Cpolygon points='0,100 100,0 100,100'/%3E%3C/g%3E%3C/svg%3E");
            background-size: 50px 50px;
        }}

        .chapter-number-big {{
            font-size: 120pt;
            font-weight: 800;
            opacity: 0.15;
            position: absolute;
            top: 20mm;
            right: 20mm;
            line-height: 1;
        }}

        .chapter-title-big {{
            font-size: 42pt;
            font-weight: 700;
            line-height: 1.1;
            margin-bottom: 10mm;
            max-width: 70%;
            position: relative;
            z-index: 1;
        }}

        .chapter-subtitle {{
            font-size: 14pt;
            opacity: 0.85;
            max-width: 60%;
            line-height: 1.5;
            position: relative;
            z-index: 1;
        }}

        p {{
            orphans: 3;
            widows: 3;
        }}

        /* ===========================================
           HERO COVER - HIGH-END SPORTS MAGAZINE
           =========================================== */
        .cover {{
            width: var(--page-width);
            height: var(--page-height);
            background: var(--primary-color);
            display: flex;
            flex-direction: column;
            justify-content: flex-end;
            align-items: flex-start;
            color: var(--contrast-color);
            position: relative;
            page: cover;
            overflow: hidden;
        }}

        /* Texture pattern diagonale */
        .cover::before {{
            content: "";
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background:
                repeating-linear-gradient(
                    -45deg,
                    transparent,
                    transparent 2px,
                    rgba(255,255,255,0.03) 2px,
                    rgba(255,255,255,0.03) 4px
                ),
                radial-gradient(
                    ellipse 80% 50% at 70% 20%,
                    rgba(255,255,255,0.1) 0%,
                    transparent 50%
                );
            pointer-events: none;
        }}

        /* Ghost Shield - Filigrana di lusso */
        .cover::after {{
            content: "";
            position: absolute;
            top: 50%;
            right: -5%;
            transform: translateY(-50%);
            width: 280mm;
            height: 280mm;
            border: 3px solid rgba(255,255,255,0.08);
            border-radius: 50%;
            background: radial-gradient(
                circle at center,
                rgba(255,255,255,0.04) 0%,
                transparent 70%
            );
            mix-blend-mode: overlay;
        }}

        .cover-content {{
            position: relative;
            z-index: 2;
            padding: 25mm;
            width: 100%;
        }}

        .cover-brand {{
            font-size: 10pt;
            letter-spacing: 6px;
            text-transform: uppercase;
            opacity: 0.7;
            margin-bottom: 8mm;
            font-weight: 500;
        }}

        .cover-title {{
            font-size: 18pt;
            font-weight: 300;
            letter-spacing: 8px;
            text-transform: uppercase;
            opacity: 0.9;
            margin-bottom: 5mm;
        }}

        .cover-club {{
            font-size: 72pt;
            font-weight: 900;
            text-transform: uppercase;
            letter-spacing: -2px;
            line-height: 0.9;
            margin-bottom: 15mm;
            max-width: 85%;
            word-wrap: break-word;
        }}

        .cover-period {{
            font-size: 32pt;
            font-weight: 200;
            letter-spacing: 4px;
            opacity: 0.85;
        }}

        /* Footer tecnico con codice a barre finto */
        .cover-footer {{
            position: absolute;
            bottom: 0;
            left: 0;
            right: 0;
            background: rgba(0,0,0,0.3);
            padding: 6mm 25mm;
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 8pt;
            letter-spacing: 1px;
            text-transform: uppercase;
            z-index: 3;
        }}

        .cover-footer-left {{
            display: flex;
            flex-direction: column;
            gap: 1mm;
        }}

        .cover-footer-barcode {{
            display: flex;
            align-items: flex-end;
            gap: 1px;
            height: 12mm;
        }}

        .cover-footer-barcode span {{
            display: block;
            width: 2px;
            background: var(--contrast-color);
            opacity: 0.8;
        }}

        .cover-category {{
            background: rgba(255,255,255,0.15);
            padding: 2mm 5mm;
            font-size: 8pt;
            letter-spacing: 2px;
            text-transform: uppercase;
            position: absolute;
            top: 25mm;
            right: 25mm;
            z-index: 3;
        }}

        /* ===========================================
           EDITORIAL INDEX PAGE - LAYOUT ASIMMETRICO
           =========================================== */
        .editorial-spread {{
            width: var(--page-width);
            /* CRITICAL: Reduced height to prevent infinite loop */
            height: 295mm !important;
            max-height: 295mm !important;
            display: grid;
            grid-template-columns: 1fr 2fr;
            page: editorial;
            overflow: hidden !important;
            break-after: page;
        }}

        @page editorial {{
            margin: 0;
            @bottom-left {{ content: none; }}
            @bottom-right {{ content: none; }}
            @bottom-center {{ content: none; }}
        }}

        /* Colonna sinistra - TOC su sfondo scuro */
        .editorial-toc {{
            background: var(--secondary-color);
            color: {self._get_contrast_color(secondary_color)};
            padding: 20mm 12mm;
            display: flex;
            flex-direction: column;
        }}

        .editorial-toc-header {{
            font-size: 8pt;
            letter-spacing: 4px;
            text-transform: uppercase;
            opacity: 0.6;
            margin-bottom: 10mm;
            padding-bottom: 3mm;
            border-bottom: 1px solid rgba(255,255,255,0.2);
        }}

        .editorial-toc-item {{
            display: flex;
            align-items: baseline;
            gap: 4mm;
            padding: 3mm 0;
            border-bottom: none;
        }}

        .editorial-toc-number {{
            font-size: 24pt;
            font-weight: 800;
            opacity: 0.3;
            min-width: 12mm;
        }}

        .editorial-toc-title {{
            font-size: 9pt;
            font-weight: 600;
            line-height: 1.3;
        }}

        .editorial-toc-stw {{
            margin-top: auto;
            padding: 4mm;
            background: rgba(255,255,255,0.1);
            border-radius: 2mm;
        }}

        .editorial-toc-stw-title {{
            font-size: 8pt;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 2mm;
        }}

        .editorial-toc-stw-desc {{
            font-size: 7pt;
            opacity: 0.8;
            line-height: 1.4;
        }}

        /* Colonna destra - Executive Summary */
        .editorial-summary {{
            background: #ffffff;
            padding: 20mm 15mm;
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }}

        .editorial-summary-header {{
            margin-bottom: 8mm;
        }}

        .editorial-summary-label {{
            font-size: 8pt;
            letter-spacing: 3px;
            text-transform: uppercase;
            color: var(--primary-color);
            margin-bottom: 3mm;
        }}

        .editorial-summary-title {{
            font-size: 28pt;
            font-weight: 800;
            color: var(--text-color);
            line-height: 1.1;
        }}

        .editorial-summary-content {{
            flex: 1;
            font-size: 9pt;
            line-height: 1.7;
            color: var(--text-color);
        }}

        /* Drop Cap stilizzato */
        .editorial-summary-content .drop-cap {{
            float: left;
            font-size: 48pt;
            font-weight: 900;
            line-height: 0.8;
            padding-right: 3mm;
            padding-top: 2mm;
            color: var(--primary-color);
        }}

        /* KPI Bento Grid nell'editorial */
        .editorial-kpi-grid {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 3mm;
            margin: 6mm 0;
        }}

        .editorial-kpi-box {{
            padding: 4mm;
            border-radius: 2mm;
            text-align: center;
        }}

        .editorial-kpi-box.primary {{
            background: var(--primary-color);
            color: var(--contrast-color);
        }}

        .editorial-kpi-box.secondary {{
            background: var(--secondary-color);
            color: {self._get_contrast_color(secondary_color)};
        }}

        .editorial-kpi-box.light {{
            background: var(--light-color);
            color: var(--text-color);
        }}

        .editorial-kpi-value {{
            font-size: 20pt;
            font-weight: 800;
            line-height: 1;
        }}

        .editorial-kpi-label {{
            font-size: 6pt;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-top: 2mm;
            opacity: 0.8;
        }}

        /* Legacy TOC (per compatibilità) */
        .toc {{
            padding: 15mm 0;
        }}

        .toc h1 {{
            color: var(--primary-color);
            font-size: 28pt;
            margin-bottom: 10mm;
            padding-bottom: 5mm;
            border-bottom: 3px solid var(--primary-color);
        }}

        .toc-item {{
            display: flex;
            align-items: baseline;
            padding: 3mm 0;
            border-bottom: 1px dotted var(--border-color);
        }}

        .toc-number {{
            font-weight: 700;
            color: var(--primary-color);
            min-width: 10mm;
        }}

        .toc-title {{
            flex: 1;
        }}

        .toc-page {{
            color: var(--text-light);
            font-size: 10pt;
        }}

        /* ===========================================
           CAPITOLI E CONTENUTO
           =========================================== */
        .chapter {{
            page: chapter;
        }}

        .chapter-header {{
            background: linear-gradient(135deg, var(--primary-color), {self._darken_color(primary_color, 0.2)});
            color: var(--contrast-color);
            padding: 15mm 10mm;
            margin: -20mm -20mm 10mm -20mm;
            text-align: center;
        }}

        .chapter-number {{
            font-size: 14pt;
            opacity: 0.8;
            letter-spacing: 3px;
            text-transform: uppercase;
        }}

        .chapter-title {{
            font-size: 28pt;
            font-weight: 700;
            margin-top: 3mm;
            string-set: chapter-title content();
        }}

        h1 {{
            color: var(--primary-color);
            font-size: 22pt;
            font-weight: 700;
            margin: 8mm 0 5mm 0;
            padding-bottom: 3mm;
            border-bottom: 2px solid var(--primary-color);
        }}

        h2 {{
            color: var(--primary-color);
            font-size: 16pt;
            font-weight: 600;
            margin: 6mm 0 4mm 0;
        }}

        h3 {{
            color: var(--secondary-color);
            font-size: 13pt;
            font-weight: 600;
            margin: 5mm 0 3mm 0;
        }}

        h4 {{
            color: var(--text-color);
            font-size: 11pt;
            font-weight: 600;
            margin: 4mm 0 2mm 0;
        }}

        p {{
            margin-bottom: 3mm;
            text-align: justify;
        }}

        /* ===========================================
           LISTE PREMIUM - FEATURE LIST STYLE
           =========================================== */

        /* Reset liste base */
        ul, ol {{
            margin: 4mm 0 6mm 0;
            padding: 0;
            list-style: none;
        }}

        /* ===========================================
           LISTE PUNTATE (UL) - Chevron/Square Marker
           =========================================== */
        .chapter-content ul {{
            margin: 4mm 0 6mm 0;
            padding: 0;
        }}

        .chapter-content ul li {{
            position: relative;
            padding-left: 6mm;
            margin-bottom: 3mm;
            line-height: 1.6;
        }}

        .chapter-content ul li::before {{
            content: "›";
            position: absolute;
            left: 0;
            top: 0;
            color: var(--primary-color);
            font-weight: 700;
            font-size: 1.3em;
            line-height: 1.2;
        }}

        /* Nested UL - secondo livello con quadratino */
        .chapter-content ul ul {{
            margin: 2mm 0 2mm 4mm;
        }}

        .chapter-content ul ul li::before {{
            content: "▪";
            font-size: 0.8em;
            top: 0.15em;
        }}

        /* Terzo livello - trattino */
        .chapter-content ul ul ul li::before {{
            content: "–";
            font-size: 1em;
        }}

        /* ===========================================
           LISTE NUMERATE (OL) - Bold Number Style
           =========================================== */
        .chapter-content ol {{
            margin: 4mm 0 6mm 0;
            padding: 0;
            counter-reset: list-counter;
        }}

        .chapter-content ol li {{
            position: relative;
            padding-left: 10mm;
            margin-bottom: 3.5mm;
            line-height: 1.6;
            counter-increment: list-counter;
        }}

        .chapter-content ol li::before {{
            content: counter(list-counter) ".";
            position: absolute;
            left: 0;
            top: 0;
            color: var(--primary-color);
            font-weight: 800;
            font-size: 1.15em;
            min-width: 8mm;
        }}

        /* Nested OL - lettere */
        .chapter-content ol ol {{
            margin: 2mm 0 2mm 4mm;
            counter-reset: nested-counter;
        }}

        .chapter-content ol ol li {{
            counter-increment: nested-counter;
            padding-left: 8mm;
        }}

        .chapter-content ol ol li::before {{
            content: counter(nested-counter, lower-alpha) ")";
            font-size: 1em;
            font-weight: 600;
        }}

        /* ===========================================
           HIGHLIGHT LIST - Key Takeaways Card Style
           =========================================== */
        .chapter-content ul.highlight-list,
        .chapter-content ol.highlight-list {{
            background: linear-gradient(135deg, #f8f9fa 0%, #ffffff 100%);
            border: 1px solid var(--border-color);
            border-left: 4px solid var(--primary-color);
            border-radius: 0 3mm 3mm 0;
            padding: 5mm 5mm 5mm 2mm;
            margin: 6mm 0;
        }}

        .chapter-content ul.highlight-list li,
        .chapter-content ol.highlight-list li {{
            padding-left: 7mm;
            margin-bottom: 3mm;
            padding-bottom: 3mm;
            border-bottom: 1px dashed rgba(0,0,0,0.08);
        }}

        .chapter-content ul.highlight-list li:last-child,
        .chapter-content ol.highlight-list li:last-child {{
            margin-bottom: 0;
            padding-bottom: 0;
            border-bottom: none;
        }}

        /* ===========================================
           COMPACT LIST - Per liste corte inline
           =========================================== */
        .chapter-content ul.compact {{
            display: flex;
            flex-wrap: wrap;
            gap: 3mm;
            margin: 4mm 0;
        }}

        .chapter-content ul.compact li {{
            background: var(--light-color);
            padding: 2mm 4mm;
            border-radius: 2mm;
            margin-bottom: 0;
            font-size: 9pt;
        }}

        .chapter-content ul.compact li::before {{
            display: none;
        }}

        /* ===========================================
           CHECK LIST - Per liste di completamento
           =========================================== */
        .chapter-content ul.checklist li::before {{
            content: "✓";
            color: #10b981;
            font-weight: 700;
            font-size: 1em;
        }}

        /* ===========================================
           TIMELINE LIST - Per roadmap/fasi
           =========================================== */
        .chapter-content ol.timeline {{
            border-left: 2px solid var(--primary-color);
            margin-left: 4mm;
            padding-left: 0;
        }}

        .chapter-content ol.timeline li {{
            padding-left: 12mm;
            padding-bottom: 4mm;
            margin-bottom: 0;
            position: relative;
        }}

        .chapter-content ol.timeline li::before {{
            content: counter(list-counter);
            position: absolute;
            left: -5mm;
            top: 0;
            width: 8mm;
            height: 8mm;
            background: var(--primary-color);
            color: var(--contrast-color);
            border-radius: 50%;
            font-size: 9pt;
            font-weight: 700;
            display: flex;
            align-items: center;
            justify-content: center;
            min-width: auto;
        }}

        .chapter-content ol.timeline li::after {{
            content: "";
            position: absolute;
            left: -1mm;
            top: 10mm;
            width: 6mm;
            height: 1px;
            background: var(--border-color);
        }}

        /* ===========================================
           TABELLE
           =========================================== */
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 5mm 0;
            font-size: 10pt;
        }}

        th {{
            background: var(--primary-color);
            color: var(--contrast-color);
            padding: 3mm 4mm;
            text-align: left;
            font-weight: 600;
            text-transform: uppercase;
            font-size: 9pt;
            letter-spacing: 0.5px;
        }}

        td {{
            padding: 3mm 4mm;
            border-bottom: 1px solid var(--border-color);
        }}

        tr:nth-child(even) td {{
            background: var(--light-color);
        }}

        /* ===========================================
           BOX INFORMATIVI
           =========================================== */
        .kpi-box {{
            background: linear-gradient(135deg, var(--light-color), #ffffff);
            border-left: 4px solid var(--primary-color);
            padding: 5mm;
            margin: 5mm 0;
            border-radius: 0 2mm 2mm 0;
        }}

        .kpi-box h4 {{
            color: var(--primary-color);
            margin-bottom: 2mm;
        }}

        .info-box {{
            background: #f8fafc;
            border: 1px solid var(--border-color);
            border-radius: 2mm;
            padding: 5mm;
            margin: 5mm 0;
        }}

        .highlight-box {{
            background: var(--primary-color);
            color: var(--contrast-color);
            padding: 5mm;
            margin: 5mm 0;
            border-radius: 2mm;
        }}

        .highlight-box h4 {{
            color: var(--contrast-color);
        }}


        /* ===========================================
           BENTO DASHBOARD - EXECUTIVE SUMMARY
           =========================================== */
        .bento-grid {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            grid-template-rows: auto;
            gap: 4mm;
            margin: 8mm 0;
            column-span: all;
        }}

        .bento-card {{
            background: var(--light-color);
            border-radius: 3mm;
            padding: 5mm;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            min-height: 25mm;
            break-inside: avoid;
            page-break-inside: avoid;
        }}

        .bento-card.primary {{
            background: var(--primary-color);
            color: var(--contrast-color);
        }}

        .bento-card.secondary {{
            background: var(--secondary-color);
            color: var(--text-color);
            border: 1px solid var(--border-color);
        }}

        .bento-card.accent {{
            background: linear-gradient(135deg, var(--primary-color), var(--secondary-color));
            color: var(--contrast-color);
        }}

        .bento-card.span-2 {{
            grid-column: span 2;
        }}

        .bento-card.span-3 {{
            grid-column: span 3;
        }}

        .bento-card.tall {{
            grid-row: span 2;
        }}

        .bento-kpi {{
            font-size: 28pt;
            font-weight: 800;
            line-height: 1;
            margin-bottom: 2mm;
        }}

        .bento-label {{
            font-size: 8pt;
            text-transform: uppercase;
            letter-spacing: 1px;
            opacity: 0.8;
        }}

        .bento-icon {{
            font-size: 24pt;
            margin-bottom: 3mm;
        }}

        .bento-title {{
            font-size: 11pt;
            font-weight: 700;
            margin-bottom: 2mm;
        }}

        .bento-text {{
            font-size: 9pt;
            line-height: 1.4;
        }}

        /* Quote Box */
        .quote-box {{
            background: var(--light-color);
            border-left: 4px solid var(--primary-color);
            padding: 6mm 8mm;
            margin: 8mm 0;
            font-size: 14pt;
            font-style: italic;
            line-height: 1.5;
            column-span: all;
        }}

        .quote-box cite {{
            display: block;
            font-size: 10pt;
            font-style: normal;
            margin-top: 3mm;
            color: var(--text-light);
        }}

        /* Sidebar per highlight */
        .sidebar-highlight {{
            background: var(--primary-color);
            color: var(--contrast-color);
            padding: 5mm;
            border-radius: 2mm;
            font-size: 9pt;
            margin: 4mm 0;
        }}

        .sidebar-highlight h4 {{
            color: var(--contrast-color);
            margin-bottom: 2mm;
        }}

        /* ===========================================
           CARD GRID
           =========================================== */
        .card-grid {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 5mm;
            margin: 5mm 0;
        }}

        .card {{
            background: #ffffff;
            border: 1px solid var(--border-color);
            border-radius: 2mm;
            padding: 5mm;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}

        .card-header {{
            background: var(--primary-color);
            color: var(--contrast-color);
            padding: 3mm 5mm;
            margin: -5mm -5mm 4mm -5mm;
            border-radius: 2mm 2mm 0 0;
            font-weight: 600;
            font-size: 10pt;
        }}

        /* ===========================================
           FONTI E APPENDICE
           =========================================== */
        .sources {{
            background: #f8fafc;
            padding: 5mm;
            border-radius: 2mm;
            margin-top: 10mm;
        }}

        .sources h2 {{
            font-size: 14pt;
            margin-bottom: 4mm;
        }}

        .source-item {{
            font-size: 9pt;
            padding: 2mm 0;
            border-bottom: 1px dotted var(--border-color);
        }}

        .source-item:last-child {{
            border-bottom: none;
        }}

        /* ===========================================
           DISCLAIMER
           =========================================== */
        .disclaimer {{
            margin-top: 10mm;
            padding: 5mm;
            background: #fff8e6;
            border-left: 4px solid #d69e2e;
            font-size: 9pt;
            color: var(--text-light);
            font-style: italic;
        }}

        /* ===========================================
           UTILITIES
           =========================================== */
        .text-center {{ text-align: center; }}
        .text-right {{ text-align: right; }}
        .font-bold {{ font-weight: 700; }}
        .text-primary {{ color: var(--primary-color); }}
        .text-muted {{ color: var(--text-light); }}
        .mt-4 {{ margin-top: 4mm; }}
        .mb-4 {{ margin-bottom: 4mm; }}
        .py-4 {{ padding-top: 4mm; padding-bottom: 4mm; }}

        /* ===========================================
           PRINT OVERRIDES
           =========================================== */
        @media print {{
            body {{
                background: white;
            }}

            .cover {{
                background: linear-gradient(135deg, var(--primary-color) 0%, {self._darken_color(primary_color, 0.3)} 100%) !important;
                -webkit-print-color-adjust: exact !important;
                print-color-adjust: exact !important;
            }}

            .chapter-header {{
                background: linear-gradient(135deg, var(--primary-color), {self._darken_color(primary_color, 0.2)}) !important;
                -webkit-print-color-adjust: exact !important;
                print-color-adjust: exact !important;
            }}

            th {{
                background: var(--primary-color) !important;
                -webkit-print-color-adjust: exact !important;
                print-color-adjust: exact !important;
            }}

            .kpi-box, .info-box, .highlight-box, .card {{
                -webkit-print-color-adjust: exact !important;
                print-color-adjust: exact !important;
            }}
        }}


        /* ===========================================
           INFOGRAPHIC BENTO GRID
           =========================================== */
        .infographic-section {{
            display: grid;
            grid-template-columns: repeat(12, 1fr);
            gap: 4mm;
            margin: 6mm 0;
            column-span: all;
            -webkit-column-span: all;
        }}

        /* Paragrafi dentro la sezione infografica */
        .infographic-section > p {{
            grid-column: span 12;
            margin: 2mm 0;
        }}

        .infographic-section > ul, .infographic-section > ol {{
            grid-column: span 12;
            margin: 2mm 0 2mm 6mm;
        }}

        .infographic-card {{
            background: var(--card-light);
            border-radius: 4mm;
            padding: 6mm;
            break-inside: avoid;
            page-break-inside: avoid;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            min-height: 30mm;
        }}

        .infographic-card.dark {{ background: var(--card-dark); color: #ffffff; }}
        .infographic-card.dark h3, .infographic-card.dark h4 {{ color: #ffffff; }}
        .infographic-card.medium {{ background: var(--card-medium); color: #ffffff; }}
        .infographic-card.brand {{ background: var(--primary-color); color: var(--contrast-color); }}
        .infographic-card.brand h3, .infographic-card.brand h4 {{ color: var(--contrast-color); }}
        .infographic-card.outline {{ background: transparent; border: 2px solid var(--primary-color); }}

        .infographic-card.col-12 {{ grid-column: span 12; }}
        .infographic-card.col-8 {{ grid-column: span 8; }}
        .infographic-card.col-6 {{ grid-column: span 6; }}
        .infographic-card.col-4 {{ grid-column: span 4; }}
        .infographic-card.col-3 {{ grid-column: span 3; }}

        .card-kpi {{ font-size: 48pt; font-weight: 800; line-height: 1; letter-spacing: -2px; margin-bottom: 2mm; }}
        .card-kpi-small {{ font-size: 32pt; font-weight: 700; line-height: 1; }}
        .card-label {{ font-size: 8pt; text-transform: uppercase; letter-spacing: 2px; opacity: 0.7; margin-top: auto; }}
        .card-title {{ font-size: 14pt; font-weight: 700; margin-bottom: 3mm; }}
        .card-subtitle {{ font-size: 9pt; opacity: 0.8; line-height: 1.4; }}

        .section-header {{
            grid-column: span 12;
            padding: 8mm 0 4mm 0;
            border-bottom: 3px solid var(--primary-color);
            margin-bottom: 2mm;
        }}

        .section-header h2 {{
            font-size: 22pt;
            font-weight: 800;
            color: var(--primary-color);
            margin: 0;
        }}

        /* ===========================================
           MOBILE VIEW - SCROLLABLE
           =========================================== */
        @media screen and (max-width: 768px) {{
            .pagedjs_pages, .pagedjs_page {{ display: contents !important; }}

            body {{
                background: #ffffff;
                font-size: 16px;
                line-height: 1.7;
                padding: 0;
                margin: 0;
            }}

            .cover {{
                width: 100%;
                height: auto;
                min-height: 100vh;
                padding: 60px 20px;
                justify-content: center;
                align-items: center;
                text-align: center;
            }}

            .cover::after {{ display: none; }}
            .cover-content {{ padding: 20px; width: 100%; }}
            .cover-brand {{ font-size: 10px; letter-spacing: 3px; margin-bottom: 20px; }}
            .cover-title {{ font-size: 14px; letter-spacing: 4px; }}
            .cover-club {{ font-size: 36px; letter-spacing: 0; line-height: 1.1; max-width: 100%; }}
            .cover-period {{ font-size: 18px; letter-spacing: 2px; }}
            .cover-category {{ position: relative; top: auto; right: auto; margin-bottom: 30px; }}
            .cover-footer {{
                position: relative;
                flex-direction: column;
                gap: 10px;
                padding: 20px;
                margin-top: 40px;
                background: rgba(0,0,0,0.2);
            }}
            .cover-footer-barcode {{ display: none; }}

            /* Editorial Spread - Stack verticale su mobile */
            .editorial-spread {{
                display: flex;
                flex-direction: column;
                width: 100%;
                height: auto;
            }}

            .editorial-toc {{
                padding: 30px 20px;
                order: 2;
            }}

            .editorial-toc-number {{ font-size: 18px; min-width: 30px; }}
            .editorial-toc-title {{ font-size: 14px; }}

            .editorial-summary {{
                padding: 30px 20px;
                order: 1;
            }}

            .editorial-summary-title {{ font-size: 28px; }}
            .editorial-summary-content {{ font-size: 14px; }}
            .editorial-summary-content .drop-cap {{ font-size: 36px; }}

            .editorial-kpi-grid {{
                grid-template-columns: repeat(3, 1fr);
                gap: 10px;
                margin: 20px 0;
            }}

            .editorial-kpi-value {{ font-size: 24px; }}
            .editorial-kpi-label {{ font-size: 8px; }}

            .chapter {{
                page-break-before: auto !important;
                break-before: auto !important;
                padding: 20px;
            }}

            .chapter-cover {{
                min-height: 60vh;
                padding: 40px 20px;
            }}

            .chapter-number-big {{ font-size: 80px; top: 10px; right: 10px; }}
            .chapter-title-big {{ font-size: 28px; max-width: 100%; }}
            .chapter-subtitle {{ font-size: 14px; max-width: 100%; }}

            h1 {{ font-size: 24px; margin: 24px 0 16px 0; }}
            h2 {{ font-size: 20px; margin: 20px 0 12px 0; }}
            h3 {{ font-size: 18px; margin: 16px 0 10px 0; }}
            h4 {{ font-size: 16px; margin: 12px 0 8px 0; }}

            p {{ font-size: 16px; line-height: 1.8; margin-bottom: 16px; }}

            .infographic-section {{
                display: flex;
                flex-direction: column;
                gap: 16px;
            }}

            .infographic-card {{
                grid-column: span 1 !important;
                min-height: auto;
                padding: 20px;
            }}

            .card-kpi {{ font-size: 36px; }}
            .card-title {{ font-size: 18px; }}

            .bento-grid {{
                display: flex;
                flex-direction: column;
                gap: 16px;
            }}

            .bento-card {{
                grid-column: span 1 !important;
                min-height: auto;
                padding: 20px;
            }}

            .bento-kpi {{ font-size: 32px; }}

            table {{
                display: block;
                overflow-x: auto;
                white-space: nowrap;
                font-size: 14px;
            }}

            th, td {{ padding: 12px 16px; }}

            .kpi-box, .info-box, .quote-box {{
                padding: 16px;
                margin: 16px 0;
                font-size: 15px;
            }}

            .toc {{ padding: 20px; }}
            .toc h1 {{ font-size: 24px; }}
            .toc-item {{ padding: 12px 0; }}

            ul, ol {{ margin: 16px 0 16px 20px; }}
            li {{ font-size: 16px; margin-bottom: 8px; }}

            .disclaimer {{ font-size: 14px; padding: 16px; margin: 20px; }}
            .sources {{ margin: 20px; padding: 16px; }}
            .source-item {{ font-size: 14px; padding: 8px 0; }}
        }}

        /* Tablet */
        @media screen and (min-width: 769px) and (max-width: 1024px) {{
            .infographic-section {{
                grid-template-columns: repeat(6, 1fr);
            }}
            .infographic-card.col-12 {{ grid-column: span 6; }}
            .infographic-card.col-6 {{ grid-column: span 3; }}
            .infographic-card.col-4 {{ grid-column: span 3; }}
        }}

        /* ===========================================
           ANTI-CRASH SAFETY OVERRIDES (LAST RESORT)
           =========================================== */
        * {{
            break-inside: auto; /* Let content break naturally */
        }}

        .cover, .editorial-spread, .chapter-cover {{
            height: auto !important;
            min-height: 90vh !important;
            max-height: 295mm !important; /* Safety cap */
            overflow: hidden !important;
            display: block !important; /* Kill Flexbox causing loops */
            page-break-after: always !important;
            break-after: page !important;
        }}

        /* Fix Cover Layout after removing Flexbox */
        .cover-content {{
            padding-top: 60mm !important;
        }}
        
        .chapter-cover {{
            padding-top: 80mm !important;
        }}

        /* Safety Visibility */
        body, .pagedjs_pages {{
            visibility: visible !important;
            opacity: 1 !important;
        }}

        img, table, .bento-grid, .kpi-box {{
            break-inside: avoid !important;
        }}

        {get_stw_matrix_css()}
    </style>
</head>
<body>

    <!-- =========================================
         HERO COVER - TACTICAL POSTER STYLE
         ========================================= -->
    <div class="cover">
        <div class="cover-bg"></div>
        <div class="cover-datastrip">
            <div class="datastrip-text">CONFIDENTIAL DOCUMENT</div>
            <div class="datastrip-text">STRATEGY ENGINE v5.4</div>
            <div class="datastrip-text">{generation_date} // {current_year}</div>
        </div>

        <div class="cover-inner">
            <div class="cover-brand">ROOTING FUTURE</div>
            <div class="cover-club">{club_name}</div>
            <div class="cover-title">PIANO STRATEGICO<br>TRIENNALE</div>

            <div class="cover-footer">
                <div><strong>PERIOD</strong><br>{current_year} — {current_year + 3}</div>
                <div><strong>STATUS</strong><br>APPROVED DRAFT</div>
                <div><strong>ID</strong><br>{category if category else 'RF-STR-001'}</div>
            </div>
        </div>
    </div>

    <!-- =========================================
         EDITORIAL SPREAD - INDEX & VISION
         ========================================= -->
    <div class="editorial-spread">
        <div class="editorial-inner">
            <!-- Colonna Sinistra: Indice -->
            <div class="editorial-toc">
                <div class="editorial-toc-header">Indice</div>
                <div class="editorial-toc-item"><span class="editorial-toc-number">01</span><span class="editorial-toc-title">Executive Summary</span></div>
                <div class="editorial-toc-item"><span class="editorial-toc-number">02</span><span class="editorial-toc-title">Area Tecnico-Sportiva</span></div>
                <div class="editorial-toc-item"><span class="editorial-toc-number">03</span><span class="editorial-toc-title">Settore Giovanile</span></div>
                <div class="editorial-toc-item"><span class="editorial-toc-number">04</span><span class="editorial-toc-title">Infrastrutture</span></div>
                <div class="editorial-toc-item"><span class="editorial-toc-number">05</span><span class="editorial-toc-title">Marketing</span></div>
                <div class="editorial-toc-item"><span class="editorial-toc-number">06</span><span class="editorial-toc-title">Sostenibilità</span></div>
                <div class="editorial-toc-item"><span class="editorial-toc-number">07</span><span class="editorial-toc-title">Governance</span></div>
                <div class="editorial-toc-item"><span class="editorial-toc-number">08</span><span class="editorial-toc-title">Piano Finanziario</span></div>
            </div>

            <!-- Colonna Destra: Executive Summary -->
            <div class="editorial-summary">
                <div class="editorial-summary-header">
                    <div class="editorial-summary-label">Capitolo 01</div>
                    <div class="editorial-summary-title">Visione<br>Strategica</div>
                </div>
                <div class="editorial-summary-content">
                    <span class="drop-cap">I</span>l presente piano delinea la strategia triennale per il consolidamento e la crescita sostenibile del club.
                    <div class="editorial-kpi-grid">
                        <div class="editorial-kpi-box primary"><div class="editorial-kpi-value">3</div><div class="editorial-kpi-label">Anni</div></div>
                        <div class="editorial-kpi-box secondary"><div class="editorial-kpi-value">8</div><div class="editorial-kpi-label">Aree</div></div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- =========================================
         LEGACY TOC (nascosto, per compatibilità)
         ========================================= -->
    <div class="chapter toc" style="display: none;">
        <h1>Indice</h1>
        <div class="toc-item">
            <span class="toc-number">1.</span>
            <span class="toc-title">Executive Summary</span>
        </div>
        <div class="toc-item">
            <span class="toc-number">2.</span>
            <span class="toc-title">Area Tecnico-Sportiva</span>
        </div>
        <div class="toc-item">
            <span class="toc-number">3.</span>
            <span class="toc-title">Sviluppo Settore Giovanile</span>
        </div>
        <div class="toc-item">
            <span class="toc-number">4.</span>
            <span class="toc-title">Infrastrutture</span>
        </div>
        <div class="toc-item">
            <span class="toc-number">5.</span>
            <span class="toc-title">Marketing e Commerciale</span>
        </div>
        <div class="toc-item">
            <span class="toc-number">6.</span>
            <span class="toc-title">Sostenibilità Sociale</span>
        </div>
        <div class="toc-item">
            <span class="toc-number">7.</span>
            <span class="toc-title">Governance e Organizzazione</span>
        </div>
        <div class="toc-item">
            <span class="toc-number">8.</span>
            <span class="toc-title">Piano Economico-Finanziario</span>
        </div>
        <div class="toc-item">
            <span class="toc-number"></span>
            <span class="toc-title">Appendice: Fonti e Riferimenti</span>
        </div>
    </div>

    <!-- =========================================
         MATRICE STW - FRAMEWORK METODOLOGICO
         ========================================= -->
    {generate_stw_matrix_html(primary_color)}

    <!-- =========================================
         CONTENUTO SEZIONI
         ========================================= -->
{sections_html}

    <!-- =========================================
         FONTI
         ========================================= -->
{sources_html}

    <!-- =========================================
         DISCLAIMER
         ========================================= -->
    <div class="disclaimer">
        <strong>Nota Metodologica:</strong> I dati contenuti nel presente documento sono stati raccolti
        e verificati alla data di generazione. Per informazioni aggiornate, si consiglia di verificare
        direttamente presso le fonti citate. I dati indicati come "stima interna" o "da verificare"
        richiedono validazione con fonti primarie.
    </div>

</body>
</html>'''

        return html

    def _generate_sections(self, plan_data: Dict, primary_color: str) -> str:
        """Genera HTML per tutte le sezioni del piano"""
        sections_config = [
            ('executive_summary', 'Executive Summary', '1'),
            ('technical_sporting', 'Area Tecnico-Sportiva', '2'),
            ('youth_development', 'Sviluppo Settore Giovanile', '3'),
            ('infrastructure', 'Infrastrutture', '4'),
            ('marketing_commercial', 'Marketing e Commerciale', '5'),
            ('social_sustainability', 'Sostenibilità Sociale', '6'),
            ('governance', 'Governance e Organizzazione', '7'),
            ('financial', 'Piano Economico-Finanziario', '8'),
        ]

        html_parts = []
        for key, title, number in sections_config:
            content = plan_data.get(key, '')
            if content:
                section_html = self._generate_section(title, content, number)
                html_parts.append(section_html)

        return '\n'.join(html_parts)

    def _generate_section(self, title: str, content: str, number: str) -> str:
        """Genera HTML per una singola sezione con stile Magazine Premium"""
        # Converti markdown in HTML
        content_html = self._markdown_to_infographic_html(content)

        # Descrizioni per ogni capitolo (per la copertina)
        chapter_subtitles = {
            '1': 'Visione strategica, obiettivi prioritari e roadmap triennale',
            '2': 'Staff tecnico, metodologia e competitività sportiva',
            '3': 'Academy, scouting e valorizzazione dei talenti',
            '4': 'Impianti sportivi, sede operativa e risorse umane',
            '5': 'Brand identity, comunicazione e sviluppo commerciale',
            '6': 'Responsabilità sociale, inclusione e sostenibilità ambientale',
            '7': 'Struttura organizzativa, compliance e digitalizzazione',
            '8': 'Analisi finanziaria, budget e piano investimenti',
        }

        subtitle = chapter_subtitles.get(number, '')

        return f'''
    <!-- COPERTINA CAPITOLO {number} -->
    <div class="chapter chapter-cover">
        <div class="chapter-inner">
            <div class="chapter-number-big">{number}</div>
            <div class="chapter-title-big">{title}</div>
            <div class="chapter-subtitle">{subtitle}</div>
        </div>
    </div>

    <!-- CONTENUTO CAPITOLO {number} -->
    <div class="chapter">
        <div class="chapter-content">
            {content_html}
        </div>
    </div>
'''

    def _markdown_to_infographic_html(self, text: str) -> str:
        """
        Converte markdown in HTML stile magazine professionale.
        Layout a 2 colonne con headers, liste, tabelle - NO card Bento Grid.
        Leggibile, stampabile, responsive.
        """
        if not text:
            return ''

        lines = text.split('\n')
        html_parts = []
        in_list = False
        in_ordered_list = False
        in_table = False
        table_rows = []

        i = 0
        while i < len(lines):
            line = lines[i].strip()

            # Riga vuota - chiudi liste/tabelle aperte
            if not line:
                if in_list:
                    html_parts.append('</ul>')
                    in_list = False
                if in_ordered_list:
                    html_parts.append('</ol>')
                    in_ordered_list = False
                if in_table:
                    html_parts.append(self._create_table(table_rows))
                    table_rows = []
                    in_table = False
                i += 1
                continue

            # Tabelle markdown
            if '|' in line and line.count('|') >= 2:
                if in_list:
                    html_parts.append('</ul>')
                    in_list = False
                if in_ordered_list:
                    html_parts.append('</ol>')
                    in_ordered_list = False
                in_table = True
                table_rows.append(line)
                i += 1
                continue

            # Se eravamo in una tabella ma questa riga non lo è, chiudi tabella
            if in_table:
                html_parts.append(self._create_table(table_rows))
                table_rows = []
                in_table = False

            # H1 - Titolo principale
            if line.startswith('# '):
                if in_list:
                    html_parts.append('</ul>')
                    in_list = False
                if in_ordered_list:
                    html_parts.append('</ol>')
                    in_ordered_list = False
                html_parts.append(f'<h1>{self._format_inline(line[2:])}</h1>')
                i += 1
                continue

            # H2 - Sezione principale (full width)
            if line.startswith('## '):
                if in_list:
                    html_parts.append('</ul>')
                    in_list = False
                if in_ordered_list:
                    html_parts.append('</ol>')
                    in_ordered_list = False
                html_parts.append(f'<h2>{self._format_inline(line[3:])}</h2>')
                i += 1
                continue

            # H3 - Sottosezione (full width)
            if line.startswith('### '):
                if in_list:
                    html_parts.append('</ul>')
                    in_list = False
                if in_ordered_list:
                    html_parts.append('</ol>')
                    in_ordered_list = False
                html_parts.append(f'<h3>{self._format_inline(line[4:])}</h3>')
                i += 1
                continue

            # H4 - Sottosezione minore
            if line.startswith('#### '):
                if in_list:
                    html_parts.append('</ul>')
                    in_list = False
                if in_ordered_list:
                    html_parts.append('</ol>')
                    in_ordered_list = False
                html_parts.append(f'<h4>{self._format_inline(line[5:])}</h4>')
                i += 1
                continue

            # Liste non ordinate
            if line.startswith('- ') or line.startswith('* '):
                if in_ordered_list:
                    html_parts.append('</ol>')
                    in_ordered_list = False
                if not in_list:
                    html_parts.append('<ul>')
                    in_list = True
                html_parts.append(f'<li>{self._format_inline(line[2:])}</li>')
                i += 1
                continue

            # Liste ordinate (1. 2. 3. etc)
            import re as regex
            ordered_match = regex.match(r'^(\d+)\.\s+(.+)$', line)
            if ordered_match:
                if in_list:
                    html_parts.append('</ul>')
                    in_list = False
                if not in_ordered_list:
                    html_parts.append('<ol>')
                    in_ordered_list = True
                html_parts.append(f'<li>{self._format_inline(ordered_match.group(2))}</li>')
                i += 1
                continue

            # Box KPI/Target/Raccomandazione
            if any(kw in line for kw in ['KPI:', 'Target:', 'Obiettivo:', 'RACCOMANDAZIONE', 'Raccomandazione']):
                if in_list:
                    html_parts.append('</ul>')
                    in_list = False
                if in_ordered_list:
                    html_parts.append('</ol>')
                    in_ordered_list = False
                html_parts.append(f'<div class="kpi-box"><p>{self._format_inline(line)}</p></div>')
                i += 1
                continue

            # Blockquote
            if line.startswith('> '):
                if in_list:
                    html_parts.append('</ul>')
                    in_list = False
                if in_ordered_list:
                    html_parts.append('</ol>')
                    in_ordered_list = False
                html_parts.append(f'<div class="quote-box">{self._format_inline(line[2:])}</div>')
                i += 1
                continue

            # Paragrafo normale
            if in_list:
                html_parts.append('</ul>')
                in_list = False
            if in_ordered_list:
                html_parts.append('</ol>')
                in_ordered_list = False
            html_parts.append(f'<p>{self._format_inline(line)}</p>')
            i += 1

        # Chiudi eventuali tag aperti
        if in_list:
            html_parts.append('</ul>')
        if in_ordered_list:
            html_parts.append('</ol>')
        if in_table:
            html_parts.append(self._create_table(table_rows))

        return '\n'.join(html_parts)

    def _create_table(self, rows: List[str]) -> str:
        """Crea tabella HTML da righe markdown"""
        if not rows:
            return ''

        # Filtra righe separatore
        def is_separator(row):
            cleaned = row.replace('|', '').strip()
            return all(c in '-: ' for c in cleaned) and len(cleaned) > 0

        data_rows = [r for r in rows if not is_separator(r)]
        if not data_rows:
            return ''

        html = ['<table>']

        for i, row in enumerate(data_rows):
            cells = [c.strip() for c in row.split('|') if c.strip()]
            if not cells:
                continue

            if i == 0:
                html.append('<thead><tr>')
                for cell in cells:
                    html.append(f'<th>{self._format_inline(cell)}</th>')
                html.append('</tr></thead><tbody>')
            else:
                html.append('<tr>')
                for cell in cells:
                    html.append(f'<td>{self._format_inline(cell)}</td>')
                html.append('</tr>')

        html.append('</tbody></table>')
        return '\n'.join(html)

    def _format_inline(self, text: str) -> str:
        """Formatta bold, italic, etc."""
        # Bold
        text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
        # Italic
        text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)
        return text

    def _generate_sources(self, sources: List[Dict]) -> str:
        """Genera HTML per le fonti"""
        if not sources:
            return ''

        html = ['<div class="chapter">', '<div class="sources">', '<h2>Fonti e Riferimenti</h2>']

        for source in sources[:30]:
            name = source.get('name', 'N/A')
            url = source.get('url', '')
            html.append(f'<div class="source-item"><strong>{name}</strong>')
            if url:
                html.append(f' - <span class="text-muted">{url[:60]}{"..." if len(url) > 60 else ""}</span>')
            html.append('</div>')

        html.append('</div></div>')
        return '\n'.join(html)

    def _lighten_color(self, hex_color: str, factor: float = 0.9) -> str:
        """Schiarisce un colore"""
        hex_color = hex_color.lstrip('#')
        r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        r = min(255, int(r + (255 - r) * factor))
        g = min(255, int(g + (255 - g) * factor))
        b = min(255, int(b + (255 - b) * factor))
        return f'{r:02x}{g:02x}{b:02x}'

    def _darken_color(self, hex_color: str, factor: float = 0.2) -> str:
        """Scurisce un colore"""
        hex_color = hex_color.lstrip('#')
        r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        r = int(r * (1 - factor))
        g = int(g * (1 - factor))
        b = int(b * (1 - factor))
        return f'#{r:02x}{g:02x}{b:02x}'

    def _get_contrast_color(self, hex_color: str) -> str:
        """Restituisce bianco o nero per contrasto"""
        hex_color = hex_color.lstrip('#')
        r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
        return '#ffffff' if luminance < 0.5 else '#1a1a1a'


# Singleton per uso globale
paged_exporter = PagedHtmlExporter()


def create_paged_html(plan_data: Dict, club_name: str, sources: List = None, metadata: Dict = None) -> Path:
    """Funzione helper per creare documento Paged.js"""
    return paged_exporter.export(plan_data, club_name, sources, metadata)
