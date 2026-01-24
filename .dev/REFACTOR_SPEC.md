# Rooting Future - Spec-Driven Refactoring Plan
## v6.1: Modularization & Simplification

**Goal:** Ridurre da 41k a ~20k LOC senza perdere feature, migliorando manutenibilità

---

## 📊 Analisi Attuale

```
Total Lines:    41,238 LOC
Core Files:
  - app.py                5,056 LOC (96 functions) ⚠️ MONOLITH
  - app_backup.py         1,691 LOC (duplicate)
  - knowledge_store.py    1,395 LOC (50 functions)
  - agents.py             1,390 LOC (27 functions)
  - executive_report.py   1,343 LOC
  - structured_renderer.py 1,083 LOC
```

**Problemi Identificati:**
1. ❌ `app.py` è un monolite (96 route + business logic)
2. ❌ Duplicazione: `app_backup.py` (1,691 LOC inutili)
3. ❌ Export layer: 6 file separati nonostante BaseExporter
4. ❌ Rendering: `structured_renderer.py` + `executive_report.py` + `methodology_section.py` = duplicazioni
5. ❌ Data pipeline: `data_sourcing.py` + `data_ingestor.py` + `data_estimator.py` = overlap

---

## 🎯 Target Architecture (Spec-Driven)

```
rooting_future/
├── core/
│   ├── __init__.py
│   ├── models.py              # Data models (consolidate data_models.py)
│   └── config.py              # Configuration management
│
├── api/
│   ├── __init__.py
│   ├── routes_plans.py        # /api/generate, /api/generate-from-docx
│   ├── routes_upload.py       # /api/upload-docx, /api/check-analysis
│   ├── routes_export.py       # /api/export/*, /download/*
│   ├── routes_editor.py       # /api/edit/*, /api/approve/*
│   └── routes_system.py       # /api/system/*, /api/stream/*
│
├── domain/
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── orchestrator.py    # MultiAgentOrchestrator
│   │   ├── async_client.py    # AsyncGeminiClient
│   │   └── specialized.py     # STW agents
│   │
│   ├── export/
│   │   ├── __init__.py
│   │   ├── base.py            # BaseExporter (già fatto OPT-003)
│   │   └── exporters.py       # Tutti gli esportatori in 1 file
│   │
│   ├── ingestion/
│   │   ├── __init__.py
│   │   └── pipeline.py        # Unify data_sourcing + data_ingestor + data_estimator
│   │
│   └── rendering/
│       ├── __init__.py
│       └── renderer.py        # Unify structured_renderer + executive_report + methodology
│
├── storage/
│   ├── __init__.py
│   ├── knowledge.py           # KnowledgeStore
│   ├── file_search.py         # FileSearchManager
│   └── cache.py               # Web research cache
│
├── web/
│   ├── __init__.py
│   ├── app.py                 # Flask app init + middleware (< 200 LOC)
│   └── views.py               # Frontend routes (render templates only)
│
├── utils/
│   ├── __init__.py
│   ├── colors.py              # club_identity.py
│   ├── stw.py                 # stw_matrix.py + stw_analyzer.py
│   └── web.py                 # web_research.py
│
└── app.py (NEW)               # Entry point (< 50 LOC)
```

---

## 📋 Refactoring Tasks (Spec-Driven)

### **PHASE 1: Quick Wins (2-3 ore)**

#### REF-001: Delete Dead Code
**Priority:** HIGH | **Impact:** -1,691 LOC | **Risk:** ZERO

```python
# Spec:
- Delete app_backup.py (obsolete)
- Delete temp_*.py files
- Delete *.pyc and __pycache__
- Delete unused imports (run autoflake)
```

**Verification:**
- `python app.py` starts without errors
- All tests pass (if any)

---

#### REF-002: Consolidate Export Layer
**Priority:** HIGH | **Impact:** -800 LOC | **Risk:** LOW

```python
# Spec: Merge all exporters into domain/export/exporters.py

# File: domain/export/exporters.py
from .base import BaseExporter

class PDFExporter(BaseExporter):
    """Server-side PDF via WeasyPrint"""
    # Move from export_pdf_server.py

class HTMLExporter(BaseExporter):
    """HTML export"""
    # Move from export_html.py

class DOCXExporter(BaseExporter):
    """DOCX export"""
    # Move from export_docx.py

class PagedHTMLExporter(BaseExporter):
    """Paged HTML export"""
    # Move from export_paged.py

class OnePagerExporter(BaseExporter):
    """One-page summary"""
    # Move from export_onepager.py

# Single import point:
from domain.export.exporters import (
    PDFExporter, HTMLExporter, DOCXExporter,
    PagedHTMLExporter, OnePagerExporter
)
```

**Verification:**
- All export formats work
- PDF generation completes in < 10s
- Backward compatibility maintained

---

#### REF-003: Consolidate Rendering Layer
**Priority:** MEDIUM | **Impact:** -1,500 LOC | **Risk:** MEDIUM

```python
# Spec: Merge structured_renderer + executive_report + methodology_section

# File: domain/rendering/renderer.py
class PlanRenderer:
    """Unified plan rendering"""

    def render_structured(self, plan, metadata):
        """Structured 7-section output"""
        pass

    def render_executive(self, plan, metadata):
        """Executive summary"""
        pass

    def add_methodology(self, content):
        """Append methodology section"""
        pass

    def render_stw_matrix(self, stw_data):
        """Render STW matrix"""
        pass

# Single import:
from domain.rendering import PlanRenderer
renderer = PlanRenderer()
```

**Verification:**
- Generated plans have all 7 sections
- Executive summary renders correctly
- Methodology section present

---

### **PHASE 2: Modularization (1-2 giorni)**

#### REF-004: Split app.py into API Routes
**Priority:** HIGH | **Impact:** -4,000 LOC | **Risk:** MEDIUM

```python
# Spec: Decompose app.py monolith

# Current:
app.py (5,056 LOC, 96 functions) → TOO BIG!

# Target:
web/app.py              (150 LOC) - Flask init + middleware
web/views.py            (200 LOC) - Frontend routes
api/routes_plans.py     (400 LOC) - Plan generation
api/routes_upload.py    (300 LOC) - Upload & analysis
api/routes_export.py    (300 LOC) - Export endpoints
api/routes_editor.py    (400 LOC) - Editor endpoints
api/routes_system.py    (150 LOC) - System & SSE

# Main entry point:
app.py (NEW):
    from web.app import create_app
    app = create_app()
    if __name__ == '__main__':
        app.run()
```

**Migration Strategy:**
1. Create `api/` folder
2. Move routes one module at a time
3. Test after each module
4. Update imports incrementally

**Verification:**
- All existing routes still work
- `/api/generate` → 200 OK
- `/api/upload-docx` → 200 OK
- Dashboard loads correctly

---

#### REF-005: Unify Data Ingestion Pipeline
**Priority:** MEDIUM | **Impact:** -1,200 LOC | **Risk:** MEDIUM

```python
# Spec: Merge data_sourcing + data_ingestor + data_estimator

# File: domain/ingestion/pipeline.py
class DataIngestionPipeline:
    """Unified data ingestion"""

    def __init__(self):
        self.docx_ingestor = DOCXIngestor()
        self.estimator = DataEstimator()
        self.web_sourcer = WebResearchSourcer()

    def ingest_stakeholder_docs(self, files):
        """Full pipeline: DOCX → extract → estimate → merge"""
        pass

    def synthesize_inputs(self, stakeholder_data):
        """Conflict resolution + alignment score"""
        pass

    def enrich_with_web_data(self, club_name, context):
        """Web research augmentation"""
        pass

# Single import:
from domain.ingestion import DataIngestionPipeline
pipeline = DataIngestionPipeline()
```

**Verification:**
- Stakeholder upload works
- Alignment dashboard appears
- Conflict detection active

---

### **PHASE 3: Storage Abstraction (1 giorno)**

#### REF-006: Split Storage Layer
**Priority:** LOW | **Impact:** -500 LOC | **Risk:** LOW

```python
# Spec: Separate concerns in storage/

# File: storage/knowledge.py
class KnowledgeStore:
    """Plans and documents"""
    pass

# File: storage/cache.py
class CacheStore:
    """Web research + API cache"""
    pass

# File: storage/file_search.py
class FileSearchManager:
    """Gemini File Search integration"""
    pass
```

**Verification:**
- Plan saves/loads work
- Cache hit rate > 80%
- File search uploads succeed

---

## 📈 Expected Results

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| **Total LOC** | 41,238 | ~20,000 | -51% |
| **app.py LOC** | 5,056 | ~150 | -97% |
| **Export files** | 6 files | 1 file | -83% |
| **Rendering files** | 3 files | 1 file | -66% |
| **Ingestion files** | 3 files | 1 file | -66% |
| **Maintainability** | Low | High | ✅ |

---

## 🚀 Implementation Order

### Week 1: Quick Wins
1. ✅ **REF-001** - Delete dead code (30 min)
2. ✅ **REF-002** - Consolidate exports (3 ore)
3. ✅ **REF-003** - Consolidate rendering (5 ore)

### Week 2: Core Refactor
4. **REF-004** - Split app.py (2 giorni)
5. **REF-005** - Unify ingestion (1 giorno)

### Week 3: Polish
6. **REF-006** - Split storage (1 giorno)
7. **Testing & Validation** (2 giorni)

---

## ✅ Success Criteria

- [ ] Total LOC < 22,000
- [ ] app.py < 200 LOC
- [ ] All features work identically
- [ ] Performance unchanged or better
- [ ] Zero regressions
- [ ] Clean git history (1 commit per REF-XXX)

---

## 🛡️ Safety Rules

1. **Never delete functionality** - only reorganize
2. **Test after each step** - don't batch refactors
3. **Keep backups** - git commit before each REF-XXX
4. **Backward compatibility** - old imports still work
5. **Document changes** - update this spec after each task

---

## 📝 Notes

- Questo è un **living document** - aggiorna dopo ogni task
- Usa `git commit -m "refactor(REF-XXX): description"` format
- Se qualcosa si rompe, `git revert` e rivaluta
- Priorità: **working code > clean code**
