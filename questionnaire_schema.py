"""
Schema questionari Rooting Future.
Struttura dati per i form digitali compilati dal Direttivo.
Ogni questionario corrisponde a un DOCX originale.
"""

QUESTIONNAIRES = {
    "valori-fondamenta": {
        "title": "Valori e Fondamenta",
        "description": "I valori sono le convinzioni fondamentali del club. Le fondamenta sono i pilastri su cui si fonda, non circoscritti ad uno specifico Piano Strategico.",
        "icon": "🏛️",
        "sections": [
            {
                "id": "valori",
                "title": "Valori del Club",
                "intro": "Elencare fino a 5 valori fondamentali del club con una breve descrizione.",
                "type": "repeatable",
                "min_items": 1,
                "max_items": 5,
                "fields": [
                    {"id": "valore", "label": "Valore", "type": "text", "placeholder": "es. Integrità, Passione, Trasparenza..."},
                    {"id": "descrizione", "label": "Descrizione", "type": "textarea", "placeholder": "Come lo dimostriamo concretamente?"},
                ],
            },
            {
                "id": "fondamenta",
                "title": "Fondamenta del Club",
                "intro": "I pilastri su cui si fonda il club. Aree d'azione che guidano il club in un lasso temporale ampio (3-5 pilastri).",
                "type": "repeatable",
                "min_items": 1,
                "max_items": 5,
                "fields": [
                    {"id": "pilastro", "label": "Pilastro", "type": "text", "placeholder": "es. Sostenibilità"},
                    {"id": "motivazione", "label": "Motivazione", "type": "textarea", "placeholder": "Perché questo pilastro è fondamentale?"},
                ],
            },
            {
                "id": "note_fondamenta",
                "title": "Note aggiuntive",
                "type": "static",
                "fields": [
                    {"id": "opinione", "label": "Ha una visione differente rispetto alle fondamenta proposte? Motivi in poche righe.", "type": "textarea", "required": False},
                ],
            },
        ],
    },
    "vision": {
        "title": "Visione",
        "description": "La visione aziendale è una proiezione del futuro del club. Uno scenario che si lega ai valori e alle fondamenta.",
        "icon": "🔭",
        "sections": [
            {
                "id": "vision_main",
                "title": "Visione del Club",
                "type": "static",
                "fields": [
                    {"id": "parole_chiave", "label": "Elenchi in ordine di importanza le parole che reputa debbano essere presenti nella Vision", "type": "textarea", "placeholder": "es. crescita, territorio, giovani, eccellenza..."},
                    {"id": "nel_2028", "label": "Nel 2028 il club sarà...", "type": "textarea", "placeholder": "Descriva come vede il club fra 3 anni"},
                    {"id": "entro_2028", "label": "Entro il 2028 il club avrà raggiunto...", "type": "textarea", "placeholder": "Traguardi concreti"},
                    {"id": "vision_frase", "label": "Provi a scrivere una bozza della dichiarazione di Vision (una frase)", "type": "textarea", "placeholder": "Un sogno realizzabile, memorabile e concreto"},
                ],
            },
        ],
    },
    "mission": {
        "title": "Missione",
        "description": "La missione stabilisce le risorse necessarie per raggiungere gli obiettivi, focalizzandosi sul presente e breve periodo.",
        "icon": "🎯",
        "sections": [
            {
                "id": "mission_main",
                "title": "Missione Aziendale",
                "type": "static",
                "fields": [
                    {"id": "parole_chiave", "label": "Elenchi in ordine di importanza le parole che reputa debbano essere presenti nella Mission", "type": "textarea"},
                    {"id": "cosa_facciamo", "label": "Cosa facciamo?", "type": "textarea"},
                    {"id": "come_lo_facciamo", "label": "Come lo facciamo?", "type": "textarea"},
                    {"id": "per_chi", "label": "Per chi lo facciamo?", "type": "textarea"},
                    {"id": "benefici", "label": "Quali sono i benefici che creiamo con quello che facciamo?", "type": "textarea"},
                    {"id": "mission_bozza", "label": "Scriva la sua bozza della dichiarazione di Mission", "type": "textarea", "placeholder": "La mission in una frase concisa"},
                ],
            },
        ],
    },
    "swot": {
        "title": "Analisi SWOT",
        "description": "Analisi dei punti di forza e debolezza interni, opportunità e minacce esterne del club.",
        "icon": "📊",
        "sections": [
            {
                "id": "swot_grid",
                "title": "Matrice SWOT",
                "type": "static",
                "fields": [
                    {"id": "forza", "label": "Punti di Forza (Strengths) — Analisi Interna", "type": "textarea", "placeholder": "Elencare i punti di forza del club..."},
                    {"id": "debolezza", "label": "Punti di Debolezza (Weaknesses) — Analisi Interna", "type": "textarea", "placeholder": "Elencare le debolezze del club..."},
                    {"id": "opportunita", "label": "Opportunità (Opportunities) — Analisi Esterna", "type": "textarea", "placeholder": "Elencare le opportunità del contesto..."},
                    {"id": "minacce", "label": "Minacce (Threats) — Analisi Esterna", "type": "textarea", "placeholder": "Elencare le minacce esterne..."},
                ],
            },
        ],
    },
    "competitors": {
        "title": "Analisi Competitors",
        "description": "Definire e valutare i competitor diretti e indiretti del club (calcistici e non).",
        "icon": "⚔️",
        "sections": [
            {
                "id": "competitors_list",
                "title": "Competitor",
                "intro": "Inserire competitor diretti (altri club calcistici) e indiretti (altri sport, intrattenimento). Minimo 3.",
                "type": "repeatable",
                "min_items": 3,
                "max_items": 6,
                "fields": [
                    {"id": "nome", "label": "Competitor (diretto o indiretto)", "type": "text", "placeholder": "es. US Fiorenzuola, Pallavolo Riccione..."},
                    {"id": "punti_forza", "label": "Punti di forza del competitor", "type": "textarea", "placeholder": "Marketing, digital, commerciale, sportivo..."},
                    {"id": "debolezze", "label": "Debolezze del competitor", "type": "textarea"},
                    {"id": "azioni", "label": "Almeno 2 azioni per competere meglio", "type": "textarea"},
                ],
            },
        ],
    },
    "pest": {
        "title": "Analisi PEST",
        "description": "Analisi dei fattori Politici, Economici, Sociali e Tecnologici del contesto in cui opera il club.",
        "icon": "🌍",
        "sections": [
            {
                "id": "pest_grid",
                "title": "Fattori PEST",
                "type": "static",
                "fields": [
                    {"id": "politica", "label": "Fattori Politici", "type": "textarea", "placeholder": "Legislazione, regolamenti sportivi, politiche locali..."},
                    {"id": "economica", "label": "Fattori Economici", "type": "textarea", "placeholder": "Crescita economica locale, sponsorizzazioni, budget..."},
                    {"id": "sociale", "label": "Fattori Sociali", "type": "textarea", "placeholder": "Demografia, tendenze culturali, partecipazione sportiva..."},
                    {"id": "tecnologica", "label": "Fattori Tecnologici / Sostenibilità", "type": "textarea", "placeholder": "Digitalizzazione, sostenibilità ambientale, innovazione..."},
                ],
            },
        ],
    },
    "stakeholders": {
        "title": "Analisi Stakeholders",
        "description": "Analisi dei portatori di interesse del club: azionisti, collaboratori, fornitori, sponsor, istituzioni, famiglie, tifosi, media.",
        "icon": "👥",
        "sections": [
            {
                "id": "stakeholders_list",
                "title": "Stakeholders",
                "intro": "Per ogni gruppo di stakeholders, descrivere la relazione attuale e le azioni di miglioramento.",
                "type": "repeatable",
                "min_items": 3,
                "max_items": 13,
                "suggested": ["Azionisti", "Collaboratori", "Fornitori", "Sponsor", "Istituzioni locali", "Scuole", "Istituzioni sportive", "Famiglie settore giovanile", "Abitanti del comune", "Tifosi", "Media", "Altre società calcistiche", "Altre società sportive"],
                "fields": [
                    {"id": "gruppo", "label": "Gruppo di Stakeholders", "type": "text", "placeholder": "es. Tifosi"},
                    {"id": "comunicazione", "label": "Tipologia di comunicazione", "type": "textarea", "placeholder": "Come comunicate attualmente con questo gruppo?"},
                    {"id": "relazione", "label": "Com'è la relazione?", "type": "textarea", "placeholder": "Qualità del rapporto attuale"},
                    {"id": "importanza", "label": "Quanto è importante per il club?", "type": "select", "options": ["Fondamentale", "Molto importante", "Importante", "Moderata", "Bassa"]},
                    {"id": "azioni", "label": "3 azioni per migliorare la relazione nel prossimo anno", "type": "textarea"},
                ],
            },
        ],
    },
    "risorse": {
        "title": "Analisi Risorse",
        "description": "Censimento delle risorse attuali del club: umane, strutturali, patrimoniali. Valutazione strategica degli interventi futuri.",
        "icon": "💎",
        "sections": [
            {
                "id": "risorse_list",
                "title": "Categorie di Risorse",
                "type": "repeatable",
                "min_items": 3,
                "max_items": 5,
                "suggested_items": [
                    {"categoria": "Umane"},
                    {"categoria": "Strutturali"},
                    {"categoria": "Patrimoniali"},
                ],
                "fields": [
                    {"id": "categoria", "label": "Categoria Risorse", "type": "text", "placeholder": "es. Umane, Strutturali, Patrimoniali"},
                    {"id": "lista_attuali", "label": "Lista risorse attuali", "type": "textarea", "placeholder": "Elencare le risorse disponibili in questa categoria"},
                    {"id": "cosa_manca", "label": "Cosa manca attualmente?", "type": "textarea", "placeholder": "Lacune e necessità"},
                    {"id": "interventi_5anni", "label": "Dove intervenire nei prossimi 5 anni?", "type": "textarea", "placeholder": "Priorità strategiche di intervento"},
                ],
            },
        ],
    },
}

# Ordine di compilazione consigliato
QUESTIONNAIRE_ORDER = [
    "valori-fondamenta",
    "vision",
    "mission",
    "swot",
    "competitors",
    "pest",
    "stakeholders",
    "risorse",
]
