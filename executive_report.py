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
    text = text.strip()
    # Rimuovi due punti iniziali (fix Task 6)
    if text.startswith(':'):
        text = text[1:].strip()
    return text


def add_source_badge_inline(text: str, source: str = "estimate") -> str:
    """
    Aggiunge badge inline al testo basato sulla fonte.
    """
    if not text:
        return ""
    
    # Mappa fonti a badge
    badge_map = {
        'verified': '<span class="source-badge source-ver">📋 VERIFICATO</span>',
        'questionnaire': '<span class="source-badge source-ver">📋 DA QUESTIONARIO</span>',
        'research': '<span class="source-badge source-ded">🔍 DEDOTTO</span>',
        'estimate': '<span class="source-badge source-est">📊 STIMATO</span>'
    }
    
    badge = badge_map.get(source, badge_map['estimate'])
    return f"{text} {badge}"


MICRO_OBJECTIVES_FALLBACKS = {
    'CREAZIONE E SVILUPPO IDENTITÀ TECNICA': [
        'Definire modulo tattico unificato (es. 4-3-3) per tutte le categorie',
        'Formare lo staff tecnico su metodologia di gioco comune',
        'Implementare sistema di valutazione performance standardizzato',
        'Creare protocollo allenamenti settimanale condiviso tra categorie'
    ],
    'COSTRUZIONE E RINNOVAMENTO STRUTTURE': [
        'Mappare stato attuale impianti con report fotografico dettagliato',
        'Prioritizzare interventi su campo allenamento settore giovanile',
        'Ottenere certificazioni sicurezza aggiornate per tutti gli impianti',
        'Installare sistema illuminazione LED su campo principale'
    ],
    'SVILUPPO AREA COMUNICAZIONE': [
        'Pubblicare 3 post/settimana sui social media con calendario editoriale',
        'Creare newsletter mensile per tesserati e sponsor',
        'Implementare area stampa digitale sul sito web',
        'Avviare collaborazione con media locali per copertura partite'
    ],
    'SVILUPPO AREA MARKETING': [
        'Lanciare campagna sponsor per stagione 2026/27 con target €50K',
        'Creare merchandising ufficiale (maglie, sciarpe) entro marzo',
        'Implementare programma fedeltà per abbonati',
        'Organizzare 2 eventi corporate per attrarre nuovi partner'
    ],
    'SVILUPPO BRAND IDENTITY': [
        'Ridisegnare logo e brand guidelines entro aprile 2026',
        'Unificare comunicazione visiva su tutti i canali',
        'Creare brand book digitale per uso interno/esterno',
        'Registrare marchio presso UIBM per protezione legale'
    ],
    'SVILUPPO AREA COMMERCIALE': [
        'Mappare potenziali sponsor locali (target list di 30 aziende)',
        'Creare presentation deck commerciale con pacchetti sponsor',
        'Assumere commerciale part-time per gestione sponsor',
        'Attivare vendita biglietti online su piattaforma dedicata'
    ],
    'SVILUPPO INCLUSIONE E UGUAGLIANZA': [
        'Creare squadra femminile o accordo con club femminile locale',
        'Implementare protocollo anti-discriminazione in tutti gli eventi',
        'Organizzare torneo giovanile inclusivo aperto a tutti',
        'Formare staff su gestione diversità e inclusione'
    ],
    'PROTEZIONE BAMBINI/E E GIOVANI': [
        'Certificare tutti gli allenatori giovanili con corso Safeguarding',
        'Implementare protocollo tutela minori conforme FIGC',
        'Nominare responsabile protezione minori nel club',
        'Attivare assicurazione specifica per settore giovanile'
    ],
    'RISORSE UMANE': [
        'Digitalizzare gestione presenze staff con sistema HR cloud',
        'Creare organigramma chiaro con ruoli e responsabilità definiti',
        'Implementare valutazione annuale performance per staff tecnico',
        'Attivare convenzioni welfare per dipendenti (palestra, assicurazioni)'
    ]
}


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
    """Estrae obiettivi MACRO e MICRO con titoli descrittivi completi."""
    result = {'macro': [], 'micro': []}
    if not content:
        # Fallback totale se contenuto assente
        result['macro'] = ["Definizione Posizionamento Strategico", "Consolidamento Struttura Organizzativa"]
        result['micro'] = ["Analisi dei processi interni", "Sviluppo competenze staff", "Definizione budget preliminare"]
        return result

    # --- MACRO OBIETTIVI ---
    # Cerca header ## (es: ## MACRO 1: TITOLO o ## 1. TITOLO)
    macro_matches = re.findall(r'##\s*(?:MACRO\s+)?(?:\d+\.)?\s*([A-ZÀ-Ÿ][^#\n]{5,100})', content)
    
    for m in macro_matches[:4]:
        clean = _clean_text(m)
        clean = re.sub(r'^(?:MACRO\s+)?\d+[:\s.-]*', '', clean, flags=re.IGNORECASE).strip()
        if len(clean) > 5 and clean not in result['macro']:
            result['macro'].append(clean)

    # --- MICRO OBIETTIVI ---
    # Cerca header ### (es: ### 1.1 TITOLO) o bullet points forti
    micro_matches = re.findall(r'###\s*(?:\d+\.\d+)?\s*([A-ZÀ-Ÿ][^#\n]{5,100})', content)
    
    # Se pochi MICRO, cerca bullet points che iniziano con grassetto
    if len(micro_matches) < 2:
        bullet_bold = re.findall(r'[-*•]\s*\*\*([A-ZÀ-Ÿ][^*]{5,80})\*\*', content)
        micro_matches.extend(bullet_bold)

    for m in micro_matches[:5]:
        clean = _clean_text(m)
        clean = re.sub(r'^\d+\.\d+[:\s.-]*', '', clean).strip()
        
        # Filtra duplicati dei macro
        is_duplicate = False
        for macro in result['macro']:
            if (clean.lower() in macro.lower() or macro.lower() in clean.lower()) and abs(len(clean) - len(macro)) < 15:
                is_duplicate = True
                break
        
        if not is_duplicate and len(clean) > 10 and clean not in result['micro']:
            result['micro'].append(clean)

    # --- SMART FALLBACKS (Basati su parole chiave nei Macro) ---
    if len(result['micro']) < 2:
        # Mappa parole chiave dei MACRO ai FALLBACK
        keyword_map = {
            'tecnica': 'CREAZIONE E SVILUPPO IDENTITÀ TECNICA',
            'sportiva': 'CREAZIONE E SVILUPPO IDENTITÀ TECNICA',
            'settore giovanile': 'CREAZIONE E SVILUPPO IDENTITÀ TECNICA',
            'struttur': 'COSTRUZIONE E RINNOVAMENTO STRUTTURE',
            'impiant': 'COSTRUZIONE E RINNOVAMENTO STRUTTURE',
            'comunicazione': 'SVILUPPO AREA COMUNICAZIONE',
            'social': 'SVILUPPO AREA COMUNICAZIONE',
            'marketing': 'SVILUPPO AREA MARKETING',
            'commerciale': 'SVILUPPO AREA COMMERCIALE',
            'brand': 'SVILUPPO BRAND IDENTITY',
            'inclusione': 'SVILUPPO INCLUSIONE E UGUAGLIANZA',
            'bambini': 'PROTEZIONE BAMBINI/E E GIOVANI',
            'risorse': 'RISORSE UMANE',
            'personale': 'RISORSE UMANE',
            'organigramma': 'RISORSE UMANE'
        }

        # Per ogni macro trovato, cerca se esiste un set di fallback pertinente
        for macro in result['macro']:
            for kw, fallback_key in keyword_map.items():
                if kw in macro.lower():
                    fallbacks = MICRO_OBJECTIVES_FALLBACKS.get(fallback_key, [])
                    for fb in fallbacks:
                        if fb not in result['micro'] and len(result['micro']) < 4:
                            result['micro'].append(fb)
                    break
            if len(result['micro']) >= 4: break

    # Fallback finali se ancora vuoti (Garantisce che il report non sia mai vuoto)
    if not result['macro']:
        result['macro'] = ["Evoluzione Organizzativa", "Sostenibilità Economico-Sportiva"]
    if not result['micro']:
        result['micro'] = ["Analisi del posizionamento territoriale", "Consolidamento dei ricavi commerciali", "Efficienza nella gestione sportiva"]

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

    # Colori club (Protagonisti)
    primary_color = metadata.get('primary_color') or '#6a0dad'
    secondary_color = metadata.get('secondary_color') or '#ffffff'
    
    # Se il secondario è bianco, usiamo un grigio scuro per i gradienti per dare profondità
    grad_secondary = secondary_color if secondary_color.lower() != "#ffffff" else "#1a202c"

    # Genera varianti colore
    primary_dark = _darken_color(primary_color, 0.2)
    text_on_primary = _get_contrast_color(primary_color)

    # Calculate text_on_cover (contrast against primary/brand_gradient)
    # If primary is light (e.g. White), the gradient is light, so text must be dark.
    r_p, g_p, b_p = tuple(int(primary_color.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
    lum_p = (0.299 * r_p + 0.587 * g_p + 0.114 * b_p) / 255
    text_on_cover = '#ffffff' if lum_p < 0.6 else '#1a1a1a'

    # FIX: Text on white background should be readable even if primary is white/light
    text_on_white = primary_color
    r, g, b = tuple(int(primary_color.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
    lum = (0.299 * r + 0.587 * g + 0.114 * b) / 255
    if lum > 0.65:
        text_on_white = _darken_color(primary_color, 0.7)
    
    # Check extra per bianco puro
    r2, g2, b2 = tuple(int(text_on_white.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
    if (0.299 * r2 + 0.587 * g2 + 0.114 * b2) / 255 > 0.7:
        text_on_white = "#333333"

    # === CALCOLO COPERTURA STW ===
    stw_progress = calculate_stw_progress(plan_data)
    stw_dashboard_html = _generate_stw_dashboard_html(stw_progress)
    
    # === ESTRAZIONE PUNTI CHIAVE PER SINTESI ===
    # Cerca il contenuto dell'executive summary generale o specifico
    exec_summary_content = plan_data.get('executive_summary') or \
                          plan_data.get('executive_summary_sporting') or \
                          ""
    
    exec_points = []
    if exec_summary_content:
        exec_points = _extract_key_points(exec_summary_content, max_points=3)
    
    # Fallback se non ci sono punti estratti
    if not exec_points:
        exec_points = ["Consolidamento della struttura societaria", "Sostenibilità finanziaria a lungo termine"]

    # === DATI FINANZIARI PER KPI ===
    known_financials = metadata.get("known_financials", {})
    club_data_for_est = {
        "dimensione_rosa": metadata.get("dimensione_rosa", 22),
        "capienza_stadio": metadata.get("capienza_stadio", 0)
    }
    estimates = estimate_missing_financials(club_data_for_est, category, known_financials)

    fatturato = estimates.get('fatturato')
    monte_ingaggi = estimates.get('monte_ingaggi')
    valore_rosa = estimates.get('valore_rosa')
    margine = estimates.get('margine_operativo')

    fat_val = fatturato.value if fatturato else 0
    mi_val = monte_ingaggi.value if monte_ingaggi else 0
    vr_val = valore_rosa.value if valore_rosa else 0
    marg_val = margine.value if margine else 0

    # === GENERAZIONE GRAFICI ===
    # 1. Pie Chart Ricavi (Stima scientifica per categoria se non dettaglio)
    # Distribuzioni tipiche basate su Report Calcio FIGC 2024
    revenue_profiles = {
        # Serie A/B: Forte impatto diritti TV e Commerciale
        'top_tier': {'Ricavi Gara': 0.15, 'Commerciale': 0.30, 'Diritti TV': 0.45, 'Altro': 0.10},
        # Serie C: Mix equilibrato, TV marginali
        'pro_tier': {'Ricavi Gara': 0.25, 'Commerciale': 0.45, 'Diritti TV': 0.15, 'Altro': 0.15},
        # LND/Dilettanti: Dipendenza da sponsor locali e biglietteria/eventi
        'amateur':  {'Ricavi Gara': 0.30, 'Sponsor Locali': 0.50, 'Eventi/Campo': 0.15, 'Altro': 0.05}
    }

    # Selezione profilo
    norm_cat = category.lower()
    if 'serie a' in norm_cat or 'serie b' in norm_cat:
        profile = revenue_profiles['top_tier']
    elif 'serie c' in norm_cat:
        profile = revenue_profiles['pro_tier']
    else:
        profile = revenue_profiles['amateur']

    revenues = {k: fat_val * pct for k, pct in profile.items()}
    
    pie_b64 = generate_revenue_pie_chart(revenues, club_name, primary_color)
    pie_img = embed_chart_in_html(pie_b64, "Composizione Ricavi")

    # 2. Gap Analysis
    from data_models import BenchmarkDatabase
    benchmarks = BenchmarkDatabase.FINANCIAL_BENCHMARKS.get(category, {})
    gap_img = ""
    if benchmarks:
        gaps = {
            'fatturato': (fat_val, benchmarks.get('fatturato_medio', fat_val)),
            'monte_ingaggi': (mi_val, benchmarks.get('monte_ingaggi_medio', mi_val)),
            'valore_rosa': (vr_val, benchmarks.get('costo_rosa_medio', vr_val))
        }
        gap_b64 = generate_gap_analysis_chart(gaps, club_name, category)
        gap_img = embed_chart_in_html(gap_b64, "Gap Analysis")

    # === GENERAZIONE CONTENT AREE ===
    areas_html = ""
    modals_html = ""
    
    area_configs = [
        ('sporting', 'Area Sportiva', '⚽', ['technical_sporting', 'youth_development']),
        ('structural', 'Area Strutturale', '🏗️', ['infrastructure']),
        ('marketing', 'Marketing & Brand', '📈', ['marketing_commercial']),
        ('social', 'Area Sociale', '🤝', ['social_sustainability', 'governance'])
    ]

    for key, title, icon, section_keys in area_configs:
        # Unisci contenuti
        content = ""
        for sk in section_keys:
            content += plan_data.get(sk, "") + "\n"
        
        objs = _extract_objectives_summary(content)
        
        # HTML per Box Area
        # Aggiungi badge se la sezione sembra verificata (placeholder logic, idealmente viene da metadata)
        macro_list = "".join([f'<li>{add_source_badge_inline(m, "estimate" if "stima" in m.lower() else "research")}</li>' for m in objs['macro'][:2]])
        micro_list = "".join([f'<li>{m}</li>' for m in objs['micro'][:2]])
        
        areas_html += f'''
        <div class="area-box clickable" onclick="openModal('modal_{key}')">
            <div class="area-header">
                <span class="area-icon">{icon}</span>
                <span class="area-title">{title}</span>
            </div>
            <div class="area-content">
                <div>
                    <span class="obj-label macro">MACRO OBIETTIVI</span>
                    <ul class="obj-list">{macro_list}</ul>
                </div>
                <div>
                    <span class="obj-label micro">AZIONI CHIAVE</span>
                    <ul class="obj-list">{micro_list}</ul>
                </div>
            </div>
            <div class="click-hint">CLICCA PER DETTAGLI ➜</div>
        </div>
        '''

        # HTML per Modale
        full_macro = "".join([f'<li>{m}</li>' for m in objs['macro']])
        full_micro = "".join([f'<li>{m}</li>' for m in objs['micro']])
        
        modals_html += f'''
        <div id="modal_{key}" class="modal">
            <div class="modal-content">
                <span class="modal-close" onclick="closeModal('modal_{key}')">&times;</span>
                <div class="modal-header">
                    <span class="modal-icon">{icon}</span>
                    <h2 style="margin:0; color:var(--primary);">{title}</h2>
                </div>
                <div class="modal-section">
                    <h3>🎯 OBIETTIVI MACRO</h3>
                    <ul class="modal-list">{full_macro}</ul>
                </div>
                <div class="modal-section">
                    <h3>⚡ AZIONI OPERATIVE</h3>
                    <ul class="modal-list">{full_micro}</ul>
                </div>
            </div>
        </div>
        '''

    # === TIMELINE ===
    # Estrai anni dal piano
    current_year = datetime.now().year
    years = [current_year, current_year+1, current_year+2]
    
    timeline_html = f'''
    <div style="display:grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin-top:20px;">
        <div style="background:#f0f4f8; padding:15px; border-radius:8px; border-top:4px solid var(--primary);">
            <div style="font-weight:800; font-size:12pt; color:var(--primary); margin-bottom:10px;">ANNO 1 ({years[0]})</div>
            <div style="font-size:9pt;">Fase di Consolidamento</div>
        </div>
        <div style="background:#f0f4f8; padding:15px; border-radius:8px; border-top:4px solid var(--secondary);">
            <div style="font-weight:800; font-size:12pt; color:var(--secondary); margin-bottom:10px;">ANNO 2 ({years[1]})</div>
            <div style="font-size:9pt;">Fase di Sviluppo</div>
        </div>
        <div style="background:#f0f4f8; padding:15px; border-radius:8px; border-top:4px solid #38a169;">
            <div style="font-weight:800; font-size:12pt; color:#38a169; margin-bottom:10px;">ANNO 3 ({years[2]})</div>
            <div style="font-size:9pt;">Fase di Espansione</div>
        </div>
    </div>
    '''

    # === COMPARISON TABLE ===
    comparison_table_html = _generate_comparison_table_html(estimates, category)

    # === METODOLOGIA FIELDS ===
    estimated_fields = {}
    for k, v in estimates.items():
        if hasattr(v, 'tier'):
            estimated_fields[k] = v.tier.value
        else:
            estimated_fields[k] = "sconosciuto"

    # === TIMING BADGE ===
    timing_badge_html = _format_timing_badge(metadata)

    # === HTML FINALE ===
    html = f'''<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <title>Executive Report - {club_name}</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Montserrat:wght@700;800;900&display=swap" rel="stylesheet">
    <style>
        :root {{
            --club-primary: {primary_color};
            --club-secondary: {secondary_color};
            --primary: var(--club-primary);
            --primary-dark: {primary_dark};
            --text-on-primary: {text_on_primary};
            --text-on-white: {text_on_white};
            --text-on-cover: {text_on_cover};
            
            --brand-gradient: linear-gradient(135deg, var(--club-primary) 0%, var(--primary-dark) 100%);
            --soft-bg: #f8fafc;
            --card-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.05), 0 8px 10px -6px rgba(0, 0, 0, 0.05);
            --accent: {grad_secondary};
            --text-main: #1e293b;
            --text-muted: #64748b;
            --white: #ffffff;
            --border-light: #f1f5f9;
        }}

        @page {{
            size: A4;
            margin: 0;
        }}

        body {{
            font-family: 'Inter', -apple-system, sans-serif;
            color: var(--text-main);
            background-color: #f1f5f9;
            margin: 0;
            padding: 0;
            line-height: 1.6;
            -webkit-print-color-adjust: exact;
        }}

        .page {{
            width: 210mm;
            min-height: 297mm;
            padding: 20mm;
            margin: 10mm auto;
            background: white;
            box-shadow: 0 0 20px rgba(0,0,0,0.1);
            position: relative;
            box-sizing: border-box;
            page-break-after: always;
            overflow: hidden;
        }}

        /* === COVER PAGE === */
        .cover {{
            background: var(--brand-gradient);
            color: var(--text-on-cover);
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            text-align: center;
            height: 297mm;
            padding: 0;
            margin: 0 auto;
        }}

        .cover-content {{
            position: relative;
            z-index: 2;
        }}

        .cover h1 {{
            font-family: 'Montserrat', sans-serif;
            font-size: 52pt;
            font-weight: 900;
            margin: 0;
            letter-spacing: -2px;
            text-transform: uppercase;
        }}

        .cover .subtitle {{
            font-size: 18pt;
            font-weight: 300;
            margin-top: 10px;
            opacity: 0.9;
            letter-spacing: 4px;
            text-transform: uppercase;
        }}

        .cover-footer {{
            position: absolute;
            bottom: 40px;
            width: 100%;
            text-align: center;
        }}

        .timing-badge {{
            position: absolute;
            bottom: 80px;
            left: 50%;
            transform: translateX(-50%);
            padding: 6px 14px;
            background: rgba(255, 255, 255, 0.15);
            border-radius: 16px;
            font-size: 9pt;
            backdrop-filter: blur(10px);
        }}

        /* === TYPOGRAPHY & HEADERS === */
        h2.section-title {{
            font-family: 'Montserrat', sans-serif;
            font-size: 24pt;
            font-weight: 800;
            color: var(--primary);
            margin-bottom: 25px;
            display: flex;
            align-items: center;
            gap: 15px;
            border-bottom: 3px solid var(--soft-bg);
            padding-bottom: 15px;
        }}

        .icon-box {{
            background: var(--soft-bg);
            padding: 10px;
            border-radius: 12px;
            font-size: 20pt;
        }}

        /* === KPI CARDS === */
        .kpi-grid {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 15px;
            margin-bottom: 30px;
        }}

        .kpi-card {{
            background: white;
            border: 1px solid var(--border-light);
            padding: 20px;
            border-radius: 16px;
            box-shadow: var(--card-shadow);
            text-align: center;
            transition: transform 0.2s;
        }}

        .kpi-card .label {{
            font-size: 8pt;
            font-weight: 600;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 8px;
        }}

        .kpi-card .value {{
            font-family: 'Montserrat', sans-serif;
            font-size: 20pt;
            font-weight: 800;
            color: var(--text-main);
        }}

        /* === STW DASHBOARD === */
        .stw-dashboard {{
            background: var(--soft-bg);
            padding: 20px;
            border-radius: 16px;
            margin-bottom: 30px;
            border: 1px solid var(--border-light);
        }}
        .stw-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
            font-weight: 700;
            color: var(--primary);
        }}
        .stw-overall {{
            font-size: 18pt;
            background: var(--primary);
            color: white;
            padding: 4px 12px;
            border-radius: 10px;
        }}
        .stw-row {{
            display: grid;
            grid-template-columns: 25px 100px 1fr 45px;
            align-items: center;
            gap: 10px;
            margin-bottom: 8px;
        }}
        .stw-icon {{ font-size: 12pt; }}
        .stw-label {{ font-size: 8pt; font-weight: 600; color: var(--text-muted); }}
        .stw-bar {{ height: 8px; background: #e2e8f0; border-radius: 4px; overflow: hidden; }}
        .stw-fill {{ height: 100%; border-radius: 4px; }}
        .stw-percent {{ font-size: 9pt; font-weight: 700; text-align: right; }}
        .stw-note {{ font-size: 7.5pt; color: var(--text-muted); margin-top: 10px; font-style: italic; }}

        /* === COMPARISON TABLE === */
        .comparison-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 9pt;
            margin-bottom: 20px;
        }}
        .comparison-table th {{
            background: var(--soft-bg);
            text-align: left;
            padding: 10px;
            border-bottom: 2px solid var(--primary);
            color: var(--primary);
            font-weight: 800;
            text-transform: uppercase;
        }}
        .comparison-table td {{
            padding: 10px;
            border-bottom: 1px solid var(--border-light);
        }}
        .gap-pos {{ color: #16a34a; font-weight: 700; }}
        .gap-neg {{ color: #dc2626; font-weight: 700; }}
        .source-badge {{
            font-size: 7pt;
            padding: 2px 8px;
            border-radius: 4px;
            font-weight: 600;
        }}
        .source-ver {{ background: #f3e8ff; color: #7e22ce; }}
        .source-ded {{ background: #e0f2fe; color: #0369a1; }}
        .source-est {{ background: #fef3c7; color: #92400e; }}

        /* === DATA SOURCE SECTION === */
        .data-header {{
            background: var(--soft-bg);
            padding: 25px;
            border-radius: 20px;
            margin-bottom: 30px;
            border-left: 6px solid var(--primary);
        }}

        .data-stats {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 20px;
            margin-top: 20px;
        }}

        .stat-circle {{
            text-align: center;
        }}

        .stat-circle .val {{
            font-size: 24pt;
            font-weight: 800;
            color: var(--primary);
            display: block;
        }}

        .stat-circle .lbl {{
            font-size: 9pt;
            color: var(--text-muted);
            font-weight: 500;
        }}

        /* === STRATEGIC AREAS === */
        .areas-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
        }}

        .area-card {{
            border: 1px solid var(--border-light);
            border-radius: 20px;
            padding: 25px;
            position: relative;
            background: white;
            box-shadow: var(--card-shadow);
        }}

        .area-card h3 {{
            font-family: 'Montserrat', sans-serif;
            font-size: 14pt;
            font-weight: 800;
            margin: 0 0 15px 0;
            display: flex;
            align-items: center;
            gap: 10px;
        }}

        .area-card .tag {{
            font-size: 7pt;
            font-weight: 700;
            padding: 4px 10px;
            border-radius: 6px;
            text-transform: uppercase;
            margin-bottom: 8px;
            display: inline-block;
        }}

        .tag-macro {{ background: #e0f2fe; color: #0369a1; }}
        .tag-action {{ background: #f0fdf4; color: #166534; }}

        .area-list {{
            list-style: none;
            padding: 0;
            margin: 0;
        }}

        .area-list li {{
            font-size: 9.5pt;
            padding-left: 15px;
            position: absolute; /* Hidden in main box, shown in modal */
            display: none;
        }}
        
        .area-card .obj-list {{
            list-style: none;
            padding: 0;
            margin: 0 0 15px 0;
        }}
        
        .area-card .obj-list li {{
            font-size: 9pt;
            padding-left: 15px;
            position: relative;
            margin-bottom: 5px;
            color: #475569;
            display: block;
        }}
        
        .area-card .obj-list li::before {{
            content: "•";
            position: absolute;
            left: 0;
            color: var(--primary);
            font-weight: bold;
        }}

        /* === CHARTS === */
        .charts-container {{
            display: grid;
            grid-template-columns: 1.2fr 0.8fr;
            gap: 20px;
            margin-top: 20px;
        }}

        .chart-wrapper {{
            background: white;
            padding: 20px;
            border-radius: 20px;
            border: 1px solid var(--border-light);
        }}

        .chart-title {{
            font-size: 11pt;
            font-weight: 700;
            margin-bottom: 15px;
            color: var(--text-main);
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}

        /* === FOOTER === */
        .footer {{
            position: absolute;
            bottom: 20mm;
            left: 20mm;
            right: 20mm;
            border-top: 1px solid var(--border-light);
            padding-top: 15px;
            display: flex;
            justify-content: space-between;
            font-size: 8pt;
            color: var(--text-muted);
        }}

        /* === MODALS === */
        .modal {{
            display: none;
            position: fixed;
            z-index: 1000;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0,0,0,0.5);
            justify-content: center;
            align-items: center;
        }}
        .modal-content {{
            background-color: white;
            padding: 40px;
            border-radius: 24px;
            width: 70%;
            max-height: 80%;
            overflow-y: auto;
            position: relative;
            box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
        }}
        .modal-close {{
            position: absolute;
            top: 20px;
            right: 20px;
            font-size: 28pt;
            font-weight: bold;
            color: var(--text-muted);
            cursor: pointer;
        }}
        .modal-header {{
            display: flex;
            align-items: center;
            gap: 20px;
            margin-bottom: 30px;
            border-bottom: 2px solid var(--soft-bg);
            padding-bottom: 20px;
        }}
        .modal-icon {{ font-size: 32pt; }}
        .modal-section {{ margin-bottom: 25px; }}
        .modal-section h3 {{ font-size: 12pt; color: var(--text-muted); margin-bottom: 10px; }}
        .modal-list {{ list-style: none; padding: 0; }}
        .modal-list li {{
            font-size: 11pt;
            padding: 12px 15px;
            background: var(--soft-bg);
            margin-bottom: 8px;
            border-radius: 10px;
            border-left: 4px solid var(--primary);
        }}

        @media print {{
            body {{ background: white; }}
            .page {{ margin: 0; box-shadow: none; }}
            .no-print {{ display: none; }}
            .modal {{ display: none !important; }}
        }}
    </style>
</head>
<body>

<!-- PAGE 1: COVER -->
<div class="cover page-break">
    <div class="cover-content">
        <div style="font-size: 12pt; letter-spacing: 8px; font-weight: 300; margin-bottom: 30px;">STRATEGY REPORT</div>
        <h1>{club_name}</h1>
        <div class="subtitle">Piano Strategico Triennale</div>
        <div style="margin-top: 60px;">
            <div style="font-weight: 800; font-size: 14pt;">{current_year} — {current_year + 3}</div>
            <div style="font-size: 10pt; opacity: 0.8; margin-top: 5px;">EXECUTIVE SUMMARY FOR THE BOARD</div>
        </div>
    </div>
    {timing_badge_html}
    <div class="cover-footer">
        <div style="font-size: 9pt; letter-spacing: 2px;">POWERED BY ROOTING FUTURE AI ENGINE v5.4.5</div>
    </div>
</div>

<!-- PAGE 2: DASHBOARD DATI -->
<div class="page page-break">
    <h2 class="section-title"><span class="icon-box">📊</span> Dashboard & Credibilità</h2>
    
    <div class="data-header">
        <div style="font-size: 14pt; font-weight: 700; color: var(--text-main);">Fondamenti Scientifici del Piano</div>
        <p style="font-size: 10pt; color: var(--text-muted); margin-top: 8px;">
            Questo report non si basa su astrazioni, ma su una pipeline di dati verificati, benchmark di categoria FIGC 
            e stime algoritmiche validate. La trasparenza del dato è il pilastro della nostra strategia.
        </p>
        
        <div class="data-stats">
            <div class="stat-circle">
                <span class="val">{metadata.get('total_questionnaires', 0)}</span>
                <span class="lbl">Questionari Board</span>
            </div>
            <div class="stat-circle">
                <span class="val">{metadata.get('verified_data_count', 0)}+</span>
                <span class="lbl">Dati Certificati</span>
            </div>
            <div class="stat-circle">
                <span class="val">{int(metadata.get('questionnaire_completion', 0) * 100)}%</span>
                <span class="lbl">Completezza Input</span>
            </div>
        </div>
    </div>

    {stw_dashboard_html}

    <h2 class="section-title"><span class="icon-box">💰</span> Financial Snapshot</h2>
    <div class="kpi-grid">
        <div class="kpi-card">
            <div class="label">Fatturato</div>
            <div class="value">€{fat_val/1_000_000:.1f}M</div>
            <div style="font-size: 7pt; margin-top: 5px;">
                <span class="source-badge source-{'ver' if fatturato and fatturato.tier == DataTier.TIER_1_FACT else 'est'}">
                    {fatturato.tier.value.upper() if fatturato else 'N/A'}
                </span>
            </div>
        </div>
        <div class="kpi-card">
            <div class="label">Monte Ingaggi</div>
            <div class="value">€{mi_val/1_000:.0f}K</div>
            <div style="font-size: 7pt; margin-top: 5px;">
                <span class="source-badge source-{'ver' if monte_ingaggi and monte_ingaggi.tier == DataTier.TIER_1_FACT else 'est'}">
                    {monte_ingaggi.tier.value.upper() if monte_ingaggi else 'N/A'}
                </span>
            </div>
        </div>
        <div class="kpi-card">
            <div class="label">Valore Rosa</div>
            <div class="value">€{vr_val/1_000:.0f}K</div>
            <div style="font-size: 7pt; margin-top: 5px;">
                <span class="source-badge source-{'ver' if valore_rosa and valore_rosa.tier == DataTier.TIER_1_FACT else 'est'}">
                    {valore_rosa.tier.value.upper() if valore_rosa else 'N/A'}
                </span>
            </div>
        </div>
        <div class="kpi-card">
            <div class="label">Margine Op.</div>
            <div class="value" style="color: {'#16a34a' if marg_val >= 0 else '#dc2626'}">€{marg_val/1_000:.0f}K</div>
            <div style="font-size: 7pt; margin-top: 5px;"><span class="source-badge source-est">STIMA</span></div>
        </div>
    </div>

    {comparison_table_html}

    <div class="charts-container">
        <div class="chart-wrapper">
            <div class="chart-title">Analisi dei Gap vs Serie {category}</div>
            {gap_img}
        </div>
        <div class="chart-wrapper">
            <div class="chart-title">Ripartizione Ricavi</div>
            {pie_img}
        </div>
    </div>

    <div class="footer">
        <span>EXECUTIVE REPORT — {club_name.upper()}</span>
        <span>PAGINA 2 DI 4</span>
    </div>
</div>

<!-- PAGE 3: AREE STRATEGICHE -->
<div class="page page-break">
    <h2 class="section-title"><span class="icon-box">🎯</span> Pilastri Strategici</h2>
    
    <div class="areas-grid">
        {areas_html.replace('area-box', 'area-card').replace('obj-label macro', 'tag tag-macro').replace('obj-label micro', 'tag tag-action')}
    </div>

    <h2 class="section-title" style="margin-top: 40px;"><span class="icon-box">📅</span> Roadmap Evolutiva</h2>
    <div style="padding: 20px; background: var(--soft-bg); border-radius: 20px;">
        {timeline_html}
    </div>

    <div class="footer">
        <span>EXECUTIVE REPORT — {club_name.upper()}</span>
        <span>PAGINA 3 DI 4</span>
    </div>
</div>

<!-- PAGE 4: METODOLOGIA -->
<div class="page">
    <h2 class="section-title"><span class="icon-box">🛡️</span> Metodologia & Fonti</h2>
    
    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 30px;">
        <div class="chart-wrapper">
            <h3 style="font-size: 12pt; margin-bottom: 15px;">Fonti di Riferimento</h3>
            <ul class="area-list">
                <li><strong>Questionari Rooting Future:</strong> Input diretti del Board compilati via Word.</li>
                <li><strong>Report Calcio FIGC 2024:</strong> Benchmark finanziari e sportivi ufficiali.</li>
                <li><strong>Transfermarkt Pro:</strong> Valutazioni di mercato e trend di rosa.</li>
                <li><strong>Web Intelligence:</strong> Analisi del contesto territoriale e news.</li>
            </ul>
        </div>
        <div class="chart-wrapper">
            <h3 style="font-size: 12pt; margin-bottom: 15px;">Validazione Dati</h3>
            <ul class="area-list">
                {_format_estimated_fields(estimated_fields)}
            </ul>
        </div>
    </div>

    <div style="margin-top: 40px; padding: 25px; border-radius: 20px; background: var(--brand-gradient); color: white;">
        <h3 style="margin: 0 0 10px 0;">Nota di Confidenzialità</h3>
        <p style="font-size: 9pt; opacity: 0.9; margin: 0;">
            Il presente documento è ad uso esclusivo del Board di {club_name}. I dati qui contenuti sono il risultato di elaborazioni AI 
            basate sulla metodologia proprietaria Rooting Future Strategy Engine. Ogni riproduzione è vietata.
        </p>
    </div>

    <div class="footer">
        <span>ROOTING FUTURE STRATEGY ENGINE v5.4.5</span>
        <span>{datetime.now().strftime('%d/%m/%Y')} — PAGINA 4 DI 4</span>
    </div>
</div>

{modals_html}

<script>
function openModal(modalId) {{
    document.getElementById(modalId).style.display = 'flex';
    document.body.style.overflow = 'hidden';
}}
function closeModal(modalId) {{
    document.getElementById(modalId).style.display = 'none';
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
