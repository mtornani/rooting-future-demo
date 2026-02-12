"""
Utility per convertire StructuredPlan in markdown formattato per webapp
"""

import logging
from typing import Dict
from data_models import StructuredPlan, StructuredSection, DataPoint

logger = logging.getLogger(__name__)


def structured_plan_to_markdown(structured_plan: StructuredPlan) -> Dict[str, str]:
    """
    Converte un StructuredPlan object in dictionary di sezioni markdown.

    Returns:
        Dict con chiavi: technical_sporting, youth_development, infrastructure, etc.
    """
    sections_markdown = {}

    for section_key, section in structured_plan.sections.items():
        try:
            markdown = _section_to_markdown(section)
            sections_markdown[section_key] = markdown
            logger.info(f"Converted section {section_key} to markdown ({len(markdown)} chars)")
        except Exception as e:
            logger.error(f"Error converting section {section_key}: {e}", exc_info=True)
            sections_markdown[section_key] = f"<p class='empty-section'>Errore nella conversione: {str(e)}</p>"

    # Aggiungi executive summary se presente
    if structured_plan.executive_summary:
        sections_markdown['executive_summary'] = structured_plan.executive_summary

    logger.info(f"Converted {len(sections_markdown)} sections to markdown")
    return sections_markdown


def _section_to_markdown(section: StructuredSection) -> str:
    """Converte una StructuredSection in markdown formattato"""
    if not section.data_points:
        return "<p class='empty-section'>Sezione non disponibile</p>"

    md = f"# {section.title}\n\n"

    # Aggiungi data points organizzati
    md += "## Indicatori Chiave\n\n"

    for dp in section.data_points:
        # Header del data point con badge
        md += f"### {dp.label}\n\n"

        # Valore principale con units
        if dp.value is not None:
            md += f"**Valore:** {_format_value(dp.value, dp.unit)}\n\n"

        # Benchmark se disponibile
        if dp.benchmark and dp.benchmark.value is not None:
            md += f"**Benchmark {dp.benchmark.category}:** {_format_value(dp.benchmark.value, dp.unit)}\n\n"

            # Deviazione con colore
            if dp.deviation is not None:
                deviation_class = "success" if dp.deviation >= 0 else "warning"
                md += f"**Scostamento:** <span class='badge-{deviation_class}'>{dp.deviation:+.1f}%</span>\n\n"

        # Fonte
        if dp.source:
            # Gestisci source.type che potrebbe essere un enum o una stringa
            if hasattr(dp.source.type, 'value'):
                source_type = dp.source.type.value
            elif dp.source.type:
                source_type = str(dp.source.type)
            else:
                source_type = "unknown"

            source_desc = dp.source.description if dp.source.description else "N/A"
            md += f"📌 **Fonte:** {source_desc} ({source_type})\n\n"

        # Confidenza (gestisce sia float che ConfidenceLevel object)
        if hasattr(dp.confidence, 'value'):
            # E' un ConfidenceLevel object
            confidence_value = dp.confidence.value
        else:
            # E' un float diretto - converti in stringa
            if isinstance(dp.confidence, float):
                if dp.confidence >= 0.8:
                    confidence_value = "high"
                elif dp.confidence >= 0.5:
                    confidence_value = "medium"
                else:
                    confidence_value = "low"
            else:
                confidence_value = str(dp.confidence)

        confidence_emoji = _confidence_emoji(confidence_value)

        # Aggiungi tooltip di aiuto per spiegare l'affidabilità
        tooltip_html = '''<span class="confidence-tooltip">
            <span class="confidence-help">?</span>
            <span class="tooltip-content">
                <strong>Cos'è l'Affidabilità?</strong>
                Indica quanto sono attendibili i dati:<br><br>
                <ul>
                    <li><strong>✅ High (80-100%):</strong> Dati verificati da fonti ufficiali (bilanci certificati, FIGC)</li>
                    <li><strong>⚠️ Medium (50-80%):</strong> Stime basate su dati parziali o medie di categoria</li>
                    <li><strong>❗ Low (&lt;50%):</strong> Stime approssimative che richiedono verifica dal club</li>
                </ul>
                Per migliorare l'affidabilità, fornire dati ufficiali del club.
            </span>
        </span>'''

        md += f"{confidence_emoji} **Affidabilità:** {confidence_value.title()} {tooltip_html}\n\n"

        md += "---\n\n"

    # Aggiungi insights se presenti (attributo opzionale)
    if hasattr(section, 'insights') and section.insights:
        md += "\n## 💡 Insights Strategici\n\n"
        for insight in section.insights:
            md += f"- {insight}\n"
        md += "\n"

    return md


def _format_value(value: float, unit: str) -> str:
    """Formatta valore con unit appropriate"""
    if unit == "EUR":
        if value >= 1_000_000:
            return f"€{value/1_000_000:.2f}M"
        elif value >= 1_000:
            return f"€{value/1_000:.1f}K"
        else:
            return f"€{value:.0f}"
    elif unit == "%":
        return f"{value:.1f}%"
    elif unit in ["anni", "giocatori", "atleti", "squadre", "campi", "posti", "abbonati", "followers", "progetti", "persone", "FTE", "membri"]:
        return f"{int(value)} {unit}"
    else:
        return f"{value} {unit}"


def _confidence_emoji(confidence_level: str) -> str:
    """Emoji per livello di confidenza"""
    mapping = {
        "high": "✅",
        "medium": "⚠️",
        "low": "❗",
        "estimated": "📊"
    }
    return mapping.get(confidence_level.lower(), "❓")
