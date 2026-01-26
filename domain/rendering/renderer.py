"""
Unified Rendering Layer - Rooting Future Strategy Engine v5.4
Consolidates structured_renderer, executive_report, and methodology_section.
"""

import os
import re
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

# Core Data Models
from data_models import (
    DataPoint, StructuredSection, StructuredPlan,
    DataType, ConfidenceLevel, DeviationType, Source, Benchmark,
    SourceType, BenchmarkDatabase
)

# Utils & Analyzers
from data_estimator import estimate_missing_financials, DataTier
from chart_generator import (
    generate_revenue_pie_chart,
    generate_benchmark_comparison,
    generate_gap_analysis_chart,
    embed_chart_in_html,
    generate_financial_charts_for_report
)
from stw_analyzer import calculate_stw_progress, STWAnalyzer
from stw_matrix import get_category_color, get_category_icon, STWCategory
from club_identity import get_club_identity

logger = logging.getLogger(__name__)

# =============================================================================
# CONSTANTS & FALLBACKS
# =============================================================================

MICRO_OBJECTIVES_FALLBACKS = {
    'CREAZIONE E SVILUPPO IDENTITÀ TECNICA': [
        'Definire modulo tattico unificato (es. 4-3-3) per tutte le categorie',
        'Formare lo staff tecnico su metodologia di gioco comune',
        'Implementare sistema di valutazione performance standardizzato',
        'Creare protocollo allenamenti settimanale condiviso tra categorie'
    ],
    'COSTRUZIONE E RINNOVAMENTO STRUTTURE': [
        'Mappare stato attuale impianti con report fotografico dettagliato',
        'Prioritizzare interventi su campo allenamento settore giovanile',
        'Ottenere certificazioni sicurezza aggiornate per tutti gli impianti',
        'Installare sistema illuminazione LED su campo principale'
    ],
    'SVILUPPO AREA COMUNICAZIONE': [
        'Pubblicare 3 post/settimana sui social media con calendario editoriale',
        'Creare newsletter mensile per tesserati e sponsor',
        'Implementare area stampa digitale sul sito web',
        'Avviare collaborazione con media locali per copertura partite'
    ],
    'SVILUPPO AREA MARKETING': [
        'Lanciare campagna sponsor per stagione 2026/27 con target €50K',
        'Creare merchandising ufficiale (maglie, sciarpe) entro marzo',
        'Implementare programma fedeltà per abbonati',
        'Organizzare 2 eventi corporate per attrarre nuovi partner'
    ],
    'SVILUPPO BRAND IDENTITY': [
        'Ridisegnare logo e brand guidelines entro aprile 2026',
        'Unificare comunicazione visiva su tutti i canali',
        'Creare brand book digitale per uso interno/esterno',
        'Registrare marchio presso UIBM per protezione legale'
    ],
    'SVILUPPO AREA COMMERCIALE': [
        'Mappare potenziali sponsor locali (target list di 30 aziende)',
        'Creare presentation deck commerciale con pacchetti sponsor',
        'Assumere commerciale part-time per gestione sponsor',
        'Attivare vendita biglietti online su piattaforma dedicata'
    ],
    'SVILUPPO INCLUSIONE E UGUAGLIANZA': [
        'Creare squadra femminile o accordo con club femminile locale',
        'Implementare protocollo anti-discriminazione in tutti gli eventi',
        'Organizzare torneo giovanile inclusivo aperto a tutti',
        'Formare staff su gestione diversità e inclusione'
    ],
    'PROTEZIONE BAMBINI/E E GIOVANI': [
        'Certificare tutti gli allenatori giovanili con corso Safeguarding',
        'Implementare protocollo tutela minori conforme FIGC',
        'Nominare responsabile protezione minori nel club',
        'Attivare assicurazione specifica per settore giovanile'
    ],
    'RISORSE UMANE': [
        'Digitalizzare gestione presenze staff con sistema HR cloud',
        'Creare organigramma chiaro con ruoli e responsabilità definiti',
        'Implementare valutazione annuale performance per staff tecnico',
        'Attivare convezioni welfare per dipendenti (palestra, assicurazioni)'
    ]
}

SYSTEM_SOURCES = {
    'questionnaire': {
        'name': 'Questionari Club',
        'type': 'tier1_fact',
        'description': 'Dati forniti direttamente dal club tramite questionari compilati',
        'confidence': 1.0
    },
    'transfermarkt': {
        'name': 'Transfermarkt',
        'type': 'tier1_fact',
        'description': 'Valori di mercato rosa, statistiche giocatori',
        'confidence': 0.90,
        'url': 'https://www.transfermarkt.it'
    },
    'figc_report': {
        'name': 'Report Calcio FIGC 2024',
        'type': 'tier1_fact',
        'description': 'Benchmark finanziari e sportivi ufficiali per categoria',
        'confidence': 0.95,
        'url': 'https://www.figc.it/it/federazione/report-calcio/'
    }
}

# =============================================================================
# HELPER FUNCTIONS (INTERNAL)
# =============================================================================

def _clean_text(text: str) -> str:
    if not text: return ""
    text = re.sub(r'\*\*|\*|#{1,4}\s*', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    if text.startswith(':'): text = text[1:].strip()
    return text

def _darken_color(hex_color: str, factor: float = 0.2) -> str:
    hex_color = hex_color.lstrip('#')
    if len(hex_color) != 6: return "#000000"
    r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    r = int(r * (1 - factor))
    g = int(g * (1 - factor))
    b = int(b * (1 - factor))
    return f'#{r:02x}{g:02x}{b:02x}'

def _get_contrast_color(hex_color: str) -> str:
    hex_color = hex_color.lstrip('#')
    if len(hex_color) != 6: return "#ffffff"
    r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
    return '#ffffff' if luminance < 0.5 else '#1a1a1a'

def _extract_key_points(content: str, max_points: int = 5) -> List[str]:
    if not content: return []
    points = []
    bold_with_content = re.findall(r'\*\*([A-Za-zÀ-ÿ][^*]{5,50})(?::\*\*|\*\*:)\s*([^*\n]{10,200})', content)
    for title, desc in bold_with_content:
        title = _clean_text(title)
        desc = _clean_text(desc)
        first_sentence = re.split(r'(?<=[.!?])\s', desc)[0] if desc else ''
        if first_sentence and len(first_sentence) > 15:
            point = f"{title}: {first_sentence}"
            if point not in points:
                points.append(point)
                if len(points) >= max_points: return points
    return points[:max_points]

# =============================================================================
# PLAN RENDERER
# =============================================================================

class PlanRenderer:
    """
    Unified rendering engine for strategic plans.
    """

    def __init__(self, output_dir: str = "output"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True, parents=True)
        self.footnotes = []
        self.footnote_counter = 0

    # --- STRUCTURED RENDERING ---

    def render_structured(self, plan: StructuredPlan) -> str:
        html = self.render_structured_html(plan)
        filename = f"{plan.club_name.replace(' ', '_')}_Structured_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        filepath = self.output_dir / filename
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html)
        return str(filepath)

    def render_structured_html(self, plan: StructuredPlan) -> str:
        self.footnotes = []
        self.footnote_counter = 0
        return f'''<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <title>Piano Strategico - {plan.club_name}</title>
    {self._get_structured_styles()}
</head>
<body>
    <div class="report">
        {self._render_structured_header(plan)}
        {self._render_credibility_dashboard(plan)}
        <main class="content">
            {"".join(self._render_section(s) for s in plan.sections.values())}
            {self._render_footnotes()}
        </main>
    </div>
</body>
</html>'''

    def _get_structured_styles(self) -> str:
        return '''<style>
            :root { --primary: #1a365d; --secondary: #2c5282; --success: #38a169; --gray-100: #f7fafc; --gray-800: #2d3748; }
            body { font-family: sans-serif; color: var(--gray-800); background: var(--gray-100); padding: 20px; }
            .report { max-width: 1000px; margin: 0 auto; background: white; box-shadow: 0 0 20px rgba(0,0,0,0.1); border-radius: 8px; overflow: hidden; }
            .report-header { background: var(--primary); color: white; padding: 40px; text-align: center; }
            .credibility-dashboard { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; padding: 20px; background: #eee; }
            .metric-card { background: white; padding: 15px; border-radius: 4px; text-align: center; }
            .content { padding: 40px; }
            .section { margin-bottom: 40px; border-bottom: 1px solid #eee; padding-bottom: 20px; }
            .summary-box { background: #f0f4f8; padding: 20px; border-left: 4px solid var(--secondary); margin: 20px 0; }
            .data-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
            .data-card { border: 1px solid #ddd; border-radius: 6px; padding: 15px; }
            .data-value { font-size: 1.5rem; font-weight: bold; color: var(--primary); }
        </style>'''

    def _render_structured_header(self, plan: StructuredPlan) -> str:
        return f'<header class="report-header"><h1>{plan.club_name}</h1><p>Piano Strategico Triennale</p></header>'

    def _render_credibility_dashboard(self, plan: StructuredPlan) -> str:
        return f'''<div class="credibility-dashboard">
            <div class="metric-card"><strong>{plan.overall_credibility:.1f}%</strong><br>Credibilita</div>
            <div class="metric-card"><strong>{plan.total_data_points}</strong><br>Dati Totali</div>
            <div class="metric-card"><strong>{plan.verified_data_points}</strong><br>Verificati</div>
            <div class="metric-card"><strong>{len(plan.bibliography)}</strong><br>Fonti</div>
        </div>'''

    def _render_section(self, section: StructuredSection) -> str:
        return f'''<section class="section">
            <h2>{section.title}</h2>
            <div class="summary-box">{section.summary}</div>
            <div class="data-grid">{"".join(self._render_data_card(dp) for dp in section.data_points)}</div>
        </section>'''

    def _render_data_card(self, dp: DataPoint) -> str:
        val = dp.formatted_value if dp.value is not None else "(da acquisire)"
        return f'<div class="data-card"><strong>{dp.label}</strong><br><span class="data-value">{val}</span></div>'

    def _render_footnotes(self) -> str:
        if not self.footnotes: return ""
        return "<h3>Note</h3>" + "".join(f"<div>[{f['num']}] {f['citation']}</div>" for f in self.footnotes)

    def _add_footnote(self, source: Source) -> int:
        self.footnote_counter += 1
        self.footnotes.append({"num": self.footnote_counter, "citation": source.to_citation()})
        return self.footnote_counter

    # --- EXECUTIVE RENDERING ---

    def render_executive(self, plan_data: Dict[str, str], club_name: str, category: str, metadata: Dict[str, Any]) -> str:
        html = self.render_executive_html(plan_data, club_name, category, metadata)
        safe_name = club_name.replace(" ", "_").replace("/", "_")
        filename = f"{safe_name}_Executive_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        filepath = self.output_dir / filename
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html)
        return str(filepath)

    def render_executive_html(self, plan_data: Dict[str, str], club_name: str, category: str, metadata: Dict[str, Any]) -> str:
        from executive_report import generate_executive_report_html
        return generate_executive_report_html(plan_data, club_name, category, metadata)

    # --- METHODOLOGY RENDERING ---

    def add_methodology(self, content: str, metadata: Dict = None, primary_color: str = "#1a365d") -> str:
        from methodology_section import generate_rooting_future_methodology_html
        methodology = generate_rooting_future_methodology_html(metadata, primary_color)
        if "</body>" in content:
            return content.replace("</body>", methodology + "</body>")
        return content + methodology

    def render_methodology(self, club_name: str, category: str, data_sources_used: List[str], estimated_fields: Dict[str, str], primary_color: str = "#1a365d") -> str:
        from methodology_section import generate_methodology_section_html
        return generate_methodology_section_html(club_name, category, data_sources_used, estimated_fields, primary_color)

    def render_stw_matrix(self, stw_data: Dict[str, int]) -> str:
        overall = sum(stw_data.values()) // len(stw_data) if stw_data else 0
        return f'''<div style="background:#f1f5f9; padding:20px; border-radius:12px; border-left:6px solid #1a365d;">
            <h4 style="margin:0 0 10px 0;">📊 Copertura Matrice STW: {overall}%</h4>
            <p style="font-size:0.85rem; color:#64748b;">Questo valore indica l'allineamento del piano agli obiettivi Sport To Win.</p>
        </div>'''
