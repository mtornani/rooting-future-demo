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

from export_styles import RF_FONT_IMPORT, RF_BADGE_CSS, RF_RESET_CSS, RF_MACRO_CSS, RF_PRINT_CSS_A4
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
    """Formatta i campi stimati con badge colorati leggibili."""
    if not estimated_fields:
        return '<li>Dati elaborati su benchmark di categoria</li>'

    _TIER_LABEL = {
        "tier1_fact": "Verificato", "fatto": "Verificato",
        "tier2_deduced": "Calcolato", "dedotto": "Calcolato",
        "tier3_estimated": "Stimato", "stimato": "Stimato",
    }
    _TIER_CLASS = {
        "tier1_fact": "tier-1", "fatto": "tier-1",
        "tier2_deduced": "tier-2", "dedotto": "tier-2",
        "tier3_estimated": "tier-3", "stimato": "tier-3",
    }
    result = []
    for k, v in estimated_fields.items():
        label = k.replace("_", " ").title()
        badge_label = _TIER_LABEL.get(v, "Stimato")
        tier_class = _TIER_CLASS.get(v, "tier-3")
        result.append(f'<li>{label}: <span class="tier-badge {tier_class}">{badge_label}</span></li>')

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
    overall = sum(stw_progress.values()) // len(stw_progress) if stw_progress else 0

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
        <p class="stw-note">Copertura proporzionale alla profondità dell'analisi per area. Per la lista completa di obiettivi MACRO/MICRO consultare il Piano Strategico Completo.</p>
    </div>
    '''


def _generate_comparison_table_html(estimates: Dict[str, Any], category: str) -> str:
    """Genera tabella confronto Club vs Benchmark per Executive Report con fonte esplicita"""
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
        
        # Determina Fonte Esplicita
        source_label = "Stima AI"
        source_class = "source-est"
        source_icon = "📊"
        
        if est.tier == DataTier.TIER_1_FACT:
            source_label = "Questionario Board"
            source_class = "source-ver"
            source_icon = "📋"
        elif est.tier == DataTier.TIER_2_DEDUCED:
            source_label = "Dedotto da Parametri"
            source_class = "source-ded"
            source_icon = "🔍"
        
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
            <td><strong>{label}</strong></td>
            <td style="font-weight:700;">{val_str}</td>
            <td style="color:#666;">{bench_str}</td>
            <td class="gap-{gap_class}">{gap_str}</td>
            <td><span class="source-badge {source_class}">{source_icon} {source_label}</span></td>
        </tr>
        '''

    return f'''
    <div class="comparison-container">
        <h4 style="margin-bottom:10px; color:#1a365d;">📊 Confronto vs Benchmark {category}</h4>
        <table class="comparison-table">
            <thead>
                <tr>
                    <th width="25%">Metrica</th>
                    <th width="15%">Club</th>
                    <th width="15%">Benchmark</th>
                    <th width="15%">Gap</th>
                    <th width="30%">Fonte Dato</th>
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
    """Estrae obiettivi MACRO e MICRO in forma sintetica con fallback aggressivi."""
    result = {'macro': [], 'micro': []}
    if not content:
        return result

    # --- MACRO OBIETTIVI ---
    # 1. Cerca header ## numerati o non
    macro_matches = re.findall(r'##\s*(?:\d+\.)?\s*([A-ZÀ-Ÿ].{5,80})', content)
    
    # 2. Se pochi header, cerca bold line all'inizio di paragrafi (case-insensitive)
    if len(macro_matches) < 2:
        bold_matches = re.findall(r'\n\*\*(?:\d+\.)?\s*([A-Za-zÀ-ÿ].{5,60})\*\*', content)
        macro_matches.extend(bold_matches)
    # 3. Fallback: bullet points come macro se ancora vuoto
    if len(macro_matches) < 2:
        bullet_macro = re.findall(r'[-*•]\s+([A-Za-zÀ-ÿ].{15,120})', content)
        macro_matches.extend(bullet_macro)

    for m in macro_matches[:4]:
        clean = _clean_text(m).split(':')[0] # Prendi solo parte prima dei due punti
        if len(clean) > 5:
            result['macro'].append(clean)

    # --- MICRO OBIETTIVI ---
    # 1. Cerca header ###
    micro_matches = re.findall(r'###\s*(?:\d+\.\d+)?\s*([A-ZÀ-Ÿ].{5,80})', content)
    
    # 2. Se pochi header, cerca bullet points forti (case-insensitive per AI output)
    if len(micro_matches) < 2:
        bullet_matches = re.findall(r'[-*•]\s+([A-Za-zÀ-ÿ].{10,100})', content)
        micro_matches.extend(bullet_matches)

    for m in micro_matches[:4]:
        clean = _clean_text(m).split(':')[0]
        if len(clean) > 5:
            result['micro'].append(clean)

    # Fallback finale se vuoto
    if not result['macro']:
        result['macro'] = ["Definizione obiettivi strategici", "Consolidamento societario"]
    if not result['micro']:
        result['micro'] = ["Analisi operativa", "Sviluppo risorse umane"]

    return result


def _extract_timeline_from_plan(plan_data: Dict) -> list:
    """
    Estrae roadmap triennale dal piano AI.
    Ritorna lista di (marker, titolo, descrizione) o [] se non trovato.
    """
    for key in ['roadmap', 'piano_triennale', 'strategic_roadmap', 'timeline']:
        content = plan_data.get(key, '')
        if content and len(content) > 100:
            # Formato markdown table: | Anno 1 | Titolo | Desc |
            table_blocks = re.findall(
                r'\|\s*(?:Anno|Year)\s*(\d)[^|]*\|\s*([^|\n]{5,120})\|(?:\s*([^|\n]{5,250})\|)?',
                content, re.IGNORECASE
            )
            if len(table_blocks) >= 2:
                return [(f'Y{b[0]}', _clean_text(b[1]), _clean_text(b[2] or '')) for b in table_blocks[:3]]

            # Formato standard: Anno 1: Titolo\nDescrizione
            blocks = re.findall(
                r'(?:Anno|Year)\s*(\d)[:\s\-–—]*([^\n]{5,200})(?:\n([^\n]{20,250}))?',
                content, re.IGNORECASE
            )
            if len(blocks) >= 2:
                return [(f'Y{b[0]}', _clean_text(b[1]), _clean_text((b[2] or '').strip())) for b in blocks[:3]]

    # Fallback: cerca nell'executive summary
    exec_s = plan_data.get('executive_summary', '') or plan_data.get('coordinator_summary', '')
    if exec_s:
        blocks = re.findall(
            r'(?:Anno|Triennio|Year)\s*(\d)[:\s\-–—]*([^\n.]{10,200})',
            exec_s, re.IGNORECASE
        )
        if len(blocks) >= 2:
            return [(f'Y{b[0]}', _clean_text(b[1]), '') for b in blocks[:3]]
    return []


def _stw_from_content_proxy(plan_data: Dict) -> Dict[str, int]:
    """
    Proxy copertura STW basata su lunghezza contenuto per categoria.
    Usato perché calculate_stw_progress() richiede codici MACRO che l'AI non scrive.
    """
    mapping = {
        'sportivi':    ['stw_sportivi', 'technical_sporting'],
        'strutturali': ['stw_strutturali', 'infrastructure'],
        'marketing':   ['stw_marketing', 'marketing_commercial'],
        'sociali':     ['stw_sociali', 'social_sustainability'],
    }
    result = {}
    for cat, keys in mapping.items():
        chars = sum(len(plan_data.get(k, '')) for k in keys)
        result[cat] = min(90, int(chars / 40)) if chars > 200 else 0
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
    # Proxy basata su contenuto: calculate_stw_progress richiede codici MACRO che l'AI non produce
    stw_progress = _stw_from_content_proxy(plan_data)
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
        key_points = _extract_key_points(content, 4)
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
    exec_points = _extract_key_points(exec_summary, 3)
    exec_html = "".join([f'<li>{p}</li>' for p in exec_points]) if exec_points else '<li>Executive summary non disponibile</li>'

    # === TIMELINE ===
    # Estrai roadmap dal piano reale
    timeline_items = _extract_timeline_from_plan(plan_data)
    is_plan_derived = bool(timeline_items)
    if not timeline_items:
        timeline_items = [
            ('Y1', f'Anno 1 ({current_year})', 'Consolidamento strutturale, governance e audit processi'),
            ('Y2', f'Anno 2 ({current_year + 1})', 'Crescita commerciale e sviluppo settore giovanile'),
            ('Y3', f'Anno 3 ({current_year + 2})', 'Sostenibilità finanziaria e legacy territoriale'),
        ]
    timeline_note = '' if is_plan_derived else '<p style="font-size:8pt; color:#718096; font-style:italic; margin-top:10px;">⚠️ Schema indicativo triennale — le milestone specifiche sono nel Piano Strategico Completo.</p>'
    timeline_items_html = ''.join(f'''
        <div class="timeline-item">
            <div class="timeline-marker" style="background:{primary_color};">{marker}</div>
            <div class="timeline-content">
                <strong>{title}</strong>
                {f"<p>{desc}</p>" if desc else ""}
            </div>
        </div>''' for marker, title, desc in timeline_items)
    timeline_html = f'<div class="timeline">{timeline_items_html}</div>{timeline_note}'

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
    <title>Report Esecutivo - {club_name}</title>
    {RF_FONT_IMPORT}
    <style>
        :root {{
            --primary: {primary_color};
            --primary-dark: {primary_dark};
            --secondary: {secondary_color};
            --accent: {primary_color};
            --text: #1a202c;
            --text-light: #718096;
            --white: #ffffff;
            --bg-light: #f7fafc;
            --border: #e2e8f0;
            
            /* Badge Colors */
            --badge-q: #7B1FA2; /* Questionnaire */
            --badge-r: #1565C0; /* Research */
            --badge-e: #F57C00; /* Estimate */
        }}

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
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            font-size: 10pt;
            line-height: 1.5;
            color: var(--text);
            background: white;
        }}

        h2, h3, .page-title {{
            font-family: 'Montserrat', 'Trebuchet MS', sans-serif;
            text-transform: uppercase;
            letter-spacing: -0.3px;
        }}

        .pt-num {{
            font-family: 'DM Serif Display', Georgia, serif;
            font-size: 11pt;
            font-weight: 400;
            color: var(--primary);
            opacity: 0.5;
            margin-right: 10px;
            text-transform: none;
            letter-spacing: 0;
        }}

        /* === COVER PAGE — split layout === */
        .cover {{
            height: 100vh;
            display: grid;
            grid-template-columns: 3fr 2fr;
            background: white;
            overflow: hidden;
        }}

        .cover-left {{
            padding: 50mm 20mm 50mm 18mm;
            display: flex;
            flex-direction: column;
            justify-content: center;
        }}

        .cover-brand {{
            font-family: 'Montserrat', sans-serif;
            font-size: 7.5pt;
            letter-spacing: 4px;
            text-transform: uppercase;
            color: var(--primary);
            margin-bottom: 28mm;
            font-weight: 700;
        }}

        .cover-label {{
            font-size: 8.5pt;
            color: var(--text-light);
            text-transform: uppercase;
            letter-spacing: 1.5px;
            margin-bottom: 10px;
            font-family: 'Montserrat', sans-serif;
        }}

        .cover h1 {{
            font-family: 'DM Serif Display', Georgia, serif;
            font-size: 38pt;
            font-weight: 400;
            color: var(--text);
            line-height: 1.05;
            margin-bottom: 18px;
            text-transform: none;
            letter-spacing: -0.5px;
        }}

        .cover-period {{
            font-family: 'Montserrat', sans-serif;
            font-size: 13pt;
            font-weight: 800;
            color: var(--primary);
            margin-bottom: 22px;
            letter-spacing: 1px;
        }}

        .cover-tag {{
            font-size: 8pt;
            color: var(--text-light);
            letter-spacing: 1px;
            text-transform: uppercase;
        }}

        .cover-right {{
            background: var(--primary);
            position: relative;
            overflow: hidden;
            display: flex;
            align-items: center;
            justify-content: center;
        }}

        .cover-right::before {{
            content: "";
            position: absolute;
            top: 0; left: 0; right: 0; bottom: 0;
            background-image: radial-gradient(circle, rgba(255,255,255,0.12) 1px, transparent 1px);
            background-size: 28px 28px;
        }}

        .cover-right-text {{
            font-family: 'DM Serif Display', Georgia, serif;
            font-size: 68pt;
            font-weight: 400;
            color: rgba(255,255,255,0.18);
            position: relative;
            z-index: 1;
            line-height: 0.9;
            text-align: center;
            letter-spacing: -2px;
        }}

        /* === PAGE SECTIONS === */
        .page {{
            padding: 10mm 0;
        }}

        .page-break {{
            page-break-after: always;
        }}

        .page-title {{
            background: white;
            color: var(--primary);
            padding: 10px 0 10px 18px;
            font-size: 13pt;
            font-weight: 800;
            margin-bottom: 20px;
            border-left: 5px solid var(--primary);
            border-bottom: 1px solid var(--border);
            display: flex;
            align-items: center;
            gap: 8px;
        }}

        /* === KPI CARDS === */
        .kpi-grid {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 12px;
            margin-bottom: 25px;
        }}

        .kpi-card {{
            background: white;
            border: 1px solid var(--border);
            border-top: 3px solid var(--primary);
            padding: 16px 14px;
            border-radius: 6px;
            text-align: left;
            box-shadow: 0 2px 6px rgba(0,0,0,0.05);
        }}

        .kpi-card .label {{
            font-size: 7pt;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.8px;
            color: var(--text-light);
            margin-bottom: 6px;
        }}

        .kpi-card .value {{
            font-family: 'DM Serif Display', Georgia, serif;
            font-size: 22pt;
            font-weight: 400;
            color: var(--primary);
            line-height: 1;
        }}

        /* === COMPARISON TABLE === */
        .comparison-container {{
            margin: 25px 0;
            background: #fff;
            border-radius: 12px;
            border: 1px solid var(--border);
            overflow: hidden;
        }}

        .comparison-table {{
            width: 100%;
            border-collapse: collapse;
        }}

        .comparison-table th {{
            background: var(--primary);
            color: white;
            padding: 12px 15px;
            text-align: left;
            font-family: 'Montserrat', sans-serif;
            font-size: 9pt;
            text-transform: uppercase;
        }}

        .comparison-table td {{
            padding: 12px 15px;
            border-bottom: 1px solid var(--border);
            font-size: 10pt;
        }}

        /* === BADGES === */
        .source-badge {{
            padding: 4px 10px;
            border-radius: 20px;
            font-size: 7.5pt;
            font-weight: 700;
            display: inline-flex;
            align-items: center;
            gap: 4px;
        }}
        .source-ver {{ background: #F3E5F5; color: var(--badge-q); }}
        .source-ded {{ background: #E3F2FD; color: var(--badge-r); }}
        .source-est {{ background: #FFF3E0; color: var(--badge-e); }}

        /* === AREAS === */
        .areas-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 15px;
        }}

        .area-box {{
            background: white;
            border: 1px solid var(--border);
            border-left: 4px solid var(--primary);
            border-radius: 6px;
            padding: 16px 18px;
            page-break-inside: avoid;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        }}

        .clickable {{
            cursor: pointer;
            transition: box-shadow 0.2s, transform 0.15s;
        }}
        .clickable:hover {{
            box-shadow: 0 6px 20px rgba(0,0,0,0.13);
            transform: translateY(-2px);
        }}

        .area-header {{
            display: flex;
            align-items: center;
            gap: 8px;
            margin-bottom: 10px;
            padding-bottom: 8px;
            border-bottom: 1px solid var(--border);
        }}
        .area-icon {{ font-size: 16pt; }}
        .area-title {{
            font-family: 'Montserrat', sans-serif;
            font-size: 10pt;
            font-weight: 700;
            flex: 1;
            color: var(--text);
        }}
        .expand-hint {{ font-size: 10pt; opacity: 0.4; }}

        .area-content {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
        }}

        .obj-label {{
            font-size: 6.5pt;
            font-weight: 700;
            letter-spacing: 0.8px;
            text-transform: uppercase;
            padding: 2px 7px;
            border-radius: 3px;
            display: inline-block;
            margin-bottom: 5px;
        }}
        .obj-label.macro {{ background: var(--primary); color: white; }}
        .obj-label.micro {{ background: var(--secondary); color: white; }}

        .obj-list {{
            list-style: none;
            padding: 0;
            margin: 0;
            font-size: 8.5pt;
            line-height: 1.4;
        }}
        .obj-list li {{
            padding: 2px 0 2px 10px;
            position: relative;
            color: var(--text);
        }}
        .obj-list li::before {{
            content: "›";
            position: absolute;
            left: 0;
            color: var(--primary);
            font-weight: bold;
        }}

        .truncate-screen {{
            display: -webkit-box;
            -webkit-line-clamp: 2;
            -webkit-box-orient: vertical;
            overflow: hidden;
        }}

        @media print {{
            .truncate-screen {{
                display: list-item;
                overflow: visible;
                -webkit-line-clamp: unset;
            }}
        }}

        .click-hint {{
            text-align: center;
            font-size: 7pt;
            color: var(--text-light);
            margin-top: 10px;
            font-style: italic;
            letter-spacing: 0.3px;
        }}

        /* === MODALS === */
        .modal {{
            display: none;
            position: fixed;
            top: 0; left: 0;
            width: 100%; height: 100%;
            background: rgba(0,0,0,0.55);
            z-index: 9999;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }}
        .modal.active {{
            display: flex;
        }}
        .modal-content {{
            background: white;
            border-radius: 10px;
            max-width: 680px;
            width: 100%;
            max-height: 82vh;
            overflow-y: auto;
            padding: 28px;
            position: relative;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        }}
        .modal-close {{
            position: absolute;
            top: 14px; right: 18px;
            font-size: 1.4rem;
            cursor: pointer;
            color: var(--text-light);
            line-height: 1;
            width: 28px; height: 28px;
            display: flex; align-items: center; justify-content: center;
            border-radius: 50%;
            transition: background 0.2s;
        }}
        .modal-close:hover {{ background: var(--bg-light); color: var(--text); }}
        .modal-header {{
            display: flex;
            align-items: center;
            gap: 12px;
            margin-bottom: 18px;
            padding-bottom: 14px;
            border-bottom: 2px solid var(--border);
        }}
        .modal-icon {{ font-size: 22pt; }}
        .modal-header h2 {{
            font-size: 14pt;
            color: var(--primary);
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        .modal-body {{ }}
        .modal-section {{ margin-bottom: 18px; }}
        .modal-section h3 {{ margin-bottom: 8px; font-size: 9.5pt; }}
        .modal-list {{
            list-style: none;
            padding: 0;
            margin: 0;
        }}
        .modal-list li {{
            padding: 7px 0 7px 14px;
            position: relative;
            font-size: 10pt;
            line-height: 1.5;
            border-bottom: 1px solid var(--border);
        }}
        .modal-list li:last-child {{ border-bottom: none; }}
        .modal-list li::before {{
            content: "▶";
            position: absolute;
            left: 0;
            color: var(--primary);
            font-size: 6pt;
            top: 10px;
        }}

        /* === STW DASHBOARD === */
        .stw-dashboard {{
            background: #fdfbff;
            border: 1px solid #e9d8fd;
            border-radius: 8px;
            padding: 18px;
            margin-top: 25px;
        }}

        .stw-fill {{
            background: var(--primary) !important;
        }}

        /* === I TUOI DATI PAGE === */
        .data-source-page {{
            background: #fcfaff;
            border: 2px solid var(--primary);
            border-radius: 10px;
            padding: 28px;
            margin: 20px 0;
        }}

        .data-stats-grid {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 20px;
            margin: 25px 0;
        }}

        .stat-item {{
            background: white;
            padding: 18px;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.06);
            text-align: center;
            border: 1px solid var(--border);
        }}

        .stat-value {{
            font-family: 'Montserrat', sans-serif;
            font-size: 26pt;
            font-weight: 800;
            color: var(--primary);
        }}

        .stat-label {{
            font-size: 8.5pt;
            font-weight: 600;
            color: var(--text-light);
            text-transform: uppercase;
            margin-top: 4px;
        }}

        /* === PRINT BUTTON (screen only) === */
        .print-bar {{
            position: fixed;
            bottom: 24px;
            right: 24px;
            z-index: 10000;
            display: flex;
            flex-direction: column;
            align-items: flex-end;
            gap: 8px;
        }}
        .print-btn {{
            background: var(--primary);
            color: white;
            border: none;
            padding: 12px 22px;
            border-radius: 8px;
            font-family: 'Montserrat', sans-serif;
            font-size: 11pt;
            font-weight: 700;
            cursor: pointer;
            box-shadow: 0 4px 16px rgba(0,0,0,0.22);
            transition: transform 0.15s, box-shadow 0.15s;
            letter-spacing: 0.5px;
        }}
        .print-btn:hover {{
            transform: translateY(-2px);
            box-shadow: 0 6px 22px rgba(0,0,0,0.28);
        }}
        .print-hint {{
            font-size: 7.5pt;
            color: #aaa;
            text-align: right;
            background: white;
            padding: 3px 10px;
            border-radius: 4px;
            border: 1px solid #eee;
        }}

        @media print {{
            .print-bar, .modal, .click-hint {{ display: none !important; }}
            * {{ -webkit-print-color-adjust: exact !important; color-adjust: exact !important; }}
            body {{ background: white; }}
            .page-break {{ page-break-after: always; break-after: page; }}
            .area-box, .kpi-card, .stat-item {{ page-break-inside: avoid; break-inside: avoid; }}
            .cover {{ height: 100vh; page-break-after: always; }}
            a {{ text-decoration: none; color: inherit; }}
        }}

        /* Shared badge styles (for common emoji badges in content) */
        {RF_BADGE_CSS}
    </style>
</head>
<body>

<!-- PRINT BUTTON -->
<div class="print-bar">
    <button class="print-btn" onclick="window.print()">📥 Salva come PDF</button>
    <div class="print-hint">File → Stampa → Salva come PDF</div>
</div>

<!-- PAGINA 1: COVER -->
<div class="cover page-break">
    <div class="cover-left">
        <div class="cover-brand">Rooting Future</div>
        <div class="cover-label">Report Esecutivo · Piano Triennale</div>
        <h1>{club_name}</h1>
        <div class="cover-period">{current_year} — {current_year + 3}</div>
        <div class="cover-tag">Riservato al Board di Gestione</div>
        {_format_timing_badge(metadata)}
    </div>
    <div class="cover-right">
        <div class="cover-right-text">{current_year}<br>—<br>{current_year + 3}</div>
    </div>
</div>

<!-- PAGINA 2: I TUOI DATI -->
<div class="page page-break">
    <div class="page-title"><span class="pt-num">01</span> I Tuoi Dati: Trasparenza e Metodologia</div>
    
    <div class="data-source-page">
        <h2 style="color: var(--primary); margin-bottom: 15px;">La Base del Tuo Piano</h2>
        <p style="font-size: 11pt; color: var(--text-light); margin-bottom: 20px;">
            Questo documento non è una semplice generazione AI. È costruito sui dati reali forniti dal Board di <strong>{club_name}</strong>, 
            incrociati con i benchmark ufficiali FIGC e la nostra metodologia proprietaria.
        </p>

        <div class="data-stats-grid">
            <div class="stat-item">
                <div class="stat-value">{metadata.get('total_questionnaires', 0)}</div>
                <div class="stat-label">Questionari Board</div>
            </div>
            <div class="stat-item">
                <div class="stat-value">{metadata.get('verified_data_count', 0)}+</div>
                <div class="stat-label">Dati Verificati</div>
            </div>
            <div class="stat-item">
                <div class="stat-value">{int(metadata.get('questionnaire_completion', 0) * 100)}%</div>
                <div class="stat-label">Completezza Input</div>
            </div>
        </div>

        <div style="background: white; padding: 20px; border-radius: 12px; border-left: 5px solid var(--badge-q);">
            <h3 style="color: var(--badge-q); font-size: 11pt; margin-bottom: 10px;">🛡️ Garanzia di Qualità</h3>
            <ul style="font-size: 9.5pt; padding-left: 20px; color: var(--text);">
                <li>Dati estratti dai questionari Word caricati dal sistema.</li>
                <li>Incrocio automatico con database benchmark Serie {category}.</li>
                <li>Validazione scientifica degli scostamenti (Gap Analysis).</li>
            </ul>
        </div>
    </div>

    <div class="page-title" style="margin-top: 30px;"><span class="pt-num">02</span> Sintesi Strategica</div>
    <div class="exec-box" style="background: #f9f7ff; border-left: 4px solid var(--primary); padding: 20px; border-radius: 0 12px 12px 0;">
        <ul style="list-style: none; padding: 0;">
            {exec_html}
        </ul>
    </div>
</div>

<!-- PAGINA 3: KPI + GRAFICI -->
<div class="page page-break">
    <div class="page-title"><span class="pt-num">03</span> Quadro Finanziario e Benchmark</div>
    
    <div class="kpi-grid">
        <div class="kpi-card">
            <div class="label">Fatturato</div>
            <div class="value">€{fat_val/1_000_000:.1f}M</div>
            <div class="source-badge source-{'ver' if fatturato and fatturato.tier == DataTier.TIER_1_FACT else 'est'}">
                { '📋' if fatturato and fatturato.tier == DataTier.TIER_1_FACT else '📊' } {fatturato.tier.value.upper() if fatturato else 'N/A'}
            </div>
        </div>
        <div class="kpi-card">
            <div class="label">Monte Ingaggi</div>
            <div class="value">€{mi_val/1_000:.0f}K</div>
            <div class="source-badge source-{'ver' if monte_ingaggi and monte_ingaggi.tier == DataTier.TIER_1_FACT else 'est'}">
                { '📋' if monte_ingaggi and monte_ingaggi.tier == DataTier.TIER_1_FACT else '📊' } {monte_ingaggi.tier.value.upper() if monte_ingaggi else 'N/A'}
            </div>
        </div>
        <div class="kpi-card">
            <div class="label">Valore Rosa</div>
            <div class="value">€{vr_val/1_000:.0f}K</div>
            <div class="source-badge source-{'ver' if valore_rosa and valore_rosa.tier == DataTier.TIER_1_FACT else 'est'}">
                { '📋' if valore_rosa and valore_rosa.tier == DataTier.TIER_1_FACT else '📊' } {valore_rosa.tier.value.upper() if valore_rosa else 'N/A'}
            </div>
        </div>
        <div class="kpi-card" style="background: {primary_color}05;">
            <div class="label">Margine Op.</div>
            <div class="value" style="color: {'#38a169' if marg_val >= 0 else '#e53e3e'}">€{marg_val/1_000:.0f}K</div>
            <div class="source-badge source-est">📊 STIMA</div>
        </div>
    </div>

    {_generate_comparison_table_html(estimates, category)}

    <div class="charts-grid" style="margin-top: 20px;">
        <div class="chart-box" style="border: none; background: #fdfbff; padding: 20px; border-radius: 12px;">
            <h4 style="font-family: 'Montserrat'; color: var(--primary);">Composizione Ricavi</h4>
            <p style="font-size:8pt; color:#718096; font-style:italic; margin-bottom:8px;">📊 Struttura media benchmark {category} — Fonte: FIGC Report Calcio 2024</p>
            {pie_img}
        </div>
        <div class="chart-box" style="border: none; background: #fdfbff; padding: 20px; border-radius: 12px;">
            <h4 style="font-family: 'Montserrat'; color: var(--primary);">Gap Analysis vs {category}</h4>
            {gap_img}
        </div>
    </div>

    {stw_dashboard_html}
</div>

<!-- PAGINA 4: AREE STRATEGICHE + ROADMAP -->
<div class="page page-break">
    <div class="page-title"><span class="pt-num">04</span> Aree Strategiche di Intervento</div>
    <div class="areas-grid">
        {areas_html}
    </div>

    <div class="page-title" style="margin-top:30px;"><span class="pt-num">05</span> Roadmap Triennale</div>
    {timeline_html}
</div>

<!-- PAGINA 5: METODOLOGIA -->
<div class="page">
    <div class="page-title"><span class="pt-num">06</span> Metodologia e Fonti</div>

    <div class="method-grid">
        <div class="method-box">
            <h4>Fonti Dati Utilizzate</h4>
            <ul style="font-size:8.5pt; padding-left:15px; color: var(--text);">
                <li><strong>Questionari Rooting Future</strong> - Input diretti del club 📋</li>
                <li><strong>FIGC Report Calcio 2024</strong> - Benchmark ufficiali di categoria</li>
                <li><strong>Transfermarkt</strong> - Valutazioni di mercato e statistiche rose</li>
                <li><strong>Web Research</strong> - News, bilanci pubblici e news territoriali 🔍</li>
            </ul>
        </div>
        <div class="method-box">
            <h4>Analisi dei Campi</h4>
            <ul style="font-size:8.5pt; padding-left:15px; color: var(--text);">
                {_format_estimated_fields(estimated_fields)}
            </ul>
        </div>
    </div>

    <div class="tier-legend" style="margin-top: 20px; background: var(--bg-light); padding: 15px; border-radius: 8px;">
        <div class="tier-item"><span class="source-badge source-ver">📋 QUESTIONARIO</span> Dato verificato dal club</div>
        <div class="tier-item"><span class="source-badge source-ded">🔍 DEDOTTO</span> Calcolato da parametri indiretti</div>
        <div class="tier-item"><span class="source-badge source-est">📊 STIMA</span> Calcolo algoritmico su benchmark</div>
    </div>

    <div class="footer">
        Piano elaborato da <strong>Rooting Future</strong> |
        {datetime.now().strftime('%d/%m/%Y')}
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
