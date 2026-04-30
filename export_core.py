"""
Rooting Future Strategy Engine - Core Export Module
Provides BaseExporter abstract class and common utilities for all export formats.
"""

import re
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from abc import ABC, abstractmethod
import markdown

from config import OUTPUT_DIR

logger = logging.getLogger(__name__)


def _wrap_macro_blocks(html: str) -> str:
    """
    Wrap MACRO structured blocks in styled card divs.
    Agents produce: ### MACRO N: Title → rendered as <h3>MACRO N: Title</h3>
    We wrap each block's content in .macro-card until the next MACRO or end.
    """
    # Split on MACRO h3 headers (capturing group preserves the delimiter)
    parts = re.split(r'(<h3>MACRO\s*\d+[:\s][^<]*</h3>)', html)
    if len(parts) <= 1:
        return html  # No MACRO blocks — return unchanged

    result = [parts[0]]  # Content before first MACRO block
    i = 1
    while i < len(parts):
        h3_tag = parts[i]
        m = re.match(r'<h3>MACRO\s*(\d+)[:\s]\s*(.*?)</h3>', h3_tag)
        if m:
            num = m.group(1)
            title = m.group(2).strip()
            body = parts[i + 1] if i + 1 < len(parts) else ""
            result.append(
                f'<div class="macro-card">'
                f'<div class="macro-header">'
                f'<span class="macro-num">MACRO {num}</span>'
                f'<span class="macro-title">{title}</span>'
                f'</div>'
                f'<div class="macro-body">{body}</div>'
                f'</div>'
            )
            i += 2
        else:
            result.append(h3_tag)
            i += 1

    return ''.join(result)


class BaseExporter(ABC):
    """
    Base abstract class for all strategic plan exporters.
    Provides common utilities for branding, data normalization, and file management.
    """

    def __init__(self, output_dir: Optional[Path] = None):
        self._output_dir = Path(output_dir) if output_dir else OUTPUT_DIR
        self._output_dir.mkdir(exist_ok=True, parents=True)

    @property
    def output_dir(self) -> Path:
        return self._output_dir

    @output_dir.setter
    def output_dir(self, value: Any):
        self._output_dir = Path(value) if value else OUTPUT_DIR
        self._output_dir.mkdir(exist_ok=True, parents=True)

    def _get_safe_filename(self, club_name: str, extension: str, prefix: str = "", suffix: str = "") -> str:
        """Generates a safe filename with timestamp."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = re.sub(r'[^\w\s-]', '', club_name).strip().replace(' ', '_')
        prefix_str = f"{prefix}_" if prefix else ""
        suffix_str = f"_{suffix}" if suffix else ""
        return f"{safe_name}_{prefix_str}{timestamp}{suffix_str}.{extension}"

    def _extract_metadata(self, metadata: Optional[Dict]) -> Dict[str, Any]:
        """Extracts common metadata with defaults."""
        metadata = metadata or {}
        primary_color = metadata.get('primary_color', '#1a365d')
        secondary_color = metadata.get('secondary_color', '#000000')
        
        return {
            'primary_color': primary_color,
            'secondary_color': secondary_color,
            'category': metadata.get('category', 'STRATEGIC PLAN'),
            'region': metadata.get('region', ''),
            'club_name': metadata.get('club_name', 'Football Club'),
            'generation_date': datetime.now().strftime("%d/%m/%Y"),
            'current_year': datetime.now().year,
            'contrast_color': self._get_contrast_color(primary_color),
            'light_color': self._lighten_color(primary_color, 0.9),
            'dark_color': self._darken_color(primary_color, 0.2),
            'total_questionnaires': metadata.get('total_questionnaires', 0),
            'credibility_score': metadata.get('credibility_score', 0),
            'sources_count': metadata.get('sources_count', 0),
        }

    def _get_contrast_color(self, hex_color: str) -> str:
        """
        Returns #FFFFFF or #000000 based on WCAG 2.1 contrast ratio.
        Ensures minimum 4.5:1 contrast for readability.
        """
        hex_color = hex_color.lstrip('#')
        if len(hex_color) != 6:
            return '#000000'  # Safe default
        try:
            # Calculate contrast with both white and black, pick better one
            contrast_white = self._calculate_contrast_ratio(hex_color, 'ffffff')
            contrast_black = self._calculate_contrast_ratio(hex_color, '000000')

            # Return the color with higher contrast
            return '#FFFFFF' if contrast_white > contrast_black else '#000000'
        except Exception:
            return '#000000'  # Safe default

    def _calculate_contrast_ratio(self, hex1: str, hex2: str) -> float:
        """
        Calculate WCAG 2.1 contrast ratio between two hex colors.
        Returns value between 1 and 21 (21 = max contrast).
        """
        def relative_luminance(hex_color: str) -> float:
            """Calculate relative luminance according to WCAG"""
            rgb = [int(hex_color[i:i+2], 16) / 255.0 for i in (0, 2, 4)]
            # Apply gamma correction
            rgb_linear = [(c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4) for c in rgb]
            return 0.2126 * rgb_linear[0] + 0.7152 * rgb_linear[1] + 0.0722 * rgb_linear[2]

        l1 = relative_luminance(hex1.lstrip('#'))
        l2 = relative_luminance(hex2.lstrip('#'))

        # Ensure l1 is the lighter color
        if l1 < l2:
            l1, l2 = l2, l1

        return (l1 + 0.05) / (l2 + 0.05)

    def _lighten_color(self, hex_color: str, factor: float = 0.9) -> str:
        """Lightens a hex color by a given factor."""
        hex_color = hex_color.lstrip('#')
        if len(hex_color) != 6:
            return hex_color
        try:
            rgb = [int(hex_color[i:i+2], 16) for i in (0, 2, 4)]
            new_rgb = [min(255, int(c + (255 - c) * factor)) for c in rgb]
            return '{:02x}{:02x}{:02x}'.format(*new_rgb)
        except Exception:
            return hex_color

    def _darken_color(self, hex_color: str, factor: float = 0.2) -> str:
        """Darkens a hex color by a given factor."""
        hex_color = hex_color.lstrip('#')
        if len(hex_color) != 6:
            return hex_color
        try:
            rgb = [int(hex_color[i:i+2], 16) for i in (0, 2, 4)]
            new_rgb = [max(0, int(c * (1 - factor))) for c in rgb]
            return '{:02x}{:02x}{:02x}'.format(*new_rgb)
        except Exception:
            return hex_color

    def _ensure_readable_text(self, text_color: str, bg_color: str, min_contrast: float = 4.5) -> str:
        """
        Ensures text color has sufficient contrast against background.
        If contrast is insufficient, returns #000000 or #FFFFFF (whichever has better contrast).

        Args:
            text_color: Hex color for text
            bg_color: Hex color for background
            min_contrast: Minimum WCAG contrast ratio (default 4.5 for normal text)

        Returns:
            Adjusted text color hex (with #)
        """
        text_hex = text_color.lstrip('#')
        bg_hex = bg_color.lstrip('#')

        try:
            current_contrast = self._calculate_contrast_ratio(text_hex, bg_hex)

            if current_contrast >= min_contrast:
                return f"#{text_hex}"  # Color is fine

            # Insufficient contrast - force black or white
            contrast_white = self._calculate_contrast_ratio('ffffff', bg_hex)
            contrast_black = self._calculate_contrast_ratio('000000', bg_hex)

            logger.warning(f"Low contrast ({current_contrast:.2f}) between #{text_hex} and #{bg_hex}. Forcing safe color.")
            return '#FFFFFF' if contrast_white > contrast_black else '#000000'

        except Exception as e:
            logger.error(f"Contrast calculation error: {e}")
            return '#000000'  # Safe default
        except Exception:
            return hex_color

    def _normalize_markdown(self, content: str) -> str:
        """Shared markdown normalization logic to fix common AI generation issues."""
        if not content:
            return ""

        # Normalize existing newlines
        content = content.replace('\r\n', '\n')

        # Strip code fences (```...```) — AI sometimes wraps tables/data in code blocks
        content = re.sub(r'```[^\n]*\n([\s\S]*?)```', r'\1', content)
        content = re.sub(r'```[^\n]*\n?', '', content)  # unclosed fences

        # Strip inline source annotations (fonte: ...) that leak from agent prompts
        content = re.sub(r'\s*\(fonte:[^)]*\)', '', content, flags=re.IGNORECASE)

        # TABLES: Separate markdown table rows that are on a single line
        # NOTE: pipes must be escaped with \| — unescaped | in regex means OR
        content = re.sub(r'\|\s+\|', '|\n|', content)

        # TABLES: Insert missing separator row after header (required by markdown lib)
        # Matches: header row followed immediately by another data row (no |---|)
        def _insert_table_separator(m: re.Match) -> str:
            header = m.group(1)
            next_row = m.group(2)
            cols = header.count('|') - 1
            sep = '|' + '---|' * max(cols, 1)
            return f'{header}\n{sep}\n{next_row}'
        content = re.sub(
            r'(\|[^-\n]+\|)\n(\|[^-\n]+\|)',
            _insert_table_separator,
            content
        )

        # Pattern: ### 1. TITLE -> converts to header h3 (removes the number)
        content = re.sub(r'###\s+\d+[\.\)]\s*', '\n\n### ', content)

        # Pattern: ## 1. TITLE -> converts to header h2
        content = re.sub(r'##\s+\d+[\.\)]\s*', '\n\n## ', content)

        # Add newline BEFORE every occurrence of ## or ### in text
        content = re.sub(r'([a-zA-Z0-9.,;:!?)])\s*(#{2,4})\s+', r'\1\n\n\2 ', content)

        # Pattern: #### followed by number like 1.1 -> header h4
        content = re.sub(r'####\s+(\d+\.\d+)\s*', '\n\n#### ', content)

        # Add newline before bullet points (* or -) that follow text
        content = re.sub(r'([^\n\*\-])\s+(\*\s+\*\*)', r'\1\n\2', content)
        content = re.sub(r'([^\n])\s+(\-\s+\*\*)', r'\1\n\2', content)
        content = re.sub(r'([^\n])\s+(\*\s+[A-Z])', r'\1\n\2', content)
        content = re.sub(r'([^\n])\s+(\-\s+[A-Z])', r'\1\n\2', content)

        # Add newline before tables (lines starting with |)
        content = re.sub(r'([^\n\|])\s+(\|[^\n]+\|)', r'\1\n\n\2', content)

        # Normalize multiple consecutive newlines (max 2)
        content = re.sub(r'\n{3,}', '\n\n', content)

        # Ensure newlines after paragraphs ending with : followed by bullet points
        content = re.sub(r'(:\s*)(\*\s+\*\*)', r':\n\2', content)

        return content.strip()

    def _get_preferred_section_order(self) -> List[str]:
        """Returns the preferred order of sections for the strategic plan."""
        return [
            'executive_summary',
            'stw_sportivi',
            'stw_strutturali',
            'stw_struttura_org',
            'stw_relazioni_ist',
            'stw_marketing',
            'stw_sociali',
            'financial',
            # Fallback for older plans
            'technical_sporting',
            'youth_sector',
            'youth_development',
            'infrastructure',
            'marketing_commercial',
            'social_sustainability',
            'governance',
            'financial_plan',
        ]

    def _get_section_titles(self) -> Dict[str, str]:
        """Returns a mapping of section keys to display titles."""
        return {
            'executive_summary': '01. Sintesi Strategica',
            'stw_sportivi': '02. ⚽ Area Tecnico-Sportiva',
            'stw_strutturali': '03. 🏗️ Infrastrutture',
            'stw_struttura_org': '04. 🏛️ Struttura Organizzativa',
            'stw_relazioni_ist': '05. 🏛 Relazioni Istituzionali',
            'stw_marketing': '06. 📢 Marketing & Commerciale',
            'stw_sociali': '07. 🤝 Area Sociale',
            'financial': '08. 💰 Piano Finanziario',
            'technical_sporting': '02. Area Tecnico-Sportiva',
            'youth_sector': '03. Settore Giovanile',
            'youth_development': '03. Sviluppo Settore Giovanile',
            'infrastructure': '04. Infrastrutture & Risorse',
            'marketing_commercial': '05. Marketing & Commerciale',
            'social_sustainability': '06. Sostenibilità & Sociale',
            'governance': '07. Governance & Organizzazione',
            'financial_plan': '06. 💰 Piano Finanziario',
        }

    def _markdown_to_html(self, text: str) -> str:
        """Converts markdown text to HTML with custom badge handling."""
        if not text:
            return ""

        # Initial markdown conversion — NO nl2br: converts every \n to <br>,
        # breaking layout when AI wraps long lines at 80 chars.
        html = markdown.markdown(text, extensions=['tables'])

        # Badge Uniformity
        html = html.replace('📋', '<span class="badge questionnaire">📋 Da Questionario</span>')
        html = html.replace('🔍', '<span class="badge research">🔍 Ricerca Web</span>')
        html = html.replace('📊', '<span class="badge estimate">📊 Stima AI</span>')

        # Special boxes — wrap entire <p> so div is always properly closed
        html = re.sub(
            r'<p><strong>(KPI|TARGET|OBIETTIVO):</strong>(.*?)</p>',
            r'<div class="kpi-box"><strong>\1:</strong>\2</div>',
            html, flags=re.DOTALL
        )
        html = re.sub(
            r'<p>💡 <strong>INSIGHT:</strong>(.*?)</p>',
            r'<div class="insight-box">💡 <strong>INSIGHT:</strong>\1</div>',
            html, flags=re.DOTALL
        )
        html = re.sub(
            r'<p>🚀 <strong>(ACTION|AZIONE):</strong>(.*?)</p>',
            r'<div class="action-box">🚀 <strong>\1:</strong>\2</div>',
            html, flags=re.DOTALL
        )

        # Strip "| Anno N" timeline remnants that appear at start of paragraphs
        # (AI outputs "| Anno 2 | Anno 3\n<strong>Budget:..." in same <p>)
        html = re.sub(r'(?:\|\s*(?:Anno|Year)\s*\d[^|\n<]*)+\|?\s*\n?', '', html)
        # Clean up any resulting empty paragraphs
        html = re.sub(r'<p>\s*</p>', '', html)

        # Wrap MACRO blocks in styled cards (Phase 3)
        html = _wrap_macro_blocks(html)

        return html

    @abstractmethod
    def export(self, plan_data: Dict, club_name: str, sources: List[Dict] = None, metadata: Dict = None) -> Path:
        """Main export method to be implemented by subclasses."""
        pass
