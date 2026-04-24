"""
Rooting Future - Shared CSS Design System
Phase 3: Centralized design tokens for all 3 export documents.

Import these constants in export_html.py, export_onepager.py, executive_report.py.
"""

# Google Fonts link tag (identical across all documents)
RF_FONT_IMPORT = (
    '<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800'
    '&family=Montserrat:wght@700;800&family=DM+Serif+Display&display=swap" rel="stylesheet">'
)

# Base reset (shared across all documents)
RF_RESET_CSS = """
* { margin: 0; padding: 0; box-sizing: border-box; }
"""

# Badge styles (identical in all 3 documents)
RF_BADGE_CSS = """
.badge { display: inline-block; padding: 2px 8px; border-radius: 10px; font-size: 0.72rem; font-weight: 700; text-transform: uppercase; margin-right: 4px; vertical-align: middle; }
.badge.questionnaire { background: #7B1FA2; color: white; }
.badge.research { background: #1565C0; color: white; }
.badge.estimate { background: #F57C00; color: white; }
"""

# MACRO card styles for structured agent output blocks
# Agents produce: ### MACRO N: Title / **Obiettivo:** / **Azioni chiave:** / **KPI:** / **Timeline:** / **Budget:**
RF_MACRO_CSS = """
.macro-card {
    border: 1px solid var(--border, #e2e8f0);
    border-left: 4px solid var(--accent, #1a365d);
    border-radius: 8px;
    margin-bottom: 24px;
    overflow: hidden;
    page-break-inside: avoid;
    break-inside: avoid;
}
.macro-header {
    background: var(--accent, #1a365d);
    color: white;
    padding: 11px 18px;
    display: flex;
    align-items: center;
    gap: 12px;
}
.macro-num {
    background: rgba(255,255,255,0.22);
    padding: 2px 10px;
    border-radius: 10px;
    font-weight: 800;
    font-size: 0.78rem;
    font-family: 'Montserrat', sans-serif;
    flex-shrink: 0;
}
.macro-title {
    font-family: 'Montserrat', sans-serif;
    font-weight: 700;
    font-size: 0.95rem;
    text-transform: uppercase;
    letter-spacing: 0.3px;
}
.macro-body {
    padding: 16px 20px;
    background: white;
}
.macro-body p { margin-bottom: 0.55rem; line-height: 1.6; }
.macro-body ul { margin: 0.35rem 0 0.75rem 1.2rem; }
.macro-body li { margin-bottom: 0.3rem; line-height: 1.5; }
/* Bold labels (Obiettivo / KPI / Timeline / Budget) styled as field labels */
.macro-body > p > strong:first-child {
    color: var(--accent, #1a365d);
    font-size: 0.72rem;
    text-transform: uppercase;
    letter-spacing: 0.6px;
    display: inline-block;
    min-width: 80px;
}
/* KPI and Budget lines get highlighted background */
.macro-body > p:has(> strong:first-child) {
    background: #f8fafc;
    border-radius: 4px;
    padding: 4px 8px;
    margin-left: -8px;
}
"""

# Print styles for the full HTML report (sidebar layout)
RF_PRINT_CSS_FULL = """
@media print {
    .print-bar, .sidebar { display: none !important; }
    .main-wrapper { margin-left: 0 !important; }
    * { -webkit-print-color-adjust: exact !important; color-adjust: exact !important; }
    .section { box-shadow: none; border: 1px solid #ddd; page-break-inside: avoid; }
    .macro-card { page-break-inside: avoid; break-inside: avoid; }
}
"""

# Print styles for A4 fixed documents (onepager / executive)
RF_PRINT_CSS_A4 = """
@media print {
    .print-bar { display: none !important; }
    * { -webkit-print-color-adjust: exact !important; color-adjust: exact !important; }
    .macro-card { page-break-inside: avoid; break-inside: avoid; }
}
"""

# Mobile responsive additions for the full HTML report
RF_MOBILE_CSS = """
@media (max-width: 768px) {
    .sidebar { display: none; }
    .main-wrapper { margin-left: 0 !important; }
    .container { padding: 20px 16px; }
    .cover h1 { font-size: 2rem; }
    .section { padding: 20px 16px; }
}
"""
