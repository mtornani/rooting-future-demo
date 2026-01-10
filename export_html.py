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

    def _generate_input_sources_html(self, metadata: Dict) -> str:
        """Genera sezione visuale per i file di input (Questionari)"""
        files = metadata.get('files_processed', [])
        if not files:
            return ""

        files_html = ""
        for f in files:
            files_html += f'''
            <div class="input-file-card">
                <div class="file-icon">📄</div>
                <div class="file-info">
                    <div class="file-name">{f}</div>
                    <div class="file-meta">Questionario Board</div>
                </div>
                <div class="file-status">✓</div>
            </div>'''

        return f'''
        <div class="input-sources-dashboard">
            <div class="input-header">
                <h3>📂 Fonti di Input (Board del Club)</h3>
                <span class="input-count">{len(files)} documenti processati</span>
            </div>
            <div class="input-files-grid">
                {files_html}
            </div>
            <p class="input-note">
                <em>Il presente piano strategico è stato elaborato analizzando i questionari compilati direttamente dal board del club.</em>
            </p>
        </div>
        '''

    def _assemble_document(self, club_name: str, metadata: Dict = None) -> str:
        """Assembla documento HTML finale con design premium"""

        # Ordina sezioni
        self.sections.sort(key=lambda s: s.order)

        # Navigation
        nav_items = ''.join([
            f'<a href="#{s.id}" class="nav-item">{s.title}</a>'
            for s in self.sections
        ])

        # STW Dashboard (Matrice STW completa)
        stw_matrix_html = generate_stw_matrix_html(metadata.get('primary_color', '#1a365d') if metadata else '#1a365d')

        # RF Methodology Section
        primary_color = metadata.get('primary_color', '#1a365d') if metadata else '#1a365d'
        rf_methodology_html = generate_rooting_future_methodology_html(metadata, primary_color)

        # Input Sources Section (NEW)
        input_sources_html = self._generate_input_sources_html(metadata) if metadata else ""

        # Sezioni HTML
        sections_html = ''
        for section in self.sections:
            sections_html += f'''
            <section class="section chapter" id="{section.id}">
                <div class="section-header">
                    <h2>{section.title}</h2>
                </div>
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
    <style>
        :root {{
            --primary: {primary_color};
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

        @page {{
            size: A4;
            margin: 20mm;
            @bottom-center {{
                content: "Pagina " counter(page);
                font-size: 9pt;
                color: #718096;
            }}
        }}

        @page :first {{
            margin: 0;
            @bottom-center {{ content: none; }}
        }}

        * {{ margin: 0; padding: 0; box-sizing: border-box; }}

        body {{
            font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
            line-height: 1.6;
            color: var(--text);
            background: var(--bg);
        }}

        /* COVER PAGE */
        .cover {{
            height: 100vh;
            background: linear-gradient(135deg, var(--primary) 0%, #1a202c 100%);
            color: white;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            text-align: center;
            page-break-after: always;
            position: relative;
            overflow: hidden;
        }}

        .cover::before {{
            content: "";
            position: absolute;
            top: 0; left: 0; right: 0; bottom: 0;
            background: url('https://www.transparenttextures.com/patterns/cubes.png');
            opacity: 0.1;
        }}

        .cover h1 {{
            font-size: 3.5rem;
            font-weight: 800;
            margin-bottom: 1rem;
            text-transform: uppercase;
            letter-spacing: 2px;
            z-index: 1;
        }}

        .cover .subtitle {{
            font-size: 1.5rem;
            opacity: 0.9;
            font-weight: 300;
            z-index: 1;
        }}

        .cover .meta-box {{
            margin-top: 3rem;
            padding: 1rem 2rem;
            background: rgba(255,255,255,0.1);
            border-radius: 50px;
            backdrop-filter: blur(10px);
            z-index: 1;
        }}

        /* NAVIGATION (Screen only) */
        .nav {{
            background: white;
            padding: 1rem;
            position: sticky;
            top: 0;
            z-index: 100;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            overflow-x: auto;
            white-space: nowrap;
        }}

        .nav-item {{
            display: inline-block;
            padding: 0.5rem 1rem;
            margin-right: 0.5rem;
            color: var(--text);
            text-decoration: none;
            border-radius: 6px;
            font-size: 0.9rem;
            transition: all 0.2s;
        }}

        .nav-item:hover {{ background: var(--bg); color: var(--primary); }}

        /* MAIN LAYOUT */
        .container {{
            max-width: 1000px;
            margin: 0 auto;
            padding: 40px 20px;
        }}

        /* SECTIONS */
        .section {{
            background: white;
            border-radius: 12px;
            padding: 40px;
            margin-bottom: 40px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.05);
            page-break-inside: avoid;
        }}

        .section.chapter {{
            page-break-before: always;
        }}

        .section-header {{
            border-bottom: 3px solid var(--primary);
            padding-bottom: 15px;
            margin-bottom: 30px;
        }}

        .section h2 {{
            color: var(--primary);
            font-size: 2rem;
            font-weight: 700;
        }}

        /* TYPOGRAPHY */
        h3 {{
            color: var(--secondary);
            font-size: 1.4rem;
            margin: 2rem 0 1rem;
            border-left: 4px solid var(--accent);
            padding-left: 1rem;
        }}

        h4 {{
            color: var(--text);
            font-size: 1.1rem;
            font-weight: 600;
            margin: 1.5rem 0 0.8rem;
        }}

        p {{ margin-bottom: 1rem; text-align: justify; }}

        ul, ol {{ margin: 1rem 0 1rem 2rem; }}
        li {{ margin-bottom: 0.5rem; }}

        /* CARDS & BOXES */
        .kpi-box {{
            background: #f0f9ff;
            border-left: 4px solid var(--accent);
            padding: 1.5rem;
            border-radius: 0 8px 8px 0;
            margin: 1.5rem 0;
        }}

        blockquote {{
            font-style: italic;
            color: var(--text-light);
            border-left: 3px solid #cbd5e0;
            padding-left: 1rem;
            margin: 1.5rem 0;
        }}

        /* INPUT SOURCES STYLES */
        .input-sources-dashboard {{
            background: white;
            border-radius: 12px;
            padding: 30px;
            margin-bottom: 40px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        }}

        .input-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            border-bottom: 1px solid var(--border);
            padding-bottom: 10px;
        }}

        .input-files-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
            gap: 15px;
            margin-bottom: 15px;
        }}

        .input-file-card {{
            display: flex;
            align-items: center;
            padding: 12px;
            background: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
        }}

        .file-icon {{ font-size: 1.5rem; margin-right: 12px; }}
        .file-info {{ flex: 1; }}
        .file-name {{ font-weight: 600; font-size: 0.9rem; color: var(--text); }}
        .file-meta {{ font-size: 0.75rem; color: var(--text-light); }}
        .file-status {{ color: var(--success); font-weight: bold; }}

        /* STW MATRIX STYLES (Injected via get_stw_matrix_css if needed, but we used inline styles mostly) */
        
        /* PRINT OPTIMIZATIONS */
        @media print {{
            .nav {{ display: none; }}
            body {{ background: white; }}
            .container {{ max-width: 100%; padding: 0; }}
            .section {{ box-shadow: none; border: none; padding: 0; margin-bottom: 20px; }}
            .cover {{ background: var(--primary) !important; -webkit-print-color-adjust: exact; }}
        }}
    </style>
</head>
<body>

    <!-- COVER PAGE -->
    <div class="cover">
        <h1>{club_name}</h1>
        <div class="subtitle">Piano Strategico {current_year}-{current_year + 3}</div>
        <div class="meta-box">
            {category} | {region}
        </div>
        {self._format_timing_badge(metadata)}
    </div>

    <!-- NAVIGATION (Screen only) -->
    <nav class="nav">
        {nav_items}
    </nav>

    <main class="container">
        <!-- INPUT SOURCES -->
        {input_sources_html}

        <!-- STW MATRIX -->
        {stw_matrix_html}

        <!-- METHODOLOGY -->
        {rf_methodology_html}

        <!-- SECTIONS -->
        {sections_html}
    </main>

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
