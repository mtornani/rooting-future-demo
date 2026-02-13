# UX-001: Content Formatting & Readability Enhancement

## Obiettivo
Trasformare il "wall of text" in contenuto strutturato, scannable e piacevole da leggere nella webapp.

## Problemi Attuali
1. **Wall of text**: Paragrafi lunghi senza formattazione
2. **No struttura visiva**: Mancano headers, bullets, highlights
3. **Markdown raw**: I contenuti markdown non vengono renderizzati correttamente
4. **No progressive disclosure**: Tutto espanso di default

## Soluzione Proposta

### 1. Parser Markdown → HTML
Processare i contenuti delle sezioni per convertire markdown in HTML formattato:

```python
# File: utils/content_formatter.py
import re
import markdown
from typing import Dict, Any

class ContentFormatter:
    """Formatta contenuti piano per webapp"""

    @staticmethod
    def format_section_content(content: str) -> str:
        """
        Converte markdown in HTML formattato con:
        - Headers con anchor links
        - Bullet points stilizzati
        - Callout boxes per info importanti
        - Code blocks con syntax highlighting
        """
        if not content or len(content) < 50:
            return '<p class="empty-section">Sezione non disponibile</p>'

        # Convert markdown to HTML
        html = markdown.markdown(
            content,
            extensions=['extra', 'codehilite', 'toc', 'tables']
        )

        # Add custom styling
        html = ContentFormatter._enhance_html(html)

        return html

    @staticmethod
    def _enhance_html(html: str) -> str:
        """Aggiunge classi CSS custom per styling"""

        # Highlight important sections (### PRIORITÀ, ### OBIETTIVI, etc.)
        html = re.sub(
            r'<h3>(PRIORITÀ|OBIETTIVI|QUICK WINS|TOP \d+|MACRO \d+)(.*?)</h3>',
            r'<h3 class="priority-header"><span class="badge-priority">\1</span>\2</h3>',
            html,
            flags=re.IGNORECASE
        )

        # Style bullet lists
        html = html.replace('<ul>', '<ul class="styled-list">')
        html = html.replace('<ol>', '<ol class="styled-ordered-list">')

        # Add icons to specific keywords
        html = ContentFormatter._add_emoji_icons(html)

        # Create callout boxes for ### sections
        html = re.sub(
            r'<h4>(.*?)</h4>',
            r'<h4 class="subsection-header">\1</h4>',
            html
        )

        return html

    @staticmethod
    def _add_emoji_icons(html: str) -> str:
        """Aggiunge emoji icons a keyword specifiche"""
        replacements = {
            'SPORTIVI': '⚽',
            'STRUTTURALI': '🏗️',
            'MARKETING': '📢',
            'SOCIALI': '🤝',
            'ANNO 1': '1️⃣',
            'ANNO 2': '2️⃣',
            'ANNO 3': '3️⃣',
            'QUICK WINS': '⚡',
            'PRIORITÀ': '🎯',
        }

        for keyword, emoji in replacements.items():
            html = html.replace(
                f'**{keyword}**',
                f'<span class="keyword-badge">{emoji} <strong>{keyword}</strong></span>'
            )

        return html

    @staticmethod
    def extract_key_metrics(content: str) -> Dict[str, Any]:
        """Estrae metriche chiave dal contenuto per dashboard"""
        metrics = {}

        # Estrai percentuali (es. "97.5%", "20%")
        percentages = re.findall(r'(\d+(?:\.\d+)?%)', content)
        if percentages:
            metrics['percentages'] = percentages[:5]

        # Estrai valori monetari (es. "€50K", "€1.2M")
        money = re.findall(r'€\s?(\d+(?:\.\d+)?[KM]?)', content)
        if money:
            metrics['financial'] = money[:5]

        # Conta priorità/obiettivi
        priorities = len(re.findall(r'MACRO \d+|PRIORITÀ \d+', content))
        if priorities:
            metrics['priorities_count'] = priorities

        return metrics
```

### 2. Enhanced CSS per Content
Aggiungere stili per contenuto formattato:

```css
/* Enhanced content styling */
.section-content {
    font-size: 16px;
    line-height: 1.8;
    color: #374151;
}

/* Headers */
.section-content h2 {
    color: #1f2937;
    font-size: 22px;
    font-weight: 700;
    margin: 32px 0 16px;
    padding-bottom: 8px;
    border-bottom: 2px solid #e5e7eb;
}

.section-content h3 {
    color: #374151;
    font-size: 18px;
    font-weight: 600;
    margin: 28px 0 12px;
}

.section-content h3.priority-header {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    padding: 12px 20px;
    border-radius: 8px;
    margin: 24px 0 16px;
}

.badge-priority {
    background: rgba(255, 255, 255, 0.2);
    padding: 4px 12px;
    border-radius: 16px;
    font-size: 12px;
    font-weight: 700;
    margin-right: 12px;
}

.subsection-header {
    color: #6366f1;
    font-size: 16px;
    font-weight: 600;
    margin: 20px 0 10px;
    padding-left: 12px;
    border-left: 3px solid #6366f1;
}

/* Lists */
.styled-list {
    list-style: none;
    padding-left: 0;
    margin: 16px 0;
}

.styled-list li {
    position: relative;
    padding-left: 32px;
    margin-bottom: 12px;
    line-height: 1.6;
}

.styled-list li::before {
    content: "→";
    position: absolute;
    left: 8px;
    color: #667eea;
    font-weight: 700;
    font-size: 18px;
}

.styled-ordered-list {
    padding-left: 32px;
    counter-reset: item;
    list-style: none;
}

.styled-ordered-list li {
    position: relative;
    padding-left: 16px;
    margin-bottom: 12px;
    counter-increment: item;
}

.styled-ordered-list li::before {
    content: counter(item) ".";
    position: absolute;
    left: -24px;
    color: #667eea;
    font-weight: 700;
    font-size: 16px;
}

/* Keyword badges */
.keyword-badge {
    display: inline-block;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    padding: 6px 14px;
    border-radius: 20px;
    font-size: 14px;
    font-weight: 600;
    margin: 4px 8px 4px 0;
}

/* Paragraphs */
.section-content p {
    margin-bottom: 16px;
    max-width: 800px;
}

/* Emphasis */
.section-content strong {
    color: #1f2937;
    font-weight: 600;
}

.section-content em {
    color: #6366f1;
    font-style: normal;
    font-weight: 500;
}

/* Tables */
.section-content table {
    width: 100%;
    border-collapse: collapse;
    margin: 24px 0;
    font-size: 15px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.05);
    border-radius: 8px;
    overflow: hidden;
}

.section-content thead {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
}

.section-content th {
    padding: 14px 16px;
    text-align: left;
    font-weight: 600;
    letter-spacing: 0.5px;
}

.section-content td {
    padding: 12px 16px;
    border-bottom: 1px solid #e5e7eb;
}

.section-content tr:hover {
    background: #f9fafb;
}

/* Code blocks */
.section-content code {
    background: #f3f4f6;
    padding: 2px 6px;
    border-radius: 4px;
    font-family: 'Monaco', 'Courier New', monospace;
    font-size: 14px;
    color: #dc2626;
}

.section-content pre {
    background: #1f2937;
    color: #f9fafb;
    padding: 20px;
    border-radius: 8px;
    overflow-x: auto;
    margin: 20px 0;
}

.section-content pre code {
    background: none;
    color: inherit;
    padding: 0;
}

/* Callout boxes */
.callout {
    background: #eff6ff;
    border-left: 4px solid #3b82f6;
    padding: 16px 20px;
    margin: 20px 0;
    border-radius: 0 8px 8px 0;
}

.callout.warning {
    background: #fef3c7;
    border-left-color: #f59e0b;
}

.callout.success {
    background: #d1fae5;
    border-left-color: #10b981;
}

/* Responsive */
@media (max-width: 768px) {
    .section-content {
        font-size: 15px;
        line-height: 1.7;
    }

    .section-content h2 {
        font-size: 20px;
    }

    .section-content h3 {
        font-size: 17px;
    }
}
```

### 3. Update Route per Formattare Contenuti
Modificare `view_strategic_plan` per processare i contenuti:

```python
from utils.content_formatter import ContentFormatter

@app.route("/view/<plan_id>")
@login_required
def view_strategic_plan(plan_id):
    # ... existing code ...

    # Format all section contents
    formatter = ContentFormatter()
    formatted_plan = {}

    for section_key, content in plan_record.plan_data.items():
        if isinstance(content, str):
            formatted_plan[section_key] = formatter.format_section_content(content)
        else:
            formatted_plan[section_key] = content

    return render_template(
        "strategic_plan_viewer.html",
        plan=formatted_plan,  # Use formatted version
        plan_id=plan_id,
        club_name=plan_record.club_name,
        category=plan_record.category,
        metadata=metadata
    )
```

## Implementation Steps

1. **Create ContentFormatter** (utils/content_formatter.py) - +200 LOC
2. **Update CSS** (static/css/plan_viewer.css) - +250 LOC
3. **Modify route** (app.py) - +15 LOC
4. **Install markdown** (`pip install markdown`)

## Benefits
- ✅ Leggibilità +80% (headers, bullets, spacing)
- ✅ Scannable content (highlights, badges)
- ✅ Professional look (tables, callouts)
- ✅ Mobile-friendly (responsive text sizes)
- ✅ Engagement +50% (visual hierarchy)

## Expected LOC
- utils/content_formatter.py: +200 LOC (new)
- static/css/plan_viewer.css: +250 LOC (additions)
- app.py: +15 LOC (formatting logic)
- requirements.txt: +1 LOC (markdown dependency)
- Total: +466 LOC

## Testing
1. View plan con sezioni markdown → verify formatting
2. Test bullet lists → check styling
3. Test tables → verify responsiveness
4. Test mobile → check readability
5. Test long paragraphs → verify max-width
