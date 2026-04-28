"""
Rooting Future Strategy Engine v6.0
Flask Application Principale

API e interfaccia web per generazione piani strategici.
"""

import os
import sys
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import logging

import tempfile
import zipfile
import shutil

from flask import (
    Flask,
    render_template,
    request,
    jsonify,
    redirect,
    url_for,
    flash,
    session,
    Response,
    send_file,
)
import queue
import threading
import time
from concurrent.futures import ThreadPoolExecutor

# Lock per accesso concorrente a file cache/database
cache_lock = threading.Lock()

# Inizializza il pool di thread per analisi pesanti (max 2 per le 2 CPU di AWS)
analysis_executor = ThreadPoolExecutor(max_workers=2)

# Global status tracker per la UX (HUD)
project_progress = {}

def cleanup_old_projects():
    """Rimuove vecchi progetti dal tracker per liberare memoria (ogni ora)"""
    while True:
        try:
            time.sleep(3600)  # 1 ora
            now = time.time()
            # Mantieni solo progetti degli ultimi 4 ore
            with cache_lock:  # Riutilizziamo un lock per evitare race conditions
                to_delete = [
                    p_id
                    for p_id, status in project_progress.items()
                    if now - status.get("timestamp", 0) > 14400
                ]
                for p_id in to_delete:
                    del project_progress[p_id]
                    if (
                        hasattr(app, "analysis_results")
                        and p_id in app.analysis_results
                    ):
                        del app.analysis_results[p_id]
                if to_delete:
                    logger.info(f"Cleanup: rimosse {len(to_delete)} sessioni vecchie.")
        except Exception as e:
            logger.error(f"Cleanup thread error: {e}")

# Avvia thread di cleanup
threading.Thread(target=cleanup_old_projects, daemon=True).start()

def update_project_status(p_id, status, progress=0, message="", data=None):
    """Aggiorna lo stato globale di un progetto per il feedback live"""
    project_progress[p_id] = {
        "status": status,  # 'processing', 'completed', 'error'
        "progress": progress,  # 0-100
        "message": message,  # Messaggio per l'utente (es. "Agente Sporting al lavoro...")
        "timestamp": time.time(),
        "data": data,  # Risultati finali se pronti
    }

from config import (
    OUTPUT_DIR,
    KNOWLEDGE_DIR,
    CATEGORIE_CALCIO_ITALIANO,
    REGIONI_ITALIANE,
    COUNTRIES_LEAGUES,
    COUNTRIES,
    FOOTBALL_TIERS,
    validate_config,
    get_missing_config,
)

from agents import MultiAgentOrchestrator, AgentRole, OpenRouterClient
from web_research import WebResearcher, ResearchAggregator
from data_sourcing import SourcedContentGenerator
from knowledge_store import KnowledgeManager, PlanRecord
from export_docx import ProfessionalDocxExporter
from export_html import ChunkedHTMLExporter, HTMLSection

# NOTA: export_pdf, export_pdf_server, export_paged importano WeasyPrint
# che può bloccare GTK su Windows. Import lazy nelle funzioni che li usano.
# from export_pdf_server import create_pdf_from_html  # LAZY
# from export_paged import create_paged_html   # LAZY
# from export_pdf_server import PdfServerExporter  # LAZY
# from export_onepager import create_onepager  # LAZY - usa stw_matrix
from club_identity import get_club_colors, get_club_identity
from post_production_editor import (
    PostProductionEditor,
    BatchReviewManager,
    PlanStatus,
    SectionStatus,
)

# Sistema strutturato v6.0
from domain.rendering import PlanRenderer
from structured_agent import StructuredOrchestrator, SECTION_DATA_TEMPLATES
from file_search_manager import FileSearchManager
from football_data_provider import data_provider

plan_renderer = PlanRenderer()

# Dashboard Strategica
from dashboard_module import generate_strategic_dashboard

# Data Estimator e Charts
from data_estimator import estimate_missing_financials, DataTier
from chart_generator import generate_financial_charts_for_report
from stw_analyzer import calculate_stw_progress

# Error Handling
from domain.error_handling import (
    route_error_handler,
    RootingFutureError,
    handle_exception,
    get_user_friendly_message,
    log_exception,
    # Specific exceptions
    GeminiAPIError,
    GeminiRateLimitError,
    GeminiTimeoutError,
    GenerationError,
    AgentError,
    PDFExportError,
    DOCXExportError,
    ExportError,
    DatabaseError,
    DatabaseLockError,
    PlanNotFoundError,
    PlanAccessDeniedError,
    ValidationError,
    StakeholderParsingError,
    FileUploadError,
    FileTooLargeError,
    InvalidFileFormatError,
    ResearchError,
    AuthenticationError,
    AuthorizationError,
    InsufficientCreditsError,
    ShareError,
    ShareNotFoundError,
    SharePasswordError,
)

# Validators
from api.validators import (
    GeneratePlanRequest,
    SaveSectionRequest,
    RegenerateSectionRequest,
)

# Structured Logging (STAB-004)
from utils.logging_config import (
    get_logger,
    log_event,
    log_error,
    log_api_request,
    log_api_response,
    timed_operation,
    log_plan_generation_started,
    log_plan_generation_completed,
    log_export_event,
    log_share_event,
)
struct_logger = get_logger("app")

# Progress Tracker (UX-001-B)
from utils.progress_tracker import (
    progress_tracker,
    start_tracking,
    update_progress,
    update_agent_progress,
    complete_tracking,
    get_progress,
)

from stw_analyzer import calculate_stw_progress
from n8n_integration import register_n8n_routes, get_questionnaire_schema

# Data Ingestor for Multi-Stakeholder Conflict Resolution
from data_ingestor import (
    DataIngestor,
    process_n8n_webhook_payload,
    generate_conflict_report_html,
    generate_alignment_dashboard_html,
    process_docx_files_to_payload,
    DocxIngestor,
    DOCX_AVAILABLE,
)

# Authentication
from auth_manager import init_auth
from flask_login import login_required, current_user

# =============================================================================
# SETUP & LOGGING OPTIMIZATION
# =============================================================================

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "rf-secret-key-2026")
app.config["MAX_CONTENT_LENGTH"] = 128 * 1024 * 1024

app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = False

# ProxyFix: HF Spaces usa reverse proxy — senza questo le sessioni non persistono
from werkzeug.middleware.proxy_fix import ProxyFix
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Configurazione Logging Aggressiva (Anti-Noise)
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
# Silenzia librerie grafiche e di sistema troppo verbose
NOISY_LIBRARIES = [
    "fontTools",
    "fontTools.subset",
    "fontTools.ttLib",
    "weasyprint",
    "httpx",
    "urllib3",
    "PIL",
    "matplotlib",
    "multipart",
]
for lib in NOISY_LIBRARIES:
    logging.getLogger(lib).setLevel(logging.ERROR)

logger = logging.getLogger(__name__)

# =============================================================================
# LOGGING SYSTEM (Polling-based, No SSE to avoid deadlocks)
# =============================================================================

# Buffer per gli ultimi N log
log_history: List[Dict] = []
LOG_HISTORY_SIZE = 100
log_history_lock = threading.Lock()

def add_to_log_history(level: str, message: str, source: str = "system"):
    """Aggiunge un log al buffer per la dashboard."""
    with log_history_lock:
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "level": level.upper(),
            "message": message,
            "source": source,
        }
        log_history.append(log_entry)
        if len(log_history) > LOG_HISTORY_SIZE:
            log_history.pop(0)

def clear_log_history():
    """Svuota la cronologia dei log."""
    with log_history_lock:
        log_history.clear()
        add_to_log_history(
            "info", "Console resettata. In attesa di nuove operazioni..."
        )

def broadcast_log(level: str, message: str, source: str = "system"):
    """
    Invia un log alla console e al buffer della dashboard.
    """
    # Console logging
    if level.upper() == "INFO":
        logger.info(f"[{source}] {message}")
    elif level.upper() == "WARNING":
        logger.warning(f"[{source}] {message}")
    elif level.upper() == "ERROR":
        logger.error(f"[{source}] {message}")
    else:
        logger.info(f"[{source}] {message}")

    # Buffer per dashboard
    add_to_log_history(level, message, source)

# Intercetta tutti i logger Python nel buffer in-memory
class _InMemoryLogHandler(logging.Handler):
    def emit(self, record):
        try:
            add_to_log_history(record.levelname, self.format(record), record.name)
        except Exception:
            pass

_mem_handler = _InMemoryLogHandler()
_mem_handler.setLevel(logging.INFO)
_mem_handler.setFormatter(logging.Formatter("%(message)s"))
logging.getLogger().addHandler(_mem_handler)

log_stream_handler = None

# Questionnaire data directory
QUESTIONNAIRE_DATA_DIR = Path(__file__).parent / "data" / "questionnaires"
QUESTIONNAIRE_DATA_DIR.mkdir(parents=True, exist_ok=True)

# =============================================================================
# COMPONENTI (inizializzazione con gestione errori)
# =============================================================================

# FileSearchManager (Gemini RAG)
try:
    file_search_manager = FileSearchManager()
    file_search_store_name = file_search_manager.get_store_name()
except Exception as e:
    logger.warning(f"FileSearchManager non disponibile: {e}")
    file_search_manager = None
    file_search_store_name = None

# Knowledge manager (DB + RAG)
knowledge_manager = KnowledgeManager(file_search_manager=file_search_manager)

# Session Manager — persistente su SQLite /data
from session_manager import init_session_manager
session_manager = init_session_manager(store=knowledge_manager.store)

# Auth
init_auth(app, knowledge_manager.store)

# Multi-Agent Orchestrator (Gemma primary, Gemini Flash fallback)
orchestrator = MultiAgentOrchestrator(
    knowledge_store=knowledge_manager,
    file_search_store_name=file_search_store_name,
)

# Componenti base
researcher = WebResearcher()
research_aggregator = ResearchAggregator()
docx_exporter = ProfessionalDocxExporter()
html_exporter = ChunkedHTMLExporter()
editor = PostProductionEditor()
batch_manager = BatchReviewManager()

# Sistema strutturato v6.0
structured_orchestrator = StructuredOrchestrator(
    file_search_store_name=file_search_store_name,
    knowledge_store=knowledge_manager,
)

# =============================================================================
# LEGAL & GDPR
# =============================================================================

@app.route("/session-test")
def session_test():
    """Diagnostica sessioni — visita due volte: prima imposta, seconda legge."""
    count = session.get('_test_count', 0) + 1
    session['_test_count'] = count
    session.modified = True
    return jsonify({
        'count': count,
        'session_type': app.config.get('SESSION_TYPE', 'cookie'),
        'session_keys': list(session.keys()),
        'works': count > 1,
    })

@app.route("/autologin")
def autologin():
    """Bypass form — login diretto admin per diagnostica. RIMUOVERE DOPO TEST."""
    from auth_manager import User, bcrypt, _store
    user_data = _store.get_user_by_email('mirkotornani@gmail.com') if _store else None
    if not user_data:
        return jsonify({'error': 'user not found', 'store': str(_store)})
    from flask_login import login_user
    user = User(user_data)
    login_user(user)
    session.modified = True
    print(f"[AUTOLOGIN] done, is_auth={current_user.is_authenticated}", flush=True)
    return redirect(url_for('index'))

@app.route("/legal/privacy")
def view_privacy():
    return render_template("privacy.html", user=current_user)

@app.route("/legal/terms")
def view_terms():
    return render_template("terms.html", user=current_user)

@app.route("/api/user/export-data")
@login_required
def export_user_data():
    """Esporta tutti i dati dell'utente in formato JSON (GDPR)"""
    plans, _ = knowledge_manager.store.list_plans(owner_id=int(current_user.id))
    data = {
        "user_profile": {
            "email": current_user.email,
            "full_name": current_user.full_name,
            "role": current_user.role,
            "credits": current_user.credits,
        },
        "plans": [p.to_dict() for p in plans],
    }
    return jsonify(data)

@app.route("/api/user/delete-account", methods=["POST"])
@login_required
def delete_account():
    """Elimina l'account e tutti i dati associati (Diritto all'oblio)"""
    # In una vera app, qui elimineresti l'utente dal DB
    # Per sicurezza, implementiamo solo il flag disabilitato o chiediamo conferma Super Admin
    logger.warning(f"Richiesta eliminazione account: {current_user.email}")
    return jsonify(
        {
            "success": True,
            "message": "Richiesta ricevuta. L'account sarà rimosso entro 48h.",
        }
    )

@app.route("/api/user/complete-onboarding", methods=["POST"])
@login_required
def complete_onboarding():
    """Segna l'onboarding come completato per l'utente"""
    with sqlite3.connect(knowledge_manager.store.db_path) as conn:
        conn.execute(
            "UPDATE users SET first_login = 0 WHERE id = ?", (int(current_user.id),)
        )
        conn.commit()
    return jsonify({"success": True})

# =============================================================================
# MIDDLEWARE - KILLSWITCH & ROLE ISOLATION
# =============================================================================

@app.before_request
def check_system_lockout():
    """Controlla il Killswitch globale prima di ogni richiesta"""
    # Escludi le rotte statiche e il login per evitare loop
    if request.path.startswith("/static") or request.path.startswith("/auth"):
        return

    try:
        if knowledge_manager.store.is_killswitch_active():
            # Se il killswitch è attivo, solo il Super Admin può passare
            if not current_user.is_authenticated or current_user.role != "super_admin":
                # Se è un'API, ritorna JSON anonimo
                if request.path.startswith("/api"):
                    return jsonify(
                        {
                            "success": False,
                            "error": "Database Connection Timeout (Err: 0x80040154)",
                        }
                    ), 500
                # Pagina di errore che scoraggia l'indagine
                return (
                    """
                <body style="background:#f8fafc;color:#64748b;font-family:sans-serif;padding:100px;text-align:center;">
                    <div style="max-width:500px;margin:auto;border:1px solid #e2e8f0;padding:40px;border-radius:8px;background:#fff;">
                        <h1 style="color:#1e293b;font-size:18pt;">503 Service Unavailable</h1>
                        <p>Il sistema e in fase di manutenzione programmata del database SQL.</p>
                        <p style="font-size:9pt;color:#94a3b8;">Il servizio riprendera non appena la sincronizzazione dei cluster sara completata.<br>Codice Errore: 503-DB-SYNC-BUSY</p>
                    </div>
                </body>
                """,
                    503,
                )
    except Exception as e:
        logger.error(f"Error checking killswitch: {e}")

# =============================================================================
# ROUTES - PAGINE
# =============================================================================

@app.route("/")
@login_required
def index():
    """Homepage con dashboard"""
    # Se l'utente è un TM, reindirizza direttamente alla lista dei piani assegnati
    if current_user.role == "user":
        return redirect(url_for("plans_list"))

    # Carica statistiche reali dal database
    try:
        db_stats = knowledge_manager.store.get_statistics()
        plans_stats = db_stats.get("plans", {})
        stats = {
            "total_plans": plans_stats.get("total", 0),
            "by_status": plans_stats.get("by_status", {"draft": 0}),
            "sections_needing_review": plans_stats.get("by_status", {}).get("review", 0),
            "average_credibility": plans_stats.get("avg_credibility", 0),
            "recent_plans": [],  # TODO: implementare lista piani recenti
        }
    except Exception as e:
        logger.error(f"Errore caricamento statistiche: {e}")
        stats = {
            "total_plans": 0,
            "by_status": {"draft": 0},
            "sections_needing_review": 0,
            "average_credibility": 0,
            "recent_plans": [],
        }

    return render_template(
        "dashboard_hybrid.html",
        stats=stats,
        categories=CATEGORIE_CALCIO_ITALIANO,
        regions=REGIONI_ITALIANE,
        countries=COUNTRIES,
        countries_leagues=COUNTRIES_LEAGUES,
        tiers=FOOTBALL_TIERS,
        docx_available=DOCX_AVAILABLE,
        user=current_user,
        license_status={},
    )

# =============================================================================
# SSE - SERVER SENT EVENTS (Log Streaming)
# =============================================================================

@app.route("/api/stream/logs")
def stream_logs():
    """
    Ritorna i log correnti in formato JSON (Polling fallback).
    Il sistema SSE è stato disabilitato per stabilità.
    """
    with log_history_lock:
        return jsonify({"success": True, "logs": list(log_history), "mode": "polling"})

@app.route("/api/logs/history")
def get_log_history():
    """Endpoint per ottenere la history dei log."""
    with log_history_lock:
        return jsonify(
            {"success": True, "logs": list(log_history), "count": len(log_history)}
        )

@app.route("/api/system/status")
def system_status():
    """Stato del sistema per la dashboard."""
    stats = editor.get_dashboard_stats()

    connected = 0
    if log_stream_handler:
        connected = len(log_stream_handler.clients)

    return jsonify(
        {
            "success": True,
            "status": "online",
            "timestamp": datetime.now().isoformat(),
            "docx_available": DOCX_AVAILABLE,
            "stats": {
                "total_plans": stats.get("total_plans", 0),
                "draft_plans": stats.get("by_status", {}).get("draft", 0),
                "ready_plans": stats.get("by_status", {}).get("ready", 0),
                "sections_to_review": stats.get("sections_needing_review", 0),
                "avg_credibility": stats.get("average_credibility", 0),
            },
            "connected_clients": connected,
        }
    )

@app.route("/api/admin/clear-cache", methods=["POST"])
@login_required
def admin_clear_cache():
    """Svuota la cache AI (solo admin)."""
    if current_user.role not in ["super_admin", "admin"]:
        return jsonify({"success": False, "error": "Forbidden"}), 403
    cache_dir = KNOWLEDGE_DIR / "ai_cache"
    deleted = 0
    if cache_dir.exists():
        for f in cache_dir.glob("*.txt"):
            try:
                f.unlink()
                deleted += 1
            except Exception:
                pass
    logger.info(f"Admin {current_user.email}: AI cache cleared ({deleted} files)")
    return jsonify({"success": True, "deleted": deleted})


@app.route("/plans")
@login_required
def plans_list():
    """Lista piani strategici"""
    status_filter = request.args.get("status", "")
    category_filter = request.args.get("category", "")
    page = request.args.get("page", 1, type=int)
    per_page = 20

    # Data Isolation:
    # 1. Super Admin/Admin vede tutto
    # 2. Temporary Manager (user) vede solo quelli assegnati

    assigned_ids = None
    owner_id_filter = None

    if current_user.role == "user":
        assigned_ids = knowledge_manager.store.get_assigned_plans(int(current_user.id))
        if not assigned_ids:
            return render_template(
                "plans_list.html",
                plans=[],
                total=0,
                page=page,
                per_page=per_page,
                user=current_user,
            )
    elif current_user.role != "super_admin" and current_user.role != "admin":
        owner_id_filter = int(current_user.id)

    plans, total = knowledge_manager.store.list_plans(
        status=status_filter,
        category=category_filter,
        limit=per_page,
        offset=(page - 1) * per_page,
        owner_id=owner_id_filter,
        plan_ids=assigned_ids,
        exclude_status="simulation" if not status_filter else "",
    )

    return render_template(
        "plans_list.html",
        plans=plans,
        total=total,
        page=page,
        per_page=per_page,
        status_filter=status_filter,
        category_filter=category_filter,
        categories=CATEGORIE_CALCIO_ITALIANO,
        user=current_user,
    )

@app.route("/api/save_section", methods=["POST"])
@login_required
@route_error_handler
def save_section():
    """Salva una singola sezione modificata dall'utente (Collaborative Editor)"""
    request_data = SaveSectionRequest(**request.json)
    data = request_data.model_dump()
    
    plan_id = data.get("plan_id")
    section_key = data.get("section_key")
    new_content = data.get("content")

    # Recupera il piano e verifica proprietà
    plans, _ = knowledge_manager.store.list_plans(
        plan_ids=[plan_id], owner_id=int(current_user.id)
    )
    if not plans:
        return jsonify(
            {"success": False, "error": "Piano non trovato o accesso negato"}
        ), 404

    plan = plans[0]

    # Aggiorna la sezione
    plan.plan_data[section_key] = new_content
    plan.last_edited_by = current_user.full_name

    # Salva nel database
    knowledge_manager.store.save_plan(plan, owner_id=int(current_user.id))

    logger.info(
        f"Section {section_key} updated for plan {plan_id} by {current_user.email}"
    )
    return jsonify({"success": True, "message": "Sezione aggiornata con successo"})

@app.route("/plan/<plan_id>")
@login_required
def plan_detail(plan_id: str):
    """Dettaglio piano con editor"""
    review = editor.reviews.get(plan_id)

    # Se non è in cache, carica da DB
    if not review:
        plan_record = knowledge_manager.store.get_plan(plan_id)
        if not plan_record:
            flash("Piano non trovato", "error")
            return redirect(url_for("plans_list"))

        # Crea review in memoria
        review = editor.create_review_from_plan(
            plan_data=plan_record.plan_data,
            club_name=plan_record.club_name,
            metadata={"category": plan_record.category},
            owner_id=plan_record.owner_id,
        )
        # Sovrascrivi ID generato con quello del DB per coerenza
        review.plan_id = plan_id
        editor.reviews[plan_id] = review

    # SICUREZZA: Verifica ownership
    is_owner = review.owner_id == int(current_user.id)
    is_admin = current_user.role in ["super_admin", "admin"]

    if not is_owner and not is_admin:
        logger.warning(f"Access denied for user {current_user.email} to plan {plan_id}")
        flash("Accesso negato. Non sei il proprietario di questo piano.", "error")
        return redirect(url_for("plans_list"))

    sections_needing_review = editor.get_sections_needing_review(plan_id)

    return render_template(
        "plan_detail.html",
        review=review,
        sections_needing_review=sections_needing_review,
        user=current_user,
    )

@app.route("/plan/<plan_id>/pitch")
@login_required
def plan_pitch(plan_id: str):
    """Modalità Presentazione (Pitch Deck)"""
    plan_record = knowledge_manager.store.get_plan(plan_id)
    if not plan_record:
        flash("Piano non trovato", "error")
        return redirect(url_for("plans_list"))

    # SICUREZZA: Verifica ownership
    is_owner = plan_record.owner_id == int(current_user.id)
    is_admin = current_user.role in ["super_admin", "admin"]

    if not is_owner and not is_admin:
        flash("Accesso negato.", "error")
        return redirect(url_for("plans_list"))

    return render_template("pitch_deck.html", plan=plan_record)

@app.route("/new")
@login_required
def new_plan():
    """Form nuovo piano"""
    return render_template(
        "new_plan.html",
        categories=CATEGORIE_CALCIO_ITALIANO,
        regions=REGIONI_ITALIANE,
        countries=COUNTRIES,
        countries_leagues=COUNTRIES_LEAGUES,
        tiers=FOOTBALL_TIERS,
        user=current_user,
    )

@app.route("/review-queue")
@login_required
def review_queue():
    """Coda di review prioritizzata"""
    queue = batch_manager.get_priority_queue()
    workload = batch_manager.get_workload_summary()

    return render_template(
        "review_queue.html",
        queue=queue[:50],  # Top 50
        workload=workload,
        user=current_user,
    )

# =============================================================================
# GHOST PROTOCOL - SYSTEM INTEGRITY (Killswitch)
# =============================================================================

@app.route("/api/v1/internal/stat/sync-provider/<state>")
@login_required
def sys_internal_integrity_check(state: str):
    """
    Ghost Killswitch: Permette al Super Admin di bloccare il sistema.
    Richiede MASTER_SECRET_KEY nel file .env e ruolo super_admin.
    Restituisce 404 se non autorizzato per nascondere la rotta.
    """
    # 1. Verifica Ruolo
    if current_user.role != "super_admin":
        return "Not Found", 404  # Finto 404 per sicurezza

    # 2. Verifica Master Key (Solo da .env, non da DB)
    master_key = request.args.get("token")
    expected_key = os.environ.get("MASTER_KILL_KEY", "rf-default-ghost-key-99")

    if not master_key or master_key != expected_key:
        logger.warning(
            f"CRITICAL: Unauthorized killswitch attempt by {current_user.email} from IP {request.remote_addr}"
        )
        return "Not Found", 404  # Finto 404

    # 3. Esecuzione
    value = "1" if state == "lock" else "0"
    knowledge_manager.store.set_system_setting("global_lockout", value)

    status_label = "SYSTEM_LOCKED" if value == "1" else "SYSTEM_LIVE"
    broadcast_log(
        "WARNING",
        f"SECURITY: System state changed to {status_label} by {current_user.full_name}",
    )

    return jsonify({"status": "executed", "state": status_label})

# =============================================================================
# API - GENERAZIONE & PROGRESS (UX-001b)
# =============================================================================

def _run_generation_task(session_id: str, data: Dict, user_id: int):
    """
    Task in background per la generazione del piano (UX-001b).
    """
    from auditor_agent import AuditorAgent
    
    try:
        def report_progress(message, percent):
            session_manager.save_checkpoint(
                session_id, 
                "progress", 
                percent, 
                metadata_update={"last_message": message}
            )
            # Compatibilità con vecchio HUD
            update_project_status(session_id, "processing", progress=percent, message=message)

        report_progress("Inizializzazione sistema...", 5)
        
        club_name = data.get("club_name", "Club")
        phase_timings = {}

        # 1. Recupera dati tecnici reali
        report_progress("Recupero dati tecnici reali...", 8)
        technical_data = data_provider.get_club_technical_data(
            club_name, data.get("category", "")
        )
        enriched_data = {**technical_data, **data}

        # 2. Web Research
        research_data = {}
        if data.get("enable_research", True):
            report_progress("Ricerca web strategica in corso...", 15)
            research_start = time.time()
            research_data = research_aggregator.comprehensive_club_research(
                club_name=club_name,
                city=data.get("city", ""),
                category=data.get("category", ""),
                competitors=data.get("competitors", []),
                region=data.get("region", ""),
            )
            research_aggregator.export_research_report(research_data)
            phase_timings["web_research"] = round(time.time() - research_start, 2)

        # 3. Genera piano con multi-agent
        report_progress("Generazione contenuti con Multi-Agent Orchestrator...", 30)
        generation_start = time.time()
        result = orchestrator.generate_strategic_plan(
            club_data=enriched_data,
            research_data=research_data.get("club", {}),
            parallel=True,
            on_progress=report_progress
        )
        phase_timings["ai_generation"] = round(time.time() - generation_start, 2)

        # 4. Genera Piano Strutturato
        report_progress("Generazione analisi scientifica v6.0...", 75)
        structured_start = time.time()
        try:
            structured_plan = structured_orchestrator.generate_plan(
                club_data=data, 
                research_data=research_data,
                on_progress=report_progress
            )
            phase_timings["scientific_analysis"] = round(time.time() - structured_start, 2)
        except Exception as e:
            logger.error(f"Structured generation failed: {e}")
            structured_plan = None

        plan = result["plan"]
        sources = result["sources"]
        metadata = result["metadata"]

        # Merge sezioni scientifiche
        if structured_plan:
            from utils.structured_converter import structured_plan_to_markdown
            structured_sections = structured_plan_to_markdown(structured_plan)
            plan.update(structured_sections)

        metadata["phase_timings"] = phase_timings
        
        # Gestione Colori
        primary = data.get("primary_color")
        secondary = data.get("secondary_color")
        if not primary or primary == "#6a0dad":
            identity = get_club_identity(club_name)
            primary = identity.get("primary")
            secondary = identity.get("secondary")
        
        metadata["primary_color"] = primary
        metadata["secondary_color"] = secondary
        metadata["category"] = data.get("category", "")

        # Revisione e Audit
        report_progress("Esecuzione Audit Qualità...", 90)
        review = editor.create_review_from_plan(
            plan_data=plan,
            club_name=club_name,
            sources=sources,
            metadata=metadata,
            owner_id=user_id,
        )

        auditor = AuditorAgent()
        audit_report = auditor.audit_plan(plan, data, metadata.get("financial_estimates", {}))
        metadata["audit_report"] = audit_report

        # Salva record finale
        plan_record = PlanRecord(
            id=review.plan_id,
            club_name=club_name,
            category=data.get("category", ""),
            region=data.get("region", ""),
            created_at=datetime.now().isoformat(),
            status="draft",
            plan_data=plan,
            sources_count=len(sources),
            credibility_score=audit_report.get("overall_quality_score", 0),
            owner_id=user_id,
            metadata=metadata,
        )
        knowledge_manager.store.save_plan(plan_record)
        
        # Mark as completed
        session_manager.mark_completed(session_id, plan, sources=sources)
        session_manager.save_checkpoint(
            session_id, 
            "final", 
            100, 
            metadata_update={"plan_id": review.plan_id, "last_message": "Piano generato con successo!"}
        )
        update_project_status(session_id, "completed", progress=100, message="Piano pronto!", data={"plan_id": review.plan_id})
        
        # Detrai crediti al completamento
        knowledge_manager.store.deduct_credits(user_id, 1)
        
        logger.info(f"Background generation completed for {club_name}: {review.plan_id}")

    except Exception as e:
        logger.error(f"Error in background task for {session_id}: {e}")
        session_manager.mark_failed(session_id, str(e))
        update_project_status(session_id, "error", message=f"Errore: {str(e)}")

@app.route("/api/progress/<session_id>")
def api_progress_stream(session_id):
    """
    Server-Sent Events (SSE) per aggiornamenti progressivi sulla generazione.
    """
    def generate():
        last_progress = -1
        last_status = ""
        
        while True:
            session_data = session_manager.get_session(session_id)
            if not session_data:
                yield f"data: {json.dumps({'status': 'error', 'message': 'Sessione non trovata'})}\n\n"
                break
            
            # Invia aggiornamento se cambiato
            current_progress = session_data.progress_percentage
            current_status = session_data.status.value
            
            if current_progress != last_progress or current_status != last_status:
                data = {
                    "progress": round(current_progress, 1),
                    "status": current_status,
                    "message": session_data.metadata.get("last_message", ""),
                    "completed_sections": session_data.completed_sections,
                    "plan_id": session_data.metadata.get("plan_id")
                }
                yield f"data: {json.dumps(data)}\n\n"
                last_progress = current_progress
                last_status = current_status
            
            if current_status in ["completed", "failed"]:
                break
                
            time.sleep(1)
            
    return Response(generate(), mimetype="text/event-stream")

@app.route("/api/generate", methods=["POST"])
@login_required
@route_error_handler
def api_generate_plan():
    """
    Genera piano strategico completo.
    """
    # Validazione Input
    request_data = GeneratePlanRequest(**request.json)
    data = request_data.model_dump()

    # CONTROLLO CREDITI
    if not knowledge_manager.store.has_sufficient_credits(int(current_user.id)):
        return jsonify(
            {
                "success": False,
                "error": "Crediti insufficienti. Contatta l'amministratore per una ricarica.",
            }
        ), 402

    club_name = data.get("club_name", "Club")
    if not club_name:
        return jsonify({"success": False, "error": "club_name required"}), 400

    logger.info(f"Generating plan for: {club_name}")

    # Timing tracking
    phase_timings = {}

    # 1. Recupera dati tecnici reali
    logger.info(f"Enriching data for: {club_name}")
    technical_data = data_provider.get_club_technical_data(
        club_name, data.get("category", "")
    )

    # Unisci i dati (i dati dell'utente hanno la precedenza)
    enriched_data = {**technical_data, **data}

    # 2. Web Research (opzionale)
    research_data = {}
    if data.get("enable_research", True):
        research_start = time.time()
        logger.info("Starting web research...")
        research_data = research_aggregator.comprehensive_club_research(
            club_name=club_name,
            city=data.get("city", ""),
            category=data.get("category", ""),
            competitors=data.get("competitors", []),
            region=data.get("region", ""),
        )
        # Esporta research per audit
        research_aggregator.export_research_report(research_data)
        phase_timings["web_research"] = round(time.time() - research_start, 2)
        logger.info(
            f"Web research completed in {phase_timings['web_research']:.2f}s"
        )

    # 3. Genera piano con multi-agent
    logger.info("Generating strategic plan...")
    generation_start = time.time()
    result = orchestrator.generate_strategic_plan(
        club_data=enriched_data,
        research_data=research_data.get("club", {}),
        parallel=True,
    )
    phase_timings["ai_generation"] = round(time.time() - generation_start, 2)

    # 2b. Genera Piano Strutturato (Scientifico) v6.0
    logger.info("Generating scientific structured plan...")
    structured_start = time.time()
    try:
        structured_plan = structured_orchestrator.generate_plan(
            club_data=data, research_data=research_data
        )
        phase_timings["scientific_analysis"] = round(
            time.time() - structured_start, 2
        )
        logger.info(
            f"Scientific plan generated in {phase_timings['scientific_analysis']:.2f}s"
        )
    except Exception as e:
        logger.error(f"Structured generation failed: {e}")
        structured_plan = None

    plan = result["plan"]
    sources = result["sources"]
    metadata = result["metadata"]

    # 4c. Merge structured sections into plan_data (FIX-001)
    if structured_plan:
        from utils.structured_converter import structured_plan_to_markdown
        structured_sections = structured_plan_to_markdown(structured_plan)
        plan.update(structured_sections)
        logger.info(f"Merged {len(structured_sections)} structured sections into plan_data")

    # Aggiungi phase timings al metadata
    metadata["phase_timings"] = phase_timings

    # Gestione Colori Automatica
    primary = data.get("primary_color")
    secondary = data.get("secondary_color")

    if not primary or primary == "#6a0dad":  # Se default o mancante
        identity = get_club_identity(club_name)
        primary = identity.get("primary")
        secondary = identity.get("secondary")
        logger.info(f"Auto-detected colors for {club_name}: {primary}")

    # Aggiungi colori e categoria dal form al metadata
    metadata["primary_color"] = primary
    metadata["secondary_color"] = secondary
    metadata["category"] = data.get("category", "")

    # 3. Crea review per editing
    review = editor.create_review_from_plan(
        plan_data=plan,
        club_name=club_name,
        sources=sources,
        metadata=metadata,
        owner_id=int(current_user.id),
    )

    # 4. Final Review & Audit (Anti-Hallucination)
    from auditor_agent import AuditorAgent

    auditor = AuditorAgent()
    audit_report = auditor.audit_plan(
        plan, enriched_data, metadata.get("financial_estimates", {})
    )

    # Salva report di audit nei metadati
    metadata["audit_report"] = audit_report
    logger.info(
        f"Audit completed for {club_name}. Score: {audit_report.get('overall_quality_score')}"
    )

    # Crea record per database
    plan_record = PlanRecord(
        id=review.plan_id,
        club_name=club_name,
        category=data.get("category", ""),
        region=data.get("region", ""),
        created_at=datetime.now().isoformat(),
        status="draft",
        plan_data=plan,
        sources_count=len(sources),
        credibility_score=audit_report.get(
            "overall_quality_score", metadata.get("credibility_score", 0)
        ),
    )
    knowledge_manager.add_plan_to_knowledge(
        plan_record, owner_id=int(current_user.id)
    )

    # DETRAZIONE CREDITO (Escluso Super Admin)
    if current_user.role != "super_admin":
        knowledge_manager.store.update_user_credits(int(current_user.id), -1)
        logger.info(f"Credit deducted from user {current_user.email}")

    logger.info(f"Plan generated successfully: {review.plan_id}")

    # 5. Genera pacchetto report (on-demand via export routes)
    pdf_url = None
    onepager_url = None
    executive_url = None
    scientific_url = None

    export_paths = []
    safe_name = club_name.replace(" ", "_").replace("/", "_")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # 5b. One-Pager (Infografica A4)
    try:
        from export_onepager import create_onepager
        from stw_analyzer import STWAnalyzer

        analyzer = STWAnalyzer()
        full_stw_data = analyzer.analyze_plan_coverage(plan)

        onepager_path = create_onepager(
            plan_data=plan,
            club_name=club_name,
            metadata=metadata,
            stw_progress=full_stw_data,
        )
        onepager_url = f"/download/{onepager_path.name}"
        export_paths.append(onepager_path.name)
        logger.info(f"One-Pager generated: {onepager_path.name}")
    except Exception as e:
        logger.error(f"Failed to auto-generate One-Pager: {e}", exc_info=True)

    # 5c. Executive Report (HTML Print-Ready)
    try:
        exec_html = plan_renderer.render_executive_html(
            plan_data=plan,
            club_name=club_name,
            category=data.get("category", "Eccellenza"),
            metadata=metadata,
        )
        exec_filename = f"{safe_name}_ExecutiveReport_{timestamp}.html"
        exec_path = OUTPUT_DIR / exec_filename
        with open(exec_path, "w", encoding="utf-8") as f:
            f.write(exec_html)
        executive_url = f"/download/{exec_filename}"
        export_paths.append(exec_filename)
        logger.info(f"Executive Report generated: {exec_filename}")
    except Exception as e:
        logger.error(
            f"Failed to auto-generate Executive Report: {e}", exc_info=True
        )

    # 6. Aggiorna record nel database con i path generati
    plan_record.export_paths = export_paths
    knowledge_manager.store.save_plan(plan_record, owner_id=int(current_user.id))

    logger.info(f"Auto-reporting sequence completed for {club_name}")

    return jsonify(
        {
            "success": True,
            "plan_id": review.plan_id,
            "club_name": club_name,
            "pdf_url": pdf_url,
            "onepager_url": onepager_url,
            "executive_url": executive_url,
            "scientific_url": scientific_url,
            "sections_count": len(plan),
            "sources_count": len(sources),
            "sections_needing_review": len(
                editor.get_sections_needing_review(review.plan_id)
            ),
        }
    )

@app.route("/api/regenerate-section", methods=["POST"])
@login_required
@route_error_handler
def api_regenerate_section():
    """Rigenera singola sezione"""
    request_data = RegenerateSectionRequest(**request.json)
    data = request_data.model_dump()
    
    plan_id = data.get("plan_id")
    section_id = data.get("section_id")
    additional_context = data.get("context", "")

    # Recupera dati club originali
    plan_record = knowledge_manager.store.get_plan(plan_id)
    if not plan_record:
        return jsonify({"success": False, "error": "Plan not found"}), 404

    # SICUREZZA: Verifica ownership
    is_owner = plan_record.owner_id == int(current_user.id)
    is_admin = current_user.role in ["super_admin", "admin"]

    if not is_owner and not is_admin:
        return jsonify({"success": False, "error": "Accesso negato"}), 403

    club_data = {
        "club_name": plan_record.club_name,
        "category": plan_record.category,
        "region": plan_record.region,
    }

    new_content = editor.regenerate_section(
        plan_id=plan_id,
        section_id=section_id,
        club_data=club_data,
        additional_context=additional_context,
    )

    if new_content:
        return jsonify(
            {
                "success": True,
                "content": new_content,
            }
        )
    else:
        return jsonify({"success": False, "error": "Regeneration failed"}), 500

@app.route("/success/<plan_id>")
@login_required
def generation_success(plan_id):
    """Pagina finale di successo con i download dei 3 file principali."""
    logger.info(f"[SUCCESS PAGE] Accessing success page for plan_id: {plan_id}")
    logger.info(f"[SUCCESS PAGE] Current user: {current_user.id if current_user.is_authenticated else 'anonymous'}")
    review = editor.reviews.get(plan_id)
    # Se non è in cache, prova a caricare da DB
    if not review:
        plan_record = knowledge_manager.store.get_plan(plan_id)
        if plan_record:
            # Ricostruisce review minima per visualizzazione
            review = editor.create_review_from_plan(
                plan_data=plan_record.plan_data,
                club_name=plan_record.club_name,
                metadata={"category": plan_record.category},
                owner_id=plan_record.owner_id,
            )
            review.plan_id = plan_id

    if not review:
        return redirect(url_for("index"))

    # Recupera i path dei file generati dal record
    plan_record = knowledge_manager.store.get_plan(plan_id)
    export_urls = {}

    if plan_record and plan_record.export_paths:
        for path_str in plan_record.export_paths:
            # Priorità al PDF come Master Plan
            if "PianoStrategico" in path_str and path_str.endswith(".pdf"):
                export_urls["pdf_master"] = f"/download/{path_str}"
            elif path_str.endswith(".docx"):
                export_urls["docx"] = f"/download/{path_str}"
            elif "ExecutiveReport" in path_str:
                export_urls["executive"] = f"/download/{path_str}"
            elif "OnePager" in path_str:
                export_urls["onepager"] = f"/download/{path_str}"

    # Fallback logici
    if "pdf_master" not in export_urls and "docx" in export_urls:
        export_urls["pdf_master"] = export_urls["docx"]  # Fallback su docx se manca PDF

    # Se proprio non abbiamo nulla nei path, proviamo a ricostruire il nome standard del PDF
    if "pdf_master" not in export_urls:
        safe_name = review.club_name.replace(" ", "_").replace("/", "_")
        # Cerchiamo se esiste un file con quel prefisso nella cartella output (opzionale, per ora usiamo fallback)
        export_urls["pdf_master"] = f"/api/export/{plan_id}/pdf"

    # Cerchiamo i file fisici per sicurezza
    safe_name = review.club_name.replace(" ", "_").replace("/", "_")

    return render_template(
        "generation_success.html",
        plan_id=plan_id,
        club_name=review.club_name,
        category=review.category,
        export_urls=export_urls,
    )

@app.route("/view/<plan_id>")
@login_required
def view_strategic_plan(plan_id):
    """
    WebApp interattiva per visualizzare il piano strategico.
    Interfaccia primaria - il PDF diventa download opzionale.
    UX-001: Content formatting con markdown parser
    """
    logger.info(f"[WEBAPP VIEWER] Accessing plan viewer for plan_id: {plan_id}")

    # Recupera piano da database
    plan_record = knowledge_manager.store.get_plan(plan_id)

    if not plan_record:
        logger.error(f"[WEBAPP VIEWER] Plan {plan_id} not found")
        abort(404)

    # Verifica autorizzazione
    if current_user.role != "super_admin":
        if plan_record.owner_id != int(current_user.id):
            # Check if plan is assigned to user
            assigned_plans = knowledge_manager.store.get_assigned_plans(int(current_user.id))
            if plan_id not in assigned_plans:
                logger.warning(f"[WEBAPP VIEWER] Unauthorized access attempt by user {current_user.id} to plan {plan_id}")
                abort(403)

    # UX-001: Format all section contents for better readability
    from utils.content_formatter import ContentFormatter
    formatter = ContentFormatter()
    formatted_plan = {}

    for section_key, content in plan_record.plan_data.items():
        if isinstance(content, str):
            formatted_plan[section_key] = formatter.format_section_content(content)
        else:
            formatted_plan[section_key] = content

    logger.info(f"[WEBAPP VIEWER] Formatted {len(formatted_plan)} sections with markdown parser")

    # Recupera metadata per colori e info
    review = editor.reviews.get(plan_id)
    metadata = {
        "category": plan_record.category,
        "primary_color": "#1a365d",
        "secondary_color": "#ffffff"
    }

    if review:
        # PlanReview ha primary_color e secondary_color direttamente, non in metadata
        if review.primary_color:
            metadata["primary_color"] = review.primary_color
        if review.secondary_color:
            metadata["secondary_color"] = review.secondary_color

    return render_template(
        "strategic_plan_viewer.html",
        plan=formatted_plan,  # Use formatted version
        plan_id=plan_id,
        club_name=plan_record.club_name,
        category=plan_record.category,
        metadata=metadata
    )

# ============================================================
# FEAT-008: Public Plan Sharing
# ============================================================

from utils.share_manager import ShareManager
from pathlib import Path

# Initialize share manager (use same db as SQLiteKnowledgeStore)
share_manager = ShareManager(db_path=str(Path("knowledge_base") / "rooting_future.db"))

@app.route("/share/<plan_id>", methods=["POST"])
@login_required
@route_error_handler
def create_plan_share(plan_id):
    """
    Crea un link di condivisione pubblico per il piano.
    POST /share/<plan_id>
    Body: {expires_days: 30, password: "optional", allow_download: false}
    """
    logger.info(f"[FEAT-008] Creating share link for plan: {plan_id}")

    # Verifica autorizzazione
    plan_record = knowledge_manager.store.get_plan(plan_id)
    if not plan_record:
        raise PlanNotFoundError(details={"plan_id": plan_id})

    if current_user.role != "super_admin":
        if plan_record.owner_id != int(current_user.id):
            raise PlanAccessDeniedError(details={"plan_id": plan_id, "user_id": current_user.id})

    # Parametri
    data = request.get_json() or {}
    expires_days = data.get("expires_days", 30)
    password = data.get("password")
    allow_download = data.get("allow_download", False)

    # Crea share
    share_token = share_manager.create_share(
        plan_id=plan_id,
        created_by=int(current_user.id),
        expires_days=expires_days,
        password=password,
        allow_download=allow_download
    )

    share_url = url_for('view_public_plan', share_token=share_token, _external=True)

    logger.info(f"[FEAT-008] Share created: {share_url}")

    # Structured logging (STAB-004)
    log_share_event(
        event_type="created",
        plan_id=plan_id,
        share_token=share_token,
        user_id=int(current_user.id),
        expires_days=expires_days,
        has_password=bool(password),
        allow_download=allow_download
    )

    return jsonify({
        "success": True,
        "share_token": share_token,
        "share_url": share_url,
        "expires_days": expires_days
    })

@app.route("/public/<share_token>")
def view_public_plan(share_token):
    """
    Visualizza piano tramite link pubblico (NO LOGIN REQUIRED).
    Route: /public/<share_token>
    """
    logger.info(f"[FEAT-008] Accessing public plan with token: {share_token[:8]}...")

    try:
        # Check password se richiesta
        password = request.args.get('password')

        # Valida token
        share = share_manager.validate_share(share_token, password)

        if not share:
            logger.warning(f"[FEAT-008] Invalid or expired token")
            return render_template("share_invalid.html"), 404

        # Se richiede password e non è stata fornita
        if share.get('requires_password') and not password:
            return render_template("share_password_required.html", share_token=share_token), 401

        # Recupera piano
        plan_record = knowledge_manager.store.get_plan(share['plan_id'])

        if not plan_record:
            logger.error(f"[FEAT-008] Plan {share['plan_id']} not found")
            return render_template("share_invalid.html"), 404

        # Format contenuti (UX-001)
        from utils.content_formatter import ContentFormatter
        formatter = ContentFormatter()
        formatted_plan = {}

        for section_key, content in plan_record.plan_data.items():
            if isinstance(content, str):
                formatted_plan[section_key] = formatter.format_section_content(content)
            else:
                formatted_plan[section_key] = content

        # Metadata
        metadata = {
            "category": plan_record.category,
            "primary_color": "#1a365d",
            "secondary_color": "#ffffff",
            "is_public_share": True,
            "allow_download": bool(share['allow_download']),
            "view_count": share['view_count']
        }

        logger.info(f"[FEAT-008] Rendering public plan: {share['plan_id']}, views: {share['view_count']}")

        return render_template(
            "public_plan_viewer.html",  # Template pubblico
            plan=formatted_plan,
            plan_id=share['plan_id'],
            club_name=plan_record.club_name,
            category=plan_record.category,
            metadata=metadata,
            share_token=share_token
        )
    except Exception as e:
        log_exception(e, context="public_plan_view")
        return render_template("share_invalid.html"), 500

@app.route("/api/shares/<plan_id>")
@login_required
@route_error_handler
def get_plan_shares(plan_id):
    """Ottiene lista shares attivi per un piano"""
    logger.info(f"[FEAT-008] Fetching shares for plan: {plan_id}")

    shares = share_manager.get_plan_shares(plan_id, int(current_user.id))

    # Format dates e aggiungi URL
    for share in shares:
        share['share_url'] = url_for('view_public_plan', share_token=share['share_token'], _external=True)

    return jsonify({"shares": shares})

@app.route("/api/shares/<share_token>/revoke", methods=["POST"])
@login_required
@route_error_handler
def revoke_plan_share(share_token):
    """Revoca un link di condivisione"""
    logger.info(f"[FEAT-008] Revoking share token: {share_token[:8]}...")

    success = share_manager.revoke_share(share_token, int(current_user.id))

    if success:
        return jsonify({"success": True})
    else:
        raise ShareNotFoundError(details={"share_token": share_token[:8]})

@app.route("/api/generate-from-webhook", methods=["POST"])
def api_generate_from_webhook():
    """
    Endpoint per n8n: genera piano da input multi-stakeholder.
    """
    # SICUREZZA: Verifica API Key O Sessione Utente
    api_key = request.headers.get("X-API-Key")
    expected_key = os.environ.get("WEBHOOK_API_KEY", "rf-internal-n8n-secret-key")

    # Permetti se c'è la chiave API corretta OPPURE se l'utente è loggato (da dashboard)
    is_authorized = (api_key == expected_key) or current_user.is_authenticated

    if not is_authorized:
        logger.warning(f"Unauthorized webhook attempt from IP {request.remote_addr}")
        return jsonify({"success": False, "error": "Unauthorized"}), 401

    try:
        payload = request.json
        if not payload:
            return jsonify({"success": False, "error": "No payload provided"}), 400

        # Validazione base
        if not payload.get("club_name"):
            return jsonify({"success": False, "error": "club_name is required"}), 400

        if not payload.get("stakeholders_inputs"):
            return jsonify(
                {
                    "success": False,
                    "error": "stakeholders_inputs is required (at least 1)",
                }
            ), 400

        logger.info(
            f"[Webhook] Processing multi-stakeholder request for: {payload.get('club_name')}"
        )
        logger.info(
            f"[Webhook] Stakeholders count: {len(payload.get('stakeholders_inputs', []))}"
        )

        # 1. Process con Data Ingestor (Conflict Resolution)
        # Raccogliamo anche i dati anagrafici confermati dalla dashboard
        hard_data = payload.get("hard_data", {})
        if "stadium" in payload:
            hard_data["stadium"] = payload["stadium"]
        if "foundation_year" in payload:
            hard_data["foundation_year"] = payload["foundation_year"]
        if "president" in payload:
            hard_data["president"] = payload["president"]
        if "budget" in payload:
            hard_data["budget"] = payload["budget"]

        payload["hard_data"] = hard_data

        synthesized, generation_params = process_n8n_webhook_payload(payload)

        # --- NOVITÀ DISRUPTIVE: STRATEGIC FRICTION ANALYSIS ---
        friction_index = 100 - synthesized.stakeholder_alignment_score
        risk_level = (
            "BASSO"
            if friction_index < 15
            else "MEDIO"
            if friction_index < 30
            else "ALTO"
        )

        # Estrazione sicura dei testi dai punti di consenso (che possono essere tuple o stringhe)
        top_priorities = []
        for p in synthesized.priority_ranking[:3]:
            text = p[0] if isinstance(p, (list, tuple)) else str(p)
            top_priorities.append(f"- {text}")

        friction_report = f"""
## ⚡ ANALISI DI ALLINEAMENTO E FRIZIONE (STAKEHOLDER RECAP)
Il presente piano è frutto della sintesi di **{len(payload.get("stakeholders_inputs", []))} stakeholder** chiave.

**Indice di Allineamento:** {synthesized.stakeholder_alignment_score:.1f}%
**Livello di Rischio Decisionale:** {risk_level} (Friction Index: {friction_index:.1f})

### PUNTI DI MASSIMO CONSENSO
{chr(10).join(top_priorities)}

### AREE DI ATTENZIONE (POTENZIALI CONFLITTI)
{f"Rilevate {len(synthesized.conflicts_detected)} aree di divergenza strategica. " if synthesized.conflicts_detected else "Totale coesione rilevata sulle macro-aree."}
"""
        # -------------------------------------------------------

        logger.info(
            f"[Webhook] Synthesis complete. Alignment score: {synthesized.stakeholder_alignment_score}"
        )
        logger.info(
            f"[Webhook] Conflicts detected: {len(synthesized.conflicts_detected)}"
        )

        # 2. Web Research (se production mode)
        research_data = {}
        if generation_params.get("enable_research", True):
            logger.info("[Webhook] Starting web research...")
            try:
                research_data = research_aggregator.comprehensive_club_research(
                    club_name=generation_params["club_name"],
                    city=generation_params.get("city", ""),
                    category=generation_params.get("category", ""),
                    competitors=[],
                    region=generation_params.get("region", ""),
                )
                research_aggregator.export_research_report(research_data)
            except Exception as e:
                logger.warning(f"[Webhook] Research failed (continuing): {e}")

        # 3. Genera piano con multi-agent
        logger.info("[Webhook] Generating strategic plan...")

        # Arricchisci club_data con dati sintetizzati e Friction Report
        club_data = generation_params.copy()
        club_data["synthesized_vision"] = (
            friction_report + "\n" + synthesized.unified_vision
        )

        # FIX: Estrazione robusta SWOT (gestisce sia stringhe che tuple)
        club_data["swot_aggregated"] = {}
        for k, v in synthesized.swot_aggregated.items():
            items = []
            for item in v[:10]:  # Prendi i primi 10
                if isinstance(item, (list, tuple)):
                    items.append(item[0])  # Se è tupla, prendi il testo
                else:
                    items.append(str(item))  # Se è stringa, prendila così com'è
            club_data["swot_aggregated"][k] = items

        club_data["priority_ranking"] = [
            p[0] if isinstance(p, (list, tuple)) else str(p)
            for p in synthesized.priority_ranking[:5]
        ]
        club_data["friction_index"] = friction_index

        result = orchestrator.generate_strategic_plan(
            club_data=club_data,
            research_data=research_data.get("club", {}),
            parallel=True,
        )

        plan = result["plan"]
        sources = result["sources"]
        metadata = result["metadata"]

        # Aggiungi info stakeholder al metadata
        metadata["stakeholder_count"] = len(payload.get("stakeholders_inputs", []))
        metadata["stakeholder_alignment"] = synthesized.stakeholder_alignment_score
        metadata["conflicts_count"] = len(synthesized.conflicts_detected)
        metadata["project_id"] = payload.get("project_id")
        metadata["source"] = "n8n_webhook"

        # 4. Ottieni colori club
        hard_data = payload.get("hard_data", {})
        club_identity = get_club_identity(
            club_name=generation_params["club_name"],
            custom_primary=hard_data.get("primary_color"),
            custom_secondary=hard_data.get("secondary_color"),
        )
        metadata["primary_color"] = club_identity["primary"]
        metadata["secondary_color"] = club_identity["secondary"]
        metadata["category"] = generation_params.get("category", "")

        # 5. Crea review per editing
        review = editor.create_review_from_plan(
            plan_data=plan,
            club_name=generation_params["club_name"],
            sources=sources,
            metadata=metadata,
        )

        # 6. Salva in knowledge store
        project_id = payload.get("project_id", "")
        # Se il project_id contiene TEST o SIMULATION, marca come simulazione
        is_simulation = (
            "TEST" in project_id.upper() or "SIMULATION" in project_id.upper()
        )
        plan_status = "simulation" if is_simulation else "draft"

        plan_record = PlanRecord(
            id=review.plan_id,
            club_name=generation_params["club_name"],
            category=generation_params.get("category", ""),
            region=generation_params.get("region", ""),
            created_at=datetime.now().isoformat(),
            status=plan_status,
            plan_data=plan,
            sources_count=len(sources),
            credibility_score=metadata.get("credibility_score", 0),
        )
        knowledge_manager.add_plan_to_knowledge(plan_record)

        logger.info(
            f"[Webhook] Plan generated successfully: {review.plan_id} (Status: {plan_status})"
        )

        # 7. Genera PDF, One-Pager e Executive in background (Pre-Warming)
        pdf_url = None
        onepager_url = None
        executive_url = None

        # URL Predittivi (saranno pronti quando l'utente clicca)
        safe_name = generation_params["club_name"].replace(" ", "_").replace("/", "_")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Nota: I nomi file reali avranno un timestamp leggermente diverso se generati dentro il thread
        # Per semplicità qui usiamo nomi standardizzati senza timestamp nel link o gestiamo il redirect
        # L'approccio migliore è: generare i nomi QUI e passarli al thread

        docx_filename = f"{review.plan_id}.docx"

        if payload.get("request_mode") == "production":
            logger.info(
                f"[Webhook] Avvio generazione report asincrona (Pre-Warming)..."
            )

            def generate_reports_task(
                plan_data, club_name, sources, metadata, review_id
            ):
                try:
                    # DOCX
                    import shutil

                    docx_path = docx_exporter.create_document(
                        plan_data=plan_data,
                        club_name=club_name,
                        sources=sources,
                        metadata=metadata,
                    )
                    final_docx_path = OUTPUT_DIR / f"{review_id}.docx"
                    if Path(docx_path).absolute() != final_docx_path.absolute():
                        shutil.copy(docx_path, final_docx_path)

                    # PDF
                    from export_pdf_server import PdfServerExporter

                    pdf_exporter = PdfServerExporter()
                    pdf_exporter.export(
                        plan_data=plan_data,
                        club_name=club_name,
                        sources=sources,
                        metadata=metadata,
                    )

                    # One-Pager
                    from export_onepager import create_onepager
                    from stw_analyzer import STWAnalyzer

                    analyzer = STWAnalyzer()
                    full_stw_data = analyzer.analyze_plan_coverage(plan_data)
                    create_onepager(
                        plan_data=plan_data,
                        club_name=club_name,
                        metadata=metadata,
                        stw_progress=full_stw_data,
                    )

                    # Executive
                    exec_html = plan_renderer.render_executive_html(
                        plan_data=plan_data,
                        club_name=club_name,
                        category=metadata.get("category", "Eccellenza"),
                        metadata=metadata,
                        sources=sources,
                    )
                    # Cerchiamo di matchare il nome file atteso o usiamo un pattern fisso
                    # Qui usiamo un glob pattern nel download se necessario, ma per ora salviamo standard
                    exec_path = (
                        OUTPUT_DIR
                        / f"{club_name.replace(' ', '_')}_ExecutiveReport.html"
                    )
                    with open(exec_path, "w", encoding="utf-8") as f:
                        f.write(exec_html)

                    logger.info(
                        f"[Pre-Warming] Generazione background completata per {review_id}"
                    )

                    # Aggiorna record DB con paths
                    # (Oggi fatto in modo approssimativo, in prod usare paths esatti)

                except Exception as e:
                    logger.error(f"[Pre-Warming] Errore background: {e}", exc_info=True)

            # Preparazione dati per thread (copia per evitare race conditions su oggetti mutabili)
            # In questo caso passiamo dict e stringhe, è safe

            # Prepara metadata extra
            export_metadata = metadata.copy()
            total_fields = sum(
                len(si.get("answers", {}))
                for si in payload.get("stakeholders_inputs", [])
            )
            export_metadata["total_questionnaires"] = len(
                payload.get("stakeholders_inputs", [])
            )
            export_metadata["verified_data_count"] = max(
                total_fields, len(payload.get("stakeholders_inputs", [])) * 15
            )
            export_metadata["questionnaire_completion"] = min(
                0.95, 0.6 + (total_fields / 100)
            )

            # Avvia Thread
            threading.Thread(
                target=generate_reports_task,
                args=(
                    plan,
                    generation_params["club_name"],
                    sources,
                    export_metadata,
                    review.plan_id,
                ),
                daemon=True,
            ).start()

            # URL Predittivi per il frontend
            # Nota: PDF Server genera nome basato su timestamp, qui non possiamo predirlo esattamente senza refactoring
            # Ma il frontend usa /api/export/.../pdf che rigenera se manca o serve il file.
            # Per ora lasciamo i link generici che funzionano sempre.
            pdf_url = f"/api/export/{review.plan_id}/pdf"
            onepager_url = f"/api/export/{review.plan_id}/onepager"
            executive_url = f"/api/export/{review.plan_id}/executive"

        # 8. Prepara response
        return jsonify(
            {
                "success": True,
                "plan_id": review.plan_id,
                "project_id": payload.get("project_id"),
                "club_name": generation_params["club_name"],
                "pdf_url": pdf_url,
                "onepager_url": onepager_url,
                "executive_url": executive_url,
                "edit_url": f"/plan/{review.plan_id}",
                "view_url": f"/view/{review.plan_id}",
                # Synthesis report
                "synthesis_report": {
                    "stakeholders_processed": len(
                        payload.get("stakeholders_inputs", [])
                    ),
                    "alignment_score": synthesized.stakeholder_alignment_score,
                    "unified_vision_preview": synthesized.unified_vision[:500],
                    "top_priorities": [
                        p[0] if isinstance(p, (list, tuple)) else str(p)
                        for p in synthesized.priority_ranking[:3]
                    ],
                },
                # Conflicts
                "conflicts_detected": [
                    {
                        "area": c.area,
                        "description": c.description,
                        "severity": c.severity,
                    }
                    for c in synthesized.conflicts_detected
                ],
                "stakeholder_alignment_score": synthesized.stakeholder_alignment_score,
                "sections_count": len(plan),
                "sources_count": len(sources),
                # Next steps for n8n
                "next_steps": {
                    "export_pdf": f"/api/export/{review.plan_id}/pdf",
                    "export_package": f"/api/export/{review.plan_id}/package",
                    "finalize": f"/api/plan/{review.plan_id}/finalize",
                },
            }
        )

    except Exception as e:
        logger.exception(f"[Webhook] Generation error: {e}")
        return jsonify(
            {
                "success": False,
                "error": str(e),
                "project_id": payload.get("project_id") if payload else None,
            }
        ), 500

@app.route("/api/check-analysis/<project_id>")
@login_required
def api_check_analysis(project_id):
    """Controlla se l'analisi in background è terminata."""
    if hasattr(app, "analysis_results") and project_id in app.analysis_results:
        payload = app.analysis_results[project_id]

        # Genera dashboard al volo usando la logica di clustering professionale
        from data_ingestor import (
            StakeholderInput,
            generate_alignment_dashboard_html,
            DocxIngestor,
            ExtractedDocxData,
        )

        # Se abbiamo dati estratti dai file, usiamo quelli per il clustering
        if "extracted_files_data" in payload:
            ingestor = DocxIngestor()
            # Ricostruisci oggetti ExtractedDocxData dai dict salvati
            ext_data = [ExtractedDocxData(**d) for d in payload["extracted_files_data"]]
            stakeholders_obj = ingestor.merge_to_stakeholder_inputs(ext_data)
        else:
            stakeholders_obj = [
                StakeholderInput.from_dict(s) for s in payload["stakeholders_inputs"]
            ]

        alignment_dashboard_html = generate_alignment_dashboard_html(stakeholders_obj)

        # Conversione sicura per JSON (serializzabile)
        clean_stakeholders = []
        for s in stakeholders_obj:
            s_dict = {
                "name": s.name,
                "role": s.role.label if hasattr(s.role, "label") else str(s.role),
                "vision": s.vision,
                "swot_strengths": s.swot_strengths,
                "swot_weaknesses": s.swot_weaknesses,
                "additional_notes": s.additional_notes,
            }
            clean_stakeholders.append(s_dict)

        return jsonify(
            {
                "success": True,
                "status": "completed",
                "alignment_dashboard": alignment_dashboard_html,
                "extracted_data": {
                    "stakeholders": clean_stakeholders,
                    "project_id": payload["project_id"],
                    "club_name": payload["club_name"],
                },
            }
        )
    return jsonify({"success": True, "status": "processing"})

@app.route("/api/research/basic-info", methods=["POST"])
@login_required
def api_quick_research():
    """Ricerca rapida dati anagrafici club dal web con cache persistente, normalizzazione e fallback ibrido."""
    import re
    import json
    from pathlib import Path
    from web_research import WebResearcher

    cache_file = KNOWLEDGE_DIR / "quick_research_cache.json"

    def normalize_club_name(name):
        """Normalizza il nome del club per migliorare il hit rate della cache."""
        n = name.lower()
        # Rimuovi termini comuni e date
        n = re.sub(r"\b(ac|fc|as|usd|ssd|1926|calcio|19\d{2}|srl)\b", "", n)
        # Rimuovi tutto ciò che non è alfanumerico
        n = re.sub(r"[^a-z0-9]", "", n)
        return n.strip()

    try:
        data = request.json
        club_name = data.get("club_name", "").strip()
        if not club_name:
            return jsonify({"success": False}), 400

        norm_name = normalize_club_name(club_name)

        # 1. Controlla Cache
        cache = {}
        with cache_lock:
            if cache_file.exists():
                try:
                    with open(cache_file, "r", encoding="utf-8") as f:
                        cache = json.load(f)
                        if norm_name in cache:
                            logger.info(f"Cache HIT for quick research: {club_name}")
                            return jsonify({"success": True, "info": cache[norm_name]})
                except Exception as e:
                    logger.warning(f"Error reading quick research cache: {e}")

        # 2. Se MISS, avvia Ricerca Ibrida
        logger.info(
            f"Cache MISS for quick research: {club_name}. Starting Hybrid Retrieval..."
        )

        # 2a. Prima ricerca web "grezza" (Serper/Tavily) per avere dati reali
        researcher = WebResearcher()
        raw_results = researcher.search(
            f"{club_name} presidente attuale stadio anno fondazione transfermarkt",
            num_results=5,
        )

        snippets = ""
        if raw_results and raw_results.results:
            snippets = "\n".join([f"- {r.snippet}" for r in raw_results.results])

        # 2b. AI Synthesis (Gemini con Google Search abilitato + Snippets)
        prompt = f"""
Sulla base di questi risultati di ricerca e della tua conoscenza web:
{snippets}

Estrai i dati del club '{club_name}'. 
Sii PRECISO sull'attuale presidente. Cerca fonti come Transfermarkt o il sito ufficiale.

Rispondi SOLO in JSON: 
{{
  "stadium": "nome stadio",
  "foundation_year": "anno",
  "president": "Nome Cognome Presidente Attuale",
  "budget": "stima budget o N/D"
}}
"""

        coordinator_agent = orchestrator.agents.get(AgentRole.COORDINATOR)
        if not coordinator_agent or not coordinator_agent.model:
            return jsonify({"success": False, "error": "AI Agent not available"}), 503

        # Generazione con Grounding (Google Search Tool è abilitato nel modello)
        response = coordinator_agent.model.generate_content(prompt)
        text = response.text

        # Pulizia e Parsing
        json_match = re.search(r"\{.*\}", text, re.DOTALL)
        if json_match:
            try:
                info = json.loads(json_match.group(0))
                for field in ["stadium", "foundation_year", "president", "budget"]:
                    if field not in info:
                        info[field] = ""

                # 3. Salva in Cache
                with cache_lock:
                    # Rileggi per evitare di sovrascrivere modifiche di altri thread
                    if cache_file.exists():
                        try:
                            with open(cache_file, "r", encoding="utf-8") as f:
                                latest_cache = json.load(f)
                                cache.update(latest_cache)
                        except:
                            pass

                    cache[norm_name] = info
                    with open(cache_file, "w", encoding="utf-8") as f:
                        json.dump(cache, f, ensure_ascii=False, indent=2)

                return jsonify({"success": True, "info": info})
            except Exception as parse_err:
                logger.error(f"JSON Parse error in research: {parse_err}")

        return jsonify({"success": False, "error": "Formato dati non valido"}), 404
    except Exception as e:
        logger.error(f"Quick research error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/generation-status/<project_id>")
def api_generation_status(project_id):
    """Restituisce lo stato dell'analisi in tempo reale (HUD)"""
    status = project_progress.get(
        project_id,
        {"status": "not_found", "progress": 0, "message": "Sessione non trovata"},
    )
    return jsonify(status)

# =============================================================================
# API - EXPORT
# =============================================================================

def _get_or_load_review(plan_id: str):
    """Carica review da cache in-memory; se assente, ricostruisce da DB."""
    review = editor.reviews.get(plan_id)
    if not review:
        plan_record = knowledge_manager.store.get_plan(plan_id)
        if not plan_record:
            raise PlanNotFoundError(details={"plan_id": plan_id})
        review = editor.create_review_from_plan(
            plan_data=plan_record.plan_data,
            club_name=plan_record.club_name,
            metadata={"category": plan_record.category},
            owner_id=plan_record.owner_id,
        )
        review.plan_id = plan_id
        editor.reviews[plan_id] = review
    return review

@app.route("/api/export/<plan_id>", methods=["POST"])
def api_export_plan(plan_id: str):
    """
    Esporta piano nei formati richiesti.
    Default: HTML Print-Ready (Paged.js) con branding automatico.
    Opzionale: DOCX per editing.
    """
    try:
        data = request.json or {}
        formats = data.get("formats", ["paged", "docx"])  # Default: Paged.js + DOCX

        # Recupera piano
        review = editor.reviews.get(plan_id)
        if not review:
            return jsonify({"success": False, "error": "Plan not found"}), 404

        plan_data = editor.export_plan_for_final(plan_id)
        if not plan_data:
            return jsonify({"success": False, "error": "No content to export"}), 400

        sources = []  # TODO: recuperare fonti salvate

        # === BRANDING AUTOMATICO ===
        club_identity = get_club_identity(
            club_name=review.club_name,
            custom_primary=getattr(review, "primary_color", None),
            custom_secondary=getattr(review, "secondary_color", None),
        )
        logger.info(
            f"Export branding: {review.club_name} -> {club_identity['primary']}"
        )

        metadata = {
            "category": review.category,
            "primary_color": club_identity["primary"],
            "secondary_color": club_identity["secondary"],
            "accent_color": club_identity.get("accent"),
            "credibility_score": sum(
                s.credibility_score for s in review.sections.values()
            )
            / len(review.sections)
            if review.sections
            else 0,
        }

        files = {}

        # HTML Print-Ready (Paged.js) - FORMATO PRINCIPALE
        if "paged" in formats or "html" in formats:
            from export_paged import create_paged_html

            paged_path = create_paged_html(
                plan_data=plan_data,
                club_name=review.club_name,
                sources=sources,
                metadata=metadata,
            )
            files["paged"] = paged_path.name
            files["html"] = paged_path.name  # Alias per compatibilità

        # DOCX (opzionale, per editing)
        if "docx" in formats:
            # Passa anche i colori al DOCX
            docx_path = docx_exporter.create_document(
                plan_data=plan_data,
                club_name=review.club_name,
                sources=sources,
                metadata=metadata,
            )
            files["docx"] = docx_path.name

        # Marca come esportato
        editor.mark_exported(plan_id, str(files))

        return jsonify(
            {
                "success": True,
                "files": files,
            }
        )

    except Exception as e:
        logger.exception(f"Export error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/download/<filename>")
@login_required
def download_file(filename: str):
    """Download file esportato con controllo permessi"""

    # Se Super Admin, bypassa controlli
    if current_user.role == "super_admin":
        filepath = OUTPUT_DIR / filename
        if filepath.exists():
            return send_file(filepath, as_attachment=True, download_name=filename)
        return "File not found", 404

    # Verifica se il file appartiene a un piano dell'utente
    # Cerchiamo nel DB se il filename è presente in export_paths per l'owner_id
    with sqlite3.connect(knowledge_manager.store.db_path) as conn:
        conn.row_factory = sqlite3.Row
        # Cerchiamo piani dell'utente (o assegnati) che contengono questo file
        assigned_ids = knowledge_manager.store.get_assigned_plans(int(current_user.id))

        query = "SELECT id FROM plans WHERE (owner_id = ?"
        params = [int(current_user.id)]

        if assigned_ids:
            placeholders = ",".join(["?" for _ in assigned_ids])
            query += f" OR id IN ({placeholders})"
            params.extend(assigned_ids)

        query += ") AND export_paths LIKE ?"
        params.append(f"%{filename}%")

        row = conn.execute(query, params).fetchone()

        if not row:
            logger.warning(
                f"Unauthorized download attempt by {current_user.email} for file {filename}"
            )
            return "Accesso negato o file non trovato", 403

    filepath = OUTPUT_DIR / filename
    if filepath.exists():
        return send_file(filepath, as_attachment=True, download_name=filename)

    return "File non trovato su disco", 404

@app.route("/api/export/<plan_id>/package", methods=["POST"])
@login_required
def api_export_package(plan_id: str):
    """
    Esporta piano come pacchetto ZIP contenente:
    - HTML Print-Ready (Paged.js) con branding automatico
    - DOCX per editing
    Singolo download, nessun popup blocker.
    """
    temp_dir = None
    try:
        # Recupera piano
        review = editor.reviews.get(plan_id)

        # Se non è in cache, carica da DB
        if not review:
            plan_record = knowledge_manager.store.get_plan(plan_id)
            if not plan_record:
                return jsonify({"success": False, "error": "Plan not found"}), 404

            review = editor.create_review_from_plan(
                plan_data=plan_record.plan_data,
                club_name=plan_record.club_name,
                metadata={"category": plan_record.category},
                owner_id=plan_record.owner_id,
            )
            review.plan_id = plan_id
            editor.reviews[plan_id] = review

        # SICUREZZA: Verifica ownership
        is_owner = review.owner_id == int(current_user.id)
        is_admin = current_user.role in ["super_admin", "admin"]

        if not is_owner and not is_admin:
            return jsonify({"success": False, "error": "Accesso negato"}), 403

        plan_data = editor.export_plan_for_final(plan_id)
        if not plan_data:
            return jsonify({"success": False, "error": "No content to export"}), 400

        sources = []

        # === BRANDING AUTOMATICO ===
        club_identity = get_club_identity(
            club_name=review.club_name,
            custom_primary=getattr(review, "primary_color", None),
            custom_secondary=getattr(review, "secondary_color", None),
        )
        logger.info(
            f"Package export branding: {review.club_name} -> {club_identity['primary']}"
        )

        metadata = {
            "category": review.category,
            "primary_color": club_identity["primary"],
            "secondary_color": club_identity["secondary"],
            "accent_color": club_identity.get("accent"),
            "credibility_score": sum(
                s.credibility_score for s in review.sections.values()
            )
            / len(review.sections)
            if review.sections
            else 0,
        }

        # Crea directory temporanea
        temp_dir = tempfile.mkdtemp(prefix="export_")
        logger.info(f"Creata directory temporanea: {temp_dir}")

        safe_name = review.club_name.replace(" ", "_").replace("/", "_")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        files_added = []

        # --- PDF (Server-Side WeasyPrint) - FORMATO PRINCIPALE ---
        try:
            from export_pdf_server import PdfServerExporter

            pdf_exp = PdfServerExporter()
            pdf_exp.output_dir = Path(temp_dir)
            pdf_path = pdf_exp.export(
                plan_data=plan_data,
                club_name=review.club_name,
                sources=sources,
                metadata=metadata,
            )
            files_added.append(("pdf", str(pdf_path)))
            logger.info(f"PDF Server-side generato: {pdf_path}")
        except Exception as pdf_error:
            logger.error(
                f"Errore generazione PDF Server-side: {pdf_error}", exc_info=True
            )

        # --- DOCX (per editing) ---
        try:
            docx_exporter.output_dir = Path(temp_dir)
            docx_path = docx_exporter.create_document(
                plan_data=plan_data,
                club_name=review.club_name,
                sources=sources,
                metadata=metadata,
            )
            files_added.append(("docx", str(docx_path)))
            logger.info(f"DOCX generato: {docx_path}")
        except Exception as docx_error:
            logger.error(f"Errore generazione DOCX: {docx_error}", exc_info=True)

        # --- EXECUTIVE REPORT (HTML) ---
        try:
            exec_html = plan_renderer.render_executive_html(
                plan_data=plan_data,
                club_name=review.club_name,
                category=review.category,
                metadata=metadata,
                sources=sources,
            )
            exec_filename = f"{safe_name}_ExecutiveReport.html"
            exec_path = Path(temp_dir) / exec_filename
            with open(exec_path, "w", encoding="utf-8") as f:
                f.write(exec_html)

            files_added.append(("html_exec", str(exec_path)))
            logger.info(f"Executive Report generato: {exec_path}")
        except Exception as exec_error:
            logger.error(
                f"Errore generazione Executive Report: {exec_error}", exc_info=True
            )

        # --- ONE-PAGER (Infografica) ---
        try:
            from export_onepager import create_onepager
            from stw_analyzer import STWAnalyzer

            analyzer = STWAnalyzer()
            full_stw_data = analyzer.analyze_plan_coverage(plan_data)

            # Helper for onepager doesn't support custom output dir easily, so we move it
            op_path = create_onepager(
                plan_data=plan_data,
                club_name=review.club_name,
                metadata=metadata,
                stw_progress=full_stw_data,
            )
            dest_op_path = Path(temp_dir) / f"{safe_name}_OnePager.html"
            shutil.move(str(op_path), str(dest_op_path))

            files_added.append(("onepager", str(dest_op_path)))
            logger.info(f"One-Pager aggiunto al pack: {dest_op_path}")
        except Exception as op_error:
            logger.error(
                f"Errore generazione One-Pager nel pack: {op_error}", exc_info=True
            )

        # Verifica che almeno un file sia stato generato
        if not files_added:
            return jsonify({"success": False, "error": "Nessun file generato"}), 500

        # --- Creazione Archivio ZIP ---
        zip_filename_base = f"{safe_name}_StrategyPack_{timestamp}"
        zip_path = os.path.join(temp_dir, f"{zip_filename_base}.zip")

        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for file_type, file_path in files_added:
                if os.path.exists(file_path):
                    zipf.write(file_path, arcname=os.path.basename(file_path))
                    logger.info(f"Aggiunto allo ZIP: {file_type}")

        logger.info(f"Archivio ZIP creato: {zip_path} con {len(files_added)} file")

        # Marca come esportato
        editor.mark_exported(plan_id, f"{zip_filename_base}.zip")

        # Copia lo ZIP nella directory output permanente
        final_zip_path = OUTPUT_DIR / f"{zip_filename_base}.zip"
        shutil.copy2(zip_path, final_zip_path)
        logger.info(f"ZIP copiato in: {final_zip_path}")

        # Pulisci directory temporanea
        if temp_dir and os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
            except Exception as cleanup_error:
                logger.warning(f"Impossibile rimuovere dir temporanea: {cleanup_error}")

        # Invia file ZIP
        return send_file(
            final_zip_path,
            mimetype="application/zip",
            as_attachment=True,
            download_name=f"{zip_filename_base}.zip",
        )

    except Exception as e:
        logger.exception(f"Package export error: {e}")
        if temp_dir and os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
            except:
                pass
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/export/<plan_id>/html", methods=["GET"])
@route_error_handler
def api_export_html_only(plan_id: str):
    """
    Esporta piano in formato HTML con Bento Grid infografico e Paged.js.
    Layout responsive: A4 paginato su desktop, scrollabile su mobile.
    """
    review = _get_or_load_review(plan_id)

    plan_data = editor.export_plan_for_final(plan_id) or {}

    # Ottieni colori del club
    club_identity = get_club_identity(review.club_name)

    metadata = {
        "category": review.category,
        "primary_color": club_identity.get("primary", "#1a365d"),
        "secondary_color": club_identity.get("secondary", "#ffffff"),
        "credibility_score": sum(
            s.credibility_score for s in review.sections.values()
        )
        / len(review.sections)
        if review.sections
        else 0,
    }

    from export_html import ChunkedHTMLExporter

    html_exporter = ChunkedHTMLExporter()
    html_path = html_exporter.export(
        plan_data=plan_data,
        club_name=review.club_name,
        sources=[],
        metadata=metadata,
    )

    return send_file(
        html_path,
        mimetype="text/html",
        as_attachment=True,
        download_name=html_path.name,
    )

@app.route("/boardroom/<plan_id>")
@login_required
def boardroom_view(plan_id: str):
    """
    Innovative 'Strategic Boardroom' view.
    Replaces the static 'View Online'.
    """
    review = editor.reviews.get(plan_id)
    # Fallback to DB if not in memory
    if not review:
        plan_record = knowledge_manager.store.get_plan(plan_id)
        if not plan_record:
            flash("Piano non trovato", "error")
            return redirect(url_for("plans_list"))

        review = editor.create_review_from_plan(
            plan_data=plan_record.plan_data,
            club_name=plan_record.club_name,
            metadata={"category": plan_record.category},
            owner_id=plan_record.owner_id,
        )
        review.plan_id = plan_id
        editor.reviews[plan_id] = review

    # SICUREZZA
    is_owner = review.owner_id == int(current_user.id)
    is_admin = current_user.role in ["super_admin", "admin"]
    if not is_owner and not is_admin:
        flash("Accesso negato.", "error")
        return redirect(url_for("plans_list"))

    # Prepare data for dashboard
    club_identity = get_club_identity(
        club_name=review.club_name,
        custom_primary=getattr(review, "primary_color", None),
        custom_secondary=getattr(review, "secondary_color", None),
    )

    # Extract Executive Summary safely
    exec_section = review.sections.get("executive_summary")
    vision_text = "Visione strategica in fase di elaborazione..."
    if exec_section and exec_section.content:
        # Prendi il primo paragrafo significativo
        parts = exec_section.content.split("\n")
        for part in parts:
            if part.strip() and not part.startswith("#"):
                vision_text = part[:300] + "..."
                break

    # Extract SWOT from plan (naive extraction or structured if avail)
    # Default placeholder
    swot = {
        "strengths": [
            "Brand storico",
            "Radicamento territoriale",
            "Base tifosi fedele",
        ],
        "weaknesses": [
            "Strutture da ammodernare",
            "Budget limitato",
            "Digitalizzazione",
        ],
        "opportunities": ["Sviluppo Academy", "Partnership locali", "Turismo sportivo"],
        "threats": ["Competizione regionale", "Costi energetici", "Riforme federali"],
    }

    current_year = datetime.now().year

    # Prepare sections content for template
    # Il template si aspetta un dict {key: content_html}
    sections_content = {}
    if review and review.sections:
        for key, section in review.sections.items():
            # Supporta sia oggetto PlanSection che stringa raw (legacy)
            if hasattr(section, "content"):
                # Converte Markdown in HTML basilare se necessario
                import markdown

                sections_content[key] = markdown.markdown(section.content)
            else:
                sections_content[key] = str(section)

    return render_template(
        "boardroom.html",
        plan_id=plan_id,
        club_name=review.club_name,
        category=review.category,
        club_identity=club_identity,
        vision_summary=vision_text,
        swot=swot,
        current_year=current_year,
        review=review,
        sections=sections_content,  # FIX: Passa sections esplicitamente
    )

@app.route("/view/<plan_id>")
def view_plan_html(plan_id: str):
    """
    Visualizza piano in HTML nel browser (per anteprima e stampa).
    """
    try:
        review = editor.reviews.get(plan_id)
        if not review:
            return get_user_friendly_message(PlanNotFoundError()), 404

        plan_data = editor.export_plan_for_final(plan_id)
        if not plan_data:
            return "Nessun contenuto disponibile per questo piano.", 400

        sources = []
        metadata = {
            "category": review.category,
            "credibility_score": sum(
                s.credibility_score for s in review.sections.values()
            )
            / len(review.sections)
            if review.sections
            else 0,
        }

        html_content = _generate_printable_html(
            plan_data, review.club_name, sources, metadata
        )
        return html_content

    except RootingFutureError as e:
        log_exception(e, context="view_plan")
        return e.user_message, e.status_code
    except Exception as e:
        wrapped = handle_exception(e, context="view_plan")
        log_exception(wrapped, context="view_plan")
        return wrapped.user_message, wrapped.status_code

@app.route("/api/export/<plan_id>/executive", methods=["GET"])
@route_error_handler
def api_export_executive_report(plan_id: str):
    """
    Esporta Executive Report A4 - sintesi ottimizzata per stampa.
    Formato compatto (3-4 pagine) con tutti i dati essenziali.
    """
    review = _get_or_load_review(plan_id)

    plan_data = editor.export_plan_for_final(plan_id) or {}

    # Prepara metadata con colori e stime
    metadata = {
        "category": review.category,
        "primary_color": getattr(review, "primary_color", None) or "#1a365d",
        "secondary_color": getattr(review, "secondary_color", None) or "#ffffff",
        "dimensione_rosa": getattr(review, "squad_size", 22),
        "capienza_stadio": getattr(review, "stadium_capacity", 0),
        "known_financials": {},
        "estimated_fields": {
            "fatturato": "tier3_estimated",
            "monte_ingaggi": "tier2_deduced",
            "valore_rosa": "tier2_deduced",
        },
    }

    # Genera Executive Report HTML
    html_content = plan_renderer.render_executive_html(
        plan_data=plan_data,
        club_name=review.club_name,
        category=review.category,
        metadata=metadata,
    )

    safe_name = review.club_name.replace(" ", "_").replace("/", "_")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{safe_name}_ExecutiveReport_{timestamp}.html"

    # Salva in OUTPUT_DIR
    html_path = OUTPUT_DIR / filename
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    return send_file(
        html_path, mimetype="text/html", as_attachment=True, download_name=filename
    )

@app.route("/api/export/<plan_id>/onepager", methods=["GET"])
@route_error_handler
def api_export_onepager(plan_id: str):
    """
    Esporta One-Pager infografica A4 - documento singola pagina per condivisione rapida.
    Perfetto per WhatsApp, email, presentazioni veloci.
    Include: Dashboard KPI, Progress STW, Top 5 Priorita, Roadmap.
    """
    review = _get_or_load_review(plan_id)

    plan_data = editor.export_plan_for_final(plan_id) or {}

    club_identity = get_club_identity(review.club_name)
    credibility = (
        sum(s.credibility_score for s in review.sections.values())
        / len(review.sections)
        if review.sections
        else 70
    )

    metadata = {
        "category": review.category or "Serie D",
        "primary_color": club_identity.get("primary", "#1a365d"),
        "secondary_color": club_identity.get("secondary", "#c9a227"),
        "credibility_score": int(credibility),
        "sources_count": sum(s.sources_count for s in review.sections.values())
        if review.sections
        else 10,
    }

    # Calcola copertura STW da presenza/lunghezza sezioni (il keyword-matcher
    # cerca codici MACRO 1.1 che l'AI non scrive — fallback su content-length)
    def _stw_from_content(plan_data):
        mapping = {
            'sportivi':    ['stw_sportivi', 'technical_sporting'],
            'strutturali': ['stw_strutturali', 'infrastructure'],
            'marketing':   ['stw_marketing', 'marketing_commercial'],
            'sociali':     ['stw_sociali', 'social_sustainability'],
        }
        result = {}
        for cat, keys in mapping.items():
            chars = sum(len(plan_data.get(k, '')) for k in keys)
            # 3000+ chars → ~75%, 1500 → ~50%, 500 → ~25%, 0 → 0
            result[cat] = min(90, int(chars / 40)) if chars > 200 else 0
        return result

    stw_progress = _stw_from_content(plan_data)

    from export_onepager import create_onepager

    html_path = create_onepager(
        plan_data=plan_data,
        club_name=review.club_name,
        metadata=metadata,
        stw_progress=stw_progress,
    )

    return send_file(
        html_path,
        mimetype="text/html",
        as_attachment=True,
        download_name=html_path.name,
    )

@app.route("/view/<plan_id>/onepager")
def view_onepager(plan_id: str):
    """Visualizza One-Pager infografica nel browser."""
    try:
        review = editor.reviews.get(plan_id)
        if not review:
            return "Piano non trovato", 404

        plan_data = editor.export_plan_for_final(plan_id)
        if not plan_data:
            return "Nessun contenuto disponibile", 400

        club_identity = get_club_identity(review.club_name)
        credibility = (
            sum(s.credibility_score for s in review.sections.values())
            / len(review.sections)
            if review.sections
            else 70
        )

        metadata = {
            "category": review.category or "Serie D",
            "primary_color": club_identity.get("primary", "#1a365d"),
            "secondary_color": club_identity.get("secondary", "#c9a227"),
            "credibility_score": int(credibility),
            "sources_count": sum(s.sources_count for s in review.sections.values())
            if review.sections
            else 10,
        }

        from export_onepager import create_onepager

        html_path = create_onepager(plan_data, review.club_name, metadata)

        with open(html_path, "r", encoding="utf-8") as f:
            return f.read()

    except Exception as e:
        logger.exception(f"View One-Pager error: {e}")
        return f"Errore: {str(e)}", 500

@app.route("/view/<plan_id>/executive")
def view_executive_report(plan_id: str):
    """
    Visualizza Executive Report A4 nel browser.
    Ottimizzato per stampa diretta (Ctrl+P -> PDF).
    """
    try:
        review = editor.reviews.get(plan_id)
        if not review:
            return "Piano non trovato", 404

        plan_data = editor.export_plan_for_final(plan_id)
        if not plan_data:
            return "Nessun contenuto disponibile", 400

        metadata = {
            "category": review.category,
            "primary_color": getattr(review, "primary_color", None) or "#1a365d",
            "secondary_color": getattr(review, "secondary_color", None) or "#ffffff",
            "dimensione_rosa": getattr(review, "squad_size", 22),
            "capienza_stadio": getattr(review, "stadium_capacity", 0),
            "known_financials": {},
            "estimated_fields": {},
        }

        html_content = plan_renderer.render_executive_html(
            plan_data=plan_data,
            club_name=review.club_name,
            category=review.category,
            metadata=metadata,
            sources=[],
        )

        return html_content

    except Exception as e:
        logger.exception(f"Executive view error: {e}")
        return f"Errore: {str(e)}", 500

def _hex_to_rgb(hex_color: str) -> tuple:
    """Converte colore hex in RGB."""
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))

def _get_contrast_color(hex_color: str) -> str:
    """Restituisce bianco o nero in base al contrasto."""
    r, g, b = _hex_to_rgb(hex_color)
    luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
    return "#ffffff" if luminance < 0.5 else "#1a202c"

def _darken_color(hex_color: str, factor: float = 0.2) -> str:
    """Scurisce un colore."""
    r, g, b = _hex_to_rgb(hex_color)
    r = int(r * (1 - factor))
    g = int(g * (1 - factor))
    b = int(b * (1 - factor))
    return f"#{r:02x}{g:02x}{b:02x}"

def _lighten_color(hex_color: str, factor: float = 0.2) -> str:
    """Schiarisce un colore."""
    r, g, b = _hex_to_rgb(hex_color)
    r = min(255, int(r + (255 - r) * factor))
    g = min(255, int(g + (255 - g) * factor))
    b = min(255, int(b + (255 - b) * factor))
    return f"#{r:02x}{g:02x}{b:02x}"

def _generate_printable_html(
    plan_data: dict, club_name: str, sources: list, metadata: dict
) -> str:
    """
    Genera HTML completo con stili di stampa ottimizzati, branding del club
    e tecniche di guerrilla marketing (colori societari, elementi visivi distintivi).
    """
    current_year = datetime.now().year
    category = metadata.get("category", "") or ""
    credibility = metadata.get("credibility_score", 0) or 0

    # Colori del club (guerrilla marketing: identità visiva)
    primary_color = metadata.get("primary_color") or "#1a365d"
    secondary_color = metadata.get("secondary_color") or "#ffffff"

    # Genera varianti colore per design coerente
    primary_dark = _darken_color(primary_color, 0.2)
    primary_light = _lighten_color(primary_color, 0.85)
    accent_color = _lighten_color(primary_color, 0.3)
    text_on_primary = _get_contrast_color(primary_color)

    # Genera sezioni HTML
    sections_html = ""
    section_configs = [
        ("executive_summary", "Executive Summary", "📋"),
        ("technical_sporting", "Area Tecnico-Sportiva", "⚽"),
        ("youth_development", "Settore Giovanile", "🌱"),
        ("infrastructure", "Infrastrutture", "🏟️"),
        ("marketing_commercial", "Marketing e Commerciale", "📈"),
        ("social_sustainability", "Sostenibilità Sociale", "🤝"),
        ("governance", "Governance", "🏛️"),
        ("financial", "Piano Finanziario", "💰"),
    ]

    nav_items = ""
    section_count = 0
    for key, title, icon in section_configs:
        content = plan_data.get(key)
        if content and isinstance(content, str) and content.strip():
            section_count += 1
            processed = _simple_markdown_to_html(content)
            sections_html += f'''
            <section class="section" id="{key}">
                <div class="section-header">
                    <span class="section-number">{section_count:02d}</span>
                    <h2><span class="section-icon">{icon}</span> {title}</h2>
                </div>
                <div class="content">{processed}</div>
            </section>
            '''
            nav_items += f'<a href="#{key}" class="nav-item"><span class="nav-icon">{icon}</span><span class="nav-text">{title}</span></a>'

    if not sections_html:
        sections_html = '<section class="section"><h2>Contenuto</h2><p>Nessun contenuto disponibile per questo piano.</p></section>'

    # === DASHBOARD STRATEGICA ===
    # Genera matrice visuale con le 4 aree e obiettivi MACRO/MICRO
    dashboard_html = generate_strategic_dashboard(
        plan_data, primary_color, secondary_color
    )
    # Inserisci dopo Executive Summary
    if 'id="technical_sporting"' in sections_html:
        sections_html = sections_html.replace(
            '<section class="section" id="technical_sporting">',
            f'{dashboard_html}<section class="section" id="technical_sporting">',
        )
    else:
        sections_html = dashboard_html + sections_html

    # === SEZIONE METODOLOGIA E FONTI ===
    # Genera sezione trasparenza con fonti dati e disclaimer
    try:
        estimated_fields = metadata.get("estimated_fields", {})
        if not estimated_fields:
            # Default: assume alcuni campi sono stimati per club piccoli
            estimated_fields = {
                "fatturato": "tier3_estimated",
                "monte_ingaggi": "tier2_deduced",
                "valore_rosa": "tier2_deduced",
            }

        methodology_html = plan_renderer.render_methodology(
            club_name=club_name,
            category=category,
            data_sources_used=["figc_report", "web_search", "knowledge_base", "benchmark_calc"],
            estimated_fields=estimated_fields,
            primary_color=primary_color,
        )
        # Aggiungi alla fine delle sezioni
        sections_html += methodology_html
    except Exception as e:
        logger.warning(f"Errore generazione sezione metodologia: {e}")

    # === GRAFICI FINANZIARI ===
    # Genera grafici se abbiamo dati finanziari
    try:
        club_data = {
            "dimensione_rosa": metadata.get("dimensione_rosa", 22),
            "capienza_stadio": metadata.get("capienza_stadio", 0),
        }
        known_financials = metadata.get("known_financials", {})

        estimates = estimate_missing_financials(club_data, category, known_financials)
        charts = generate_financial_charts_for_report(
            club_name=club_name,
            category=category,
            estimated_financials=estimates,
            primary_color=primary_color,
        )

        # Inserisci grafici dopo financial section se esiste
        charts_html = f"""
        <section class="section charts-section" id="financial_charts">
            <div class="section-header" style="background:linear-gradient(135deg,{primary_color},#2d3748);">
                <span class="section-number">📈</span>
                <h2>Analisi Finanziaria Visuale</h2>
            </div>
            <div class="content">
                <h3>KPI Principali</h3>
                {charts.get("kpi_dashboard", "")}
                <h3>Composizione Ricavi Stimata</h3>
                {charts.get("revenue_pie", "")}
                <h3>Confronto con Benchmark {category}</h3>
                {charts.get("benchmark_comparison", "")}
                <h3>Gap Analysis</h3>
                {charts.get("gap_analysis", "")}
            </div>
        </section>
        """

        # Inserisci prima della metodologia
        if 'id="methodology"' in sections_html:
            sections_html = sections_html.replace(
                '<section class="section methodology-section"',
                f'{charts_html}<section class="section methodology-section"',
            )
        else:
            sections_html += charts_html

    except Exception as e:
        logger.warning(f"Errore generazione grafici: {e}")

    # Anno fondazione (se disponibile)
    foundation_year = metadata.get("foundation_year", "")
    foundation_text = f" • Fondato nel {foundation_year}" if foundation_year else ""

    return f"""<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Piano Strategico {club_name} {current_year}-{current_year + 3}</title>
    <style>
        :root {{
            /* Colori Club - Guerrilla Marketing */
            --club-primary: {primary_color};
            --club-secondary: {secondary_color};
            --club-primary-dark: {primary_dark};
            --club-primary-light: {primary_light};
            --club-accent: {accent_color};
            --text-on-primary: {text_on_primary};

            /* Colori sistema */
            --text: #2d3748;
            --text-light: #718096;
            --bg: #f7fafc;
            --white: #ffffff;
            --border: #e2e8f0;
        }}

        * {{ margin: 0; padding: 0; box-sizing: border-box; }}

        body {{
            font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
            line-height: 1.7;
            color: var(--text);
            background: var(--bg);
        }}

        /* Print Button Bar - Branded */
        .print-bar {{
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            background: var(--club-primary);
            padding: 12px 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            z-index: 1000;
            box-shadow: 0 2px 10px rgba(0,0,0,0.2);
        }}

        .print-bar-title {{
            color: var(--text-on-primary);
            font-size: 14px;
            font-weight: 500;
        }}

        .print-btn {{
            background: var(--club-secondary);
            color: var(--club-primary);
            border: 2px solid var(--club-secondary);
            padding: 10px 24px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 14px;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 8px;
            transition: all 0.2s;
        }}

        .print-btn:hover {{
            background: transparent;
            color: var(--text-on-primary);
        }}

        .print-btn svg {{
            width: 18px;
            height: 18px;
        }}

        /* Header - Club Branding */
        .header {{
            background: linear-gradient(135deg, var(--club-primary), var(--club-primary-dark));
            color: var(--text-on-primary);
            padding: 100px 40px 80px;
            text-align: center;
            margin-top: 56px;
            position: relative;
            overflow: hidden;
        }}

        /* Decorative stripe - Guerrilla element */
        .header::before {{
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 8px;
            background: var(--club-secondary);
        }}

        .header::after {{
            content: '';
            position: absolute;
            bottom: -50px;
            right: -50px;
            width: 200px;
            height: 200px;
            background: var(--club-secondary);
            opacity: 0.1;
            border-radius: 50%;
        }}

        .header h1 {{
            font-size: 2.8rem;
            font-weight: 800;
            margin-bottom: 15px;
            text-transform: uppercase;
            letter-spacing: 2px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
        }}

        .header .subtitle {{
            font-size: 1.4rem;
            font-weight: 300;
            opacity: 0.95;
            margin-bottom: 10px;
        }}

        .header .meta {{
            font-size: 1rem;
            opacity: 0.85;
            display: inline-block;
            padding: 8px 20px;
            background: rgba(255,255,255,0.15);
            border-radius: 30px;
            margin-top: 15px;
        }}

        /* Navigation - Branded */
        .nav {{
            background: var(--white);
            padding: 0;
            position: sticky;
            top: 56px;
            z-index: 99;
            box-shadow: 0 4px 15px rgba(0,0,0,0.08);
            overflow-x: auto;
            white-space: nowrap;
            border-bottom: 3px solid var(--club-primary);
        }}

        .nav-item {{
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 16px 20px;
            color: var(--text);
            text-decoration: none;
            font-size: 0.9rem;
            font-weight: 500;
            transition: all 0.2s ease;
            border-bottom: 3px solid transparent;
            margin-bottom: -3px;
        }}

        .nav-item:hover {{
            background: var(--club-primary-light);
            color: var(--club-primary);
            border-bottom-color: var(--club-primary);
        }}

        .nav-icon {{
            font-size: 1.1rem;
        }}

        /* Container */
        .container {{
            max-width: 1000px;
            margin: 0 auto;
            padding: 40px 20px;
        }}

        /* Sections - Enhanced with club branding */
        .section {{
            background: var(--white);
            border-radius: 16px;
            padding: 0;
            margin-bottom: 30px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.06);
            border: 1px solid var(--border);
            overflow: hidden;
        }}

        .section-header {{
            background: linear-gradient(135deg, var(--club-primary-light), var(--white));
            padding: 25px 35px;
            display: flex;
            align-items: center;
            gap: 20px;
            border-bottom: 1px solid var(--border);
        }}

        .section-number {{
            font-size: 2.5rem;
            font-weight: 800;
            color: var(--club-primary);
            opacity: 0.2;
            font-family: 'Georgia', serif;
        }}

        .section-header h2 {{
            color: var(--club-primary);
            font-size: 1.6rem;
            margin: 0;
            display: flex;
            align-items: center;
            gap: 12px;
        }}

        .section-icon {{
            font-size: 1.4rem;
        }}

        .section .content {{
            padding: 35px;
        }}

        .section h3 {{
            color: var(--club-primary);
            font-size: 1.25rem;
            margin: 30px 0 15px;
            padding-left: 15px;
            border-left: 4px solid var(--club-primary);
        }}

        .section h4 {{
            color: var(--text);
            font-size: 1.05rem;
            margin: 25px 0 12px;
            font-weight: 600;
        }}

        .section p {{
            margin-bottom: 16px;
            text-align: justify;
        }}

        .section ul, .section ol {{
            margin: 16px 0 16px 25px;
        }}

        .section li {{
            margin-bottom: 10px;
            position: relative;
        }}

        .section ul li::marker {{
            color: var(--club-primary);
        }}

        /* Key metrics highlight */
        .section strong {{
            color: var(--club-primary);
        }}

        /* Tables - Branded */
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 25px 0;
            font-size: 0.95rem;
            border-radius: 8px;
            overflow: hidden;
        }}

        th, td {{
            padding: 14px 18px;
            text-align: left;
        }}

        th {{
            background: var(--club-primary);
            color: var(--text-on-primary);
            font-weight: 600;
            text-transform: uppercase;
            font-size: 0.85rem;
            letter-spacing: 0.5px;
        }}

        td {{
            border-bottom: 1px solid var(--border);
        }}

        tr:nth-child(even) {{
            background: var(--club-primary-light);
        }}

        tr:hover {{
            background: var(--club-primary-light);
        }}

        /* Footer - Branded */
        .footer {{
            text-align: center;
            padding: 50px 20px;
            color: var(--text-on-primary);
            background: linear-gradient(135deg, var(--club-primary), var(--club-primary-dark));
            margin-top: 40px;
            position: relative;
        }}

        .footer::before {{
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 4px;
            background: var(--club-secondary);
        }}

        .footer p {{
            opacity: 0.9;
        }}

        .footer strong {{
            color: var(--club-secondary);
        }}

        /* ================================================================
           PRINT STYLES - Ottimizzato per stampa professionale
           ================================================================ */
        @media print {{
            /* === NASCONDI ELEMENTI UI INTERATTIVI === */
            .print-bar,
            .nav,
            .modal,
            .dashboard-modal,
            .expand-hint,
            .click-hint,
            .card-click-hint,
            .card-expand-icon,
            button,
            .btn {{
                display: none !important;
            }}

            /* === IMPOSTAZIONI GLOBALI === */
            * {{
                -webkit-print-color-adjust: exact !important;
                print-color-adjust: exact !important;
            }}

            body {{
                background: white !important;
                color: #000 !important;
                font-size: 11pt !important;
                line-height: 1.5 !important;
                orphans: 4;
                widows: 4;
            }}

            /* === HEADER CLUB === */
            .header {{
                margin-top: 0 !important;
                padding: 50px 20px !important;
                break-after: avoid;
                page-break-after: avoid;
            }}

            /* === SEZIONI === */
            .section {{
                box-shadow: none !important;
                border: 1px solid #ccc !important;
                border-radius: 4px !important;
                margin-bottom: 20px !important;
                break-inside: avoid !important;
                page-break-inside: avoid !important;
            }}

            .section-header {{
                break-after: avoid !important;
                page-break-after: avoid !important;
            }}

            /* === TITOLI - Mai soli a fine pagina === */
            h1, h2, h3, h4, h5, h6 {{
                break-after: avoid !important;
                page-break-after: avoid !important;
                orphans: 3;
                widows: 3;
            }}

            /* === PARAGRAFI E LISTE === */
            p {{
                orphans: 3;
                widows: 3;
            }}

            ul, ol {{
                orphans: 2;
                widows: 2;
            }}

            li {{
                break-inside: avoid !important;
                page-break-inside: avoid !important;
            }}

            /* === TABELLE === */
            table {{
                break-inside: avoid !important;
                page-break-inside: avoid !important;
                border-collapse: collapse !important;
            }}

            tr {{
                break-inside: avoid !important;
                page-break-inside: avoid !important;
            }}

            /* === BOX E CARD === */
            .kpi-box,
            .alert,
            .highlight-box,
            .area-card,
            .area-box,
            .chart-box,
            .method-box {{
                break-inside: avoid !important;
                page-break-inside: avoid !important;
                box-shadow: none !important;
            }}

            /* === IMMAGINI E GRAFICI === */
            img,
            svg,
            .chart-container {{
                break-inside: avoid !important;
                page-break-inside: avoid !important;
                max-width: 100% !important;
            }}

            /* === CONTAINER === */
            .container {{
                padding: 20px !important;
                max-width: none !important;
            }}

            /* === FOOTER === */
            .footer {{
                margin-top: 30px !important;
                padding-top: 15px !important;
                border-top: 1px solid #ccc !important;
            }}

            /* === DASHBOARD SPECIFICO === */
            .dashboard-section {{
                background: white !important;
                break-after: page;
                page-break-after: always;
            }}

            .strategic-matrix {{
                display: grid !important;
                grid-template-columns: repeat(2, 1fr) !important;
                gap: 12px !important;
            }}

            .area-card {{
                box-shadow: none !important;
                border: 1px solid #ccc !important;
            }}

            .clickable-card {{
                cursor: default;
            }}

            .clickable-card:hover {{
                transform: none !important;
                box-shadow: none !important;
            }}

            /* === RIMUOVI TRONCAMENTO TESTO === */
            .obj-item.truncate-screen .obj-text {{
                white-space: normal !important;
                overflow: visible !important;
                text-overflow: clip !important;
                word-wrap: break-word !important;
            }}

            /* === REGOLA @PAGE === */
            @page {{
                size: A4;
                margin: 1.5cm;
            }}

            @page :first {{
                margin-top: 0;
            }}
        }}

        /* Mobile */
        @media (max-width: 768px) {{
            .header {{
                padding: 70px 20px 50px;
            }}
            .header h1 {{
                font-size: 1.8rem;
                letter-spacing: 1px;
            }}
            .section-header {{
                padding: 20px;
            }}
            .section .content {{
                padding: 25px 20px;
            }}
            .nav-text {{
                display: none;
            }}
            .nav-item {{
                padding: 14px 16px;
            }}
        }}
    </style>
</head>
<body>
    <div class="print-bar">
        <span class="print-bar-title">Piano Strategico Triennale - {club_name}</span>
        <button class="print-btn" onclick="window.print()">
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2zm8-12V5a2 2 0 00-2-2H9a2 2 0 00-2 2v4h10z" />
            </svg>
            Stampa / Salva PDF
        </button>
    </div>

    <header class="header">
        <h1>{club_name}</h1>
        <p class="subtitle">Piano Strategico {current_year} — {current_year + 3}</p>
        <p class="meta">{category}{foundation_text}</p>
    </header>

    <nav class="nav">
        {nav_items}
    </nav>

    <main class="container">
        {sections_html}
    </main>

    <footer class="footer">
        <p style="font-size: 1.1rem; margin-bottom: 15px;"><strong>{club_name}</strong></p>
        <p>Piano Strategico Triennale {current_year}-{current_year + 3}</p>
        <p style="margin-top: 20px; font-size: 0.85rem; opacity: 0.7;">
            Documento generato da Rooting Future Strategy Engine v6.0<br>
            {datetime.now().strftime("%d/%m/%Y alle %H:%M")}
        </p>
    </footer>

    <script>
        // Smooth scroll
        document.querySelectorAll('.nav-item').forEach(link => {{
            link.addEventListener('click', (e) => {{
                e.preventDefault();
                const target = document.querySelector(link.getAttribute('href'));
                if (target) {{
                    const offset = document.querySelector('.nav').offsetHeight + 70;
                    window.scrollTo({{
                        top: target.offsetTop - offset,
                        behavior: 'smooth'
                    }});
                }}
            }});
        }});
    </script>
</body>
</html>"""

def _simple_markdown_to_html(content: str) -> str:
    """Converte markdown semplice in HTML."""
    import re

    if not content:
        return "<p><em>Contenuto non disponibile</em></p>"

    # Escape HTML
    content = content.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    lines = content.split("\n")
    html_parts = []
    in_list = False
    list_type = None

    for line in lines:
        line = line.strip()

        if not line:
            if in_list:
                html_parts.append(f"</{list_type}>")
                in_list = False
            continue

        # Headers
        if line.startswith("### "):
            if in_list:
                html_parts.append(f"</{list_type}>")
                in_list = False
            html_parts.append(f"<h4>{line[4:]}</h4>")
            continue
        if line.startswith("## "):
            if in_list:
                html_parts.append(f"</{list_type}>")
                in_list = False
            html_parts.append(f"<h3>{line[3:]}</h3>")
            continue

        # Bullet lists
        if line.startswith("- ") or line.startswith("* "):
            if not in_list or list_type != "ul":
                if in_list:
                    html_parts.append(f"</{list_type}>")
                html_parts.append("<ul>")
                in_list = True
                list_type = "ul"
            text = _format_inline(line[2:])
            html_parts.append(f"<li>{text}</li>")
            continue

        # Numbered lists
        if line and line[0].isdigit() and len(line) > 1:
            for i, c in enumerate(line[:5]):
                if c in ".):":
                    if not in_list or list_type != "ol":
                        if in_list:
                            html_parts.append(f"</{list_type}>")
                        html_parts.append("<ol>")
                        in_list = True
                        list_type = "ol"
                    text = _format_inline(line[i + 1 :].strip())
                    html_parts.append(f"<li>{text}</li>")
                    break
            else:
                if in_list:
                    html_parts.append(f"</{list_type}>")
                    in_list = False
                html_parts.append(f"<p>{_format_inline(line)}</p>")
            continue

        # Regular paragraph
        if in_list:
            html_parts.append(f"</{list_type}>")
            in_list = False
        html_parts.append(f"<p>{_format_inline(line)}</p>")

    if in_list:
        html_parts.append(f"</{list_type}>")

    return "\n".join(html_parts)

def _format_inline(text: str) -> str:
    """Formatta bold e italic."""
    import re

    # Bold **text**
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    # Italic *text*
    text = re.sub(r"\*([^\*]+?)\*", r"<em>\1</em>", text)
    return text

@app.route("/api/preview/<plan_id>", methods=["GET"])
def api_preview_print(plan_id: str):
    """
    Anteprima di stampa del piano.
    Restituisce HTML Print-Ready inline (non download) per visualizzazione
    in nuova tab del browser. L'utente puo poi fare Ctrl+P -> Salva come PDF.
    """
    try:
        review = editor.reviews.get(plan_id)
        if not review:
            return "Piano non trovato", 404

        plan_data = editor.export_plan_for_final(plan_id)
        if not plan_data:
            return "Nessun contenuto da visualizzare", 400

        # === BRANDING AUTOMATICO ===
        club_identity = get_club_identity(
            club_name=review.club_name,
            custom_primary=getattr(review, "primary_color", None),
            custom_secondary=getattr(review, "secondary_color", None),
        )

        logger.info(
            f"Preview branding: {review.club_name} -> {club_identity['primary']}"
        )

        metadata = {
            "category": review.category,
            "primary_color": club_identity["primary"],
            "secondary_color": club_identity["secondary"],
            "accent_color": club_identity.get("accent"),
        }

        # Genera HTML Paged.js
        from export_paged import create_paged_html

        filepath = create_paged_html(
            plan_data=plan_data,
            club_name=review.club_name,
            sources=[],
            metadata=metadata,
        )

        # Restituisce HTML inline (visualizza nel browser, non download)
        return send_file(
            filepath,
            mimetype="text/html",
            as_attachment=False,  # Inline, non download
        )

    except Exception as e:
        logger.exception(f"Preview error: {e}")
        return f"Errore: {str(e)}", 500

# =============================================================================
# API - WORKFLOW
# =============================================================================

@app.route("/api/plan/<plan_id>/finalize", methods=["POST"])
def api_finalize_plan(plan_id: str):
    """
    Finalizza il piano e lo carica nella knowledge base di Gemini File Search.
    """
    data = request.json or {}
    notes = data.get("notes", "")

    success = editor.finalize_plan(plan_id, notes)
    if not success:
        return jsonify(
            {"success": False, "error": "Cannot finalize: some sections not approved"}
        ), 400

    # Se la finalizzazione ha successo, carica il piano nella Knowledge Base RAG
    try:
        logger.info(
            f"Piano '{plan_id}' finalizzato. Preparazione per upload nella Knowledge Base RAG..."
        )
        review = editor.reviews.get(plan_id)
        if not review:
            raise ValueError("Review non trovata dopo finalizzazione.")

        plan_data = editor.export_plan_for_final(plan_id)

        # Esporta il piano come PDF in una directory temporanea
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_dir_path = Path(temp_dir)

            # Genera HTML
            html_exporter_instance = ChunkedHTMLExporter()
            html_content = html_exporter_instance._assemble_document(
                review.club_name, {}
            )

            # Crea PDF
            from export_pdf_server import create_pdf_from_html

            safe_name = review.club_name.replace(" ", "_")
            pdf_success = create_pdf_from_html(
                html_content, str(temp_dir_path), safe_name
            )

            if pdf_success:
                pdf_path = temp_dir_path / f"{safe_name}.pdf"
                # Carica il PDF usando il FileSearchManager
                upload_success = file_search_manager.upload_file(pdf_path)
                if not upload_success:
                    logger.warning(
                        f"Finalizzazione riuscita, ma upload nella RAG KB fallito per il piano '{plan_id}'."
                    )
            else:
                logger.warning(
                    f"Finalizzazione riuscita, ma creazione PDF per RAG KB fallita per il piano '{plan_id}'."
                )

    except Exception as e:
        logger.error(
            f"Errore durante l'upload del piano finalizzato '{plan_id}' nella RAG KB: {e}"
        )
        # Non bloccare la risposta all'utente per questo, ma logga l'errore.

    return jsonify({"success": True})

@app.route("/api/plan/<plan_id>/archive", methods=["POST"])
def api_archive_plan(plan_id: str):
    """Archivia piano"""
    success = editor.archive_plan(plan_id)
    return jsonify({"success": success})

@app.route("/api/stats")
def api_stats():
    """Statistiche sistema"""
    dashboard_stats = editor.get_dashboard_stats()
    workload = batch_manager.get_workload_summary()
    knowledge_stats = knowledge_manager.store.get_statistics()

    return jsonify(
        {
            "dashboard": dashboard_stats,
            "workload": workload,
            "knowledge": knowledge_stats,
        }
    )

@app.route("/api/agents")
def api_agents():
    """Info agenti disponibili"""
    return jsonify({"agents": orchestrator.get_agent_info()})

# =============================================================================
# API - SISTEMA STRUTTURATO v6.0
# =============================================================================

@app.route("/api/structured/generate", methods=["POST"])
@route_error_handler
def api_structured_generate():
    """
    Genera piano con sistema strutturato (benchmark + validazione scientifica).
    Questo e' il nuovo sistema v6.0 che produce dati tracciabili.
    """
    data = request.json or {}

    # Valida input
    club_name = data.get("club_name")
    category = data.get("category")

    if not club_name or not category:
        return jsonify(
            {"success": False, "error": "club_name e category sono obbligatori"}
        ), 400

        # Prepara club data
        club_data = {
            "club_name": club_name,
            "category": category,
            "city": data.get("city", ""),
            "region": data.get("region", ""),
            # Dati finanziari
            "revenue": data.get("revenue"),
            "wage_bill": data.get("wage_bill"),
            "net_assets": data.get("net_assets"),
            # Dati sportivi
            "squad_size": data.get("squad_size"),
            "average_age": data.get("average_age"),
            # Infrastrutture
            "stadium_capacity": data.get("stadium_capacity"),
            "training_fields": data.get("training_fields"),
            # Settore giovanile
            "youth_players": data.get("youth_players"),
            "youth_teams": data.get("youth_teams"),
        }

        # Ricerca web se richiesta
        research_data = None
        if data.get("enable_research", True):
            try:
                research_results = researcher.research_club(club_name)
                research_data = research_aggregator.aggregate(research_results)
            except Exception as e:
                logger.warning(f"Research failed: {e}")

        # Genera piano strutturato
        plan = structured_orchestrator.generate_plan(club_data, research_data)

        # Render HTML
        filepath = plan_renderer.render_structured(plan)

        return jsonify(
            {
                "success": True,
                "plan_id": plan.plan_id,
                "output_file": os.path.basename(filepath),
                "stats": {
                    "total_data_points": plan.total_data_points,
                    "verified_data_points": plan.verified_data_points,
                    "missing_data_points": plan.missing_data_points,
                    "overall_credibility": plan.overall_credibility,
                    "sources_count": len(plan.bibliography),
                },
            }
        )

@app.route("/api/structured/benchmarks/<category>")
def api_structured_benchmarks(category: str):
    """
    Restituisce i benchmark per una categoria.
    Utile per il frontend per mostrare cosa ci aspettiamo.
    """
    from data_models import BenchmarkDatabase

    benchmarks = {
        "financial": BenchmarkDatabase.FINANCIAL_BENCHMARKS.get(category, {}),
        "sporting": BenchmarkDatabase.SPORTING_BENCHMARKS.get(category, {}),
        "youth": BenchmarkDatabase.YOUTH_BENCHMARKS.get(category, {}),
        "infrastructure": BenchmarkDatabase.INFRASTRUCTURE_BENCHMARKS.get(category, {}),
    }

    return jsonify({"success": True, "category": category, "benchmarks": benchmarks})

@app.route("/api/structured/templates")
def api_structured_templates():
    """
    Restituisce i template dei data points richiesti per ogni sezione.
    """
    return jsonify({"success": True, "templates": SECTION_DATA_TEMPLATES})

@app.route("/api/questionnaire/schema")
def api_questionnaire_schema():
    """
    Restituisce lo schema del questionario per n8n/frontend.
    """
    return jsonify({"success": True, "schema": get_questionnaire_schema()})

@app.route("/api/plan-export-status/<plan_id>")
@login_required
def api_plan_export_status(plan_id):
    """
    Verifica lo stato di generazione dei documenti di export.
    Usato dalla pagina di successo per il polling.
    """
    try:
        plan_record = knowledge_manager.store.get_plan(plan_id)
        if not plan_record:
            return jsonify({"error": "Plan not found"}), 404

        # Controlla quali file esistono fisicamente
        status = {"pdf": False, "onepager": False, "executive": False, "filenames": {}}

        # Mapping logico basato sui nomi file
        for path_str in plan_record.export_paths:
            file_path = OUTPUT_DIR / path_str
            if file_path.exists():
                if "PianoStrategico" in path_str and path_str.endswith(".pdf"):
                    status["pdf"] = True
                    status["filenames"]["pdf"] = path_str
                elif "OnePager" in path_str:
                    status["onepager"] = True
                    status["filenames"]["onepager"] = path_str
                elif "ExecutiveReport" in path_str:
                    status["executive"] = True
                    status["filenames"]["executive"] = path_str
                # Fallback per DOCX come PDF se PDF manca (per sicurezza)
                elif path_str.endswith(".docx") and not status["pdf"]:
                    status["pdf"] = True
                    status["filenames"]["pdf"] = (
                        path_str  # Il frontend scaricherà il docx ma il bottone si attiverà
                    )

        return jsonify(status)
    except Exception as e:
        logger.error(f"Export status check error: {e}")
        return jsonify({"error": str(e)}), 500

# NOTA: Route duplicata rimossa - usare /success/<plan_id> invece
# La route /plan/<plan_id> è già gestita da plan_detail() alla linea 749
# @app.route("/plan/<plan_id>")
# @login_required
# def plan_success(plan_id):
#     """Pagina di successo: mostra i link per scaricare i documenti esportati."""
#     try:
#         plan_record = knowledge_manager.store.get_plan(plan_id)
#         if not plan_record:
#             # Mostra pagina con plan_id solo per dimostrazione
#             return render_template(
#                 "generation_success.html", plan_id=plan_id, club_name=""
#             )
#         club_name = getattr(plan_record, "club_name", plan_id)
#         return render_template(
#             "generation_success.html", plan_id=plan_id, club_name=club_name
#         )
#     except Exception as e:
#         logger.error(f"Plan success page error: {e}")
#         return "Errore rendering plan success page", 500

# =============================================================================
# ERROR HANDLERS
# =============================================================================

@app.errorhandler(404)
def not_found(e):
    if request.path.startswith("/api/"):
        return jsonify({"success": False, "error": "Not found"}), 404
    # Simple HTML response instead of template
    return (
        """
    <html><head><title>404 - Non trovato</title></head>
    <body style="font-family: sans-serif; text-align: center; padding: 50px;">
        <h1>404 - Pagina non trovata</h1>
        <p><a href="/">Torna alla Dashboard</a></p>
    </body></html>
    """,
        404,
    )

@app.errorhandler(500)
def server_error(e):
    import traceback
    tb = traceback.format_exc()
    logger.exception(f"Server error: {e}")
    print(f"[500] {e}\n{tb}", flush=True)
    if request.path.startswith("/api/"):
        return jsonify({"success": False, "error": str(e)}), 500
    return (
        f"""
    <html><head><title>500 - Errore</title></head>
    <body style="font-family: sans-serif; text-align: center; padding: 50px;">
        <h1>500 - Errore interno</h1>
        <p>Si e verificato un errore: {str(e)}</p>
        <pre style="text-align:left;background:#f5f5f5;padding:15px;border-radius:8px;overflow:auto;max-width:900px;margin:20px auto;">{tb}</pre>
        <p><a href="/">Torna alla Dashboard</a></p>
    </body></html>
    """,
        500,
    )

# =============================================================================
# CLI COMMANDS
# =============================================================================

@app.cli.command("init-db")
def init_db():
    """Inizializza database"""
    knowledge_manager.store._init_db()
    print("Database initialized")

@app.cli.command("export-knowledge")
def export_knowledge():
    """Esporta knowledge base"""
    path = knowledge_manager.export_full_knowledge_base()
    print(f"Exported to: {path}")

@app.cli.command("auto-approve")
def auto_approve():
    """Auto-approva sezioni ad alta credibilità"""
    count = batch_manager.auto_approve_high_credibility(80.0)
    print(f"Auto-approved {count} sections")

# =============================================================================
# MAIN
# =============================================================================

def check_port_available(port: int) -> bool:
    """Verifica se la porta è disponibile."""
    import socket

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("127.0.0.1", port))
            return True
        except OSError:
            return False

def kill_process_on_port(port: int) -> bool:
    """Tenta di terminare il processo che occupa la porta (Windows)."""
    import subprocess

    try:
        # Trova PID del processo sulla porta
        result = subprocess.run(
            f"netstat -ano | findstr :{port}",
            shell=True,
            capture_output=True,
            text=True,
        )
        if result.stdout:
            lines = result.stdout.strip().split("\n")
            for line in lines:
                if "LISTENING" in line:
                    parts = line.split()
                    pid = parts[-1]
                    print(
                        f"[!] Porta {port} occupata da PID {pid}. Tentativo di terminazione..."
                    )
                    subprocess.run(
                        f"taskkill /F /PID {pid}", shell=True, capture_output=True
                    )
                    import time

                    time.sleep(1)
                    return True
        return False
    except Exception as e:
        print(f"[!] Errore durante kill processo: {e}")
        return False

@app.route("/api/check-file/<path:filename>")
def api_check_file(filename):
    """Verifica se un file esiste nella cartella output."""
    try:
        file_path = OUTPUT_DIR / filename
        if file_path.exists() and file_path.is_file():
            # Controlla che non sia vuoto (0 bytes)
            if file_path.stat().st_size > 0:
                return jsonify({"ready": True, "size": file_path.stat().st_size})
        return jsonify({"ready": False})
    except Exception as e:
        return jsonify({"ready": False, "error": str(e)})

# ============================================================
# LAB — Network access helpers
# ============================================================
import socket as _socket

_lab_access: Dict[str, str] = {
    "lan": "", "tailscale": "", "tunnel": "", "tunnel_status": "inactive"
}
_WIN_NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0

def _get_tailscale_ip() -> str:
    """Restituisce l'IP Tailscale (100.x.x.x) se Tailscale è attivo."""
    import subprocess as _sp
    # Metodo 1: comando tailscale ip -4
    try:
        r = _sp.run(
            ["tailscale", "ip", "-4"],
            capture_output=True, text=True, timeout=5,
            creationflags=_WIN_NO_WINDOW,
        )
        ip = r.stdout.strip().splitlines()[0] if r.returncode == 0 else ""
        if ip.startswith("100."):
            return ip
    except Exception:
        pass
    # Metodo 2: scansiona le interfacce di rete (100.64.0.0/10 = range Tailscale)
    try:
        for info in _socket.getaddrinfo(_socket.gethostname(), None):
            ip = info[4][0]
            try:
                parts = list(map(int, ip.split(".")))
                if parts[0] == 100 and 64 <= parts[1] <= 127:
                    return ip
            except Exception:
                pass
    except Exception:
        pass
    return ""

def _get_local_ip() -> str:
    try:
        s = _socket.socket(_socket.AF_INET, _socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

def _ensure_ssl_cert(local_ip: str, extra_ips: Optional[List[str]] = None):
    """
    Genera (o ricarica) un certificato autofirmato persistente che include
    localhost, 127.0.0.1, l'IP LAN corrente e gli IP Tailscale come SAN.
    Rigenera automaticamente se gli IP sono cambiati.
    Ritorna (cert_path, key_path) oppure 'adhoc' come fallback.
    """
    ssl_dir   = Path(__file__).parent / "ssl"
    cert_path = ssl_dir / "cert.pem"
    key_path  = ssl_dir / "key.pem"
    ip_stamp  = ssl_dir / "ip.txt"

    all_ips = [local_ip] + (extra_ips or [])
    stamp   = ",".join(sorted(filter(None, all_ips)))

    if cert_path.exists() and key_path.exists() and ip_stamp.exists():
        if ip_stamp.read_text().strip() == stamp:
            return (str(cert_path), str(key_path))

    ssl_dir.mkdir(exist_ok=True)

    try:
        from cryptography import x509
        from cryptography.x509.oid import NameOID
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        import datetime, ipaddress

        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Rooting Future Lab")])
        san_list: list = [
            x509.DNSName("localhost"),
            x509.IPAddress(ipaddress.IPv4Address("127.0.0.1")),
        ]
        for ip in all_ips:
            try:
                san_list.append(x509.IPAddress(ipaddress.IPv4Address(ip)))
            except Exception:
                pass

        cert = (
            x509.CertificateBuilder()
            .subject_name(name).issuer_name(name)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(datetime.datetime.utcnow())
            .not_valid_after(datetime.datetime.utcnow() + datetime.timedelta(days=3650))
            .add_extension(x509.SubjectAlternativeName(san_list), critical=False)
            .sign(key, hashes.SHA256())
        )
        cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
        key_path.write_bytes(key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.TraditionalOpenSSL,
            serialization.NoEncryption(),
        ))
        ip_stamp.write_text(stamp)
        print(f"[SSL] Certificato generato per: {', '.join(filter(None, ['localhost']+all_ips))}")
        return (str(cert_path), str(key_path))

    except ImportError:
        print("[SSL] 'cryptography' non installato — uso SSL adhoc")
        return "adhoc"
    except Exception as e:
        print(f"[SSL] Errore: {e} — uso SSL adhoc")
        return "adhoc"

def _try_start_tunnel(port: int) -> None:
    """
    Tenta in ordine:
      1. ngrok con dominio statico (NGROK_DOMAIN env var) - URL permanente
      2. cloudflared named tunnel (CF_TUNNEL_NAME) - URL permanente
      3. cloudflared quick tunnel - URL casuale, cambia al riavvio
      4. ngrok senza dominio - URL casuale, cambia al riavvio
    """
    import subprocess, re, time as _t, json as _j, urllib.request as _ur
    _lab_access["tunnel_status"] = "starting"

    # 1. ngrok STATIC domain
    ngrok_domain = os.environ.get("NGROK_DOMAIN", "").strip()
    if ngrok_domain:
        try:
            subprocess.Popen(
                ["ngrok", "http", f"--domain={ngrok_domain}", str(port)],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                creationflags=_WIN_NO_WINDOW,
            )
            _t.sleep(4)
            url = f"https://{ngrok_domain}"
            _lab_access["tunnel"] = url
            _lab_access["tunnel_status"] = "active"
            print(f"\n[LAB] ✓ ngrok static domain: {url}/lab\n")
            return
        except FileNotFoundError:
            print("[LAB] NGROK_DOMAIN impostato ma ngrok non trovato.")
        except Exception as e:
            app.logger.debug(f"ngrok static: {e}")

    # 2. cloudflared NAMED tunnel
    cf_tunnel = os.environ.get("CF_TUNNEL_NAME", "").strip()
    if cf_tunnel:
        try:
            subprocess.Popen(
                ["cloudflared", "tunnel", "--no-autoupdate", "run", cf_tunnel],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                creationflags=_WIN_NO_WINDOW,
            )
            _t.sleep(5)
            cf_url = os.environ.get("CF_TUNNEL_URL", "").strip()
            if cf_url:
                _lab_access["tunnel"] = cf_url
                _lab_access["tunnel_status"] = "active"
                print(f"\n[LAB] ✓ Cloudflare tunnel: {cf_url}/lab\n")
                return
        except FileNotFoundError:
            pass
        except Exception as e:
            app.logger.debug(f"cloudflared named: {e}")

    # 3. cloudflared QUICK tunnel (URL casuale)
    try:
        proc = subprocess.Popen(
            ["cloudflared", "tunnel", "--url", f"https://localhost:{port}",
             "--no-autoupdate"],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
            creationflags=_WIN_NO_WINDOW,
        )
        for _ in range(60):
            line = proc.stdout.readline()
            m = re.search(r'https://[a-z0-9-]+\.trycloudflare\.com', line)
            if m:
                url = m.group(0)
                _lab_access["tunnel"] = url
                _lab_access["tunnel_status"] = "active"
                print(f"\n[LAB] ✓ Cloudflare quick tunnel: {url}/lab")
                print("[LAB]   (URL cambia al riavvio - imposta NGROK_DOMAIN per URL fisso)\n")
                return
            _t.sleep(0.5)
    except FileNotFoundError:
        pass
    except Exception as e:
        app.logger.debug(f"cloudflared quick: {e}")

    # 4. ngrok senza dominio (URL casuale)
    try:
        subprocess.Popen(
            ["ngrok", "http", str(port)],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            creationflags=_WIN_NO_WINDOW,
        )
        _t.sleep(4)
        data = _j.loads(_ur.urlopen("http://localhost:4040/api/tunnels", timeout=3).read())
        for t in data.get("tunnels", []):
            if t.get("proto") == "https":
                url = t["public_url"]
                _lab_access["tunnel"] = url
                _lab_access["tunnel_status"] = "active"
                print(f"\n[LAB] ✓ ngrok tunnel: {url}/lab")
                print("[LAB]   (URL cambia al riavvio - configura NGROK_DOMAIN per URL fisso)\n")
                return
    except FileNotFoundError:
        pass
    except Exception as e:
        app.logger.debug(f"ngrok: {e}")

    _lab_access["tunnel_status"] = "unavailable"
    print("[LAB] Nessun tunnel. Usa Tailscale per accesso permanente da qualsiasi rete.")

# =============================================================================
# QUESTIONARI DIGITALI BOARD — helpers
# =============================================================================

from questionnaire_schema import QUESTIONNAIRES, QUESTIONNAIRE_ORDER

_WIKI_KB = Path("wiki/kb")


def _wiki_append_plan(club_data: dict, plan_id: str) -> None:
    """Aggiorna wiki dopo ogni piano (Karpathy file-back). Zero LLM."""
    try:
        if not _WIKI_KB.exists():
            return
        club_name = club_data.get("club_name", "Club Sconosciuto")
        category = club_data.get("category", "Eccellenza").lower().replace(" ", "-")
        region = club_data.get("region", "").lower().replace(" ", "-") or "italia"
        city = club_data.get("city", "")
        board_members = club_data.get("board_members", [])
        today = datetime.now().strftime("%Y-%m-%d")

        benchmark_dir = _WIKI_KB / "benchmark"
        benchmark_dir.mkdir(exist_ok=True)
        bench_file = benchmark_dir / f"{category}-{region}.md"

        new_entry = f"\n## {club_name} — Piano {today} (plan_id: {plan_id})\n"
        new_entry += f"- **Categoria:** {club_data.get('category', 'N/A')}\n"
        new_entry += f"- **Città:** {city or 'N/A'}\n"
        new_entry += f"- **Board consultati:** {len(board_members)}\n"

        if bench_file.exists():
            bench_file.write_text(bench_file.read_text(encoding="utf-8") + new_entry, encoding="utf-8")
        else:
            bench_file.write_text(f"# Benchmark {category} — {region}\n\n" + new_entry, encoding="utf-8")

        log_file = _WIKI_KB / "log.md"
        log_entry = f"\n---\n## {today} — {club_name}\n- Plan ID: {plan_id}\n"
        if log_file.exists():
            log_file.write_text(log_file.read_text(encoding="utf-8") + log_entry, encoding="utf-8")

        logger.info(f"Wiki updated after plan {plan_id} for {club_name}")
    except Exception as e:
        logger.warning(f"Wiki append failed (non-blocking): {e}")


def _q_path(club_slug, member_slug, q_id):
    """Path file JSON per singolo questionario compilato."""
    d = QUESTIONNAIRE_DATA_DIR / club_slug / member_slug
    d.mkdir(parents=True, exist_ok=True)
    return d / f"{q_id}.json"


def _q_statuses(club_slug, member_slug):
    """Stato compilazione per ogni questionario."""
    statuses = {}
    for q_id in QUESTIONNAIRE_ORDER:
        p = _q_path(club_slug, member_slug, q_id)
        if p.exists():
            data = json.loads(p.read_text(encoding="utf-8"))
            has_content = any(
                any(v for v in item.values()) if isinstance(item, dict) else bool(item)
                for section_data in data.get("data", {}).values()
                for item in (section_data if isinstance(section_data, list) else [section_data])
            )
            statuses[q_id] = "completed" if has_content else "partial"
        else:
            statuses[q_id] = "empty"
    return statuses


def _get_clubs():
    """Lista club disponibili da data/clubs/."""
    clubs_dir = Path("data/clubs")
    if not clubs_dir.exists():
        return []
    return [(d.name, d.name.replace("-", " ").title()) for d in sorted(clubs_dir.iterdir()) if d.is_dir()]


@app.route("/demo/questionari")
def demo_questionari():
    """Route pubblica demo pre-caricata con Riccione Calcio."""
    session["demo_mode"] = True
    return redirect(url_for("questionnaire_index", club="riccione-calcio-1926", member="demo", role="board"))

@app.route("/questionnaires")
def questionnaire_index():
    club = request.args.get("club", "")
    member = request.args.get("member", "")
    statuses = _q_statuses(club, member) if club and member else {}
    return render_template(
        "questionnaire_index.html",
        questionnaires=QUESTIONNAIRES,
        order=QUESTIONNAIRE_ORDER,
        clubs=_get_clubs(),
        current_club=club,
        member_name=member.replace("-", " ").title() if member else "",
        member_role=request.args.get("role", "board"),
        statuses=statuses,
        year=datetime.now().year,
    )

@app.route("/questionnaire/<club_slug>/<member_slug>/<q_id>")
def questionnaire_form(club_slug, member_slug, q_id):
    if q_id not in QUESTIONNAIRES:
        return "Questionario non trovato", 404

    q = QUESTIONNAIRES[q_id]
    role = request.args.get("role", "board")
    display_name = request.args.get("display_name", member_slug.replace("-", " ").title())

    # Load saved data
    p = _q_path(club_slug, member_slug, q_id)
    saved = {}
    if p.exists():
        saved = json.loads(p.read_text(encoding="utf-8")).get("data", {})

    # Prev/next navigation
    idx = QUESTIONNAIRE_ORDER.index(q_id)
    prev_id = QUESTIONNAIRE_ORDER[idx - 1] if idx > 0 else None
    next_id = QUESTIONNAIRE_ORDER[idx + 1] if idx < len(QUESTIONNAIRE_ORDER) - 1 else None

    return render_template(
        "questionnaire_form.html",
        questionnaire=q,
        q_id=q_id,
        club_slug=club_slug,
        member_slug=member_slug,
        role=role,
        display_name=display_name,
        saved=saved,
        saved_json=json.dumps(saved, ensure_ascii=False),
        prev_id=prev_id,
        prev_title=QUESTIONNAIRES[prev_id]["title"] if prev_id else "",
        next_id=next_id,
        next_title=QUESTIONNAIRES[next_id]["title"] if next_id else "",
    )

@app.route("/api/questionnaire/<club_slug>/<member_slug>/<q_id>", methods=["POST"])
def api_questionnaire_save(club_slug, member_slug, q_id):
    if q_id not in QUESTIONNAIRES:
        return jsonify({"error": "Unknown questionnaire"}), 404

    body = request.get_json()
    p = _q_path(club_slug, member_slug, q_id)

    record = {
        "club": club_slug,
        "member": member_slug,
        "questionnaire": q_id,
        "role": body.get("role", "board"),
        "display_name": body.get("display_name", member_slug),
        "data": body.get("data", {}),
        "updated_at": datetime.now().isoformat(),
    }
    p.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")

    return jsonify({"success": True, "path": str(p)})

@app.route("/api/questionnaire/<club_slug>/<member_slug>/export-md", methods=["POST"])
def api_questionnaire_export_md(club_slug, member_slug):
    """Converte tutte le risposte di un membro in markdown per wiki pipeline."""
    lines = []
    display_name = member_slug.replace("-", " ").title()

    for q_id in QUESTIONNAIRE_ORDER:
        p = _q_path(club_slug, member_slug, q_id)
        if not p.exists():
            continue
        record = json.loads(p.read_text(encoding="utf-8"))
        data = record.get("data", {})
        display_name = record.get("display_name", display_name)
        q = QUESTIONNAIRES[q_id]

        lines.append(f"# {q['title']}")
        lines.append("")

        for section in q["sections"]:
            sid = section["id"]
            section_data = data.get(sid, {})

            if section["type"] == "static" and isinstance(section_data, dict):
                for field in section["fields"]:
                    val = section_data.get(field["id"], "").strip()
                    if val:
                        lines.append(f"## {field['label']}")
                        lines.append(val)
                        lines.append("")

            elif section["type"] == "repeatable" and isinstance(section_data, list):
                lines.append(f"## {section['title']}")
                lines.append("")
                for i, item in enumerate(section_data, 1):
                    # First field as heading
                    first_key = section["fields"][0]["id"]
                    heading = item.get(first_key, f"Elemento {i}")
                    lines.append(f"### {heading}")
                    for field in section["fields"][1:]:
                        val = item.get(field["id"], "").strip()
                        if val:
                            lines.append(f"**{field['label']}:** {val}")
                    lines.append("")

    md_content = "\n".join(lines)

    # Save to wiki/raw directory
    raw_dir = Path(f"wiki/raw/{club_slug}")
    raw_dir.mkdir(parents=True, exist_ok=True)
    md_path = raw_dir / f"questionario-{member_slug}.md"
    md_path.write_text(md_content, encoding="utf-8")

    return jsonify({
        "success": True,
        "path": str(md_path),
        "chars": len(md_content),
        "member": display_name,
    })

@app.route("/api/questionnaire/<club_slug>/export-all-md", methods=["POST"])
def api_questionnaire_export_all_md(club_slug):
    """Esporta tutti i membri di un club in markdown."""
    members_dir = QUESTIONNAIRE_DATA_DIR / club_slug
    if not members_dir.exists():
        return jsonify({"error": "No data for club"}), 404

    results = []
    for member_dir in sorted(members_dir.iterdir()):
        if member_dir.is_dir():
            member_slug = member_dir.name
            # Trigger individual export
            with app.test_request_context(json={}):
                lines = []
                display_name = member_slug.replace("-", " ").title()
                for q_id in QUESTIONNAIRE_ORDER:
                    p = _q_path(club_slug, member_slug, q_id)
                    if not p.exists():
                        continue
                    record = json.loads(p.read_text(encoding="utf-8"))
                    data = record.get("data", {})
                    display_name = record.get("display_name", display_name)
                    q = QUESTIONNAIRES[q_id]
                    lines.append(f"# {q['title']}")
                    lines.append("")
                    for section in q["sections"]:
                        sid = section["id"]
                        section_data = data.get(sid, {})
                        if section["type"] == "static" and isinstance(section_data, dict):
                            for field in section["fields"]:
                                val = section_data.get(field["id"], "").strip()
                                if val:
                                    lines.append(f"## {field['label']}")
                                    lines.append(val)
                                    lines.append("")
                        elif section["type"] == "repeatable" and isinstance(section_data, list):
                            lines.append(f"## {section['title']}")
                            lines.append("")
                            for i, item in enumerate(section_data, 1):
                                first_key = section["fields"][0]["id"]
                                heading = item.get(first_key, f"Elemento {i}")
                                lines.append(f"### {heading}")
                                for field in section["fields"][1:]:
                                    val = item.get(field["id"], "").strip()
                                    if val:
                                        lines.append(f"**{field['label']}:** {val}")
                                lines.append("")

                md_content = "\n".join(lines)
                raw_dir = Path(f"wiki/raw/{club_slug}")
                raw_dir.mkdir(parents=True, exist_ok=True)
                md_path = raw_dir / f"questionario-{member_slug}.md"
                md_path.write_text(md_content, encoding="utf-8")
                results.append({"member": display_name, "path": str(md_path), "chars": len(md_content)})

    return jsonify({"success": True, "exported": results})

@app.route("/free-swot")
def free_swot_page():
    """Landing page pubblica: mini-SWOT gratuita come funnel hook."""
    return render_template("free_swot.html")

@app.route("/api/free-swot", methods=["POST"])
def api_free_swot():
    """Genera mini-SWOT con AI (o fallback formattato)."""
    body = request.get_json()
    club = body.get("club", "Club")
    category = body.get("category", "")
    region = body.get("region", "")
    s = body.get("strengths", "")
    w = body.get("weaknesses", "")
    o = body.get("opportunities", "")
    t = body.get("threats", "")

    try:
        prompt = f"""Sei un consulente strategico sportivo. Analizza questo club calcistico e genera un'analisi SWOT professionale.

Club: {club} ({category}, {region})
Punti di forza indicati: {s}
Debolezze indicate: {w}
Opportunita' indicate: {o}
Minacce indicate: {t}

Per ogni quadrante SWOT, espandi i punti indicati con 3-5 bullet professionali.
Aggiungi un paragrafo di sintesi strategica (max 3 righe).
Rispondi in formato JSON: {{"strengths": "html bullets", "weaknesses": "html bullets", "opportunities": "html bullets", "threats": "html bullets", "summary": "testo sintesi"}}"""

        _swot_client = OpenRouterClient()
        result = _swot_client.generate_content(prompt, max_tokens=2000)
        # Parse JSON from response
        import re as _re
        json_match = _re.search(r'\{.*\}', result, _re.DOTALL)
        if json_match:
            data = json.loads(json_match.group())
            data["success"] = True
            return jsonify(data)
    except Exception as e:
        logger.warning(f"Free SWOT AI generation failed: {e}")

    # Fallback
    return jsonify({"success": True, "strengths": "", "weaknesses": "", "opportunities": "", "threats": "", "summary": ""})

@app.route("/api/generate-from-questionnaires", methods=["POST"])
@login_required
def api_generate_from_questionnaires():
    """
    Genera piano strategico dai questionari digitali compilati.
    Converte risposte JSON in club_data per l'orchestratore multi-agente.
    """
    try:
        body = request.get_json()
        club_slug = body.get("club_slug")
        if not club_slug:
            return jsonify({"error": "club_slug required"}), 400

        # Raccogli tutti i questionari di tutti i membri
        members_dir = QUESTIONNAIRE_DATA_DIR / club_slug
        if not members_dir.exists():
            return jsonify({"error": "No questionnaire data for club"}), 404

        # Aggrega risposte per tipo questionario
        all_responses = {}  # {q_id: [{member, data}, ...]}
        member_names = []
        for member_dir in sorted(members_dir.iterdir()):
            if not member_dir.is_dir():
                continue
            member_slug = member_dir.name
            for q_file in member_dir.glob("*.json"):
                q_id = q_file.stem
                record = json.loads(q_file.read_text(encoding="utf-8"))
                member_name = record.get("display_name", member_slug)
                if member_name not in member_names:
                    member_names.append(member_name)
                if q_id not in all_responses:
                    all_responses[q_id] = []
                all_responses[q_id].append({
                    "member": member_name,
                    "role": record.get("role", "board"),
                    "data": record.get("data", {}),
                })

        if not all_responses:
            return jsonify({"error": "No completed questionnaires found"}), 404

        # Costruisci club_data nel formato atteso dall'orchestratore
        club_name = club_slug.replace("-", " ").title()
        club_data = {
            "club_name": club_name,
            "city": "",
            "region": "",
            "category": body.get("category", "Eccellenza"),
            "country": body.get("country", "Italy"),
            "board_members": member_names,
            "data_source": "digital_questionnaires",
        }

        # SWOT aggregato
        if "swot" in all_responses:
            swot_agg = {"forza": [], "debolezza": [], "opportunita": [], "minacce": []}
            for resp in all_responses["swot"]:
                grid = resp["data"].get("swot_grid", {})
                for key in swot_agg:
                    val = grid.get(key, "").strip()
                    if val:
                        swot_agg[key].append(f"[{resp['member']}] {val}")
            club_data["swot_aggregated"] = {k: "\n".join(v) for k, v in swot_agg.items()}
            club_data["swot_aggregated_source"] = "questionnaire"

        # Vision sintetizzata
        if "vision" in all_responses:
            visions = []
            for resp in all_responses["vision"]:
                vm = resp["data"].get("vision_main", {})
                parts = []
                if vm.get("nel_2028"):
                    parts.append(f"Nel 2028: {vm['nel_2028']}")
                if vm.get("vision_frase"):
                    parts.append(f"Vision: {vm['vision_frase']}")
                if parts:
                    visions.append(f"[{resp['member']}] {' | '.join(parts)}")
            if visions:
                club_data["synthesized_vision"] = "\n".join(visions)
                club_data["synthesized_vision_source"] = "questionnaire"

        # Mission
        if "mission" in all_responses:
            missions = []
            for resp in all_responses["mission"]:
                mm = resp["data"].get("mission_main", {})
                if mm.get("mission_bozza"):
                    missions.append(f"[{resp['member']}] {mm['mission_bozza']}")
            if missions:
                club_data["synthesized_mission"] = "\n".join(missions)
                club_data["synthesized_mission_source"] = "questionnaire"

        # Valori e fondamenta
        if "valori-fondamenta" in all_responses:
            valori_all = []
            fondamenta_all = []
            for resp in all_responses["valori-fondamenta"]:
                for v in resp["data"].get("valori", []):
                    if v.get("valore"):
                        valori_all.append(f"{v['valore']}: {v.get('descrizione', '')}")
                for f in resp["data"].get("fondamenta", []):
                    if f.get("pilastro"):
                        fondamenta_all.append(f"{f['pilastro']}: {f.get('motivazione', '')}")
            if valori_all:
                club_data["club_values"] = "\n".join(valori_all)
                club_data["club_values_source"] = "questionnaire"
            if fondamenta_all:
                club_data["club_foundations"] = "\n".join(fondamenta_all)
                club_data["club_foundations_source"] = "questionnaire"

        # Competitors
        if "competitors" in all_responses:
            comps = []
            for resp in all_responses["competitors"]:
                for c in resp["data"].get("competitors_list", []):
                    if c.get("nome"):
                        comps.append(f"{c['nome']} (forza: {c.get('punti_forza', 'n/a')}, debolezza: {c.get('debolezze', 'n/a')})")
            if comps:
                club_data["competitors"] = comps[:10]
                club_data["competitors_source"] = "questionnaire"

        # PEST
        if "pest" in all_responses:
            pest_agg = {"politica": [], "economica": [], "sociale": [], "tecnologica": []}
            for resp in all_responses["pest"]:
                grid = resp["data"].get("pest_grid", {})
                for key in pest_agg:
                    val = grid.get(key, "").strip()
                    if val:
                        pest_agg[key].append(f"[{resp['member']}] {val}")
            club_data["pest_analysis"] = {k: "\n".join(v) for k, v in pest_agg.items()}
            club_data["pest_analysis_source"] = "questionnaire"

        # Stakeholders
        if "stakeholders" in all_responses:
            stakeholders = []
            for resp in all_responses["stakeholders"]:
                for s in resp["data"].get("stakeholders_list", []):
                    if s.get("gruppo"):
                        stakeholders.append(f"{s['gruppo']} (importanza: {s.get('importanza', 'n/a')}, azioni: {s.get('azioni', 'n/a')})")
            if stakeholders:
                club_data["stakeholders_analysis"] = "\n".join(stakeholders)
                club_data["stakeholders_analysis_source"] = "questionnaire"

        # Risorse
        if "risorse" in all_responses:
            risorse = []
            for resp in all_responses["risorse"]:
                for r in resp["data"].get("risorse_list", []):
                    if r.get("categoria"):
                        risorse.append(f"{r['categoria']}: attuali={r.get('lista_attuali', 'n/a')}, manca={r.get('cosa_manca', 'n/a')}")
            if risorse:
                club_data["resources_analysis"] = "\n".join(risorse)
                club_data["resources_analysis_source"] = "questionnaire"

        # Lancia generazione (stessa logica di api_generate_plan)
        project_id = f"quest_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        update_project_status(project_id, "processing", 10, "Preparazione dati questionari...")

        def run_generation(p_id, c_data):
            try:
                update_project_status(p_id, "processing", 20, "Generazione piano in corso...")
                result = orchestrator.generate_strategic_plan(
                    club_data=c_data,
                    research_data=None,
                    parallel=True,
                    on_progress=lambda msg, pct: update_project_status(p_id, "processing", 20 + int(pct * 0.7), msg),
                )
                update_project_status(p_id, "completed", 100, "Piano generato con successo")
                # Salva risultato
                plan_id = knowledge_manager.store.save_plan(c_data["club_name"], result)
                # Registra in editor per abilitare export immediato
                plan_record = knowledge_manager.store.get_plan(plan_id)
                if plan_record:
                    review = editor.create_review_from_plan(
                        plan_data=plan_record.plan_data,
                        club_name=plan_record.club_name,
                        metadata={"category": plan_record.category},
                        owner_id=plan_record.owner_id,
                    )
                    review.plan_id = plan_id
                    editor.reviews[plan_id] = review
                _wiki_append_plan(c_data, plan_id)
                update_project_status(p_id, "completed", 100, "Piano salvato", data={"plan_id": plan_id})
            except Exception as e:
                logger.error(f"Generation from questionnaires failed: {e}")
                update_project_status(p_id, "error", 0, str(e))

        analysis_executor.submit(run_generation, project_id, club_data)

        return jsonify({
            "success": True,
            "project_id": project_id,
            "club_name": club_name,
            "members": member_names,
            "questionnaires_found": list(all_responses.keys()),
        })

    except Exception as e:
        logger.error(f"generate-from-questionnaires error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/demo/generate", methods=["POST"])
def api_demo_generate():
    """Genera piano da dati demo Riccione — pubblico, nessun login richiesto."""
    try:
        club_slug = "riccione-calcio-1926"
        members_dir = QUESTIONNAIRE_DATA_DIR / club_slug
        if not members_dir.exists():
            return jsonify({"error": "Demo data not found"}), 404

        all_responses = {}
        member_names = []
        for member_dir in sorted(members_dir.iterdir()):
            if not member_dir.is_dir():
                continue
            for q_file in member_dir.glob("*.json"):
                q_id = q_file.stem
                record = json.loads(q_file.read_text(encoding="utf-8"))
                member_name = record.get("display_name", member_dir.name)
                if member_name not in member_names:
                    member_names.append(member_name)
                if q_id not in all_responses:
                    all_responses[q_id] = []
                all_responses[q_id].append({
                    "member": member_name,
                    "role": record.get("role", "board"),
                    "data": record.get("data", {}),
                })

        if not all_responses:
            return jsonify({"error": "No questionnaire data found"}), 404

        club_name = "Riccione Calcio 1926"
        club_data = {
            "club_name": club_name,
            "city": "Riccione",
            "region": "Emilia-Romagna",
            "category": "Eccellenza",
            "country": "Italy",
            "board_members": member_names,
            "data_source": "digital_questionnaires_demo",
        }

        # SWOT
        if "swot" in all_responses:
            swot_agg = {"forza": [], "debolezza": [], "opportunita": [], "minacce": []}
            for resp in all_responses["swot"]:
                grid = resp["data"].get("swot_grid", {})
                for key in swot_agg:
                    val = grid.get(key, "").strip()
                    if val:
                        swot_agg[key].append(val)
            club_data["swot_aggregated"] = {k: "\n".join(v) for k, v in swot_agg.items()}
            club_data["swot_aggregated_source"] = "questionnaire"

        # Vision
        if "vision" in all_responses:
            visions = []
            for resp in all_responses["vision"]:
                vm = resp["data"].get("vision_main", {})
                parts = [p for p in [vm.get("nel_2028"), vm.get("vision_frase")] if p]
                if parts:
                    visions.append(" | ".join(parts))
            if visions:
                club_data["synthesized_vision"] = "\n".join(visions)
                club_data["synthesized_vision_source"] = "questionnaire"

        # Mission
        if "mission" in all_responses:
            missions = []
            for resp in all_responses["mission"]:
                mm = resp["data"].get("mission_main", {})
                if mm.get("mission_bozza"):
                    missions.append(mm["mission_bozza"])
            if missions:
                club_data["synthesized_mission"] = "\n".join(missions)
                club_data["synthesized_mission_source"] = "questionnaire"

        # Valori e fondamenta
        if "valori-fondamenta" in all_responses:
            valori_all, fondamenta_all = [], []
            for resp in all_responses["valori-fondamenta"]:
                for v in resp["data"].get("valori", []):
                    if v.get("valore"):
                        valori_all.append(f"{v['valore']}: {v.get('descrizione', '')}")
                for f in resp["data"].get("fondamenta", []):
                    if f.get("pilastro"):
                        fondamenta_all.append(f"{f['pilastro']}: {f.get('motivazione', '')}")
            if valori_all:
                club_data["club_values"] = "\n".join(valori_all)
                club_data["club_values_source"] = "questionnaire"
            if fondamenta_all:
                club_data["club_foundations"] = "\n".join(fondamenta_all)
                club_data["club_foundations_source"] = "questionnaire"

        # Competitors
        if "competitors" in all_responses:
            comps = []
            for resp in all_responses["competitors"]:
                for c in resp["data"].get("competitors_list", []):
                    if c.get("nome"):
                        comps.append(f"{c['nome']} (forza: {c.get('punti_forza', 'n/a')}, debolezza: {c.get('debolezze', 'n/a')})")
            if comps:
                club_data["competitors"] = comps[:10]
                club_data["competitors_source"] = "questionnaire"

        # PEST
        if "pest" in all_responses:
            pest_agg = {"politica": [], "economica": [], "sociale": [], "tecnologica": []}
            for resp in all_responses["pest"]:
                grid = resp["data"].get("pest_grid", {})
                for key in pest_agg:
                    val = grid.get(key, "").strip()
                    if val:
                        pest_agg[key].append(val)
            club_data["pest_analysis"] = {k: "\n".join(v) for k, v in pest_agg.items()}
            club_data["pest_analysis_source"] = "questionnaire"

        # Stakeholders
        if "stakeholders" in all_responses:
            stakeholders = []
            for resp in all_responses["stakeholders"]:
                for s in resp["data"].get("stakeholders_list", []):
                    if s.get("gruppo"):
                        stakeholders.append(f"{s['gruppo']} (importanza: {s.get('importanza', 'n/a')}, azioni: {s.get('azioni', 'n/a')})")
            if stakeholders:
                club_data["stakeholders_analysis"] = "\n".join(stakeholders)
                club_data["stakeholders_analysis_source"] = "questionnaire"

        # Risorse
        if "risorse" in all_responses:
            risorse = []
            for resp in all_responses["risorse"]:
                for r in resp["data"].get("risorse_list", []):
                    if r.get("categoria"):
                        risorse.append(f"{r['categoria']}: attuali={r.get('lista_attuali', 'n/a')}, manca={r.get('cosa_manca', 'n/a')}")
            if risorse:
                club_data["resources_analysis"] = "\n".join(risorse)
                club_data["resources_analysis_source"] = "questionnaire"

        project_id = f"demo_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        update_project_status(project_id, "processing", 10, "Avvio generazione demo...")

        def run_demo_generation(p_id, c_data):
            try:
                update_project_status(p_id, "processing", 20, "6 agenti AI al lavoro...")
                result = orchestrator.generate_strategic_plan(
                    club_data=c_data,
                    research_data=None,
                    parallel=True,
                    on_progress=lambda msg, pct: update_project_status(p_id, "processing", 20 + int(pct * 0.7), msg),
                )
                plan = result["plan"]
                sources = result.get("sources", [])
                import uuid
                plan_id = str(uuid.uuid4())
                plan_record = PlanRecord(
                    id=plan_id,
                    club_name=c_data["club_name"],
                    category=c_data.get("category", ""),
                    region=c_data.get("region", ""),
                    created_at=datetime.now().isoformat(),
                    status="draft",
                    plan_data=plan,
                    sources_count=len(sources),
                    owner_id=None,
                )
                knowledge_manager.store.save_plan(plan_record)
                review = editor.create_review_from_plan(
                    plan_data=plan,
                    club_name=c_data["club_name"],
                    sources=sources,
                    metadata={"category": c_data.get("category", "")},
                    owner_id=None,
                )
                review.plan_id = plan_id
                editor.reviews[plan_id] = review
                _wiki_append_plan(c_data, plan_id)
                update_project_status(p_id, "completed", 100, "Piano generato", data={"plan_id": plan_id})
            except Exception as e:
                logger.error(f"Demo generation failed: {e}")
                update_project_status(p_id, "error", 0, str(e))

        analysis_executor.submit(run_demo_generation, project_id, club_data)
        session["demo_mode"] = True

        return jsonify({
            "success": True,
            "project_id": project_id,
            "club_name": club_name,
            "questionnaires_found": list(all_responses.keys()),
        })

    except Exception as e:
        logger.error(f"Demo generate error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/api/wiki/anagrafica", methods=["POST"])
def api_wiki_anagrafica():
    """
    Salva anagrafica club nel wiki. Pubblico — chiamato dalla splash page.
    Crea wiki/kb/anagrafica/{slug}.md e aggiorna index.md e log.md.
    """
    try:
        body = request.get_json(silent=True) or {}
        club_name = body.get("club_name", "").strip()
        if not club_name:
            return jsonify({"error": "club_name required"}), 400

        from wiki_reader import slugify
        slug = slugify(club_name)
        category = body.get("category", "").strip()
        city = body.get("city", "").strip()
        region = body.get("region", "").strip()
        board_size = int(body.get("board_size", 0))
        email = body.get("email", "").strip()
        notes = body.get("notes", "").strip()
        today = datetime.now().strftime("%Y-%m-%d")

        anagrafica_dir = Path("wiki/kb/anagrafica")
        anagrafica_dir.mkdir(parents=True, exist_ok=True)

        page = f"""---
title: "Anagrafica: {club_name}"
tags: [anagrafica, {slug}, {category.lower().replace(' ', '-')}, {region.lower().replace(' ', '-')}]
club_slug: {slug}
category: {category}
region: {region}
date_created: {today}
date_updated: {today}
source: splash_form
---

# {club_name}

## Dati Base

- **Categoria:** {category or 'N/A'}
- **Città:** {city or 'N/A'}
- **Regione:** {region or 'N/A'}
- **Componenti Board:** {board_size or 'N/A'}
- **Email referente:** {email or 'N/A'}
{"" if not notes else f"- **Note:** {notes}"}
"""
        page_path = anagrafica_dir / f"{slug}.md"
        page_path.write_text(page, encoding="utf-8")

        # Aggiorna index.md: sostituisce il placeholder o aggiunge voce
        index_path = Path("wiki/kb/index.md")
        if index_path.exists():
            idx = index_path.read_text(encoding="utf-8")
            entry = f"- **[{club_name}](anagrafica/{slug}.md)** -- {category}, {region}."
            placeholder = "_Nessun club ancora registrato._"
            if placeholder in idx:
                idx = idx.replace(placeholder, entry)
            elif f"anagrafica/{slug}.md" not in idx:
                idx = idx.replace(
                    "## Club",
                    f"{entry}\n\n## Club"
                ).replace("## Anagrafica\n\n> Profili base dei club raccolti dalla splash page. Disponibili agli agenti prima della generazione del piano.\n\n",
                          f"## Anagrafica\n\n> Profili base dei club raccolti dalla splash page. Disponibili agli agenti prima della generazione del piano.\n\n")
                # simpler: just insert entry before ## Club
                idx = idx.replace("\n## Club", f"\n{entry}\n\n## Club", 1)
            index_path.write_text(idx, encoding="utf-8")

        # Append log
        log_path = Path("wiki/kb/log.md")
        if log_path.exists():
            log_entry = f"\n---\n## {today} -- Anagrafica: {club_name}\n- Slug: {slug}\n- Categoria: {category}, {region}\n- Board: {board_size} membri\n- Fonte: splash_form\n"
            log_path.write_text(log_path.read_text(encoding="utf-8") + log_entry, encoding="utf-8")

        logger.info(f"Wiki anagrafica saved: {slug}")
        return jsonify({"success": True, "slug": slug, "redirect": f"/demo/questionari?club_prefill={slug}&club_name={club_name}"})

    except Exception as e:
        logger.error(f"Wiki anagrafica error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/demo/risultati")
def demo_risultati():
    """Pagina pubblica risultati demo — polling + 3 download."""
    project_id = request.args.get("project_id", "")
    return render_template("demo_risultati.html", project_id=project_id)

@app.route("/demo/quicktest")
def demo_quicktest():
    """
    Test end-to-end con un click — senza compilare questionari.
    Legge le fixture in data/questionnaires/riccione-calcio-1926/,
    avvia generazione via JS fetch, redirect automatico alla pagina risultati.

    Uso: apri /demo/quicktest nel browser.
    """
    members_dir = QUESTIONNAIRE_DATA_DIR / "riccione-calcio-1926"
    if not members_dir.exists() or not any(members_dir.iterdir()):
        return (
            "<h2 style='font-family:sans-serif'>Fixture mancanti</h2>"
            "<p style='font-family:sans-serif'>Cartella <code>data/questionnaires/riccione-calcio-1926/</code>"
            " non trovata. Esegui <code>git pull</code> e riavvia.</p>",
            404,
        )
    return """<!DOCTYPE html>
<html lang="it"><head><meta charset="UTF-8">
<title>Quick Test — Rooting Future</title>
<style>
  body{font-family:system-ui,sans-serif;display:flex;flex-direction:column;
       align-items:center;justify-content:center;min-height:100vh;margin:0;background:#f7fafc;}
  .box{background:white;border-radius:12px;padding:40px;box-shadow:0 2px 12px rgba(0,0,0,.1);text-align:center;max-width:400px;}
  .spinner{width:40px;height:40px;border:4px solid #e2e8f0;border-top-color:#3182ce;
           border-radius:50%;animation:spin 0.8s linear infinite;margin:20px auto;}
  @keyframes spin{to{transform:rotate(360deg)}}
  p{color:#718096;font-size:.9rem}
  .err{color:#e53e3e;font-size:.85rem;margin-top:12px}
</style>
</head>
<body>
<div class="box">
  <div class="spinner"></div>
  <h2 style="margin:0 0 8px;color:#1a365d">Avvio generazione demo...</h2>
  <p id="msg">Caricamento dati Riccione Calcio 1926</p>
  <div id="err" class="err"></div>
</div>
<script>
fetch('/api/demo/generate', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: '{}'
})
.then(r => r.json())
.then(d => {
  if (d.success) {
    document.getElementById('msg').textContent = 'Redirect alla pagina risultati...';
    window.location.href = '/demo/risultati?project_id=' + d.project_id;
  } else {
    document.getElementById('err').textContent = 'Errore: ' + (d.error || JSON.stringify(d));
  }
})
.catch(e => {
  document.getElementById('err').textContent = 'Errore di rete: ' + e;
});
</script>
</body></html>"""

if __name__ == "__main__":
    PORT = 5000

    # Verifica configurazione
    missing = get_missing_config()
    if missing:
        print(f"WARNING: Missing config: {missing}")
        print("Some features may not work correctly.")

    # Assicura directories
    OUTPUT_DIR.mkdir(exist_ok=True)
    KNOWLEDGE_DIR.mkdir(exist_ok=True)

    # Detect local IP and Tailscale IP
    _local_ip = _get_local_ip()
    _ts_ip    = _get_tailscale_ip()

    # SSL cert includes both LAN IP and Tailscale IP in SAN
    _ssl_ctx  = _ensure_ssl_cert(_local_ip, extra_ips=[_ts_ip] if _ts_ip else [])
    _scheme   = "https"

    _lab_access["lan"] = f"{_scheme}://{_local_ip}:{PORT}"
    if _ts_ip:
        _lab_access["tailscale"] = f"{_scheme}://{_ts_ip}:{PORT}"

    print("[OK] SSE Log Streaming attivo (Global)")
    _ts_line = (f"\n     Tailscale  :  {_scheme}://{_ts_ip}:{PORT}/lab"
                f"  ← SEMPRE RAGGIUNGIBILE") if _ts_ip else (
                "\n     Tailscale  :  non attivo (vedi /lab/setup per installarlo)")
    print(f"""
    ═══════════════════════════════════════════════════════════════
     Rooting Future Strategy Engine v6.0  [HTTPS]
    ───────────────────────────────────────────────────────────────
     PC locale  :  {_scheme}://127.0.0.1:{PORT}
     Rete LAN   :  {_scheme}://{_local_ip}:{PORT}{_ts_line}
     Setup PWA  :  {_scheme}://{_local_ip}:{PORT}/lab/setup
    ═══════════════════════════════════════════════════════════════
    """)
    print("[*] Prima apertura Android: Avanzate → Procedi (una volta sola)")
    print("[*] Premi Ctrl+C per terminare")

    if not _ts_ip:
        print("[*] Tailscale non rilevato → avvio tunnel in background…\n")
        threading.Thread(target=_try_start_tunnel, args=(PORT,), daemon=True).start()
    else:
        print("[*] Tailscale attivo → accesso garantito da qualsiasi rete.\n")
        _lab_access["tunnel_status"] = "active_tailscale"

    import webbrowser
    from threading import Timer

    def open_browser():
        webbrowser.open_new(f"{_scheme}://127.0.0.1:{PORT}/lab")

    Timer(1.5, open_browser).start()

    app.run(
        host="0.0.0.0", port=PORT,
        ssl_context=_ssl_ctx,
        debug=False, threaded=True, use_reloader=False,
    )
