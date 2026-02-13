"""
Rooting Future - Content Formatter v1.0
Converts markdown content to styled HTML for webapp viewer
"""

import re
import markdown
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


class ContentFormatter:
    """Formatta contenuti piano strategico per webapp"""

    @staticmethod
    def format_section_content(content: str) -> str:
        """
        Converte markdown in HTML formattato con:
        - Headers con anchor links
        - Bullet points stilizzati
        - Callout boxes per info importanti
        - Code blocks con syntax highlighting
        - Keyword badges
        """
        if not content:
            return '<p class="empty-section">Sezione non disponibile</p>'

        # Strip whitespace
        content = content.strip()

        if len(content) < 20:
            return '<p class="empty-section">Sezione non disponibile</p>'

        try:
            # Convert markdown to HTML with extensions
            html = markdown.markdown(
                content,
                extensions=[
                    'extra',           # Tables, fenced code, etc.
                    'codehilite',      # Syntax highlighting
                    'toc',             # Table of contents
                    'tables',          # GitHub-style tables
                    'nl2br',           # Newline to <br>
                ]
            )

            # Add custom styling enhancements
            html = ContentFormatter._enhance_html(html)

            logger.debug(f"[FORMATTER] Formatted content: {len(content)} chars -> {len(html)} chars HTML")
            return html

        except Exception as e:
            logger.error(f"[FORMATTER] Error formatting content: {e}")
            # Fallback: wrap in paragraph tags
            return f'<p>{content}</p>'

    @staticmethod
    def _enhance_html(html: str) -> str:
        """Aggiunge classi CSS custom per styling avanzato"""

        # 1. Highlight priority headers (### PRIORITÀ, ### OBIETTIVI, etc.)
        html = re.sub(
            r'<h3>(PRIORITÀ|OBIETTIVI|QUICK WINS|TOP \d+|MACRO \d+|STRATEGIA|PILASTRI|AZIONI)(.*?)</h3>',
            r'<h3 class="priority-header"><span class="badge-priority">\1</span>\2</h3>',
            html,
            flags=re.IGNORECASE
        )

        # 2. Style all bullet lists
        html = html.replace('<ul>', '<ul class="styled-list">')

        # 3. Style ordered lists
        html = html.replace('<ol>', '<ol class="styled-ordered-list">')

        # 4. Add emoji icons to specific keywords
        html = ContentFormatter._add_emoji_icons(html)

        # 5. Create callout boxes for h4 subsections
        html = re.sub(
            r'<h4>(.*?)</h4>',
            r'<h4 class="subsection-header">\1</h4>',
            html
        )

        # 6. Enhance h2 headers
        html = re.sub(
            r'<h2>(.*?)</h2>',
            r'<h2 class="section-h2">\1</h2>',
            html
        )

        # 7. Create callout boxes for important notes
        # Match patterns like "NOTA:", "IMPORTANTE:", "ATTENZIONE:"
        html = re.sub(
            r'<p>(NOTA|IMPORTANTE|ATTENZIONE|NOTA BENE|NB):\s*(.*?)</p>',
            r'<div class="callout">\1: \2</div>',
            html,
            flags=re.IGNORECASE
        )

        return html

    @staticmethod
    def _add_emoji_icons(html: str) -> str:
        """Aggiunge emoji icons a keyword specifiche"""
        replacements = {
            # Categorie principali
            'SPORTIVI': '⚽',
            'STRUTTURALI': '🏗️',
            'MARKETING': '📢',
            'COMMERCIALE': '💼',
            'SOCIALI': '🤝',
            'FINANZIARI': '💰',
            'TECNICI': '⚙️',

            # Timeline
            'ANNO 1': '1️⃣',
            'ANNO 2': '2️⃣',
            'ANNO 3': '3️⃣',
            'BREVE TERMINE': '⚡',
            'MEDIO TERMINE': '📅',
            'LUNGO TERMINE': '🎯',

            # Priorità
            'QUICK WINS': '⚡',
            'PRIORITÀ': '🎯',
            'URGENTE': '🚨',
            'ALTA': '🔴',
            'MEDIA': '🟡',
            'BASSA': '🟢',

            # Settori
            'GIOVANILE': '🌱',
            'PRIMA SQUADRA': '⭐',
            'INFRASTRUTTURE': '🏗️',
            'GOVERNANCE': '⚖️',
        }

        for keyword, emoji in replacements.items():
            # Replace in strong tags
            html = re.sub(
                rf'<strong>({keyword})</strong>',
                rf'<span class="keyword-badge">{emoji} <strong>\1</strong></span>',
                html,
                flags=re.IGNORECASE
            )

            # Replace in plain text at start of paragraphs
            html = re.sub(
                rf'<p>({keyword}):',
                rf'<p><span class="keyword-badge">{emoji} <strong>\1</strong></span>:',
                html,
                flags=re.IGNORECASE
            )

        return html

    @staticmethod
    def extract_key_metrics(content: str) -> Dict[str, Any]:
        """Estrae metriche chiave dal contenuto per dashboard"""
        if not content:
            return {}

        metrics = {}

        try:
            # Estrai percentuali (es. "97.5%", "20%")
            percentages = re.findall(r'(\d+(?:\.\d+)?%)', content)
            if percentages:
                metrics['percentages'] = percentages[:5]

            # Estrai valori monetari (es. "€50K", "€1.2M")
            money = re.findall(r'€\s?(\d+(?:\.\d+)?[KM]?)', content, re.IGNORECASE)
            if money:
                metrics['financial'] = money[:5]

            # Conta priorità/obiettivi
            priorities = len(re.findall(r'MACRO \d+|PRIORITÀ \d+|OBIETTIVO \d+', content, re.IGNORECASE))
            if priorities:
                metrics['priorities_count'] = priorities

            # Estrai numeri importanti (es. "15 progetti", "3 anni")
            numbers = re.findall(r'\b(\d+)\s+(progetti|obiettivi|anni|mesi|settimane)', content, re.IGNORECASE)
            if numbers:
                metrics['key_numbers'] = [(num, unit) for num, unit in numbers[:5]]

        except Exception as e:
            logger.error(f"[FORMATTER] Error extracting metrics: {e}")

        return metrics


# Utility function for quick formatting
def format_plan_section(content: str) -> str:
    """Quick utility to format a single section"""
    formatter = ContentFormatter()
    return formatter.format_section_content(content)
