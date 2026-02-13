# Rooting Future Strategy Engine - Project Overview

## 🎯 Vision

AI-powered strategic planning system that generates professional strategic plans for soccer clubs worldwide in under 60 seconds.

## 📊 Current State

**Version**: v5.5 (Production-Ready)
**Status**: Stable, in production use
**Next**: v6.0 - Performance & Scalability Optimizations

## 🏗️ Architecture

### Core System
- **Multi-Agent Orchestrator**: 6 specialized agents + 1 coordinator
- **Methodology**: Sport To Win (STW) - 21 MACRO objectives across 4 categories
- **RAG Learning**: File Search Store integration with Gemini
- **Export Pipeline**: PDF, DOCX, HTML, Excel, ZIP packages

### Agent Structure
```
MultiAgentOrchestrator
├── STW Sportivi (8 MACRO objectives)
├── STW Strutturali (2 MACRO objectives)
├── STW Marketing (4 MACRO objectives)
├── STW Sociali (7 MACRO objectives)
├── Financial Strategist
└── Strategic Coordinator (synthesizes all)
```

## 🛠️ Tech Stack

### Backend
- **Framework**: Flask 3.1.2 (migration to FastAPI planned)
- **Language**: Python 3.11+
- **Server**: Waitress (production), Flask dev server
- **Database**: SQLite with WAL mode (PostgreSQL migration planned)

### AI/ML
- **Primary LLM**: Gemini 2.0 Flash (via google-generativeai 0.8.5)
- **RAG**: Google File Search Store API
- **Embeddings**: models/embedding-001
- **Context**: 200k tokens per agent

### Export Layer
- **PDF**: WeasyPrint 67.0
- **DOCX**: python-docx 1.2.0
- **HTML**: Jinja2 templates + custom CSS
- **Excel**: openpyxl 3.1.5

### Data Layer
- **Database**: SQLite 3 (knowledge_base/rooting_future.db)
- **Cache**: File-based AI cache + search cache
- **Persistence**: JSON for intermediate states

### Frontend
- **Templates**: Jinja2 with Bootstrap-inspired custom CSS
- **Dashboard**: Hybrid live console + upload interface
- **Auth**: Flask-Login 0.6.3 + bcrypt
- **Payments**: Stripe 14.1.0 (credit system)

## 📐 Key Patterns

### 1. Agent Generation Flow
```python
club_data → MultiAgentOrchestrator → 6 agents (parallel/sequential)
    ↓
Each agent: RAG context fetch → Gemini generate → Post-process
    ↓
Coordinator: Synthesize all outputs → Executive Summary
    ↓
Export: PDF + DOCX + OnePager + Package
```

### 2. RAG Context Fetching
```python
# Per ogni agent
rag_context = knowledge_store.get_context_for_generation(
    club_category=category,
    section_type=section_keyword
)
# Retrieves 1-2 best examples from previous plans
```

### 3. Export Pattern (Current - Duplicated)
```
export_pdf_server.py    → WeasyPrint
export_html.py          → Jinja2 render
export_docx.py          → python-docx
export_paged.py         → Paged CSS media
export_onepager.py      → Infographic
export_package.py       → ZIP bundler
```
⚠️ **Problem**: 60% code duplication across exporters

### 4. Data Sourcing (3-Tier System)
```
Tier 1: Real data from user input (questionnaire)
Tier 2: Web research (Serper/Tavily APIs)
Tier 3: AI estimation from benchmarks
```

## 🚨 Known Issues & Constraints

### Performance Bottlenecks
1. **Fake Async**: `asyncio.gather()` used but Gemini calls are synchronous
   - Current: 60s for 6 agents
   - Potential: 15-20s with real parallelism

2. **No Database Indices**: SQLite queries slow on 200+ plans
   - Linear scan on every RAG fetch
   - No WAL mode configured

3. **Export Duplication**: 6 modules with shared logic
   - Hard to maintain
   - Inconsistent branding

### Scalability Limits
- **Max concurrent plans**: ~5 (ThreadPoolExecutor max_workers=2)
- **Context rot**: Can occur in long sessions
- **SQLite locking**: Concurrent writes block

### API Dependencies
- **Gemini API**: Rate limits (60 req/min)
- **Web Research**: Serper (100 searches/month free tier)
- **File Search**: Google File Search Store quotas

## 📝 Code Style Guidelines

### Type Hints (Required)
```python
def generate(self, club_data: Dict, research_data: Dict = None) -> Dict[str, Any]:
    """Generate strategic plan section"""
    pass
```

### Logging (Never print)
```python
import logging
logger = logging.getLogger(__name__)

logger.info("Starting generation...")
logger.error(f"Failed: {e}")
```

### Config Management
```python
# ✅ Good
from config import MODEL_CONFIG, GEMINI_API_KEY

# ❌ Bad
api_key = "hardcoded_key"
```

### Error Handling
```python
try:
    response = model.generate_content(prompt)
except InvalidArgument as e:
    logger.error(f"Invalid argument: {e}")
    # Fallback logic
except Exception as e:
    logger.error(f"Unexpected error: {e}")
    return {'content': 'Error...', 'sources': []}
```

## 🎯 Current Priorities (v6.0)

### Tier 1: Critical Performance Wins
1. **Real Async Execution** (2-3 days)
   - Replace fake asyncio with ThreadPoolExecutor
   - Add rate limiting
   - Add retry logic with exponential backoff

2. **Export Layer Unification** (3-5 days)
   - Create BaseExporter abstract class
   - Refactor 6 exporters to inherit
   - Remove 500+ LOC duplication

3. **SQLite Indexing** (1 hour)
   - Add indices on (category, section_type)
   - Enable WAL mode
   - Add PRAGMA synchronous=NORMAL

### Tier 2: Strategic Refactoring (1-2 weeks)
- Stratified prompt construction
- Unified error handling (circuit breaker)
- Split storage layer (plan/document/cache stores)

### Tier 3: Scalability Foundation (1-2 months)
- FastAPI migration
- PostgreSQL + Redis
- Celery task queue

## 🔐 Security & Licensing

### License System
- **HWID-based**: Machine-locked licenses
- **Activation**: license.key required to run
- **Enforcement**: Middleware check on every request

### Authentication
- **User system**: Super Admin, Admin, Manager roles
- **Multi-tenancy**: User-isolated data (plan ownership)
- **Credits**: Pay-per-plan generation model

## 📊 Metrics & KPIs

### Performance
- Generation time: <60s (target: <20s)
- Export time: 10-30s per PDF
- Database query time: ~100-500ms (target: <50ms)

### Quality
- Plans generated: 200+ in production
- Knowledge base: 17MB (RAG corpus)
- AI cache: Reduces redundant calls by ~30%

### Business
- Credit system: 1 credit = 1 strategic plan
- Stripe integration: Ready for SaaS launch
- Multi-format output: 100% of plans export successfully

## 🚀 Quick Start Commands

```bash
# Development
python app.py                    # Start dev server

# Testing
pytest tests/ -v                 # Run test suite
python -m py_compile agents.py   # Syntax check

# Production
waitress-serve --port=5000 app:app

# Build
python build_nuitka.bat          # Windows executable
```

## 📚 Key Files Reference

| File | Purpose | LOC |
|------|---------|-----|
| `app.py` | Flask app, routes, auth | ~2500 |
| `agents.py` | Multi-agent orchestrator | ~1250 |
| `structured_agent.py` | Structured data generation | ~800 |
| `export_pdf_server.py` | PDF export | ~400 |
| `knowledge_store.py` | SQLite RAG storage | ~500 |
| `config.py` | Central configuration | ~300 |

## 🔄 Development Workflow

1. **Feature branch**: `git checkout -b feature/name`
2. **Implement**: Make changes
3. **Test**: Run relevant tests
4. **Commit**: Atomic commits with clear messages
5. **Verify**: App starts, no crashes
6. **PR/Merge**: When feature complete

## 📞 Support Resources

- **CHANGELOG**: `ROOTING_FUTURE_CHANGELOG.md`
- **Audit**: `AUDIT_TECNICO_COMMERCIALIZZAZIONE.md`
- **Optimization Plan**: `.dev/tasks.json`

---

**Last Updated**: 2026-01-23
**Maintained By**: Development Team
**Next Review**: After v6.0 milestone
