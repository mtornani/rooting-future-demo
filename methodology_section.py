"""
Methodology Section Generator
==============================

Genera la sezione "Metodologia e Fonti" per i report,
rendendo trasparente la provenienza di ogni dato.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass


@dataclass
class DataSourceInfo:
    """Informazioni su una fonte dati"""
    name: str
    type: str  # 'tier1_fact', 'tier2_deduced', 'tier3_estimated'
    description: str
    confidence: float
    url: Optional[str] = None


# Fonti standard del sistema
SYSTEM_SOURCES = {
    'transfermarkt': DataSourceInfo(
        name='Transfermarkt',
        type='tier1_fact',
        description='Valori di mercato rosa, statistiche giocatori',
        confidence=0.90,
        url='https://www.transfermarkt.it'
    ),
    'figc_report': DataSourceInfo(
        name='Report Calcio FIGC 2024',
        type='tier1_fact',
        description='Benchmark finanziari e sportivi ufficiali per categoria',
        confidence=0.95,
        url='https://www.figc.it/it/federazione/report-calcio/'
    ),
    'web_search': DataSourceInfo(
        name='Ricerca Web (Serper/Google)',
        type='tier2_deduced',
        description='News, articoli, bilanci pubblici, comunicati stampa',
        confidence=0.70
    ),
    'knowledge_base': DataSourceInfo(
        name='Knowledge Base Interna',
        type='tier1_fact',
        description='Documenti PDF caricati (bilanci, statuti, piani precedenti)',
        confidence=0.85
    ),
    'benchmark_calc': DataSourceInfo(
        name='Calcolo da Benchmark',
        type='tier3_estimated',
        description='Stima algoritmica basata su medie di categoria FIGC',
        confidence=0.40
    ),
    'derived_calc': DataSourceInfo(
        name='Calcolo Derivato',
        type='tier2_deduced',
        description='Valore calcolato da altri dati noti (es. monte ingaggi da valore rosa)',
        confidence=0.55
    )
}


def generate_methodology_section_html(
    club_name: str,
    category: str,
    data_sources_used: List[str],
    estimated_fields: Dict[str, str],
    primary_color: str = '#1a365d'
) -> str:
    """
    Genera HTML della sezione Metodologia e Fonti.

    Args:
        club_name: Nome del club
        category: Categoria (Serie A, B, C, D, Eccellenza, etc.)
        data_sources_used: Lista di chiavi fonti usate (es. ['transfermarkt', 'figc_report'])
        estimated_fields: Dict {nome_campo: tier} dei campi stimati
        primary_color: Colore primario per styling

    Returns:
        HTML string della sezione
    """

    # Genera lista fonti
    sources_html = ""
    for source_key in data_sources_used:
        source = SYSTEM_SOURCES.get(source_key)
        if source:
            confidence_pct = int(source.confidence * 100)
            tier_badge = _get_tier_badge(source.type)
            url_html = f' <a href="{source.url}" target="_blank" style="color:{primary_color};">↗</a>' if source.url else ''

            sources_html += f'''
            <div class="source-item">
                <div class="source-header">
                    <span class="source-name">{source.name}{url_html}</span>
                    {tier_badge}
                </div>
                <div class="source-desc">{source.description}</div>
                <div class="confidence-bar">
                    <div class="confidence-fill" style="width:{confidence_pct}%;background:{_get_confidence_color(source.confidence)};"></div>
                    <span class="confidence-label">Affidabilità: {confidence_pct}%</span>
                </div>
            </div>
            '''

    # Genera tabella campi stimati
    estimated_html = ""
    if estimated_fields:
        rows = ""
        for field, tier in estimated_fields.items():
            tier_badge = _get_tier_badge(tier)
            field_label = field.replace('_', ' ').title()
            rows += f'''
            <tr>
                <td>{field_label}</td>
                <td>{tier_badge}</td>
                <td>{_get_tier_explanation(tier)}</td>
            </tr>
            '''

        estimated_html = f'''
        <div class="estimated-section">
            <h4>Dati Stimati nel Report</h4>
            <p class="disclaimer">I seguenti valori non provengono da fonti ufficiali dirette ma sono stati calcolati algoritmicamente:</p>
            <table class="estimated-table">
                <thead>
                    <tr>
                        <th>Campo</th>
                        <th>Tipo</th>
                        <th>Metodologia</th>
                    </tr>
                </thead>
                <tbody>
                    {rows}
                </tbody>
            </table>
        </div>
        '''

    # Genera spiegazione Tier
    tier_explanation = '''
    <div class="tier-legend">
        <h4>Legenda Affidabilità Dati</h4>
        <div class="tier-items">
            <div class="tier-item">
                <span class="tier-badge tier-1">FATTO</span>
                <span>Dato verificato da fonte ufficiale (bilancio, FIGC, Transfermarkt)</span>
            </div>
            <div class="tier-item">
                <span class="tier-badge tier-2">DEDOTTO</span>
                <span>Calcolato da dati correlati o fonti indirette</span>
            </div>
            <div class="tier-item">
                <span class="tier-badge tier-3">STIMA</span>
                <span>Stima algoritmica basata su benchmark di categoria</span>
            </div>
        </div>
    </div>
    '''

    return f'''
    <section class="section methodology-section" id="methodology">
        <div class="section-header" style="background:linear-gradient(135deg,{primary_color},#2d3748);">
            <span class="section-number">📊</span>
            <h2>Metodologia e Fonti</h2>
        </div>
        <div class="content methodology-content">
            <div class="methodology-intro">
                <p>Questo report è stato generato da <strong>Rooting Future Strategy Engine v5.4</strong>,
                un sistema di intelligenza artificiale specializzato in pianificazione strategica per club calcistici.</p>
                <p>I dati presentati provengono da molteplici fonti con diversi livelli di affidabilità,
                come indicato dalle etichette <span class="tier-badge tier-1">FATTO</span>,
                <span class="tier-badge tier-2">DEDOTTO</span> e <span class="tier-badge tier-3">STIMA</span>.</p>
            </div>

            <div class="sources-section">
                <h4>Fonti Dati Utilizzate</h4>
                <div class="sources-grid">
                    {sources_html}
                </div>
            </div>

            {estimated_html}

            {tier_explanation}

            <div class="benchmark-note">
                <h4>Benchmark di Riferimento: {category}</h4>
                <p>I valori di benchmark utilizzati per le stime si riferiscono alla categoria <strong>{category}</strong>
                e derivano principalmente dal <em>Report Calcio FIGC 2024</em> e da elaborazioni su dati pubblici del settore.</p>
                <p class="update-note">Ultimo aggiornamento benchmark: Gennaio 2024</p>
            </div>

            <div class="disclaimer-box">
                <strong>⚠️ Disclaimer</strong>
                <p>I dati contrassegnati come [STIMA] o [DEDOTTO] hanno natura indicativa e potrebbero differire
                significativamente dai valori reali. Si raccomanda di verificare i dati critici con fonti ufficiali
                prima di assumere decisioni strategiche o finanziarie.</p>
                <p>Generato il {datetime.now().strftime('%d/%m/%Y alle %H:%M')}</p>
            </div>
        </div>

        <style>
            .methodology-section {{
                background: #f8fafc;
            }}
            .methodology-content {{
                padding: 30px;
            }}
            .methodology-intro {{
                background: white;
                padding: 20px;
                border-radius: 8px;
                border-left: 4px solid {primary_color};
                margin-bottom: 25px;
            }}
            .methodology-intro p {{
                margin: 10px 0;
                line-height: 1.7;
            }}
            .sources-section h4, .estimated-section h4, .tier-legend h4, .benchmark-note h4 {{
                color: {primary_color};
                margin-bottom: 15px;
                font-size: 1.1rem;
            }}
            .sources-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
                gap: 15px;
                margin-bottom: 25px;
            }}
            .source-item {{
                background: white;
                padding: 15px;
                border-radius: 8px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.06);
            }}
            .source-header {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 8px;
            }}
            .source-name {{
                font-weight: 600;
                color: #2d3748;
            }}
            .source-desc {{
                font-size: 0.85rem;
                color: #718096;
                margin-bottom: 10px;
            }}
            .confidence-bar {{
                height: 6px;
                background: #e2e8f0;
                border-radius: 3px;
                position: relative;
                overflow: hidden;
            }}
            .confidence-fill {{
                height: 100%;
                border-radius: 3px;
                transition: width 0.3s;
            }}
            .confidence-label {{
                font-size: 0.75rem;
                color: #718096;
                display: block;
                margin-top: 4px;
            }}
            .tier-badge {{
                padding: 3px 8px;
                border-radius: 4px;
                font-size: 0.7rem;
                font-weight: 700;
                letter-spacing: 0.5px;
            }}
            .tier-1, .tier-badge[class*="tier1"] {{
                background: #C8E6C9;
                color: #2E7D32;
            }}
            .tier-2, .tier-badge[class*="tier2"] {{
                background: #BBDEFB;
                color: #1565C0;
            }}
            .tier-3, .tier-badge[class*="tier3"] {{
                background: #FFF9C4;
                color: #F57F17;
            }}
            .estimated-table {{
                width: 100%;
                border-collapse: collapse;
                margin: 15px 0;
                background: white;
                border-radius: 8px;
                overflow: hidden;
            }}
            .estimated-table th {{
                background: {primary_color};
                color: white;
                padding: 12px;
                text-align: left;
                font-size: 0.85rem;
            }}
            .estimated-table td {{
                padding: 12px;
                border-bottom: 1px solid #e2e8f0;
                font-size: 0.9rem;
            }}
            .tier-legend {{
                background: white;
                padding: 20px;
                border-radius: 8px;
                margin: 25px 0;
            }}
            .tier-items {{
                display: flex;
                flex-direction: column;
                gap: 10px;
            }}
            .tier-item {{
                display: flex;
                align-items: center;
                gap: 12px;
            }}
            .tier-item span:last-child {{
                color: #4a5568;
                font-size: 0.9rem;
            }}
            .benchmark-note {{
                background: linear-gradient(135deg, #e8f5e9, #f1f8e9);
                padding: 20px;
                border-radius: 8px;
                margin: 25px 0;
            }}
            .benchmark-note p {{
                margin: 8px 0;
            }}
            .update-note {{
                font-size: 0.85rem;
                color: #718096;
                font-style: italic;
            }}
            .disclaimer-box {{
                background: #fff8e1;
                border: 1px solid #ffcc02;
                padding: 20px;
                border-radius: 8px;
                margin-top: 25px;
            }}
            .disclaimer-box strong {{
                color: #f57c00;
                display: block;
                margin-bottom: 10px;
            }}
            .disclaimer-box p {{
                margin: 8px 0;
                font-size: 0.9rem;
                color: #5d4037;
            }}
            .disclaimer {{
                font-size: 0.9rem;
                color: #718096;
                margin-bottom: 15px;
            }}
            @media print {{
                .methodology-section {{
                    page-break-before: always;
                }}
            }}
        </style>
    </section>
    '''


def _get_tier_badge(tier_type: str) -> str:
    """Genera badge HTML per il tier"""
    if 'tier1' in tier_type or tier_type == 'fatto':
        return '<span class="tier-badge tier-1">FATTO</span>'
    elif 'tier2' in tier_type or tier_type == 'dedotto':
        return '<span class="tier-badge tier-2">DEDOTTO</span>'
    else:
        return '<span class="tier-badge tier-3">STIMA</span>'


def _get_tier_explanation(tier_type: str) -> str:
    """Restituisce spiegazione del metodo di calcolo"""
    explanations = {
        'tier1_fact': 'Dato verificato da fonte ufficiale',
        'fatto': 'Dato verificato da fonte ufficiale',
        'tier2_deduced': 'Calcolato da valore rosa × moltiplicatore categoria',
        'dedotto': 'Calcolato da dati correlati noti',
        'tier3_estimated': 'Media benchmark categoria (Report FIGC 2024)',
        'stimato': 'Stima da benchmark categoria'
    }
    return explanations.get(tier_type, 'Metodologia non specificata')


def _get_confidence_color(confidence: float) -> str:
    """Restituisce colore in base al livello di confidence"""
    if confidence >= 0.8:
        return '#38a169'  # Verde
    elif confidence >= 0.5:
        return '#3182ce'  # Blu
    else:
        return '#dd6b20'  # Arancione


def get_default_sources_for_report() -> List[str]:
    """Restituisce lista fonti standard usate in ogni report"""
    return ['figc_report', 'web_search', 'knowledge_base', 'benchmark_calc']
