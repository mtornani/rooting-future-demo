"""
Rooting Future Strategy Engine
Export One-Pager Infografica

Genera un documento A4 singola pagina (o doppia) con:
- Dashboard visuale immediata
- KPI chiave
- Matrice STW semplificata
- Top 5 priorità

Perfetto per condivisione rapida su WhatsApp, email, presentazioni.
"""

import re
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

from config import OUTPUT_DIR
from stw_matrix import STW_FRAMEWORK, STWCategory, get_category_color, get_category_icon
from stw_analyzer import calculate_stw_progress

logger = logging.getLogger(__name__)


class OnePagerExporter:
    """
    Genera infografica A4 singola pagina per condivisione rapida.
    Design: Dashboard-style con KPI, progress bars, top priorities.
    """

    def __init__(self):
        OUTPUT_DIR.mkdir(exist_ok=True)
        self._output_dir = OUTPUT_DIR

    def export(
        self,
        plan_data: Dict,
        club_name: str,
        metadata: Dict = None,
        stw_progress: Dict[str, int] = None
    ) -> Path:
        """
        Genera One-Pager infografica.

        Args:
            plan_data: Dict con sezioni del piano (per estrarre highlights)
            club_name: Nome del club
            metadata: Metadati (colori, categoria, credibility_score, etc.)
            stw_progress: Dict con progressi STW per categoria {categoria: percentuale}

        Returns:
            Path del file HTML generato
        """
        metadata = metadata or {}
        primary_color = metadata.get('primary_color', '#1a365d')
        secondary_color = metadata.get('secondary_color', '#c9a227')
        category = metadata.get('category', 'Serie D')
        credibility_score = metadata.get('credibility_score', 72)
        sources_count = metadata.get('sources_count', 15)
        total_questionnaires = metadata.get('total_questionnaires', 0)

        # Estrai highlights dal piano
        highlights = self._extract_highlights(plan_data)

        # Calcola progress STW dinamicamente se non fornito
        if stw_progress is None:
            logger.info("Calculating STW progress from plan content...")
            stw_progress = calculate_stw_progress(plan_data)
            logger.info(f"STW Progress calculated: {stw_progress}")

        # Genera HTML
        html = self._generate_html(
            club_name=club_name,
            primary_color=primary_color,
            secondary_color=secondary_color,
            category=category,
            credibility_score=credibility_score,
            sources_count=sources_count,
            stw_progress=stw_progress,
            highlights=highlights,
            total_questionnaires=total_questionnaires,
            metadata=metadata
        )

        # Salva
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = re.sub(r'[^\w\s-]', '', club_name).strip().replace(' ', '_')
        filename = f"{safe_name}_OnePager_{timestamp}.html"
        filepath = self._output_dir / filename

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html)

        logger.info(f"One-Pager exported: {filepath}")
        return filepath

    def _extract_highlights(self, plan_data: Dict) -> Dict[str, Any]:
        """Estrae highlights chiave dal piano per il one-pager"""
        highlights = {
            'vision': '',
            'top_priorities': [],
            'quick_wins': [],
            'key_kpis': [],
            'risks': []
        }

        # Estrai dall'executive summary
        exec_summary = plan_data.get('executive_summary', '')
        if exec_summary:
            # Cerca visione
            vision_match = re.search(r'(?:visione|vision)[:\s]*([^.]+\.)', exec_summary, re.IGNORECASE)
            if vision_match:
                highlights['vision'] = vision_match.group(1).strip()[:200]

            # Cerca priorità (liste numerate)
            priorities = re.findall(r'(?:^|\n)\s*\d+\.\s*\*?\*?([^*\n]+)', exec_summary)
            highlights['top_priorities'] = [p.strip() for p in priorities[:5]]

        # Estrai KPI dal financial
        financial = plan_data.get('financial', '')
        if financial:
            # Cerca numeri con € o %
            kpi_matches = re.findall(r'([\w\s]+)[:\s]*(€[\d.,]+[KMB]?|\d+%|\d+[\.,]\d+)', financial)
            highlights['key_kpis'] = [(k.strip(), v) for k, v in kpi_matches[:4]]

        return highlights

    def _generate_questionnaire_badge(self, total_questionnaires: int) -> str:
        """Genera badge per i questionari compilati"""
        if total_questionnaires == 0:
            return ""

        return f'''
            <div class="credibility-badge" style="background: linear-gradient(135deg, #7B1FA2 0%, #9C27B0 100%);">
                <span>📋 Doc. Board:</span>
                <span class="credibility-score">{total_questionnaires}</span>
            </div>
        '''

    def _generate_html(
        self,
        club_name: str,
        primary_color: str,
        secondary_color: str,
        category: str,
        credibility_score: int,
        sources_count: int,
        stw_progress: Dict[str, int],
        highlights: Dict[str, Any],
        total_questionnaires: int = 0,
        metadata: Dict = None
    ) -> str:
        """Genera l'HTML completo del One-Pager"""
        metadata = metadata or {}

        current_year = datetime.now().year
        generation_date = datetime.now().strftime("%d/%m/%Y")

        # Calcola colore chiaro
        light_color = self._lighten_color(primary_color, 0.92)
        contrast_color = self._get_contrast_color(primary_color)

        # Top priorities HTML
        priorities_html = ''
        priorities = highlights.get('top_priorities', [])
        if not priorities:
            priorities = [
                'Completare organigramma tecnico (STW 1.1)',
                'Definire piano marketing annuale (STW M2.2)',
                'Attivare sistema CRM tifosi (STW M2.4)',
                'Sviluppare programma settore giovanile',
                'Implementare policy HR aziendali'
            ]
        for i, p in enumerate(priorities[:5], 1):
            priorities_html += f'''
            <div class="priority-item">
                <span class="priority-num">{i}</span>
                <span class="priority-text">{p[:60]}{'...' if len(p) > 60 else ''}</span>
            </div>'''

        # STW Progress bars
        stw_bars_html = ''
        stw_labels = {
            'sportivi': ('SPORTIVI', get_category_icon(STWCategory.SPORTIVI)),
            'strutturali': ('STRUTTURALI', get_category_icon(STWCategory.STRUTTURALI)),
            'marketing': ('MARKETING', get_category_icon(STWCategory.MARKETING)),
            'sociali': ('SOCIALI', get_category_icon(STWCategory.SOCIALI))
        }
        for key, (label, icon) in stw_labels.items():
            progress = stw_progress.get(key, 50)
            color = get_category_color(getattr(STWCategory, key.upper()))
            stw_bars_html += f'''
            <div class="stw-row">
                <span class="stw-icon">{icon}</span>
                <span class="stw-label">{label}</span>
                <div class="stw-bar">
                    <div class="stw-fill" style="width: {progress}%; background: {color};"></div>
                </div>
                <span class="stw-percent">{progress}%</span>
            </div>'''

        html = f'''<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>One-Pager - {club_name}</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=Oswald:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {{
            --primary: {primary_color};
            --secondary: {secondary_color};
            --light: #{light_color};
            --contrast: {contrast_color};
            --text: #1a1a1a;
            --text-muted: #666666;
            --border: #e5e5e5;
        }}

        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        @page {{
            size: A4;
            margin: 0;
        }}

        body {{
            font-family: 'Inter', -apple-system, sans-serif;
            background: #ffffff;
            color: var(--text);
            width: 210mm;
            min-height: 297mm;
            margin: 0 auto;
            padding: 0;
            -webkit-print-color-adjust: exact !important;
            print-color-adjust: exact !important;
        }}

        /* ============================================
           HEADER - Full width brand bar
           ============================================ */
        .header {{
            background: var(--primary);
            color: var(--contrast);
            padding: 8mm 10mm;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}

        .header-left {{
            display: flex;
            flex-direction: column;
            gap: 1mm;
        }}

        .header-brand {{
            font-size: 7pt;
            letter-spacing: 3px;
            text-transform: uppercase;
            opacity: 0.7;
        }}

        .header-club {{
            font-family: 'Oswald', sans-serif;
            font-size: 28pt;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 1px;
            line-height: 1;
        }}

        .header-right {{
            text-align: right;
        }}

        .header-title {{
            font-family: 'Oswald', sans-serif;
            font-size: 10pt;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 2px;
        }}

        .header-period {{
            font-size: 8pt;
            opacity: 0.8;
            margin-top: 1mm;
        }}

        /* ============================================
           MAIN CONTENT - Grid Layout
           ============================================ */
        .main {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            grid-template-rows: auto auto auto;
            gap: 5mm;
            padding: 8mm 10mm;
        }}

        /* ============================================
           KPI DASHBOARD - Top Row Full Width
           ============================================ */
        .kpi-dashboard {{
            grid-column: span 2;
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 4mm;
        }}

        .kpi-card {{
            background: var(--light);
            border-radius: 3mm;
            padding: 5mm;
            text-align: center;
            border-left: 4px solid var(--primary);
        }}

        .kpi-card.highlight {{
            background: var(--primary);
            color: var(--contrast);
            border-left: none;
        }}

        .kpi-value {{
            font-family: 'Oswald', sans-serif;
            font-size: 28pt;
            font-weight: 700;
            line-height: 1;
        }}

        .kpi-label {{
            font-size: 7pt;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-top: 2mm;
            opacity: 0.8;
        }}

        /* ============================================
           STW PROGRESS SECTION
           ============================================ */
        .stw-section {{
            background: #fafafa;
            border-radius: 3mm;
            padding: 5mm;
        }}

        .section-title {{
            font-family: 'Oswald', sans-serif;
            font-size: 11pt;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 1px;
            color: var(--primary);
            margin-bottom: 4mm;
            padding-bottom: 2mm;
            border-bottom: 2px solid var(--primary);
        }}

        .stw-row {{
            display: flex;
            align-items: center;
            gap: 3mm;
            margin-bottom: 3mm;
        }}

        .stw-icon {{
            font-size: 14pt;
            width: 8mm;
        }}

        .stw-label {{
            font-size: 8pt;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            width: 25mm;
        }}

        .stw-bar {{
            flex: 1;
            height: 6mm;
            background: #e0e0e0;
            border-radius: 3mm;
            overflow: hidden;
        }}

        .stw-fill {{
            height: 100%;
            border-radius: 3mm;
            transition: width 0.3s ease;
        }}

        .stw-percent {{
            font-size: 9pt;
            font-weight: 700;
            width: 10mm;
            text-align: right;
        }}

        /* ============================================
           PRIORITIES SECTION
           ============================================ */
        .priorities-section {{
            background: #fafafa;
            border-radius: 3mm;
            padding: 5mm;
        }}

        .priority-item {{
            display: flex;
            align-items: flex-start;
            gap: 3mm;
            margin-bottom: 3mm;
            padding-bottom: 3mm;
            border-bottom: 1px dashed var(--border);
        }}

        .priority-item:last-child {{
            margin-bottom: 0;
            padding-bottom: 0;
            border-bottom: none;
        }}

        .priority-num {{
            background: var(--primary);
            color: var(--contrast);
            width: 6mm;
            height: 6mm;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 8pt;
            font-weight: 700;
            flex-shrink: 0;
        }}

        .priority-text {{
            font-size: 9pt;
            line-height: 1.4;
        }}

        /* ============================================
           VISION QUOTE - Full Width
           ============================================ */
        .vision-section {{
            grid-column: span 2;
            background: linear-gradient(135deg, var(--primary) 0%, {self._darken_color(primary_color, 0.2)} 100%);
            color: var(--contrast);
            padding: 6mm 8mm;
            border-radius: 3mm;
            position: relative;
        }}

        .vision-quote {{
            font-size: 12pt;
            font-style: italic;
            line-height: 1.5;
            position: relative;
            padding-left: 8mm;
        }}

        .vision-quote::before {{
            content: '"';
            font-family: 'Oswald', serif;
            font-size: 48pt;
            position: absolute;
            left: -2mm;
            top: -5mm;
            opacity: 0.3;
        }}

        .vision-label {{
            font-size: 7pt;
            text-transform: uppercase;
            letter-spacing: 2px;
            opacity: 0.7;
            margin-bottom: 2mm;
        }}

        /* ============================================
           TIMELINE / ROADMAP
           ============================================ */
        .timeline-section {{
            grid-column: span 2;
            background: #fafafa;
            border-radius: 3mm;
            padding: 5mm;
        }}

        .timeline {{
            display: flex;
            justify-content: space-between;
            position: relative;
            margin-top: 4mm;
        }}

        .timeline::before {{
            content: '';
            position: absolute;
            top: 4mm;
            left: 10%;
            right: 10%;
            height: 2px;
            background: var(--border);
        }}

        .timeline-item {{
            text-align: center;
            position: relative;
            flex: 1;
        }}

        .timeline-dot {{
            width: 8mm;
            height: 8mm;
            background: var(--primary);
            border-radius: 50%;
            margin: 0 auto 3mm;
            display: flex;
            align-items: center;
            justify-content: center;
            color: var(--contrast);
            font-size: 7pt;
            font-weight: 700;
            position: relative;
            z-index: 1;
        }}

        .timeline-year {{
            font-family: 'Oswald', sans-serif;
            font-size: 10pt;
            font-weight: 700;
            color: var(--primary);
        }}

        .timeline-desc {{
            font-size: 7pt;
            color: var(--text-muted);
            margin-top: 1mm;
        }}

        /* ============================================
           FOOTER
           ============================================ */
        .footer {{
            background: var(--text);
            color: #ffffff;
            padding: 4mm 10mm;
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 7pt;
        }}

        .footer-left {{
            display: flex;
            gap: 6mm;
        }}

        .footer-item {{
            display: flex;
            flex-direction: column;
        }}

        .footer-label {{
            opacity: 0.6;
            text-transform: uppercase;
            letter-spacing: 1px;
            font-size: 6pt;
        }}

        .footer-value {{
            font-weight: 600;
        }}

        .footer-qr {{
            width: 15mm;
            height: 15mm;
            background: #ffffff;
            border-radius: 2mm;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 6pt;
            color: var(--text);
        }}

        /* ============================================
           CREDIBILITY BADGE
           ============================================ */
        .credibility-badge {{
            display: inline-flex;
            align-items: center;
            gap: 2mm;
            background: rgba(255,255,255,0.2);
            padding: 2mm 4mm;
            border-radius: 2mm;
            font-size: 8pt;
        }}

        .credibility-score {{
            font-weight: 700;
            font-size: 10pt;
        }}

        /* ============================================
           PRINT STYLES
           ============================================ */
        @media print {{
            body {{
                width: 210mm;
                height: 297mm;
            }}

            .header, .vision-section, .kpi-card.highlight {{
                -webkit-print-color-adjust: exact !important;
                print-color-adjust: exact !important;
            }}
        }}
    </style>
</head>
<body>

    <!-- HEADER -->
    <header class="header">
        <div class="header-left">
            <span class="header-brand">Rooting Future</span>
            <span class="header-club">{club_name}</span>
        </div>
        <div class="header-right">
            <div class="header-title">Piano Strategico</div>
            <div class="header-period">{current_year} — {current_year + 3}</div>
            <div class="credibility-badge">
                <span>Credibilità:</span>
                <span class="credibility-score">{credibility_score}%</span>
            </div>
            {self._generate_questionnaire_badge(total_questionnaires)}
        </div>
    </header>

    <!-- MAIN CONTENT -->
    <main class="main">

        <!-- KPI DASHBOARD -->
        <div class="kpi-dashboard">
            <div class="kpi-card highlight">
                <div class="kpi-value">3</div>
                <div class="kpi-label">Anni Piano</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-value">8</div>
                <div class="kpi-label">Aree Strategiche</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-value">{sources_count}</div>
                <div class="kpi-label">Fonti Verificate</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-value">21</div>
                <div class="kpi-label">Obiettivi STW</div>
            </div>
        </div>

        <!-- STW PROGRESS -->
        <div class="stw-section">
            <h3 class="section-title">Copertura Matrice STW</h3>
            {stw_bars_html}
        </div>

        <!-- TOP PRIORITIES -->
        <div class="priorities-section">
            <h3 class="section-title">Top 5 Priorità</h3>
            {priorities_html}
        </div>

        <!-- VISION QUOTE -->
        <div class="vision-section">
            <div class="vision-label">Visione Strategica</div>
            <div class="vision-quote">
                {highlights.get('vision', 'Consolidare la posizione competitiva attraverso lo sviluppo del settore giovanile, il rafforzamento dell\'identità di marca e la sostenibilità economico-finanziaria nel medio-lungo termine.')}
            </div>
        </div>

        <!-- TIMELINE ROADMAP -->
        <div class="timeline-section">
            <h3 class="section-title">Roadmap Triennale</h3>
            <div class="timeline">
                <div class="timeline-item">
                    <div class="timeline-dot">Q1</div>
                    <div class="timeline-year">{current_year}</div>
                    <div class="timeline-desc">Setup &<br>Analisi</div>
                </div>
                <div class="timeline-item">
                    <div class="timeline-dot">Q4</div>
                    <div class="timeline-year">{current_year}</div>
                    <div class="timeline-desc">Quick<br>Wins</div>
                </div>
                <div class="timeline-item">
                    <div class="timeline-dot">H1</div>
                    <div class="timeline-year">{current_year + 1}</div>
                    <div class="timeline-desc">Sviluppo<br>Organico</div>
                </div>
                <div class="timeline-item">
                    <div class="timeline-dot">H2</div>
                    <div class="timeline-year">{current_year + 2}</div>
                    <div class="timeline-desc">Scale<br>Up</div>
                </div>
                <div class="timeline-item">
                    <div class="timeline-dot">FY</div>
                    <div class="timeline-year">{current_year + 3}</div>
                    <div class="timeline-desc">Target<br>Raggiunto</div>
                </div>
            </div>
        </div>

    </main>

    <!-- FOOTER -->
    <footer class="footer">
        <div class="footer-left">
            <div class="footer-item">
                <span class="footer-label">Categoria</span>
                <span class="footer-value">{category}</span>
            </div>
            <div class="footer-item">
                <span class="footer-label">Generato</span>
                <span class="footer-value">{generation_date}</span>
            </div>
            <div class="footer-item">
                <span class="footer-label">Framework</span>
                <span class="footer-value">STW Methodology</span>
            </div>
            <div class="footer-item">
                <span class="footer-label">Engine</span>
                <span class="footer-value">Rooting Future v5.4</span>
            </div>
            {f'''<div class="footer-item">
                <span class="footer-label">⏱️ Tempo Gen.</span>
                <span class="footer-value">{int(metadata.get("total_generation_time", 0) // 60)}m {int(metadata.get("total_generation_time", 0) % 60)}s</span>
            </div>''' if metadata and metadata.get("total_generation_time") else ''}
        </div>
        <div class="footer-qr">
            QR
        </div>
    </footer>

</body>
</html>'''

        return html

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
onepager_exporter = OnePagerExporter()


def create_onepager(
    plan_data: Dict,
    club_name: str,
    metadata: Dict = None,
    stw_progress: Dict[str, int] = None
) -> Path:
    """
    Funzione helper per creare One-Pager infografica.

    Args:
        plan_data: Dati del piano strategico
        club_name: Nome del club
        metadata: Metadati (colori, categoria, etc.)
        stw_progress: Progressi STW per categoria

    Returns:
        Path del file HTML generato
    """
    return onepager_exporter.export(plan_data, club_name, metadata, stw_progress)


if __name__ == "__main__":
    # Test
    test_plan = {
        'executive_summary': '''
            La visione strategica triennale prevede il consolidamento della posizione competitiva.

            1. Completare organigramma tecnico
            2. Definire piano marketing
            3. Sviluppare settore giovanile
            4. Implementare CRM
            5. Rafforzare governance
        ''',
        'financial': '''
            Fatturato target: €500K
            Monte ingaggi: 45%
            ROI previsto: 15%
        '''
    }

    test_metadata = {
        'primary_color': '#1a365d',
        'secondary_color': '#c9a227',
        'category': 'Eccellenza',
        'credibility_score': 78,
        'sources_count': 12
    }

    path = create_onepager(test_plan, "AC Riccione 1926", test_metadata)
    print(f"One-Pager generato: {path}")
