# Piano Miglioramenti Output Rooting Future
## Data: 10 Gennaio 2026

---

## 🎯 Obiettivo

Trasformare l'output da "accozzaglia AI generica" a "Piano strategico professionale Rooting Future" con:
- Riferimenti chiari ai questionari compilati
- Marchio di fabbrica metodologia RF
- Presentazione visuale superiore
- Dati concreti e utili

---

## 📋 Problemi Attuali Identificati

### 1. **Executive Report Vuoto**
```html
<ul class="obj-list"><li>Da definire</li></ul>
```
**Problema**: Tutte le sezioni dicono "Da definire" invece di mostrare obiettivi reali

**Causa**: `_extract_objectives_summary()` non trova obiettivi nel contenuto

**Fix**: Migliorare estrazione o mostrare KPI alternativi

---

### 2. **Zero Riferimenti ai Questionari**
**Problema**: Nessuna menzione di:
- Questionari compilati dal club
- Dati forniti dalla società
- Input ricevuti

**Impatto**: Sembra tutto inventato dall'AI, non personalizzato

**Fix Necessario**:
- Badge "📋 Da Questionario" accanto ai dati forniti
- Sezione "Input del Club" prominente
- Riferimenti specifici: "Come indicato nel questionario..."

---

### 3. **Manca Marchio "Rooting Future Methodology"**
**Problema**: Output generico, potrebbe essere di qualsiasi tool AI

**Fix Necessario**:
- Sezione "Metodologia Rooting Future" in evidenza
- Logo/Brand identity visibile
- Spiegazione del processo unico RF:
  ```
  1. Analisi Questionari Club
  2. Benchmark FIGC + Transfermarkt
  3. Web Research territoriale
  4. AI Agents STW-aligned
  5. Validazione scientifica
  ```

---

### 4. **Nessun Indicatore Tempi**
**Problema**: Utente non sa quanto ci ha messo il sistema

**Fix Necessario**:
- Badge "⏱️ Generato in 2m 34s"
- Breakdown tempi per fase:
  ```
  • Analisi Questionari: 12s
  • Web Research: 45s
  • AI Generation: 1m 24s
  • Post-processing: 13s
  ```

---

### 5. **Piano Strategico = "Muro di Testo"**
**Problema Attuale**:
```
Lunghi paragrafi senza pause visive
Nessun TOC cliccabile
Nessun highlight/callout
Sezioni non collapsibili
```

**Fix Necessario**:
- **Table of Contents interattiva** (sticky sidebar)
- **Callout boxes** per punti chiave
- **Progress indicators** (es. "Completezza: 85%")
- **Visual separators** tra sezioni
- **Collapsible sections** per lettura progressiva
- **Summary cards** all'inizio di ogni sezione

---

### 6. **Executive Report Scarno**
**Problema**:
- Nessun KPI reale
- Grafici ma senza contesto
- Obiettivi "Da definire"

**Fix Necessario**:
- Mostrare KPI dal questionario (budget, tesserati, etc.)
- Tabella "Dati Club vs Benchmark"
- Estratto obiettivi prioritari reali
- Citazioni dirette dal questionario

---

## 🛠️ Implementazione

### FASE 1: Tracking Tempi di Generazione

**File da modificare**: `app.py`

```python
import time

# All'inizio della generazione
start_time = time.time()
timings = {}

# Durante le fasi
timings['questionnaire_parsing'] = time_questionnaire()
timings['web_research'] = time_research()
timings['ai_generation'] = time_agents()
timings['post_processing'] = time_export()

total_time = time.time() - start_time

# Passa a metadata
metadata['generation_timings'] = timings
metadata['total_generation_time'] = total_time
```

**Output nei template**:
```html
<div class="generation-badge">
    ⏱️ Generato in <strong>2m 34s</strong>
    <span class="tooltip">Dettagli tempi...</span>
</div>
```

---

### FASE 2: Sezione "Metodologia Rooting Future"

**File da modificare**:
- `executive_report.py`
- `export_html.py`
- `export_onepager.py`

**Contenuto Nuovo**:
```html
<div class="rf-methodology-section">
    <h2>🏆 Metodologia Rooting Future</h2>

    <div class="methodology-badge">
        <img src="logo_rf.png" alt="Rooting Future" />
        <span>Strategic Planning Framework</span>
    </div>

    <div class="methodology-steps">
        <div class="step">
            <div class="step-number">1</div>
            <div class="step-content">
                <h4>📋 Analisi Questionari Club</h4>
                <p><strong>Compilati da:</strong> {club_name}</p>
                <p><strong>Dati raccolti:</strong> {questionari_count} questionari, {data_points} punti dati</p>
                <ul class="data-list">
                    <li>✓ Organigramma (12 campi compilati)</li>
                    <li>✓ Budget e Finanze (8 valori forniti)</li>
                    <li>✓ Strutture e Impianti (5 risposte)</li>
                </ul>
            </div>
        </div>

        <div class="step">
            <div class="step-number">2</div>
            <div class="step-content">
                <h4>🔍 Web Research & Benchmark</h4>
                <p>Fonti verificate: FIGC, Transfermarkt, Visura Camerale</p>
            </div>
        </div>

        <div class="step">
            <div class="step-number">3</div>
            <div class="step-content">
                <h4>🤖 AI Multi-Agente STW-Aligned</h4>
                <p>6 agenti specializzati + validazione scientifica</p>
            </div>
        </div>

        <div class="step">
            <div class="step-number">4</div>
            <div class="step-content">
                <h4>📊 Output Validato e Verificato</h4>
                <p>Credibilità: {credibility_score}%</p>
            </div>
        </div>
    </div>
</div>
```

---

### FASE 3: Badge "Da Questionario"

**File da modificare**: `structured_renderer.py`, `export_html.py`

**Logica**:
```python
def add_source_badge(data_point):
    if data_point.source == "questionnaire":
        return '<span class="badge questionnaire">📋 Da Questionario</span>'
    elif data_point.source == "web_research":
        return '<span class="badge research">🔍 Ricerca Web</span>'
    elif data_point.data_type == "ESTIMATE":
        return '<span class="badge estimate">📊 Stima AI</span>'
```

**Output**:
```html
<div class="data-card">
    <h4>
        Tesserati Settore Giovanile
        <span class="badge questionnaire">📋 Da Questionario</span>
    </h4>
    <div class="value">247</div>
    <p class="source-note">Fonte: Compilato dal club il 08/01/2026</p>
</div>
```

---

### FASE 4: Migliorare Layout Piano Strategico

**File da modificare**: `export_html.py`

**Aggiunte**:

1. **Table of Contents Sticky**:
```html
<aside class="toc-sidebar">
    <h3>Indice</h3>
    <nav class="toc-nav">
        <a href="#exec" class="toc-link active">Executive Summary</a>
        <a href="#sportivi" class="toc-link">⚽ Sportivi <span class="progress">75%</span></a>
        <a href="#strutturali" class="toc-link">🏗️ Strutturali <span class="progress">60%</span></a>
        ...
    </nav>
</aside>
```

2. **Callout Boxes**:
```html
<div class="callout callout-info">
    <div class="callout-icon">💡</div>
    <div class="callout-content">
        <strong>Insight Chiave:</strong> Il club ha fornito organigramma completo con 12 ruoli definiti...
    </div>
</div>
```

3. **Section Headers con Summary**:
```html
<section id="sportivi" class="strategic-section">
    <div class="section-header">
        <h2>⚽ Obiettivi Sportivi</h2>
        <div class="section-meta">
            <span class="coverage-badge">Copertura STW: 75%</span>
            <span class="data-badge">8 MACRO, 32 MICRO</span>
        </div>
    </div>

    <div class="section-summary">
        <strong>In sintesi:</strong> Consolidamento area tecnica con focus su settore giovanile...
    </div>

    <!-- Contenuto sezione -->
</section>
```

4. **Collapsible Subsections**:
```html
<div class="collapsible-section">
    <button class="collapse-toggle">
        <span class="toggle-icon">▼</span>
        <strong>MACRO 1: Identità Tecnica</strong>
        <span class="mini-badge">4 azioni</span>
    </button>
    <div class="collapse-content">
        <!-- Contenuto MICRO -->
    </div>
</div>
```

---

### FASE 5: Arricchire Executive Report

**File da modificare**: `executive_report.py`

**Aggiunte**:

1. **Tabella Dati Club vs Benchmark**:
```html
<table class="comparison-table">
    <thead>
        <tr>
            <th>Metrica</th>
            <th>Club</th>
            <th>Benchmark {category}</th>
            <th>Gap</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td>Tesserati SG <span class="badge questionnaire">📋</span></td>
            <td>247</td>
            <td>180</td>
            <td class="positive">+37%</td>
        </tr>
        <tr>
            <td>Budget Annuo <span class="badge estimate">📊</span></td>
            <td>€586K</td>
            <td>€4.5M</td>
            <td class="negative">-87%</td>
        </tr>
    </tbody>
</table>
```

2. **Input Club Section**:
```html
<div class="club-input-section">
    <h3>📋 Dati Forniti dal Club</h3>
    <div class="input-grid">
        <div class="input-card">
            <div class="input-label">Questionari Compilati</div>
            <div class="input-value">4/4</div>
        </div>
        <div class="input-card">
            <div class="input-label">Dati Verificati</div>
            <div class="input-value">18</div>
        </div>
        <div class="input-card">
            <div class="input-label">Documenti Caricati</div>
            <div class="input-value">2 (Statuto, Organigramma)</div>
        </div>
    </div>
</div>
```

3. **Quote dal Questionario**:
```html
<blockquote class="questionnaire-quote">
    <p>"L'obiettivo principale è consolidare il settore giovanile raggiungendo 300 tesserati entro 2 anni"</p>
    <cite>— Da questionario Area Sportiva, compilato 08/01/2026</cite>
</blockquote>
```

---

## 📊 Tracking Questionari nel Sistema

**File da modificare**: `data_ingestor.py`, `app.py`

Quando il sistema processa un questionario DOCX:

```python
questionnaire_data = {
    'filename': 'Questionario_Sportivo.docx',
    'upload_date': '2026-01-08',
    'parsed_fields': {
        'tesserati_sg': 247,
        'allenatori_qualificati': 12,
        'obiettivo_tesserati_3y': 300,
        # etc.
    },
    'completion_rate': 0.85,  # 85% campi compilati
    'verified_data_points': 18
}

metadata['questionnaires'] = [questionnaire_data, ...]
metadata['total_questionnaires'] = 4
metadata['questionnaire_completion'] = 0.90
```

---

## 🎨 Visual Identity "Rooting Future"

### Logo/Brand Header
```html
<div class="rf-brand-header">
    <div class="rf-logo">
        <svg><!-- Logo RF --></svg>
    </div>
    <div class="rf-tagline">
        <h1>Strategic Planning Framework</h1>
        <p>Metodologia Data-Driven per il Calcio Italiano</p>
    </div>
</div>
```

### Color Scheme
```css
:root {
    --rf-primary: #1a365d;      /* Blu istituzionale */
    --rf-secondary: #2E7D32;    /* Verde calcio */
    --rf-accent: #F57C00;       /* Arancione energia */
    --rf-questionnaire: #7B1FA2; /* Viola per badge questionario */
}
```

### Badge System
```css
.badge {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 4px 8px;
    border-radius: 12px;
    font-size: 0.75rem;
    font-weight: 600;
}

.badge.questionnaire {
    background: linear-gradient(135deg, #7B1FA2, #9C27B0);
    color: white;
}

.badge.research {
    background: linear-gradient(135deg, #1565C0, #1976D2);
    color: white;
}

.badge.estimate {
    background: linear-gradient(135deg, #F57C00, #FB8C00);
    color: white;
}
```

---

## ⏱️ Esempio Output Tempi

```
⏱️ Piano generato in 2m 34s

Breakdown:
├─ 📋 Parsing Questionari: 12s
├─ 🔍 Web Research: 45s
├─ 🤖 AI Multi-Agente: 1m 24s
│   ├─ Sportivi: 18s
│   ├─ Strutturali: 14s
│   ├─ Marketing: 16s
│   ├─ Sociali: 15s
│   ├─ Governance: 12s
│   └─ Coordinator: 9s
└─ 📄 Export & Formatting: 13s
```

---

## 🚀 Priorità di Implementazione

### ALTA PRIORITÀ (Fare Subito)
1. ✅ Badge "Da Questionario" per dati forniti
2. ✅ Sezione "Metodologia Rooting Future"
3. ✅ Tracking tempi di generazione
4. ✅ Tabella "Dati Club vs Benchmark"

### MEDIA PRIORITÀ (Entro questa settimana)
5. Migliorare layout piano (TOC, callouts)
6. Collapsible sections
7. Input Club section in Executive

### BASSA PRIORITÀ (Nice to have)
8. Quote dal questionario
9. Logo/Brand identity grafica
10. Analytics dashboard

---

## 📝 Note Implementative

### Come Tracciare Dati da Questionario

Quando `data_ingestor.py` processa un DOCX:
```python
for field, value in parsed_data.items():
    data_point = DataPoint(
        id=f"q_{field}",
        label=field_labels[field],
        value=value,
        data_type=DataType.VERIFIED,
        source=Source(
            type="questionnaire",
            name=f"Questionario {section}",
            date="2026-01-08",
            url=None
        ),
        confidence=1.0,
        confidence_level=ConfidenceLevel.HIGH
    )
```

Poi nei template:
```python
if data_point.source.type == "questionnaire":
    badge = '<span class="badge questionnaire">📋 Da Questionario</span>'
```

---

**Fine Piano Miglioramenti**

*Documento preparato per implementazione graduale*
*Priorità: Alta per badge + metodologia + tempi*
