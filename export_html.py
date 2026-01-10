"""
Rooting Future Strategy Engine v5.4
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

from config import OUTPUT_DIR, EXPORT_CONFIG
from stw_analyzer import get_stw_coverage_summary
from stw_matrix import get_category_color, get_category_icon, STWCategory
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

class ChunkedHTMLExporter:
    """
    Genera HTML in modo incrementale per evitare troncamenti.
    Strategia: genera sezione per sezione, poi assembla.
    """

    def __init__(self):
        OUTPUT_DIR.mkdir(exist_ok=True)
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

        Args:
            plan_data: Dict con sezioni del piano
            club_name: Nome del club
            sources: Lista fonti
            metadata: Metadati

        Returns:
            Path file HTML generato
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = re.sub(r'[^\w\s-]', '', club_name).strip().replace(' ', '_')
        base_filename = f"{safe_name}_{timestamp}"

        self.sections = []

        # Calcola copertura STW
        self.stw_coverage = get_stw_coverage_summary(plan_data)

        # 1. Genera sezioni
        section_configs = [
            ('executive_summary', 'Executive Summary', 0),
            ('technical_sporting', 'Area Tecnico-Sportiva', 1),
            ('youth_development', 'Sviluppo Settore Giovanile', 2),
            ('infrastructure', 'Infrastrutture', 3),
            ('marketing_commercial', 'Marketing e Commerciale', 4),
            ('social_sustainability', 'Sostenibilità Sociale', 5),
            ('governance', 'Governance e Organizzazione', 6),
            ('financial', 'Piano Economico-Finanziario', 7),
        ]

        for key, title, order in section_configs:
            if key in plan_data and plan_data[key]:
                section = HTMLSection(
                    id=key,
                    title=title,
                    content=self._process_section_content(plan_data[key]),
                    order=order
                )
                self.sections.append(section)

                # Salva sezione intermedia (backup)
                self._save_section_backup(section, base_filename)

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
        final_html = self._assemble_document(club_name, metadata)

        # 4. Salva
        filepath = OUTPUT_DIR / f"{base_filename}.html"
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(final_html)

        logger.info(f"HTML exported: {filepath}")

        # 5. Genera versione multi-pagina se necessario
        if len(self.sections) > EXPORT_CONFIG.generate_multipage_threshold:
            self._generate_multipage_version(base_filename, club_name, metadata)

        return filepath

    # =========================================================================
    # PROCESSING
    # =========================================================================

    def _normalize_markdown(self, content: str) -> str:
        """
        Pre-processa il contenuto per normalizzare il markdown.
        Gli agenti AI spesso generano contenuto senza newline appropriate.
        """
        # Normalizza newline esistenti
        content = content.replace('\r\n', '\n')

        # TABELLE: Separa le righe delle tabelle markdown che sono su una sola linea
        # Pattern: | cell | cell | | cell | cell | -> separa con newline
        content = re.sub(r'\|\s+\|', '|\n|', content)

        # Pattern: ### 1. TITOLO -> converte in header h3 seguito dal titolo (rimuove il numero)
        content = re.sub(r'###\s+\d+[\.\)]\s*', '\n\n### ', content)

        # Pattern: ## 1. TITOLO -> converte in header h2 seguito dal titolo
        content = re.sub(r'##\s+\d+[\.\)]\s*', '\n\n## ', content)

        # Aggiungi newline PRIMA di ogni occorrenza di ## o ### nel testo
        # Questo cattura anche i casi dove ## appare dopo testo senza newline
        content = re.sub(r'([a-zA-Z0-9.,;:!?)\]])\s*(#{2,4})\s+', r'\1\n\n\2 ', content)

        # Pattern: #### seguito da numero come 1.1 -> header h4
        content = re.sub(r'####\s+(\d+\.\d+)\s*', r'\n\n#### ', content)

        # Aggiungi newline prima di bullet points (* o -) che seguono testo
        # Ma solo se seguiti da testo o bold
        content = re.sub(r'([^\n\*\-])\s+(\*\s+\*\*)', r'\1\n\2', content)
        content = re.sub(r'([^\n])\s+(\-\s+\*\*)', r'\1\n\2', content)
        content = re.sub(r'([^\n])\s+(\*\s+[A-Z])', r'\1\n\2', content)
        content = re.sub(r'([^\n])\s+(\-\s+[A-Z])', r'\1\n\2', content)

        # Aggiungi newline prima delle tabelle (linee che iniziano con |)
        content = re.sub(r'([^\n\|])\s+(\|[^\n]+\|)', r'\1\n\n\2', content)

        # Normalizza multiple newline consecutive (max 2)
        content = re.sub(r'\n{3,}', '\n\n', content)

        # Assicurati che ci siano newline dopo paragrafi che finiscono con :
        # e sono seguiti da bullet points
        content = re.sub(r'(:\s*)(\*\s+\*\*)', r':\n\2', content)

        return content.strip()

    def _process_section_content(self, content: str) -> str:
        """Converte contenuto markdown-like in HTML con parsing robusto"""
        # Gestisci None
        if content is None:
            return "<p><em>Contenuto non disponibile</em></p>"

        html_parts = []

        # STEP 1: Pre-processing - aggiungi newline prima dei marker markdown
        # Questo è cruciale perché gli agenti AI spesso generano contenuto senza newline
        content = self._normalize_markdown(content)

        # Normalizza le newline e splitta per linee
        lines = content.replace('\r\n', '\n').split('\n')

        i = 0
        current_list_type = None  # 'ul' o 'ol'
        list_items = []

        while i < len(lines):
            line = lines[i].strip()

            # Skip linee vuote
            if not line:
                # Chiudi lista aperta se presente
                if current_list_type:
                    html_parts.append(f'<{current_list_type}>')
                    html_parts.extend([f'<li>{item}</li>' for item in list_items])
                    html_parts.append(f'</{current_list_type}>')
                    current_list_type = None
                    list_items = []
                i += 1
                continue

            # Headers (## e ###)
            if line.startswith('### '):
                if current_list_type:
                    html_parts.append(f'<{current_list_type}>')
                    html_parts.extend([f'<li>{item}</li>' for item in list_items])
                    html_parts.append(f'</{current_list_type}>')
                    current_list_type = None
                    list_items = []
                html_parts.append(f'<h4>{self._escape_html(line[4:])}</h4>')
                i += 1
                continue
            elif line.startswith('## '):
                if current_list_type:
                    html_parts.append(f'<{current_list_type}>')
                    html_parts.extend([f'<li>{item}</li>' for item in list_items])
                    html_parts.append(f'</{current_list_type}>')
                    current_list_type = None
                    list_items = []
                html_parts.append(f'<h3>{self._escape_html(line[3:])}</h3>')
                i += 1
                continue
            elif line.startswith('# '):
                if current_list_type:
                    html_parts.append(f'<{current_list_type}>')
                    html_parts.extend([f'<li>{item}</li>' for item in list_items])
                    html_parts.append(f'</{current_list_type}>')
                    current_list_type = None
                    list_items = []
                html_parts.append(f'<h3>{self._escape_html(line[2:])}</h3>')
                i += 1
                continue

            # Tabelle markdown (raccogli tutte le righe della tabella)
            if '|' in line and line.count('|') >= 2:
                if current_list_type:
                    html_parts.append(f'<{current_list_type}>')
                    html_parts.extend([f'<li>{item}</li>' for item in list_items])
                    html_parts.append(f'</{current_list_type}>')
                    current_list_type = None
                    list_items = []

                table_lines = [line]
                i += 1
                while i < len(lines) and '|' in lines[i]:
                    table_lines.append(lines[i].strip())
                    i += 1
                html_parts.append(self._markdown_table_to_html('\n'.join(table_lines)))
                continue

            # Bullet lists
            if line.startswith('- ') or line.startswith('* '):
                if current_list_type == 'ol':
                    html_parts.append('<ol>')
                    html_parts.extend([f'<li>{item}</li>' for item in list_items])
                    html_parts.append('</ol>')
                    list_items = []
                current_list_type = 'ul'
                list_items.append(self._format_inline(line[2:]))
                i += 1
                continue

            # Numbered lists
            if line and line[0].isdigit():
                match = None
                for j, c in enumerate(line[:5]):
                    if c in '.):':
                        match = j
                        break
                if match is not None:
                    if current_list_type == 'ul':
                        html_parts.append('<ul>')
                        html_parts.extend([f'<li>{item}</li>' for item in list_items])
                        html_parts.append('</ul>')
                        list_items = []
                    current_list_type = 'ol'
                    list_items.append(self._format_inline(line[match + 1:].strip()))
                    i += 1
                    continue

            # Chiudi lista se non siamo più in una lista
            if current_list_type:
                html_parts.append(f'<{current_list_type}>')
                html_parts.extend([f'<li>{item}</li>' for item in list_items])
                html_parts.append(f'</{current_list_type}>')
                current_list_type = None
                list_items = []

            # KPI boxes
            if any(kw in line for kw in ['KPI:', 'Target:', 'Obiettivo:', 'Indicatore:']):
                html_parts.append(f'<div class="kpi-box">{self._format_inline(line)}</div>')
                i += 1
                continue

            # Quote
            if line.startswith('> '):
                html_parts.append(f'<blockquote>{self._format_inline(line[2:])}</blockquote>')
                i += 1
                continue

            # Raccomandazioni/Note box
            if line.startswith('**Raccomandazione') or line.startswith('**Nota') or line.startswith('**RACCOMANDAZIONE'):
                html_parts.append(f'<div class="kpi-box">{self._format_inline(line)}</div>')
                i += 1
                continue

            # Paragrafo normale - raccoglie linee consecutive non vuote
            para_lines = [line]
            i += 1
            while i < len(lines):
                next_line = lines[i].strip()
                # Stop se linea vuota, header, lista, tabella
                if (not next_line or
                    next_line.startswith('#') or
                    next_line.startswith('- ') or
                    next_line.startswith('* ') or
                    (next_line and next_line[0].isdigit() and len(next_line) > 1 and next_line[1] in '.):') or
                    ('|' in next_line and next_line.count('|') >= 2)):
                    break
                para_lines.append(next_line)
                i += 1

            para_text = ' '.join(para_lines)
            if para_text:
                html_parts.append(f'<p>{self._format_inline(para_text)}</p>')

        # Chiudi lista finale se presente
        if current_list_type:
            html_parts.append(f'<{current_list_type}>')
            html_parts.extend([f'<li>{item}</li>' for item in list_items])
            html_parts.append(f'</{current_list_type}>')

        return '\n'.join(html_parts)

    def _escape_html(self, text: str) -> str:
        """Escape caratteri HTML"""
        return (text
                .replace('&', '&amp;')
                .replace('<', '&lt;')
                .replace('>', '&gt;')
                .replace('"', '&quot;'))

    def _format_inline(self, text: str) -> str:
        """Formatta bold, italic, etc."""
        # Escape HTML first
        text = self._escape_html(text)

        # Bold **text**
        text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
        # Italic *text*
        text = re.sub(r'\*([^\*]+?)\*', r'<em>\1</em>', text)

        # Stilizza pattern speciali
        # (dato da acquisire), (stima interna), etc.
        text = re.sub(
            r'\((dato da acquisire|stima interna|da verificare|da definire)\)',
            r'<span class="data-pending">(\1)</span>',
            text,
            flags=re.IGNORECASE
        )

        # Fonte: xyz
        text = re.sub(
            r'\(fonte:\s*([^)]+)\)',
            r'<span class="source-ref">(fonte: \1)</span>',
            text,
            flags=re.IGNORECASE
        )

        return text

    def _markdown_table_to_html(self, md_table: str) -> str:
        """Converte tabella markdown in HTML"""
        lines = [l.strip() for l in md_table.split('\n') if l.strip()]

        # Filtra righe separatore (contengono solo -, :, |, spazi)
        # e righe che iniziano con :--- (alignment indicators)
        def is_separator_row(line):
            # Rimuovi i pipe e controlla se rimane solo -, :, spazi
            cleaned = line.replace('|', '').strip()
            return all(c in '-: ' for c in cleaned) and len(cleaned) > 0

        lines = [l for l in lines if not is_separator_row(l)]

        if not lines:
            return ''

        html = ['<div class="table-wrapper"><table>']

        header_added = False
        for i, line in enumerate(lines):
            cells = [c.strip() for c in line.split('|')]
            # Rimuovi celle vuote ai bordi
            cells = [c for c in cells if c]

            if not cells:
                continue

            if i == 0 and not header_added:
                html.append('<thead><tr>')
                for cell in cells:
                    # Non processare celle che sembrano separatori
                    if not all(c in '-: ' for c in cell):
                        html.append(f'<th>{self._format_inline(cell)}</th>')
                html.append('</tr></thead><tbody>')
                header_added = True
            else:
                html.append('<tr>')
                for cell in cells:
                    if not all(c in '-: ' for c in cell):
                        html.append(f'<td>{self._format_inline(cell)}</td>')
                html.append('</tr>')

        html.append('</tbody></table></div>')
        return '\n'.join(html)

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
        section_dir = OUTPUT_DIR / f"{base_filename}_sections"
        section_dir.mkdir(exist_ok=True)

        filepath = section_dir / f"{section.order:02d}_{section.id}.html"
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(f'<section id="{section.id}"><h2>{section.title}</h2>{section.content}</section>')

    # =========================================================================
    # DOCUMENT ASSEMBLY
    # =========================================================================

    def _format_timing_badge(self, metadata: Dict) -> str:
        """Genera badge con timing di generazione"""
        if not metadata:
            return ""

        total_time = metadata.get('total_generation_time')
        if not total_time:
            return ""

        # Format total time
        minutes = int(total_time // 60)
        seconds = int(total_time % 60)
        time_str = f"{minutes}m {seconds}s" if minutes > 0 else f"{seconds}s"

        # Get detailed timings
        phase_timings = metadata.get('phase_timings', {})
        agent_timings = metadata.get('agent_timings', {})

        timing_html = f'''
        <div class="timing-badge" title="Clicca per dettagli">
            ⏱️ Generato in {time_str}
        </div>'''

        # Add breakdown if available
        if phase_timings or agent_timings:
            breakdown_lines = []

            if phase_timings.get('web_research'):
                breakdown_lines.append(f"🔍 Ricerca Web: {phase_timings['web_research']}s")

            if agent_timings:
                breakdown_lines.append(f"🤖 AI Multi-Agente: {metadata.get('total_generation_time', 0) - phase_timings.get('web_research', 0):.1f}s")
                for agent_name, agent_time in list(agent_timings.items())[:5]:  # Top 5 agents
                    breakdown_lines.append(f"   ├─ {agent_name}: {agent_time}s")

            if breakdown_lines:
                timing_html += f'''
        <div class="timing-details">
            Breakdown:<br>
            {" • ".join(breakdown_lines)}
        </div>'''

        return timing_html

    def _generate_stw_dashboard_html(self) -> str:
        """Genera widget dashboard copertura STW"""
        if not hasattr(self, 'stw_coverage') or not self.stw_coverage:
            return ""

        progress = self.stw_coverage.get('progress', {})
        overall_progress = self.stw_coverage.get('overall_progress', 0)

        # Progress bars per categoria
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

            bars_html += f'''
            <div class="stw-progress-row">
                <span class="stw-icon">{icon}</span>
                <span class="stw-label">{label}</span>
                <div class="stw-progress-bar">
                    <div class="stw-progress-fill" style="width: {prog}%; background: {color};"></div>
                </div>
                <span class="stw-percentage">{prog}%</span>
            </div>
            '''

        return f'''
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
            <p class="stw-note">
                <em>La copertura STW indica la percentuale di obiettivi MACRO e MICRO presenti nel piano rispetto al framework completo Sport To Win.</em>
            </p>
        </div>
        '''

    def _assemble_document(self, club_name: str, metadata: Dict = None) -> str:
        """Assembla documento HTML finale"""

        # Ordina sezioni
        self.sections.sort(key=lambda s: s.order)

        # Navigation
        nav_items = ''.join([
            f'<a href="#{s.id}" class="nav-item">{s.title}</a>'
            for s in self.sections
        ])

        # STW Dashboard
        stw_dashboard_html = self._generate_stw_dashboard_html()

        # RF Methodology Section
        primary_color = metadata.get('primary_color', '#1a365d') if metadata else '#1a365d'
        rf_methodology_html = generate_rooting_future_methodology_html(metadata, primary_color)

        # Sezioni HTML
        sections_html = ''
        for section in self.sections:
            sections_html += f'''
            <section class="section" id="{section.id}">
                <h2>{section.title}</h2>
                <div class="content">
                    {section.content}
                </div>
            </section>
            '''

        # Metadata
        category = metadata.get('category', '') if metadata else ''
        region = metadata.get('region', '') if metadata else ''
        credibility = metadata.get('credibility_score', 0) if metadata else 0

        current_year = datetime.now().year

        return f'''<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Piano Strategico {club_name} {current_year}-{current_year + 3}</title>
    <meta name="description" content="Piano Strategico {club_name} - Rooting Future Strategy Engine">
    <style>
        :root {{
            --primary: #1a365d;
            --secondary: #2c5282;
            --accent: #3182ce;
            --text: #2d3748;
            --text-light: #718096;
            --bg: #f7fafc;
            --white: #ffffff;
            --success: #38a169;
            --warning: #d69e2e;
            --border: #e2e8f0;
        }}

        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        html {{
            scroll-behavior: smooth;
        }}

        body {{
            font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
            line-height: 1.7;
            color: var(--text);
            background: var(--bg);
        }}

        /* Header */
        .header {{
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            color: var(--white);
            padding: 60px 40px;
            text-align: center;
            position: relative;
        }}

        .header::after {{
            content: '';
            position: absolute;
            bottom: 0;
            left: 0;
            right: 0;
            height: 4px;
            background: var(--accent);
        }}

        .header h1 {{
            font-size: 2.5rem;
            font-weight: 700;
            margin-bottom: 10px;
            letter-spacing: -0.5px;
        }}

        .header .subtitle {{
            font-size: 1.2rem;
            opacity: 0.9;
        }}

        .header .meta {{
            margin-top: 15px;
            font-size: 0.9rem;
            opacity: 0.8;
        }}

        .timing-badge {{
            display: inline-block;
            margin-top: 15px;
            padding: 8px 16px;
            background: rgba(255, 255, 255, 0.15);
            border-radius: 20px;
            font-size: 0.85rem;
            font-weight: 500;
            backdrop-filter: blur(10px);
            cursor: help;
        }}

        .timing-badge:hover {{
            background: rgba(255, 255, 255, 0.25);
        }}

        .timing-details {{
            margin-top: 8px;
            font-size: 0.75rem;
            opacity: 0.7;
            display: none;
        }}

        .timing-badge:hover + .timing-details {{
            display: block;
        }}

        /* Questionnaire Badge */
        .badge-questionnaire {{
            background: linear-gradient(135deg, #7B1FA2, #9C27B0);
            color: white;
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 0.75rem;
            font-weight: 600;
            display: inline-flex;
            align-items: center;
            gap: 4px;
            margin-left: 8px;
            vertical-align: middle;
        }}

        /* Navigation */
        .nav {{
            background: var(--white);
            padding: 15px 20px;
            position: sticky;
            top: 0;
            z-index: 100;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            overflow-x: auto;
            white-space: nowrap;
        }}

        .nav-item {{
            display: inline-block;
            padding: 8px 16px;
            margin-right: 8px;
            color: var(--secondary);
            text-decoration: none;
            border-radius: 6px;
            font-size: 0.9rem;
            transition: all 0.2s ease;
        }}

        .nav-item:hover {{
            background: var(--bg);
            color: var(--primary);
        }}

        .nav-item.active {{
            background: var(--accent);
            color: var(--white);
        }}

        /* Container */
        .container {{
            max-width: 1000px;
            margin: 0 auto;
            padding: 40px 20px;
        }}

        /* Sections */
        .section {{
            background: var(--white);
            border-radius: 12px;
            padding: 40px;
            margin-bottom: 30px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.05);
            border: 1px solid var(--border);
        }}

        .section h2 {{
            color: var(--primary);
            font-size: 1.8rem;
            margin-bottom: 20px;
            padding-bottom: 15px;
            border-bottom: 3px solid var(--accent);
        }}

        .section h3 {{
            color: var(--secondary);
            font-size: 1.3rem;
            margin: 30px 0 15px;
            padding-top: 20px;
            border-top: 1px solid var(--border);
        }}

        .section h3:first-of-type {{
            border-top: none;
            padding-top: 0;
        }}

        .section h4 {{
            color: var(--secondary);
            font-size: 1.1rem;
            margin: 25px 0 12px;
        }}

        .section p {{
            margin-bottom: 16px;
            text-align: justify;
        }}

        .section ul, .section ol {{
            margin: 16px 0 16px 30px;
        }}

        .section li {{
            margin-bottom: 10px;
        }}

        /* Tables */
        .table-wrapper {{
            overflow-x: auto;
            margin: 20px 0;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 0.95rem;
        }}

        th, td {{
            padding: 14px 16px;
            text-align: left;
            border-bottom: 1px solid var(--border);
        }}

        th {{
            background: var(--primary);
            color: var(--white);
            font-weight: 600;
            text-transform: uppercase;
            font-size: 0.85rem;
            letter-spacing: 0.5px;
        }}

        tr:nth-child(even) {{
            background: #f8fafc;
        }}

        tr:hover {{
            background: #edf2f7;
        }}

        /* KPI Box */
        .kpi-box {{
            background: linear-gradient(135deg, #ebf8ff, #e6fffa);
            border-left: 4px solid var(--accent);
            padding: 20px 25px;
            margin: 25px 0;
            border-radius: 0 8px 8px 0;
        }}

        .kpi-box strong {{
            color: var(--primary);
        }}

        /* Info boxes per vari tipi di contenuto */
        .info-box {{
            background: #f0f9ff;
            border: 1px solid #bae6fd;
            border-radius: 8px;
            padding: 16px 20px;
            margin: 16px 0;
        }}

        .warning-box {{
            background: #fffbeb;
            border: 1px solid #fcd34d;
            border-left: 4px solid var(--warning);
            border-radius: 0 8px 8px 0;
            padding: 16px 20px;
            margin: 16px 0;
        }}

        .success-box {{
            background: #f0fdf4;
            border: 1px solid #86efac;
            border-left: 4px solid var(--success);
            border-radius: 0 8px 8px 0;
            padding: 16px 20px;
            margin: 16px 0;
        }}

        /* Dato da acquisire styling */
        .section p {{
            margin-bottom: 16px;
            text-align: justify;
            line-height: 1.8;
        }}

        /* Stile per (dato da acquisire) */
        .content em {{
            color: var(--text-light);
            font-style: italic;
        }}

        /* Enfasi su keyword importanti */
        .content strong {{
            color: var(--primary);
            font-weight: 600;
        }}

        /* Sub-sections più chiare */
        .section h4 {{
            color: var(--secondary);
            font-size: 1.1rem;
            margin: 25px 0 12px;
            padding-left: 12px;
            border-left: 3px solid var(--accent);
        }}

        /* Liste migliorate */
        .section ul {{
            list-style: none;
            margin: 16px 0;
            padding: 0;
        }}

        .section ul li {{
            padding: 8px 0 8px 28px;
            position: relative;
            border-bottom: 1px solid #f1f5f9;
        }}

        .section ul li:last-child {{
            border-bottom: none;
        }}

        .section ul li::before {{
            content: '→';
            position: absolute;
            left: 0;
            color: var(--accent);
            font-weight: bold;
        }}

        .section ol {{
            margin: 16px 0 16px 24px;
            padding: 0;
        }}

        .section ol li {{
            padding: 8px 0;
            padding-left: 8px;
        }}

        /* Data pending e source refs */
        .data-pending {{
            background: #fef3c7;
            color: #92400e;
            padding: 2px 6px;
            border-radius: 4px;
            font-size: 0.9em;
            font-style: italic;
        }}

        .source-ref {{
            background: #dbeafe;
            color: #1e40af;
            padding: 2px 6px;
            border-radius: 4px;
            font-size: 0.85em;
        }}

        /* Blockquote */
        blockquote {{
            border-left: 4px solid var(--accent);
            padding: 15px 20px;
            margin: 20px 0;
            background: #f8fafc;
            font-style: italic;
            color: var(--secondary);
        }}

        /* Sources */
        .sources-section {{
            background: #f8fafc;
            padding: 25px;
            border-radius: 8px;
        }}

        .sources-intro {{
            margin-bottom: 20px;
            color: var(--text-light);
        }}

        .sources-list {{
            margin: 15px 0 15px 25px;
        }}

        .sources-list li {{
            margin-bottom: 8px;
        }}

        .sources-list a {{
            color: var(--accent);
            word-break: break-all;
            text-decoration: none;
        }}

        .sources-list a:hover {{
            text-decoration: underline;
        }}

        .sources-list.trusted li::marker {{
            color: var(--success);
        }}

        .disclaimer {{
            font-size: 0.85rem;
            color: var(--text-light);
            font-style: italic;
            margin-top: 25px;
            padding-top: 20px;
            border-top: 1px solid var(--border);
        }}

        /* Footer */
        .footer {{
            text-align: center;
            padding: 40px 20px;
            color: var(--text-light);
            font-size: 0.9rem;
            border-top: 1px solid var(--border);
            margin-top: 40px;
            background: var(--white);
        }}

        .footer .brand {{
            color: var(--accent);
            font-weight: 600;
        }}

        /* Credibility Badge */
        .credibility-badge {{
            display: inline-block;
            padding: 8px 16px;
            border-radius: 20px;
            font-size: 0.85rem;
            font-weight: 600;
            margin-top: 15px;
        }}

        .credibility-high {{
            background: #c6f6d5;
            color: #22543d;
        }}

        .credibility-medium {{
            background: #fefcbf;
            color: #744210;
        }}

        .credibility-low {{
            background: #fed7d7;
            color: #742a2a;
        }}

        /* Print styles */
        /* ================================================================
           PRINT STYLES - Ottimizzato per stampa professionale
           ================================================================ */
        @media print {{
            /* === NASCONDI ELEMENTI UI INTERATTIVI === */
            .print-bar, 
            .nav,
            .modal,
            .expand-hint,
            .click-hint,
            .card-click-hint,
            .card-expand-icon,
            button,
            .btn {{
                display: none !important;
            }}

            /* === IMPOSTAZIONI GLOBALI === */
            * {{
                -webkit-print-color-adjust: exact !important;
                print-color-adjust: exact !important;
            }}

            body {{
                background: white !important;
                color: #000 !important;
                font-size: 11pt !important;
                line-height: 1.5 !important;
                orphans: 4;
                widows: 4;
            }}

            /* === HEADER CLUB === */
            .header {{
                margin-top: 0 !important;
                padding: 30px 20px !important;
                break-after: avoid;
                page-break-after: avoid;
            }}

            /* === SEZIONI === */
            .section {{
                box-shadow: none !important;
                border: 1px solid #ccc !important;
                border-radius: 4px !important;
                margin-bottom: 20px !important;
            }}

            /* Header sezione NON deve restare solo a fine pagina */
            .section-header {{
                break-after: avoid !important;
                page-break-after: avoid !important;
            }}

            /* Ogni sezione principale inizia su nuova pagina (opzionale) */
            .section.page-break-before {{
                break-before: page;
                page-break-before: always;
            }}

            /* === TITOLI - Mai soli a fine pagina === */
            h1, h2, h3, h4, h5, h6 {{
                break-after: avoid !important;
                page-break-after: avoid !important;
                orphans: 3;
                widows: 3;
            }}

            /* === PARAGRAFI === */
            p {{
                orphans: 3;
                widows: 3;
            }}

            /* === LISTE === */
            ul, ol {{
                orphans: 2;
                widows: 2;
            }}

            li {{
                break-inside: avoid !important;
                page-break-inside: avoid !important;
            }}

            /* === TABELLE - Mai tagliate === */
            table {{
                break-inside: avoid !important;
                page-break-inside: avoid !important;
                border-collapse: collapse !important;
            }}

            th {{
                background-color: var(--primary) !important;
                color: white !important;
            }}

            tr {{
                break-inside: avoid !important;
                page-break-inside: avoid !important;
            }}

            /* === BOX E CARD - Mai tagliate === */
            .kpi-box, 
            .alert, 
            .highlight-box,
            .area-card,
            .area-box,
            .chart-box,
            .method-box {{
                break-inside: avoid !important;
                page-break-inside: avoid !important;
                box-shadow: none !important;
            }}

            /* === IMMAGINI E GRAFICI === */
            img, 
            svg,
            .chart-container {{
                break-inside: avoid !important;
                page-break-inside: avoid !important;
                max-width: 100% !important;
            }}

            /* === CONTAINER === */
            .container {{
                padding: 15px !important;
                max-width: none !important;
            }}

            /* === FOOTER === */
            .footer {{
                margin-top: 30px !important;
                padding-top: 15px !important;
                border-top: 1px solid #ccc !important;
            }}

            /* === LINK - Mostra URL === */
            a[href]:after {{
                content: none !important; /* Disabilita per evitare clutter */
            }}

            /* === REGOLA @PAGE === */
            @page {{
                size: A4;
                margin: 1.5cm;
            }}

            @page :first {{
                margin-top: 0;
            }}
        }}

        /* Tablet (portrait and landscape) */
        @media (max-width: 1024px) {{
            .stw-progress-row {{
                grid-template-columns: 25px 120px 1fr 55px;
                gap: 12px;
            }}
            .stw-overall-value {{
                font-size: 1.8rem;
            }}
        }}

        /* Tablet (portrait) and Mobile (landscape) */
        @media (max-width: 768px) {{
            .header {{
                padding: 40px 20px;
            }}
            .header h1 {{
                font-size: 1.8rem;
            }}
            .section {{
                padding: 25px 20px;
            }}
            .container {{
                padding: 20px 15px;
            }}
            table {{
                font-size: 0.85rem;
                display: block;
                overflow-x: auto;
            }}
            th, td {{
                padding: 8px 10px;
            }}
            .stw-coverage-dashboard {{
                padding: 20px 15px;
            }}
            .stw-progress-row {{
                grid-template-columns: 25px 100px 1fr 50px;
                gap: 8px;
            }}
            .stw-overall-value {{
                font-size: 1.5rem;
            }}
        }}

        /* Mobile (portrait) */
        @media (max-width: 480px) {{
            .header h1 {{
                font-size: 1.5rem;
            }}
            .header .subtitle {{
                font-size: 1rem;
            }}
            .section {{
                padding: 20px 15px;
            }}
            .stw-coverage-dashboard {{
                padding: 15px 10px;
            }}
            .stw-progress-row {{
                grid-template-columns: 20px 80px 1fr 45px;
                gap: 6px;
            }}
            .stw-label {{
                font-size: 0.75rem;
            }}
            .stw-percentage {{
                font-size: 0.8rem;
            }}
            .stw-overall-value {{
                font-size: 1.3rem;
            }}
            table {{
                font-size: 0.75rem;
            }}
            th, td {{
                padding: 6px 8px;
            }}
        }}

        /* ============================================
           STW COVERAGE DASHBOARD
           ============================================ */
        .stw-coverage-dashboard {{
            max-width: 1200px;
            margin: 30px auto;
            padding: 25px 30px;
            background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
        }}

        .stw-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            padding-bottom: 15px;
            border-bottom: 2px solid var(--border);
        }}

        .stw-header h3 {{
            margin: 0;
            font-size: 1.4rem;
            color: var(--primary);
        }}

        .stw-overall {{
            display: flex;
            flex-direction: column;
            align-items: flex-end;
        }}

        .stw-overall-label {{
            font-size: 0.9rem;
            color: var(--text-light);
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}

        .stw-overall-value {{
            font-size: 2rem;
            font-weight: 700;
            color: var(--success);
        }}

        .stw-progress-container {{
            display: grid;
            grid-template-columns: 1fr;
            gap: 15px;
            margin-bottom: 15px;
        }}

        .stw-progress-row {{
            display: grid;
            grid-template-columns: 30px 150px 1fr 60px;
            align-items: center;
            gap: 15px;
            padding: 10px;
            background: white;
            border-radius: 8px;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
        }}

        .stw-icon {{
            font-size: 1.5rem;
            text-align: center;
        }}

        .stw-label {{
            font-weight: 600;
            font-size: 0.9rem;
            color: var(--text);
        }}

        .stw-progress-bar {{
            height: 24px;
            background: #e9ecef;
            border-radius: 12px;
            overflow: hidden;
            position: relative;
        }}

        .stw-progress-fill {{
            height: 100%;
            transition: width 0.6s ease;
            border-radius: 12px;
            position: relative;
            background: linear-gradient(90deg, currentColor 0%, currentColor 80%, rgba(255,255,255,0.2) 100%);
        }}

        .stw-percentage {{
            font-weight: 700;
            font-size: 0.95rem;
            color: var(--text);
            text-align: right;
        }}

        .stw-note {{
            margin-top: 15px;
            padding: 12px;
            background: rgba(255, 255, 255, 0.7);
            border-left: 4px solid var(--accent);
            border-radius: 4px;
            font-size: 0.85rem;
            color: var(--text-light);
            line-height: 1.5;
        }}

        @media print {{
            .stw-coverage-dashboard {{
                page-break-inside: avoid;
                background: #f8f9fa !important;
                box-shadow: none !important;
            }}
        }}
    </style>
</head>
<body>
    <header class="header">
        <h1>Piano Strategico {club_name}</h1>
        <p class="subtitle">{current_year} — {current_year + 3}</p>
        <p class="meta">{category}{" | " + region if region else ""}</p>
        {f'<span class="credibility-badge credibility-{"high" if credibility >= 70 else "medium" if credibility >= 50 else "low"}">Credibilità dati: {credibility}%</span>' if credibility else ''}
        {self._format_timing_badge(metadata)}
    </header>

    <nav class="nav">
        {nav_items}
    </nav>

    {stw_dashboard_html}

    {rf_methodology_html}

    <main class="container">
        {sections_html}
    </main>

    <footer class="footer">
        <p>Documento generato da <span class="brand">Rooting Future Strategy Engine</span> v5.4</p>
        <p style="margin-top: 8px;">© {current_year} - Tutti i diritti riservati</p>
        <p style="margin-top: 12px; font-size: 0.8rem; color: #a0aec0;">
            Generato il {datetime.now().strftime('%d/%m/%Y alle %H:%M')}
        </p>
    </footer>

    <script>
        // Smooth scroll per navigation
        document.querySelectorAll('.nav-item').forEach(link => {{
            link.addEventListener('click', (e) => {{
                e.preventDefault();
                const target = document.querySelector(link.getAttribute('href'));
                if (target) {{
                    const navHeight = document.querySelector('.nav').offsetHeight;
                    window.scrollTo({{
                        top: target.offsetTop - navHeight - 20,
                        behavior: 'smooth'
                    }});
                }}
            }});
        }});

        // Active nav item on scroll
        const sections = document.querySelectorAll('.section');
        const navItems = document.querySelectorAll('.nav-item');
        const nav = document.querySelector('.nav');

        function updateActiveNav() {{
            const navHeight = nav.offsetHeight;
            let current = '';

            sections.forEach(section => {{
                const top = section.offsetTop - navHeight - 100;
                if (window.scrollY >= top) {{
                    current = section.getAttribute('id');
                }}
            }});

            navItems.forEach(item => {{
                item.classList.remove('active');
                if (item.getAttribute('href') === '#' + current) {{
                    item.classList.add('active');
                }}
            }});
        }}

        window.addEventListener('scroll', updateActiveNav);
        updateActiveNav();

        // Print button (optional)
        function printDocument() {{
            window.print();
        }}
    </script>
</body>
</html>'''

    def _generate_multipage_version(self, base_filename: str, club_name: str, metadata: Dict = None):
        """Genera versione multi-pagina per documenti lunghi"""
        multipage_dir = OUTPUT_DIR / f"{base_filename}_multipage"
        multipage_dir.mkdir(exist_ok=True)

        # Index page
        index_content = self._generate_index_page(club_name, metadata)
        with open(multipage_dir / 'index.html', 'w', encoding='utf-8') as f:
            f.write(index_content)

        # Section pages
        for i, section in enumerate(self.sections):
            prev_section = self.sections[i - 1] if i > 0 else None
            next_section = self.sections[i + 1] if i < len(self.sections) - 1 else None

            section_html = self._generate_section_page(section, club_name, prev_section, next_section)
            with open(multipage_dir / f'{section.id}.html', 'w', encoding='utf-8') as f:
                f.write(section_html)

        logger.info(f"Multipage version generated: {multipage_dir}")

    def _generate_index_page(self, club_name: str, metadata: Dict = None) -> str:
        """Genera pagina indice per versione multi-pagina"""
        current_year = datetime.now().year

        links = ''.join([
            f'''<a href="{s.id}.html" class="section-link">
                <span class="num">{s.order + 1}</span>
                <span class="title">{s.title}</span>
                <span class="arrow">→</span>
            </a>'''
            for s in self.sections
        ])

        return f'''<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Piano Strategico {club_name} - Indice</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Segoe UI', system-ui, sans-serif;
            background: linear-gradient(135deg, #1a365d 0%, #2c5282 100%);
            min-height: 100vh;
            padding: 40px 20px;
        }}
        .container {{
            max-width: 700px;
            margin: 0 auto;
        }}
        .header {{
            text-align: center;
            color: white;
            margin-bottom: 40px;
        }}
        .header h1 {{
            font-size: 2rem;
            margin-bottom: 10px;
        }}
        .header p {{
            opacity: 0.8;
        }}
        .section-link {{
            display: flex;
            align-items: center;
            padding: 20px 25px;
            background: white;
            margin-bottom: 12px;
            border-radius: 10px;
            text-decoration: none;
            color: #2d3748;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
            transition: all 0.3s ease;
        }}
        .section-link:hover {{
            transform: translateX(8px);
            box-shadow: 0 6px 20px rgba(0,0,0,0.15);
        }}
        .num {{
            width: 40px;
            height: 40px;
            background: #3182ce;
            color: white;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            margin-right: 18px;
            font-weight: bold;
            font-size: 1.1rem;
        }}
        .title {{
            flex: 1;
            font-size: 1.1rem;
            font-weight: 500;
        }}
        .arrow {{
            color: #3182ce;
            font-size: 1.2rem;
        }}
        .footer {{
            text-align: center;
            color: rgba(255,255,255,0.7);
            margin-top: 40px;
            font-size: 0.9rem;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Piano Strategico</h1>
            <p>{club_name} | {current_year}-{current_year + 3}</p>
        </div>
        {links}
        <div class="footer">
            <p>Rooting Future Strategy Engine v5.4</p>
        </div>
    </div>
</body>
</html>'''

    def _generate_section_page(
        self,
        section: HTMLSection,
        club_name: str,
        prev_section: Optional[HTMLSection],
        next_section: Optional[HTMLSection]
    ) -> str:
        """Genera pagina singola sezione"""
        prev_link = f'<a href="{prev_section.id}.html" class="nav-link prev">← {prev_section.title}</a>' if prev_section else '<span></span>'
        next_link = f'<a href="{next_section.id}.html" class="nav-link next">{next_section.title} →</a>' if next_section else '<span></span>'

        return f'''<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{section.title} | Piano Strategico {club_name}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Segoe UI', system-ui, sans-serif;
            background: #f7fafc;
            line-height: 1.7;
            color: #2d3748;
        }}
        .top-nav {{
            background: #1a365d;
            padding: 15px 25px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .top-nav a {{
            color: white;
            text-decoration: none;
            font-size: 0.95rem;
        }}
        .top-nav a:hover {{
            text-decoration: underline;
        }}
        .top-nav .club-name {{
            color: rgba(255,255,255,0.7);
        }}
        .container {{
            max-width: 900px;
            margin: 40px auto;
            padding: 0 20px;
        }}
        .section {{
            background: white;
            padding: 45px;
            border-radius: 12px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        }}
        .section h1 {{
            color: #1a365d;
            font-size: 2rem;
            border-bottom: 3px solid #3182ce;
            padding-bottom: 15px;
            margin-bottom: 30px;
        }}
        .section h3 {{
            color: #2c5282;
            font-size: 1.25rem;
            margin: 30px 0 15px;
        }}
        .section h4 {{
            color: #2c5282;
            font-size: 1.1rem;
            margin: 25px 0 12px;
        }}
        .section p {{
            margin-bottom: 16px;
            text-align: justify;
        }}
        .section ul, .section ol {{
            margin: 16px 0 16px 30px;
        }}
        .section li {{
            margin-bottom: 10px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}
        th, td {{
            padding: 12px 15px;
            text-align: left;
            border-bottom: 1px solid #e2e8f0;
        }}
        th {{
            background: #1a365d;
            color: white;
        }}
        .kpi-box {{
            background: #e6fffa;
            border-left: 4px solid #3182ce;
            padding: 20px;
            margin: 20px 0;
            border-radius: 0 8px 8px 0;
        }}
        blockquote {{
            border-left: 4px solid #3182ce;
            padding: 15px 20px;
            margin: 20px 0;
            background: #f8fafc;
            font-style: italic;
        }}
        .page-nav {{
            display: flex;
            justify-content: space-between;
            margin-top: 40px;
            padding-top: 25px;
            border-top: 1px solid #e2e8f0;
        }}
        .nav-link {{
            color: #3182ce;
            text-decoration: none;
            font-weight: 500;
        }}
        .nav-link:hover {{
            text-decoration: underline;
        }}
    </style>
</head>
<body>
    <nav class="top-nav">
        <a href="index.html">← Indice</a>
        <span class="club-name">{club_name}</span>
    </nav>
    <main class="container">
        <article class="section">
            <h1>{section.title}</h1>
            {section.content}
            <div class="page-nav">
                {prev_link}
                {next_link}
            </div>
        </article>
    </main>
</body>
</html>'''
