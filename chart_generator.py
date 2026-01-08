"""
Chart Generator Module
======================

Genera grafici per i report PDF usando Matplotlib.
Include:
- Pie Chart ricavi
- Bar Chart confronto benchmark
- Data Cards per KPI
"""

import matplotlib
matplotlib.use('Agg')  # Backend non-GUI per server
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.figure import Figure
import io
import base64
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

# Colori coerenti
COLORS = {
    'primary': '#1a365d',
    'secondary': '#3182ce',
    'success': '#38a169',
    'warning': '#dd6b20',
    'danger': '#e53e3e',
    'gray': '#718096',
    'light': '#e2e8f0',
    'pie': ['#3182ce', '#38a169', '#dd6b20', '#9f7aea', '#ed64a6', '#667eea']
}


def set_chart_style():
    """Imposta stile globale per tutti i grafici"""
    plt.style.use('seaborn-v0_8-whitegrid')
    plt.rcParams['font.family'] = 'sans-serif'
    plt.rcParams['font.sans-serif'] = ['Segoe UI', 'Arial', 'Helvetica']
    plt.rcParams['axes.titleweight'] = 'bold'
    plt.rcParams['axes.titlesize'] = 12
    plt.rcParams['axes.labelsize'] = 10
    plt.rcParams['figure.facecolor'] = 'white'


def generate_revenue_pie_chart(
    revenues: Dict[str, float],
    club_name: str,
    primary_color: str = '#1a365d'
) -> str:
    """
    Genera Pie Chart della composizione ricavi.

    Args:
        revenues: Dict con categorie ricavi e valori
        club_name: Nome del club
        primary_color: Colore primario per styling

    Returns:
        Base64 encoded PNG image
    """
    set_chart_style()

    # Filtra valori nulli o zero
    revenues = {k: v for k, v in revenues.items() if v and v > 0}

    if not revenues:
        return ""

    fig, ax = plt.subplots(figsize=(8, 6))

    labels = list(revenues.keys())
    values = list(revenues.values())
    colors = COLORS['pie'][:len(values)]

    # Crea pie chart con percentuali
    wedges, texts, autotexts = ax.pie(
        values,
        labels=None,
        autopct=lambda pct: f'{pct:.1f}%' if pct > 5 else '',
        colors=colors,
        startangle=90,
        pctdistance=0.75,
        explode=[0.02] * len(values)
    )

    # Stile percentuali
    for autotext in autotexts:
        autotext.set_color('white')
        autotext.set_fontweight('bold')
        autotext.set_fontsize(10)

    # Legenda con valori
    legend_labels = [f'{l}: €{v:,.0f}' for l, v in zip(labels, values)]
    ax.legend(
        wedges, legend_labels,
        title="Composizione Ricavi",
        loc="center left",
        bbox_to_anchor=(1, 0, 0.5, 1),
        fontsize=9
    )

    ax.set_title(f'Struttura Ricavi - {club_name}', pad=20, fontsize=14)

    plt.tight_layout()

    return _fig_to_base64(fig)


def generate_benchmark_comparison(
    club_values: Dict[str, float],
    benchmark_values: Dict[str, float],
    club_name: str,
    category: str,
    primary_color: str = '#1a365d'
) -> str:
    """
    Genera Bar Chart confronto club vs benchmark di categoria.

    Args:
        club_values: Valori del club
        benchmark_values: Valori benchmark di categoria
        club_name: Nome del club
        category: Categoria (Serie A, B, C, D, ecc.)
        primary_color: Colore primario

    Returns:
        Base64 encoded PNG image
    """
    set_chart_style()

    # Prepara dati (solo metriche presenti in entrambi)
    metrics = [k for k in club_values if k in benchmark_values]
    if not metrics:
        return ""

    club_vals = [club_values[m] for m in metrics]
    bench_vals = [benchmark_values[m] for m in metrics]

    # Formatta etichette
    labels = [m.replace('_', ' ').title() for m in metrics]

    fig, ax = plt.subplots(figsize=(10, 6))

    x = range(len(metrics))
    width = 0.35

    bars1 = ax.bar([i - width/2 for i in x], club_vals, width,
                   label=club_name, color=primary_color, edgecolor='white')
    bars2 = ax.bar([i + width/2 for i in x], bench_vals, width,
                   label=f'Media {category}', color=COLORS['gray'], edgecolor='white')

    ax.set_ylabel('Valore (€)')
    ax.set_title(f'Confronto con Benchmark {category}', pad=20, fontsize=14)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=45, ha='right')
    ax.legend()

    # Aggiungi valori sopra le barre
    def autolabel(bars):
        for bar in bars:
            height = bar.get_height()
            if height >= 1_000_000:
                label = f'€{height/1_000_000:.1f}M'
            elif height >= 1_000:
                label = f'€{height/1_000:.0f}K'
            else:
                label = f'€{height:.0f}'
            ax.annotate(label,
                       xy=(bar.get_x() + bar.get_width() / 2, height),
                       xytext=(0, 3),
                       textcoords="offset points",
                       ha='center', va='bottom', fontsize=8)

    autolabel(bars1)
    autolabel(bars2)

    # Formatta asse Y
    ax.yaxis.set_major_formatter(lambda x, p: f'€{x/1_000_000:.1f}M' if x >= 1_000_000 else f'€{x/1_000:.0f}K')

    plt.tight_layout()

    return _fig_to_base64(fig)


def generate_gap_analysis_chart(
    gaps: Dict[str, Tuple[float, float]],  # {metric: (club_value, benchmark_value)}
    club_name: str,
    category: str
) -> str:
    """
    Genera grafico analisi gap (differenza % rispetto a benchmark).
    Verde = sopra media, Rosso = sotto media.
    """
    set_chart_style()

    if not gaps:
        return ""

    metrics = list(gaps.keys())
    percentages = []

    for m in metrics:
        club_val, bench_val = gaps[m]
        if bench_val > 0:
            pct = ((club_val - bench_val) / bench_val) * 100
        else:
            pct = 0
        percentages.append(pct)

    fig, ax = plt.subplots(figsize=(10, max(4, len(metrics) * 0.5)))

    colors = [COLORS['success'] if p >= 0 else COLORS['danger'] for p in percentages]
    labels = [m.replace('_', ' ').title() for m in metrics]

    bars = ax.barh(labels, percentages, color=colors, edgecolor='white')

    # Linea zero
    ax.axvline(x=0, color=COLORS['gray'], linestyle='-', linewidth=1)

    # Etichette percentuali
    for bar, pct in zip(bars, percentages):
        width = bar.get_width()
        label = f'+{pct:.0f}%' if pct >= 0 else f'{pct:.0f}%'
        ax.annotate(label,
                   xy=(width, bar.get_y() + bar.get_height()/2),
                   xytext=(5 if width >= 0 else -5, 0),
                   textcoords="offset points",
                   ha='left' if width >= 0 else 'right',
                   va='center', fontweight='bold', fontsize=9)

    ax.set_xlabel('Scostamento da Media Categoria (%)')
    ax.set_title(f'Gap Analysis vs {category}', pad=20, fontsize=14)

    plt.tight_layout()

    return _fig_to_base64(fig)


def generate_data_card_html(
    value: Any,
    label: str,
    icon: str = "",
    trend: str = "",
    tier_badge: str = "",
    color: str = "#1a365d"
) -> str:
    """
    Genera HTML per una Data Card (box colorato per KPI).

    Args:
        value: Valore da visualizzare
        label: Etichetta del KPI
        icon: Emoji o icona
        trend: Testo trend (es. "+5% YoY")
        tier_badge: Badge tier ([STIMA], [DEDOTTO])
        color: Colore primario

    Returns:
        HTML string della data card
    """
    # Formatta valore
    if isinstance(value, (int, float)):
        if value >= 1_000_000:
            formatted_value = f"€{value/1_000_000:.1f}M"
        elif value >= 1_000:
            formatted_value = f"€{value/1_000:.0f}K"
        else:
            formatted_value = f"€{value:,.0f}"
    else:
        formatted_value = str(value)

    tier_html = ""
    if tier_badge:
        badge_color = "#FFC107" if "STIMA" in tier_badge else "#17A2B8"
        tier_html = f'<span style="background:{badge_color};color:#fff;padding:2px 6px;border-radius:4px;font-size:10px;margin-left:8px;">{tier_badge}</span>'

    trend_html = ""
    if trend:
        trend_color = "#38a169" if "+" in trend else "#e53e3e" if "-" in trend else "#718096"
        trend_html = f'<div style="color:{trend_color};font-size:12px;margin-top:4px;">{trend}</div>'

    return f'''
    <div style="background:linear-gradient(135deg,{color},#2d3748);border-radius:12px;padding:20px;color:white;min-width:180px;box-shadow:0 4px 15px rgba(0,0,0,0.1);">
        <div style="font-size:14px;opacity:0.9;margin-bottom:8px;">{icon} {label}</div>
        <div style="font-size:28px;font-weight:700;">{formatted_value}{tier_html}</div>
        {trend_html}
    </div>
    '''


def generate_kpi_dashboard_html(
    kpis: List[Dict],
    columns: int = 4
) -> str:
    """
    Genera dashboard HTML con multiple Data Cards.

    Args:
        kpis: Lista di dict con keys: value, label, icon, trend, tier_badge, color
        columns: Numero di colonne

    Returns:
        HTML string della dashboard
    """
    cards_html = ""
    for kpi in kpis:
        cards_html += generate_data_card_html(
            value=kpi.get('value', 0),
            label=kpi.get('label', ''),
            icon=kpi.get('icon', ''),
            trend=kpi.get('trend', ''),
            tier_badge=kpi.get('tier_badge', ''),
            color=kpi.get('color', '#1a365d')
        )

    return f'''
    <div style="display:grid;grid-template-columns:repeat({columns},1fr);gap:16px;margin:24px 0;">
        {cards_html}
    </div>
    '''


def _fig_to_base64(fig: Figure) -> str:
    """Converte figura Matplotlib in base64 per embedding HTML"""
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=150, bbox_inches='tight',
                facecolor='white', edgecolor='none')
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.getvalue()).decode('utf-8')


def embed_chart_in_html(base64_img: str, alt_text: str = "Chart") -> str:
    """Genera tag img HTML con immagine base64"""
    if not base64_img:
        return ""
    return f'<img src="data:image/png;base64,{base64_img}" alt="{alt_text}" style="max-width:100%;height:auto;margin:20px 0;border-radius:8px;box-shadow:0 2px 10px rgba(0,0,0,0.1);" />'


# =============================================================================
# INTEGRATION FUNCTIONS
# =============================================================================

def generate_financial_charts_for_report(
    club_name: str,
    category: str,
    estimated_financials: Dict,
    primary_color: str = '#1a365d'
) -> Dict[str, str]:
    """
    Genera tutti i grafici finanziari per un report.

    Returns:
        Dict con chiavi: 'revenue_pie', 'benchmark_comparison', 'gap_analysis', 'kpi_dashboard'
        Valori sono HTML strings pronti per embedding
    """
    from data_models import BenchmarkDatabase

    charts = {}

    # Estrai valori
    fatturato = estimated_financials.get('fatturato', {})
    monte_ingaggi = estimated_financials.get('monte_ingaggi', {})
    valore_rosa = estimated_financials.get('valore_rosa', {})

    fat_val = fatturato.value if hasattr(fatturato, 'value') else fatturato.get('value', 0)
    mi_val = monte_ingaggi.value if hasattr(monte_ingaggi, 'value') else monte_ingaggi.get('value', 0)
    vr_val = valore_rosa.value if hasattr(valore_rosa, 'value') else valore_rosa.get('value', 0)

    # 1. Pie Chart Ricavi (stime componenti)
    revenues = {
        'Ricavi Gara': fat_val * 0.25,
        'Sponsor/Commerciale': fat_val * 0.35,
        'Diritti TV/Media': fat_val * 0.20,
        'Settore Giovanile': fat_val * 0.10,
        'Altri Ricavi': fat_val * 0.10
    }
    pie_b64 = generate_revenue_pie_chart(revenues, club_name, primary_color)
    charts['revenue_pie'] = embed_chart_in_html(pie_b64, "Composizione Ricavi")

    # 2. Benchmark Comparison
    benchmarks = BenchmarkDatabase.FINANCIAL_BENCHMARKS.get(category, {})
    if benchmarks:
        club_vals = {
            'fatturato_medio': fat_val,
            'monte_ingaggi_medio': mi_val,
            'costo_rosa_medio': vr_val
        }
        bench_vals = {k: v for k, v in benchmarks.items() if k != 'source'}
        bar_b64 = generate_benchmark_comparison(club_vals, bench_vals, club_name, category, primary_color)
        charts['benchmark_comparison'] = embed_chart_in_html(bar_b64, "Confronto Benchmark")

    # 3. Gap Analysis
    if benchmarks:
        gaps = {
            'fatturato': (fat_val, benchmarks.get('fatturato_medio', fat_val)),
            'monte_ingaggi': (mi_val, benchmarks.get('monte_ingaggi_medio', mi_val)),
            'valore_rosa': (vr_val, benchmarks.get('costo_rosa_medio', vr_val))
        }
        gap_b64 = generate_gap_analysis_chart(gaps, club_name, category)
        charts['gap_analysis'] = embed_chart_in_html(gap_b64, "Gap Analysis")

    # 4. KPI Dashboard
    def get_tier_badge(est):
        if hasattr(est, 'tier'):
            if est.tier.value == 'stimato':
                return '[STIMA]'
            elif est.tier.value == 'dedotto':
                return '[DEDOTTO]'
        return ''

    kpis = [
        {'value': fat_val, 'label': 'Fatturato', 'icon': '💰', 'tier_badge': get_tier_badge(fatturato), 'color': '#1a365d'},
        {'value': mi_val, 'label': 'Monte Ingaggi', 'icon': '👥', 'tier_badge': get_tier_badge(monte_ingaggi), 'color': '#2E7D32'},
        {'value': vr_val, 'label': 'Valore Rosa', 'icon': '⚽', 'tier_badge': get_tier_badge(valore_rosa), 'color': '#1565C0'},
    ]

    # Aggiungi margine se presente
    margine = estimated_financials.get('margine_operativo', {})
    if margine:
        m_val = margine.value if hasattr(margine, 'value') else margine.get('value', 0)
        kpis.append({
            'value': m_val,
            'label': 'Margine Operativo',
            'icon': '📊',
            'tier_badge': get_tier_badge(margine),
            'color': '#38a169' if m_val >= 0 else '#e53e3e'
        })

    charts['kpi_dashboard'] = generate_kpi_dashboard_html(kpis)

    return charts
