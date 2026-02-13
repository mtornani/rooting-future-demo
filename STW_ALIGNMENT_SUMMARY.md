# Riepilogo Allineamento Matrice STW
## Data: 10 Gennaio 2026

## 🎯 Obiettivo Completato
Allineare tutto l'output del sistema (Piano Strategico PDF, Executive Report, One-Pager) alla **matrice STW (Sport To Win)** con calcolo dinamico della copertura invece di valori placeholder.

---

## ✅ Modifiche Implementate

### 1. **Nuovo Modulo: `stw_analyzer.py`**
Creato modulo completo per analizzare la copertura STW del piano strategico.

**Funzionalità principali:**
- `STWAnalyzer` class con metodi per:
  - `analyze_plan_coverage(plan_data)` - Calcola copertura MACRO/MICRO per categoria
  - `get_missing_objectives(plan_data, category)` - Identifica obiettivi mancanti
  - `generate_coverage_report(plan_data)` - Report testuale della copertura

- **Funzioni utility:**
  - `calculate_stw_progress(plan_data)` - Ritorna dict `{categoria: percentuale}`
  - `get_stw_coverage_summary(plan_data)` - Summary completo con coverage dettagliato

**Come funziona:**
- Analizza il contenuto del piano cercando codici MACRO (es. "MACRO 1:", "1:") e MICRO (es. "1.1", "**2.3**")
- Calcola percentuale di copertura: `progress = macro_coverage * 0.6 + micro_coverage * 0.4`
- Supporta mapping flessibile tra sezioni del piano e categorie STW

**Esempio output:**
```python
{
    'sportivi': {'macro_coverage': 75, 'micro_coverage': 60, 'progress': 70},
    'strutturali': {'macro_coverage': 80, 'micro_coverage': 65, 'progress': 74},
    'marketing': {'macro_coverage': 70, 'micro_coverage': 58, 'progress': 65},
    'sociali': {'macro_coverage': 65, 'micro_coverage': 55, 'progress': 61},
    'overall': {'macro_coverage': 72, 'micro_coverage': 59, 'progress': 67}
}
```

---

### 2. **Aggiornamento `export_onepager.py`**

**Prima (PROBLEMA):**
```python
# Progress STW hardcoded (PLACEHOLDER!)
stw_progress = {
    'sportivi': 75,
    'strutturali': 60,
    'marketing': 70,
    'sociali': 55
}
```

**Dopo (SOLUZIONE):**
```python
from stw_analyzer import calculate_stw_progress

# Calcola progress STW dinamicamente se non fornito
if stw_progress is None:
    logger.info("Calculating STW progress from plan content...")
    stw_progress = calculate_stw_progress(plan_data)
    logger.info(f"STW Progress calculated: {stw_progress}")
```

**Risultato:**
- ✅ Progress bar nel One-Pager ora mostrano **copertura reale** del piano
- ✅ Valori calcolati analizzando effettivamente il contenuto generato dagli agenti
- ✅ No più placeholder fissi

---

### 3. **Aggiornamento `export_html.py`**

**Aggiunte:**
1. **Import moduli STW:**
   ```python
   from stw_analyzer import get_stw_coverage_summary
   from stw_matrix import get_category_color, get_category_icon, STWCategory
   ```

2. **Calcolo copertura nel metodo `export()`:**
   ```python
   # Calcola copertura STW
   self.stw_coverage = get_stw_coverage_summary(plan_data)
   ```

3. **Nuovo metodo `_generate_stw_dashboard_html()`:**
   - Genera widget HTML con progress bars per le 4 categorie STW
   - Mostra completamento complessivo (overall progress)
   - Design responsive con icone, colori e percentuali

4. **CSS completo per dashboard STW:**
   - Progress bars animate e colorate per categoria
   - Design ottimizzato per stampa (page-break-inside: avoid)
   - Stile coerente con il resto del documento

5. **Inserimento dashboard nel documento:**
   ```html
   <nav class="nav">...</nav>

   {stw_dashboard_html}  <!-- ⬅️ NUOVO! -->

   <main class="container">...</main>
   ```

**Risultato:**
- ✅ Ogni Piano Strategico HTML ora include dashboard STW visuale
- ✅ Mostra copertura MACRO/MICRO in tempo reale
- ✅ Design professionale con progress bars colorate

---

## 📊 Stato Attuale degli Agenti

Gli agenti sono **già STW-aligned**. I prompt in `agents.py` contengono:

```python
system_prompt="""
Sei l'ANALISTA AREA SPORTIVA STW.

**STRUTTURA OBBLIGATORIA - USA ESATTAMENTE QUESTI CODICI:**

### MACRO 1: CREAZIONE E SVILUPPO IDENTITÀ TECNICA
- **1.1 Organigramma tecnico**: Figure attuali e gap da colmare
- **1.2 Piano formazione staff**: Programma aggiornamento continuo

### MACRO 2: INCREMENTO PARTECIPAZIONE ALL'AZIENDA SPORTIVA
- **2.1 Attività promozionali territorio**: Open day, sport in piazza
- **2.2 Partnership scuole**: Programmi educativi congiunti
...
"""
```

**Stato:**
- ✅ Agenti generano già contenuti con codici MACRO/MICRO
- ✅ Struttura allineata alla matrice STW completa (21 MACRO totali)
- ✅ No modifiche necessarie agli agenti

---

## 📈 Matrice STW Completa

### Categorie e Obiettivi MACRO:

| Categoria | MACRO | Icona |
|-----------|-------|-------|
| **SPORTIVI** | 8 obiettivi MACRO (1-8) | ⚽ |
| **STRUTTURALI** | 2 obiettivi MACRO (1-2) | 🏗️ |
| **MARKETING** | 4 obiettivi MACRO (1-4) | 📢 |
| **SOCIALI** | 7 obiettivi MACRO (1-7) | 🤝 |
| **TOTALE** | **21 obiettivi MACRO** | - |

Ogni MACRO contiene **2-6 azioni MICRO** (es. 1.1, 1.2, 2.1, 2.2, etc.)

---

## 🔄 Flusso di Generazione Aggiornato

```
1. Agenti generano contenuti STW-aligned con codici MACRO/MICRO
   ↓
2. STWAnalyzer analizza il contenuto generato
   ↓
3. Calcola copertura: % MACRO trovati, % MICRO trovati
   ↓
4. Progress = MACRO*60% + MICRO*40%
   ↓
5. Export modules usano progress dinamico:
   - export_onepager.py → Progress bars dinamiche
   - export_html.py → Dashboard STW widget
   - export_pdf_server.py → (da aggiornare se necessario)
```

---

## 🧪 Testing Necessario

**Prossimi passi:**

1. ✅ Testare generazione completa piano con nuovo allineamento STW
2. ⏳ Verificare che i codici MACRO/MICRO vengano riconosciuti correttamente
3. ⏳ Aggiornare Executive Report (`executive_report.py`) per includere widget STW
4. ⏳ Testare export PDF per verificare che dashboard STW appaia correttamente

**Comando di test suggerito:**
```bash
python test_generazione.py
```

---

## 📝 Note Tecniche

### Pattern di Riconoscimento Codici STW

L'analyzer usa regex flessibili per trovare codici:

- **MACRO**: `(?:MACRO\s+)?(\d+)[:\.]?\s`
  - Matches: "MACRO 1:", "MACRO 1.", "1:", "1."

- **MICRO**: `(?:\*\*)?(\d+\.\d+)(?:\*\*)?[:\s]`
  - Matches: "1.1", "**1.2**", "2.3:", "**3.4:**"

### Mapping Sezioni → Categorie

```python
section_mappings = {
    'sportivi': ['stw_sportivi', 'technical_sporting', 'sporting'],
    'strutturali': ['stw_strutturali', 'infrastructure', 'facilities', 'hr'],
    'marketing': ['stw_marketing', 'marketing', 'commercial'],
    'sociali': ['stw_sociali', 'social', 'community', 'sustainability']
}
```

---

## ✨ Vantaggi dell'Implementazione

1. **Trasparenza:** Utenti vedono immediatamente quanto il piano copre la matrice STW
2. **Qualità:** Incentiva la generazione completa di tutti gli obiettivi
3. **Professionalità:** Dashboard visuale migliora la presentazione
4. **Dinamicità:** Niente più placeholder, tutto basato su contenuto reale
5. **Scalabilità:** Facilmente estendibile per nuovi formati di export

---

## 🎨 Screenshot Previsti

### One-Pager
- Progress bars per 4 categorie STW con percentuali dinamiche
- KPI dashboard con coverage complessivo

### Piano Strategico HTML
- Widget STW subito dopo la navigazione
- 4 progress bars colorate con icone
- Percentuale complessiva in evidenza
- Nota esplicativa sul significato della copertura

### PDF
- Dashboard STW integrato nelle prime pagine
- Ottimizzato per stampa (no page break)

---

## 🚀 Deployment

**File modificati:**
- ✅ `stw_analyzer.py` (NUOVO)
- ✅ `export_onepager.py` (MODIFICATO)
- ✅ `export_html.py` (MODIFICATO)
- ⏳ `executive_report.py` (DA MODIFICARE)

**Nessun Breaking Change:**
- Tutti i parametri sono opzionali
- Fallback ai placeholder se `plan_data` è vuoto
- Retrocompatibile con codice esistente

---

**Documentazione generata da Claude Sonnet 4.5 - 10/01/2026**
