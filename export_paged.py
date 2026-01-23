"""
Rooting Future Strategy Engine
Export HTML Print-First con Paged.js
"""

import re
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from export_core import BaseExporter
from stw_matrix import generate_stw_matrix_html, get_stw_matrix_css

logger = logging.getLogger(__name__)

class PagedHtmlExporter(BaseExporter):
    """
    Esporta piani strategici in HTML Print-First usando Paged.js.
    """

    def export(
        self,
        plan_data: Dict,
        club_name: str,
        sources: List[Dict] = None,
        metadata: Dict = None
    ) -> Path:
        """
        Genera documento HTML print-first.
        """
        meta = self._extract_metadata(metadata)
        
        # Genera HTML
        html = self._generate_html(
            plan_data=plan_data,
            club_name=club_name,
            sources=sources or [],
            meta=meta
        )

        # Salva
        filename = self._get_safe_filename(club_name, "html", prefix="PianoStrategico", suffix="print")
        filepath = self.output_dir / filename

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html)

        logger.info(f"Paged HTML exported: {filepath}")
        return filepath

    def _generate_html(
        self,
        plan_data: Dict,
        club_name: str,
        sources: List[Dict],
        meta: Dict
    ) -> str:
        """Genera l'HTML completo con Paged.js"""

        primary_color = meta['primary_color']
        secondary_color = meta['secondary_color']
        light_color = meta['light_color']
        contrast_color = meta['contrast_color']
        current_year = meta['current_year']
        generation_date = meta['generation_date']

        # Genera contenuto sezioni
        sections_html = self._generate_sections(plan_data, primary_color)
        sources_html = self._generate_sources(sources) if sources else ""

        html = f'''<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <title>Piano Strategico - {club_name}</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&family=Oswald:wght@400;500;600;700&display=swap" rel="stylesheet">
    <script src="https://unpkg.com/pagedjs/dist/paged.polyfill.js"></script>
    <style>
        :root {{
            --primary-color: {primary_color};
            --secondary-color: {secondary_color};
            --light-color: #{light_color};
            --contrast-color: {contrast_color};
            --text-color: #111111;
        }}

        @page {{
            size: A4;
            margin: 20mm;
            @bottom-left {{ content: "{club_name} // STRATEGY"; font-family: 'Oswald'; font-size: 8pt; }}
            @bottom-right {{ content: counter(page); font-family: 'Oswald'; font-weight: 700; color: var(--primary-color); }}
        }}

        body {{ font-family: 'Inter', sans-serif; font-size: 10pt; line-height: 1.6; }}
        h1 {{ font-family: 'Oswald'; font-size: 32pt; color: var(--primary-color); border-bottom: 4px solid var(--primary-color); page-break-before: always; }}
        h2 {{ font-family: 'Oswald'; font-size: 18pt; border-left: 6px solid var(--primary-color); padding-left: 10px; margin-top: 20px; }}
        
        .cover {{ height: 297mm; background: var(--primary-color); color: var(--contrast-color); padding: 40mm 20mm; page-break-after: always; }}
        .cover-club {{ font-family: 'Oswald'; font-size: 72pt; font-weight: 700; line-height: 0.85; }}
        
        .kpi-box {{ background: var(--light-color); border-left: 4px solid var(--primary-color); padding: 15px; margin: 15px 0; }}
        .badge {{ display: inline-block; padding: 2px 8px; border-radius: 10px; font-size: 8pt; font-weight: 700; }}
        .badge.questionnaire {{ background: #F3E5F5; color: #7B1FA2; }}
        .badge.research {{ background: #E3F2FD; color: #1565C0; }}
        .badge.estimate {{ background: #FFF3E0; color: #F57C00; }}

        {get_stw_matrix_css()}
    </style>
</head>
<body>
    <div class="cover">
        <div style="font-size: 12pt; letter-spacing: 5px;">ROOTING FUTURE</div>
        <div class="cover-club">{club_name}</div>
        <div style="font-size: 24pt; font-weight: 300; margin-top: 20px;">PIANO STRATEGICO<br>{current_year} — {current_year+3}</div>
    </div>

    {generate_stw_matrix_html(primary_color)}

    {sections_html}

    {sources_html}
</body>
</html>'''
        return html

    def _generate_sections(self, plan_data: Dict, primary_color: str) -> str:
        sections_config = self._get_preferred_section_order()
        section_titles = self._get_section_titles()
        html_parts = []
        
        for key in sections_config:
            content = plan_data.get(key, '')
            if content:
                title = section_titles.get(key, key)
                html_parts.append(f'<h1>{title}</h1>')
                normalized = self._normalize_markdown(content)
                html_parts.append(f'<div class="section-content">{self._markdown_to_html(normalized)}</div>')
        
        return '\n'.join(html_parts)

        def _generate_sources(self, sources: List[Dict]) -> str:
            html = ['<h1>Fonti e Metodologia</h1><ul>']
            for s in sources[:20]:
                html.append(f'<li><strong>{s.get("name", "Fonte")}</strong>: {s.get("url", "")}</li>')
            html.append('</ul>')
            return '\n'.join(html)
            # Alias for backward compatibility
        paged_exporter = PagedHtmlExporter()
        
        def create_paged_html(
            plan_data: Dict,
            club_name: str,
            sources: List[Dict] = None,
            metadata: Dict = None
        ) -> Path:
            """Helper function to create paged HTML."""
            return paged_exporter.export(plan_data, club_name, sources, metadata)
        