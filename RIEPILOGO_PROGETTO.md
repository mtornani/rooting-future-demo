# Rooting Future Strategy Engine v5.4

## Riepilogo Progetto

**Data:** 14 Dicembre 2025
**Stato:** In sviluppo attivo

---

## Descrizione

Sistema AI multi-agente per la generazione automatica di piani strategici triennali per società calcistiche italiane. Il sistema analizza dati del club, effettua ricerche web, e genera documenti professionali con validazione scientifica dei dati.

---

## Architettura Tecnica

### Stack Tecnologico
- **Backend:** Python 3.11 + Flask
- **AI Engine:** Google Gemini 2.0 Flash (multi-agente)
- **Database:** SQLite + JSON knowledge base
- **Frontend:** HTML/CSS/JS vanilla (Jinja2 templates)
- **Export:** python-docx, HTML custom

### Struttura Directory
```
rooting_future/
├── app.py                    # Flask application principale
├── agents.py                 # Sistema multi-agente (8 agenti specializzati)
├── web_research.py           # Modulo ricerca web automatica
├── knowledge_store.py        # Knowledge base e apprendimento
├── post_production_editor.py # Sistema review e approvazione
├── export_docx.py            # Export DOCX professionale
├── export_html.py            # Export HTML (single + multipage)
├── data_models.py            # [NEW] Modelli dati strutturati
├── structured_agent.py       # [NEW] Agenti con output JSON strutturato
├── structured_renderer.py    # [NEW] Renderer HTML per dati strutturati
├── config.py                 # Configurazione
├── templates/                # Template Jinja2
│   ├── base.html
│   ├── index.html
│   ├── new_plan.html
│   ├── plan_detail.html
│   ├── plans_list.html
│   └── review_queue.html
├── static/
│   ├── css/style.css
│   └── js/main.js
├── output/                   # File esportati
└── knowledge_base/           # Dati ricerca e piani salvati
```

---

## Sistema Multi-Agente

### Agenti Implementati (8)
1. **Technical Sporting Agent** - Area tecnico-sportiva
2. **Youth Development Agent** - Settore giovanile
3. **Infrastructure Agent** - Infrastrutture e impianti
4. **Marketing Commercial Agent** - Marketing e commerciale
5. **Social Sustainability Agent** - Sostenibilità e impatto sociale
6. **Governance Agent** - Governance e organizzazione
7. **Financial Agent** - Piano economico-finanziario
8. **Coordinator Agent** - Executive summary e coordinamento

### Flusso di Generazione
1. Input dati club (form web)
2. Ricerca web automatica (Google Search API)
3. Generazione parallela sezioni (Gemini 2.0)
4. Post-produzione e review
5. Approvazione sezioni
6. Export finale

---

## Sistema di Validazione Scientifica (NUOVO)

### Problema Risolto
L'output degli agenti AI era "una lista interminabile di parole senza cognizione di causa" - mancava oggettività e riferimenti a benchmark verificabili.

### Soluzione Implementata

#### Data Models (`data_models.py`)
```python
@dataclass
class DataPoint:
    id: str
    label: str
    category: str
    value: Union[float, int, str, None]
    unit: Optional[str] = None
    data_type: DataType  # VERIFIED, BENCHMARK, ESTIMATE, TO_ACQUIRE
    source: Optional[Source] = None
    benchmark: Optional[Benchmark] = None
    deviation: Optional[float] = None
    deviation_type: Optional[DeviationType]  # ABOVE, BELOW, ALIGNED, CRITICAL
    confidence: float = 0.0
    confidence_level: ConfidenceLevel  # HIGH, MEDIUM, LOW, VERY_LOW
```

#### Tipi di Dato
- **VERIFIED** - Dato verificato da fonte ufficiale
- **BENCHMARK** - Valore di riferimento di categoria
- **ESTIMATE** - Stima basata su dati disponibili
- **TO_ACQUIRE** - Dato mancante da acquisire
- **CALCULATED** - Calcolato da altri dati
- **PROJECTED** - Proiezione futura

#### Livelli di Confidenza
- **HIGH** (90-100%) - Fonte ufficiale verificata
- **MEDIUM** (70-89%) - Fonte affidabile
- **LOW** (50-69%) - Stima ragionevole
- **VERY_LOW** (<50%) - Dato incerto

#### Tipi di Deviazione
- **ALIGNED** (±10%) - In linea con benchmark
- **ABOVE** (>10%) - Sopra benchmark
- **BELOW** (<-10%) - Sotto benchmark
- **CRITICAL** (>50%) - Scostamento critico

#### Database Benchmark
Benchmark pre-caricati per tutte le categorie:
- Serie A, Serie B, Serie C
- Serie D, Eccellenza

Metriche per categoria:
- Fatturato medio
- Monte ingaggi
- Capienza stadio
- Età media rosa
- Tesserati settore giovanile
- etc.

### Structured Renderer (`structured_renderer.py`)

Output HTML professionale con:
- **Credibility Dashboard** - Metriche aggregate di affidabilità
- **Data Cards** - Visualizzazione singoli data point con:
  - Valore e unità
  - Badge tipo dato (Verificato/Stima/Da Acquisire)
  - Badge confidenza (%)
  - Confronto benchmark con valore di riferimento
  - Indicatore deviazione (colorato per severità)
  - Citazione fonte con nota a piè di pagina
- **Key Findings** - Evidenze chiave per sezione
- **Raccomandazioni** - Azioni strategiche prioritizzate
- **Bibliografia** - Fonti citate con numerazione

### API Endpoints Strutturati
```
POST /api/structured/generate     # Genera piano strutturato
GET  /api/structured/benchmarks/  # Ottiene benchmark per categoria
GET  /api/structured/templates    # Ottiene template data point
```

---

## Sistema Export Attuale

### DOCX (`export_docx.py`)
- Layout professionale con brand colors
- Copertina con metadata
- Indice navigabile
- Sezioni con heading gerarchici
- Tabelle formattate
- Liste puntate/numerate
- Box KPI evidenziati
- Footer con paginazione

### HTML (`export_html.py`)
- Single page completa
- Versione multipage navigabile
- CSS professionale embedded
- Responsive design
- Print-friendly styles
- Indice con anchor links

### Problemi Identificati

1. **Popup Blocker** - Export multiplo (DOCX+HTML) usa `window.open()` che viene bloccato dai browser per il secondo file

2. **Formato non ottimale** - DOCX e HTML non sono ideali per documenti strategici da presentare a board:
   - DOCX: modificabile (non sempre desiderato), formattazione può variare
   - HTML: non professionale per stampa/presentazione

3. **Mancanza PDF** - Il formato PDF sarebbe più appropriato:
   - Layout fisso e professionale
   - Non modificabile
   - Stampa perfetta
   - Standard per documenti ufficiali

---

## Frontend Attuale

### Pagine
- **Home** (`/`) - Dashboard con statistiche e accesso rapido
- **Nuovo Piano** (`/new`) - Form inserimento dati club
- **Lista Piani** (`/plans`) - Elenco con filtri e paginazione
- **Dettaglio Piano** (`/plan/<id>`) - View/edit sezioni, approvazione, export
- **Review Queue** (`/review-queue`) - Coda revisione pending

### Funzionalità UI
- Form validazione client-side
- Modal per edit sezioni
- Toast notifications
- Loading states
- Live search/filter
- Responsive layout base

### Limitazioni
- UI/UX basic (non moderne)
- No framework CSS (tutto custom)
- JavaScript vanilla (no reattività)
- Manca preview real-time
- Export UX problematica (popup blocker)
- No drag & drop
- No dark mode
- Mobile experience limitata

---

## Richieste di Consulenza

### 1. Frontend Framework
Quale approccio consiglieresti per modernizzare il frontend?
- React/Vue/Svelte per SPA?
- HTMX per progressive enhancement?
- Tailwind/Bootstrap per styling?
- Mantenere server-side rendering con Jinja2?

### 2. Sistema Export
Come gestire l'export in modo più professionale?
- Aggiungere PDF (weasyprint/reportlab/puppeteer)?
- Download singolo ZIP con tutti i formati?
- Preview in-browser prima dell'export?
- Quale formato prioritizzare per documenti strategici?

### 3. UX Export
Come risolvere il problema del popup blocker per download multipli?
- Generare ZIP server-side?
- Download sequenziale con delay?
- Modale con link ai file generati?
- Usare Blob/download attribute invece di window.open?

### 4. Integrazione Sistema Strutturato
Il nuovo sistema di validazione scientifica (`structured_*`) genera HTML standalone. Come integrarlo meglio nel flusso esistente?
- Sostituire completamente il sistema markdown-based?
- Offrire entrambe le modalità?
- Unificare i renderer?

---

## Metriche Esempio Output Strutturato

```
Club: Rimini FC
Categoria: Serie C

Credibilità Complessiva: 7.0%
Data Points Totali: 20
Dati Verificati: 0
Completezza Dati: 10%
Fonti Citate: 1

Esempio Data Card:
┌─────────────────────────────────────────┐
│ Fatturato Annuo                         │
│ [Stima] [70%]                           │
├─────────────────────────────────────────┤
│ €586K                                   │
│                                         │
│ Benchmark Serie C: €4.5M                │
│ ⚠ -87.0% vs benchmark (CRITICO)        │
│                                         │
│ 📚 Dati forniti dal club [1]           │
└─────────────────────────────────────────┘
```

---

## File da Consultare per Dettagli

- `app.py` - Routing e API endpoints
- `agents.py` - Logica agenti e prompt engineering
- `data_models.py` - Strutture dati validazione
- `structured_renderer.py` - Rendering HTML strutturato
- `export_html.py` / `export_docx.py` - Export attuali
- `templates/plan_detail.html` - UI principale review/export

---

## Prossimi Passi Proposti

1. Decidere strategia frontend (framework vs progressive enhancement)
2. Implementare export PDF professionale
3. Risolvere UX export (ZIP o altro)
4. Integrare sistema strutturato nel flusso principale
5. Migliorare UI/UX generale
6. Aggiungere preview documento pre-export
