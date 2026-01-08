"""
Rooting Future Strategy Engine v5.4
Professional DOCX Export Module

Genera documenti Word di qualità consulenziale (stile Deloitte/McKinsey/BCG).
Formattazione professionale con:
- Copertina elegante
- Indice navigabile
- Header/footer con numerazione
- Tabelle formattate
- Box KPI evidenziati
- Sezione fonti strutturata
"""

import os
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import logging

try:
    from docx import Document
    from docx.shared import Inches, Pt, Cm, RGBColor, Twips
    from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
    from docx.enum.table import WD_TABLE_ALIGNMENT
    from docx.enum.style import WD_STYLE_TYPE
    from docx.enum.section import WD_ORIENT
    from docx.oxml.ns import qn
    from docx.oxml import OxmlElement
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False

from config import OUTPUT_DIR, EXPORT_CONFIG

logger = logging.getLogger(__name__)


# =============================================================================
# COLORI BRAND
# =============================================================================

from docx.shared import RGBColor


def hex_to_rgb(hex_color: str) -> tuple:
    """Converte colore hex in tupla RGB."""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


def hex_to_RGBColor(hex_color: str) -> RGBColor:
    """Converte colore hex in RGBColor per python-docx."""
    r, g, b = hex_to_rgb(hex_color)
    return RGBColor(r, g, b)


def get_contrast_color(hex_color: str) -> str:
    """Restituisce bianco o nero in base al contrasto."""
    r, g, b = hex_to_rgb(hex_color)
    luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
    return '#ffffff' if luminance < 0.5 else '#1a202c'


def darken_color(hex_color: str, factor: float = 0.2) -> str:
    """Scurisce un colore."""
    r, g, b = hex_to_rgb(hex_color)
    r = int(r * (1 - factor))
    g = int(g * (1 - factor))
    b = int(b * (1 - factor))
    return f'{r:02x}{g:02x}{b:02x}'


def lighten_color(hex_color: str, factor: float = 0.85) -> str:
    """Schiarisce un colore (per sfondi)."""
    r, g, b = hex_to_rgb(hex_color)
    r = min(255, int(r + (255 - r) * factor))
    g = min(255, int(g + (255 - g) * factor))
    b = min(255, int(b + (255 - b) * factor))
    return f'{r:02x}{g:02x}{b:02x}'


class BrandColors:
    """
    Palette colori professionale.
    Può essere personalizzata con i colori del club.
    """
    # Default colors
    PRIMARY = RGBColor(26, 54, 93)       # #1a365d - Blu scuro
    SECONDARY = RGBColor(44, 82, 130)    # #2c5282 - Blu medio
    ACCENT = RGBColor(49, 130, 206)      # #3182ce - Blu accent
    TEXT = RGBColor(45, 55, 72)          # #2d3748 - Grigio scuro
    LIGHT_TEXT = RGBColor(113, 128, 150) # #718096 - Grigio chiaro
    SUCCESS = RGBColor(56, 161, 105)     # #38a169 - Verde
    WARNING = RGBColor(214, 158, 46)     # #d69e2e - Giallo
    LIGHT_BG = RGBColor(247, 250, 252)   # #f7fafc - Sfondo chiaro
    WHITE = RGBColor(255, 255, 255)

    # Hex versions for cell shading
    PRIMARY_HEX = "1a365d"
    SECONDARY_HEX = "2c5282"
    LIGHT_BG_HEX = "f7fafc"
    ACCENT_HEX = "3182ce"

    @classmethod
    def from_club_colors(cls, primary_color: str = None, secondary_color: str = None):
        """
        Crea una palette personalizzata basata sui colori del club.

        Args:
            primary_color: Colore primario del club (hex, es. '#AC1A2F')
            secondary_color: Colore secondario del club (hex, es. '#000000')

        Returns:
            Classe BrandColors configurata
        """
        if primary_color:
            cls.PRIMARY = hex_to_RGBColor(primary_color)
            cls.PRIMARY_HEX = primary_color.lstrip('#')
            cls.SECONDARY = hex_to_RGBColor(darken_color(primary_color, 0.15))
            cls.SECONDARY_HEX = darken_color(primary_color, 0.15)
            cls.ACCENT = hex_to_RGBColor(primary_color)
            cls.ACCENT_HEX = primary_color.lstrip('#')
            cls.LIGHT_BG_HEX = lighten_color(primary_color, 0.92)

        if secondary_color:
            # Il secondario può essere usato per header text contrast
            pass

        return cls


# =============================================================================
# PROFESSIONAL DOCX EXPORTER
# =============================================================================

class ProfessionalDocxExporter:
    """
    Esporta piani strategici in formato DOCX professionale.
    Qualità consulenza Big4 (Deloitte, KPMG, PwC, EY).
    """

    def __init__(self):
        if not DOCX_AVAILABLE:
            raise ImportError("python-docx not installed. Run: pip install python-docx")

        OUTPUT_DIR.mkdir(exist_ok=True)
        self._output_dir = OUTPUT_DIR
        self.doc = None
        self.toc_entries: List[Tuple[str, int]] = []
        self.current_page = 1

    @property
    def output_dir(self):
        return self._output_dir

    @output_dir.setter
    def output_dir(self, value):
        self._output_dir = Path(value) if value else OUTPUT_DIR

    def create_document(
        self,
        plan_data: Dict,
        club_name: str,
        sources: List[Dict] = None,
        metadata: Dict = None
    ) -> Path:
        """
        Crea documento DOCX professionale completo.

        Args:
            plan_data: Dict con sezioni del piano
            club_name: Nome del club
            sources: Lista fonti utilizzate
            metadata: Metadati aggiuntivi (include primary_color, secondary_color)

        Returns:
            Path del file generato
        """
        self.doc = Document()
        self.toc_entries = []

        # Applica colori del club se disponibili (guerrilla marketing)
        if metadata:
            primary_color = metadata.get('primary_color')
            secondary_color = metadata.get('secondary_color')
            if primary_color:
                BrandColors.from_club_colors(primary_color, secondary_color)
                logger.info(f"DOCX: Applicati colori club {primary_color}")

        # Setup documento
        self._setup_styles()
        self._setup_page_layout()

        # 1. Copertina
        self._add_cover_page(club_name, metadata)

        # 2. Indice
        self._add_table_of_contents(plan_data)

        # 3. Executive Summary
        if 'executive_summary' in plan_data:
            self._add_section("Executive Summary", plan_data['executive_summary'], level=1, number="1")

        # 4. Sezioni principali
        section_config = [
            ('technical_sporting', 'Area Tecnico-Sportiva', '2'),
            ('youth_development', 'Sviluppo Settore Giovanile', '3'),
            ('infrastructure', 'Infrastrutture', '4'),
            ('marketing_commercial', 'Marketing e Commerciale', '5'),
            ('social_sustainability', 'Sostenibilità Sociale', '6'),
            ('governance', 'Governance e Organizzazione', '7'),
            ('financial', 'Piano Economico-Finanziario', '8'),
        ]

        for key, title, number in section_config:
            if key in plan_data and plan_data[key]:
                self._add_section(title, plan_data[key], level=1, number=number)

        # 5. Appendice Fonti
        if sources:
            self._add_sources_appendix(sources)

        # 6. Disclaimer finale
        self._add_disclaimer()

        # 7. Footer con numerazione
        self._add_header_footer(club_name)

        # Salva
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = re.sub(r'[^\w\s-]', '', club_name).strip().replace(' ', '_')
        filename = f"{safe_name}_PianoStrategico_{timestamp}.docx"
        filepath = self._output_dir / filename

        self.doc.save(str(filepath))
        logger.info(f"DOCX exported: {filepath}")

        return filepath

    # =========================================================================
    # SETUP
    # =========================================================================

    def _setup_styles(self):
        """Configura stili documento"""
        styles = self.doc.styles

        # Heading 1 - Titoli sezione principali
        h1 = styles['Heading 1']
        h1.font.name = EXPORT_CONFIG.heading_font
        h1.font.size = Pt(EXPORT_CONFIG.heading1_size)
        h1.font.bold = True
        h1.font.color.rgb = BrandColors.PRIMARY
        h1.paragraph_format.space_before = Pt(24)
        h1.paragraph_format.space_after = Pt(16)
        h1.paragraph_format.keep_with_next = True
        h1.paragraph_format.page_break_before = True

        # Heading 2 - Sottosezioni
        h2 = styles['Heading 2']
        h2.font.name = EXPORT_CONFIG.heading_font
        h2.font.size = Pt(EXPORT_CONFIG.heading2_size)
        h2.font.bold = True
        h2.font.color.rgb = BrandColors.SECONDARY
        h2.paragraph_format.space_before = Pt(18)
        h2.paragraph_format.space_after = Pt(10)
        h2.paragraph_format.keep_with_next = True

        # Heading 3
        h3 = styles['Heading 3']
        h3.font.name = EXPORT_CONFIG.heading_font
        h3.font.size = Pt(14)
        h3.font.bold = True
        h3.font.color.rgb = BrandColors.SECONDARY
        h3.paragraph_format.space_before = Pt(14)
        h3.paragraph_format.space_after = Pt(8)

        # Normal - Corpo testo
        normal = styles['Normal']
        normal.font.name = EXPORT_CONFIG.body_font
        normal.font.size = Pt(EXPORT_CONFIG.body_size)
        normal.font.color.rgb = BrandColors.TEXT
        normal.paragraph_format.space_after = Pt(8)
        normal.paragraph_format.line_spacing_rule = WD_LINE_SPACING.MULTIPLE
        normal.paragraph_format.line_spacing = 1.15

        # Quote - Per highlight/citazioni
        try:
            quote = styles.add_style('CustomQuote', WD_STYLE_TYPE.PARAGRAPH)
        except ValueError:
            quote = styles['CustomQuote']

        quote.font.name = EXPORT_CONFIG.body_font
        quote.font.size = Pt(EXPORT_CONFIG.body_size)
        quote.font.italic = True
        quote.font.color.rgb = BrandColors.SECONDARY
        quote.paragraph_format.left_indent = Cm(1)
        quote.paragraph_format.right_indent = Cm(1)
        quote.paragraph_format.space_before = Pt(12)
        quote.paragraph_format.space_after = Pt(12)

    def _setup_page_layout(self):
        """Configura layout pagina A4"""
        section = self.doc.sections[0]
        section.page_width = Cm(21)
        section.page_height = Cm(29.7)
        section.left_margin = Cm(2.5)
        section.right_margin = Cm(2.5)
        section.top_margin = Cm(2.5)
        section.bottom_margin = Cm(2)
        section.header_distance = Cm(1.25)
        section.footer_distance = Cm(1)

    # =========================================================================
    # COPERTINA
    # =========================================================================

    def _add_cover_page(self, club_name: str, metadata: Dict = None):
        """Aggiunge copertina professionale"""
        # Spazio superiore
        for _ in range(6):
            self.doc.add_paragraph()

        # Logo/Brand
        logo_para = self.doc.add_paragraph()
        logo_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = logo_para.add_run("ROOTING FUTURE")
        run.font.size = Pt(16)
        run.font.bold = True
        run.font.color.rgb = BrandColors.ACCENT
        run.font.name = EXPORT_CONFIG.heading_font

        # Sottotitolo brand
        sub = self.doc.add_paragraph()
        sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = sub.add_run("Strategy Engine")
        run.font.size = Pt(12)
        run.font.color.rgb = BrandColors.LIGHT_TEXT

        # Spazio
        for _ in range(3):
            self.doc.add_paragraph()

        # Linea decorativa superiore
        line = self.doc.add_paragraph()
        line.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = line.add_run("━" * 50)
        run.font.color.rgb = BrandColors.ACCENT
        run.font.size = Pt(8)

        self.doc.add_paragraph()

        # Titolo principale
        title = self.doc.add_paragraph()
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = title.add_run("PIANO STRATEGICO")
        run.font.size = Pt(36)
        run.font.bold = True
        run.font.color.rgb = BrandColors.PRIMARY
        run.font.name = EXPORT_CONFIG.heading_font

        # Nome club
        club_para = self.doc.add_paragraph()
        club_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = club_para.add_run(club_name.upper())
        run.font.size = Pt(28)
        run.font.bold = True
        run.font.color.rgb = BrandColors.SECONDARY
        run.font.name = EXPORT_CONFIG.heading_font

        self.doc.add_paragraph()

        # Periodo
        period = self.doc.add_paragraph()
        period.alignment = WD_ALIGN_PARAGRAPH.CENTER
        current_year = datetime.now().year
        run = period.add_run(f"{current_year} — {current_year + 3}")
        run.font.size = Pt(20)
        run.font.color.rgb = BrandColors.TEXT

        # Spazio
        for _ in range(4):
            self.doc.add_paragraph()

        # Linea decorativa inferiore
        line = self.doc.add_paragraph()
        line.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = line.add_run("━" * 50)
        run.font.color.rgb = BrandColors.ACCENT
        run.font.size = Pt(8)

        # Spazio
        for _ in range(2):
            self.doc.add_paragraph()

        # Metadati
        if metadata:
            category = metadata.get('category', '')
            region = metadata.get('region', '')
            if category or region:
                meta_para = self.doc.add_paragraph()
                meta_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
                text = f"{category}" + (f" | {region}" if region else "")
                run = meta_para.add_run(text)
                run.font.size = Pt(12)
                run.font.color.rgb = BrandColors.LIGHT_TEXT

        # Data generazione
        self.doc.add_paragraph()
        date_para = self.doc.add_paragraph()
        date_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        months_it = ["Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno",
                     "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre"]
        now = datetime.now()
        date_str = f"{now.day} {months_it[now.month - 1]} {now.year}"
        run = date_para.add_run(f"Documento generato: {date_str}")
        run.font.size = Pt(10)
        run.font.color.rgb = BrandColors.LIGHT_TEXT

        # Confidenzialità
        conf = self.doc.add_paragraph()
        conf.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = conf.add_run("CONFIDENZIALE - Solo per uso interno")
        run.font.size = Pt(9)
        run.font.italic = True
        run.font.color.rgb = BrandColors.LIGHT_TEXT

        # Page break
        self.doc.add_page_break()

    # =========================================================================
    # INDICE
    # =========================================================================

    def _add_table_of_contents(self, plan_data: Dict):
        """Aggiunge indice manuale"""
        # Titolo
        toc_title = self.doc.add_paragraph()
        run = toc_title.add_run("Indice")
        run.font.size = Pt(24)
        run.font.bold = True
        run.font.color.rgb = BrandColors.PRIMARY

        self.doc.add_paragraph()

        # Voci indice
        toc_items = [
            ("1.", "Executive Summary"),
            ("2.", "Area Tecnico-Sportiva"),
            ("3.", "Sviluppo Settore Giovanile"),
            ("4.", "Infrastrutture"),
            ("5.", "Marketing e Commerciale"),
            ("6.", "Sostenibilità Sociale"),
            ("7.", "Governance e Organizzazione"),
            ("8.", "Piano Economico-Finanziario"),
            ("", "Appendice: Fonti e Riferimenti"),
        ]

        for num, title in toc_items:
            para = self.doc.add_paragraph()
            para.paragraph_format.space_after = Pt(6)

            # Numero
            if num:
                run = para.add_run(f"{num} ")
                run.font.bold = True
                run.font.color.rgb = BrandColors.PRIMARY

            # Titolo
            run = para.add_run(title)
            run.font.color.rgb = BrandColors.TEXT

            # Tab leader (dots) - simulato
            run = para.add_run(" " + "." * 60)
            run.font.color.rgb = BrandColors.LIGHT_TEXT
            run.font.size = Pt(8)

        self.doc.add_page_break()

    # =========================================================================
    # SEZIONI CONTENUTO
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

    def _add_section(
        self,
        title: str,
        content: str,
        level: int = 1,
        number: str = ""
    ):
        """
        Aggiunge sezione con formattazione professionale.
        Processa markdown-like content.
        """
        # Heading
        heading_text = f"{number}. {title}" if number else title
        self.doc.add_heading(heading_text, level=level)
        self.toc_entries.append((title, level))

        # Pre-processa il contenuto per normalizzare il markdown
        content = self._normalize_markdown(content)

        # Processa contenuto - prima splitta per doppio newline, poi per singolo
        # per gestire i blocchi misti
        lines = content.split('\n')

        i = 0
        while i < len(lines):
            line = lines[i].strip()

            if not line:
                i += 1
                continue

            # Heading 1 (# )
            if line.startswith('# ') and not line.startswith('## '):
                self.doc.add_heading(line[2:], level=2)  # h2 in DOCX (h1 è il titolo sezione)
                i += 1
                continue

            # Heading 2 (##)
            if line.startswith('## '):
                self.doc.add_heading(line[3:], level=2)
                i += 1
                continue

            # Heading 3 (###)
            if line.startswith('### '):
                self.doc.add_heading(line[4:], level=3)
                i += 1
                continue

            # Heading 4 (####)
            if line.startswith('#### '):
                p = self.doc.add_paragraph()
                run = p.add_run(line[5:])
                run.bold = True
                run.font.color.rgb = BrandColors.SECONDARY
                i += 1
                continue

            # Tabella markdown (raccogli tutte le righe della tabella)
            if '|' in line and line.count('|') >= 2:
                table_lines = [line]
                i += 1
                while i < len(lines) and '|' in lines[i]:
                    table_lines.append(lines[i].strip())
                    i += 1
                self._add_table_from_markdown('\n'.join(table_lines))
                continue

            # Bullet list (raccogli tutte le righe della lista)
            if line.startswith('- ') or line.startswith('* '):
                list_lines = [line]
                i += 1
                while i < len(lines) and (lines[i].strip().startswith('- ') or lines[i].strip().startswith('* ')):
                    list_lines.append(lines[i].strip())
                    i += 1
                self._add_bullet_list('\n'.join(list_lines))
                continue

            # Numbered list (raccogli tutte le righe della lista)
            if line and line[0].isdigit() and len(line) > 1 and any(line[j] in '.):' for j in range(1, min(4, len(line)))):
                list_lines = [line]
                i += 1
                while i < len(lines):
                    next_line = lines[i].strip()
                    if next_line and next_line[0].isdigit() and len(next_line) > 1 and any(next_line[j] in '.):' for j in range(1, min(4, len(next_line)))):
                        list_lines.append(next_line)
                        i += 1
                    else:
                        break
                self._add_numbered_list('\n'.join(list_lines))
                continue

            # KPI box
            if any(kw in line for kw in ['KPI:', 'Target:', 'Obiettivo:', 'Indicatore:']):
                self._add_kpi_box(line)
                i += 1
                continue

            # Quote (>)
            if line.startswith('> '):
                self._add_quote(line[2:])
                i += 1
                continue

            # Raccomandazioni box
            if line.startswith('**Raccomandazione') or line.startswith('**RACCOMANDAZIONE') or line.startswith('**Nota'):
                self._add_kpi_box(line)
                i += 1
                continue

            # Paragrafo normale - raccoglie linee consecutive non-speciali
            para_lines = [line]
            i += 1
            while i < len(lines):
                next_line = lines[i].strip()
                # Stop se linea vuota o speciale
                if (not next_line or
                    next_line.startswith('#') or
                    next_line.startswith('- ') or
                    next_line.startswith('* ') or
                    next_line.startswith('> ') or
                    (next_line and next_line[0].isdigit() and len(next_line) > 1 and any(next_line[j] in '.):' for j in range(1, min(4, len(next_line))))) or
                    ('|' in next_line and next_line.count('|') >= 2)):
                    break
                para_lines.append(next_line)
                i += 1

            para_text = ' '.join(para_lines)
            if para_text:
                p = self.doc.add_paragraph()
                self._add_formatted_text(p, para_text)

    def _add_bullet_list(self, text: str):
        """Aggiunge lista puntata"""
        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith(('- ', '* ')):
                bullet_text = line[2:]
                p = self.doc.add_paragraph(style='List Bullet')
                self._add_formatted_text(p, bullet_text)

    def _add_numbered_list(self, text: str):
        """Aggiunge lista numerata"""
        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            if line and line[0].isdigit():
                # Rimuovi numero iniziale
                for i, c in enumerate(line):
                    if c in '.):' and i < 4:
                        list_text = line[i + 1:].strip()
                        break
                else:
                    list_text = line

                p = self.doc.add_paragraph(style='List Number')
                self._add_formatted_text(p, list_text)

    def _add_formatted_text(self, paragraph, text: str):
        """Aggiunge testo con formattazione inline (bold, italic)"""
        # Pattern per bold e italic
        parts = re.split(r'(\*\*.*?\*\*|\*.*?\*)', text)

        for part in parts:
            if not part:
                continue
            if part.startswith('**') and part.endswith('**'):
                run = paragraph.add_run(part[2:-2])
                run.bold = True
            elif part.startswith('*') and part.endswith('*') and len(part) > 2:
                run = paragraph.add_run(part[1:-1])
                run.italic = True
            else:
                paragraph.add_run(part)

    def _add_table_from_markdown(self, md_table: str):
        """Converte tabella markdown in tabella Word"""
        lines = [l.strip() for l in md_table.strip().split('\n') if l.strip()]

        # Filtra righe separatore (contengono solo -, :, |, spazi)
        def is_separator_row(line):
            cleaned = line.replace('|', '').strip()
            return all(c in '-: ' for c in cleaned) and len(cleaned) > 0

        lines = [l for l in lines if not is_separator_row(l)]

        if not lines:
            return

        # Parse righe
        rows = []
        for line in lines:
            cells = [c.strip() for c in line.split('|')]
            # Filtra celle vuote o che sono solo separatori
            cells = [c for c in cells if c and not all(ch in '-: ' for ch in c)]
            if cells:
                rows.append(cells)

        if not rows:
            return

        # Crea tabella
        num_cols = max(len(r) for r in rows)
        table = self.doc.add_table(rows=len(rows), cols=num_cols)
        table.style = 'Table Grid'
        table.alignment = WD_TABLE_ALIGNMENT.CENTER

        for i, row_data in enumerate(rows):
            row = table.rows[i]
            for j, cell_text in enumerate(row_data):
                if j < num_cols:
                    cell = row.cells[j]

                    # Pulisci testo cella
                    if cell.paragraphs:
                        p = cell.paragraphs[0]
                        p.clear()
                        self._add_formatted_text(p, cell_text)
                    else:
                        cell.text = cell_text

                    # Header row styling
                    if i == 0:
                        for paragraph in cell.paragraphs:
                            for run in paragraph.runs:
                                run.font.bold = True
                                run.font.color.rgb = BrandColors.WHITE
                        # Background
                        self._set_cell_shading(cell, BrandColors.PRIMARY_HEX)
                    else:
                        # Righe alternate
                        if i % 2 == 0:
                            self._set_cell_shading(cell, BrandColors.LIGHT_BG_HEX)

        self.doc.add_paragraph()

    def _set_cell_shading(self, cell, color_hex: str):
        """Imposta sfondo cella"""
        shading = OxmlElement('w:shd')
        shading.set(qn('w:fill'), color_hex)
        cell._tc.get_or_add_tcPr().append(shading)

    def _add_kpi_box(self, text: str):
        """Aggiunge box KPI evidenziato"""
        # Crea tabella 1x1 per simulare box
        table = self.doc.add_table(rows=1, cols=1)
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        cell = table.rows[0].cells[0]

        # Background verde chiaro
        self._set_cell_shading(cell, BrandColors.LIGHT_BG_HEX)

        # Bordo sinistro accent
        tc_pr = cell._tc.get_or_add_tcPr()
        borders = OxmlElement('w:tcBorders')
        left = OxmlElement('w:left')
        left.set(qn('w:val'), 'single')
        left.set(qn('w:sz'), '24')
        left.set(qn('w:color'), BrandColors.ACCENT_HEX)
        borders.append(left)
        tc_pr.append(borders)

        # Contenuto
        if cell.paragraphs:
            p = cell.paragraphs[0]
            self._add_formatted_text(p, text)

        self.doc.add_paragraph()

    def _add_quote(self, text: str):
        """Aggiunge citazione/quote"""
        try:
            p = self.doc.add_paragraph(style='CustomQuote')
        except KeyError:
            p = self.doc.add_paragraph()
            p.paragraph_format.left_indent = Cm(1)

        self._add_formatted_text(p, text)

    # =========================================================================
    # APPENDICE FONTI
    # =========================================================================

    def _add_sources_appendix(self, sources: List[Dict]):
        """Aggiunge appendice con fonti strutturate"""
        self.doc.add_page_break()
        self.doc.add_heading("Appendice: Fonti e Riferimenti", level=1)

        # Introduzione
        intro = self.doc.add_paragraph()
        intro.add_run(
            "I dati e le informazioni contenuti in questo documento sono stati "
            "verificati attraverso le seguenti fonti. Per i dati non verificabili "
            "esternamente, è stata indicata la natura di stima interna."
        )

        self.doc.add_paragraph()

        # Raggruppa per tipo
        trusted = [s for s in sources if s.get('is_trusted', False)]
        other = [s for s in sources if not s.get('is_trusted', False)]

        if trusted:
            self.doc.add_heading("Fonti Istituzionali e Autorevoli", level=2)

            for s in trusted[:20]:
                p = self.doc.add_paragraph(style='List Bullet')
                run = p.add_run(f"{s.get('name', 'N/A')}: ")
                run.bold = True

                url = s.get('url', '')
                if url:
                    run = p.add_run(url[:80])
                    run.font.size = Pt(9)
                    run.font.color.rgb = BrandColors.LIGHT_TEXT

        if other:
            self.doc.add_paragraph()
            self.doc.add_heading("Altre Fonti Consultate", level=2)

            for s in other[:15]:
                p = self.doc.add_paragraph(style='List Bullet')
                p.add_run(s.get('name', 'N/A'))

    def _add_disclaimer(self):
        """Aggiunge disclaimer finale"""
        self.doc.add_paragraph()

        p = self.doc.add_paragraph()
        run = p.add_run("Nota Metodologica: ")
        run.bold = True
        run.font.color.rgb = BrandColors.SECONDARY

        run = p.add_run(
            "I dati contenuti nel presente documento sono stati raccolti e verificati "
            "alla data di generazione. Per informazioni aggiornate, si consiglia di "
            "verificare direttamente presso le fonti citate. I dati indicati come "
            "'stima interna' o 'da verificare' richiedono validazione con fonti primarie."
        )
        run.font.size = Pt(9)
        run.font.italic = True
        run.font.color.rgb = BrandColors.LIGHT_TEXT

    # =========================================================================
    # HEADER/FOOTER
    # =========================================================================

    def _add_header_footer(self, club_name: str):
        """Aggiunge header e footer con numerazione pagine"""
        section = self.doc.sections[0]

        # Footer
        footer = section.footer
        footer.is_linked_to_previous = False

        footer_para = footer.paragraphs[0] if footer.paragraphs else footer.add_paragraph()
        footer_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        footer_para.clear()

        # Page number field
        run = footer_para.add_run()
        self._add_page_number_field(run)

        run = footer_para.add_run(f"  |  {club_name}  |  Piano Strategico")
        run.font.size = Pt(9)
        run.font.color.rgb = BrandColors.LIGHT_TEXT

    def _add_page_number_field(self, run):
        """Aggiunge campo numero pagina"""
        fld_char1 = OxmlElement('w:fldChar')
        fld_char1.set(qn('w:fldCharType'), 'begin')

        instr = OxmlElement('w:instrText')
        instr.set(qn('xml:space'), 'preserve')
        instr.text = 'PAGE'

        fld_char2 = OxmlElement('w:fldChar')
        fld_char2.set(qn('w:fldCharType'), 'separate')

        fld_char3 = OxmlElement('w:fldChar')
        fld_char3.set(qn('w:fldCharType'), 'end')

        run._r.append(fld_char1)
        run._r.append(instr)
        run._r.append(fld_char2)
        run._r.append(fld_char3)


# =============================================================================
# BATCH EXPORTER
# =============================================================================

class BatchDocxExporter:
    """
    Esportatore batch per multipli piani.
    Ottimizzato per gestire 200+ documenti.
    """

    def __init__(self):
        self.exporter = ProfessionalDocxExporter()
        self.export_log: List[Dict] = []

    def export_batch(
        self,
        plans: List[Dict],
        output_dir: Path = None
    ) -> List[Path]:
        """
        Esporta batch di piani.

        Args:
            plans: Lista di {plan_data, club_name, sources, metadata}
            output_dir: Directory output (default: OUTPUT_DIR)

        Returns:
            Lista path file generati
        """
        output_dir = output_dir or OUTPUT_DIR
        output_dir.mkdir(exist_ok=True)

        generated = []

        for i, plan_info in enumerate(plans):
            try:
                filepath = self.exporter.create_document(
                    plan_data=plan_info.get('plan_data', {}),
                    club_name=plan_info.get('club_name', f'Club_{i}'),
                    sources=plan_info.get('sources', []),
                    metadata=plan_info.get('metadata', {})
                )
                generated.append(filepath)

                self.export_log.append({
                    'club': plan_info.get('club_name', ''),
                    'path': str(filepath),
                    'status': 'success',
                    'timestamp': datetime.now().isoformat(),
                })

                logger.info(f"Exported {i + 1}/{len(plans)}: {filepath.name}")

            except Exception as e:
                logger.error(f"Export failed for plan {i}: {e}")
                self.export_log.append({
                    'club': plan_info.get('club_name', ''),
                    'status': 'failed',
                    'error': str(e),
                    'timestamp': datetime.now().isoformat(),
                })

        return generated

    def get_export_summary(self) -> Dict:
        """Sommario esportazione"""
        success = sum(1 for log in self.export_log if log.get('status') == 'success')
        failed = sum(1 for log in self.export_log if log.get('status') == 'failed')

        return {
            'total': len(self.export_log),
            'success': success,
            'failed': failed,
            'success_rate': round((success / len(self.export_log)) * 100, 1) if self.export_log else 0,
            'log': self.export_log,
        }
