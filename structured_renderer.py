"""
Structured Renderer per Rooting Future Strategy Engine v5.4

Genera report HTML/PDF professionali da dati strutturati con:
- Visualizzazione benchmark vs dati reali
- Citazioni scientifiche
- Dashboard di credibilità
- Tabelle di confronto
"""

import os
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path

from data_models import (
    DataPoint, StructuredSection, StructuredPlan,
    DataType, ConfidenceLevel, DeviationType, Source, Benchmark
)


class StructuredHTMLRenderer:
    """
    Renderer HTML per piani strutturati.
    Genera report professionali con tracciabilità scientifica dei dati.
    """

    def __init__(self, output_dir: str = "output"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.footnotes: List[str] = []
        self.footnote_counter = 0

    def render(self, plan: StructuredPlan) -> str:
        """
        Genera HTML completo del piano.
        """
        self.footnotes = []
        self.footnote_counter = 0

        html = f'''<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Piano Strategico - {plan.club_name}</title>
    {self._get_styles()}
</head>
<body>
    <div class="report">
        {self._render_header(plan)}
        {self._render_credibility_dashboard(plan)}
        {self._render_toc(plan)}

        <main class="content">
            {self._render_executive_summary(plan)}

            {"".join(self._render_section(s) for s in plan.sections.values())}

            {self._render_bibliography(plan)}
            {self._render_footnotes()}
        </main>

        {self._render_footer(plan)}
    </div>
</body>
</html>'''

        # Salva file
        filename = f"{plan.club_name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        filepath = self.output_dir / filename

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html)

        return str(filepath)

    def _get_styles(self) -> str:
        """CSS professionale per report"""
        return '''
    <style>
        :root {
            --primary: #1a365d;
            --secondary: #2c5282;
            --accent: #3182ce;
            --success: #38a169;
            --warning: #d69e2e;
            --danger: #e53e3e;
            --gray-100: #f7fafc;
            --gray-200: #edf2f7;
            --gray-300: #e2e8f0;
            --gray-600: #718096;
            --gray-800: #2d3748;
        }

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
            font-size: 14px;
            line-height: 1.6;
            color: var(--gray-800);
            background: var(--gray-100);
        }

        .report {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            box-shadow: 0 0 40px rgba(0,0,0,0.1);
        }

        /* Header */
        .report-header {
            background: linear-gradient(135deg, var(--primary) 0%, var(--secondary) 100%);
            color: white;
            padding: 60px 40px;
            position: relative;
        }

        .report-header h1 {
            font-size: 2.5rem;
            margin-bottom: 10px;
        }

        .report-header .subtitle {
            font-size: 1.2rem;
            opacity: 0.9;
        }

        .report-header .meta {
            margin-top: 20px;
            font-size: 0.9rem;
            opacity: 0.8;
        }

        /* Credibility Dashboard */
        .credibility-dashboard {
            background: var(--gray-100);
            padding: 30px 40px;
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            border-bottom: 3px solid var(--primary);
        }

        .metric-card {
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            text-align: center;
        }

        .metric-card .value {
            font-size: 2rem;
            font-weight: bold;
            color: var(--primary);
        }

        .metric-card .label {
            font-size: 0.85rem;
            color: var(--gray-600);
            margin-top: 5px;
        }

        .metric-card.success .value { color: var(--success); }
        .metric-card.warning .value { color: var(--warning); }
        .metric-card.danger .value { color: var(--danger); }

        /* Progress bar */
        .progress-bar {
            height: 8px;
            background: var(--gray-200);
            border-radius: 4px;
            margin-top: 10px;
            overflow: hidden;
        }

        .progress-bar .fill {
            height: 100%;
            border-radius: 4px;
            transition: width 0.3s;
        }

        .progress-bar .fill.high { background: var(--success); }
        .progress-bar .fill.medium { background: var(--warning); }
        .progress-bar .fill.low { background: var(--danger); }

        /* TOC */
        .toc {
            padding: 30px 40px;
            background: white;
            border-bottom: 1px solid var(--gray-200);
        }

        .toc h2 {
            font-size: 1.2rem;
            color: var(--primary);
            margin-bottom: 15px;
        }

        .toc-list {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 10px;
        }

        .toc-item {
            padding: 10px 15px;
            background: var(--gray-100);
            border-radius: 4px;
            color: var(--gray-800);
            text-decoration: none;
            transition: background 0.2s;
        }

        .toc-item:hover {
            background: var(--gray-200);
        }

        /* Content */
        .content {
            padding: 40px;
        }

        /* Section */
        .section {
            margin-bottom: 50px;
            page-break-inside: avoid;
        }

        .section-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding-bottom: 15px;
            border-bottom: 2px solid var(--primary);
            margin-bottom: 25px;
        }

        .section-header h2 {
            color: var(--primary);
            font-size: 1.5rem;
        }

        .section-metrics {
            display: flex;
            gap: 15px;
        }

        .section-metric {
            font-size: 0.8rem;
            padding: 5px 10px;
            background: var(--gray-100);
            border-radius: 4px;
        }

        /* Summary box */
        .summary-box {
            background: linear-gradient(135deg, var(--gray-100) 0%, white 100%);
            padding: 25px;
            border-radius: 8px;
            border-left: 4px solid var(--accent);
            margin-bottom: 30px;
        }

        .summary-box p {
            font-size: 1.05rem;
            line-height: 1.7;
        }

        /* Key findings */
        .key-findings {
            margin-bottom: 30px;
        }

        .key-findings h3 {
            font-size: 1.1rem;
            color: var(--secondary);
            margin-bottom: 15px;
        }

        .finding-item {
            display: flex;
            align-items: flex-start;
            padding: 12px 15px;
            background: white;
            border: 1px solid var(--gray-200);
            border-radius: 6px;
            margin-bottom: 10px;
        }

        .finding-item::before {
            content: "\\2713";
            color: var(--success);
            font-weight: bold;
            margin-right: 12px;
        }

        /* Data Point Card */
        .data-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }

        .data-card {
            background: white;
            border: 1px solid var(--gray-200);
            border-radius: 8px;
            overflow: hidden;
        }

        .data-card-header {
            background: var(--gray-100);
            padding: 15px;
            border-bottom: 1px solid var(--gray-200);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .data-card-header .label {
            font-weight: 600;
            color: var(--gray-800);
        }

        .data-card-body {
            padding: 20px;
        }

        .data-value-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
        }

        .data-value {
            font-size: 1.8rem;
            font-weight: bold;
            color: var(--primary);
        }

        .data-value.missing {
            font-size: 1rem;
            color: var(--warning);
            font-weight: normal;
            font-style: italic;
        }

        /* Benchmark comparison */
        .benchmark-row {
            background: var(--gray-100);
            padding: 12px 15px;
            border-radius: 6px;
            margin-bottom: 10px;
        }

        .benchmark-label {
            font-size: 0.8rem;
            color: var(--gray-600);
            margin-bottom: 5px;
        }

        .benchmark-comparison {
            display: flex;
            align-items: center;
            gap: 15px;
        }

        .benchmark-value {
            font-weight: 600;
        }

        .deviation {
            padding: 3px 8px;
            border-radius: 4px;
            font-size: 0.85rem;
            font-weight: 500;
        }

        .deviation.aligned {
            background: #c6f6d5;
            color: #22543d;
        }

        .deviation.above {
            background: #bee3f8;
            color: #2a4365;
        }

        .deviation.below {
            background: #fed7d7;
            color: #742a2a;
        }

        .deviation.critical {
            background: #feb2b2;
            color: #742a2a;
            font-weight: bold;
        }

        /* Source citation */
        .source-row {
            margin-top: 10px;
            padding-top: 10px;
            border-top: 1px dashed var(--gray-200);
        }

        .source-citation {
            font-size: 0.8rem;
            color: var(--gray-600);
            display: flex;
            align-items: center;
            gap: 5px;
        }

        .source-citation::before {
            content: "\\1F4DA";
        }

        .footnote-ref {
            color: var(--accent);
            font-size: 0.7rem;
            vertical-align: super;
            cursor: help;
        }

        /* Badges */
        .data-badge {
            padding: 3px 8px;
            border-radius: 4px;
            font-size: 0.75rem;
            font-weight: 500;
            text-transform: uppercase;
        }

        .data-verified { background: #c6f6d5; color: #22543d; }
        .data-benchmark { background: #bee3f8; color: #2a4365; }
        .data-estimate { background: #feebc8; color: #744210; }
        .data-to-acquire { background: #fed7d7; color: #742a2a; }
        .data-calculated { background: #e9d8fd; color: #44337a; }
        .data-projected { background: #b2f5ea; color: #234e52; }

        .confidence-badge {
            padding: 3px 8px;
            border-radius: 4px;
            font-size: 0.75rem;
            font-weight: 600;
        }

        .confidence-success { background: #c6f6d5; color: #22543d; }
        .confidence-warning { background: #feebc8; color: #744210; }
        .confidence-caution { background: #fed7e2; color: #702459; }
        .confidence-danger { background: #fed7d7; color: #742a2a; }

        /* Recommendations */
        .recommendations {
            margin-top: 30px;
        }

        .recommendations h3 {
            font-size: 1.1rem;
            color: var(--secondary);
            margin-bottom: 15px;
        }

        .recommendation-card {
            display: flex;
            background: white;
            border: 1px solid var(--gray-200);
            border-radius: 8px;
            overflow: hidden;
            margin-bottom: 15px;
        }

        .recommendation-priority {
            width: 6px;
            flex-shrink: 0;
        }

        .recommendation-priority.high { background: var(--danger); }
        .recommendation-priority.medium { background: var(--warning); }
        .recommendation-priority.low { background: var(--success); }

        .recommendation-content {
            padding: 15px 20px;
            flex: 1;
        }

        .recommendation-title {
            font-weight: 600;
            margin-bottom: 5px;
        }

        .recommendation-meta {
            display: flex;
            gap: 15px;
            margin-top: 10px;
            font-size: 0.8rem;
            color: var(--gray-600);
        }

        /* Tables */
        .data-table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }

        .data-table th,
        .data-table td {
            padding: 12px 15px;
            text-align: left;
            border-bottom: 1px solid var(--gray-200);
        }

        .data-table th {
            background: var(--primary);
            color: white;
            font-weight: 600;
        }

        .data-table tr:hover {
            background: var(--gray-100);
        }

        /* Bibliography */
        .bibliography {
            margin-top: 50px;
            padding-top: 30px;
            border-top: 2px solid var(--gray-200);
        }

        .bibliography h2 {
            color: var(--primary);
            margin-bottom: 20px;
        }

        .bib-item {
            padding: 10px 0;
            border-bottom: 1px solid var(--gray-200);
            display: flex;
            gap: 10px;
        }

        .bib-number {
            color: var(--accent);
            font-weight: bold;
            min-width: 30px;
        }

        .bib-content {
            flex: 1;
        }

        .bib-type {
            font-size: 0.75rem;
            padding: 2px 6px;
            background: var(--gray-200);
            border-radius: 3px;
            margin-left: 10px;
        }

        /* Footnotes */
        .footnotes {
            margin-top: 40px;
            padding: 20px;
            background: var(--gray-100);
            border-radius: 8px;
            font-size: 0.85rem;
        }

        .footnotes h3 {
            font-size: 1rem;
            margin-bottom: 15px;
        }

        .footnote-item {
            margin-bottom: 8px;
            display: flex;
            gap: 10px;
        }

        .footnote-num {
            color: var(--accent);
            font-weight: bold;
        }

        /* Footer */
        .report-footer {
            background: var(--gray-800);
            color: white;
            padding: 30px 40px;
            text-align: center;
            font-size: 0.85rem;
        }

        .report-footer .disclaimer {
            opacity: 0.7;
            margin-top: 10px;
        }

        /* Print styles */
        @media print {
            body { background: white; }
            .report { box-shadow: none; max-width: none; }
            .section { page-break-inside: avoid; }
            .data-card { break-inside: avoid; }
        }
    </style>'''

    def _render_header(self, plan: StructuredPlan) -> str:
        return f'''
        <header class="report-header">
            <h1>Piano Strategico Triennale</h1>
            <div class="subtitle">{plan.club_name}</div>
            <div class="meta">
                <span>Categoria: {plan.category}</span> |
                <span>Data: {datetime.now().strftime("%d/%m/%Y")}</span> |
                <span>Versione: 1.0</span>
            </div>
        </header>'''

    def _render_credibility_dashboard(self, plan: StructuredPlan) -> str:
        cred_class = "success" if plan.overall_credibility >= 70 else "warning" if plan.overall_credibility >= 50 else "danger"
        cred_fill = "high" if plan.overall_credibility >= 70 else "medium" if plan.overall_credibility >= 50 else "low"

        completeness = 0
        if plan.total_data_points > 0:
            completeness = ((plan.total_data_points - plan.missing_data_points) / plan.total_data_points) * 100

        comp_class = "success" if completeness >= 80 else "warning" if completeness >= 50 else "danger"

        return f'''
        <div class="credibility-dashboard">
            <div class="metric-card {cred_class}">
                <div class="value">{plan.overall_credibility:.1f}%</div>
                <div class="label">Credibilita Complessiva</div>
                <div class="progress-bar">
                    <div class="fill {cred_fill}" style="width: {plan.overall_credibility}%"></div>
                </div>
            </div>

            <div class="metric-card">
                <div class="value">{plan.total_data_points}</div>
                <div class="label">Punti Dati Totali</div>
            </div>

            <div class="metric-card success">
                <div class="value">{plan.verified_data_points}</div>
                <div class="label">Dati Verificati</div>
            </div>

            <div class="metric-card {comp_class}">
                <div class="value">{completeness:.0f}%</div>
                <div class="label">Completezza Dati</div>
                <div class="progress-bar">
                    <div class="fill {"high" if completeness >= 80 else "medium" if completeness >= 50 else "low"}" style="width: {completeness}%"></div>
                </div>
            </div>

            <div class="metric-card">
                <div class="value">{len(plan.bibliography)}</div>
                <div class="label">Fonti Citate</div>
            </div>
        </div>'''

    def _render_toc(self, plan: StructuredPlan) -> str:
        items = "".join(
            f'<a href="#{s.section_id}" class="toc-item">{s.title}</a>'
            for s in plan.sections.values()
        )
        return f'''
        <nav class="toc">
            <h2>Indice</h2>
            <div class="toc-list">
                {items}
            </div>
        </nav>'''

    def _render_executive_summary(self, plan: StructuredPlan) -> str:
        if not plan.executive_summary:
            return ""

        return f'''
        <section class="section" id="executive-summary">
            <div class="section-header">
                <h2>Executive Summary</h2>
            </div>
            <div class="summary-box">
                <p>{plan.executive_summary}</p>
            </div>
        </section>'''

    def _render_section(self, section: StructuredSection) -> str:
        return f'''
        <section class="section" id="{section.section_id}">
            <div class="section-header">
                <h2>{section.title}</h2>
                <div class="section-metrics">
                    <span class="section-metric">Credibilita: {section.credibility_score:.0f}%</span>
                    <span class="section-metric">Completezza: {section.data_completeness:.0f}%</span>
                    <span class="section-metric">Fonti: {section.sources_count}</span>
                </div>
            </div>

            <div class="summary-box">
                <p>{section.summary}</p>
            </div>

            {self._render_key_findings(section.key_findings)}
            {self._render_data_points(section.data_points)}
            {self._render_recommendations(section.recommendations)}
        </section>'''

    def _render_key_findings(self, findings: List[str]) -> str:
        if not findings:
            return ""

        items = "".join(f'<div class="finding-item">{f}</div>' for f in findings)
        return f'''
        <div class="key-findings">
            <h3>Evidenze Chiave</h3>
            {items}
        </div>'''

    def _render_data_points(self, data_points: List[DataPoint]) -> str:
        if not data_points:
            return ""

        cards = "".join(self._render_data_card(dp) for dp in data_points)
        return f'''
        <div class="data-grid">
            {cards}
        </div>'''

    def _render_data_card(self, dp: DataPoint) -> str:
        # Badge tipo dato
        type_badge = dp.get_status_badge()

        # Badge confidenza
        conf_badge = dp.get_confidence_badge()

        # Valore
        if dp.value is None:
            value_html = f'<span class="data-value missing">(dato da acquisire)</span>'
        else:
            value_html = f'<span class="data-value">{dp.formatted_value}</span>'

        # Benchmark comparison
        benchmark_html = ""
        if dp.benchmark:
            deviation_html = dp.get_deviation_display()
            benchmark_html = f'''
            <div class="benchmark-row">
                <div class="benchmark-label">Benchmark {dp.benchmark.category}</div>
                <div class="benchmark-comparison">
                    <span class="benchmark-value">{self._format_benchmark_value(dp.benchmark)}</span>
                    {deviation_html}
                </div>
            </div>'''

        # Source citation
        source_html = ""
        if dp.source:
            footnote_num = self._add_footnote(dp.source)
            source_html = f'''
            <div class="source-row">
                <div class="source-citation">
                    {dp.source.to_citation()}
                    <span class="footnote-ref" title="Vedi nota {footnote_num}">[{footnote_num}]</span>
                </div>
            </div>'''

        # Methodology note
        method_html = ""
        if dp.methodology:
            method_html = f'<div class="source-citation" style="margin-top: 5px;">Metodologia: {dp.methodology}</div>'

        return f'''
        <div class="data-card">
            <div class="data-card-header">
                <span class="label">{dp.label}</span>
                <div style="display: flex; gap: 8px;">
                    {type_badge}
                    {conf_badge}
                </div>
            </div>
            <div class="data-card-body">
                <div class="data-value-row">
                    {value_html}
                </div>
                {benchmark_html}
                {source_html}
                {method_html}
            </div>
        </div>'''

    def _format_benchmark_value(self, benchmark: Benchmark) -> str:
        """Formatta il valore del benchmark"""
        val = benchmark.value
        if isinstance(val, (int, float)):
            if val >= 1_000_000:
                return f"{val/1_000_000:.1f}M"
            elif val >= 1_000:
                return f"{val/1_000:.0f}K"
            else:
                return f"{val:,.0f}"
        return str(val)

    def _add_footnote(self, source: Source) -> int:
        """Aggiunge footnote e restituisce numero"""
        self.footnote_counter += 1
        self.footnotes.append({
            "num": self.footnote_counter,
            "citation": source.to_citation(),
            "url": source.url
        })
        return self.footnote_counter

    def _render_recommendations(self, recommendations: List[Dict]) -> str:
        if not recommendations:
            return ""

        cards = ""
        for rec in recommendations:
            priority = rec.get('priority', 'medium')
            cards += f'''
            <div class="recommendation-card">
                <div class="recommendation-priority {priority}"></div>
                <div class="recommendation-content">
                    <div class="recommendation-title">{rec.get('title', 'Raccomandazione')}</div>
                    <div>{rec.get('description', '')}</div>
                    <div class="recommendation-meta">
                        <span>Impatto: {rec.get('impact', 'N/A')}</span>
                        <span>Timeline: {rec.get('timeline', 'N/A')}</span>
                        <span>Investimento: {rec.get('investment_type', 'N/A')}</span>
                    </div>
                </div>
            </div>'''

        return f'''
        <div class="recommendations">
            <h3>Raccomandazioni Strategiche</h3>
            {cards}
        </div>'''

    def _render_bibliography(self, plan: StructuredPlan) -> str:
        if not plan.bibliography:
            return ""

        items = ""
        for i, source in enumerate(plan.bibliography, 1):
            items += f'''
            <div class="bib-item">
                <span class="bib-number">[{i}]</span>
                <div class="bib-content">
                    {source.to_citation()}
                    <span class="bib-type">{source.type.value}</span>
                    {f'<br><a href="{source.url}" target="_blank">{source.url}</a>' if source.url else ''}
                </div>
            </div>'''

        return f'''
        <div class="bibliography">
            <h2>Bibliografia e Fonti</h2>
            {items}
        </div>'''

    def _render_footnotes(self) -> str:
        if not self.footnotes:
            return ""

        items = ""
        for fn in self.footnotes:
            items += f'''
            <div class="footnote-item">
                <span class="footnote-num">[{fn['num']}]</span>
                <span>{fn['citation']}</span>
            </div>'''

        return f'''
        <div class="footnotes">
            <h3>Note</h3>
            {items}
        </div>'''

    def _render_footer(self, plan: StructuredPlan) -> str:
        return f'''
        <footer class="report-footer">
            <div>Rooting Future Strategy Engine v5.4</div>
            <div class="disclaimer">
                Questo documento e stato generato con supporto AI.
                I dati contrassegnati come "stima" o "da acquisire" richiedono verifica.
                Le fonti sono citate nel testo e nella bibliografia.
            </div>
        </footer>'''


# =============================================================================
# COMPARISON TABLE GENERATOR
# =============================================================================

class ComparisonTableGenerator:
    """
    Genera tabelle di confronto benchmark vs dati reali.
    """

    @staticmethod
    def generate_financial_comparison(data_points: List[DataPoint], category: str) -> str:
        """Genera tabella confronto finanziario"""
        from data_models import BenchmarkDatabase

        rows = ""
        for dp in data_points:
            if dp.category != "financial":
                continue

            # Get benchmark
            benchmark = dp.benchmark
            bench_val = benchmark.value if benchmark else "N/A"
            deviation = f"{dp.deviation:+.1f}%" if dp.deviation is not None else "N/A"

            status_class = ""
            if dp.deviation_type:
                status_class = dp.deviation_type.value

            rows += f'''
            <tr class="{status_class}">
                <td><strong>{dp.label}</strong></td>
                <td>{dp.formatted_value or "(da acquisire)"}</td>
                <td>{bench_val}</td>
                <td class="deviation-cell">{deviation}</td>
                <td>{dp.source.to_citation() if dp.source else "N/A"}</td>
                <td>{dp.confidence:.0f}%</td>
            </tr>'''

        return f'''
        <table class="data-table comparison-table">
            <thead>
                <tr>
                    <th>Indicatore</th>
                    <th>Valore Club</th>
                    <th>Benchmark {category}</th>
                    <th>Scostamento</th>
                    <th>Fonte</th>
                    <th>Confidenza</th>
                </tr>
            </thead>
            <tbody>
                {rows}
            </tbody>
        </table>'''


# =============================================================================
# DEMO / TEST
# =============================================================================

def create_demo_plan() -> StructuredPlan:
    """Crea piano demo per test rendering"""
    from data_models import (
        DataPoint, StructuredSection, StructuredPlan,
        DataType, Source, SourceType, Benchmark, BenchmarkDatabase
    )

    # Crea data points di esempio
    fatturato = BenchmarkDatabase.create_data_point_with_benchmark(
        id="fin_001",
        label="Fatturato Annuo",
        value=586424,
        unit="EUR",
        category="Serie C",
        domain="financial",
        metric="fatturato_medio",
        source=Source(
            type=SourceType.OFFICIAL,
            name="Bilancio Depositato 2024",
            reference="Conto Economico",
            verified=True
        ),
        data_type=DataType.VERIFIED,
        confidence=95
    )

    tesserati = BenchmarkDatabase.create_data_point_with_benchmark(
        id="you_001",
        label="Tesserati Settore Giovanile",
        value=None,  # Da acquisire
        unit="unita",
        category="Serie C",
        domain="youth",
        metric="tesserati_giovanili",
        data_type=DataType.TO_ACQUIRE,
        confidence=0
    )

    capienza = BenchmarkDatabase.create_data_point_with_benchmark(
        id="inf_001",
        label="Capienza Stadio",
        value=12200,
        unit="posti",
        category="Serie C",
        domain="infrastructure",
        metric="capienza_stadio",
        source=Source(
            type=SourceType.OFFICIAL,
            name="Scheda Impianto FIGC",
            reference="Agibilita 2024"
        ),
        data_type=DataType.VERIFIED,
        confidence=100
    )

    # Crea sezione
    section = StructuredSection(
        section_id="financial",
        title="Analisi Economico-Finanziaria",
        summary="L'analisi finanziaria evidenzia una situazione critica con fatturato significativamente sotto la media di categoria. E' necessaria una strategia aggressiva di incremento ricavi.",
        key_findings=[
            "Fatturato 87% sotto la media di categoria Serie C",
            "Necessita di ristrutturazione finanziaria urgente",
            "Potenziale di crescita da sponsorizzazioni locali"
        ],
        data_points=[fatturato, tesserati, capienza],
        recommendations=[
            {
                "title": "Piano di Ristrutturazione Finanziaria",
                "description": "Definire un piano triennale per portare il fatturato al 50% della media di categoria",
                "priority": "high",
                "impact": "Alto",
                "timeline": "12-24 mesi",
                "investment_type": "Strategico"
            }
        ]
    )

    # Crea piano
    plan = StructuredPlan(
        plan_id="demo_001",
        club_name="Demo FC",
        category="Serie C",
        executive_summary="Questo piano strategico triennale definisce il percorso di crescita del club con focus su sostenibilita finanziaria, sviluppo del settore giovanile e potenziamento infrastrutturale."
    )
    plan.add_section(section)

    return plan


if __name__ == "__main__":
    # Test
    plan = create_demo_plan()
    renderer = StructuredHTMLRenderer()
    filepath = renderer.render(plan)
    print(f"Report generato: {filepath}")
