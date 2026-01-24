# 🤖 Gemini CLI - Instructions for Rooting Future Development

## 📋 Setup & Context Loading

### Before Starting ANY Task

```bash
# 1. Navigate to project root
cd C:\Users\Mirko\Desktop\rooting_future

# 2. Activate virtual environment
.\venv\Scripts\Activate.ps1

# 3. Read context files (CRITICAL - DO THIS FIRST)
cat .dev\PROJECT.md       # Project overview
cat .dev\tasks.json       # Active tasks
cat docs\ARCHITECTURE.md  # Code patterns and gotchas
```

**Why this matters**: These files contain critical context about the codebase, known issues, and patterns to follow. Skipping this leads to breaking changes.

---

## 🎯 Task Execution Workflow

### Step 1: Select Task

```bash
# View active tasks
cat .dev\tasks.json | jq '.active[] | {id, title, priority, estimate}'
```

**Output Example**:
```json
{
  "id": "OPT-001",
  "title": "SQLite Indexing & WAL Mode",
  "priority": "high",
  "estimate": "1h"
}
```

### Step 2: Load Task Details

```bash
# Get full task specification
cat .dev\tasks.json | jq '.active[] | select(.id == "OPT-001")'
```

**This shows**:
- Description
- Files to modify
- Tasks breakdown
- Verification steps

### Step 3: Ask Gemini to Execute

**Template Prompt**:

```
I need you to implement task OPT-001 from .dev/tasks.json.

CONTEXT (READ THESE FIRST):
- .dev/PROJECT.md - Project overview and tech stack
- docs/ARCHITECTURE.md - Code patterns and gotchas
- .dev/tasks.json - Task specification

TASK: OPT-001 - SQLite Indexing & WAL Mode

FILES TO MODIFY:
- knowledge_store.py

IMPLEMENTATION STEPS:
1. Add CREATE INDEX on documents(category, section_type)
2. Add CREATE INDEX on plans(created_at DESC)
3. Enable PRAGMA journal_mode=WAL
4. Add PRAGMA synchronous=NORMAL
5. Test with 100 queries before/after

VERIFICATION:
- sqlite3 knowledge_base/rooting_future.db '.indices' shows new indices
- PRAGMA journal_mode returns 'wal'
- Query benchmark shows >60% improvement
- App starts without errors

CRITICAL RULES:
1. Read docs/ARCHITECTURE.md section on "SQLite Locking" before starting
2. Use type hints on all functions
3. Use logger (not print) for logging
4. Follow existing code style in knowledge_store.py
5. Test that app.py still starts after changes

Begin implementation now. Show me the changes you'll make to knowledge_store.py.
```

### Step 4: Review Changes

After Gemini proposes changes:

```bash
# View proposed diff
git diff knowledge_store.py

# Check syntax
python -m py_compile knowledge_store.py

# Test app starts
python app.py
# (Ctrl+C after you see "Running on http://127.0.0.1:5000")
```

### Step 5: Run Verification

```bash
# For OPT-001 example
sqlite3 knowledge_base\rooting_future.db ".indices"
# Should show: idx_documents_category_section, idx_plans_created

sqlite3 knowledge_base\rooting_future.db "PRAGMA journal_mode;"
# Should return: wal
```

### Step 6: Commit (If Passed)

```bash
git add knowledge_store.py
git commit -m "feat(OPT-001): add SQLite indexing and WAL mode

- Added index on documents(category, section_type)
- Added index on plans(created_at DESC)
- Enabled PRAGMA journal_mode=WAL
- Added PRAGMA synchronous=NORMAL
- Query performance improved by 70%

Closes OPT-001"
```

### Step 7: Update Task Status

```bash
# Mark task as done
# (Do this manually in .dev/tasks.json or ask Gemini to update it)
```

---

## 🛡️ CRITICAL RULES FOR GEMINI

### Always Do

✅ **Read context files BEFORE coding**
   - .dev/PROJECT.md
   - docs/ARCHITECTURE.md
   - .dev/tasks.json

✅ **Check existing patterns**
   ```bash
   # Example: How is logging done?
   grep -n "logger\." agents.py | head -5
   ```

✅ **Use type hints**
   ```python
   def get_plan(plan_id: str) -> Dict[str, Any]:
       pass
   ```

✅ **Follow imports structure**
   ```python
   # Standard library first
   import os
   from pathlib import Path

   # Third-party
   import google.generativeai as genai

   # Local
   from config import MODEL_CONFIG
   ```

✅ **Test before committing**
   ```bash
   python -m py_compile <file>
   python app.py  # Should start without errors
   ```

### Never Do

❌ **Don't use print() for output**
   ```python
   # ❌ Bad
   print("Starting generation")

   # ✅ Good
   logger.info("Starting generation")
   ```

❌ **Don't hardcode paths or keys**
   ```python
   # ❌ Bad
   api_key = "AIzaSyC..."

   # ✅ Good
   from config import GEMINI_API_KEY
   ```

❌ **Don't modify multiple unrelated files in one task**
   - Stick to files listed in task specification
   - If you need to modify others, ask first

❌ **Don't introduce new dependencies without approval**
   ```python
   # ❌ Bad
   import new_library  # Not in requirements.txt

   # ✅ Good - ask first
   # "Can I add library X? It solves Y problem."
   ```

❌ **Don't skip verification steps**
   - Every task has verification steps
   - Run ALL of them before claiming done

---

## 🔍 Common Operations

### Find Where Something Is Used

```bash
# Example: Where is MultiAgentOrchestrator used?
grep -r "MultiAgentOrchestrator" --include="*.py"
```

### Check Function Signature

```bash
# Example: How is generate_strategic_plan called?
grep -A 5 "def generate_strategic_plan" agents.py
```

### See Recent Changes

```bash
git log --oneline -10
git show <commit-hash>
```

### Test Specific Module

```bash
pytest tests/test_agents.py -v
pytest tests/test_knowledge_store.py::test_save_plan -v
```

---

## 🐛 Debugging Guide

### App Won't Start

```bash
# Check syntax errors
python -m py_compile app.py

# Check import errors
python -c "import agents; import knowledge_store"

# Check .env file exists
ls .env

# Check Python version
python --version  # Should be 3.11+
```

### Import Errors

```bash
# Verify virtual environment active
.\venv\Scripts\Activate.ps1

# Check installed packages
pip list | grep gemini
pip list | grep flask

# Reinstall if needed
pip install -r requirements.txt
```

### Database Locked Error

```bash
# Check if app is running
tasklist | findstr python

# Kill if needed
taskkill /F /IM python.exe

# Try again
python app.py
```

### Gemini API Errors

```bash
# Check API key set
echo $env:GOOGLE_API_KEY
# or
cat .env | grep GOOGLE_API_KEY

# Check quota
# (Go to Google AI Studio → Check usage)
```

---

## 📊 Task Complexity Guide

### Low Complexity (1-2 hours)
- **OPT-001**: SQLite indexing
  - Single file change
  - SQL statements only
  - No logic changes

### Medium Complexity (1-3 days)
- **OPT-002**: Real async execution
  - 2 files to modify
  - New class to create
  - Refactor existing methods
  - Requires testing

### High Complexity (3-5 days)
- **OPT-003**: Export layer unification
  - 7 files involved
  - New abstraction layer
  - Large refactor
  - Risk of breaking exports

**Recommendation**: Start with low complexity tasks to build confidence.

---

## 🎓 Learning from Codebase

### Understand Agent Pattern

```bash
# Read agent specifications
grep -A 20 "class AgentRole" agents.py

# See how agents are initialized
grep -A 30 "class StrategicAgent" agents.py

# Check system prompts
grep -A 50 "system_prompt=GLOBAL_VOICE_DIRECTIVE" agents.py
```

### Understand Export Pattern

```bash
# Compare two exporters
diff export_pdf_server.py export_html.py

# See common patterns (this will show duplication)
```

### Understand RAG Pattern

```bash
# How RAG context is fetched
grep -A 20 "get_context_for_generation" knowledge_store.py

# How it's used in agents
grep -B 5 -A 10 "rag_context" agents.py
```

---

## 💡 Pro Tips

### 1. Use Incremental Changes

Instead of:
```bash
# ❌ Change 5 things at once
```

Do:
```bash
# ✅ Change 1 thing, test, commit, repeat
git commit -m "step 1: add index on documents"
git commit -m "step 2: enable WAL mode"
git commit -m "step 3: add benchmark test"
```

### 2. Test in Isolation

```bash
# Create test script
cat > test_sqlite.py <<EOF
import sqlite3
conn = sqlite3.connect('knowledge_base/rooting_future.db')
cursor = conn.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
print(cursor.fetchall())
EOF

python test_sqlite.py
```

### 3. Use Comments for Complex Logic

```python
# ✅ Good - explain WHY not WHAT
# Use WAL mode for concurrent read/write support
# See: https://www.sqlite.org/wal.html
cursor.execute('PRAGMA journal_mode=WAL')
```

### 4. Check Performance Impact

```bash
# Before change
time python test_query.py

# After change
time python test_query.py

# Should be faster!
```

---

## 🤝 Handoff to Claude Code

If a task is too complex or you get stuck:

### Create Handoff Document

```bash
cat > .dev\handoff_OPT-002.md <<EOF
# Handoff: OPT-002 (Gemini → Claude)

## What I Did
- Created AsyncGeminiClient class in agents.py (lines 100-150)
- Added ThreadPoolExecutor with max_workers=6
- Updated _generate_parallel to use executor

## What's Left
- Add rate limiting (60 req/min)
- Add retry logic with exponential backoff
- Test with real generation (currently untested)
- Update structured_agent.py similarly

## Files Modified
- agents.py (in progress)

## Issues Encountered
- Not sure how to implement rate limiter
- Need to handle executor shutdown properly

## Next Steps
1. Implement RateLimiter class
2. Add to AsyncGeminiClient
3. Test with pytest
4. Update structured_agent.py

## Context for Claude
- Read docs/ARCHITECTURE.md section "Async/Await Confusion"
- See .dev/tasks.json for full OPT-002 spec
- My WIP code is on branch: feature/async-gemini
EOF
```

### Let Mirko know:
"Ho creato .dev/handoff_OPT-002.md. Passalo a Claude Code per continuare."

---

## 📚 Reference Commands

```bash
# Project structure
tree -L 2 -I 'venv|__pycache__|node_modules|dist|build'

# Find all Python files
find . -name "*.py" -not -path "./venv/*"

# Count lines of code
find . -name "*.py" -not -path "./venv/*" | xargs wc -l

# Search for TODOs
grep -r "TODO" --include="*.py"

# Check requirements
pip list --format=freeze > current_requirements.txt
diff requirements.txt current_requirements.txt
```

---

## ✅ Quick Checklist (Before Saying "Done")

- [ ] Read .dev/PROJECT.md, docs/ARCHITECTURE.md
- [ ] Implemented all steps from task specification
- [ ] Used type hints on new/modified functions
- [ ] Used logger (not print)
- [ ] Ran `python -m py_compile <file>` - no errors
- [ ] Ran `python app.py` - starts successfully
- [ ] Ran all verification steps from task
- [ ] Git commit with clear message
- [ ] Updated .dev/tasks.json (marked done: true)
- [ ] Logged learnings in .dev/progress.txt (if any)

---

## 🆘 When to Ask for Help

- ❓ Task specification unclear
- ❓ Found a pattern you don't understand
- ❓ Breaking change seems necessary
- ❓ Verification step failing consistently
- ❓ Need to modify files not listed in task
- ❓ Performance worse after change
- ❓ Complex refactor feels risky

**How to ask**:
```
"Ho un dubbio su OPT-002:

Problema: [describe]
Cosa ho provato: [list attempts]
Cosa dicono i docs: [reference ARCHITECTURE.md section]
Domanda specifica: [clear question]"
```

---

## 🎯 Success Metrics

After completing a task, you should be able to answer YES to:

1. ✅ Did I read all context files first?
2. ✅ Does the app still start?
3. ✅ Did I follow existing code patterns?
4. ✅ Did all verification steps pass?
5. ✅ Is the git commit message clear?
6. ✅ Could another developer understand my changes?

If any NO → revisit before marking done.

---

**Remember**: You're not just writing code, you're maintaining a production system. Quality > Speed.

---

## 📞 Support

- Project docs: .dev/PROJECT.md
- Architecture: docs/ARCHITECTURE.md
- Task list: .dev/tasks.json
- Progress log: .dev/progress.txt
- Git history: `git log --oneline -20`

**Happy coding! 🚀**
