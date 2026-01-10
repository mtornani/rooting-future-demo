"""
Rooting Future Strategy Engine
Export One-Pager Infografica

Genera un documento A4 singola pagina (o doppia) con:
- Dashboard visuale immediata
- KPI chiave
- Matrice STW semplificata
- Top 5 priorità

Design: Senior Data Architect Edition (Purple & Bold)
"""

import re
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

from config import OUTPUT_DIR
from stw_matrix import STW_FRAMEWORK, STWCategory, get_category_color, get_category_icon
from stw_analyzer import calculate_stw_progress
from data_estimator import estimate_missing_financials, DataTier

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
        """
        metadata = metadata or {}
        primary_color = "#6a0dad" # Viola RF
        secondary_color = metadata.get('secondary_color', '#c9a227')
        category = metadata.get('category', 'Serie D')
        credibility_score = metadata.get('credibility_score', 72)
        sources_count = metadata.get('sources_count', 15)
        total_questionnaires = metadata.get('total_questionnaires', 0)

        # Centralized KPI Extraction
        club_data_input = {
            'dimensione_rosa': metadata.get('dimensione_rosa', 22),
            'capienza_stadio': metadata.get('capienza_stadio', 0)
        }
        known_financials = metadata.get('known_financials', {})
        estimates = estimate_missing_financials(club_data_input, category, known_financials)

        # Estrai highlights dal piano
        highlights = self._extract_highlights(plan_data)

        # Calcola progress STW dinamicamente se non fornito
        if stw_progress is None:
            stw_progress = calculate_stw_progress(plan_data)

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
            estimates=estimates,
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

            # Cerca priorità (liste numerate o bold)
            priorities = re.findall(r'(?:^|\n)\s*\d+\.\s*\*?\*?([^*\n]+)', exec_summary)
            if not priorities:
                priorities = re.findall(r'\*\*([A-ZÀ-Ÿ].{10,80})\*\*', exec_summary)
            highlights['top_priorities'] = [p.strip() for p in priorities[:5]]

        return highlights

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
        estimates: Dict = None,
        metadata: Dict = None
    ) -> str:
        """Genera l'HTML completo del One-Pager con Montserrat/Inter"""
        metadata = metadata or {}
        current_year = datetime.now().year
        generation_date = datetime.now().strftime("%d/%m/%Y")

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
                <span class="priority-text">{p}</span>
            </div>'''

        # KPI Dashboard con dati reali centralizzati
        kpis = []
        if estimates:
            fat = estimates.get('fatturato')
            mi = estimates.get('monte_ingaggi')
            vr = estimates.get('valore_rosa')
            
            kpis.append(('FATTURATO', f"€{fat.value/1000:.0f}K", 'ver' if fat.tier == DataTier.TIER_1_FACT else 'est'))
            kpis.append(('INGAGGI', f"€{mi.value/1000:.0f}K", 'ver' if mi.tier == DataTier.TIER_1_FACT else 'est'))
            kpis.append(('ROSA', f"€{vr.value/1000:.0f}K", 'ver' if vr.tier == DataTier.TIER_1_FACT else 'est'))
            kpis.append(('FONTI', str(sources_count), 'r'))

        kpi_html = ''
        for label, val, s_type in kpis:
            badge = '📋' if s_type == 'ver' else '📊' if s_type == 'est' else '🔍'
            kpi_html += f'''
            <div class="kpi-card">
                <div class="kpi-value">{val}</div>
                <div class="kpi-label">{badge} {label}</div>
            </div>'''

        # STW Progress bars
        stw_bars_html = ''
        stw_labels = [
            ('sportivi', 'SPORTIVI', STWCategory.SPORTIVI),
            ('strutturali', 'STRUTTURALI', STWCategory.STRUTTURALI),
            ('marketing', 'MARKETING', STWCategory.MARKETING),
            ('sociali', 'SOCIALI', STWCategory.SOCIALI)
        ]
        for key, label, cat_enum in stw_labels:
            progress = stw_progress.get(key, 50)
            color = get_category_color(cat_enum)
            stw_bars_html += f'''
            <div class="stw-row">
                <span class="stw-icon">{get_category_icon(cat_enum)}</span>
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
    <title>One-Pager - {club_name}</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600&family=Montserrat:wght@700;800&display=swap" rel="stylesheet">
    <style>
        :root {{
            --primary: {primary_color};
            --primary-dark: #4b0082;
            --secondary: {secondary_color};
            --text: #1a1a1a;
            --text-muted: #666;
            --bg-light: #fdfbff;
            --badge-q: #7B1FA2;
        }}

        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        @page {{ size: A4; margin: 0; }}

        body {{
            font-family: 'Inter', sans-serif;
            background: #ffffff;
            color: var(--text);
            width: 210mm;
            height: 297mm;
            margin: 0 auto;
            display: flex;
            flex-direction: column;
        }}

        .header {{
            background: linear-gradient(135deg, var(--primary-dark) 0%, var(--primary) 100%);
            color: white;
            padding: 10mm 15mm;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}

        .header-club {{
            font-family: 'Montserrat', sans-serif;
            font-size: 24pt;
            font-weight: 800;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}

        .main {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 8mm;
            padding: 10mm 15mm;
            flex: 1;
        }}

        .kpi-dashboard {{
            grid-column: span 2;
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 5mm;
        }}

        .kpi-card {{
            background: var(--bg-light);
            border-radius: 12px;
            padding: 6mm;
            text-align: center;
            border: 1px solid #e9d8fd;
            border-bottom: 4px solid var(--primary);
        }}

        .kpi-value {{
            font-family: 'Montserrat', sans-serif;
            font-size: 22pt;
            font-weight: 800;
            color: var(--primary);
            line-height: 1;
        }}

        .kpi-label {{
            font-size: 7.5pt;
            font-weight: 700;
            text-transform: uppercase;
            margin-top: 2mm;
            color: var(--text-muted);
        }}

        .section-title {{
            font-family: 'Montserrat', sans-serif;
            font-size: 12pt;
            font-weight: 800;
            text-transform: uppercase;
            color: var(--primary);
            margin-bottom: 5mm;
            border-bottom: 2px solid var(--primary);
            padding-bottom: 2mm;
        }}

        .stw-section, .priorities-section {{
            background: white;
            border-radius: 12px;
            padding: 6mm;
            border: 1px solid #eee;
        }}

        .stw-row {{ display: flex; align-items: center; gap: 3mm; margin-bottom: 4mm; }}
        .stw-label {{ font-size: 8pt; font-weight: 700; width: 25mm; }}
        .stw-bar {{ flex: 1; height: 5mm; background: #eee; border-radius: 10px; overflow: hidden; }}
        .stw-fill {{ height: 100%; border-radius: 10px; }}
        .stw-percent {{ font-size: 9pt; font-weight: 700; width: 10mm; text-align: right; }}

        .priority-item {{ display: flex; align-items: flex-start; gap: 4mm; margin-bottom: 4mm; }}
        .priority-num {{ background: var(--primary); color: white; width: 7mm; height: 7mm; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: 800; font-size: 9pt; flex-shrink: 0; }}
        .priority-text {{ font-size: 9.5pt; line-height: 1.3; font-weight: 500; }}

        .vision-section {{
            grid-column: span 2;
            background: linear-gradient(135deg, var(--primary-dark) 0%, var(--primary) 100%);
            color: white;
            padding: 8mm 10mm;
            border-radius: 12px;
            text-align: center;
        }}

        .vision-quote {{ font-family: 'Inter', sans-serif; font-size: 13pt; font-style: italic; line-height: 1.5; }}

        .footer {{
            background: #1a1a1a;
            color: white;
            padding: 6mm 15mm;
            display: flex;
            justify-content: space-between;
            font-size: 8pt;
        }}

        .credibility-badge {{ background: var(--badge-q); color: white; padding: 2px 8px; border-radius: 4px; font-weight: 700; }}
    </style>
</head>
<body>
    <header class="header">
        <div>
            <div style="font-size: 8pt; letter-spacing: 3px; opacity: 0.8; text-transform: uppercase;">Strategic Infographic</div>
            <div class="header-club">{club_name}</div>
        </div>
        <div style="text-align: right;">
            <div style="font-family: 'Montserrat'; font-size: 11pt; font-weight: 700;">PIANO STRATEGICO {current_year}</div>
            <div class="credibility-badge">📋 Dati Board: {total_questionnaires} • {credibility_score}% Credibilità</div>
        </div>
    </header>

    <main class="main">
        <div class="kpi-dashboard">
            {kpi_html}
        </div>

        <div class="stw-section">
            <h3 class="section-title">Copertura Matrice STW</h3>
            {stw_bars_html}
        </div>

        <div class="priorities-section">
            <h3 class="section-title">Top 5 Priorità</h3>
            {priorities_html}
        </div>

        <div class="vision-section">
            <div style="font-size: 8pt; text-transform: uppercase; letter-spacing: 2px; margin-bottom: 3mm; opacity: 0.7;">Visione Strategica Unificata</div>
            <div class="vision-quote">"{highlights.get('vision', 'Guidare il club verso una crescita sostenibile, unendo eccellenza tecnica e solidità finanziaria.')}"</div>
        </div>
    </main>

    <footer class="footer">
        <div>Rooting Future Strategy Engine v5.4.3</div>
        <div>Generato il {generation_date}</div>
        <div>Metodologia STW-Aligned</div>
    </footer>
</body>
</html>'''
        return html

    def _lighten_color(self, hex_color: str, factor: float = 0.9) -> str:
        hex_color = hex_color.lstrip('#')
        r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        r = min(255, int(r + (255 - r) * factor))
        g = min(255, int(g + (255 - g) * factor))
        b = min(255, int(b + (255 - b) * factor))
        return f'{r:02x}{g:02x}{b:02x}'

    def _darken_color(self, hex_color: str, factor: float = 0.2) -> str:
        hex_color = hex_color.lstrip('#')
        r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        r = int(r * (1 - factor))
        g = int(g * (1 - factor))
        b = int(b * (1 - factor))
        return f'#{r:02x}{g:02x}{b:02x}'

    def _get_contrast_color(self, hex_color: str) -> str:
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
    """
    return onepager_exporter.export(plan_data, club_name, metadata, stw_progress)


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
