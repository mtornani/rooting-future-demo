# 🎯 SPEC-DRIVEN DEVELOPMENT MIGRATION PLAN
## Rooting Future Strategy Engine v5.5 → v6.0

---

## 📋 EXECUTIVE SUMMARY

**Obiettivo**: Trasformare Rooting Future da sviluppo ad-hoc a **Spec-Driven Development** usando un framework multi-agente (Ralph + GSD + BMad concepts).

**Perché ora?**
1. Codebase maturo (~28k LOC) con debito tecnico identificato
2. Ottimizzazioni critiche mappate dall'audit (async, export unification, ecc.)
3. Team distribuito (Claude Code + Gemini CLI) che necessita coordinamento
4. Necessità di scaling (multi-tenant, horizontal scaling)

**Outcome atteso**:
- Sistema di sviluppo autonomo orchestrato
- Context rot eliminato (fresh agent spawns)
- Qualità consistente attraverso verification loops
- Git history atomico e tracciabile
- Documentation auto-generated

---

## 🏗️ ARCHITETTURA PROPOSTA

### Hybrid Framework: "Rooting Spec Engine" (RSE)

```
┌─────────────────────────────────────────────────────┐
│         ROOTING SPEC ENGINE (RSE) v1.0              │
├─────────────────────────────────────────────────────┤
│                                                     │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────┐ │
│  │   Ralph     │  │     GSD      │  │   BMad    │ │
│  │  (Loop)     │  │ (Context)    │  │ (Agents)  │ │
│  └─────────────┘  └──────────────┘  └───────────┘ │
│         │                │                │        │
│         └────────────────┴────────────────┘        │
│                          │                         │
│              ┌───────────▼──────────┐              │
│              │   RSE Orchestrator    │              │
│              └───────────┬──────────┘              │
│                          │                         │
│         ┌────────────────┼────────────────┐        │
│         │                │                │        │
│    ┌────▼─────┐    ┌────▼────┐    ┌─────▼────┐   │
│    │ Claude   │    │  Gemini │    │  Shared  │   │
│    │  Code    │    │   CLI   │    │   State  │   │
│    └──────────┘    └─────────┘    └──────────┘   │
│                                                     │
└─────────────────────────────────────────────────────┘
```

### Componenti Chiave

#### 1. **Ralph Loop** (Autonomia)
- Orchestrazione ciclo iterativo
- Fresh context per ogni task
- Max iterations configurable
- Auto-commit per task atomico

#### 2. **GSD Context Engineering** (Qualità)
- PROJECT.md, STATE.md, ROADMAP.md
- XML-structured plans
- Verification loops
- Size limits anti-context-rot

#### 3. **BMad Agents** (Specializzazione)
- 21 agent specializzati adattati al dominio Rooting Future
- Scale-adaptive (Level 0-4 based on complexity)
- Workflow-guided (non solo generazione codice)

---

## 📁 STRUTTURA FILE SYSTEM PROPOSTA

```
rooting_future/
├── .rse/                           # Rooting Spec Engine root
│   ├── config.json                 # RSE configuration
│   ├── PROJECT.md                  # Vision, goals, tech stack
│   ├── STATE.md                    # Current position, decisions, blockers
│   ├── ROADMAP.md                  # Milestones and phases
│   └── AGENTS.md                   # Codebase learnings for AI
│
├── specs/                          # PRDs and specifications
│   ├── current/                    # Active milestone
│   │   ├── prd.json               # Structured user stories (Ralph format)
│   │   ├── REQUIREMENTS.md        # Scoped requirements
│   │   └── phases/                # Per-phase specs
│   │       ├── 01-async-refactor/
│   │       │   ├── CONTEXT.md     # Implementation decisions
│   │       │   ├── RESEARCH.md    # Investigation findings
│   │       │   ├── PLAN-01.md     # Task 1: ThreadPoolExecutor
│   │       │   ├── PLAN-02.md     # Task 2: Gemini async wrapper
│   │       │   ├── SUMMARY-01.md  # What was done
│   │       │   └── VERIFICATION.md# Phase verification
│   │       └── 02-export-unification/
│   │           └── ...
│   └── archive/                   # Completed milestones
│       └── v5.5-optimization/
│
├── .rse/progress.txt              # Append-only learnings (Ralph)
├── .rse/todos.md                  # Captured ideas (GSD)
│
├── agents/                        # RSE Agent definitions
│   ├── pm.md                      # Product Manager agent
│   ├── architect.md               # Software Architect agent
│   ├── developer.md               # Senior Developer agent
│   ├── qa.md                      # QA Engineer agent
│   └── devops.md                  # DevOps Engineer agent
│
├── scripts/
│   ├── rse/                       # RSE scripts
│   │   ├── rse.sh                # Main orchestrator loop
│   │   ├── spawn_agent.sh        # Spawn fresh AI instance
│   │   ├── verify_task.sh        # Run verification checks
│   │   └── commit_task.sh        # Atomic git commit
│   └── ...
│
├── [existing codebase]
│   ├── app.py
│   ├── agents.py
│   └── ...
│
└── README.md                      # Updated with RSE workflow
```

---

## 🚀 PHASE 1: FOUNDATION (Week 1)

### 1.1 Initialize RSE Structure

**Tasks:**
- [ ] Create `.rse/` directory structure
- [ ] Generate initial `PROJECT.md` (automated scan of codebase)
- [ ] Create `ROADMAP.md` from audit findings (Tier 1/2/3 priorities)
- [ ] Initialize `prd.json` con primi 3 epic dal Tier 1

**Tool**: Script `scripts/rse/init_rse.py`

```python
# scripts/rse/init_rse.py
"""
Initialize Rooting Spec Engine for existing project
"""
def scan_codebase():
    """Scan project and generate PROJECT.md"""
    # Analyze:
    # - Tech stack (requirements.txt)
    # - Architecture (main modules)
    # - Conventions (existing patterns)
    # - Current issues (TODOs, FIXMEs)

def generate_roadmap_from_audit():
    """Convert audit findings to ROADMAP.md"""
    # Read: AUDIT_TECNICO_COMMERCIALIZZAZIONE.md
    # Extract: Tier 1/2/3 priorities
    # Format: BMad-style milestones with phases

def create_initial_prd():
    """Create prd.json for first 3 Tier 1 tasks"""
    # Task 1: Real async (ThreadPoolExecutor)
    # Task 2: Export unification (BaseExporter)
    # Task 3: SQLite indexing
```

---

### 1.2 Agent Definitions

**Crea 5 agenti core** adattati al dominio Rooting Future:

#### `agents/pm.md` - Product Manager
```markdown
# Product Manager Agent

## Role
Strategic product decisions for Rooting Future platform.

## Expertise
- SaaS business model (credit system, licensing)
- Soccer club management domain
- Sport To Win (STW) methodology
- Competitor analysis (SportEasy, TeamSnap, etc.)

## Responsibilities
- Define user stories from stakeholder needs
- Prioritize backlog (business value vs technical debt)
- Acceptance criteria definition
- Scope management (v1/v2/v3)

## Context Awareness
- Target users: Società calcistiche dilettantistiche
- Key metric: Time-to-strategic-plan (target: <60s)
- Monetization: Credit-based + licensing
```

#### `agents/architect.md` - Software Architect
```markdown
# Software Architect Agent

## Role
System design and architectural decisions.

## Expertise
- Multi-agent AI systems (Gemini 2.0)
- Flask → FastAPI migration patterns
- SQLite → PostgreSQL migration
- RAG systems (File Search, embeddings)
- Async Python (asyncio, ThreadPoolExecutor)

## Responsibilities
- Design phase architecture
- Technology selection (libraries, frameworks)
- Identify dependencies between tasks
- Performance considerations
- Scalability planning

## Known Patterns (Rooting Future)
- 6 STW specialized agents + coordinator
- AICache system (file-based)
- KnowledgeStore (SQLite with WAL mode)
- Export layer: WeasyPrint for PDF, python-docx for DOCX
```

#### `agents/developer.md` - Senior Developer
```markdown
# Senior Developer Agent

## Role
Implementation and code quality.

## Expertise
- Python 3.11+ (type hints, dataclasses)
- Flask 3.x (blueprints, context)
- Gemini SDK (google-generativeai, google-genai)
- Async patterns (asyncio, concurrent.futures)
- Testing (pytest, unittest)

## Responsibilities
- Write clean, tested code
- Follow existing patterns
- Create atomic commits
- Update AGENTS.md with learnings
- Run verification checks

## Code Style (Rooting Future)
- Type hints on all function signatures
- Docstrings for public methods
- Logger usage (not print)
- Config via config.py (no hardcoded paths)
```

#### `agents/qa.md` - QA Engineer
```markdown
# QA Engineer Agent

## Role
Quality assurance and verification.

## Responsibilities
- Define verification steps per task
- Run automated checks (typecheck, tests)
- Browser verification for UI changes
- Load testing for performance tasks
- Create bug reports if issues found

## Verification Checklist (Rooting Future)
1. Code compiles: `python -m py_compile {files}`
2. Tests pass: `pytest tests/ -v`
3. Lint clean: `flake8 {files}` (if configured)
4. App starts: `python app.py` (no crash)
5. API functional: curl tests for endpoints
```

#### `agents/devops.md` - DevOps Engineer
```markdown
# DevOps Engineer Agent

## Role
Deployment, infrastructure, CI/CD.

## Responsibilities
- Docker configuration
- Environment setup (.env management)
- Database migrations
- Build scripts (Nuitka compilation)
- Deployment automation

## Current Stack (Rooting Future)
- Server: Waitress (production), Flask dev server
- Database: SQLite (local), PostgreSQL (future)
- Build: Nuitka for Windows executable
- Deploy: VPS with PM2 (ecosystem.config.js)
```

---

### 1.3 RSE Orchestrator Script

**File**: `scripts/rse/rse.sh`

```bash
#!/bin/bash
# Rooting Spec Engine - Main orchestrator loop

MAX_ITERATIONS=${1:-10}
TOOL=${2:-claude}  # claude or gemini
ITERATION=0

echo "🚀 Rooting Spec Engine v1.0"
echo "   Tool: $TOOL"
echo "   Max iterations: $MAX_ITERATIONS"
echo ""

while [ $ITERATION -lt $MAX_ITERATIONS ]; do
    ITERATION=$((ITERATION + 1))
    echo "═══════════════════════════════════════"
    echo "   ITERATION $ITERATION/$MAX_ITERATIONS"
    echo "═══════════════════════════════════════"

    # 1. Read current state
    CURRENT_PHASE=$(jq -r '.currentPhase' .rse/STATE.json)
    NEXT_TASK=$(jq -r '.userStories[] | select(.passes == false) | .id' specs/current/prd.json | head -1)

    if [ -z "$NEXT_TASK" ]; then
        echo "✅ All tasks completed!"
        echo "<promise>COMPLETE</promise>"
        exit 0
    fi

    echo "📋 Next task: $NEXT_TASK"

    # 2. Spawn fresh AI agent with context
    ./scripts/rse/spawn_agent.sh "$TOOL" "$NEXT_TASK"

    # 3. Verify task
    ./scripts/rse/verify_task.sh "$NEXT_TASK"
    VERIFY_STATUS=$?

    if [ $VERIFY_STATUS -eq 0 ]; then
        echo "✅ Task $NEXT_TASK passed verification"

        # 4. Commit atomically
        ./scripts/rse/commit_task.sh "$NEXT_TASK"

        # 5. Update prd.json
        jq "(.userStories[] | select(.id == \"$NEXT_TASK\") | .passes) = true" \
            specs/current/prd.json > specs/current/prd.json.tmp
        mv specs/current/prd.json.tmp specs/current/prd.json

        # 6. Append learnings
        echo "[$ITERATION] Completed $NEXT_TASK" >> .rse/progress.txt
    else
        echo "❌ Task $NEXT_TASK failed verification"
        echo "[$ITERATION] FAILED $NEXT_TASK - see logs" >> .rse/progress.txt

        # Optional: auto-retry or break
        read -p "Retry? (y/n): " RETRY
        if [ "$RETRY" != "y" ]; then
            exit 1
        fi
    fi

    echo ""
done

echo "⏱️  Max iterations reached. Current progress:"
jq -r '.userStories[] | "\(.id): \(.passes)"' specs/current/prd.json
```

---

### 1.4 Agent Spawner

**File**: `scripts/rse/spawn_agent.sh`

```bash
#!/bin/bash
# Spawn fresh AI agent with context for task

TOOL=$1      # claude or gemini
TASK_ID=$2

# Load task details
TASK_TITLE=$(jq -r ".userStories[] | select(.id == \"$TASK_ID\") | .title" specs/current/prd.json)
TASK_DESC=$(jq -r ".userStories[] | select(.id == \"$TASK_ID\") | .description" specs/current/prd.json)
TASK_PLAN=$(jq -r ".userStories[] | select(.id == \"$TASK_ID\") | .plan" specs/current/prd.json)

# Build prompt with context
PROMPT="# TASK: $TASK_TITLE

## Description
$TASK_DESC

## Plan
$TASK_PLAN

## Context Files (Read Before Starting)
- .rse/PROJECT.md - Project overview
- .rse/STATE.md - Current position
- .rse/AGENTS.md - Codebase learnings
- .rse/progress.txt - Previous iterations

## Your Role
You are a Senior Developer implementing this task atomically.

## Requirements
1. Read all context files first
2. Implement according to plan
3. Follow code style in agents/developer.md
4. Run verification checks
5. Update AGENTS.md if you discover new patterns
6. Create atomic commit with message: 'feat($TASK_ID): $TASK_TITLE'

## Verification Steps
$(jq -r ".userStories[] | select(.id == \"$TASK_ID\") | .verification[]" specs/current/prd.json)

Begin implementation now.
"

# Spawn agent based on tool
if [ "$TOOL" == "claude" ]; then
    echo "$PROMPT" | claude --dangerously-skip-permissions
elif [ "$TOOL" == "gemini" ]; then
    echo "$PROMPT" | gemini
else
    echo "Unknown tool: $TOOL"
    exit 1
fi
```

---

## 🎯 PHASE 2: FIRST MILESTONE (Week 2-3)

### 2.1 Create PRD for Tier 1 Optimizations

**File**: `specs/current/prd.json`

```json
{
  "milestone": "v6.0-performance-foundation",
  "branchName": "feature/v6-performance",
  "currentPhase": 1,
  "userStories": [
    {
      "id": "PERF-001",
      "title": "Real Async Execution with ThreadPoolExecutor",
      "description": "Replace fake asyncio.gather() with real parallel execution using ThreadPoolExecutor",
      "priority": 1,
      "complexity": "medium",
      "passes": false,
      "files": [
        "agents.py",
        "structured_agent.py"
      ],
      "plan": "1. Create AsyncGeminiClient wrapper with ThreadPoolExecutor\n2. Update MultiAgentOrchestrator._generate_parallel to use real parallelism\n3. Remove fake asyncio code\n4. Add rate limiting logic\n5. Add retry mechanism with exponential backoff",
      "verification": [
        "python -m py_compile agents.py structured_agent.py",
        "pytest tests/test_agents.py -v",
        "Time measurement: 6 agents should complete in <20s (vs current 60s)"
      ],
      "acceptanceCriteria": [
        "6 agents execute in real parallel",
        "Generation time reduced by >60%",
        "No asyncio.gather() remains",
        "Rate limiting prevents API overload"
      ]
    },
    {
      "id": "PERF-002",
      "title": "Unify Export Layer with BaseExporter",
      "description": "Consolidate 6 export modules into single base class with inheritance",
      "priority": 1,
      "complexity": "high",
      "passes": false,
      "dependencies": [],
      "files": [
        "export_pdf_server.py",
        "export_html.py",
        "export_docx.py",
        "export_paged.py",
        "export_onepager.py",
        "export_package.py",
        "export_core.py (NEW)"
      ],
      "plan": "1. Create export_core.py with BaseExporter abstract class\n2. Extract common methods: _apply_branding, _add_methodology, _prepare_content\n3. Refactor PDFExporter to inherit from BaseExporter\n4. Migrate other exporters one by one\n5. Verify all exports still work\n6. Remove duplicated code",
      "verification": [
        "pytest tests/test_exports.py -v",
        "Generate test plan with all 6 formats - verify all succeed",
        "Line count reduction: should remove >500 LOC"
      ],
      "acceptanceCriteria": [
        "All 6 export formats functional",
        "Code duplication eliminated",
        "Single source of truth for branding",
        "-500 LOC achieved"
      ]
    },
    {
      "id": "PERF-003",
      "title": "SQLite Indexing and WAL Mode",
      "description": "Add database indices and enable Write-Ahead Logging for performance",
      "priority": 1,
      "complexity": "low",
      "passes": false,
      "files": [
        "knowledge_store.py"
      ],
      "plan": "1. Add CREATE INDEX statements in _init_db()\n2. Index: (category, section_type) for documents table\n3. Index: (created_at DESC) for plans table\n4. Enable PRAGMA journal_mode=WAL\n5. Add PRAGMA synchronous=NORMAL for performance\n6. Run benchmark: 100 queries before/after",
      "verification": [
        "sqlite3 knowledge_base/rooting_future.db '.indices' | grep idx_",
        "pytest tests/test_knowledge_store.py -v",
        "Benchmark: Query time should reduce by >60%"
      ],
      "acceptanceCriteria": [
        "Indices created successfully",
        "WAL mode enabled",
        "Query performance +70%",
        "Concurrent read/write supported"
      ]
    }
  ]
}
```

---

### 2.2 Execute First Milestone

```bash
# Initialize RSE
python scripts/rse/init_rse.py

# Create feature branch
git checkout -b feature/v6-performance

# Run RSE loop
./scripts/rse/rse.sh 10 claude

# Or with Gemini CLI
./scripts/rse/rse.sh 10 gemini
```

**Expected Output:**
```
🚀 Rooting Spec Engine v1.0
   Tool: claude
   Max iterations: 10

═══════════════════════════════════════
   ITERATION 1/10
═══════════════════════════════════════
📋 Next task: PERF-001
✅ Task PERF-001 passed verification
[1] Completed PERF-001

═══════════════════════════════════════
   ITERATION 2/10
═══════════════════════════════════════
📋 Next task: PERF-002
✅ Task PERF-002 passed verification
[2] Completed PERF-002

═══════════════════════════════════════
   ITERATION 3/10
═══════════════════════════════════════
📋 Next task: PERF-003
✅ Task PERF-003 passed verification
[3] Completed PERF-003

✅ All tasks completed!
<promise>COMPLETE</promise>
```

---

## 🔄 PHASE 3: DUAL-AGENT COLLABORATION (Week 4)

### 3.1 Claude Code + Gemini CLI Handoff Protocol

**Scenario**: Task troppo complesso per single agent → split tra Claude (architecture) e Gemini (implementation)

**File**: `scripts/rse/handoff.sh`

```bash
#!/bin/bash
# Handoff protocol between Claude and Gemini

TASK_ID=$1
FROM_TOOL=$2  # claude or gemini
TO_TOOL=$3    # gemini or claude

echo "🔄 HANDOFF: $FROM_TOOL → $TO_TOOL for task $TASK_ID"

# 1. Export current state from FROM_TOOL
./scripts/rse/export_state.sh "$FROM_TOOL" "$TASK_ID"

# 2. Create handoff document
HANDOFF_DOC=".rse/handoffs/${TASK_ID}_${FROM_TOOL}_to_${TO_TOOL}.md"
cat > "$HANDOFF_DOC" <<EOF
# Handoff: $TASK_ID
## From: $FROM_TOOL
## To: $TO_TOOL
## Date: $(date)

## Work Completed
$(jq -r ".userStories[] | select(.id == \"$TASK_ID\") | .progress" specs/current/prd.json)

## Next Steps
$(jq -r ".userStories[] | select(.id == \"$TASK_ID\") | .nextSteps" specs/current/prd.json)

## Files Modified
$(git diff --name-only)

## Context for $TO_TOOL
- Read: .rse/AGENTS.md for codebase patterns
- Read: $HANDOFF_DOC for work completed
- Continue from "Next Steps" above
EOF

echo "📄 Handoff document: $HANDOFF_DOC"

# 3. Spawn TO_TOOL with handoff context
./scripts/rse/spawn_agent.sh "$TO_TOOL" "$TASK_ID" --handoff "$HANDOFF_DOC"
```

**Use Case Example:**

```bash
# Claude designs architecture
./scripts/rse/spawn_agent.sh claude ARCH-001

# Claude realizes implementation is tedious → handoff to Gemini
./scripts/rse/handoff.sh ARCH-001 claude gemini

# Gemini implements based on Claude's design
# Gemini finishes → handoff back to Claude for verification
./scripts/rse/handoff.sh ARCH-001 gemini claude
```

---

## 📊 PHASE 4: METRICS & OBSERVABILITY (Week 5)

### 4.1 RSE Dashboard

**File**: `scripts/rse/dashboard.py`

```python
"""
RSE Dashboard - Track progress, quality, and velocity
"""
import json
from pathlib import Path
from datetime import datetime

def generate_dashboard():
    """Generate HTML dashboard from RSE state"""

    # Load data
    prd = json.loads(Path('specs/current/prd.json').read_text())
    state = json.loads(Path('.rse/STATE.json').read_text())
    progress = Path('.rse/progress.txt').read_text().splitlines()

    # Calculate metrics
    total_stories = len(prd['userStories'])
    completed_stories = len([s for s in prd['userStories'] if s['passes']])
    completion_rate = (completed_stories / total_stories) * 100

    # Git stats
    commits = subprocess.run(
        ['git', 'log', '--oneline', '--grep', 'feat('],
        capture_output=True, text=True
    ).stdout.splitlines()

    # Generate HTML
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>RSE Dashboard - Rooting Future</title>
        <style>
            body {{ font-family: system-ui; margin: 40px; }}
            .metric {{ display: inline-block; margin: 20px; padding: 20px;
                      background: #f0f0f0; border-radius: 8px; }}
            .metric h2 {{ margin: 0; font-size: 3em; }}
            .metric p {{ margin: 5px 0 0 0; color: #666; }}
            .progress {{ width: 100%; height: 40px; background: #e0e0e0;
                        border-radius: 20px; overflow: hidden; }}
            .progress-bar {{ height: 100%; background: #6B46C1;
                            transition: width 0.3s; }}
        </style>
    </head>
    <body>
        <h1>🎯 RSE Dashboard - Rooting Future v6.0</h1>

        <div class="metric">
            <h2>{completion_rate:.0f}%</h2>
            <p>Milestone Progress</p>
        </div>

        <div class="metric">
            <h2>{completed_stories}/{total_stories}</h2>
            <p>Stories Completed</p>
        </div>

        <div class="metric">
            <h2>{len(commits)}</h2>
            <p>Atomic Commits</p>
        </div>

        <div class="metric">
            <h2>{len(progress)}</h2>
            <p>Iterations</p>
        </div>

        <h2>Progress</h2>
        <div class="progress">
            <div class="progress-bar" style="width: {completion_rate}%"></div>
        </div>

        <h2>Recent Activity</h2>
        <ul>
            {''.join(f'<li>{line}</li>' for line in progress[-10:])}
        </ul>
    </body>
    </html>
    """

    Path('.rse/dashboard.html').write_text(html)
    print("✅ Dashboard generated: .rse/dashboard.html")

if __name__ == '__main__':
    generate_dashboard()
```

---

## 🎓 LEARNING SYSTEM

### 5.1 AGENTS.md Auto-Update

**Hook**: `scripts/rse/hooks/post-commit`

```bash
#!/bin/bash
# Post-commit hook: Extract learnings and update AGENTS.md

COMMIT_MSG=$(git log -1 --pretty=%B)

# Check if feat commit
if [[ $COMMIT_MSG == feat* ]]; then
    # Extract task ID
    TASK_ID=$(echo "$COMMIT_MSG" | grep -oP 'feat\(\K[^)]+')

    # Prompt AI to update AGENTS.md
    python scripts/rse/update_agents_md.py "$TASK_ID"
fi
```

**Script**: `scripts/rse/update_agents_md.py`

```python
"""
Update AGENTS.md with learnings from completed task
"""
import sys
import subprocess

def update_agents_md(task_id: str):
    """Spawn AI to analyze git diff and update AGENTS.md"""

    # Get files changed
    diff = subprocess.run(
        ['git', 'diff', 'HEAD~1', 'HEAD'],
        capture_output=True, text=True
    ).stdout

    prompt = f"""
# Task: Update AGENTS.md with learnings from {task_id}

## Git Diff
{diff}

## Instructions
Analyze the changes and identify:
1. New patterns introduced (if any)
2. Gotchas discovered (if any)
3. Dependencies/libraries used
4. Performance considerations
5. Testing approaches

Append to .rse/AGENTS.md in this format:

### [{task_id}] {title}
- Pattern: [describe pattern]
- Gotcha: [describe gotcha]
- Dependencies: [list new dependencies]

Keep it concise. Only add if truly valuable for future iterations.
"""

    # Spawn AI (Claude preferred for documentation)
    subprocess.run(['claude', '--dangerously-skip-permissions'], input=prompt, text=True)

if __name__ == '__main__':
    task_id = sys.argv[1]
    update_agents_md(task_id)
```

---

## 📚 DOCUMENTATION AUTO-GENERATION

### 6.1 Phase Summary Generator

**File**: `scripts/rse/generate_summary.py`

```python
"""
Generate phase summary after completion
"""
def generate_phase_summary(phase_num: int):
    """AI-generated summary of what was accomplished"""

    # Read phase plans
    phase_dir = Path(f'specs/current/phases/{phase_num:02d}-*')
    plans = list(phase_dir.glob('PLAN-*.md'))
    summaries = list(phase_dir.glob('SUMMARY-*.md'))

    # Get git commits for this phase
    commits = subprocess.run(
        ['git', 'log', '--oneline', '--grep', f'feat({phase_num:02d}-'],
        capture_output=True, text=True
    ).stdout

    prompt = f"""
# Generate Phase {phase_num} Summary

## Plans Executed
{[p.read_text() for p in plans]}

## Task Summaries
{[s.read_text() for s in summaries]}

## Git Commits
{commits}

## Instructions
Create a comprehensive phase summary with:
1. **Overview**: What was this phase about?
2. **Key Changes**: What files were modified and why?
3. **Challenges**: Any unexpected issues?
4. **Metrics**: Performance improvements, LOC changes, etc.
5. **Next Steps**: What this enables for future phases

Write in Markdown. Be concise but complete.
"""

    # Spawn AI
    result = subprocess.run(
        ['claude', '--dangerously-skip-permissions'],
        input=prompt, text=True, capture_output=True
    )

    # Save summary
    summary_path = phase_dir / 'PHASE_SUMMARY.md'
    summary_path.write_text(result.stdout)

    print(f"✅ Phase summary: {summary_path}")
```

---

## 🔮 ROADMAP COMPLETO

### Milestone 1: Foundation (Week 1)
- [x] RSE structure initialization
- [x] Agent definitions (5 core agents)
- [x] Orchestrator script (rse.sh)
- [x] First PRD (Tier 1 optimizations)

### Milestone 2: First Wins (Week 2-3)
- [ ] Execute PERF-001 (Real async)
- [ ] Execute PERF-002 (Export unification)
- [ ] Execute PERF-003 (SQLite indexing)
- [ ] Measure ROI: performance gains

### Milestone 3: Dual-Agent Workflow (Week 4)
- [ ] Handoff protocol (Claude ↔ Gemini)
- [ ] Test complex task split
- [ ] Document collaboration patterns

### Milestone 4: Observability (Week 5)
- [ ] RSE Dashboard
- [ ] Metrics tracking
- [ ] Quality gates
- [ ] Learning system (AGENTS.md auto-update)

### Milestone 5: Scale Testing (Week 6)
- [ ] Tier 2 optimization (FastAPI migration)
- [ ] Multi-phase execution
- [ ] Verification loops
- [ ] Documentation auto-generation

### Milestone 6: Production Ready (Week 7-8)
- [ ] CI/CD integration
- [ ] Multi-tenant support planning
- [ ] Horizontal scaling preparation
- [ ] Full Tier 3 execution

---

## 🎯 SUCCESS METRICS

### Quantitative
| Metric | Baseline | Target | Measurement |
|--------|----------|--------|-------------|
| Generation time | 60s | <20s | Timer in orchestrator |
| Code duplication | High | -500 LOC | `cloc` before/after |
| Query performance | Slow | +70% | Benchmark script |
| Context rot | Frequent | Eliminated | Fresh spawns |
| Commit atomicity | Mixed | 100% | Git log analysis |

### Qualitative
- [ ] Consistent code quality across iterations
- [ ] Clear git history (bisect-friendly)
- [ ] Self-documenting (AGENTS.md grows)
- [ ] Onboarding new dev in <1 hour (read docs only)
- [ ] Handoff between Claude/Gemini seamless

---

## 🚀 GETTING STARTED NOW

### Immediate Action (Next 30 Minutes)

```bash
# 1. Create RSE structure
mkdir -p .rse specs/current agents scripts/rse

# 2. Initialize PROJECT.md
cat > .rse/PROJECT.md <<EOF
# Rooting Future Strategy Engine

## Vision
AI-powered strategic planning system for soccer clubs worldwide.

## Tech Stack
- Backend: Flask 3.x → FastAPI (planned)
- AI: Gemini 2.0 Flash (6 specialized agents)
- Database: SQLite → PostgreSQL (planned)
- Export: WeasyPrint (PDF), python-docx (DOCX)

## Architecture
Multi-agent orchestrator with RAG learning (File Search Store).

## Current State
v5.5 - Stable, production-ready
v6.0 - Performance optimization in progress

## Key Constraints
- Generation time target: <60s
- Mobile-friendly output required
- Multi-tenant ready (future)
EOF

# 3. Create first PRD
cp specs/current/prd.json.example specs/current/prd.json
# Edit with your tasks

# 4. Test orchestrator
./scripts/rse/rse.sh 1 claude  # Single iteration test
```

---

## 💬 QUESTIONS TO ANSWER

Visto l'approccio proposto, vorrei feedback su:

1. **Tool preference**: Preferisci iniziare con Claude Code, Gemini CLI, o entrambi da subito?

2. **Complexity level**: Preferisci:
   - **Quick Start**: Solo Ralph loop + basic verification
   - **Standard**: Ralph + GSD context engineering
   - **Full**: Ralph + GSD + BMad agents (come proposto)

3. **First task**: Quale task Tier 1 vuoi tacklear per primo?
   - PERF-001 (Async refactor) - Impact più alto
   - PERF-003 (SQLite indexing) - Win più rapido (1 ora)
   - PERF-002 (Export unification) - Refactoring più grande

4. **Agent specialization**: Servono agent domain-specific (es. "STW Methodology Agent", "Soccer Domain Expert") o bastano i 5 core?

5. **Git workflow**: Vuoi:
   - Feature branch per milestone completo
   - Branch per ogni phase
   - Trunk-based con feature flags

---

## 📖 RIFERIMENTI

- **Ralph Pattern**: https://github.com/geoffreyhuntley/ralph
- **GSD**: https://github.com/taches-ai/get-shit-done-cc
- **BMad**: https://github.com/bmad-code-org/BMAD-METHOD
- **Audit Rooting Future**: `AUDIT_TECNICO_COMMERCIALIZZAZIONE.md` (questo repo)

---

**Ready to start? Let's build the Rooting Spec Engine! 🚀**
