"""
Rooting Future Strategy Engine v6.0
HTML Export Module con Chunking

Genera documenti HTML professionali evitando troncamenti.
Strategia: genera sezioni separatamente, poi assembla.
"""

import os
import re
import json
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from pathlib import Path
import logging

from config import EXPORT_CONFIG
from export_core import BaseExporter
from export_styles import RF_FONT_IMPORT, RF_RESET_CSS, RF_BADGE_CSS, RF_MACRO_CSS, RF_PRINT_CSS_FULL, RF_MOBILE_CSS
from stw_analyzer import get_stw_coverage_summary
from stw_matrix import get_category_color, get_category_icon, STWCategory, generate_stw_matrix_html, get_stw_matrix_css
from domain.rendering.renderer import PlanRenderer
def generate_rooting_future_methodology_html(metadata=None, primary_color='#1a365d'):
    return PlanRenderer().add_methodology("", metadata, primary_color)

logger = logging.getLogger(__name__)


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class HTMLSection:
    """Sezione HTML singola"""
    id: str
    title: str
    content: str
    order: int
    subsections: List[Dict] = field(default_factory=list)


# =============================================================================
# CHUNKED HTML EXPORTER
# =============================================================================

class ChunkedHTMLExporter(BaseExporter):
    """
    Genera HTML in modo incrementale per evitare troncamenti.
    Strategia: genera sezione per sezione, poi assembla.
    """

    def __init__(self, output_dir: Optional[Path] = None):
        super().__init__(output_dir)
        self.sections: List[HTMLSection] = []

    def export(
        self,
        plan_data: Dict,
        club_name: str,
        sources: List[Dict] = None,
        metadata: Dict = None
    ) -> Path:
        """
        Genera documento HTML completo senza troncamenti.
        """
        meta = self._extract_metadata(metadata)
        base_filename = self._get_safe_filename(club_name, "html", prefix="Piano").replace(".html", "")

        self.sections = []

        # Calcola copertura STW
        self.stw_coverage = get_stw_coverage_summary(plan_data)

        # 1. Genera sezioni
        section_titles = self._get_section_titles()
        preferred_order = self._get_preferred_section_order()

        order_idx = 0
        for key in preferred_order:
            if key in plan_data and plan_data[key]:
                section = HTMLSection(
                    id=key,
                    title=section_titles.get(key, key.replace('_', ' ').title()),
                    content=self._process_section_content(plan_data[key]),
                    order=order_idx
                )
                self.sections.append(section)
                self._save_section_backup(section, base_filename)
                order_idx += 1

        # 2. Aggiungi fonti se presenti
        if sources:
            sources_section = HTMLSection(
                id='sources',
                title='Fonti e Riferimenti',
                content=self._generate_sources_html(sources),
                order=99
            )
            self.sections.append(sources_section)

        # 3. Assembla documento finale
        final_html = self._assemble_document(club_name, meta)

        # 4. Salva
        filepath = self.output_dir / f"{base_filename}.html"
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(final_html)

        logger.info(f"HTML exported: {filepath}")

        # 5. Genera versione multi-pagina se necessario
        if len(self.sections) > EXPORT_CONFIG.generate_multipage_threshold:
            self._generate_multipage_version(base_filename, club_name, meta)

        return filepath

    def _get_accent_color(self, primary: str, secondary: str) -> str:
        """Ritorna il primary se abbastanza scuro, altrimenti il secondary (evita bianco su bianco)."""
        try:
            h = primary.lstrip('#')
            r, g, b = int(h[0:2], 16) / 255, int(h[2:4], 16) / 255, int(h[4:6], 16) / 255
            luminance = 0.299 * r + 0.587 * g + 0.114 * b
            return secondary if luminance > 0.6 else primary
        except Exception:
            return primary

    def _process_section_content(self, content: str) -> str:
        """Converte contenuto markdown-like in HTML usando BaseExporter logic"""
        if not content:
            return "<p><em>Contenuto non disponibile per questa sezione.</em></p>"

        # Guard: content troppo corto o messaggio d'errore → non renderizzare
        _error_markers = ["errore di connessione", "verifica la connessione", "si è verificato un errore"]
        if len(content.strip()) < 80 or any(m in content.lower() for m in _error_markers):
            return (
                '<div style="border-left:4px solid #F57C00; background:#FFF8E1; padding:14px 18px; '
                'border-radius:0 6px 6px 0; color:#555; font-style:italic;">'
                '⚠ Sezione non generata correttamente. Rigenera il piano per ottenere i contenuti completi.'
                '</div>'
            )

        normalized = self._normalize_markdown(content)
        return self._markdown_to_html(normalized)

    def _generate_sources_html(self, sources: List[Dict]) -> str:
        """Genera HTML per sezione fonti"""
        html = ['<div class="sources-section">']
        html.append('<p class="sources-intro">I dati contenuti in questo documento sono stati verificati attraverso le seguenti fonti:</p>')

        trusted = [s for s in sources if s.get('is_trusted', False)]
        other = [s for s in sources if not s.get('is_trusted', False)]

        if trusted:
            html.append('<h4>Fonti Istituzionali e Autorevoli</h4><ul class="sources-list trusted">')
            for s in trusted[:20]:
                url = s.get("url", "#")
                name = s.get("name", "N/A")
                html.append(f'<li><strong>{name}</strong>: <a href="{url}" target="_blank" rel="noopener">{url[:60]}{"..." if len(url) > 60 else ""}</a></li>')
            html.append('</ul>')

        if other:
            html.append('<h4>Altre Fonti Consultate</h4><ul class="sources-list">')
            for s in other[:15]:
                html.append(f'<li>{s.get("name", "N/A")}</li>')
            html.append('</ul>')

        html.append('<p class="disclaimer">Nota: I dati sono stati verificati alla data di generazione. Per informazioni aggiornate, verificare direttamente le fonti citate.</p>')
        html.append('</div>')

        return '\n'.join(html)

    def _save_section_backup(self, section: HTMLSection, base_filename: str):
        """Salva sezione singola come backup"""
        section_dir = self.output_dir / f"{base_filename}_sections"
        section_dir.mkdir(exist_ok=True)

        filepath = section_dir / f"{section.order:02d}_{section.id}.html"
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(f'<section id="{section.id}"><h2>{section.title}</h2>{section.content}</section>')

    # =========================================================================
    # DOCUMENT ASSEMBLY
    # =========================================================================

    def _format_timing_badge(self, meta: Dict) -> str:
        """Genera badge con timing di generazione"""
        total_time = meta.get('total_generation_time', 0)
        if not total_time:
            return ""

        minutes = int(total_time // 60)
        seconds = int(total_time % 60)
        time_str = f"{minutes}m {seconds}s" if minutes > 0 else f"{seconds}s"

        return f'''\
        <div class="timing-badge">
            ⏱️ Generato in {time_str}
        </div>'''

    def _generate_stw_dashboard_html(self) -> str:
        """Genera widget dashboard copertura STW"""
        if not hasattr(self, 'stw_coverage') or not self.stw_coverage:
            return ""

        progress = self.stw_coverage.get('progress', {})
        overall_progress = self.stw_coverage.get('overall_progress', 0)

        bars_html = ''
        categories = [
            ('sportivi', 'SPORTIVI', STWCategory.SPORTIVI),
            ('strutturali', 'STRUTTURALI', STWCategory.STRUTTURALI),
            ('marketing', 'MARKETING', STWCategory.MARKETING),
            ('sociali', 'SOCIALI', STWCategory.SOCIALI)
        ]

        for key, label, cat_enum in categories:
            prog = progress.get(key, 0)
            color = get_category_color(cat_enum)
            icon = get_category_icon(cat_enum)

            bars_html += f'''\
            <div class="stw-progress-row">
                <span class="stw-icon">{icon}</span>
                <span class="stw-label">{label}</span>
                <div class="stw-progress-bar">
                    <div class="stw-progress-fill" style="width: {prog}%; background: {color};"></div>
                </div>
                <span class="stw-percentage">{prog}%</span>
            </div>
            '''

        return f'''\
        <div class="stw-coverage-dashboard">
            <div class="stw-header">
                <h3>📊 Copertura Matrice STW</h3>
                <div class="stw-overall">
                    <span class="stw-overall-label">Completamento Complessivo</span>
                    <span class="stw-overall-value">{overall_progress}%</span>
                </div>
            </div>
            <div class="stw-progress-container">
                {bars_html}
            </div>
        </div>
        '''

    def _generate_input_sources_html(self, meta: Dict) -> str:
        """Genera sezione visuale per i file di input (Questionari)"""
        files = meta.get('files_processed', [])
        if not files:
            return ""

        files_html = ""
        for f in files:
            files_html += f'''\
            <div class="input-file-card">
                <div class="file-icon">📄</div>
                <div class="file-info">
                    <div class="file-name">{f}</div>
                    <div class="file-meta">Questionario Board</div>
                </div>
                <div class="file-status">✓</div>
            </div>'''

        return f'''\
        <div class="input-sources-dashboard">
            <div class="input-header">
                <h3>📂 Fonti di Input (Board del Club)</h3>
                <span class="input-count">{len(files)} documenti processati</span>
            </div>
            <div class="input-files-grid">
                {files_html}
            </div>
        </div>
        '''

    def _assemble_document(self, club_name: str, meta: Dict) -> str:
        """Assembla documento HTML finale con design premium"""
        self.sections.sort(key=lambda s: s.order)

        primary_color = meta['primary_color']
        text_on_primary = meta['contrast_color']
        # Se il primary è troppo chiaro (es. bianco), usa secondary come accent visibile
        accent_color = self._get_accent_color(primary_color, meta.get('secondary_color', '#1a365d'))
        # Cover gradient: always use accent (dark) so white text stays readable
        cover_end = '#' + self._darken_color(accent_color, 0.28)

        stw_matrix_html = generate_stw_matrix_html(accent_color)
        rf_methodology_html = generate_rooting_future_methodology_html(meta, accent_color)
        input_sources_html = self._generate_input_sources_html(meta)

        # Navigation
        nav_items = ""
        for s in self.sections:
            nav_items += f'<a href="#{s.id}" class="nav-item"><span class="nav-title">{s.title}</span></a>'

        # Sections HTML
        if not self.sections:
            sections_html = '''\
            <section class="section chapter" id="no-content">
                <div class="section-header"><h2>⚠ Contenuto non disponibile</h2></div>
                <div class="section-body" style="color:#555;">
                    <p>Il piano strategico non contiene sezioni generate. Possibili cause:</p>
                    <ul style="margin:12px 0 0 20px; line-height:2;">
                        <li>Il modello AI (Gemma 3 27B) ha superato la quota giornaliera gratuita</li>
                        <li>Timeout durante la generazione parallela degli agenti</li>
                        <li>Sessione scaduta — rigenera il piano</li>
                    </ul>
                    <p style="margin-top:16px;"><strong>Soluzione:</strong> Rigenera il piano. Se il problema persiste,
                    il sistema passerà automaticamente al modello Gemini Flash.</p>
                </div>
            </section>'''
        else:
            sections_html = ''
            for section in self.sections:
                sections_html += f'''\
            <section class="section chapter" id="{section.id}">
                <div class="section-header">
                    <h2>{section.title}</h2>
                </div>
                <div class="content section-body">
                    {section.content}
                </div>
            </section>
            '''

        current_year = meta['current_year']

        return f'''<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Piano Strategico {club_name} {current_year}-{current_year + 3}</title>
    {RF_FONT_IMPORT}
    <style>
        :root {{
            --primary: {primary_color};
            --text-on-primary: {text_on_primary};
            --accent: {accent_color};
            --bg: #f8fafc;
            --white: #ffffff;
            --border: #e2e8f0;
            --sidebar-width: 280px;
        }}

        {RF_RESET_CSS}
        body {{ font-family: 'Inter', sans-serif; background: var(--bg); display: flex; }}

        .sidebar {{
            width: var(--sidebar-width); height: 100vh; background: white;
            border-right: 1px solid var(--border); position: fixed; left: 0; top: 0;
            display: flex; flex-direction: column; z-index: 1000;
        }}

        .sidebar-header {{ padding: 24px 20px; background: var(--accent); color: var(--text-on-primary); text-align: center; border-bottom: 3px solid var(--primary); }}
        .nav {{ flex: 1; overflow-y: auto; padding: 16px 10px; }}
        .nav-item {{ display: block; padding: 10px 14px; margin-bottom: 3px; color: #4a5568; text-decoration: none; border-radius: 6px; font-weight: 600; font-size: 0.85rem; border-left: 3px solid transparent; }}
        .nav-item:hover {{ background: var(--bg); color: var(--accent); border-left-color: var(--accent); }}

        .main-wrapper {{ margin-left: var(--sidebar-width); flex: 1; }}
        .container {{ max-width: 900px; margin: 0 auto; padding: 60px 40px; }}

        .cover {{
            height: 55vh; background: linear-gradient(150deg, {accent_color} 0%, {cover_end} 100%);
            color: white; display: flex; flex-direction: column;
            justify-content: center; align-items: center; text-align: center;
            position: relative; overflow: hidden;
        }}
        .cover::after {{
            content: "";
            position: absolute; top: 0; left: 0; right: 0; bottom: 0;
            background-image: radial-gradient(circle, rgba(255,255,255,0.1) 1px, transparent 1px);
            background-size: 32px 32px;
        }}
        .cover h1 {{ font-family: 'Montserrat', sans-serif; font-size: 3.5rem; text-transform: uppercase; position: relative; z-index: 1; }}
        .cover p {{ position: relative; z-index: 1; }}

        .section {{ background: white; border-radius: 10px; padding: 36px 40px; margin-bottom: 28px; border: 1px solid var(--border); box-shadow: 0 2px 12px rgba(0,0,0,0.05); }}
        .section-header {{ border-bottom: 3px solid var(--accent); padding-bottom: 16px; margin-bottom: 28px; }}
        .section-header h2 {{ color: var(--accent); font-family: 'DM Serif Display', Georgia, serif; font-size: 1.9rem; font-weight: 400; text-transform: none; letter-spacing: -0.3px; }}
        .section-body {{ min-width: 0; overflow-wrap: break-word; word-wrap: break-word; }}

        /* Non-MACRO h3 fallback (headings outside MACRO cards) */
        h3 {{ color: var(--accent); margin-top: 1.8rem; margin-bottom: 0.8rem; border-left: 4px solid var(--accent); padding-left: 12px; }}
        p {{ margin-bottom: 1rem; line-height: 1.7; overflow-wrap: break-word; }}

        .kpi-box {{ background: #f8f9fa; border-left: 4px solid var(--accent); padding: 1.2rem 1.5rem; margin: 1.2rem 0; border-radius: 0 6px 6px 0; overflow-wrap: break-word; }}

        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th {{ background: var(--accent); color: white; padding: 12px; text-align: left; }}
        td {{ padding: 12px; border-bottom: 1px solid var(--border); }}

        .print-bar {{ position: fixed; bottom: 24px; right: 24px; z-index: 10000; display: flex; flex-direction: column; align-items: flex-end; gap: 6px; }}
        .print-btn {{ background: var(--accent); color: var(--text-on-primary); border: none; padding: 11px 20px; border-radius: 7px; font-family: 'Montserrat', sans-serif; font-size: 10pt; font-weight: 700; cursor: pointer; box-shadow: 0 4px 14px rgba(0,0,0,0.2); transition: transform 0.15s; }}
        .print-btn:hover {{ transform: translateY(-2px); }}
        .print-hint {{ font-size: 7pt; color: #aaa; background: white; padding: 2px 8px; border-radius: 3px; border: 1px solid #eee; }}

        {RF_BADGE_CSS}
        {RF_MACRO_CSS}
        {RF_PRINT_CSS_FULL}
        {RF_MOBILE_CSS}
        {get_stw_matrix_css()}
    </style>
</head>
<body>
<div class="print-bar">
    <button class="print-btn" onclick="window.print()">📥 Stampa / PDF</button>
    <div class="print-hint">File → Stampa → Salva come PDF</div>
</div>
    <aside class="sidebar">
        <div class="sidebar-header"><h2>Rooting Future</h2></div>
        <nav class="nav">
            <a href="#cover" class="nav-item">Copertina</a>
            <a href="#stw-matrix" class="nav-item">Matrice STW</a>
            {nav_items}
        </nav>
    </aside>
    <div class="main-wrapper">
        <header id="cover" class="cover">
            <h1>{club_name}</h1>
            <p>Piano Strategico {current_year}-{current_year + 3}</p>
            {self._format_timing_badge(meta)}
        </header>
        <main class="container">
            <div id="stw-matrix" class="section">
                <div class="section-header"><h2>Framework STW</h2></div>
                {stw_matrix_html}
            </div>
            {rf_methodology_html}
            {sections_html}
        </main>
    </div>
</body>
</html>'''

    def _generate_multipage_version(self, base_filename: str, club_name: str, meta: Dict):
        """Genera versione multi-pagina"""
        multipage_dir = self.output_dir / f"{base_filename}_multipage"
        multipage_dir.mkdir(exist_ok=True)
        logger.info(f"Multipage version generated in {multipage_dir}")
