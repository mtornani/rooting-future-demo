# Rooting Future Strategy Engine - Project Status

**Ultimo aggiornamento:** 2026-02-20
**Versione:** v6.0.0-alpha
**Percorso progetto:** `D:\AI\rooting-future`
**Branch attivo:** `hf-clean`
**Ultimo commit:** `13ad702` - feat: dashboard health widget, real-time progress bar, license card

> **NOTA PER AI ASSISTENTI:** Questo e' l'UNICO file di stato del progetto.
> Aggiornalo quando fai modifiche significative. NON creare file di stato alternativi.

---

## Cos'e' Rooting Future?

Software per la generazione automatica di **piani strategici triennali** per societa' calcistiche italiane. Utilizza AI (Google Gemini / OpenRouter) per analizzare dati del club e generare documenti professionali.

---

## Stato Completamento: ALPHA READY

Tutti i componenti core sono operativi. Il sistema supporta deploy cloud (HF Spaces) e desktop (EXE).

### Componenti

| Componente | Stato | Note |
|---|---|---|
| Core Engine (6 agenti AI) | Completo | Multi-Agent Orchestrator + Structured Agent |
| Dual AI Provider | Completo | Gemini (default) + OpenRouter (alternativa gratuita) |
| Export System | Completo | PDF (Playwright), DOCX, HTML, OnePager, Executive Report |
| Web Application | Completo | Dashboard, Plan Viewer, Progress SSE, Sharing, Settings |
| Admin Panel | Completo | KPI, gestione utenti, licenze (genera/revoca), statistiche |
| Security & Licensing | Completo | HWID-bound, scadenza, auto-creazione utente, revoca |
| Testing | Completo | 9 file test in `tests/` + test standalone + `.coverage` presente |
| Documentation | Completo | Manuali IT/EN in `docs/`, README admin |
| Deploy Cloud | Completo | HF Spaces (Docker + Gunicorn), fix cookie iframe |
| Build Desktop | Completo | PyInstaller EXE (381 MB), release ZIP (134 MB) |

### Da completare (nice-to-have, non bloccanti)

- Video tutorial
- Installer Windows (Inno Setup - spec pronto, non testato)
- Auto-update system (post-release)

---

## Stack Tecnologico

| Componente | Tecnologia |
|---|---|
| Backend | Flask (Python 3.12 locale, 3.11 su HF) |
| AI | Google Gemini API + OpenRouter (OpenAI-compatible) |
| Database | SQLite + WAL mode |
| PDF Export | Playwright/Chromium (primario) |
| DOCX Export | python-docx |
| Logging | structlog (JSON/console) |
| Validation | Pydantic v2 |
| Testing | pytest + pytest-cov |
| Frontend | Vanilla JS + CSS (no framework) |
| Deploy Cloud | HF Spaces (Docker + Gunicorn) |
| Deploy Desktop | PyInstaller |

---

## Struttura Progetto

```
rooting_future/
├── app.py                     # Flask app principale (~5900 LOC, 214 KB)
├── agents.py                  # Multi-agent + OpenRouterClient (65 KB)
├── structured_agent.py        # Agenti dati scientifici (28 KB)
├── config.py                  # Configurazione + OpenRouter models (17 KB)
├── license_manager.py         # Gestione licenze HWID + scadenza
├── knowledge_store.py         # Database SQLite + licenses table (64 KB)
├── session_manager.py         # Session recovery
├── web_research.py            # Web scraping per info club
│
├── api/
│   └── validators.py          # Pydantic input validation
│
├── domain/
│   ├── error_handling.py      # 20+ exception classes
│   └── rendering.py           # Plan rendering
│
├── utils/
│   ├── logging_config.py      # Structured logging
│   ├── progress_tracker.py    # Real-time progress SSE
│   ├── share_manager.py       # Public sharing system
│   └── content_formatter.py   # Markdown -> HTML
│
├── export_core.py             # Export base layer
├── export_docx.py             # DOCX export
├── export_html.py             # HTML export
├── export_onepager.py         # One-pager export
├── export_pdf_chromium.py     # PDF via Playwright
├── export_pdf_server.py       # PDF server-side
├── export_paged.py            # Paged export
├── export_package.py          # Package export
│
├── templates/                 # 22 Jinja2 templates
│   ├── dashboard_hybrid.html  # Dashboard (health, progress, licenza)
│   ├── admin_panel.html       # Admin + licenze tab
│   ├── activation.html        # Attivazione licenza
│   ├── settings.html          # API keys + provider AI
│   ├── strategic_plan_viewer.html
│   └── ...
│
├── static/css/                # Stylesheets (responsive)
├── static/js/                 # JavaScript
│
├── tests/                     # 9 file test pytest
│   ├── test_agents.py
│   ├── test_e2e_flow.py       # Test end-to-end (21 KB)
│   ├── test_error_handling.py
│   ├── test_export.py
│   ├── test_ingestion.py
│   ├── test_knowledge_store.py
│   ├── test_logging.py
│   ├── test_progress_tracker.py
│   └── test_validation.py
│
├── tools/                     # Admin tools
│   ├── dist/LicenseKeyGen.exe # GUI generator (~10 MB)
│   └── keygen_cli.py          # CLI generator
│
├── docs/                      # Documentazione
│   ├── MANUALE_UTENTE.md      # Manuale italiano
│   ├── USER_MANUAL.md         # English manual
│   ├── ARCHITECTURE.md        # Architettura sistema
│   └── N8N_SETUP_PROMPT.md
│
├── release/                   # Build distribuzione
│   ├── RootingFuture_v6.0.0-alpha.zip          # 134 MB
│   ├── RootingFuture_v6.0.0-alpha-openrouter.zip # 134 MB
│   └── RootingFuture_AdminTools.zip             # 10 MB
│
├── .dev/                      # Spec e roadmap (19 file)
├── Dockerfile                 # HF Spaces deploy
└── requirements.txt
```

---

## Flusso Generazione Piano

```
1. Upload DOCX stakeholder (opzionale)
   ↓
2. Inserimento dati club (nome, citta', categoria)
   ↓
3. Web research automatico
   ↓
4. 6 Agenti AI in parallelo:
   - STW Sportivi, Strutturali, Marketing, Sociali
   - Financial, Coordinator
   ↓
5. Structured Agent (dati scientifici)
   ↓
6. Audit qualita'
   ↓
7. Salvataggio + WebApp disponibile
   ↓
8. Export PDF/DOCX on-demand
```

---

## Modalita' Deploy

### Cloud (HF Spaces - SaaS)
- URL: https://huggingface.co/spaces/mtornani/rooting-future
- No licenza HWID (bypass automatico con env `HF_SPACES=1`)
- Cookie: `SameSite=None + Secure=True` per iframe
- Costo: 0 EUR/mese (free tier HF)

### Desktop (Enterprise)
- EXE via PyInstaller (381 MB)
- Licenza HWID-bound con scadenza
- Admin genera chiave, cliente attiva con email + key
- Auto-creazione utente su attivazione

---

## API Principali

| Endpoint | Metodo | Descrizione |
|---|---|---|
| `/` | GET | Dashboard |
| `/new` | GET | Form nuovo piano |
| `/api/generate` | POST | Genera piano (async) |
| `/api/generate-from-docx` | POST | Genera da DOCX (HTTP 202 + session_id) |
| `/api/progress/<id>` | GET | SSE progress stream |
| `/view/<plan_id>` | GET | WebApp piano |
| `/api/export/pdf/<id>` | GET | Export PDF |
| `/api/export/docx/<id>` | GET | Export DOCX |
| `/share/<plan_id>` | POST | Crea link pubblico |
| `/public/<token>` | GET | Piano pubblico |
| `/api/admin/licenses` | GET | Lista licenze |
| `/api/admin/licenses/<id>/revoke` | POST | Revoca licenza |
| `/api/system/status` | GET | System health (auto-refresh 10s) |

---

## Come Avviare

```bash
# Locale
cd D:\AI\rooting-future
venv\Scripts\activate
set GEMINI_API_KEY=your_key
py -3 app.py
# http://localhost:5000

# Test
py -3 -m pytest tests/ -v
py -3 -m pytest tests/ --cov=. --cov-report=html
```

---

## Repository Git

| Remote | URL | Branch |
|---|---|---|
| origin (GitHub) | https://github.com/mtornani/rooting-future-demo | hf-clean |
| hf (HF Spaces) | https://huggingface.co/spaces/mtornani/rooting-future | main |

**Branches locali:** `hf-clean` (attivo), `master`, `fix/sse-handler`, `fix/startup-debug`, `fix/web-research-default-key`

---

## Cronologia Modifiche Recenti

| Data | Modifiche |
|---|---|
| 2026-02-15 | Dashboard Hybrid: System Health, Progress Bar SSE, Card Licenza |
| 2026-02-14 | Deploy HF Spaces + fix login iframe (SameSite cookies) |
| 2026-02-07 | Hot-reload API keys senza riavvio |
| 2026-02-06 | Mobile responsive, Admin licenses tab, rebuild EXE con OpenRouter |
| 2026-02-05 | OpenRouter provider alternativo |
| Pre-Feb | Core engine, export system, licensing, test suite, sharing |

---

*Documento aggiornato il 2026-02-20*
