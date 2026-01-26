# REF-004: WebApp Piano Strategico Strutturato

## Obiettivo
Creare un'interfaccia web interattiva per visualizzare il piano strategico, rendendo il PDF un download opzionale invece dell'output primario.

## Problemi Attuali
1. **PDF come output primario**: Problemi di rendering, lento (30s con WeasyPrint)
2. **No navigazione interattiva**: Piano strategico è solo documento statico
3. **UX limitata**: Non si può espandere/collassare sezioni, navigare rapidamente
4. **No responsive**: PDF non funziona su mobile
5. **No search**: Impossibile cercare keyword nel piano

## Soluzione Proposta

### 1. Route `/view/{plan_id}` - Viewer Interattivo

```python
@app.route("/view/<plan_id>")
@login_required
def view_strategic_plan(plan_id):
    """
    Visualizzazione web del piano strategico con:
    - Sidebar navigazione sezioni
    - Sezioni collapsibili
    - Search box
    - Export buttons (PDF/DOCX on-demand)
    """
    review = editor.reviews.get(plan_id)
    if not review:
        abort(404)

    # Load structured plan from database
    plan_data = knowledge_manager.get_plan_by_id(plan_id)

    return render_template(
        'strategic_plan_viewer.html',
        plan=plan_data,
        plan_id=plan_id,
        club_name=review.club_name
    )
```

### 2. Template Structure: `strategic_plan_viewer.html`

```html
<!DOCTYPE html>
<html lang="it">
<head>
    <title>{{ club_name }} - Piano Strategico</title>
    <link rel="stylesheet" href="/static/css/plan_viewer.css">
</head>
<body>
    <!-- Sidebar Navigation -->
    <aside class="sidebar">
        <div class="sidebar-header">
            <h2>{{ club_name }}</h2>
            <p class="subtitle">Piano Strategico 2026-2028</p>
        </div>

        <!-- Search Box -->
        <div class="search-box">
            <input type="text" id="planSearch" placeholder="Cerca nel piano...">
        </div>

        <!-- Navigation Menu -->
        <nav class="section-nav">
            <a href="#executive-summary" class="nav-link active">
                <span class="icon">📊</span> Executive Summary
            </a>
            <a href="#market-analysis" class="nav-link">
                <span class="icon">📈</span> Analisi di Mercato
            </a>
            <a href="#competitive-landscape" class="nav-link">
                <span class="icon">⚔️</span> Competitive Landscape
            </a>
            <a href="#swot" class="nav-link">
                <span class="icon">🎯</span> SWOT Analysis
            </a>
            <a href="#strategic-objectives" class="nav-link">
                <span class="icon">🏆</span> Obiettivi Strategici
            </a>
            <a href="#tactical-plan" class="nav-link">
                <span class="icon">📋</span> Piano Tattico
            </a>
            <a href="#financial-projections" class="nav-link">
                <span class="icon">💰</span> Proiezioni Finanziarie
            </a>
            <a href="#implementation-roadmap" class="nav-link">
                <span class="icon">🗺️</span> Roadmap Implementazione
            </a>
            <a href="#kpi-dashboard" class="nav-link">
                <span class="icon">📊</span> KPI Dashboard
            </a>
            <a href="#risk-management" class="nav-link">
                <span class="icon">⚠️</span> Risk Management
            </a>
            <a href="#stakeholder-alignment" class="nav-link">
                <span class="icon">🤝</span> Allineamento Stakeholder
            </a>
        </nav>

        <!-- Export Actions -->
        <div class="sidebar-actions">
            <button class="btn btn-primary" onclick="exportPDF()">
                📄 Scarica PDF
            </button>
            <button class="btn btn-secondary" onclick="exportDOCX()">
                📝 Scarica DOCX
            </button>
            <button class="btn btn-tertiary" onclick="exportOnePager()">
                📊 OnePager
            </button>
        </div>
    </aside>

    <!-- Main Content -->
    <main class="plan-content">
        <!-- Executive Summary -->
        <section id="executive-summary" class="plan-section">
            <div class="section-header">
                <h1>Executive Summary</h1>
                <button class="collapse-btn" data-target="executive-summary-content">
                    <span class="icon">▼</span>
                </button>
            </div>
            <div id="executive-summary-content" class="section-content">
                {{ plan.executive_summary|safe }}
            </div>
        </section>

        <!-- Market Analysis -->
        <section id="market-analysis" class="plan-section">
            <div class="section-header">
                <h1>Analisi di Mercato</h1>
                <button class="collapse-btn" data-target="market-analysis-content">
                    <span class="icon">▼</span>
                </button>
            </div>
            <div id="market-analysis-content" class="section-content">
                {{ plan.market_analysis|safe }}
            </div>
        </section>

        <!-- ... altre sezioni ... -->

        <!-- Interactive Charts (if data available) -->
        <section id="financial-projections" class="plan-section">
            <div class="section-header">
                <h1>Proiezioni Finanziarie</h1>
                <button class="collapse-btn" data-target="financial-content">
                    <span class="icon">▼</span>
                </button>
            </div>
            <div id="financial-content" class="section-content">
                <div class="chart-container">
                    <canvas id="revenueChart"></canvas>
                </div>
                {{ plan.financial_projections|safe }}
            </div>
        </section>
    </main>

    <script src="/static/js/plan_viewer.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
</body>
</html>
```

### 3. CSS: `static/css/plan_viewer.css`

```css
/* Layout */
body {
    margin: 0;
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    display: flex;
    height: 100vh;
    overflow: hidden;
}

/* Sidebar */
.sidebar {
    width: 280px;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    display: flex;
    flex-direction: column;
    overflow-y: auto;
    box-shadow: 2px 0 10px rgba(0,0,0,0.1);
}

.sidebar-header {
    padding: 24px 20px;
    border-bottom: 1px solid rgba(255,255,255,0.2);
}

.sidebar-header h2 {
    margin: 0;
    font-size: 20px;
    font-weight: 700;
}

.sidebar-header .subtitle {
    margin: 8px 0 0 0;
    opacity: 0.8;
    font-size: 14px;
}

/* Search Box */
.search-box {
    padding: 16px 20px;
}

.search-box input {
    width: 100%;
    padding: 10px 12px;
    border: none;
    border-radius: 8px;
    background: rgba(255,255,255,0.2);
    color: white;
    font-size: 14px;
    backdrop-filter: blur(10px);
}

.search-box input::placeholder {
    color: rgba(255,255,255,0.7);
}

/* Navigation */
.section-nav {
    flex: 1;
    padding: 8px 0;
}

.nav-link {
    display: flex;
    align-items: center;
    padding: 12px 20px;
    color: white;
    text-decoration: none;
    transition: background 0.2s;
    font-size: 14px;
    gap: 12px;
}

.nav-link:hover {
    background: rgba(255,255,255,0.1);
}

.nav-link.active {
    background: rgba(255,255,255,0.2);
    border-left: 3px solid white;
    font-weight: 600;
}

.nav-link .icon {
    font-size: 18px;
    width: 24px;
    text-align: center;
}

/* Sidebar Actions */
.sidebar-actions {
    padding: 20px;
    border-top: 1px solid rgba(255,255,255,0.2);
    display: flex;
    flex-direction: column;
    gap: 8px;
}

.btn {
    padding: 10px 16px;
    border: none;
    border-radius: 8px;
    font-size: 14px;
    font-weight: 600;
    cursor: pointer;
    transition: transform 0.2s, box-shadow 0.2s;
}

.btn:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(0,0,0,0.2);
}

.btn-primary {
    background: white;
    color: #667eea;
}

.btn-secondary {
    background: rgba(255,255,255,0.2);
    color: white;
    backdrop-filter: blur(10px);
}

.btn-tertiary {
    background: transparent;
    color: white;
    border: 1px solid rgba(255,255,255,0.3);
}

/* Main Content */
.plan-content {
    flex: 1;
    overflow-y: auto;
    background: #f8f9fa;
    padding: 40px 60px;
}

/* Section */
.plan-section {
    background: white;
    border-radius: 12px;
    margin-bottom: 24px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.05);
    overflow: hidden;
}

.section-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 24px 32px;
    background: linear-gradient(90deg, #f8f9fa 0%, #e9ecef 100%);
    border-bottom: 2px solid #dee2e6;
}

.section-header h1 {
    margin: 0;
    font-size: 24px;
    font-weight: 700;
    color: #212529;
}

.collapse-btn {
    background: none;
    border: none;
    cursor: pointer;
    font-size: 18px;
    color: #6c757d;
    transition: transform 0.3s;
}

.collapse-btn.collapsed .icon {
    transform: rotate(-90deg);
}

.section-content {
    padding: 32px;
    color: #495057;
    line-height: 1.7;
    max-height: 10000px;
    transition: max-height 0.5s ease-out;
    overflow: hidden;
}

.section-content.collapsed {
    max-height: 0;
    padding-top: 0;
    padding-bottom: 0;
}

/* Typography */
.section-content h2 {
    color: #212529;
    font-size: 20px;
    margin-top: 24px;
    margin-bottom: 12px;
}

.section-content h3 {
    color: #495057;
    font-size: 18px;
    margin-top: 20px;
    margin-bottom: 10px;
}

.section-content ul {
    padding-left: 24px;
}

.section-content li {
    margin-bottom: 8px;
}

/* Charts */
.chart-container {
    max-width: 800px;
    margin: 24px auto;
    padding: 20px;
    background: #f8f9fa;
    border-radius: 8px;
}

/* Responsive */
@media (max-width: 768px) {
    body {
        flex-direction: column;
    }

    .sidebar {
        width: 100%;
        height: auto;
        max-height: 40vh;
    }

    .plan-content {
        padding: 20px;
    }
}

/* Print Styles */
@media print {
    .sidebar {
        display: none;
    }

    .plan-content {
        padding: 0;
    }

    .section-header {
        break-after: avoid;
    }

    .section-content {
        page-break-inside: avoid;
    }
}
```

### 4. JavaScript: `static/js/plan_viewer.js`

```javascript
// Collapsible sections
document.querySelectorAll('.collapse-btn').forEach(btn => {
    btn.addEventListener('click', function() {
        const targetId = this.dataset.target;
        const content = document.getElementById(targetId);

        content.classList.toggle('collapsed');
        this.classList.toggle('collapsed');
    });
});

// Sidebar navigation active state
const navLinks = document.querySelectorAll('.nav-link');
const sections = document.querySelectorAll('.plan-section');

// Intersection Observer for scroll-based active state
const observerOptions = {
    root: null,
    rootMargin: '-50% 0px -50% 0px',
    threshold: 0
};

const observer = new IntersectionObserver(entries => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            const id = entry.target.id;

            // Update active nav link
            navLinks.forEach(link => {
                link.classList.remove('active');
                if (link.getAttribute('href') === `#${id}`) {
                    link.classList.add('active');
                }
            });
        }
    });
}, observerOptions);

sections.forEach(section => observer.observe(section));

// Smooth scroll
navLinks.forEach(link => {
    link.addEventListener('click', function(e) {
        e.preventDefault();
        const targetId = this.getAttribute('href').substring(1);
        const target = document.getElementById(targetId);

        target.scrollIntoView({
            behavior: 'smooth',
            block: 'start'
        });
    });
});

// Search functionality
const searchInput = document.getElementById('planSearch');
let searchTimeout;

searchInput.addEventListener('input', function() {
    clearTimeout(searchTimeout);
    const query = this.value.toLowerCase().trim();

    if (query.length < 3) {
        // Clear highlights
        clearSearchHighlights();
        return;
    }

    searchTimeout = setTimeout(() => {
        searchInPlan(query);
    }, 300);
});

function searchInPlan(query) {
    clearSearchHighlights();

    sections.forEach(section => {
        const content = section.querySelector('.section-content');
        const text = content.textContent.toLowerCase();

        if (text.includes(query)) {
            // Highlight section header
            section.classList.add('search-match');

            // Expand section if collapsed
            const collapseBtn = section.querySelector('.collapse-btn');
            const sectionContent = section.querySelector('.section-content');
            if (sectionContent.classList.contains('collapsed')) {
                sectionContent.classList.remove('collapsed');
                collapseBtn.classList.remove('collapsed');
            }
        }
    });
}

function clearSearchHighlights() {
    document.querySelectorAll('.search-match').forEach(el => {
        el.classList.remove('search-match');
    });
}

// Export functions
function exportPDF() {
    const planId = document.body.dataset.planId;
    showExportLoadingModal('PDF');

    fetch(`/api/export/${planId}/pdf`)
        .then(response => response.blob())
        .then(blob => {
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `Piano_Strategico_${planId}.pdf`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            hideExportLoadingModal();
        })
        .catch(error => {
            console.error('Export failed:', error);
            hideExportLoadingModal();
            alert('Errore durante l\'esportazione PDF. Riprova.');
        });
}

function exportDOCX() {
    const planId = document.body.dataset.planId;
    window.location.href = `/api/export/${planId}/docx`;
}

function exportOnePager() {
    const planId = document.body.dataset.planId;
    window.location.href = `/api/export/${planId}/onepager`;
}

function showExportLoadingModal(format) {
    // Create modal overlay
    const modal = document.createElement('div');
    modal.id = 'exportModal';
    modal.innerHTML = `
        <div class="modal-overlay">
            <div class="modal-content">
                <div class="spinner"></div>
                <h3>Generazione ${format} in corso...</h3>
                <p>Questo potrebbe richiedere fino a 30 secondi</p>
            </div>
        </div>
    `;
    document.body.appendChild(modal);
}

function hideExportLoadingModal() {
    const modal = document.getElementById('exportModal');
    if (modal) {
        modal.remove();
    }
}
```

## Implementation Steps

### Step 1: Create Route & Template
- Add `/view/<plan_id>` route to `app.py`
- Create `templates/strategic_plan_viewer.html`
- Create `static/css/plan_viewer.css`
- Create `static/js/plan_viewer.js`

### Step 2: Database Schema Update
```python
# Add to knowledge_store.py
def get_plan_by_id(self, plan_id: str) -> Dict[str, Any]:
    """
    Fetch structured plan data from strategic_plans table.
    Returns dict with all sections as HTML.
    """
    # Implementation
```

### Step 3: Modify Success Page
- Change 3rd card from "Piano Strategico PDF" to "Visualizza Piano Completo"
- Link to `/view/{plan_id}` instead of PDF download
- Add secondary "Scarica PDF" button

### Step 4: Update Export Routes
- Make PDF generation async (don't block UI)
- Add loading modal during export
- Return file via download endpoint

## Benefits
1. **Faster UX**: No 30s wait for PDF - instant view
2. **Interactive**: Navigate, search, collapse sections
3. **Responsive**: Works on mobile/tablet
4. **Accessible**: Better than PDF for screen readers
5. **Flexible**: Easy to add features (comments, sharing, analytics)
6. **PDF optional**: Generate only when explicitly requested

## Target Metrics
- ✅ < 1s page load for `/view/{plan_id}`
- ✅ Sidebar navigation smooth scroll
- ✅ Search responds in < 300ms
- ✅ Mobile responsive (320px - 1920px)
- ✅ Print CSS generates clean printout

## Expected LOC Changes
- app.py: +40 LOC (new route)
- templates/strategic_plan_viewer.html: +350 LOC (new file)
- static/css/plan_viewer.css: +280 LOC (new file)
- static/js/plan_viewer.js: +150 LOC (new file)
- templates/generation_success.html: ~15 LOC (modify 3rd card)
- Total: +815 LOC (net +815)

## Testing Plan
1. Generate plan → view in webapp → verify all sections render
2. Test sidebar navigation (smooth scroll, active state)
3. Test collapsible sections (expand/collapse)
4. Test search (find keyword, highlight sections)
5. Test export buttons (PDF download, DOCX, OnePager)
6. Test responsive (mobile, tablet, desktop)
7. Test print CSS (Ctrl+P → check layout)

## Notes
- This makes PDF export **optional** instead of primary
- WebApp becomes the default way to view plans
- PDF generation still works but with armored fallback (REF-003)
- Users can print from browser if they need paper copy
