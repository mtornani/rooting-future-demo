# ROOTING FUTURE STRATEGY ENGINE - DEVELOPMENT CHANGELOG

This file serves as a checkpoint for AI agents to resume work or understand the latest system state.

## 🟢 [v5.4.4] - 2026-01-10
**Commit:** `latest`
**Branch:** `master`

### 🎨 Design System Unification (Guerrilla Style)
*   **Unified Visual Identity:** Applied the "Guerrilla Marketing" aesthetic to both the **Executive Report** and the **One-Pager**.
*   **Typography Overhaul:** Standardized fonts across all 3 documents: **Montserrat** for headers (H1/H2) and **Inter** for body text.
*   **Branding:** Implemented consistent **Purple Gradients (#6a0dad)** for table headers, KPI cards, and cover pages.
*   **Textures:** Added the "cubes" pattern texture to all document covers for a premium, tactile feel.

### 📊 Data Coherence & UX Alignment
*   **Centralized KPI Extraction:** Replaced hardcoded placeholders and fragile regex in the One-Pager with real data extracted from the centralized `estimates` system.
*   **Explicit Badging:** Standardized the 📋🔍📊 badge system. Every KPI now explicitly shows its source with professional color-coding (e.g., light purple for "Questionario Board").
*   **"I TUOI DATI" Section:** Added a dedicated page to the Executive Report that visualizes input statistics (questionnaires count, verified data points, and completeness percentage).

---

## 🟢 [v5.4.3] - 2026-01-10
**Commit:** `a2dbd9e421b2152296e722ba58dff867f7bed98e`
**Branch:** `master`

### 🛡️ Stability & Infrastructure
*   **Disabled SSE Log Streaming:** Removed SSE-based logging which caused deadlocks.
*   **Implemented Stable Polling:** Replaced SSE with a lightweight REST polling buffer for 100% startup stability.

---

## 🟢 [v5.4.2] - 2026-01-10
**Commit:** `6454d52994b4fc34dec574e6179a6f53c1d6120e`
**Branch:** `master`

### 🐛 Fixes
*   **Executive Report:** Fixed `AttributeError` caused by incorrect `DataTier` enum reference.

---

## 🟢 [v5.4.1] - 2026-01-10
**Commit:** `8ff905c9a571184945f4f143ddc42c177749b29d`
**Branch:** `master`

### 🚀 Major UX/UI Upgrades (Strategic Plan)
*   **Visual Overhaul:** Transformed the Strategic Plan (`export_html.py`) to a premium report.
*   **New Components:** Added Input Sources Dashboard and STW Matrix Visualization.

---
**Note:** Always check `git status` and `git log` for the absolute latest state.
