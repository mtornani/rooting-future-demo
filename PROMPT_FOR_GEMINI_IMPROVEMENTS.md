# Prompt per Gemini - Miglioramenti Rooting Future v5.4.5

## 📋 Contesto Sistema

Stai lavorando su **Rooting Future Strategy Engine v5.4.5**, un sistema Flask che genera piani strategici per società calcistiche italiane utilizzando:
- AI Multi-Agente (OpenAI GPT-4)
- Framework STW (21 MACRO-aree strategiche)
- Web Research automatico
- Ingestion documenti DOCX con stakeholder profiling

**Repository:** `C:\Users\Mirko\Desktop\rooting_future`
**Branch:** `master`
**Python:** 3.x con Flask

---

## 🎯 Task da Completare

### **1. Badge "Da Questionario" per Dati Verificati**

**Obiettivo:** Aggiungere badge visivi che distinguono la fonte dei dati in tutti gli output.

**Files da Modificare:**
- `data_ingestor.py` - Tracciare quali dati vengono da questionari vs web research vs stime AI
- `structured_renderer.py` - Badge visuale nei testi renderizzati
- `export_html.py` - Mostrare badge nel Piano Strategico HTML
- `executive_report.py` - Mostrare badge nell'Executive Report
- `export_onepager.py` - Mostrare badge nel One-Pager (se applicabile)

**Specifiche Design:**

```html
<!-- Badge da aggiungere inline nei dati -->
<span class="badge badge-questionnaire">📋 Da Questionario</span>
<span class="badge badge-research">🔍 Ricerca Web</span>
<span class="badge badge-estimate">📊 Stima AI</span>
```

**CSS da Aggiungere:**
```css
.badge {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 12px;
    font-size: 0.75rem;
    font-weight: 600;
    margin-left: 8px;
    vertical-align: middle;
}

.badge-questionnaire {
    background: linear-gradient(135deg, #7B1FA2, #9C27B0);
    color: white;
}

.badge-research {
    background: linear-gradient(135deg, #0288D1, #03A9F4);
    color: white;
}

.badge-estimate {
    background: linear-gradient(135deg, #F57C00, #FF9800);
    color: white;
}
```

**Logica di Tracking:**

In `data_ingestor.py`, aggiungere a ogni dato un attributo `source`:

```python
# Esempio struttura dati
club_data = {
    'nome': 'ASD Example',
    'categoria': {'value': 'Serie D', 'source': 'questionnaire'},
    'tesserati': {'value': 450, 'source': 'research'},
    'budget': {'value': 500000, 'source': 'estimate'}
}
```

In `structured_renderer.py`, quando renderizzi un dato, aggiungi il badge:

```python
def render_with_badge(value, source):
    badge_map = {
        'questionnaire': '📋 Da Questionario',
        'research': '🔍 Ricerca Web',
        'estimate': '📊 Stima AI'
    }
    badge = badge_map.get(source, '')
    return f"{value} <span class='badge badge-{source}'>{badge}</span>"
```

**Note:**
- Mantieni retro-compatibilità: se `source` non esiste, non mostrare badge
- Aggiungi `'questionnaire'` a `SYSTEM_SOURCES` in `data_ingestor.py` se non presente
- Badge devono essere responsive: su mobile mostrare solo icona (📋 🔍 📊)

---

### **2. Fix Executive Report Sezioni Vuote ("Da definire")**

**Problema:** L'Executive Report mostra "Da definire" per alcuni obiettivi invece di contenuti reali.

**File da Analizzare:**
- `executive_report.py` (funzione che genera obiettivi)
- `agents.py` (verifica se gli agenti generano obiettivi vuoti)

**Steps:**

1. **Identifica dove viene generato "Da definire":**
   - Cerca nel codice: `grep -r "Da definire" executive_report.py`

2. **Verifica la fonte:**
   - Se viene da `agents.py`: gli agenti non stanno generando obiettivi completi
   - Se viene da `executive_report.py`: logica di fallback incompleta

3. **Fix Preferito:**
   - Se l'agente non genera obiettivi, usa una lista di default basata sull'area strategica
   - Esempio per area "Finanziaria":
     ```python
     default_objectives = {
         'Finanziaria': [
             'Raggiungere sostenibilità economica entro 2 anni',
             'Diversificare fonti di ricavo oltre il ticketing',
             'Ottimizzare il rapporto costi/ricavi della rosa'
         ],
         'Sportiva': [
             'Mantenere categoria/promozione',
             'Migliorare ranking giovanili regionali',
             'Implementare data-driven scouting'
         ]
         # ... altri
     }
     ```

4. **Aggiungi Logging:**
   ```python
   if not objectives or objectives == "Da definire":
       logger.warning(f"Empty objectives for area {area_name}, using defaults")
       objectives = default_objectives.get(area_name, ["Obiettivo in fase di definizione"])
   ```

**Output Atteso:**
- Executive Report senza mai mostrare "Da definire"
- Se dati mancano, usare obiettivi generici ma realistici per categoria/area

---

### **3. Tabella "Dati Club vs Benchmark" in Executive Report**

**Obiettivo:** Aggiungere una tabella comparativa che mostra i KPI del club vs la media della categoria.

**Posizione:** Nella sezione "Sintesi Finanziaria" o come nuova sezione dedicata.

**Dati da Comparare:**

| Metrica | Club | Benchmark Categoria | Gap | Trend |
|---------|------|---------------------|-----|-------|
| Budget Annuale | €500.000 | €450.000 | +11% 📈 | Sopra media |
| Tesserati | 450 | 380 | +18% 📈 | Eccellente |
| Ricavi Commerciali | €120.000 | €100.000 | +20% 📈 | Buono |
| Costo Rosa | €300.000 | €280.000 | +7% 📊 | In linea |
| Spettatori Medi | 350 | 420 | -17% 📉 | Da migliorare |

**Source dei Benchmark:**
- Usare i dati già presenti in `web_research_orchestrator.py` (ricerca FIGC, Transfermarkt)
- Se non disponibili, usare stime basate su categoria:
  ```python
  CATEGORY_BENCHMARKS = {
      'Serie D': {
          'budget': 450000,
          'tesserati': 380,
          'ricavi_commerciali': 100000,
          'spettatori_medi': 420
      },
      'Eccellenza': {
          'budget': 250000,
          'tesserati': 280,
          'ricavi_commerciali': 60000,
          'spettatori_medi': 250
      }
      # ... altri
  }
  ```

**Design Tabella (HTML/CSS):**

```html
<div class="benchmark-section">
    <h3>📊 Dati Club vs Benchmark Categoria</h3>
    <table class="benchmark-table">
        <thead>
            <tr>
                <th>Metrica</th>
                <th>Il Tuo Club</th>
                <th>Media {categoria}</th>
                <th>Gap</th>
                <th>Valutazione</th>
            </tr>
        </thead>
        <tbody>
            <tr class="positive">
                <td>Budget Annuale</td>
                <td>€500.000</td>
                <td>€450.000</td>
                <td class="gap-positive">+11%</td>
                <td>📈 Sopra media</td>
            </tr>
            <tr class="negative">
                <td>Spettatori Medi</td>
                <td>350</td>
                <td>420</td>
                <td class="gap-negative">-17%</td>
                <td>📉 Da migliorare</td>
            </tr>
        </tbody>
    </table>
    <p class="note">Benchmark basati su dati FIGC e Transfermarkt per categoria {categoria} stagione 2025/26</p>
</div>
```

**CSS:**
```css
.benchmark-table {
    width: 100%;
    border-collapse: collapse;
    margin: 20px 0;
    background: white;
    border-radius: 8px;
    overflow: hidden;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

.benchmark-table thead {
    background: linear-gradient(135deg, #6a0dad, #9b30ff);
    color: white;
}

.benchmark-table th, .benchmark-table td {
    padding: 12px 16px;
    text-align: left;
    border-bottom: 1px solid #eee;
}

.gap-positive {
    color: #38a169;
    font-weight: 600;
}

.gap-negative {
    color: #e53e3e;
    font-weight: 600;
}

.benchmark-table tr.positive {
    background: rgba(56, 161, 105, 0.05);
}

.benchmark-table tr.negative {
    background: rgba(229, 62, 62, 0.05);
}
```

**Logica Calcolo Gap:**
```python
def calculate_gap(club_value, benchmark_value):
    if benchmark_value == 0:
        return "N/A"

    gap_percent = ((club_value - benchmark_value) / benchmark_value) * 100

    if gap_percent > 10:
        trend = "📈 Sopra media"
        css_class = "positive"
    elif gap_percent < -10:
        trend = "📉 Da migliorare"
        css_class = "negative"
    else:
        trend = "📊 In linea"
        css_class = "neutral"

    return {
        'gap': f"{gap_percent:+.0f}%",
        'trend': trend,
        'css_class': css_class
    }
```

**Integrazione:**
- Aggiungi funzione `generate_benchmark_table()` in `executive_report.py`
- Inseriscila dopo la sezione "Sintesi Finanziaria" o come sezione a sé stante
- Passa i dati del club e la categoria per recuperare il benchmark

---

## 📁 File Structure Reference

```
rooting_future/
├── app.py                          # Flask main server
├── agents.py                       # AI Multi-Agente STW
├── data_ingestor.py               # Ingestion dati DOCX/JSON
├── structured_renderer.py         # Rendering testo con formattazione
├── export_html.py                 # Export Piano Strategico HTML
├── executive_report.py            # Export Executive Report
├── export_onepager.py            # Export One-Pager
├── export_pdf_server.py          # PDF generation server
├── web_research_orchestrator.py  # Web research engine
├── club_identity.py              # Club colors & branding
├── stw_matrix.py                 # STW Framework (21 MACRO)
└── templates/
    └── dashboard_simple.html      # Web UI
```

---

## ⚠️ Istruzioni di Lavoro

1. **Leggi SEMPRE i file prima di modificarli:**
   - Non fare assunzioni sulla struttura attuale
   - Verifica dipendenze tra moduli

2. **Mantieni Coerenza:**
   - Usa lo stesso stile di codice esistente (PEP8, docstrings, type hints)
   - Segui le convenzioni di naming (snake_case per funzioni/variabili)

3. **Testing:**
   - Dopo ogni modifica, testa con:
     ```bash
     python app.py
     ```
   - Verifica output HTML, Executive Report, One-Pager

4. **Version Control:**
   - Se fai commit, segui il formato:
     ```
     Add [feature]: brief description

     - Detail 1
     - Detail 2
     ```

5. **Documentazione:**
   - Aggiorna `ROOTING_FUTURE_CHANGELOG.md` con i tuoi cambiamenti
   - Formato:
     ```markdown
     ## 🟢 [v5.4.6] - 2026-01-12
     ### [Nome Feature]
     * Descrizione cambiamento
     * File modificati: `file1.py`, `file2.py`
     ```

---

---

### **4. Fix Obiettivi MICRO Duplicati (Executive Report)** 🔥 CRITICO

**Problema Rilevato:** Negli output attuali, gli obiettivi MICRO duplicano semplicemente i MACRO invece di essere specifici e actionable.

**Esempio Problema Attuale:**
```
Area Sportiva:

MACRO:
- CREAZIONE E SVILUPPO IDENTITÀ TECNICA

MICRO:
- MACRO 1: CREAZIONE E SVILUPPO IDENTITÀ TECNICA  ← DUPLICATO!
- Situazione attuale  ← Generico, non un obiettivo
- Azione proposta     ← Generico, non un obiettivo
```

**Cosa Deve Essere:**
```
MACRO:
- CREAZIONE E SVILUPPO IDENTITÀ TECNICA

MICRO (obiettivi specifici e actionable):
- Implementare 4-3-3 come modulo base per tutte le categorie
- Assumere Match Analyst certificato UEFA entro 6 mesi
- Sviluppare database centralizzato per tracking performance giocatori
- Standardizzare protocollo di allenamento settimanale per settore giovanile
```

**File da Modificare:**
- `executive_report.py` - Funzione che genera gli obiettivi MICRO
- `agents.py` - Verifica che gli agenti AI producano MICRO reali

**Soluzione:**

1. **Verifica output agenti AI:** Gli agenti devono generare obiettivi MICRO granulari, non duplicare i MACRO.

2. **Implementa fallback intelligente:** Se gli agenti non producono MICRO validi, usa template basati sull'area:

```python
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
    # Aggiungi altri MACRO se necessario
}

def get_micro_objectives(macro_name, agent_output):
    """
    Estrae obiettivi MICRO dall'output dell'agente.
    Se non validi, usa fallback intelligenti.
    """
    # Tenta di estrarre MICRO dall'output agente
    if agent_output and len(agent_output) > 0:
        # Verifica che non siano duplicati dei MACRO
        if not is_duplicate_of_macro(agent_output, macro_name):
            return agent_output

    # Fallback: usa template predefiniti
    logger.warning(f"Using fallback MICRO objectives for {macro_name}")
    return MICRO_OBJECTIVES_FALLBACKS.get(macro_name, [
        f"Definire piano operativo dettagliato per {macro_name}",
        f"Assegnare responsabile e budget per {macro_name}",
        f"Stabilire KPI misurabili per {macro_name}"
    ])

def is_duplicate_of_macro(objectives, macro_name):
    """Verifica se gli obiettivi MICRO sono solo duplicati del MACRO"""
    for obj in objectives:
        if macro_name.lower() in obj.lower() and len(obj) < len(macro_name) + 20:
            return True
    return False
```

3. **Validazione:** Assicurati che ogni MICRO sia:
   - Specifico (non generico)
   - Actionable (verbo d'azione chiaro)
   - Misurabile (quando possibile)
   - Non duplicato dal MACRO

**Impatto:** Gli obiettivi MICRO diventano operativi e realistici, aumentando drasticamente il valore del documento.

---

### **5. Aggiungere Motivazioni alle Top 5 Priorities (One-Pager)** 🔥 CRITICO

**Problema Rilevato:** Il One-Pager mostra le Top 5 priorità ma senza spiegare il "perché" (motivazione strategica).

**Attuale:**
```html
1. SPORTIVI MACRO 1: Miglioramento Competitivo Prima Squadra
   [nessuna motivazione visibile]

2. STRUTTURALI MACRO 1: Sviluppo Organizzativo e Infrastrutturale
   [nessuna motivazione visibile]
```

**Nota:** Questa feature era prevista nel CHANGELOG v5.4.5:
> "Strategic Priority Justification: The One-Pager now includes a brief 'Why' (Motivation)"

**File da Modificare:**
- `export_onepager.py` - Funzione che genera la sezione "Top 5 Priorities"

**Soluzione:**

1. **Aggiungi campo "why" nella struttura dati:**

```python
# In export_onepager.py, dove vengono generate le priorità

priorities = [
    {
        'rank': 1,
        'title': 'SPORTIVI MACRO 1: Miglioramento Competitivo Prima Squadra',
        'category': 'SPORTIVI',
        'why': 'Necessario per consolidare posizione playoff e attrarre sponsor con performance sportive migliori. Impatto diretto su ricavi commerciali.'
    },
    {
        'rank': 2,
        'title': 'STRUTTURALI MACRO 1: Sviluppo Organizzativo e Infrastrutturale',
        'category': 'STRUTTURALI',
        'why': 'Investimento fondamentale per sostenere crescita settore giovanile ed efficienza operativa di lungo periodo.'
    },
    {
        'rank': 3,
        'title': 'MARKETING MACRO 1: Sviluppo Area Comunicazione',
        'category': 'MARKETING',
        'why': 'Incrementare visibilità locale e engagement tifosi è prerequisito per crescita ricavi commerciali del 20%.'
    },
    # ... altri
]
```

2. **Aggiorna template HTML:**

Il CSS per `.priority-reason` **esiste già** nel template (line ~120):

```css
.priority-reason {
    font-size: 8pt;
    line-height: 1.3;
    color: var(--text-muted);
    font-style: italic;
}
```

Quindi basta popolarlo:

```html
<div class="priority-item">
    <span class="priority-num">1</span>
    <div style="display: flex; flex-direction: column;">
        <span class="priority-text">{title}</span>
        <span class="priority-reason">{why}</span>  <!-- Aggiungi questa linea! -->
    </div>
</div>
```

3. **Generazione Automatica "Why":**

Se il "why" non è fornito, genera automaticamente basandoti sulla categoria:

```python
DEFAULT_MOTIVATIONS = {
    'SPORTIVI': 'Performance sportiva è driver principale per crescita club e attenzione mediatica.',
    'STRUTTURALI': 'Fondamenta organizzative robuste garantiscono sostenibilità di lungo termine.',
    'MARKETING': 'Visibilità e brand strength sono prerequisiti per crescita ricavi commerciali.',
    'SOCIALI': 'Impatto sociale positivo rafforza legame con territorio e attrae sponsor ESG-oriented.',
    'FINANZIARI': 'Sostenibilità economica è condizione necessaria per ogni strategia di crescita.'
}

def get_priority_motivation(category, title):
    """Genera motivazione automatica se non fornita"""
    # Cerca motivazione specifica nel title o usa default categoria
    return DEFAULT_MOTIVATIONS.get(category, 'Priorità strategica identificata dal board.')
```

**Impatto:** Le priorità diventano strategicamente giustificate, non sembrano più arbitrarie.

---

### **6. Fix ":" Iniziali nella Sintesi Strategica (Executive Report)** 🔥 CRITICO

**Problema Rilevato:** Nel Executive Report, sezione "Sintesi Strategica Triennale", i testi iniziano con ":" lasciando un doppio punto visibile.

**Esempio:**
```html
<h4>Area Sportiva</h4>
<div class="sintesi-text">: La Direzione strategica prevede...</div>
                         ↑
                    Due punti all'inizio!
```

**File da Modificare:**
- `executive_report.py` - Funzione che genera la Sintesi Strategica

**Soluzione Rapida:**

**Opzione A - Rimuovi i ":"**
```python
# Cerca questa linea in executive_report.py (probabilmente intorno a line 478-500)
sintesi_text = f": {area_summary}"

# Sostituisci con:
sintesi_text = area_summary
```

**Opzione B - Aggiungi Label "Focus:" o "Strategia:"**
```python
# Se vuoi mantenere i ":" con un label
sintesi_text = f"<strong>Focus:</strong> {area_summary}"
# Oppure
sintesi_text = f"<strong>Strategia:</strong> {area_summary}"
```

**Raccomandazione:** Usa Opzione A (rimozione) per mantenere design pulito e minimale.

**Impatto:** Fix cosmetico ma importante per professionalità del documento.

---

### **7. Badge Inline nei Contenuti Testuali** 🟡 MEDIA PRIORITÀ

**Problema Rilevato:** I badge fonte dati (📋 VERIFICATO, 🔍 DEDOTTO, 📊 STIMATO) esistono nel CSS ma non vengono applicati inline nei contenuti testuali.

**Attuale:**
```html
<div class="sintesi-text">...finalizzato al miglioramento delle performance
e al raggiungimento di obiettivi competitivi ambiziosi `(fonte: stima AI)`.</div>
```

**Dovrebbe Essere:**
```html
<div class="sintesi-text">...finalizzato al miglioramento delle performance
e al raggiungimento di obiettivi competitivi ambiziosi
<span class="badge badge-estimate">📊 STIMATO</span></div>
```

**File da Modificare:**
- `structured_renderer.py` - Rendering testo con badge inline
- `executive_report.py` - Applicare badge nei testi della sintesi
- `export_html.py` - Applicare badge nel Piano Strategico

**Soluzione:**

1. **Crea funzione helper in `structured_renderer.py`:**

```python
def add_source_badge_inline(text, source):
    """
    Aggiunge badge inline al testo sostituendo note testuali.

    Args:
        text: Testo da processare
        source: 'verified', 'research', 'estimate'

    Returns:
        Testo con badge HTML inline
    """
    badge_html = {
        'verified': '<span class="badge badge-questionnaire">📋 VERIFICATO</span>',
        'research': '<span class="badge badge-research">🔍 DEDOTTO</span>',
        'estimate': '<span class="badge badge-estimate">📊 STIMATO</span>'
    }

    # Rimuovi note testuali tipo "(fonte: stima AI)" o "`(fonte: stima AI)`"
    import re
    text = re.sub(r'`?\(fonte:.*?\)`?', '', text)

    # Aggiungi badge inline
    badge = badge_html.get(source, '')
    return f"{text.strip()} {badge}"
```

2. **Applica nei template:**

```python
# In executive_report.py, dove generi la sintesi
for area in areas:
    area_text = add_source_badge_inline(area['summary'], area.get('source', 'estimate'))
    sintesi_items.append(f'<div class="sintesi-text">{area_text}</div>')
```

**Impatto:** Massima trasparenza sulla fonte di ogni affermazione, senza inquinare il testo con note testuali.

---

### **8. Verifica e Fix PDF Piano Strategico** 🟡 MEDIA PRIORITÀ

**Problema:** Non è stato possibile analizzare il contenuto del PDF per verificare:
- Presenza sezione "Metodologia Rooting Future"
- Timing badge visibile
- STW Dashboard rendering
- Font premium (Montserrat/Inter)
- Texture cubes sulla cover

**File da Verificare:**
- `export_pdf_server.py` - Generatore PDF principale
- Output: `AC_Riccione_1926_PianoStrategico_20260111_215133.pdf`

**Azioni:**

1. **Apri manualmente il PDF** generato e verifica:
   - [ ] Cover page con gradiente club colors + texture
   - [ ] Font Montserrat per titoli, Inter per body text
   - [ ] Sezione "Metodologia Rooting Future" presente dopo STW Dashboard
   - [ ] Timing badge nel footer o header: "⏱️ Generato in Xm Ys"
   - [ ] STW Dashboard con barre colorate per categoria
   - [ ] Tabelle e layout responsive e ben formattati

2. **Se elementi mancano:** Controlla che `export_pdf_server.py` includa tutte le feature v5.4.5:

```python
# Verifica presenza di queste chiamate in export_pdf_server.py

# 1. Metodologia RF
methodology_html = generate_rooting_future_methodology_html(metadata, primary_color)

# 2. Timing badge
timing_badge = _format_timing_badge(metadata)

# 3. STW Dashboard
stw_dashboard_html = generate_stw_dashboard(...)

# 4. Font loading
fonts = """
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600&family=Montserrat:wght@700;800&display=swap" rel="stylesheet">
"""

# 5. Texture background
cover_style = """
background: var(--brand-gradient);
background-image: url('https://www.transparenttextures.com/patterns/cubes.png');
"""
```

3. **Testing:** Dopo ogni modifica a `export_pdf_server.py`, rigenera il PDF e verifica visivamente.

**Impatto:** Il PDF è il documento più "ufficiale" per i club, deve essere impeccabile.

---

## 🎯 Priorità Task (Aggiornata)

### **🔥 ALTA PRIORITÀ (FIX IMMEDIATI)**
1. **Fix Obiettivi MICRO Duplicati** - Blocca qualità contenuto (Task 4)
2. **Aggiungere Motivazioni Top 5 Priorities** - Feature prevista v5.4.5 non implementata (Task 5)
3. **Fix ":" Iniziali Sintesi Strategica** - Fix cosmetico rapido (Task 6)

### **🟡 MEDIA PRIORITÀ**
4. **Badge Inline nei Contenuti** - Migliora trasparenza (Task 7)
5. **Verifica PDF Piano Strategico** - Assicura qualità documento ufficiale (Task 8)
6. **Tabella Benchmark** - Nice-to-have, possibile già parzialmente presente (Task 3)

### **🟢 BASSA PRIORITÀ (già presenti nei task originali)**
7. **Badge "Da Questionario" Sistema Completo** - Già parzialmente implementato (Task 1)
8. **Fix "Da definire" Fallback** - Probabilmente già risolto, verificare (Task 2)

---

## 📊 Riepilogo Analisi Output v5.4.5

Prima di iniziare, ecco un'analisi degli output attuali (AC Riccione 1926, generati il 2026-01-11):

### ✅ Cosa Funziona Benissimo:
- **Design System Unificato:** Brand gradient dinamico (Club colors → Purple), texture cubes, font premium
- **Executive Report HTML:** Cover professionale, KPI cards, aree clickable con modal expansion
- **One-Pager:** Layout A4 compatto, STW coverage bars, credibilità badge ben visualizzato
- **Badge Sistema:** CSS classes pronte per `📋 VERIFICATO`, `🔍 DEDOTTO`, `📊 STIMATO`
- **Benchmark Comparison:** Già presente in Executive Report (sezione "Confronto vs Benchmark")

### ❌ Problemi Critici Trovati:
1. **Obiettivi MICRO duplicano i MACRO** (invece di essere specifici)
2. **Top 5 Priorities senza motivazioni** (feature prevista v5.4.5 non implementata)
3. **":" iniziali nella Sintesi Strategica** (errore di formattazione)
4. **Badge non applicati inline nei contenuti** (solo come note testuali)
5. **PDF non verificabile programmaticamente** (serve controllo manuale)

**I task 4, 5, 6 sopra sono stati creati specificamente per risolvere questi problemi.**

---

## 🚀 Output Atteso

Alla fine del lavoro, fornisci:

1. **Summary delle modifiche:**
   - File modificati (con line numbers)
   - Nuove funzioni aggiunte
   - Breaking changes (se presenti)

2. **Test Results:**
   - Screenshot dell'output (se possibile)
   - Conferma che tutti i 3 formati (HTML, Executive, One-Pager) funzionano

3. **Updated Changelog:**
   - Entry per v5.4.6 in `ROOTING_FUTURE_CHANGELOG.md`

---

## 📞 Domande/Dubbi

Se qualcosa non è chiaro o trovi problemi:
- Documenta il problema trovato
- Proponi soluzioni alternative
- Non bloccarti: se una feature è complessa, implementa una versione semplificata funzionante

---

**Buon lavoro! 🚀**
