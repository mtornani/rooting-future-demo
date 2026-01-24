# Rooting Future - Architecture & Patterns

## 🏗️ System Architecture

### High-Level Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        Flask App (app.py)                    │
│  Routes | Auth | Webhooks | SSE Streaming | Admin Panel     │
└───────────────────────┬─────────────────────────────────────┘
                        │
        ┌───────────────┴───────────────┐
        │                               │
        ▼                               ▼
┌──────────────────┐          ┌──────────────────┐
│  Multi-Agent     │          │  Structured      │
│  Orchestrator    │          │  Orchestrator    │
│  (agents.py)     │          │  (structured_    │
│                  │          │   agent.py)      │
└────────┬─────────┘          └────────┬─────────┘
         │                             │
         │ spawns 6+1 agents           │ generates tables/data
         │                             │
         ▼                             ▼
┌────────────────────────────────────────────────┐
│            Gemini 2.0 Flash API                │
│         (google-generativeai SDK)              │
└────────────────────────────────────────────────┘
         │                             │
         │ stores/retrieves            │
         ▼                             ▼
┌─────────────────────┐    ┌──────────────────────┐
│  Knowledge Store    │    │   Export Pipeline    │
│  (SQLite + RAG)     │    │   (PDF/DOCX/HTML)    │
└─────────────────────┘    └──────────────────────┘
```

## 📦 Core Components

### 1. Multi-Agent Orchestrator (`agents.py`)

**Purpose**: Coordinates 6 specialized agents + 1 coordinator to generate strategic plans.

**Architecture**:
```python
class MultiAgentOrchestrator:
    def __init__(self, knowledge_store, file_search_store_name):
        self.agents = {
            AgentRole.COORDINATOR: StrategicAgent(...)
            AgentRole.STW_SPORTIVI: StrategicAgent(...)
            AgentRole.STW_STRUTTURALI: StrategicAgent(...)
            AgentRole.STW_MARKETING: StrategicAgent(...)
            AgentRole.STW_SOCIALI: StrategicAgent(...)
            AgentRole.FINANCIAL: StrategicAgent(...)
        }

    def generate_strategic_plan(self, club_data, parallel=True):
        # Execute agents
        # Synthesize with coordinator
        # Return complete plan
```

**Key Methods**:
- `generate_strategic_plan()` - Main entry point
- `_generate_sequential()` - Execute agents one by one
- `_generate_parallel()` - Execute agents concurrently (⚠️ currently fake async)
- `generate_single_section()` - Regenerate specific section

**Agent Roles**:
| Role | Responsibility | Output Section |
|------|---------------|----------------|
| COORDINATOR | Executive summary synthesis | `executive_summary` |
| STW_SPORTIVI | 8 sports objectives (MACRO 1-8) | `stw_sportivi` |
| STW_STRUTTURALI | 2 infrastructure objectives | `stw_strutturali` |
| STW_MARKETING | 4 marketing objectives | `stw_marketing` |
| STW_SOCIALI | 7 social objectives | `stw_sociali` |
| FINANCIAL | Economic-financial plan | `financial_plan` |

### 2. Strategic Agent (`agents.py:StrategicAgent`)

**Purpose**: Individual agent that generates content for one domain.

**Pattern**:
```python
class StrategicAgent:
    def __init__(self, spec: AgentSpec, file_search_store_name: str):
        self.spec = spec  # System prompt, expertise
        self.model = genai.GenerativeModel(MODEL_CONFIG.name)
        self.cache = AICache()  # File-based cache
        self.sourcer = SourcedContentGenerator()

    def generate(self, club_data, research_data, rag_context):
        # 1. Build prompt with RAG context
        prompt = self._build_simple_prompt(club_data, rag_context)

        # 2. Check AI cache
        cached = self.cache.get(prompt)
        if cached:
            return cached

        # 3. Call Gemini
        response = self.model.generate_content(prompt)

        # 4. Post-process and cache
        content = self._post_process(response.text)
        self.cache.set(prompt, content)

        return {'content': content, 'sources': [...]}
```

**Critical Details**:
- ⚠️ **Gemini calls are synchronous** - blocking I/O
- ✅ **AI Cache** reduces redundant calls (~30% hit rate)
- ✅ **Fallback mechanism** if tools fail (retry without tools)
- ⚠️ **No rate limiting** - can hit API limits

### 3. RAG System (Knowledge Store + File Search)

**Purpose**: Learn from previous successful plans to improve quality.

**Flow**:
```
Previous Plans → SQLite → Embeddings → File Search Store (Google)
                                              ↓
New Plan Generation ← RAG Context Fetch ←─────┘
```

**Implementation**:
```python
# knowledge_store.py
class SQLiteKnowledgeStore:
    def save_plan(self, plan_id, club_data, plan_content):
        # Save to SQLite
        # Upload to Gemini File Search Store for RAG

    def get_context_for_generation(self, club_category, section_type):
        # Query similar plans by category
        # Return 1-2 best examples
```

**⚠️ Performance Issue**:
- No indices on `category`, `section_type` → linear scan
- Queried for EVERY agent (6x per plan) → bottleneck

### 4. Export Pipeline

**Current State** (6 separate modules):

```
export_pdf_server.py    → WeasyPrint (HTML → PDF)
export_html.py          → Jinja2 templates
export_docx.py          → python-docx
export_paged.py         → Paged CSS media (print-optimized HTML)
export_onepager.py      → Infographic summary
export_package.py       → ZIP bundler (all formats)
```

**Common Pattern** (duplicated 6 times):
```python
def export(club_name, plan_data, metadata):
    # 1. Apply branding (colors, logo)
    # 2. Render template
    # 3. Add methodology section
    # 4. Generate output file
    # 5. Return filepath
```

**⚠️ Problem**: 60% code duplication across modules.

**Solution Needed**: `BaseExporter` abstract class.

## 🔄 Data Flow

### Plan Generation Flow

```
1. User Input (Web Form)
   ↓
2. app.py: /api/generate endpoint
   ↓
3. Background task: generate_strategic_plan_background()
   ↓
4. MultiAgentOrchestrator.generate_strategic_plan()
   ├─ RAG context fetch (6x parallel)
   ├─ Agent 1: STW Sportivi → Gemini API
   ├─ Agent 2: STW Strutturali → Gemini API
   ├─ Agent 3: STW Marketing → Gemini API
   ├─ Agent 4: STW Sociali → Gemini API
   ├─ Agent 5: Financial → Gemini API
   └─ Agent 6: Coordinator → Gemini API (synthesizes)
   ↓
5. Post-Production Editor (cleanup, validation)
   ↓
6. Knowledge Store: save plan + upload to File Search
   ↓
7. Export Pipeline: Generate PDF, DOCX, OnePager
   ↓
8. Response: URLs to download files
```

**Timing** (current):
- Steps 1-3: ~2s
- Step 4 (Generation): ~60s ⚠️ (should be 15-20s)
- Steps 5-7: ~15s
- **Total**: ~77s

## 🧩 Key Design Patterns

### 1. Multi-Agent Coordination

**Pattern**: Specialized agents with single responsibility.

**Benefits**:
- ✅ Modular: Each agent can be improved independently
- ✅ Testable: Can test individual agents
- ✅ Scalable: Add new agents without touching existing

**Trade-offs**:
- ⚠️ Sequential execution slow (60s)
- ⚠️ Coordinator depends on all agents completing

### 2. RAG Learning Loop

**Pattern**: Every generated plan becomes training data.

```python
# After generation
knowledge_store.save_plan(plan_id, club_data, plan_content)
knowledge_store.upload_to_file_search(plan_id)

# Before next generation
rag_context = knowledge_store.get_context_for_generation(category, section)
# Agent sees examples from similar clubs
```

**Benefits**:
- ✅ Quality improves over time
- ✅ Consistent tone and structure
- ✅ Learns domain-specific patterns

### 3. AI Cache Layer

**Pattern**: File-based cache keyed by prompt MD5 hash.

```python
class AICache:
    def get(self, prompt: str) -> Optional[str]:
        cache_path = cache_dir / f"{md5(prompt)}.txt"
        if cache_path.exists():
            return cache_path.read_text()
        return None

    def set(self, prompt: str, response: str):
        cache_path = cache_dir / f"{md5(prompt)}.txt"
        cache_path.write_text(response)
```

**Benefits**:
- ✅ Reduces API calls (~30% hit rate)
- ✅ Faster iteration during development
- ✅ Cost savings

**Trade-offs**:
- ⚠️ Cache invalidation manual
- ⚠️ No TTL (time to live)
- ⚠️ Not distributed (single machine only)

### 4. Data Sourcing (3-Tier System)

**Pattern**: Transparent data provenance.

```python
# Tier 1: Real data (highest trust)
if club_data.get(f"{field}_source") == "questionnaire":
    value = club_data[field]
    source = "(fonte: questionario)"

# Tier 2: Web research
elif research_data.get(field):
    value = research_data[field]
    source = "(fonte: ricerca web)"

# Tier 3: AI estimation (lowest trust)
else:
    value = estimate_from_benchmarks(field, category)
    source = "(fonte: stima AI)"
```

**Output**: Every data point tagged with source badge.

## 🚨 Known Gotchas

### 1. Gemini API Quirks

**Issue**: Tool declarations must match exact API schema.

```python
# ❌ WRONG (causes "Unknown field" error)
tool = genai.protos.Tool(google_search={})

# ✅ CORRECT (no tools, or use supported tools only)
model = genai.GenerativeModel(MODEL_CONFIG.name)
```

**Fix Applied**: Removed `google_search` tool in v5.5.

### 2. WeasyPrint Performance

**Issue**: PDF generation slow (~10-30s per document).

```python
# Slow operation
weasyprint.HTML(string=html_content).write_pdf(filepath)
```

**Workarounds**:
- Use simpler CSS (avoid heavy calc())
- Optimize images (compress before embedding)
- Consider alternative: `wkhtmltopdf` or `puppeteer`

### 3. SQLite Locking

**Issue**: Concurrent writes block.

```python
# Multiple agents writing logs simultaneously → lock
logger.info("Agent started")  # Writes to DB-backed log
```

**Solution**: Enable WAL mode (OPT-001).

```sql
PRAGMA journal_mode=WAL;
```

### 4. Context Window Limits

**Issue**: Prompts can exceed Gemini's 200k token limit.

**Current Mitigation**:
- Truncate RAG context to 2 examples max
- Summarize research data before injection

**Better Solution**: Stratified prompts (OPT-004).

### 5. Async/Await Confusion

**Issue**: `asyncio.gather()` used but calls are synchronous.

```python
# ❌ FAKE ASYNC (no actual parallelism)
async def run_agent(role, agent):
    output = agent.generate(club_data)  # Synchronous blocking call
    return role.value, output

results = await asyncio.gather(*tasks)  # Doesn't parallelize
```

**Why it doesn't work**: `agent.generate()` calls `model.generate_content()` which is synchronous I/O.

**Fix (OPT-002)**:
```python
executor = ThreadPoolExecutor(max_workers=6)
futures = [executor.submit(agent.generate, club_data) for agent in agents]
results = [future.result() for future in as_completed(futures)]
```

## 📊 Performance Characteristics

### Current Bottlenecks

| Operation | Time | Bottleneck |
|-----------|------|-----------|
| Agent generation (6 agents) | ~60s | Fake async |
| RAG context fetch (6x) | ~3-5s | No indices |
| PDF export | ~10-30s | WeasyPrint CPU-bound |
| Knowledge store save | ~2s | SQLite write locks |

### Target Performance (v6.0)

| Operation | Current | Target | Improvement |
|-----------|---------|--------|-------------|
| Agent generation | 60s | 15-20s | 66% faster |
| RAG context fetch | 5s | 1-2s | 60% faster |
| Database queries | 500ms | 50ms | 90% faster |

## 🔐 Security Patterns

### 1. License Enforcement

**Pattern**: Hardware-bound licensing.

```python
# auth_manager.py
def check_license():
    hwid = get_machine_id()
    license_data = load_license_key()

    if not validate_license(hwid, license_data):
        abort(403, "Invalid license")
```

**Trigger**: Middleware on every request.

### 2. Multi-Tenancy Isolation

**Pattern**: User-scoped data access.

```python
@login_required
def get_plan(plan_id):
    plan = db.get_plan(plan_id)

    if plan.owner_id != current_user.id:
        abort(403)  # Cannot access other users' plans

    return plan
```

### 3. Webhook Signature Validation

**Pattern**: HMAC verification for n8n webhooks.

```python
@app.route("/webhook/n8n", methods=["POST"])
def n8n_webhook():
    signature = request.headers.get("X-API-Key")

    if signature != WEBHOOK_SECRET:
        abort(401)

    # Process webhook
```

## 🛠️ Development Patterns

### 1. Configuration Management

**Pattern**: Centralized config with environment overrides.

```python
# config.py
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
MODEL_CONFIG = ModelConfig(
    name="gemini-2.0-flash",
    temperature=0.7,
    max_tokens=8192
)

# Usage
from config import GEMINI_API_KEY, MODEL_CONFIG
```

### 2. Logging Standards

**Pattern**: Structured logging with context.

```python
import logging
logger = logging.getLogger(__name__)

# ✅ Good
logger.info(f"Agent {agent.spec.name} completed in {elapsed:.2f}s")
logger.error(f"Generation failed: {e}", exc_info=True)

# ❌ Bad
print("Done")  # Not logged
raise Exception(f"Error: {e}")  # No context
```

### 3. Error Handling Strategy

**Pattern**: Fail gracefully with fallbacks.

```python
try:
    response = model.generate_content(prompt)
except InvalidArgument as e:
    logger.warning(f"Tool error, retrying without tools: {e}")
    fallback_model = genai.GenerativeModel(MODEL_CONFIG.name)
    response = fallback_model.generate_content(prompt)
except Exception as e:
    logger.error(f"Generation failed: {e}")
    return {'content': 'Error generating content', 'sources': []}
```

## 📚 Module Dependencies

### Core Dependencies

```
agents.py
├─ config.py (MODEL_CONFIG, GEMINI_API_KEY)
├─ data_sourcing.py (SourcedContentGenerator)
├─ data_estimator.py (estimate_missing_financials)
└─ knowledge_store.py (SQLiteKnowledgeStore)

app.py
├─ agents.py (MultiAgentOrchestrator)
├─ structured_agent.py (StructuredOrchestrator)
├─ export_*.py (all exporters)
├─ knowledge_store.py
├─ auth_manager.py (login_required decorator)
└─ license_manager.py (check_license)
```

### External Dependencies (Critical)

- `google-generativeai==0.8.5` - Gemini API client
- `Flask==3.1.2` - Web framework
- `weasyprint==67.0` - PDF generation
- `python-docx==1.2.0` - DOCX generation
- `pytest==9.0.2` - Testing

## 🔄 Refactoring Opportunities

### High Priority

1. **Real Async** (OPT-002)
   - Replace `asyncio` with `ThreadPoolExecutor`
   - Impact: 66% generation time reduction

2. **SQLite Indexing** (OPT-001)
   - Add indices, enable WAL
   - Impact: 70% query speed improvement

3. **Export Unification** (OPT-003)
   - Create `BaseExporter` class
   - Impact: -500 LOC, easier maintenance

### Medium Priority

4. **Stratified Prompts** (OPT-004)
5. **Circuit Breaker** (OPT-005)
6. **Storage Layer Split** (OPT-006)

### Low Priority (Post-v6.0)

7. FastAPI migration
8. PostgreSQL + Redis
9. Celery task queue

---

**This document is living documentation. Update when patterns change.**

Last Updated: 2026-01-23
