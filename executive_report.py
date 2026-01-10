"""
Executive Report A4 Generator
=============================

Genera un report sintetico ottimizzato per stampa A4.
Contiene tutti i dati essenziali senza verbosità.

Struttura (max 6-8 pagine A4):
1. Cover Page con branding club
2. Dashboard Strategica (1 pagina)
3. KPI Finanziari con grafici (1 pagina)
4. Sintesi per Area (4 aree, 1/2 pagina ciascuna = 2 pagine)
5. Timeline e Milestones (1 pagina)
6. Metodologia e Fonti (1 pagina)
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
import re

from data_estimator import estimate_missing_financials, DataTier
from chart_generator import (
    generate_revenue_pie_chart,
    generate_benchmark_comparison,
    generate_gap_analysis_chart,
    embed_chart_in_html
)
from methodology_section import generate_methodology_section_html, get_default_sources_for_report
from data_models import BenchmarkDatabase
from stw_analyzer import calculate_stw_progress
from stw_matrix import get_category_color, get_category_icon, STWCategory


def _clean_text(text: str) -> str:
    """Pulisce il testo da markdown e formattazione."""
    if not text:
        return ""
    # Rimuovi markdown
    text = re.sub(r'\*\*|\*|#{1,4}\s*', '', text)
    # Rimuovi spazi multipli
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def _truncate_text(text: str, max_len: int = 60) -> str:
    """Tronca il testo in modo intelligente (su parola)."""
    if not text or len(text) <= max_len:
        return text
    # Tronca su spazio
    truncated = text[:max_len].rsplit(' ', 1)[0]
    if len(truncated) < max_len * 0.6:
        truncated = text[:max_len]
    return truncated + "..."


def _extract_key_points(content: str, max_points: int = 5) -> List[str]:
    """Estrae i punti chiave da un contenuto markdown.

    Cerca pattern come:
    - **Titolo:** Contenuto che segue...
    - ## 1. Titolo sezione
    - Bullet points significativi
    """
    if not content:
        return []

    points = []

    # Pattern 1: **Titolo:** seguito da contenuto (es. "**Area Strutturale:** Descrizione...")
    # Questo cattura titolo + prima frase del contenuto
    bold_with_content = re.findall(
        r'\*\*([A-Za-zÀ-ÿ][^*]{5,50})(?::\*\*|\*\*:)\s*([^*\n]{10,200})',
        content
    )
    for title, desc in bold_with_content:
        title = _clean_text(title)
        desc = _clean_text(desc)
        # Tronca descrizione alla prima frase
        first_sentence = re.split(r'(?<=[.!?])\s', desc)[0] if desc else ''
        if first_sentence and len(first_sentence) > 15:
            point = f"{title}: {first_sentence}"
            if point not in points:
                points.append(point)
                if len(points) >= max_points:
                    return points

    # Pattern 2: Titoli numerati ## 1. TITOLO
    numbered_titles = re.findall(
        r'#{2,4}\s*\d+\.\s*([A-ZÀ-Ÿ][^\n]{10,80})',
        content
    )
    for title in numbered_titles:
        clean = _clean_text(title)
        if len(clean) > 15 and clean not in points:
            points.append(clean)
            if len(points) >= max_points:
                return points

    # Pattern 3: Bullet points significativi
    bullets = re.findall(r'[-*•]\s+([A-ZÀ-Ÿ][^\n]{20,120})', content)
    for bullet in bullets:
        clean = _clean_text(bullet)
        if len(clean) > 20 and clean not in points and not clean.endswith(':'):
            points.append(clean)
            if len(points) >= max_points:
                return points

    # Fallback: prime frasi complete del documento
    if len(points) < max_points:
        # Rimuovi markdown e split su frasi
        plain = _clean_text(content)
        sentences = re.split(r'(?<=[.!?])\s+', plain)
        for s in sentences:
            s = s.strip()
            if len(s) > 40 and len(s) < 200 and s not in points:
                if s[0].isupper() and not s.endswith(':'):
                    points.append(s)
                    if len(points) >= max_points:
                        break

    return points[:max_points]


def _format_estimated_fields(estimated_fields: Dict[str, str]) -> str:
    """Formatta i campi stimati con badge colorati per tier."""
    if not estimated_fields:
        return '<li>Tutti i campi stimati algoritmicamente</li>'

    result = []
    for k, v in estimated_fields.items():
        label = k.replace("_", " ").title()
        tier_class = "tier-1" if v == "fatto" else "tier-2" if v == "dedotto" else "tier-3"
        result.append(f'<li>{label}: <span class="tier-badge {tier_class}">{v.upper()}</span></li>')

    return ''.join(result)


def _format_timing_badge(metadata: Dict) -> str:
    """Genera badge con timing di generazione per Executive Report"""
    if not metadata:
        return ""

    total_time = metadata.get('total_generation_time')
    if not total_time:
        return ""

    # Format total time
    minutes = int(total_time // 60)
    seconds = int(total_time % 60)
    time_str = f"{minutes}m {seconds}s" if minutes > 0 else f"{seconds}s"

    return f'<div class="timing-badge">⏱️ Generato in {time_str}</div>'


def _generate_stw_dashboard_html(stw_progress: Dict[str, int]) -> str:
    """Genera widget dashboard copertura STW per Executive Report"""

    # Calcola overall
    overall = sum(stw_progress.values()) // len(stw_progress)

    # Progress bars per categoria
    bars_html = ''
    categories = [
        ('sportivi', 'SPORTIVI', STWCategory.SPORTIVI),
        ('strutturali', 'STRUTTURALI', STWCategory.STRUTTURALI),
        ('marketing', 'MARKETING', STWCategory.MARKETING),
        ('sociali', 'SOCIALI', STWCategory.SOCIALI)
    ]

    for key, label, cat_enum in categories:
        prog = stw_progress.get(key, 0)
        color = get_category_color(cat_enum)
        icon = get_category_icon(cat_enum)

        bars_html += f'''
        <div class="stw-row">
            <span class="stw-icon">{icon}</span>
            <span class="stw-label">{label}</span>
            <div class="stw-bar">
                <div class="stw-fill" style="width: {prog}%; background: {color};"></div>
            </div>
            <span class="stw-percent">{prog}%</span>
        </div>
        '''

    return f'''
    <div class="stw-dashboard">
        <div class="stw-header">
            <span>📊 Copertura Matrice STW</span>
            <span class="stw-overall">{overall}%</span>
        </div>
        {bars_html}
        <p class="stw-note">La copertura STW indica la percentuale di obiettivi MACRO e MICRO presenti nel piano.</p>
    </div>
    '''


def _generate_comparison_table_html(estimates: Dict[str, Any], category: str) -> str:
    """Genera tabella confronto Club vs Benchmark per Executive Report"""
    benchmarks = BenchmarkDatabase.FINANCIAL_BENCHMARKS.get(category, {})
    if not benchmarks:
        return ""

    metrics = [
        ('fatturato', 'Fatturato Annuo', '€'),
        ('monte_ingaggi', 'Monte Ingaggi', '€'),
        ('costo_rosa', 'Costo Rosa', '€'),
    ]

    rows_html = ""
    for key, label, unit in metrics:
        est = estimates.get(key)
        if not est:
            continue

        val = est.value
        bench_key = 'fatturato_medio' if key == 'fatturato' else 'monte_ingaggi_medio' if key == 'monte_ingaggi' else 'costo_rosa_medio'
        bench_val = benchmarks.get(bench_key, 0)
        
        # Badge questionario se tier è FATTO (dato certo)
        q_badge = '<span class="badge-questionnaire">📋</span>' if est.tier == DataTier.FATTO else ""
        
        # Formattazione
        val_str = f"{unit}{val/1000000:.1f}M" if val >= 1000000 else f"{unit}{val/1000:.0f}K"
        bench_str = f"{unit}{bench_val/1000000:.1f}M" if bench_val >= 1000000 else f"{unit}{bench_val/1000:.0f}K"
        
        # Calcolo Gap
        gap = 0
        if bench_val > 0:
            gap = ((val - bench_val) / bench_val) * 100
        
        gap_class = "pos" if gap >= -10 else "neg"
        gap_str = f"{gap:+.1f}%"

        rows_html += f'''
        <tr>
            <td>{label} {q_badge}</td>
            <td style="font-weight:700;">{val_str}</td>
            <td style="color:#666;">{bench_str}</td>
            <td class="gap-{gap_class}">{gap_str}</td>
        </tr>
        '''

    return f'''
    <div class="comparison-container">
        <h4 style="margin-bottom:10px; color:#1a365d;">📊 Confronto vs Benchmark {category}</h4>
        <table class="comparison-table">
            <thead>
                <tr>
                    <th>Metrica</th>
                    <th>Club</th>
                    <th>Benchmark</th>
                    <th>Gap</th>
                </tr>
            </thead>
            <tbody>
                {rows_html}
            </tbody>
        </table>
    </div>
    '''


def _generate_questionnaire_box(metadata: Dict[str, Any], club_name: str) -> str:
    """Genera box evidenziato per i questionari compilati"""
    total_q = metadata.get('total_questionnaires', 0)
    verified = metadata.get('verified_data_count', 0)
    completion = metadata.get('questionnaire_completion', 0)

    # Se non ci sono dati, non mostrare il box
    if total_q == 0:
        return ""

    completion_pct = int(completion * 100)

    return f'''
    <div style="background: linear-gradient(135deg, #7B1FA2 0%, #9C27B0 100%);
                padding: 12px; border-radius: 6px; margin-bottom: 15px; color: white;">
        <h4 style="margin: 0 0 8px 0; font-size: 11pt; color: white;">
            ✅ Questionari Compilati dai Membri del Board di {club_name}
        </h4>
        <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; text-align: center;">
            <div>
                <div style="font-size: 20pt; font-weight: 700;">{total_q}</div>
                <div style="font-size: 8pt; opacity: 0.9;">Documenti Word</div>
            </div>
            <div>
                <div style="font-size: 20pt; font-weight: 700;">{verified}+</div>
                <div style="font-size: 8pt; opacity: 0.9;">Dati Forniti</div>
            </div>
            <div>
                <div style="font-size: 20pt; font-weight: 700;">{completion_pct}%</div>
                <div style="font-size: 8pt; opacity: 0.9;">Completezza</div>
            </div>
        </div>
    </div>
    '''


def _extract_objectives_summary(content: str) -> Dict[str, List[str]]:
    """Estrae obiettivi MACRO e MICRO in forma sintetica."""
    result = {'macro': [], 'micro': []}
    if not content:
        return result

    # MACRO: ## N. TITOLO (cattura tutto il titolo)
    macro_pattern = r'#{2,3}\s*\d+\.\s*([A-ZÀ-Ÿ][^\n]{5,80})'
    macro_matches = re.findall(macro_pattern, content)
    for m in macro_matches[:4]:
        clean = _clean_text(m)
        # Mantieni capitalizzazione originale, solo pulisci
        result['macro'].append(clean)  # Nessun troncamento, lascia che CSS gestisca

    # MICRO: ### N.N TITOLO
    micro_pattern = r'#{3,4}\s*\d+\.\d+\s*([A-ZÀ-Ÿ][^\n]{5,60})'
    micro_matches = re.findall(micro_pattern, content)
    for m in micro_matches[:4]:
        clean = _clean_text(m)
        result['micro'].append(clean)  # Nessun troncamento

    return result


def generate_executive_report_html(
    plan_data: Dict[str, str],
    club_name: str,
    category: str,
    metadata: Dict[str, Any],
    sources: List[Dict] = None
) -> str:
    """
    Genera Executive Report HTML ottimizzato per stampa A4.

    Args:
        plan_data: Contenuti delle sezioni del piano
        club_name: Nome del club
        category: Categoria (Serie A, B, C, D, Eccellenza)
        metadata: Metadati inclusi colori, stime finanziarie
        sources: Lista fonti

    Returns:
        HTML completo ottimizzato A4
    """
    current_year = datetime.now().year

    # Colori club
    primary_color = metadata.get('primary_color') or '#1a365d'
    secondary_color = metadata.get('secondary_color') or '#ffffff'

    # Genera varianti colore
    primary_dark = _darken_color(primary_color, 0.2)
    text_on_primary = _get_contrast_color(primary_color)

    # === CALCOLO COPERTURA STW ===
    stw_progress = calculate_stw_progress(plan_data)
    stw_dashboard_html = _generate_stw_dashboard_html(stw_progress)

    # === STIME FINANZIARIE ===
    club_data = {
        'dimensione_rosa': metadata.get('dimensione_rosa', 22),
        'capienza_stadio': metadata.get('capienza_stadio', 0)
    }
    known_financials = metadata.get('known_financials', {})
    estimates = estimate_missing_financials(club_data, category, known_financials)

    # Estrai valori
    fatturato = estimates.get('fatturato')
    monte_ingaggi = estimates.get('monte_ingaggi')
    valore_rosa = estimates.get('valore_rosa')
    margine = estimates.get('margine_operativo')

    fat_val = fatturato.value if fatturato else 0
    mi_val = monte_ingaggi.value if monte_ingaggi else 0
    vr_val = valore_rosa.value if valore_rosa else 0
    marg_val = margine.value if margine else 0

    # === GRAFICI COMPATTI ===
    # Pie chart ricavi
    revenues = {
        'Gara': fat_val * 0.25,
        'Sponsor': fat_val * 0.35,
        'Media': fat_val * 0.20,
        'Altro': fat_val * 0.20
    }
    pie_b64 = generate_revenue_pie_chart(revenues, club_name, primary_color)
    pie_img = f'<img src="data:image/png;base64,{pie_b64}" style="max-width:100%;height:auto;" />' if pie_b64 else ''

    # Gap analysis
    benchmarks = BenchmarkDatabase.FINANCIAL_BENCHMARKS.get(category, {})
    if benchmarks:
        gaps = {
            'Fatturato': (fat_val, benchmarks.get('fatturato_medio', fat_val)),
            'Ingaggi': (mi_val, benchmarks.get('monte_ingaggi_medio', mi_val)),
            'Rosa': (vr_val, benchmarks.get('costo_rosa_medio', vr_val))
        }
        gap_b64 = generate_gap_analysis_chart(gaps, club_name, category)
        gap_img = f'<img src="data:image/png;base64,{gap_b64}" style="max-width:100%;height:auto;" />' if gap_b64 else ''
    else:
        gap_img = ''

    # === SEZIONI SINTETICHE CON POPUP ===
    areas_config = [
        ('technical_sporting', 'Area Sportiva', '⚽', '#2E7D32'),
        ('infrastructure', 'Infrastrutture', '🏗️', '#1565C0'),
        ('marketing_commercial', 'Marketing', '📈', '#F57C00'),
        ('social_sustainability', 'Sociale', '🤝', '#7B1FA2'),
    ]

    areas_html = ""
    modals_html = ""

    for idx, (key, title, icon, color) in enumerate(areas_config):
        content = plan_data.get(key, '')
        objectives = _extract_objectives_summary(content)

        # Preview compatta (max 3 items per colonna)
        # Testo completo con classe CSS per troncamento solo su schermo
        macro_preview = objectives['macro'][:3]
        micro_preview = objectives['micro'][:3]

        macro_preview_html = "".join([f'<li class="truncate-screen">{m}</li>' for m in macro_preview]) or '<li>Da definire</li>'
        micro_preview_html = "".join([f'<li class="truncate-screen">{m}</li>' for m in micro_preview]) or '<li>Da definire</li>'

        # Contenuto completo per il modal (senza troncamento)
        macro_full_html = "".join([f'<li>{m}</li>' for m in objectives['macro']]) or '<li>Da definire</li>'
        micro_full_html = "".join([f'<li>{m}</li>' for m in objectives['micro']]) or '<li>Da definire</li>'

        # Estrai anche punti chiave per il modal
        key_points = _extract_key_points(content, 6)
        key_points_html = "".join([f'<li>{p}</li>' for p in key_points]) if key_points else ''

        modal_id = f"modal-{key}"

        # Card cliccabile (anteprima)
        areas_html += f'''
        <div class="area-box clickable" style="border-left-color:{color};" onclick="openModal('{modal_id}')">
            <div class="area-header">
                <span class="area-icon">{icon}</span>
                <span class="area-title">{title}</span>
                <span class="expand-hint">🔍</span>
            </div>
            <div class="area-content">
                <div class="obj-col">
                    <div class="obj-label macro">MACRO</div>
                    <ul class="obj-list">{macro_preview_html}</ul>
                </div>
                <div class="obj-col">
                    <div class="obj-label micro">MICRO</div>
                    <ul class="obj-list">{micro_preview_html}</ul>
                </div>
            </div>
            <div class="click-hint">Clicca per espandere</div>
        </div>
        '''

        # Modal con contenuto completo
        modals_html += f'''
        <div id="{modal_id}" class="modal">
            <div class="modal-content" style="border-top: 5px solid {color};">
                <span class="modal-close" onclick="closeModal('{modal_id}')">&times;</span>
                <div class="modal-header">
                    <span class="modal-icon">{icon}</span>
                    <h2>{title}</h2>
                </div>
                <div class="modal-body">
                    <div class="modal-section">
                        <h3><span class="obj-label macro">OBIETTIVI MACRO</span></h3>
                        <ul class="modal-list">{macro_full_html}</ul>
                    </div>
                    <div class="modal-section">
                        <h3><span class="obj-label micro">OBIETTIVI MICRO</span></h3>
                        <ul class="modal-list">{micro_full_html}</ul>
                    </div>
                    {f'<div class="modal-section"><h3>Punti Chiave</h3><ul class="modal-list">{key_points_html}</ul></div>' if key_points_html else ''}
                </div>
            </div>
        </div>
        '''

    # === EXECUTIVE SUMMARY ESTRATTO ===
    exec_summary = plan_data.get('executive_summary', '')
    exec_points = _extract_key_points(exec_summary, 5)
    exec_html = "".join([f'<li>{p}</li>' for p in exec_points]) if exec_points else '<li>Executive summary non disponibile</li>'

    # === TIMELINE ===
    timeline_html = f'''
    <div class="timeline">
        <div class="timeline-item">
            <div class="timeline-marker" style="background:{primary_color};">Y1</div>
            <div class="timeline-content">
                <strong>Anno 1 - Fondamenta</strong>
                <p>Consolidamento strutturale, audit processi, setup governance</p>
            </div>
        </div>
        <div class="timeline-item">
            <div class="timeline-marker" style="background:{primary_color};">Y2</div>
            <div class="timeline-content">
                <strong>Anno 2 - Crescita</strong>
                <p>Espansione commerciale, sviluppo settore giovanile, investimenti infrastrutturali</p>
            </div>
        </div>
        <div class="timeline-item">
            <div class="timeline-marker" style="background:{primary_color};">Y3</div>
            <div class="timeline-content">
                <strong>Anno 3 - Consolidamento</strong>
                <p>Sostenibilità finanziaria, obiettivi sportivi, legacy territoriale</p>
            </div>
        </div>
    </div>
    '''

    # === METODOLOGIA COMPATTA ===
    # Genera campi stimati dalle stime effettive
    estimated_fields = metadata.get('estimated_fields', {})
    if not estimated_fields:
        # Usa le stime calcolate per mostrare i tier
        estimated_fields = {}
        if fatturato:
            estimated_fields['fatturato'] = fatturato.tier.value
        if monte_ingaggi:
            estimated_fields['monte_ingaggi'] = monte_ingaggi.tier.value
        if valore_rosa:
            estimated_fields['valore_rosa'] = valore_rosa.tier.value
        if margine:
            estimated_fields['margine_operativo'] = margine.tier.value

    # === HTML FINALE ===
    html = f'''<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <title>Executive Report - {club_name}</title>
    <style>
        @page {{
            size: A4;
            margin: 15mm;
        }}

        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: 'Segoe UI', Arial, sans-serif;
            font-size: 10pt;
            line-height: 1.4;
            color: #333;
            background: white;
        }}

        /* === COVER PAGE === */
        .cover {{
            height: 100vh;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            background: linear-gradient(135deg, {primary_color}, {primary_dark});
            color: {text_on_primary};
            text-align: center;
        }}

        .cover h1 {{
            font-size: 28pt;
            margin-bottom: 10px;
            text-transform: uppercase;
            letter-spacing: 3px;
        }}

        .cover .subtitle {{
            font-size: 14pt;
            opacity: 0.9;
            margin-bottom: 30px;
        }}

        .cover .period {{
            font-size: 18pt;
            font-weight: 700;
            background: {secondary_color};
            color: {primary_color};
            padding: 10px 30px;
            border-radius: 30px;
            margin-bottom: 40px;
        }}

        .cover .category {{
            font-size: 12pt;
            opacity: 0.8;
        }}

        .cover .generated {{
            position: absolute;
            bottom: 30px;
            font-size: 9pt;
            opacity: 0.7;
        }}

        .timing-badge {{
            position: absolute;
            bottom: 70px;
            left: 50%;
            transform: translateX(-50%);
            padding: 6px 14px;
            background: rgba(255, 255, 255, 0.15);
            border-radius: 16px;
            font-size: 9pt;
            font-weight: 500;
            backdrop-filter: blur(10px);
        }}

        /* === PAGE SECTIONS === */
        .page {{
            padding: 8mm 0;
        }}

        .page-break {{
            page-break-after: always;
        }}

        .page-title {{
            background: {primary_color};
            color: {text_on_primary};
            padding: 12px 20px;
            font-size: 14pt;
            font-weight: 700;
            margin-bottom: 15px;
            border-radius: 4px;
        }}

        .page-title .icon {{
            margin-right: 10px;
        }}

        /* === KPI CARDS === */
        .kpi-grid {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 10px;
            margin-bottom: 20px;
        }}

        .kpi-card {{
            background: linear-gradient(135deg, {primary_color}, {primary_dark});
            color: {text_on_primary};
            padding: 15px;
            border-radius: 8px;
            text-align: center;
        }}

        .kpi-card .value {{
            font-size: 18pt;
            font-weight: 700;
        }}

        .kpi-card .label {{
            font-size: 8pt;
            opacity: 0.9;
            margin-top: 5px;
        }}

        .kpi-card .tier {{
            font-size: 7pt;
            background: rgba(255,255,255,0.2);
            padding: 2px 6px;
            border-radius: 3px;
            margin-top: 5px;
            display: inline-block;
        }}

        /* === CHARTS === */
        .charts-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 15px;
        }}

        .chart-box {{
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            padding: 10px;
        }}

        .chart-box h4 {{
            font-size: 10pt;
            color: {primary_color};
            margin-bottom: 10px;
            text-align: center;
        }}

        .chart-box img {{
            max-width: 100%;
            height: auto;
        }}

        /* === AREAS === */
        .areas-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 12px;
        }}

        .area-box {{
            border: 1px solid #e0e0e0;
            border-left: 4px solid;
            border-radius: 0 8px 8px 0;
            padding: 10px;
            background: #fafafa;
            page-break-inside: avoid;
        }}

        .area-header {{
            display: flex;
            align-items: center;
            gap: 6px;
            margin-bottom: 8px;
            padding-bottom: 6px;
            border-bottom: 1px solid #e0e0e0;
        }}

        .area-icon {{
            font-size: 14pt;
        }}

        .area-title {{
            font-weight: 700;
            font-size: 10pt;
        }}

        .area-content {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 8px;
            margin-bottom: 8px;
        }}

        .obj-col {{
            min-width: 0; /* Permette al contenuto di restringersi */
        }}

        .obj-label {{
            font-size: 6pt;
            font-weight: 700;
            padding: 2px 5px;
            border-radius: 3px;
            display: inline-block;
            margin-bottom: 4px;
        }}

        .obj-label.macro {{
            background: #C8E6C9;
            color: #2E7D32;
        }}

        .obj-label.micro {{
            background: #FFF9C4;
            color: #F57F17;
        }}

        .obj-list {{
            font-size: 7pt;
            padding-left: 12px;
            margin: 0;
            word-wrap: break-word;
            overflow-wrap: break-word;
            hyphens: auto;
        }}

        .obj-list li {{
            margin-bottom: 3px;
            line-height: 1.25;
        }}

        /* Troncamento solo su schermo, non in print */
        .obj-list li.truncate-screen {{
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            max-width: 100%;
        }}

        /* === CLICKABLE CARDS === */
        .area-box.clickable {{
            cursor: pointer;
            transition: all 0.2s ease;
            position: relative;
        }}

        .area-box.clickable:hover {{
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            border-color: #999;
        }}

        .expand-hint {{
            margin-left: auto;
            font-size: 12pt;
            opacity: 0.5;
        }}

        .area-box.clickable:hover .expand-hint {{
            opacity: 1;
        }}

        .click-hint {{
            text-align: center;
            font-size: 7pt;
            color: #999;
            margin-top: 5px;
            font-style: italic;
        }}

        /* === MODAL POPUP === */
        .modal {{
            display: none;
            position: fixed;
            z-index: 1000;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0,0,0,0.6);
            backdrop-filter: blur(3px);
        }}

        .modal.active {{
            display: flex;
            align-items: center;
            justify-content: center;
        }}

        .modal-content {{
            background: white;
            width: 90%;
            max-width: 700px;
            max-height: 85vh;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            animation: modalSlideIn 0.3s ease;
        }}

        @keyframes modalSlideIn {{
            from {{
                opacity: 0;
                transform: translateY(-30px) scale(0.95);
            }}
            to {{
                opacity: 1;
                transform: translateY(0) scale(1);
            }}
        }}

        .modal-close {{
            position: absolute;
            right: 20px;
            top: 15px;
            font-size: 28px;
            font-weight: bold;
            color: #666;
            cursor: pointer;
            z-index: 10;
        }}

        .modal-close:hover {{
            color: #000;
        }}

        .modal-header {{
            padding: 20px 25px;
            background: #f8f9fa;
            border-bottom: 1px solid #e0e0e0;
            display: flex;
            align-items: center;
            gap: 12px;
            position: relative;
        }}

        .modal-icon {{
            font-size: 28pt;
        }}

        .modal-header h2 {{
            margin: 0;
            font-size: 18pt;
            color: #333;
        }}

        .modal-body {{
            padding: 25px;
            max-height: 60vh;
            overflow-y: auto;
        }}

        .modal-section {{
            margin-bottom: 20px;
        }}

        .modal-section:last-child {{
            margin-bottom: 0;
        }}

        .modal-section h3 {{
            font-size: 11pt;
            margin-bottom: 10px;
            color: #444;
        }}

        .modal-list {{
            padding-left: 20px;
            margin: 0;
        }}

        .modal-list li {{
            margin-bottom: 8px;
            font-size: 10pt;
            line-height: 1.5;
        }}



        /* === EXECUTIVE SUMMARY === */
        .exec-box {{
            background: {primary_color}10;
            border-left: 4px solid {primary_color};
            padding: 15px;
            border-radius: 0 8px 8px 0;
        }}

        .exec-box ul {{
            padding-left: 20px;
        }}

        .exec-box li {{
            margin-bottom: 8px;
        }}

        /* === TIMELINE === */
        .timeline {{
            display: flex;
            justify-content: space-between;
            margin: 20px 0;
        }}

        .timeline-item {{
            flex: 1;
            text-align: center;
            padding: 0 10px;
        }}

        .timeline-marker {{
            width: 50px;
            height: 50px;
            border-radius: 50%;
            color: white;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 700;
            font-size: 14pt;
            margin: 0 auto 10px;
        }}

        .timeline-content {{
            font-size: 9pt;
        }}

        .timeline-content strong {{
            display: block;
            margin-bottom: 5px;
            color: {primary_color};
        }}

        /* === METHODOLOGY === */
        .method-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 15px;
        }}

        .method-box {{
            background: #f5f5f5;
            padding: 12px;
            border-radius: 8px;
        }}

        .method-box h4 {{
            font-size: 10pt;
            color: {primary_color};
            margin-bottom: 8px;
        }}

        .tier-legend {{
            display: flex;
            gap: 15px;
            margin-top: 15px;
        }}

        .tier-item {{
            display: flex;
            align-items: center;
            gap: 5px;
            font-size: 8pt;
        }}

        .tier-badge {{
            padding: 2px 8px;
            border-radius: 3px;
            font-size: 7pt;
            font-weight: 700;
        }}

        .tier-1 {{ background: #C8E6C9; color: #2E7D32; }}
        .tier-2 {{ background: #BBDEFB; color: #1565C0; }}
        .tier-3 {{ background: #FFF9C4; color: #F57F17; }}

        .disclaimer {{
            background: #fff8e1;
            border: 1px solid #ffcc02;
            padding: 10px;
            border-radius: 4px;
            font-size: 8pt;
            margin-top: 15px;
        }}

        /* === FOOTER === */
        .footer {{
            text-align: center;
            font-size: 8pt;
            color: #999;
            margin-top: 20px;
            padding-top: 10px;
            border-top: 1px solid #e0e0e0;
        }}

        /* === STW DASHBOARD === */
        .stw-dashboard {{
            background: #f8f9fa;
            border-radius: 8px;
            padding: 15px;
            margin-top: 15px;
        }}

        .stw-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 12px;
            padding-bottom: 10px;
            border-bottom: 2px solid #e0e0e0;
            font-weight: 600;
            font-size: 10pt;
        }}

        .stw-overall {{
            font-size: 18pt;
            font-weight: 700;
            color: #38a169;
        }}

        .stw-row {{
            display: grid;
            grid-template-columns: 20px 100px 1fr 50px;
            align-items: center;
            gap: 10px;
            margin-bottom: 8px;
        }}

        .stw-icon {{
            font-size: 12pt;
            text-align: center;
        }}

        .stw-label {{
            font-size: 8pt;
            font-weight: 600;
            color: #333;
        }}

        .stw-bar {{
            height: 16px;
            background: #e9ecef;
            border-radius: 8px;
            overflow: hidden;
        }}

        .stw-fill {{
            height: 100%;
            transition: width 0.6s ease;
        }}

        .stw-percent {{
            font-size: 8pt;
            font-weight: 700;
            text-align: right;
        }}

        .stw-note {{
            font-size: 7pt;
            color: #666;
            margin-top: 10px;
            font-style: italic;
        }}

        /* === QUESTIONNAIRE BADGE === */
        .badge-questionnaire {{
            background: linear-gradient(135deg, #7B1FA2, #9C27B0);
            color: white;
            padding: 1px 6px;
            border-radius: 10px;
            font-size: 7pt;
            font-weight: 700;
            margin-left: 5px;
            display: inline-flex;
            align-items: center;
        }}

        /* === COMPARISON TABLE === */
        .comparison-container {{
            margin-top: 15px;
        }}

        .comparison-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 8pt;
        }}

        .comparison-table th {{
            background: #f1f3f5;
            padding: 6px 10px;
            text-align: left;
            border-bottom: 2px solid #dee2e6;
        }}

        .comparison-table td {{
            padding: 8px 10px;
            border-bottom: 1px solid #dee2e6;
        }}

        .gap-pos {{ color: #38a169; font-weight: 700; }}
        .gap-neg {{ color: #e53e3e; font-weight: 700; }}

        /* ================================================================
           RESPONSIVE STYLES - Mobile & Tablet
           ================================================================ */

        /* Tablet */
        @media (max-width: 1024px) {{
            .kpi-grid {{
                grid-template-columns: repeat(2, 1fr);
            }}
            .stw-row {{
                grid-template-columns: 18px 90px 1fr 45px;
                gap: 8px;
            }}
        }}

        /* Mobile */
        @media (max-width: 768px) {{
            body {{
                font-size: 9pt;
            }}
            .cover h1 {{
                font-size: 22pt;
            }}
            .cover .period {{
                font-size: 14pt;
            }}
            .page-title {{
                font-size: 12pt;
                padding: 10px 15px;
            }}
            .kpi-grid {{
                grid-template-columns: 1fr;
                gap: 8px;
            }}
            .kpi-card {{
                padding: 12px;
            }}
            .charts-grid {{
                grid-template-columns: 1fr;
            }}
            .areas-grid {{
                grid-template-columns: 1fr;
            }}
            .stw-dashboard {{
                padding: 12px;
            }}
            .stw-row {{
                grid-template-columns: 16px 75px 1fr 40px;
                gap: 6px;
                margin-bottom: 6px;
            }}
            .stw-icon {{
                font-size: 10pt;
            }}
            .stw-label {{
                font-size: 7pt;
            }}
            .stw-percent {{
                font-size: 7pt;
            }}
            .stw-overall {{
                font-size: 14pt;
            }}
        }}

        /* Mobile Small */
        @media (max-width: 480px) {{
            .cover h1 {{
                font-size: 18pt;
            }}
            .cover .subtitle {{
                font-size: 11pt;
            }}
            .stw-row {{
                grid-template-columns: 14px 60px 1fr 35px;
                gap: 4px;
            }}
            .stw-label {{
                font-size: 6pt;
            }}
        }}

        /* ================================================================
           PRINT STYLES - Executive Report A4 Ottimizzato
           ================================================================ */
        @media print {{
            /* === NASCONDI ELEMENTI INTERATTIVI === */
            .modal,
            .click-hint,
            .expand-hint,
            button {{
                display: none !important;
            }}

            /* === FORZA COLORI === */
            * {{
                -webkit-print-color-adjust: exact !important;
                print-color-adjust: exact !important;
            }}

            body {{
                background: white !important;
                font-size: 10pt !important;
            }}

            /* === COVER PAGE === */
            .cover {{
                height: 100vh;
                break-after: page;
            }}

            /* === PAGE BREAKS === */
            .page-break {{
                break-after: page !important;
                page-break-after: always !important;
            }}

            .page {{
                padding: 0 !important;
            }}

            /* === ELEMENTI NON SPEZZABILI === */
            .no-break,
            .kpi-card,
            .kpi-grid,
            .chart-box,
            .area-box,
            .exec-box,
            .method-box,
            .timeline,
            .stw-dashboard,
            .disclaimer {{
                break-inside: avoid !important;
                page-break-inside: avoid !important;
            }}

            /* === TITOLI === */
            .page-title,
            h2, h3, h4 {{
                break-after: avoid !important;
                page-break-after: avoid !important;
            }}

            /* === CARD AREE CLICCABILI === */
            .area-box.clickable {{
                cursor: default;
            }}

            .area-box.clickable:hover {{
                transform: none !important;
                box-shadow: none !important;
            }}

            /* === RIMUOVI TRONCAMENTO === */
            .obj-list li.truncate-screen {{
                white-space: normal !important;
                overflow: visible !important;
                text-overflow: clip !important;
                word-wrap: break-word !important;
            }}

            /* === GRAFICI === */
            .charts-grid {{
                break-inside: avoid !important;
            }}

            .chart-box img {{
                max-width: 100% !important;
                height: auto !important;
            }}

            /* === BOX SHADOW REMOVAL === */
            .kpi-card,
            .chart-box,
            .area-box,
            .method-box {{
                box-shadow: none !important;
            }}

            /* === REGOLA @PAGE === */
            @page {{
                size: A4;
                margin: 15mm;
            }}
        }}
    </style>
</head>
<body>

<!-- PAGINA 1: COVER -->
<div class="cover page-break">
    <h1>{club_name}</h1>
    <div class="subtitle">Piano Strategico Triennale</div>
    <div class="period">{current_year} - {current_year + 3}</div>
    <div class="category">{category}</div>
    {_format_timing_badge(metadata)}
    <div class="generated">
        Executive Report generato da Rooting Future Strategy Engine v5.4<br>
        {datetime.now().strftime('%d/%m/%Y')}
    </div>
</div>

<!-- PAGINA 2: EXECUTIVE SUMMARY + KPI + GRAFICI -->
<div class="page page-break">
    <div class="page-title"><span class="icon">📋</span> Executive Summary</div>
    <div class="exec-box">
        <ul>{exec_html}</ul>
    </div>

    <div class="page-title" style="margin-top:15px;"><span class="icon">💰</span> Quadro Finanziario</div>
    <div class="kpi-grid">
        <div class="kpi-card">
            <div class="value">€{fat_val/1_000_000:.1f}M</div>
            <div class="label">Fatturato</div>
            <div class="tier">{fatturato.tier.value.upper() if fatturato else 'N/A'}</div>
        </div>
        <div class="kpi-card">
            <div class="value">€{mi_val/1_000:.0f}K</div>
            <div class="label">Monte Ingaggi</div>
            <div class="tier">{monte_ingaggi.tier.value.upper() if monte_ingaggi else 'N/A'}</div>
        </div>
        <div class="kpi-card">
            <div class="value">€{vr_val/1_000:.0f}K</div>
            <div class="label">Valore Rosa</div>
            <div class="tier">{valore_rosa.tier.value.upper() if valore_rosa else 'N/A'}</div>
        </div>
        <div class="kpi-card" style="background:{'linear-gradient(135deg,#38a169,#2f855a)' if marg_val >= 0 else 'linear-gradient(135deg,#e53e3e,#c53030)'};">
            <div class="value">€{marg_val/1_000:.0f}K</div>
            <div class="label">Margine Op.</div>
            <div class="tier">{margine.tier.value.upper() if margine else 'N/A'}</div>
        </div>
    </div>

    {_generate_comparison_table_html(estimates, category)}

    <div class="charts-grid">
        <div class="chart-box">
            <h4>Composizione Ricavi</h4>
            {pie_img}
        </div>
        <div class="chart-box">
            <h4>Gap vs Benchmark {category}</h4>
            {gap_img}
        </div>
    </div>

    {stw_dashboard_html}
</div>

<!-- PAGINA 3: AREE STRATEGICHE + ROADMAP -->
<div class="page page-break">
    <div class="page-title"><span class="icon">🎯</span> Aree Strategiche</div>
    <div class="areas-grid">
        {areas_html}
    </div>

    <div class="page-title" style="margin-top:15px;"><span class="icon">📅</span> Roadmap Triennale</div>
    {timeline_html}
</div>

<!-- PAGINA 4: METODOLOGIA (ultima, senza page-break) -->
<div class="page">
    <div class="page-title"><span class="icon">📊</span> Metodologia e Fonti</div>

    {_generate_questionnaire_box(metadata, club_name)}

    <div class="method-grid">
        <div class="method-box">
            <h4>Fonti Dati</h4>
            <ul style="font-size:8pt;padding-left:15px;">
                <li><strong>FIGC Report Calcio 2024</strong> - Benchmark ufficiali</li>
                <li><strong>Transfermarkt</strong> - Valori rosa, statistiche</li>
                <li><strong>Web Research</strong> - News, bilanci pubblici</li>
                <li><strong>Knowledge Base</strong> - Documenti caricati</li>
            </ul>
        </div>
        <div class="method-box">
            <h4>Campi Stimati</h4>
            <ul style="font-size:8pt;padding-left:15px;">
                {_format_estimated_fields(estimated_fields)}
            </ul>
        </div>
    </div>

    <div class="tier-legend">
        <div class="tier-item"><span class="tier-badge tier-1">FATTO</span> Dato verificato</div>
        <div class="tier-item"><span class="tier-badge tier-2">DEDOTTO</span> Calcolato</div>
        <div class="tier-item"><span class="tier-badge tier-3">STIMA</span> Benchmark</div>
    </div>

    <div class="disclaimer">
        <strong>⚠️ Disclaimer:</strong> I dati contrassegnati [STIMA] hanno natura indicativa.
        Si raccomanda verifica con fonti ufficiali prima di decisioni strategiche.
    </div>

    <div class="footer">
        🤖 Generato da <strong>Rooting Future Strategy Engine v5.4</strong> |
        {datetime.now().strftime('%d/%m/%Y %H:%M')} |
        Per il piano completo vedere documento esteso
    </div>
</div>

<!-- MODALS -->
{modals_html}

<script>
function openModal(modalId) {{
    document.getElementById(modalId).classList.add('active');
    document.body.style.overflow = 'hidden';
}}

function closeModal(modalId) {{
    document.getElementById(modalId).classList.remove('active');
    document.body.style.overflow = 'auto';
}}

// Chiudi modal cliccando fuori
document.addEventListener('click', function(e) {{
    if (e.target.classList.contains('modal')) {{
        e.target.classList.remove('active');
        document.body.style.overflow = 'auto';
    }}
}});

// Chiudi modal con ESC
document.addEventListener('keydown', function(e) {{
    if (e.key === 'Escape') {{
        document.querySelectorAll('.modal.active').forEach(m => {{
            m.classList.remove('active');
        }});
        document.body.style.overflow = 'auto';
    }}
}});
</script>

</body>
</html>
'''

    return html


def _darken_color(hex_color: str, factor: float = 0.2) -> str:
    """Scurisce un colore hex."""
    hex_color = hex_color.lstrip('#')
    r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    r = int(r * (1 - factor))
    g = int(g * (1 - factor))
    b = int(b * (1 - factor))
    return f'#{r:02x}{g:02x}{b:02x}'


def _get_contrast_color(hex_color: str) -> str:
    """Restituisce bianco o nero per contrasto ottimale."""
    hex_color = hex_color.lstrip('#')
    r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
    return '#ffffff' if luminance < 0.5 else '#1a1a1a'
