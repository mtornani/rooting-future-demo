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
from stw_analyzer import get_stw_coverage_summary
from stw_matrix import get_category_color, get_category_icon, STWCategory, generate_stw_matrix_html
from methodology_section import generate_rooting_future_methodology_html

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

    def _process_section_content(self, content: str) -> str:
        """Converte contenuto markdown-like in HTML usando BaseExporter logic"""
        if content is None:
            return "<p><em>Contenuto non disponibile</em></p>"
        
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
        
        stw_matrix_html = generate_stw_matrix_html(primary_color)
        rf_methodology_html = generate_rooting_future_methodology_html(meta, primary_color)
        input_sources_html = self._generate_input_sources_html(meta)

        # Navigation
        nav_items = ""
        for s in self.sections:
            nav_items += f'<a href="#{s.id}" class="nav-item"><span class="nav-title">{s.title}</span></a>'

        # Sections HTML
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
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&family=Montserrat:wght@700;800&display=swap" rel="stylesheet">
    <style>
        :root {{
            --primary: {primary_color};
            --text-on-primary: {text_on_primary};
            --bg: #f8fafc;
            --white: #ffffff;
            --border: #e2e8f0;
            --sidebar-width: 280px;
        }}

        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: 'Inter', sans-serif; background: var(--bg); display: flex; }}

        .sidebar {{ 
            width: var(--sidebar-width); height: 100vh; background: white;
            border-right: 1px solid var(--border); position: fixed; left: 0; top: 0;
            display: flex; flex-direction: column; z-index: 1000;
        }}

        .sidebar-header {{ padding: 30px 20px; background: var(--primary); color: var(--text-on-primary); text-align: center; }}
        .nav {{ flex: 1; overflow-y: auto; padding: 20px 10px; }}
        .nav-item {{ display: block; padding: 12px 15px; margin-bottom: 5px; color: #1a202c; text-decoration: none; border-radius: 8px; font-weight: 600; font-size: 0.9rem; }}
        .nav-item:hover {{ background: var(--bg); color: var(--primary); }}

        .main-wrapper {{ margin-left: var(--sidebar-width); flex: 1; }}
        .container {{ max-width: 900px; margin: 0 auto; padding: 60px 40px; }}

        .cover {{
            height: 60vh; background: linear-gradient(135deg, var(--primary) 0%, #1a202c 100%);
            color: var(--text-on-primary); display: flex; flex-direction: column;
            justify-content: center; align-items: center; text-align: center;
        }}
        .cover h1 {{ font-family: 'Montserrat', sans-serif; font-size: 4rem; text-transform: uppercase; }}

        .section {{ background: white; border-radius: 16px; padding: 50px; margin-bottom: 40px; border: 1px solid var(--border); }}
        .section-header {{ border-bottom: 4px solid var(--primary); padding-bottom: 20px; margin-bottom: 40px; }}
        .section-header h2 {{ color: var(--primary); font-family: 'Montserrat', sans-serif; font-size: 2.2rem; }}

        h3 {{ color: var(--primary); margin-top: 2rem; margin-bottom: 1rem; border-left: 5px solid var(--primary); padding-left: 15px; }}
        p {{ margin-bottom: 1.2rem; text-align: justify; }}
        
        .kpi-box {{ background: #f0f9ff; border-left: 4px solid var(--primary); padding: 1.5rem; margin: 1.5rem 0; border-radius: 0 8px 8px 0; }}
        .badge {{ display: inline-block; padding: 3px 10px; border-radius: 12px; font-size: 0.7rem; font-weight: 700; text-transform: uppercase; margin-right: 5px; }}
        .badge.questionnaire {{ background: #7B1FA2; color: white; }}
        .badge.research {{ background: #1565C0; color: white; }}
        .badge.estimate {{ background: #F57C00; color: white; }}

        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th {{ background: var(--primary); color: var(--text-on-primary); padding: 12px; text-align: left; }}
        td {{ padding: 12px; border-bottom: 1px solid var(--border); }}

        @media print {{ .sidebar {{ display: none; }} .main-wrapper {{ margin-left: 0; }} }}
    </style>
</head>
<body>
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
