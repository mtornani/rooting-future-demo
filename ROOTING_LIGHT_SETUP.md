# ✅ Rooting Light - Setup Completato!

## 🎉 Cosa Abbiamo Creato

**Rooting Light** è ora attivo! Una versione pragmatica e leggera di spec-driven development, senza overhead enterprise.

### 📁 Struttura Creata

```
rooting_future/
├── .dev/                          # Development context
│   ├── PROJECT.md                 # Project overview (28k LOC, v5.5→v6.0)
│   ├── tasks.json                 # 3 active tasks (Tier 1 optimizations)
│   ├── progress.txt               # Development log (append-only)
│   ├── GEMINI_INSTRUCTIONS.md     # Gemini CLI workflow guide
│   ├── QUICK_START.md             # Quick reference
│   └── README.md                  # .dev/ directory guide
│
├── docs/
│   └── ARCHITECTURE.md            # Code patterns, gotchas, dependencies
│
└── [existing codebase unchanged]
```

---

## 🚀 Come Usarlo con Gemini CLI

### Opzione 1: Prompt Completo (Copy-Paste Ready)

```
Ciao Gemini! Sono su un progetto chiamato Rooting Future (strategia AI per club calcistici).

Ho bisogno che implementi il task OPT-001 (SQLite Indexing).

CONTEXT FILES - Leggi questi prima di iniziare:

---
FILE: .dev/PROJECT.md
[Qui incolli tutto il contenuto di .dev\PROJECT.md]
---

---
FILE: docs/ARCHITECTURE.md - Sezione "SQLite Locking"
[Qui incolli la sezione rilevante da docs\ARCHITECTURE.md]
---

---
FILE: .dev/tasks.json - Task OPT-001
{
  "id": "OPT-001",
  "title": "SQLite Indexing & WAL Mode",
  "files": ["knowledge_store.py"],
  "tasks": [
    "Add CREATE INDEX on documents(category, section_type)",
    "Add CREATE INDEX on plans(created_at DESC)",
    "Enable PRAGMA journal_mode=WAL",
    "Add PRAGMA synchronous=NORMAL"
  ],
  "verification": [
    "sqlite3 knowledge_base/rooting_future.db '.indices' shows new indices",
    "PRAGMA journal_mode returns 'wal'",
    "Query benchmark shows >60% improvement"
  ]
}
---

CRITICAL RULES (from GEMINI_INSTRUCTIONS.md):
1. Use type hints on all functions
2. Use logger (not print) for logging
3. Follow existing code style in knowledge_store.py
4. Test that app.py starts after changes

TASK: Modifica knowledge_store.py per aggiungere gli indici SQLite e abilitare WAL mode.

Mostrami prima le modifiche che farai, poi le implementerò.
```

### Opzione 2: Prompt Breve (Se Gemini può leggere file)

```
Task: Implementa OPT-001 da .dev/tasks.json

Context files:
- .dev/PROJECT.md
- docs/ARCHITECTURE.md (sezione SQLite)
- .dev/GEMINI_INSTRUCTIONS.md

Segui le CRITICAL RULES. Mostrami le modifiche a knowledge_store.py.
```

---

## 🎯 I 3 Task Pronti

### 1️⃣ OPT-001: SQLite Indexing (START HERE)
- **Tempo**: 1 ora
- **File**: `knowledge_store.py`
- **Impatto**: +70% query speed
- **Difficoltà**: ⭐ (Bassa)
- **ROI**: 🔥🔥🔥 (Altissimo)

**Perché iniziare qui**: Win veloce, alto impatto, basso rischio.

### 2️⃣ OPT-002: Real Async Execution
- **Tempo**: 2-3 giorni
- **File**: `agents.py`, `structured_agent.py`
- **Impatto**: -66% generation time (60s → 20s)
- **Difficoltà**: ⭐⭐⭐ (Media)
- **ROI**: 🔥🔥🔥🔥🔥 (Massimo)

**Perché dopo OPT-001**: Più complesso, ma impatto enorme.

### 3️⃣ OPT-003: Export Unification
- **Tempo**: 3-5 giorni
- **File**: 7 files (export_*.py)
- **Impatto**: -500 LOC, manutenibilità +80%
- **Difficoltà**: ⭐⭐⭐⭐ (Alta)
- **ROI**: 🔥🔥🔥 (Alto a lungo termine)

**Perché per ultimo**: Refactor grande, richiede attenzione.

---

## 🔄 Workflow Quotidiano

### Mattina (15 min)
```bash
cd C:\Users\Mirko\Desktop\rooting_future
.\venv\Scripts\Activate.ps1

# Check status
type .dev\tasks.json | jq '.active[] | {id, title, done}'

# Review progress
type .dev\progress.txt | tail -20
```

### Durante lo sviluppo (con Gemini)
```bash
# 1. Passa context a Gemini (vedi Opzione 1/2 sopra)
# 2. Gemini propone modifiche
# 3. Verifica modifiche
python -m py_compile <file>
python app.py  # Should start

# 4. Run verification
# (steps specifici in tasks.json)

# 5. Commit if passed
git add <files>
git commit -m "feat(OPT-XXX): description"

# 6. Update progress
echo "[2026-01-23] COMPLETED OPT-XXX: brief note" >> .dev\progress.txt
```

### Sera (5 min)
```bash
# Update tasks.json (mark done: true)
# Push changes
git push origin feature/v6-performance
```

---

## 📊 Metriche di Successo

### Dopo OPT-001
- [ ] App starts in <2s (unchanged)
- [ ] SQLite indices visible (`sqlite3 ... '.indices'`)
- [ ] WAL mode enabled (`PRAGMA journal_mode` → wal)
- [ ] Query time -70% (benchmark)

### Dopo OPT-002
- [ ] Generation time: 60s → 15-20s
- [ ] Real parallelism (6 agents concurrent)
- [ ] No rate limit errors

### Dopo OPT-003
- [ ] All 6 export formats work
- [ ] Code duplication gone (-500 LOC)
- [ ] Single branding logic

---

## 🆘 Troubleshooting

### Gemini non capisce il context
**Soluzione**: Usa Opzione 1 (copy-paste completo dei file)

### App non parte dopo modifiche
```bash
# Check syntax
python -m py_compile <file_modificato>

# Check imports
python -c "import knowledge_store"

# Rollback if needed
git checkout <file>
```

### Task troppo complesso
**Soluzione**: Crea handoff per Claude Code
```bash
# Create .dev/handoff_OPT-XXX.md
# Descrivi cosa hai fatto, cosa manca, problemi incontrati
```

### Gemini propone breaking changes
**Soluzione**: Rifiuta, chiedi approccio conservativo
```
"No, questa modifica rompe il pattern esistente.
Segui il pattern in docs/ARCHITECTURE.md sezione X.
Proponi soluzione che mantiene compatibilità."
```

---

## 🎓 Tips per Gemini CLI

### 1. Context è TUTTO
Più context dai (PROJECT.md, ARCHITECTURE.md), migliore è l'output.

### 2. Sii Specifico
❌ "Ottimizza il database"
✅ "Aggiungi indici su documents(category, section_type) e plans(created_at DESC)"

### 3. Chiedi Review Prima
"Mostrami le modifiche PRIMA di implementare" → Evita errori

### 4. Verifica SEMPRE
Non assumere che funzioni. Testa OGNI cambiamento.

### 5. Small Commits
1 commit per task. Atomico. Revertibile.

---

## 🚦 Cosa Fare ORA

### Passo 1: Familiarizza
```bash
# Leggi questi 3 file (5 min)
type .dev\PROJECT.md | more
type .dev\tasks.json | more
type .dev\GEMINI_INSTRUCTIONS.md | more
```

### Passo 2: Prima Task (1 ora)
```bash
# Implementa OPT-001 con Gemini
# Usa prompt da "Opzione 1" sopra
```

### Passo 3: Verifica Win
```bash
# Check indices
sqlite3 knowledge_base\rooting_future.db ".indices"

# Celebrate! 🎉
```

### Passo 4: Log & Commit
```bash
git commit -m "feat(OPT-001): SQLite indexing and WAL mode"
echo "[2026-01-23] COMPLETED OPT-001 - First Rooting Light win!" >> .dev\progress.txt
```

---

## 🔮 Prossimi Passi (Dopo v6.0)

Una volta completate le 3 task Tier 1:

1. **Valuta ROI**: Misura miglioramenti reali
2. **Decide Tier 2**: Stratified prompts? Circuit breaker?
3. **Planning v7.0**: FastAPI migration? Multi-tenant?

Ma per ora: **Focus su OPT-001, OPT-002, OPT-003.**

---

## ✅ Checklist Setup Rooting Light

- [x] Creata struttura `.dev/`
- [x] Scritto PROJECT.md (overview completo)
- [x] Definite 3 task Tier 1 in tasks.json
- [x] Documentati pattern in ARCHITECTURE.md
- [x] Creato workflow guide per Gemini CLI
- [x] Aggiornato .gitignore
- [x] Pronto per primo task (OPT-001)

**🎉 Setup completato al 100%!**

---

## 💬 Domande Frequenti

**Q: Devo usare scripts/ralph/ come nei framework originali?**
A: No. Rooting Light è manual trigger. Più flessibilità, zero overhead.

**Q: Posso usare Claude Code invece di Gemini?**
A: Sì! Leggi `.dev/QUICK_START.md`. Stesso workflow, tool diverso.

**Q: Cosa faccio se un task è troppo grande?**
A: Spezza in sub-task. Esempio: OPT-002 → Step 1 (AsyncClient), Step 2 (Orchestrator), Step 3 (Test).

**Q: Devo seguire l'ordine OPT-001, 002, 003?**
A: Consigliato (crescente complessità), ma non obbligatorio.

**Q: Quanto tempo prende v6.0 completo?**
A: OPT-001 (1h) + OPT-002 (2-3 giorni) + OPT-003 (3-5 giorni) = **~1 settimana full-time**.

---

## 🎯 Obiettivo Finale (v6.0)

```
Generation Time:  60s → 15-20s  (-66%)
Query Speed:      500ms → 50ms   (+90%)
Code Duplication: High → None    (-500 LOC)
Maintainability:  Medium → High  (+80%)
```

**Sei pronto? Inizia con OPT-001 ora! 🚀**

---

**Buon coding con Rooting Light!**
