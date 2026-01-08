"""
Rooting Future Strategy Engine - Server-Side PDF Export
Engine: WeasyPrint (Python Native)
Design: Tactical Sports Report v3.0 (Anti-Crash Server Edition)
"""

import re
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import weasyprint

from config import OUTPUT_DIR
from stw_matrix import generate_stw_matrix_html, get_stw_matrix_css

logger = logging.getLogger(__name__)

class PdfServerExporter:
    """
    Esporta piani strategici direttamente in PDF utilizzando WeasyPrint.
    Elimina la dipendenza da Paged.js e i problemi di rendering del browser.
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
        Genera il file PDF finale.
        """
        # Estrazione metadati e colori
        primary_color = metadata.get('primary_color', '#1a365d') if metadata else '#1a365d'
        secondary_color = metadata.get('secondary_color', '#000000') if metadata else '#000000'
        category = metadata.get('category', 'STRATEGIC PLAN') if metadata else 'STRATEGIC PLAN'

        # Genera l'HTML con il CSS ottimizzato per WeasyPrint
        html_content = self._generate_html(
            plan_data=plan_data,
            club_name=club_name,
            sources=sources or [],
            primary_color=primary_color,
            secondary_color=secondary_color,
            category=category
        )

        # Output path
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = re.sub(r'[^\w\s-]', '', club_name).strip().replace(' ', '_')
        filename = f"{safe_name}_PianoStrategico_{timestamp}.pdf"
        filepath = self._output_dir / filename

        # Generazione PDF via WeasyPrint
        logger.info(f"Inizio generazione PDF per {club_name} via WeasyPrint...")
        try:
            weasyprint.HTML(string=html_content).write_pdf(filepath)
            logger.info(f"PDF generato con successo: {filepath}")
        except Exception as e:
            logger.error(f"Errore WeasyPrint: {e}")
            raise

        return filepath

    def _generate_html(self, plan_data, club_name, sources, primary_color, secondary_color, category) -> str:
        light_color = self._lighten_color(primary_color, 0.95)
        contrast_color = self._get_contrast_color(primary_color)
        current_year = datetime.now().year
        generation_date = datetime.now().strftime("%d/%m/%Y")

        # Genera contenuto sezioni
        sections_html = self._generate_sections_html(plan_data, primary_color)

        return f'''
<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <title>Piano Strategico - {club_name}</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600&family=Oswald:wght@500;700&display=swap');

        :root {{
            --primary-color: {primary_color};
            --secondary-color: {secondary_color};
            --light-color: #{light_color};
            --contrast-color: {contrast_color};
            --text-color: #111111;
            --border-color: #eeeeee;
        }}

        /* ===========================================
           CONFIGURAZIONE PAGINA (Paged Media)
           Magazine Style con Running Header
           =========================================== */
        @page {{
            size: A4;
            margin: 22mm 20mm 18mm 20mm;

            /* RUNNING HEADER - Nome club in alto */
            @top-left {{
                content: "{club_name.upper()}";
                font-family: 'Oswald', sans-serif;
                font-size: 9pt;
                font-weight: 700;
                letter-spacing: 3px;
                color: {primary_color};
                border-bottom: 0.5pt solid #ddd;
                padding-bottom: 3mm;
            }}
            @top-right {{
                content: "PIANO STRATEGICO {current_year}—{current_year+3}";
                font-family: 'Oswald', sans-serif;
                font-size: 8pt;
                letter-spacing: 2px;
                color: #666;
                border-bottom: 0.5pt solid #ddd;
                padding-bottom: 3mm;
            }}

            /* FOOTER */
            @bottom-left {{
                content: "{category.upper()} // DOCUMENTO RISERVATO";
                font-family: 'Inter', sans-serif;
                font-size: 7pt;
                color: #999;
                border-top: 0.3pt solid #eee;
                padding-top: 4mm;
            }}
            @bottom-right {{
                content: counter(page);
                font-family: 'Oswald', sans-serif;
                font-size: 10pt;
                font-weight: 700;
                color: {primary_color};
                border-top: 0.3pt solid #eee;
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
            line-height: 1.75; /* Aumentato per respirare */
            color: var(--text-color);
            background: #ffffff;
            margin: 0;
            padding: 0;
            overflow-x: hidden; /* Clip pseudo-element full-bleed backgrounds */
        }}

        /* ===========================================
           TIPOGRAFIA TATTICA
           =========================================== */
        h1, h2, h3, h4, .cover-club, .chapter-number {{
            font-family: 'Oswald', sans-serif;
            text-transform: uppercase;
            letter-spacing: 1px;
            line-height: 1.1;
        }}

        h1 {{
            font-size: 32pt;
            font-weight: 700;
            color: var(--primary-color);
            border-bottom: 4pt solid var(--primary-color);
            padding-bottom: 3mm;
            margin: 15mm 0 10mm 0;
            page-break-before: always;
        }}

        h2 {{
            position: relative;
            z-index: 1;
            font-size: 16pt;
            font-weight: 700;
            color: var(--contrast-color);
            padding: 5mm 0;
            margin-top: 12mm;
            margin-bottom: 8mm;
            page-break-after: avoid;
            font-family: 'Oswald', sans-serif;
            text-transform: uppercase;
            letter-spacing: 2px;
            line-height: 1.2;
        }}

        h2::before {{
            content: "";
            position: absolute;
            top: 0;
            bottom: 0;
            left: -500mm;
            right: -500mm;
            background-color: var(--primary-color);
            z-index: -1;
        }}

        h3 {{
            font-size: 13pt;
            font-weight: 600;
            color: var(--text-color);
            margin: 10mm 0 5mm 0;
            padding-bottom: 2mm;
            border-bottom: 2pt solid var(--primary-color);
        }}

        h4 {{
            font-size: 11pt;
            font-weight: 600;
            color: var(--primary-color);
            margin: 8mm 0 4mm 0;
        }}

        p {{
            margin-bottom: 5mm; /* Aumentato per respirare */
            text-align: justify;
            line-height: 1.8;
        }}

        /* ===========================================
           COPERTINA POSTER (Tactical Edition)
           =========================================== */
        .cover {{
            width: 210mm;
            height: 297mm;
            background-color: var(--primary-color);
            color: var(--contrast-color);
            position: relative;
            overflow: hidden;
            page-break-after: always;
        }}

        .cover-bg {{
            position: absolute;
            top: 0; left: 0; width: 100%; height: 100%;
            background-image: repeating-linear-gradient(
                135deg,
                rgba(0,0,0,0.05) 0px,
                rgba(0,0,0,0.05) 1px,
                transparent 1px,
                transparent 15px
            );
        }}

        .cover-datastrip {{
            position: absolute;
            top: 0; right: 0; width: 15mm; height: 100%;
            background: #000;
            color: rgba(255,255,255,0.5);
            font-family: monospace;
            font-size: 7pt;
            text-align: center;
            padding-top: 20mm;
            writing-mode: vertical-rl;
            letter-spacing: 2px;
        }}

        .cover-content {{
            position: absolute;
            top: 100mm; left: 25mm; right: 40mm;
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
            font-size: 72pt;
            font-weight: 700;
            line-height: 0.9;
            margin-bottom: 8mm;
            text-shadow: 4pt 4pt 0px rgba(0,0,0,0.15);
        }}

        .cover-title {{
            font-size: 24pt;
            font-weight: 300;
            opacity: 0.9;
            border-left: 3pt solid var(--contrast-color);
            padding-left: 6mm;
        }}

        /* ===========================================
           LAYOUT A COLONNE (Magazine Style)
           =========================================== */
        .section-container {{
            margin-bottom: 10mm;
        }}

        .section-body {{
            column-count: 2;
            column-gap: 10mm;
            text-align: justify;
            overflow: hidden; /* Clip pseudo-element full-bleed backgrounds */
        }}

        /* ===========================================
           ELEMENTI FULL-WIDTH (column-span: all)
           Questi elementi attraversano entrambe le colonne
           =========================================== */
        h1, h2, h3, h4 {{
            column-span: all;
        }}

        table, figure, img, svg, .chart-container, .kpi-box, .quote-box, .insight-box, .highlight-box {{
            column-span: all;
            break-inside: avoid;
            page-break-inside: avoid;
        }}

        /* Evita interruzioni brutte dentro elementi importanti */
        li, tr, blockquote {{
            break-inside: avoid;
            page-break-inside: avoid;
        }}

        /* Grafici e immagini: MAI tagliare */
        img, svg, canvas, .chart, .plotly-graph-div {{
            max-width: 100%;
            height: auto;
            break-inside: avoid;
            page-break-inside: avoid;
            display: block;
            margin: 6mm auto;
        }}

        /* Container grafici */
        .chart-container, .figure-container {{
            width: 100%;
            break-inside: avoid;
            page-break-inside: avoid;
            margin: 8mm 0;
            padding: 5mm;
            background: #fafafa;
            border: 1px solid #eee;
        }}

        /* ===========================================
           LISTE TATTICHE
           =========================================== */
        ul {{ list-style: none; padding-left: 0; margin: 5mm 0; }}
        ul li {{
            padding: 3mm 0;
            border-bottom: 1px solid #eee;
            position: relative;
            padding-left: 6mm;
        }}
        ul li::before {{
            content: "›";
            position: absolute;
            left: 0;
            color: var(--primary-color);
            font-family: 'Oswald';
            font-weight: 700;
            font-size: 14pt;
            line-height: 1;
        }}

        ol {{
            padding-left: 0;
            list-style: none;
            counter-reset: tactical-counter;
        }}
        ol li {{
            counter-increment: tactical-counter;
            padding: 3mm 0 3mm 12mm;
            position: relative;
            border-bottom: 1px solid #eee;
        }}
        ol li::before {{
            content: counter(tactical-counter, decimal-leading-zero);
            position: absolute;
            left: 0;
            background: var(--primary-color);
            color: #fff;
            font-family: 'Oswald';
            font-size: 9pt;
            padding: 1mm 2mm;
            min-width: 8mm;
            text-align: center;
        }}

        /* ===========================================
           TABELLE E KPI
           =========================================== */
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 8mm 0;
            page-break-inside: avoid;
        }}
        th {{
            background: var(--primary-color);
            color: var(--contrast-color);
            text-align: left;
            padding: 4mm;
            font-family: 'Oswald';
            font-size: 10pt;
        }}
        td {{
            padding: 4mm;
            border-bottom: 1px dotted #ccc;
            font-size: 9pt;
        }}

        /* ===========================================
           BOX INFORMATIVI - SKIMMABILITY
           =========================================== */
        .kpi-box {{
            background: linear-gradient(135deg, var(--light-color) 0%, #ffffff 100%);
            border-left: 5pt solid var(--primary-color);
            padding: 6mm 8mm;
            margin: 8mm 0;
            break-inside: avoid;
            page-break-inside: avoid;
        }}

        .kpi-box strong {{
            color: var(--primary-color);
            font-family: 'Oswald', sans-serif;
            font-size: 11pt;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}

        /* INSIGHT BOX - Per concetti chiave */
        .insight-box {{
            background: #F9F9F9;
            border-left: 4pt solid var(--primary-color);
            padding: 5mm 6mm;
            margin: 8mm 0;
            break-inside: avoid;
            page-break-inside: avoid;
            font-size: 9.5pt;
            line-height: 1.6;
        }}

        .insight-box::before {{
            content: "KEY INSIGHT";
            display: block;
            font-family: 'Oswald', sans-serif;
            font-size: 8pt;
            font-weight: 700;
            color: var(--primary-color);
            letter-spacing: 2px;
            margin-bottom: 3mm;
            text-transform: uppercase;
        }}

        /* HIGHLIGHT BOX - Per dati numerici importanti */
        .highlight-box {{
            background: var(--primary-color);
            color: var(--contrast-color);
            padding: 6mm 8mm;
            margin: 8mm 0;
            break-inside: avoid;
            text-align: center;
        }}

        .highlight-box .big-number {{
            font-family: 'Oswald', sans-serif;
            font-size: 36pt;
            font-weight: 700;
            line-height: 1;
            margin-bottom: 2mm;
        }}

        .highlight-box .label {{
            font-size: 9pt;
            text-transform: uppercase;
            letter-spacing: 2px;
            opacity: 0.9;
        }}

        .quote-box {{
            background: #f5f5f5;
            border-left: 3pt solid var(--secondary-color);
            padding: 5mm 8mm;
            margin: 8mm 0;
            font-style: italic;
            font-size: 10pt;
            line-height: 1.7;
            break-inside: avoid;
        }}

        .quote-box::before {{
            content: open-quote;
            font-size: 24pt;
            color: var(--primary-color);
            font-family: Georgia, serif;
            line-height: 0;
            vertical-align: -8pt;
            margin-right: 2mm;
        }}

        {get_stw_matrix_css()}
    </style>
</head>
<body>
    <div class="cover">
        <div class="cover-bg"></div>
        <div class="cover-datastrip">
            ROOTING FUTURE STRATEGY ENGINE v5.4 // {generation_date} // {category.upper()} // CONFIDENTIAL
        </div>
        <div class="cover-content">
            <div class="cover-brand">STRATEGIC DOSSIER</div>
            <div class="cover-club">{club_name}</div>
            <div class="cover-title">PIANO STRATEGICO<br>SVILUPPO {current_year}—{current_year+3}</div>
            
            <div style="margin-top: 20mm; font-family: 'Oswald'; font-size: 10pt; letter-spacing: 2px; color: rgba(255,255,255,0.7);">
                APPROVED BY ROOTING FUTURE BOARD
            </div>
        </div>
    </div>

    {sections_html}

    {self._generate_sources_html(sources)}
</body>
</html>
'''

    def _generate_sections_html(self, plan_data, primary_color) -> str:
        html = []
        section_titles = {
            'executive_summary': '01. Executive Summary',
            'technical_sporting': '02. Area Tecnico-Sportiva',
            'youth_sector': '03. Settore Giovanile',
            'infrastructure': '04. Infrastrutture & Risorse',
            'marketing_commercial': '05. Marketing & Commerciale',
            'social_sustainability': '06. Sostenibilità & Sociale',
            'governance': '07. Governance & Organizzazione',
            'financial': '08. Piano Finanziario',
        }

        for key, content in plan_data.items():
            if not content: continue
            title = section_titles.get(key, key.replace('_', ' ').title())
            html.append(f'<div class="section-container">')
            html.append(f'<h1>{title}</h1>')
            html.append(f'<div class="section-body">{self._markdown_to_html(content)}</div>')
            html.append(f'</div>')
        return "".join(html)

    def _markdown_to_html(self, text: str) -> str:
        if not text: return ""
        lines = text.split('\n')
        html_parts = []
        in_list = False
        in_ordered_list = False
        in_table = False
        table_rows = []

        for line in lines:
            line = line.strip()
            if not line:
                if in_list: html_parts.append('</ul>'); in_list = False
                if in_ordered_list: html_parts.append('</ol>'); in_ordered_list = False
                if in_table: html_parts.append(self._create_table(table_rows)); table_rows = []; in_table = False
                continue

            if '|' in line and line.count('|') >= 2:
                in_table = True
                table_rows.append(line)
                continue
            
            if in_table:
                html_parts.append(self._create_table(table_rows))
                table_rows = []; in_table = False

            if line.startswith('### '): html_parts.append(f'<h3>{self._format_inline(line[4:])}</h3>')
            elif line.startswith('## '): html_parts.append(f'<h2>{self._format_inline(line[3:])}</h2>')
            elif line.startswith('# '): html_parts.append(f'<h1>{self._format_inline(line[2:])}</h1>')
            elif line.startswith('- ') or line.startswith('* '):
                if not in_list: html_parts.append('<ul>'); in_list = True
                html_parts.append(f'<li>{self._format_inline(line[2:])}</li>')
            elif re.match(r'^\d+\. ', line):
                if not in_ordered_list: html_parts.append('<ol>'); in_ordered_list = True
                html_parts.append(f'<li>{self._format_inline(re.sub(r'^\d+\. ', "", line))}</li>')
            elif any(kw in line for kw in ['KPI:', 'Target:', 'Obiettivo:', 'RACCOMANDAZIONE', 'Raccomandazione']):
                html_parts.append(f'<div class="kpi-box">{self._format_inline(line)}</div>')
            elif any(kw in line.lower() for kw in ['importante:', 'nota:', 'key insight:', 'punto chiave:']):
                html_parts.append(f'<div class="insight-box">{self._format_inline(line)}</div>')
            elif line.startswith('> '):
                html_parts.append(f'<div class="quote-box">{self._format_inline(line[2:])}</div>')
            else:
                html_parts.append(f'<p>{self._format_inline(line)}</p>')

        if in_list: html_parts.append('</ul>')
        if in_ordered_list: html_parts.append('</ol>')
        if in_table: html_parts.append(self._create_table(table_rows))

        return "\n".join(html_parts)

    def _create_table(self, rows: List[str]) -> str:
        if not rows: return ''
        data_rows = [r for r in rows if not all(c in '|- : ' for c in r.strip())]
        if not data_rows: return ''
        html = ['<table>']
        for i, row in enumerate(data_rows):
            cells = [c.strip() for c in row.split('|') if c.strip()]
            tag = 'th' if i == 0 else 'td'
            html.append('<tr>' + "".join([f'<{tag}>{self._format_inline(c)}</{tag}>' for c in cells]) + '</tr>')
        html.append('</table>')
        return "".join(html)

    def _format_inline(self, text: str) -> str:
        text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
        text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)
        return text

    def _generate_sources_html(self, sources) -> str:
        if not sources: return ""
        html = ['<h1>Fonti e Metodologia</h1>', '<div class="section-body"><ul>']
        for s in sources[:20]:
            name = s.get('name', 'Fonte esterna')
            url = s.get('url', '')
            html.append(f'<li><strong>{name}</strong><br><small>{url}</small></li>')
        html.append('</ul></div>')
        return "".join(html)

    def _lighten_color(self, hex_color: str, factor: float) -> str:
        hex_color = hex_color.lstrip('#')
        if len(hex_color) != 6: return hex_color
        rgb = [int(hex_color[i:i+2], 16) for i in (0, 2, 4)]
        new_rgb = [min(255, int(c + (255 - c) * factor)) for c in rgb]
        return '{:02x}{:02x}{:02x}'.format(*new_rgb)

    def _get_contrast_color(self, hex_color: str) -> str:
        hex_color = hex_color.lstrip('#')
        if len(hex_color) != 6: return '#FFFFFF'
        rgb = [int(hex_color[i:i+2], 16) for i in (0, 2, 4)]
        brightness = (rgb[0] * 299 + rgb[1] * 587 + rgb[2] * 114) / 1000
        return '#000000' if brightness > 128 else '#FFFFFF'