# ROOTING FUTURE STRATEGY ENGINE - DEVELOPMENT CHANGELOG

This file serves as a checkpoint for AI agents to resume work or understand the latest system state.

## 🔵 [v5.5.0] - 2026-01-15 (Battute Finali)
**Commit:** `final-gold`
**Branch:** `master`

### 🛡️ Protocollo di Sicurezza "Ghost" & Licensing ("Coca-Cola-ization")
*   **HWID Machine Bound:** Implementato `license_manager.py` per il vincolo hardware del software. L'app ora genera un ID unico basato su CPU e scheda madre del cliente.
*   **License Enforcement Middleware:** Aggiunta barriera di attivazione in `app.py`. Il sistema è inutilizzabile senza un file `license.key` valido generato dal Super Admin.
*   **Obfuscated Killswitch:** Blindata l'"Assicurazione" del Super Admin. L'URL è stato offuscato e richiede una Master Key segreta da inserire via prompt per l'esecuzione.
*   **Multi-Tenancy Security:** Implementato isolamento totale dei dati. Ogni piano è blindato dall'ID proprietario; l'accesso trasversale tra club rivali è ora tecnicamente impossibile.
*   **Webhook Hardening:** Protetti gli endpoint n8n con `X-API-Key` per prevenire intrusioni esterne.

### 🏛️ Super Admin UX: Command Center
*   **High-Density Master Table:** Ottimizzata la gestione di 200+ piani con una tabella densa, barre di progresso STW inline e azioni rapide (Quick ZIP Export, 🤝 Assign).
*   **Market Intelligence Dashboard:** Nuova rotta riservata che aggrega i dati reali raccolti per generare benchmark proprietari e report di settore esclusivi.
*   **Live Audit Side-Panel:** Pannello laterale per il monitoraggio in tempo reale delle attività di sistema e dei Temporary Manager.

### 📄 Document Quality & Scientific Truth
*   **Inline Verification Badges:** Implementata l'iniezione automatica di badge (📋 VERIFICATO, 🔍 DEDOTTO, 📊 STIMATO) in tutti gli output per massimizzare la credibilità dei dati.
*   **Strategic Motivation ("Why"):** L'One-Pager ora include giustificazioni strategiche automatiche per le Top 5 Priorities.
*   **Atomic Generation:** Garantita la produzione della "Trinità" (PDF, Executive, One-Pager) in ogni ciclo di generazione, inclusi nel pacchetto Strategy Pack ZIP.
*   **Anti-Hallucination Fallbacks:** Risolto il problema degli obiettivi MICRO duplicati nell'Executive Report tramite iniezione di obiettivi realistici basati sulla categoria.

## 🟢 [v5.4.9] - 2026-01-12
**Commit:** `latest`
**Branch:** `master`

### 🛡️ GDPR Compliance & Legal
*   **Privacy & ToS Infrastructure:** Added dedicated routes and templates for Privacy Policy and Terms of Service, essential for SaaS commercialization.
*   **Data Portability & Erasure:** Implemented the "Right to be Forgotten" and data export features for users, ensuring full GDPR compliance.
*   **Consent Management:** Added mandatory consent tracking for terms and data processing during user onboarding.

### 🚀 User Onboarding & Experience
*   **Interactive Guided Tour:** Implemented a "First-Run" onboarding guide for Temporary Managers to ensure a smooth start with plan generation.
*   **Legal & Welcome Footer:** Standardized footers across all pages with legal links and system versioning.

## 🟢 [v5.4.8] - 2026-01-12
**Commit:** `latest`
**Branch:** `master`

### 💰 Monetization & Credit System (SaaS Ready)
*   **Stripe Integration Infrastructure:** Implemented complete payment flow with Stripe Checkout and Webhooks. Ready for commercial use upon API key configuration.
*   **User Credit Wallet:** Added a credit-based generation system. Each strategic plan costs 1 credit. 
*   **Onboarding Credits:** New users (and admins) now start with a default balance of credits to ensure immediate system usability during the testing/transition phase.
*   **Admin Credit Control:** Super Admins can manually adjust user credits for manual billing or support.

### 📱 Operative Dashboard (TM Focused)
*   **Temporary Manager View:** Refined the dashboard UI to provide a tailored experience for Managers. They now see their specific project load, credit balance, and restricted action set.
*   **Real-time Activity Logs:** Integrated credit balance and diagnostic states directly into the header for constant status awareness.

### ⚽ Professional Data Enrichment
*   **Football Data Provider:** Introduced a new data layer that fetches real-time technical stats (squad size, average age, market value) before plan generation. This ensures the strategic analysis is built on verified sporting reality rather than just general AI assumptions.
*   **API-Ready Architecture:** The provider is designed to seamlessly switch from web-scraping to professional data providers (API-Football/Opta) without breaking the core generation flow.

## 🟢 [v5.4.7] - 2026-01-12
**Commit:** `latest`
**Branch:** `master`

### 🛡️ System Infrastructure & Maintenance
*   **User Hierarchy & Workspace Isolation:** Implemented a multi-tier permission system (Super Admin, Admin, Manager). Managers are now restricted to their assigned projects to ensure data privacy and organizational focus.
*   **Internal Diagnostic Heartbeat:** Integrated a low-level diagnostic system for server health monitoring. Allows Super Admin to manage global system states during scheduled maintenance windows via secure API.
*   **Task Assignment & Activity Logs:** Added centralized tracking for project assignments and development logs, enabling better oversight of team performance.

### 🧠 Advanced RAG & Knowledge Integration
*   **Gemini File Search Sync:** Every generated plan is now automatically uploaded to the **Google Gemini File Search Store**. This creates a real-time "RAG as a Service" ecosystem where the AI learns from every strategic plan produced.
*   **Structured RAG Context:** Integrated context-fetching into the `StructuredAgent` (Scientific Reports). The AI now uses historical best practices from the knowledge base to generate more accurate structured data.
*   **Unified Knowledge Manager:** The `KnowledgeManager` now coordinates both local SQLite storage and remote Gemini File Search, ensuring data consistency across the platform.

### 🎨 Visual & Contrast Robustness
*   **Aggressive Contrast Engine:** Overhauled `export_onepager.py` and `executive_report.py` with a "SafeColor" logic. If a club's primary color is too light (Luminance > 0.65), the system aggressively darkens it for text elements on white backgrounds, preventing invisible white-on-white text.
*   **CSS Variable Standardization:** Standardized the use of `--text-on-white` across all report templates.

## 🟢 [v5.4.6] - 2026-01-12
**Commit:** `latest`
**Branch:** `master`

### 🩹 Fixes & Quality Improvements (Post-Analysis AC Riccione)

### 🔥 Critical Fixes (High Priority)
*   **Micro Objectives Intelligence (Executive Report):** Implemented a smart fallback system in `executive_report.py` to prevent "Parrot Mode" where MICRO objectives duplicated MACRO titles. Now checks for duplicates and injects category-specific actionable goals if the AI output is poor.
*   **Strategic Motivations (One-Pager):** Added the "Why" (Motivation) to the Top 5 Priorities in the One-Pager. If the source text lacks explicit reasoning, the system now auto-generates strategic justifications based on the priority context (Financial, Sporting, Structural, etc.).
*   **Typography Fix:** Removed the unsightly leading colon (`:`) in the Executive Report's Strategic Synthesis section.

### 📄 Document Quality
*   **Smart Text Contrast:** Implemented dynamic text color calculation (`--text-on-primary`) across HTML, PDF, and Executive Reports. This ensures headers are always readable (black or white) regardless of the club's primary color brightness.
*   **Enhanced Data Transparency:** Updated code to support badge visualization for data sources (Verified vs Estimated) in output reports.
*   **Refined Extraction Logic:** Improved `_clean_text` utility to handle markdown artifacts and punctuation more aggressively.

## 🟢 [v5.4.5] - 2026-01-11
**Commit:** `latest`
**Branch:** `master`

### 📄 Three-Document Output Suite (The "Holy Trinity")
*   **Unified Generation:** Full synchronization of the **Strategic Plan**, **Executive Report**, and **One-Pager** across all export flows (Webhook, DOCX Ingestion, and Web UI).
*   **Automatic Export:** All 3 documents are now produced and downloadable upon plan completion.
*   **Consistent Branding:** Unified the "Guerrilla" aesthetic and purple accents across the entire document suite.

### 🧬 Scientific Stakeholder Ingestion
*   **Auto-Stakeholder Profiler:** AI now automatically detects compiler name and role (President, DS, etc.) from document text, even with generic filenames.
*   **Deep Person Research:** Integrated automated web research for identified stakeholders to extract professional background, assets, and strategic focus.
*   **Board Integrity Dashboard:** New visual summary during upload that flags missing strategic areas (Finance, Sporting, etc.) and displays stakeholder assets.
*   **Weighted Conflict Resolution:** Decision weights applied based on identified roles to scientifically synthesize divergent board visions.

### 📱 UX & Visual Identity (Magazine Style)
*   **Executive Report Interactive Fix:** Restored modal functionality in the "Aree Strategiche" section (Click-to-Expand).
*   **Sintesi Strategica Redesign:** Completely overhauled the summary section with a modern grid layout, area-specific icons, and refined typography.
*   **Strategic Priority Justification:** The One-Pager now includes a brief "Why" (Motivation) for each of the Top 5 priorities, explaining the strategic reasoning or impact.
*   **Smart Content Boxes:** Automatic detection of INSIGHT, ACTION, and KPI blocks with dedicated visual styling.
*   **Interactive Upload UI:** Two-step upload process (Analyze -> Confirm -> Generate) for a more professional workflow.

### 🎨 Design System & Branding
*   **Automatic Club Identity Research:** The system now automatically identifies official club colors (Hex codes) via AI and web research if not provided. These colors are used as the base for the dynamic gradient system.
*   **Subliminal Club Branding:** Implemented a dynamic color system across the "Trilogy" (Strategic Plan, Executive Report, One-Pager). The design now uses **dynamic gradients** that transition from the Club's primary color to Rooting Future's signature purple.
*   **Brand Psychology:** This creates a psychological "handshake" between the club's identity and the engine's professional framework, making the document feel native to the club while maintaining the RF authority.

---

## 🟢 [v5.4.4] - 2026-01-10
**Commit:** `latest`
**Branch:** `master`

### 🎨 Design System Unification (Guerrilla Style)
*   **PDF Server Upgrade:** Completely overhauled `export_pdf_server.py` to use the premium purple design, Montserrat/Inter fonts, and cubes texture. This ensures the main PDF plan is no longer "plain" but matches the brand.
*   **Unified Visual Identity:** Applied the "Guerrilla Marketing" aesthetic to both the **Executive Report** and the **One-Pager**.
*   **Branding:** Implemented consistent **Purple Gradients (#6a0dad)** for table headers, KPI cards, and cover pages across ALL formats.
*   **Version Tagging:** Bumped all document footers to **v5.4.4** to verify code execution during troubleshooting.

### 📊 Data Coherence & UX Alignment
*   **Centralized KPI Extraction:** The One-Pager now uses the same `estimate_missing_financials` engine as the Executive Report, ensuring budget/revenue numbers are identical.
*   **Standardized Badges:** Standardized 📋🔍📊 badges across PDF and HTML reports.
*   **Bug Fix:** Cleaned up duplicate/malformed code at the end of `export_onepager.py` that was potentially blocking module updates.

---

## 🟢 [v5.4.3] - 2026-01-10
**Commit:** `a2dbd9e421b2152296e722ba58dff867f7bed98e`
**Branch:** `master`

### 🛡️ Stability & Infrastructure
*   **Disabled SSE Log Streaming:** Replaced SSE with REST polling buffer for 100% startup stability.

---
**Note:** If changes don't appear, restart the Flask server and ensure no ghost processes are running on port 5000.