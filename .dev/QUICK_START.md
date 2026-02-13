# 🚀 Rooting Light - Quick Start Guide

## Per Gemini CLI

### 1. Carica il Context (SEMPRE prima di iniziare)

```bash
cd C:\Users\Mirko\Desktop\rooting_future
.\venv\Scripts\Activate.ps1

# Passa questi file a Gemini
type .dev\PROJECT.md
type .dev\tasks.json
type docs\ARCHITECTURE.md
type .dev\GEMINI_INSTRUCTIONS.md
```

### 2. Scegli Task

```bash
# Vedi task disponibili
type .dev\tasks.json | jq ".active[] | {id, title, estimate}"
```

### 3. Esegui Task

**Prompt Template per Gemini**:

```
Implementa task OPT-001 da .dev/tasks.json.

CONTEXT FILES (leggi prima):
[incolla contenuto di PROJECT.md]
[incolla contenuto di ARCHITECTURE.md]
[incolla sezione task da tasks.json]

Segui le CRITICAL RULES in GEMINI_INSTRUCTIONS.md.

Mostrami le modifiche che farai al codice.
```

### 4. Verifica

```bash
# Syntax check
python -m py_compile <file_modificato>

# App starts
python app.py

# Run verification steps (vedi tasks.json)
```

### 5. Commit

```bash
git add <files>
git commit -m "feat(OPT-XXX): description

- Change 1
- Change 2

Closes OPT-XXX"
```

### 6. Log Progress

```bash
# Aggiungi entry a .dev/progress.txt
echo "[2026-01-23] COMPLETED OPT-001: SQLite indexing - 70% query speed improvement" >> .dev\progress.txt
```

---

## Per Claude Code

### 1. Carica Context

```
Read these files:
- .dev/PROJECT.md
- .dev/tasks.json
- docs/ARCHITECTURE.md

Then implement task OPT-XXX following the specification.
```

### 2. Execute

Claude Code può leggere i file automaticamente e procedere.

---

## Task Prioritization

**Start Here** (Quick Wins):
1. OPT-001 (1h) - SQLite indexing

**Then**:
2. OPT-002 (2-3 days) - Real async
3. OPT-003 (3-5 days) - Export unification

**Later** (Backlog):
- OPT-004, OPT-005, OPT-006
- SCALE-001, SCALE-002

---

## Files You'll Touch

### OPT-001 (SQLite Indexing)
- `knowledge_store.py` - Add indices

### OPT-002 (Real Async)
- `agents.py` - Create AsyncGeminiClient, update orchestrator
- `structured_agent.py` - Apply same pattern

### OPT-003 (Export Unification)
- `export_core.py` (NEW) - BaseExporter class
- `export_pdf_server.py` - Refactor to inherit
- `export_html.py` - Refactor to inherit
- `export_docx.py` - Refactor to inherit
- `export_paged.py` - Refactor to inherit
- `export_onepager.py` - Refactor to inherit
- `export_package.py` - Update imports

---

## Success Metrics

After each task:
- [ ] App starts without errors
- [ ] All verification steps pass
- [ ] Git commit created
- [ ] Progress logged
- [ ] Tasks.json updated (done: true)

---

## Emergency Contacts

- **Problem with Gemini**: Check .dev/GEMINI_INSTRUCTIONS.md
- **Architecture questions**: Read docs/ARCHITECTURE.md
- **Task unclear**: Check .dev/tasks.json for full spec
- **Stuck**: Create handoff document and pass to other AI

---

Ready to start? Pick OPT-001 and go! 🚀
