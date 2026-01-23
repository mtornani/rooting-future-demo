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
        """Returns #FFFFFF or #000000 based on the contrast of the input hex color."""
        hex_color = hex_color.lstrip('#')
        if len(hex_color) != 6:
            return '#FFFFFF'
        try:
            r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
            # YIQ formula for brightness
            brightness = (r * 299 + g * 587 + b * 114) / 1000
            return '#000000' if brightness > 128 else '#FFFFFF'
        except Exception:
            return '#FFFFFF'

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

    def _normalize_markdown(self, content: str) -> str:
        """Shared markdown normalization logic to fix common AI generation issues."""
        if not content:
            return ""
        
        # Normalize existing newlines
        content = content.replace('\r\n', '\n')

        # TABLES: Separate markdown table rows that are on a single line
        content = re.sub(r'|\s+|', '|\n|', content)

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
            'executive_summary': '01. Executive Summary',
            'stw_sportivi': '02. ⚽ Obiettivi Sportivi',
            'stw_strutturali': '03. 🏗️ Obiettivi Strutturali',
            'stw_marketing': '04. 📢 Obiettivi Marketing',
            'stw_sociali': '05. 🤝 Obiettivi Sociali',
            'financial': '06. 💰 Piano Finanziario',
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
        
        # Initial markdown conversion
        html = markdown.markdown(text, extensions=['tables', 'nl2br'])
        
        # Badge Uniformity
        html = html.replace('📋', '<span class="badge questionnaire">📋 Da Questionario</span>')
        html = html.replace('🔍', '<span class="badge research">🔍 Ricerca Web</span>')
        html = html.replace('📊', '<span class="badge estimate">📊 Stima AI</span>')
        
        # Special boxes (KPI, INSIGHT, ACTION)
        html = re.sub(r'<p><strong>(KPI|TARGET|OBIETTIVO):</strong>', r'<div class="kpi-box"><strong>\1:</strong>', html)
        html = re.sub(r'<p>💡 <strong>INSIGHT:</strong>', r'<div class="insight-box">💡 <strong>INSIGHT:</strong>', html)
        html = re.sub(r'<p>🚀 <strong>(ACTION|AZIONE):</strong>', r'<div class="action-box">🚀 <strong>\1:</strong>', html)
        
        # Close boxes
        html = html.replace(':</strong></p>', ':</strong></div>')
        
        return html

    @abstractmethod
    def export(self, plan_data: Dict, club_name: str, sources: List[Dict] = None, metadata: Dict = None) -> Path:
        """Main export method to be implemented by subclasses."""
        pass
