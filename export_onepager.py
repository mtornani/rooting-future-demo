"""
Rooting Future Strategy Engine
Export One-Pager Infografica

Genera un documento A4 singola pagina (o doppia) con:
- Dashboard visuale immediata
- KPI chiave
- Matrice STW semplificata
- Top 5 priorità

Design: Senior Data Architect Edition (Purple & Bold)

CONSOLIDATO: Ora eredita da BaseExporter (REF-002)
"""

import re
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

from export_core import BaseExporter
from export_styles import RF_FONT_IMPORT, RF_BADGE_CSS
from stw_matrix import STW_FRAMEWORK, STWCategory, get_category_color, get_category_icon
from stw_analyzer import calculate_stw_progress
from data_estimator import estimate_missing_financials, DataTier

logger = logging.getLogger(__name__)


class OnePagerExporter(BaseExporter):
    """
    Genera infografica A4 singola pagina per condivisione rapida.
    Design: Dashboard-style con KPI, progress bars, top priorities.

    Eredita da BaseExporter per condividere utilities comuni.
    """

    def __init__(self, output_dir: Optional[Path] = None):
        super().__init__(output_dir)

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
        primary_color = metadata.get('primary_color', '#6a0dad')
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
        highlights = self._extract_highlights(plan_data, metadata)

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

    def _extract_highlights(self, plan_data: Dict, metadata: Dict = None) -> Dict[str, Any]:
        """Estrae highlights chiave dal piano per il one-pager"""
        highlights = {
            'vision': '',
            'top_priorities': [],
            'quick_wins': [],
            'key_kpis': [],
            'risks': []
        }
        
        # Default motivations dictionary
        DEFAULT_MOTIVATIONS = {
            'SPORTIVI': 'Performance sportiva è driver principale per crescita club e attenzione mediatica.',
            'STRUTTURALI': 'Fondamenta organizzative robuste garantiscono sostenibilità di lungo termine.',
            'MARKETING': 'Visibilità e brand strength sono prerequisiti per crescita ricavi commerciali.',
            'SOCIALI': 'Impatto sociale positivo rafforza legame con territorio e attrae sponsor ESG-oriented.',
            'FINANZIARI': 'Sostenibilità economica è condizione necessaria per ogni strategia di crescita.'
        }

        # Estrai dall'executive summary (anche coordinator_summary come alias)
        exec_summary = plan_data.get('executive_summary', '') or plan_data.get('coordinator_summary', '')
        if exec_summary:
            # Cerca visione — pattern specifico
            vision_match = re.search(r'(?:visione|vision)[:\s]*([^.]+\.)', exec_summary, re.IGNORECASE)
            if vision_match:
                highlights['vision'] = vision_match.group(1).strip()[:200]
            # Fallback: prima frase lunga del summary come vision statement
            if not highlights['vision']:
                sentences = re.findall(r'[A-ZÀ-Ÿ][^.!?]{40,200}[.!?]', exec_summary)
                if sentences:
                    highlights['vision'] = sentences[0].strip()[:200]

            # Cerca priorità (liste numerate o bold) con eventuale motivazione
            priorities = re.findall(r'(?:^|\n)\s*\d+\.\s*\*?\*?([^*\n]+)', exec_summary)
            if not priorities:
                priorities = re.findall(r'\*\*([A-ZÀ-Ÿ].{10,80})\*\*', exec_summary)
            
            # Formatta priorità separando eventuale motivazione (cerca " - " o " : ")
            formatted_priorities = []
            for p in priorities[:5]:
                p_text = p.strip()
                title = p_text
                reason = ""
                
                if " - " in p_text:
                    parts = p_text.split(" - ", 1)
                    title = parts[0].strip()
                    reason = parts[1].strip()
                elif " : " in p_text:
                    parts = p_text.split(" : ", 1)
                    title = parts[0].strip()
                    reason = parts[1].strip()
                
                # FALLBACK MOTIVATION GENERATION
                if not reason:
                    # Guess category from title
                    t_upper = title.upper()
                    if 'SPORT' in t_upper or 'TECNIC' in t_upper or 'SQUADRA' in t_upper:
                        reason = DEFAULT_MOTIVATIONS['SPORTIVI']
                    elif 'STRUTTUR' in t_upper or 'IMPIANT' in t_upper or 'ORGANIZ' in t_upper:
                        reason = DEFAULT_MOTIVATIONS['STRUTTURALI']
                    elif 'MARKET' in t_upper or 'COMUNICAZ' in t_upper or 'BRAND' in t_upper:
                        reason = DEFAULT_MOTIVATIONS['MARKETING']
                    elif 'SOCIAL' in t_upper or 'TERRITOR' in t_upper:
                        reason = DEFAULT_MOTIVATIONS['SOCIALI']
                    elif 'FINANZ' in t_upper or 'BUDGET' in t_upper or 'RICAV' in t_upper:
                        reason = DEFAULT_MOTIVATIONS['FINANZIARI']
                    else:
                        reason = "Priorità strategica identificata per massimizzare l'impatto nel breve termine."

                formatted_priorities.append({"title": title, "reason": reason})
            
            highlights['top_priorities'] = formatted_priorities

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
        
        # Calculate contrast for dynamic backgrounds
        contrast_color = self._get_contrast_color(primary_color)
        contrast_color_secondary = self._get_contrast_color(secondary_color)
        
        # FIX: Text on white background should be readable even if primary is white/light
        text_on_white = primary_color
        # Calcolo luminanza: se il colore è troppo chiaro, lo scuriamo in modo aggressivo per il testo su bianco
        r, g, b = tuple(int(primary_color.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
        lum = (0.299 * r + 0.587 * g + 0.114 * b) / 255
        
        if lum > 0.65: # Abbassata soglia per maggior sicurezza
            # Se è quasi bianco, usa un grigio molto scuro o il colore originale molto scurito
            text_on_white = '#' + self._darken_color(primary_color, 0.7)
        
        # Ulteriore check: se dopo lo scurimento è ancora troppo chiaro (es. partendo da bianco puro)
        r2, g2, b2 = tuple(int(text_on_white.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
        lum2 = (0.299 * r2 + 0.587 * g2 + 0.114 * b2) / 255
        if lum2 > 0.7:
            text_on_white = "#333333" # Fallback a grigio scuro leggibile

        # Top priorities HTML
        priorities_html = ''
        priorities = highlights.get('top_priorities', [])
        if not priorities:
            priorities_html = '<p style="font-size:8pt; color:#888; font-style:italic;">Priorità non estratte — consultare il Piano Strategico Completo.</p>'
        for i, p in enumerate(priorities[:5], 1):
            title = p.get('title', '') if isinstance(p, dict) else p
            reason = p.get('reason', '') if isinstance(p, dict) else ''
            
            priorities_html += f'''
            <div class="priority-item">
                <span class="priority-num" style="background: {text_on_white}; color: {self._get_contrast_color(text_on_white)};">{i}</span>
                <div style="display: flex; flex-direction: column;">
                    <span class="priority-text" style="font-weight: 700; color: {text_on_white};">{title}</span>
                    {f'<span class="priority-reason" style="font-size: 8pt; color: #666; font-style: italic; margin-top: 0.5mm;">{reason}</span>' if reason else ''}
                </div>
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
            <div class="kpi-card" style="border-bottom-color: {text_on_white};
">
                <div class="kpi-value" style="color: {text_on_white};">{val}</div>
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
            prog_data = stw_progress.get(key, {})
            # Gestisci sia dict che int per compatibilità
            progress = prog_data.get('progress', 50) if isinstance(prog_data, dict) else prog_data
            reasoning = prog_data.get('reasoning', '') if isinstance(prog_data, dict) else ''
            
            color = get_category_color(cat_enum)
            stw_bars_html += f'''
            <div class="stw-row" style="margin-bottom: 4mm; display: flex; flex-direction: column; align-items: stretch;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1mm;">
                    <span class="stw-label" style="font-weight: 700; font-size: 8pt; width: auto;">{get_category_icon(cat_enum)} {label}</span>
                    <span class="stw-percent" style="font-weight: 800; color: {color}; width: auto;">{progress}%</span>
                </div>
                <div class="stw-bar" style="background: #eee; height: 6px; border-radius: 3px; overflow: hidden; width: 100%;">
                    <div class="stw-fill" style="width: {progress}%; background: {color}; height: 100%;"></div>
                </div>
                {f'<div style="font-size: 7pt; color: #666; margin-top: 1mm; font-style: italic;">{reasoning}</div>' if reasoning else ''}
            </div>'''

        html = f'''<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <title>Piano Strategico - {club_name}</title>
    {RF_FONT_IMPORT}
    <style>
        :root {{
            --club-primary: {metadata.get('primary_color', primary_color)};
            --club-secondary: {metadata.get('secondary_color', secondary_color)};
            --primary: var(--club-primary);
            --primary-dark: var(--club-primary);
            --brand-gradient: linear-gradient(135deg, var(--club-primary) 0%, var(--club-secondary) 100%);
            --secondary: var(--club-secondary);
            --contrast-color: {contrast_color};
            --contrast-color-sec: {contrast_color_secondary};
            --text-on-white: {text_on_white};
            --text: #1a1a1a;
            --text-muted: #666;
            --bg-light: #fdfbff;
            --badge-q: #7B1FA2;
        }}

        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        @page {{ size: A4; margin: 0; }}

        body {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: #ffffff;
            color: var(--text);
            width: 210mm;
            height: 297mm;
            margin: 0 auto;
            display: flex;
            flex-direction: column;
        }}

        .header {{ 
            background: var(--brand-gradient);
            color: var(--contrast-color);
            padding: 10mm 15mm;
            display: flex;
            justify-content: space-between;
            align-items: center;
            position: relative;
        }}
        

        .header-club {{
            font-family: 'DM Serif Display', Georgia, serif;
            font-size: 24pt;
            font-weight: 400;
            text-transform: none;
            letter-spacing: -0.3px;
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
            background: white;
            border-radius: 8px;
            padding: 6mm;
            text-align: center;
            border: 1px solid rgba(0,0,0,0.08);
            border-bottom: 4px solid var(--text-on-white);
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        }}

        .kpi-value {{
            font-family: 'DM Serif Display', Georgia, serif;
            font-size: 22pt;
            font-weight: 400;
            color: var(--text-on-white);
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
            color: var(--text-on-white);
            margin-bottom: 5mm;
            border-bottom: 2px solid var(--text-on-white);
            padding-bottom: 2mm;
        }}

        .stw-section, .priorities-section {{
            background: white;
            border-radius: 8px;
            padding: 6mm;
            border: 1px solid rgba(0,0,0,0.07);
            box-shadow: 0 2px 8px rgba(0,0,0,0.04);
        }}

        .priority-item {{ display: flex; align-items: flex-start; gap: 4mm; margin-bottom: 3.5mm; }}
        .priority-num {{ 
            background: var(--text-on-white); 
            color: var(--contrast-color); 
            width: 6.5mm; height: 6.5mm; 
            border-radius: 50%; 
            display: flex; align-items: center; justify-content: center; 
            font-weight: 800; font-size: 8.5pt; 
            flex-shrink: 0; margin-top: 0.5mm; 
        }}
        .priority-text {{ font-size: 9pt; line-height: 1.2; font-weight: 700; color: var(--text-on-white); }}
        .priority-reason {{ font-size: 8pt; line-height: 1.3; color: var(--text-muted); font-style: italic; }}

        .vision-section {{ 
            grid-column: span 2;
            background: var(--brand-gradient);
            color: var(--contrast-color);
            padding: 8mm 10mm;
            border-radius: 12px;
            text-align: center;
            position: relative;
            overflow: hidden;
        }}
        

        .vision-quote {{ font-family: 'DM Serif Display', Georgia, serif; font-size: 13pt; font-style: italic; line-height: 1.5; position: relative; z-index: 1; }}

        .footer {{
            background: var(--club-primary);
            color: var(--contrast-color);
            padding: 5mm 15mm;
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 8pt;
            border-top: 2px solid var(--club-secondary);
            opacity: 0.92;
        }}

        .credibility-badge {{ background: var(--badge-q); color: white; padding: 2px 8px; border-radius: 4px; font-weight: 700; }}

        /* === 1-PAGE CONSTRAINT === */
        body {{ overflow: hidden; }}
        .main {{ overflow: hidden; }}

        /* === PRINT BUTTON (screen only) === */
        .print-bar {{
            position: fixed;
            bottom: 20px;
            right: 20px;
            z-index: 10000;
            display: flex;
            flex-direction: column;
            align-items: flex-end;
            gap: 6px;
        }}
        .print-btn {{
            background: var(--club-secondary);
            color: white;
            border: none;
            padding: 10px 18px;
            border-radius: 7px;
            font-family: 'Montserrat', sans-serif;
            font-size: 10pt;
            font-weight: 700;
            cursor: pointer;
            box-shadow: 0 4px 14px rgba(0,0,0,0.22);
            transition: transform 0.15s;
            letter-spacing: 0.5px;
        }}
        .print-btn:hover {{ transform: translateY(-2px); }}
        .print-hint {{
            font-size: 7pt;
            color: #aaa;
            background: white;
            padding: 2px 8px;
            border-radius: 3px;
            border: 1px solid #eee;
        }}

        @media print {{
            .print-bar {{ display: none !important; }}
            * {{ -webkit-print-color-adjust: exact !important; color-adjust: exact !important; }}
            body {{ overflow: visible; height: 297mm; }}
        }}

        {RF_BADGE_CSS}
    </style>
</head>
<body>
<div class="print-bar">
    <button class="print-btn" onclick="window.print()">📥 Salva come PDF</button>
    <div class="print-hint">File → Stampa → Salva come PDF</div>
</div>
    <header class="header">
        <div>
            <div style="font-size: 8pt; letter-spacing: 2px; opacity: 0.8; text-transform: uppercase;">Rooting Future</div>
            <div class="header-club">{club_name}</div>
        </div>
        <div style="text-align: right; color: var(--contrast-color-sec);">
            <div style="font-family: 'Montserrat'; font-size: 11pt; font-weight: 700;">Piano Strategico {current_year}–{current_year + 3}</div>
            <div style="font-size: 8pt; opacity: 0.8; margin-top: 2mm;">Sintesi per la condivisione</div>
        </div>
    </header>

    <main class="main">
        <div class="kpi-dashboard">
            {kpi_html}
            <div style="grid-column: span 4; display: flex; justify-content: center; gap: 15mm; font-size: 7.5pt; margin-top: -2mm; color: var(--text-muted); font-weight: 500;">
                <span>📋 <strong style="color:#7B1FA2">Verificato</strong></span>
                <span>🔍 <strong style="color:#1565C0">Stimato</strong></span>
                <span>📊 <strong style="color:#F57C00">Benchmark</strong></span>
            </div>
        </div>
        
        <div class="stw-section">
            <h3 class="section-title">Copertura Strategica</h3>
            {stw_bars_html}
            <p style="font-size:7pt; color:#999; font-style:italic; margin-top:2mm;">Indicatore proporzionale alla profondità dell'analisi per area.</p>
        </div>

        <div class="priorities-section">
            <h3 class="section-title">Priorità Strategiche</h3>
            {priorities_html}
        </div>

        <div class="vision-section">
            <div style="font-size: 8pt; text-transform: uppercase; letter-spacing: 2px; margin-bottom: 3mm; opacity: 0.8;">Visione Strategica</div>
            <div class="vision-quote">"{highlights.get('vision', 'Guidare il club verso una crescita sostenibile, unendo eccellenza tecnica e solidità finanziaria.')}"</div>
        </div>
    </main>

    <footer class="footer">
        <div>&copy; {current_year} Rooting Future</div>
        <div>Piano Strategico · Analisi Dati · Uso Riservato</div>
        <div>rooting-future.it</div>
    </footer>
</body>
</html>'''
        return html

    # Color helpers ereditati da BaseExporter:
    # - _get_contrast_color()
    # - _lighten_color()
    # - _darken_color()


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
