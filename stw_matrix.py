"""
Matrice STW - Framework Metodologico
Sport To Win Strategic Framework

Struttura gerarchica degli obiettivi strategici per club sportivi.
Ogni categoria contiene obiettivi MACRO e relative azioni MICRO.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum


class STWCategory(Enum):
    """Categorie principali della Matrice STW"""
    SPORTIVI = "sportivi"
    STRUTTURALI = "strutturali"
    MARKETING = "marketing"
    SOCIALI = "sociali"


@dataclass
class MicroObjective:
    """Singola azione MICRO"""
    code: str  # es. "1.1", "2.3"
    title: str
    description: str = ""


@dataclass
class MacroObjective:
    """Obiettivo MACRO con relative azioni MICRO"""
    code: str  # es. "1", "2"
    title: str
    micro_objectives: List[MicroObjective] = field(default_factory=list)


@dataclass
class STWSection:
    """Sezione della matrice (colonna)"""
    title: str
    macro_objectives: List[MacroObjective] = field(default_factory=list)


# =============================================================================
# MATRICE STW COMPLETA - Framework di riferimento
# =============================================================================

STW_FRAMEWORK: Dict[STWCategory, List[STWSection]] = {

    # =========================================================================
    # OBIETTIVI SPORTIVI
    # =========================================================================
    STWCategory.SPORTIVI: [
        # Colonna 1
        STWSection(
            title="Identità e Struttura Tecnica",
            macro_objectives=[
                MacroObjective(
                    code="1",
                    title="CREAZIONE E SVILUPPO IDENTITÀ TECNICA",
                    micro_objectives=[
                        MicroObjective("1.1", "Definizione e completamento organigramma tecnico",
                                      "Figure in possesso di adeguati titoli e licenze"),
                        MicroObjective("1.2", "Creazione e monitoraggio piano formazione tecnica",
                                      "Programma di aggiornamento continuo per lo staff"),
                    ]
                ),
                MacroObjective(
                    code="2",
                    title="INCREMENTO PARTECIPAZIONE ALL'AZIENDA SPORTIVA",
                    micro_objectives=[
                        MicroObjective("2.1", "Attività promozionali sul territorio",
                                      "Open day, sport in piazza, eventi locali"),
                        MicroObjective("2.2", "Partnership con scuole del territorio",
                                      "Programmi educativi e sportivi congiunti"),
                        MicroObjective("2.3", "Centri estivi per giovani potenziali utenti",
                                      "Campus e attività ricreative"),
                        MicroObjective("2.4", "Eventi per settori meno partecipati",
                                      "Promozione di discipline minori"),
                        MicroObjective("2.5", "Tornei/eventi per non tesserati",
                                      "Apertura al territorio"),
                    ]
                ),
                MacroObjective(
                    code="3",
                    title="POTENZIAMENTO STRUTTURA DIRIGENZIALE",
                    micro_objectives=[
                        MicroObjective("3.1", "Standard per scelta figure dirigenziali",
                                      "Criteri di selezione formalizzati"),
                        MicroObjective("3.2", "Formazione dirigenti esistenti",
                                      "Programmi di aggiornamento manageriale"),
                        MicroObjective("3.3", "Completamento organigramma dirigenziale",
                                      "Definizione ruoli e responsabilità"),
                    ]
                ),
            ]
        ),
        # Colonna 2
        STWSection(
            title="Competitività e Scouting",
            macro_objectives=[
                MacroObjective(
                    code="4",
                    title="MIGLIORAMENTO COMPETITIVO",
                    micro_objectives=[
                        MicroObjective("4.1", "Strategia tecnica coerente SG-Prima Squadra",
                                      "Modello di gioco unificato"),
                        MicroObjective("4.2", "Allenatori con licenza massima",
                                      "Innalzamento qualifiche tecniche"),
                        MicroObjective("4.3", "Miglioramento rete scouting",
                                      "Ampliamento osservatori e strumenti"),
                        MicroObjective("4.4", "Partecipazione a match/tornei qualificanti",
                                      "Competizioni di livello adeguato"),
                    ]
                ),
                MacroObjective(
                    code="5",
                    title="PROPOSTA DEL CLUB PER I TESSERATI",
                    micro_objectives=[
                        MicroObjective("5.1", "Programma tecnico/fisico adeguato",
                                      "Sviluppo e monitoraggio performance"),
                        MicroObjective("5.2", "Potenziamento struttura medica",
                                      "Staff sanitario qualificato"),
                        MicroObjective("5.3", "Potenziamento fisioterapia e macchinari",
                                      "Attrezzature per recupero e prevenzione"),
                        MicroObjective("5.4", "Potenziamento struttura logistica",
                                      "Trasporti, trasferte, organizzazione"),
                    ]
                ),
                MacroObjective(
                    code="6",
                    title="RAFFORZAMENTO SETTORE SCOUTING",
                    micro_objectives=[
                        MicroObjective("6.1", "Responsabile attività di scouting",
                                      "Figura dedicata con competenze specifiche"),
                        MicroObjective("6.2", "Budget dedicato e strumenti",
                                      "Risorse per osservazione e analisi"),
                        MicroObjective("6.3", "Metriche valutazione area scouting",
                                      "KPI per misurare efficacia"),
                        MicroObjective("6.4", "Creazione foresteria",
                                      "Alloggio per atleti fuori sede"),
                    ]
                ),
            ]
        ),
        # Colonna 3
        STWSection(
            title="Club Affiliati e Settori Specifici",
            macro_objectives=[
                MacroObjective(
                    code="7",
                    title="RAFFORZAMENTO CLUB AFFILIATI",
                    micro_objectives=[
                        MicroObjective("7.1", "Responsabile sviluppo club affiliati",
                                      "Coordinamento rete territoriale"),
                        MicroObjective("7.2", "Progetto tecnico coerente",
                                      "Metodologia condivisa"),
                        MicroObjective("7.3", "Incontri tecnici e organizzativi",
                                      "Formazione e networking"),
                        MicroObjective("7.4", "Organizzazione torneo affiliati",
                                      "Evento annuale di riferimento"),
                        MicroObjective("7.5", "Aumento ricavi dedicati",
                                      "Sostenibilità del progetto"),
                        MicroObjective("7.6", "Standard allenatori e formazione",
                                      "Qualità uniforme nella rete"),
                    ]
                ),
                MacroObjective(
                    code="8",
                    title="SVILUPPO AREA TECNICO-SPORTIVA SPECIFICA",
                    micro_objectives=[
                        MicroObjective("8.1", "Partecipazione competizioni competitive",
                                      "Presenza in tornei di livello"),
                        MicroObjective("8.2", "Formazione allenatori e arbitri",
                                      "Staff adeguato allo scopo"),
                        MicroObjective("8.3", "Organizzazione eventi dedicati",
                                      "Competizioni locali"),
                        MicroObjective("8.4", "Reclutamento collaboratori di livello",
                                      "Professionisti per sviluppo settore"),
                        MicroObjective("8.5", "Legame con istituzioni e territorio",
                                      "Partnership strategiche"),
                        MicroObjective("8.6", "Aumento entrate commerciali dedicate",
                                      "Sostenibilità economica"),
                    ]
                ),
            ]
        ),
    ],

    # =========================================================================
    # OBIETTIVI STRUTTURALI E INFRASTRUTTURALI
    # =========================================================================
    STWCategory.STRUTTURALI: [
        STWSection(
            title="Infrastrutture e Risorse Umane",
            macro_objectives=[
                MacroObjective(
                    code="1",
                    title="COSTRUZIONE E RINNOVAMENTO STRUTTURE",
                    micro_objectives=[
                        MicroObjective("1.1", "Rinnovamento campi attuali",
                                      "Manutenzione e upgrade impianti esistenti"),
                        MicroObjective("1.2", "Costruzione nuovi impianti sportivi",
                                      "Espansione capacità e offerta"),
                        MicroObjective("1.3", "Creazione progetto retail store",
                                      "Punto vendita merchandising ufficiale"),
                        MicroObjective("1.4", "Rinnovo/costruzione sede operativa",
                                      "Uffici e spazi amministrativi"),
                    ]
                ),
                MacroObjective(
                    code="2",
                    title="RISORSE UMANE",
                    micro_objectives=[
                        MicroObjective("2.1", "Policy aziendali e standardizzazione processi",
                                      "Formalizzazione procedure HR"),
                        MicroObjective("2.2", "Strumenti monitoraggio lavoro",
                                      "Performance management e feedback"),
                        MicroObjective("2.3", "Programmi benessere aziendale",
                                      "Welfare e work-life balance"),
                    ]
                ),
            ]
        ),
    ],

    # =========================================================================
    # OBIETTIVI MARKETING E COMMERCIALI
    # =========================================================================
    STWCategory.MARKETING: [
        STWSection(
            title="Comunicazione e Marketing",
            macro_objectives=[
                MacroObjective(
                    code="1",
                    title="SVILUPPO AREA COMUNICAZIONE",
                    micro_objectives=[
                        MicroObjective("1.1", "Ufficio stampa strutturato",
                                      "Responsabile con adeguati titoli"),
                        MicroObjective("1.2", "Strumentazione adeguata",
                                      "Tool per social media e media monitoring"),
                        MicroObjective("1.3", "Strumenti misurazione",
                                      "KPI comunicazione (reach, engagement)"),
                    ]
                ),
                MacroObjective(
                    code="2",
                    title="SVILUPPO AREA MARKETING",
                    micro_objectives=[
                        MicroObjective("2.1", "Responsabile qualificato",
                                      "Profilo con competenze marketing sportivo"),
                        MicroObjective("2.2", "Piano marketing annuale",
                                      "Documento formale approvato dal direttivo"),
                        MicroObjective("2.3", "Verifica relazione club-utenti",
                                      "Survey e feedback periodici"),
                        MicroObjective("2.4", "Implementazione CRM",
                                      "Gestione relazioni e privacy"),
                    ]
                ),
            ]
        ),
        STWSection(
            title="Brand e Commerciale",
            macro_objectives=[
                MacroObjective(
                    code="3",
                    title="SVILUPPO BRAND IDENTITY",
                    micro_objectives=[
                        MicroObjective("3.1", "Valorizzazione patrimonio storico",
                                      "Museo, archivio, eventi legacy"),
                        MicroObjective("3.2", "Potenziamento dotazioni sportive",
                                      "Merchandising qualità e quantità"),
                        MicroObjective("3.3", "Marketing automation",
                                      "Profilazione utenti e tifosi"),
                    ]
                ),
                MacroObjective(
                    code="4",
                    title="SVILUPPO AREA COMMERCIALE",
                    micro_objectives=[
                        MicroObjective("4.1", "Piano commerciale formale",
                                      "In accordo col marketing, approvato dal direttivo"),
                        MicroObjective("4.2", "Strutturazione area commerciale",
                                      "Responsabile + team dedicato"),
                        MicroObjective("4.3", "Revisione periodica obiettivi",
                                      "Monitoraggio ricavi e target"),
                    ]
                ),
            ]
        ),
    ],

    # =========================================================================
    # OBIETTIVI SOCIALI E SOSTENIBILITÀ
    # =========================================================================
    STWCategory.SOCIALI: [
        STWSection(
            title="Inclusione e Protezione",
            macro_objectives=[
                MacroObjective(
                    code="1",
                    title="SVILUPPO PROGETTI ANTI-RAZZISMO",
                    micro_objectives=[
                        MicroObjective("1.1", "Promozione campagne istituzionali",
                                      "Adesione a iniziative nazionali/internazionali"),
                        MicroObjective("1.2", "Attività preventive nel club",
                                      "Formazione e sensibilizzazione"),
                        MicroObjective("1.3", "Attività integrate con partner",
                                      "Collaborazioni con associazioni"),
                        MicroObjective("1.4", "Procedure segnalazione abusi",
                                      "Canali sicuri e confidenziali"),
                        MicroObjective("1.5", "Eventi dedicati",
                                      "Giornate tematiche e iniziative"),
                    ]
                ),
                MacroObjective(
                    code="2",
                    title="PROTEZIONE BAMBINI/E E GIOVANI/E",
                    micro_objectives=[
                        MicroObjective("2.1", "Certificazioni idoneità staff",
                                      "Allenatori ed educatori verificati"),
                        MicroObjective("2.2", "Implementazione policy",
                                      "Procedure di safeguarding"),
                        MicroObjective("2.3", "Eventi formazione giovani",
                                      "Educazione e consapevolezza"),
                    ]
                ),
                MacroObjective(
                    code="3",
                    title="SVILUPPO INCLUSIONE E UGUAGLIANZA",
                    micro_objectives=[
                        MicroObjective("3.1", "Adeguamento strutture",
                                      "Accessibilità per tutti"),
                        MicroObjective("3.2", "Attività promozione inclusione",
                                      "Programmi dedicati"),
                        MicroObjective("3.3", "Policy ed eventi dedicati",
                                      "Formalizzazione impegno"),
                    ]
                ),
            ]
        ),
        STWSection(
            title="Salute e Sostenibilità",
            macro_objectives=[
                MacroObjective(
                    code="4",
                    title="ADEGUATEZZA A QUALSIASI ABILITÀ",
                    micro_objectives=[
                        MicroObjective("4.1", "Opportunità sport per tutti",
                                      "Programmi paralimpici e adattati"),
                        MicroObjective("4.2", "Formazione staff e eventi dedicati",
                                      "Competenze specifiche"),
                        MicroObjective("4.3", "Collaborazione partner esterni",
                                      "Associazioni e istituzioni"),
                    ]
                ),
                MacroObjective(
                    code="5",
                    title="SALUTE E BENESSERE",
                    micro_objectives=[
                        MicroObjective("5.1", "Progetti terza età e salute",
                                      "Programmi per over 65 e riabilitazione"),
                        MicroObjective("5.2", "Campagne istituzionali",
                                      "Prevenzione e stili di vita sani"),
                        MicroObjective("5.3", "Programmi nutrizionali",
                                      "Educazione alimentare"),
                    ]
                ),
                MacroObjective(
                    code="6",
                    title="SOLIDARIETÀ E DIRITTI",
                    micro_objectives=[
                        MicroObjective("6.1", "Collaborazione istituzioni statali",
                                      "Supporto campagne istituzionali"),
                        MicroObjective("6.2", "Policy diritti umani",
                                      "Documento formale"),
                        MicroObjective("6.3", "Opportunità per rifugiati",
                                      "Programmi di integrazione"),
                        MicroObjective("6.4", "Garanzia privacy",
                                      "Protezione dati soggetti coinvolti"),
                    ]
                ),
                MacroObjective(
                    code="7",
                    title="ADEGUAMENTO ECONOMIA CIRCOLARE",
                    micro_objectives=[
                        MicroObjective("7.1", "Collaborazione istituzioni",
                                      "Promozione campagne ambientali"),
                        MicroObjective("7.2", "Procedure riduzione impatto",
                                      "Acqua, plastica, gas, carburanti, riciclo"),
                        MicroObjective("7.3", "Adeguamento strutture",
                                      "Impianti eco-sostenibili"),
                        MicroObjective("7.4", "Progetti/eventi green",
                                      "Iniziative per giovani e partner"),
                    ]
                ),
            ]
        ),
    ],
}


# =============================================================================
# FUNZIONI DI UTILITÀ
# =============================================================================

def get_category_name(category: STWCategory) -> str:
    """Restituisce il nome visualizzabile della categoria"""
    names = {
        STWCategory.SPORTIVI: "Obiettivi Sportivi",
        STWCategory.STRUTTURALI: "Obiettivi Strutturali e Infrastrutturali",
        STWCategory.MARKETING: "Obiettivi Marketing e Commerciali",
        STWCategory.SOCIALI: "Obiettivi Sociali e Sostenibilità",
    }
    return names.get(category, category.value)


def get_category_icon(category: STWCategory) -> str:
    """Restituisce un'icona Unicode per la categoria"""
    icons = {
        STWCategory.SPORTIVI: "⚽",
        STWCategory.STRUTTURALI: "🏗️",
        STWCategory.MARKETING: "📢",
        STWCategory.SOCIALI: "🤝",
    }
    return icons.get(category, "📋")


def get_category_color(category: STWCategory) -> str:
    """Restituisce un colore CSS per la categoria"""
    colors = {
        STWCategory.SPORTIVI: "#2E7D32",      # Verde scuro
        STWCategory.STRUTTURALI: "#1565C0",   # Blu
        STWCategory.MARKETING: "#E65100",     # Arancione
        STWCategory.SOCIALI: "#7B1FA2",       # Viola
    }
    return colors.get(category, "#424242")


def count_objectives(category: STWCategory) -> tuple:
    """Conta macro e micro obiettivi per categoria"""
    sections = STW_FRAMEWORK.get(category, [])
    macro_count = sum(len(s.macro_objectives) for s in sections)
    micro_count = sum(
        len(m.micro_objectives)
        for s in sections
        for m in s.macro_objectives
    )
    return macro_count, micro_count


def get_total_counts() -> dict:
    """Restituisce il conteggio totale di tutti gli obiettivi"""
    total_macro = 0
    total_micro = 0
    by_category = {}

    for category in STWCategory:
        macro, micro = count_objectives(category)
        total_macro += macro
        total_micro += micro
        by_category[category.value] = {"macro": macro, "micro": micro}

    return {
        "total_macro": total_macro,
        "total_micro": total_micro,
        "by_category": by_category
    }


# =============================================================================
# GENERAZIONE HTML MATRICE
# =============================================================================

def generate_stw_matrix_html(primary_color: str = "#1a365d") -> str:
    """
    Genera l'HTML della Matrice STW per inclusione nei documenti.
    Design: layout compatto orizzontale con 4 colonne per la overview,
    poi dettaglio sequenziale per ogni categoria.
    """
    counts = get_total_counts()

    # Header con overview compatta
    html = f'''
    <div class="stw-matrix-container chapter" style="page-break-before: always;">
        <h1 class="stw-title">Matrice STW</h1>
        <p class="stw-subtitle">Sport To Win Strategic Framework</p>

        <div class="stw-intro">
            <p>Il presente Piano Strategico è strutturato secondo la <strong>Metodologia STW</strong>,
            un framework proprietario che garantisce una copertura completa di tutte le aree
            strategiche di un club sportivo.</p>
            <div class="stw-stats">
                <div class="stw-stat">
                    <span class="stw-stat-number">4</span>
                    <span class="stw-stat-label">Categorie</span>
                </div>
                <div class="stw-stat">
                    <span class="stw-stat-number">{counts["total_macro"]}</span>
                    <span class="stw-stat-label">Obiettivi Macro</span>
                </div>
                <div class="stw-stat">
                    <span class="stw-stat-number">{counts["total_micro"]}</span>
                    <span class="stw-stat-label">Azioni Micro</span>
                </div>
            </div>
        </div>

        <!-- Overview compatta delle 4 categorie -->
        <div class="stw-overview">
    '''

    # Overview boxes (4 in riga)
    for category in STWCategory:
        cat_color = get_category_color(category)
        cat_icon = get_category_icon(category)
        cat_name = get_category_name(category)
        macro_count, micro_count = count_objectives(category)

        html += f'''
            <div class="stw-overview-box" style="border-top: 4px solid {cat_color};">
                <div class="stw-overview-icon">{cat_icon}</div>
                <div class="stw-overview-name">{cat_name}</div>
                <div class="stw-overview-count">{macro_count} macro · {micro_count} micro</div>
            </div>
        '''

    html += '''
        </div>

        <!-- Dettaglio categorie in sequenza verticale -->
        <div class="stw-details">
    '''

    # Dettaglio per ogni categoria (in sequenza, non griglia)
    for category in STWCategory:
        cat_color = get_category_color(category)
        cat_icon = get_category_icon(category)
        cat_name = get_category_name(category)
        sections = STW_FRAMEWORK.get(category, [])
        macro_count, micro_count = count_objectives(category)

        html += f'''
            <div class="stw-category-detail">
                <div class="stw-category-header-compact" style="background: {cat_color};">
                    <span class="stw-icon">{cat_icon}</span>
                    <span class="stw-category-name">{cat_name}</span>
                </div>
                <div class="stw-category-content">
        '''

        for section in sections:
            html += f'<div class="stw-section-compact"><span class="stw-section-label">{section.title}:</span> '

            macro_items = []
            for macro in section.macro_objectives:
                micro_codes = ", ".join([m.code for m in macro.micro_objectives])
                macro_items.append(f'<strong>{macro.code}.</strong> {macro.title} <span class="stw-micro-codes">({micro_codes})</span>')

            html += " | ".join(macro_items)
            html += '</div>'

        html += '</div></div>'

    html += '''
        </div>

        <div class="stw-legend">
            <p><strong>Legenda:</strong> Gli obiettivi MACRO rappresentano le direzioni strategiche,
            mentre le azioni MICRO sono i passi operativi concreti per raggiungerli.
            Ogni sezione del piano è mappata su questa matrice.</p>
        </div>
    </div>
    '''

    return html


def get_stw_matrix_css() -> str:
    """CSS dedicato per la Matrice STW"""
    return '''
    /* ===========================================
       MATRICE STW - STILI
       =========================================== */
    .stw-matrix-container {
        padding: 0;
    }

    .stw-title {
        font-size: 28pt;
        font-weight: 700;
        color: var(--primary-color);
        text-align: center;
        margin-bottom: 5mm;
        letter-spacing: 2px;
    }

    .stw-subtitle {
        font-size: 14pt;
        color: var(--text-light);
        text-align: center;
        margin-bottom: 8mm;
        font-style: italic;
    }

    .stw-intro {
        background: var(--light-color);
        padding: 6mm;
        border-radius: 3mm;
        margin-bottom: 8mm;
        text-align: center;
    }

    .stw-intro p {
        margin-bottom: 5mm;
        font-size: 11pt;
        line-height: 1.5;
    }

    .stw-stats {
        display: flex;
        justify-content: center;
        gap: 15mm;
    }

    .stw-stat {
        text-align: center;
    }

    .stw-stat-number {
        display: block;
        font-size: 24pt;
        font-weight: 700;
        color: var(--primary-color);
    }

    .stw-stat-label {
        font-size: 9pt;
        color: var(--text-light);
        text-transform: uppercase;
        letter-spacing: 1px;
    }

    .stw-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 5mm;
    }

    .stw-category {
        background: #ffffff;
        border-radius: 2mm;
        overflow: hidden;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        page-break-inside: avoid;
    }

    .stw-category-header {
        color: white;
        padding: 3mm 4mm;
        display: flex;
        align-items: center;
        gap: 2mm;
    }

    .stw-icon {
        font-size: 14pt;
    }

    .stw-category-name {
        font-weight: 600;
        font-size: 10pt;
        flex-grow: 1;
    }

    .stw-category-count {
        font-size: 8pt;
        opacity: 0.9;
    }

    .stw-category-body {
        padding: 3mm 4mm;
    }

    .stw-section {
        margin-bottom: 3mm;
    }

    .stw-section-title {
        font-size: 9pt;
        font-weight: 600;
        color: var(--text-color);
        margin-bottom: 2mm;
        padding-bottom: 1mm;
        border-bottom: 1px solid var(--border-color);
    }

    .stw-macro {
        margin-bottom: 2mm;
    }

    .stw-macro-title {
        font-size: 8pt;
        font-weight: 600;
        color: var(--primary-color);
        margin-bottom: 1mm;
    }

    .stw-micro-list {
        margin: 0;
        padding-left: 4mm;
        font-size: 7pt;
        color: var(--text-light);
        line-height: 1.4;
    }

    .stw-micro-list li {
        margin-bottom: 0.5mm;
    }

    .stw-micro-list strong {
        color: var(--text-color);
    }

    .stw-legend {
        margin-top: 5mm;
        padding: 3mm;
        background: #f8f9fa;
        border-radius: 2mm;
        font-size: 8pt;
        color: var(--text-light);
        text-align: center;
    }

    /* Stampa ottimizzata */
    @media print {
        .stw-category {
            box-shadow: none;
            border: 1px solid var(--border-color);
        }
    }
    '''


if __name__ == "__main__":
    # Test
    counts = get_total_counts()
    print("=== Matrice STW - Conteggio ===")
    print(f"Totale MACRO: {counts['total_macro']}")
    print(f"Totale MICRO: {counts['total_micro']}")
    print()
    for cat, data in counts['by_category'].items():
        print(f"  {cat}: {data['macro']} macro, {data['micro']} micro")
