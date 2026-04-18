# Rooting Future -- Wiki Schema v1.0

> Questo file governa il comportamento del LLM nella gestione del Wiki.
> Ogni agente lo legge all'avvio per capire dove trovare e come aggiornare la conoscenza.

---

## 1. Struttura Directory

```
wiki/
  WIKI_SCHEMA.md          <- Questo file (regole per il LLM)
  raw/{club_slug}/        <- Documenti originali club (IMMUTABILI)
    vision.md
    mission.md
    swot.md
    pest.md
    competitors.md
    stakeholders.md
    risorse.md
    valori-fondamenta.md
    intervista-board.md
  kb/                     <- Knowledge Base (gestita dal LLM)
    index.md              <- Catalogo di tutte le pagine con summary
    log.md                <- Registro cronologico append-only
    clubs/                <- Una pagina per club analizzato
      {club_slug}.md
      {club_slug}/        <- Sub-dir per piani generati
        piano_v1.md
    strategie/            <- Pattern e best practice ricorrenti
    benchmark/            <- Dati quantitativi per categoria/regione
    concetti/             <- Concetti chiave della metodologia STW
    sintesi/              <- Analisi cross-club e lezioni apprese
```

## 2. Formato Pagine Wiki

Ogni pagina in `kb/` segue questo formato:

```markdown
---
title: "Titolo Pagina"
tags: [eccellenza, sportivi, settore-giovanile]
clubs: [riccione-calcio-1926]
date_created: 2026-04-12
date_updated: 2026-04-12
sources:
  - raw/riccione-calcio-1926/vision.md
  - raw/riccione-calcio-1926/swot.md
---

# Titolo Pagina

Contenuto in markdown...

Cross-link ad altre pagine: vedi [[settore-giovanile-eccellenza]]

## Fonti

- Vision Riccione Calcio 1926 (raw/riccione-calcio-1926/vision.md)
- Analisi SWOT Riccione (raw/riccione-calcio-1926/swot.md)
```

### Convenzioni

- **Slug club**: lowercase, trattini (es. `riccione-calcio-1926`)
- **Nomi pagine**: descrittivi, lowercase, trattini (es. `settore-giovanile-eccellenza.md`)
- **Cross-link**: `[[nome-pagina]]` senza path (risolti da index.md)
- **Tag frontmatter**:
  - `categoria`: eccellenza, serie-d, promozione, prima-categoria
  - `area-stw`: sportivi, strutturali, marketing, sociali, financial
  - `tipo`: club, strategia, benchmark, concetto, sintesi
- **Date**: ISO 8601 (`2026-04-12`)
- **Contenuto minimo sezione**: mai meno di 200 caratteri per evitare pagine vuote

## 3. Documenti Raw (Layer 1)

I 9 documenti compilati dal club vengono convertiti da DOCX a Markdown e salvati in
`wiki/raw/{club_slug}/`. Questi file sono **immutabili** -- il LLM li legge ma non li
modifica mai.

**I 9 documenti standard:**

| # | Documento | File | Contenuto atteso |
|---|-----------|------|-----------------|
| 1 | Vision | `vision.md` | Dove vuole essere il club tra 3-5 anni |
| 2 | Mission | `mission.md` | Perche' esiste il club, valori fondanti |
| 3 | Analisi SWOT | `swot.md` | Forze, debolezze, opportunita', minacce |
| 4 | Analisi PEST | `pest.md` | Fattori politici, economici, sociali, tecnologici |
| 5 | Competitors | `competitors.md` | Analisi club competitor nello stesso bacino |
| 6 | Stakeholders | `stakeholders.md` | Mappa stakeholder e loro interessi |
| 7 | Risorse | `risorse.md` | Inventario risorse umane, finanziarie, infrastrutturali |
| 8 | Valori/Fondamenta | `valori-fondamenta.md` | DNA del club, storia, identita' |
| 9 | Intervista Board | `intervista-board.md` | Sintesi delle interviste ai dirigenti |

**Documenti aggiuntivi** (opzionali): bilanci, organigrammi, piani precedenti,
regolamenti FIGC. Vanno in `wiki/raw/{club_slug}/extra/`.

## 4. Workflow: Ingest

**Trigger**: Un nuovo club viene inserito nel sistema.

**Flusso**:

1. **Converti**: I 9 DOCX vengono convertiti in Markdown in `wiki/raw/{club_slug}/`
2. **Leggi**: Il LLM legge tutti i 9 documenti del club
3. **Crea pagina club**: Crea `wiki/kb/clubs/{club_slug}.md` con sintesi strutturata:
   - Anagrafica (nome, categoria, regione, anno fondazione)
   - Sintesi Vision e Mission
   - Punti chiave SWOT (top 3 per quadrante)
   - Fattori PEST rilevanti
   - Competitor principali
   - Stakeholder chiave e loro peso
   - Risorse disponibili (budget stimato, staff, infrastrutture)
   - Temi emersi dalle interviste board
4. **Aggiorna strategie/**: Per ogni insight significativo, aggiorna o crea la pagina
   strategia pertinente. Esempio: se il club ha un settore giovanile forte, aggiorna
   `strategie/settore-giovanile-eccellenza.md` con il caso di questo club.
5. **Aggiorna benchmark/**: Se il club fornisce dati quantitativi (budget, staff, ricavi),
   aggiorna `benchmark/{categoria}-{regione}.md`.
6. **Aggiorna concetti/**: Se emergono pattern STW rilevanti, aggiorna le pagine in
   `concetti/`.
7. **Aggiorna index.md**: Aggiungi le nuove pagine create/modificate.
8. **Log**: Appendi entry a `log.md`:
   ```
   ## 2026-04-12 — Ingest: Riccione Calcio 1926
   - Club: Riccione Calcio 1926 (Eccellenza, Emilia-Romagna)
   - Pagine create: clubs/riccione-calcio-1926.md
   - Pagine aggiornate: strategie/settore-giovanile-eccellenza.md, benchmark/eccellenza-emilia-romagna.md
   - Note: Club con forte identita' territoriale, settore giovanile da sviluppare
   ```

**Regola**: Una singola ingest tipicamente tocca 5-15 pagine Wiki.

## 5. Workflow: Generazione Piano

**Trigger**: L'utente chiede di generare un piano strategico per un club gia' ingerito.

**Flusso per ogni agente:**

1. **Leggi index.md** per trovare pagine rilevanti
2. **Carica contesto Wiki** secondo il mapping agenti (sezione 7)
3. **Genera sezione** con tutto il contesto Wiki nel prompt
4. **Dopo generazione completa**: salva piano come `wiki/kb/clubs/{club_slug}/piano_v{n}.md`
5. **Post-generazione**: integra lezioni apprese in `strategie/` e `sintesi/lezioni-apprese.md`

**Differenza dal RAG**: Il RAG iniettava 3000 char (~2 documenti troncati). Il Wiki
fornisce 10-50K char di conoscenza sintetizzata e pertinente. Il LLM ha contesto
ricchissimo per generare output dettagliato.

## 6. Workflow: Lint

**Trigger**: Periodico o manuale.

**Controlli**:
- Pagine orfane (nessun link entrante da index.md o altre pagine)
- Cross-link rotti (riferimento a pagina che non esiste)
- Contraddizioni tra pagine (dati numerici incoerenti)
- Gap di conoscenza (concetti menzionati ma senza pagina propria)
- Pagine stale (non aggiornate da piu' di 90 giorni)
- Benchmark incompleti (categorie senza dati)

## 7. Mapping Agenti -> Pagine Wiki

Ogni agente legge un sottoinsieme specifico del Wiki per generare la sua sezione.

| Agente | Pagine Wiki da Leggere |
|--------|----------------------|
| **Strategic Coordinator** | `clubs/{slug}.md`, `sintesi/overview.md`, `benchmark/{cat}.md` |
| **STW Sportivi** | `clubs/{slug}.md` (sez. sportiva), `strategie/settore-giovanile-*.md`, `strategie/competitivo-*.md`, `concetti/stw-sportivi.md` |
| **STW Strutturali** | `clubs/{slug}.md` (sez. strutturale), `strategie/ristrutturazione-*.md`, `strategie/hr-*.md`, `concetti/infrastrutture-*.md` |
| **STW Marketing** | `clubs/{slug}.md` (sez. marketing), `strategie/marketing-*.md`, `strategie/diversificazione-ricavi-*.md`, `concetti/brand-*.md` |
| **STW Sociali** | `clubs/{slug}.md` (sez. sociale), `strategie/impatto-sociale-*.md`, `strategie/sostenibilita-*.md`, `concetti/stw-sociali.md` |
| **Financial Strategist** | `clubs/{slug}.md` (dati finanziari), `benchmark/{cat}.md`, `concetti/sostenibilita-finanziaria.md` |
| **Research Validator** | Tutto il Wiki pertinente al club (verifica coerenza) |
| **Post-Production Editor** | `clubs/{slug}.md`, `sintesi/lezioni-apprese.md` |

**Regola**: ogni agente riceve al massimo 50K caratteri di contesto Wiki. Se le pagine
eccedono, tronca le pagine strategie/ mantenendo intatte clubs/{slug}.md e benchmark/.

## 8. Cosa NON Fare

- **NON modificare** file in `wiki/raw/` -- sono immutabili
- **NON usare embedding/vettori** -- il Wiki e' markdown, il LLM lo legge direttamente
- **NON creare database** -- il Wiki e' una directory di file, versionabile con git
- **NON duplicare contenuto** -- se un concetto esiste gia' in una pagina, linkata invece di copiare
- **NON generare pagine vuote** -- minimo 200 caratteri di contenuto utile
- **NON sovrascrivere piani precedenti** -- incrementa la versione (piano_v1, piano_v2...)
