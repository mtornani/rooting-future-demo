# Rooting Future - Roadmap to Alpha Release
## Da Refactoring a Prodotto Distribuibile

**Goal:** Zero errori runtime + UX professionale + Build distribuibile

---

## 📊 Stato Attuale (Post REF-006)

```
✅ Codebase pulito (~20k LOC, -50%)
✅ Performance ottimizzate (OPT-001, OPT-002, OPT-003)
✅ Architettura modulare (REF-001 → REF-006)

⚠️ Mancano ancora:
- Testing automatico (0% coverage)
- Error handling robusto
- Validazione input utente
- Logging strutturato
- UI/UX polish
- Build process affidabile
```

---

## 🎯 Roadmap Post-Refactoring

### **PHASE 1: Stabilità & Zero Errori** (1-2 settimane)

#### STAB-001: Test Suite Foundation
**Priority:** CRITICAL | **Estimate:** 3-4 giorni

```python
# Spec: Pytest test suite con >60% coverage

tests/
├── test_agents.py              # Multi-agent orchestration
├── test_export.py              # PDF/DOCX/HTML generation
├── test_ingestion.py           # Stakeholder DOCX parsing
├── test_knowledge_store.py     # Database operations
├── test_web_research.py        # API mocking
└── test_integration.py         # End-to-end flow

# Target coverage:
- Core business logic: >80%
- API endpoints: >70%
- Overall: >60%

# Verification:
pytest --cov=. --cov-report=html
# Generate coverage report
# Fix failing tests until green
```

**Benefits:**
- Catch bugs BEFORE users see them
- Safe refactoring (tests catch regressions)
- Confidence in releases

---

#### STAB-002: Robust Error Handling
**Priority:** CRITICAL | **Estimate:** 2 giorni

```python
# Spec: Try-catch every external call

# File: domain/error_handling.py
class RootingFutureException(Exception):
    """Base exception with user-friendly messages"""
    pass

class GeminiAPIError(RootingFutureException):
    """Gemini API failures"""
    user_message = "Servizio AI temporaneamente non disponibile"

class PDFGenerationError(RootingFutureException):
    """PDF export failures"""
    user_message = "Errore nella generazione PDF"

class StakeholderParsingError(RootingFutureException):
    """DOCX parsing failures"""
    user_message = "File DOCX non valido o corrotto"

# Usage in routes:
try:
    result = orchestrator.generate_strategic_plan(...)
except GeminiAPIError as e:
    logger.exception("Gemini failure")
    return jsonify({
        "success": False,
        "error": e.user_message,
        "support_code": str(uuid.uuid4())[:8]
    }), 503
```

**What to wrap:**
- ✅ Gemini API calls (rate limits, timeouts)
- ✅ PDF generation (WeasyPrint crashes)
- ✅ DOCX parsing (corrupted files)
- ✅ File uploads (size limits, formats)
- ✅ Database writes (disk full, locks)
- ✅ Web research (network failures)

**Result:** App NEVER crashes, always returns useful error

---

#### STAB-003: Input Validation Layer
**Priority:** HIGH | **Estimate:** 2 giorni

```python
# Spec: Validate ALL user inputs

# File: api/validators.py
from pydantic import BaseModel, validator

class GeneratePlanRequest(BaseModel):
    club_name: str
    city: str
    country: str
    category: str

    @validator('club_name')
    def validate_club_name(cls, v):
        if len(v) < 3:
            raise ValueError("Nome club troppo corto")
        if len(v) > 100:
            raise ValueError("Nome club troppo lungo")
        return v.strip()

    @validator('country')
    def validate_country(cls, v):
        allowed = ['Italy', 'Spain', 'Germany', ...]
        if v not in allowed:
            raise ValueError("Paese non supportato")
        return v

# Usage:
@app.route("/api/generate", methods=["POST"])
def api_generate():
    try:
        data = GeneratePlanRequest(**request.json)
    except ValidationError as e:
        return jsonify({"error": str(e)}), 400
    # Proceed with validated data
```

**What to validate:**
- File uploads (size < 10MB, format DOCX/ZIP only)
- Club names (length, charset)
- Dates (foundation_year 1800-2024)
- Colors (valid hex codes)
- Emails (if licensing)

**Result:** Garbage input rejected BEFORE processing

---

#### STAB-004: Structured Logging
**Priority:** MEDIUM | **Estimate:** 1 giorno

```python
# Spec: JSON structured logs for debugging

# File: utils/logging_config.py
import structlog

logger = structlog.get_logger()

# Usage:
logger.info(
    "plan_generated",
    plan_id=plan_id,
    club_name=club_name,
    duration_seconds=duration,
    agent_count=6,
    stakeholder_count=len(stakeholders)
)

# Output (JSON):
{
    "event": "plan_generated",
    "plan_id": "plan_107bcc_20260124181959",
    "club_name": "AC Riccione 1926",
    "duration_seconds": 46.3,
    "agent_count": 6,
    "stakeholder_count": 1,
    "timestamp": "2026-01-24T18:19:59Z"
}
```

**Benefits:**
- Easy to grep/search logs
- Can send to monitoring (Sentry, DataDog)
- Debug production issues faster

---

### **PHASE 2: UX/UI Polish** (1 settimana)

#### UX-001: Loading States & Progress
**Priority:** HIGH | **Estimate:** 2 giorni

```html
<!-- Current: Generic "Generazione in corso..." -->
<!-- Target: Specific feedback per step -->

<div id="progressSteps">
    <div class="step completed">✓ File caricati</div>
    <div class="step active">⏳ Analisi stakeholder in corso...</div>
    <div class="step pending">Generazione piano strategico</div>
    <div class="step pending">Creazione documenti</div>
</div>

<!-- Real-time updates via SSE -->
<script>
    const eventSource = new EventSource('/api/progress/' + projectId);
    eventSource.onmessage = (e) => {
        const data = JSON.parse(e.data);
        updateProgressUI(data.step, data.message, data.percent);
    };
</script>
```

**What users see:**
- ✅ File upload → instant feedback
- ✅ Analysis → "Analizzati 3/5 stakeholder..."
- ✅ Generation → "Agente Marketing completato..."
- ✅ Export → "Creazione PDF in corso..."

**Result:** No più "si è bloccato?" - sempre chiaro cosa sta facendo

---

#### UX-002: Error Messages User-Friendly
**Priority:** HIGH | **Estimate:** 1 giorno

```html
<!-- Current: Technical errors -->
"NameError: name 'column' is not defined"

<!-- Target: User-friendly + actionable -->
<div class="error-card">
    <h3>⚠️ Problema durante la generazione PDF</h3>
    <p>Non siamo riusciti a creare il documento PDF per un errore tecnico.</p>

    <div class="error-actions">
        <button onclick="retryPDF()">Riprova</button>
        <button onclick="downloadDOCX()">Scarica DOCX invece</button>
        <a href="/support?code=A7F3">Contatta supporto</a>
    </div>

    <details>
        <summary>Dettagli tecnici (per sviluppatori)</summary>
        <code>Error code: A7F3 | WeasyPrint layout exception</code>
    </details>
</div>
```

**Fix all:**
- "404" → "Pagina non trovata"
- "500" → "Errore del server - riprova tra poco"
- "Gemini API error" → "Servizio AI temporaneamente non disponibile"

---

#### UX-003: Form Validation Visuale
**Priority:** MEDIUM | **Estimate:** 1 giorno

```html
<!-- Real-time validation feedback -->
<div class="form-group">
    <label for="club_name">Nome Club *</label>
    <input
        type="text"
        id="club_name"
        class="valid"
        aria-invalid="false"
    >
    <span class="validation-hint success">✓ Nome valido</span>
</div>

<div class="form-group">
    <label for="foundation_year">Anno Fondazione</label>
    <input
        type="number"
        id="foundation_year"
        class="invalid"
        value="1700"
        aria-invalid="true"
    >
    <span class="validation-hint error">
        ⚠️ Anno deve essere tra 1800 e 2024
    </span>
</div>
```

**Benefits:**
- User knows BEFORE submit if input is wrong
- Less frustration

---

#### UX-004: Success States & Celebrations
**Priority:** LOW | **Estimate:** 1 giorno

```html
<!-- After successful generation -->
<div class="success-celebration">
    <div class="confetti"></div>
    <h1>🎉 Piano Strategico Generato!</h1>
    <p>Il piano per <strong>AC Riccione 1926</strong> è pronto</p>

    <div class="download-cards">
        <a href="/download/pdf/..." class="card primary">
            <span class="icon">📄</span>
            <strong>PDF Esecutivo</strong>
            <small>Piano completo - 47 pagine</small>
        </a>
        <a href="/download/docx/..." class="card">
            <span class="icon">📝</span>
            <strong>DOCX Editabile</strong>
            <small>Per modifiche e personalizzazioni</small>
        </a>
        <a href="/download/onepager/..." class="card">
            <span class="icon">📊</span>
            <strong>OnePager</strong>
            <small>Sintesi 1 pagina</small>
        </a>
    </div>
</div>
```

**Delight users** when things work!

---

### **PHASE 3: Build & Distribution** (3-4 giorni)

#### BUILD-001: PyInstaller Production Build
**Priority:** CRITICAL | **Estimate:** 2 giorni

```python
# Spec: Single EXE distribuibile Windows

# File: RootingFuture_Production.spec
# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('templates', 'templates'),
        ('static', 'static'),
        ('knowledge_base/*.db', 'knowledge_base'),  # Include empty DB
        ('.env.example', '.'),
    ],
    hiddenimports=[
        'google.generativeai',
        'weasyprint',
        'docx',
        'flask',
        # All deps
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['pytest', 'black', 'mypy'],  # Dev deps
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='RootingFuture_Alpha_v0.1.0',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # No console window
    icon='static/icon.ico',
    version_file='version_info.txt'  # Windows version info
)
```

**Build command:**
```bash
pyinstaller RootingFuture_Production.spec --clean
```

**Output:**
```
dist/RootingFuture_Alpha_v0.1.0.exe  (150-200 MB)
```

**Test checklist:**
- [ ] EXE starts on fresh Windows 10/11
- [ ] No antivirus false positives
- [ ] All templates/static files load
- [ ] Database initializes correctly
- [ ] PDF generation works
- [ ] Licensing works (if enabled)

---

#### BUILD-002: Installer con Inno Setup
**Priority:** HIGH | **Estimate:** 1 giorno

```ini
; File: installer.iss (Inno Setup script)

[Setup]
AppName=Rooting Future Strategy Engine
AppVersion=0.1.0-alpha
AppPublisher=Your Company
DefaultDirName={autopf}\RootingFuture
DefaultGroupName=Rooting Future
OutputBaseFilename=RootingFuture_Setup_v0.1.0_alpha
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
SetupIconFile=static\icon.ico

[Files]
Source: "dist\RootingFuture_Alpha_v0.1.0.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "README_ALPHA.md"; DestDir: "{app}"; Flags: isreadme
Source: "LICENSE.txt"; DestDir: "{app}"

[Icons]
Name: "{group}\Rooting Future"; Filename: "{app}\RootingFuture_Alpha_v0.1.0.exe"
Name: "{commondesktop}\Rooting Future"; Filename: "{app}\RootingFuture_Alpha_v0.1.0.exe"

[Run]
Filename: "{app}\RootingFuture_Alpha_v0.1.0.exe"; Description: "Avvia Rooting Future"; Flags: postinstall nowait skipifsilent
```

**Output:**
```
RootingFuture_Setup_v0.1.0_alpha.exe (installer ~160 MB)
```

**Features:**
- ✅ Desktop shortcut
- ✅ Start menu entry
- ✅ Uninstaller
- ✅ Windows version check
- ✅ Professional installer UI

---

#### BUILD-003: README & Documentation
**Priority:** MEDIUM | **Estimate:** 1 giorno

```markdown
# File: README_ALPHA.md

# Rooting Future - Versione Alpha 0.1.0

## 🚀 Installazione

1. Scarica `RootingFuture_Setup_v0.1.0_alpha.exe`
2. Esegui installer
3. Lancia da desktop shortcut
4. Browser si apre su http://localhost:5000

## ⚙️ Configurazione (Prima Esecuzione)

### Gemini API Key (Obbligatoria)
1. Vai su https://aistudio.google.com/apikey
2. Crea API key gratuita
3. Apri Settings nell'app
4. Inserisci API key
5. Salva

## 📚 Guida Rapida

### Generare un Piano Strategico

1. **Upload Stakeholder (opzionale)**
   - Carica file DOCX con questionari
   - Sistema analizza e risolve conflitti

2. **Dati Club**
   - Nome, città, campionato
   - Colori sociali

3. **Genera**
   - Attendi 1-2 minuti
   - Scarica PDF/DOCX/OnePager

## ⚠️ Limitazioni Versione Alpha

- Solo Windows 10/11 (64-bit)
- Richiede connessione internet
- Gemini API key necessaria
- Export PDF può essere lento (~30s)
- Massimo 5 stakeholder per piano

## 🐛 Bug Conosciuti

- [ ] PDF export fallisce su club con nomi molto lunghi
- [ ] Upload ZIP > 10MB timeout
- [ ] Alcuni caratteri speciali causano errori

Segnala bug: [email/github link]

## 📝 Changelog

### v0.1.0-alpha (2026-02-XX)
- Prima release alpha
- Generazione piani strategici
- Export PDF/DOCX/OnePager
- Analisi stakeholder multi-input
- Web research automatico

## 📄 Licenza

[Your license]
```

---

### **PHASE 4: Alpha Testing** (1 settimana)

#### TEST-001: Internal Alpha Test
**Priority:** CRITICAL | **Estimate:** 3 giorni

```
# Alpha Test Plan

Testers: 3-5 persone (non sviluppatori)

Test Scenarios:
1. Fresh install su PC pulito
2. Generate 5 diverse club (varie categorie)
3. Upload 10 stakeholder docs
4. Test tutti export formats
5. Test error cases (bad inputs, network down)

Track:
- Crash count (target: 0)
- Error rate (target: <5%)
- UX friction points
- Performance issues
- Bug reports
```

**Iterate based on feedback!**

---

## 🎯 **Mia Raccomandazione: L'Ordine Giusto**

### **Step 1: STAB (Stabilità) FIRST** ✅ PRIORITÀ MASSIMA
```
STAB-001: Tests (60% coverage)
STAB-002: Error handling
STAB-003: Input validation
STAB-004: Logging

Durata: 1.5-2 settimane
```

**Perché PRIMA di tutto:**
- Build distribuibile senza test = disaster
- Users vedono errori tecnici = brutta figura
- Hard to debug without logs

---

### **Step 2: UX Polish** ✅ SECONDO
```
UX-001: Loading states
UX-002: Error messages
UX-003: Form validation
UX-004: Success celebrations

Durata: 1 settimana
```

**Perché DOPO stabilità:**
- Stabilità > estetica
- Ma UX professionale = credibilità

---

### **Step 3: Build & Distribute** ✅ TERZO
```
BUILD-001: PyInstaller
BUILD-002: Installer
BUILD-003: Documentation

Durata: 3-4 giorni
```

**Perché ULTIMO:**
- Build solo quando app stabile
- Altrimenti rebuild continuo

---

### **Step 4: Alpha Testing** ✅ FINALE
```
TEST-001: 3-5 beta testers
Iterate based on feedback

Durata: 1 settimana
```

---

## 📅 **Timeline Completa**

```
✅ DONE: REF-001 → REF-006 (3 settimane)
│
├─ Week 1-2: STAB-001 → STAB-004 (stabilità)
│  └─ Deliverable: Test suite + error handling
│
├─ Week 3: UX-001 → UX-004 (polish)
│  └─ Deliverable: Professional UI/UX
│
├─ Week 4: BUILD-001 → BUILD-003 (build)
│  └─ Deliverable: RootingFuture_Setup_v0.1.0_alpha.exe
│
└─ Week 5: TEST-001 (alpha test)
   └─ Deliverable: Feedback → iterate
```

**Total: ~6-7 settimane da oggi**

**Target Alpha Release:** Metà Marzo 2026

---

## ✅ **La Mia Risposta Diretta**

### Dopo REF-006, io farei:

1. **STAB-002 (Error Handling)** - 2 giorni
   - Wrap OGNI chiamata esterna
   - User-friendly error messages
   - **CRITICAL per alpha distribuibile**

2. **STAB-001 (Tests)** - 3-4 giorni
   - Almeno test per:
     - Plan generation end-to-end
     - PDF export
     - Stakeholder upload
   - **Catch bugs BEFORE users**

3. **UX-002 (Error Messages)** - 1 giorno
   - Replace "NameError" con "Qualcosa è andato storto"
   - **Professional impression**

4. **BUILD-001 (Executable)** - 2 giorni
   - PyInstaller single EXE
   - Test su PC pulito
   - **First distributable alpha**

**Poi iterate based on feedback.**

---

## 🎨 **Estetica: Quando?**

**Short answer:** DOPO stabilità, DURANTE UX polish (Step 2)

**Why:**
- Bella UI con bugs = frustrazione
- Brutta UI che funziona > bella UI che crasha
- Ma... **UX professionale = credibilità**

**Cosa intendi per "estetica"?**
- Colors/branding? → Quick (1 giorno)
- Animations/transitions? → Medium (2-3 giorni)
- Redesign completo? → Heavy (1-2 settimane)

**Consiglio:** CSS polish dopo STAB, ma PRIMA di alpha release.

---

## 📝 **TL;DR - Prossimi Step**

Dopo REF-006:

1. ✅ **STAB-002**: Error handling (2 giorni) ← START HERE
2. ✅ **STAB-001**: Test suite (4 giorni)
3. ✅ **UX-002**: User-friendly errors (1 giorno)
4. ✅ **BUILD-001**: PyInstaller EXE (2 giorni)
5. ✅ **Alpha test** con 3-5 persone

**Total: 2-3 settimane → ALPHA DISTRIBUIBILE**

---

Vuoi che creiamo task file per STAB-001/002? Oppure preferisci finire prima REF-002 → REF-006?
