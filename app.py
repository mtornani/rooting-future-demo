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
    STRIPE_PUBLIC_KEY,
    STRIPE_SECRET_KEY,
    STRIPE_WEBHOOK_SECRET,
    CREDIT_PRICE_ID,
    validate_config,
    get_missing_config,
)

import stripe

stripe.api_key = STRIPE_SECRET_KEY

from agents import MultiAgentOrchestrator, AgentRole
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
from structured_agent import StructuredOrchestrator
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


# SSE handler rimosso perché instabile su alcuni sistemi
log_stream_handler = None


from license_manager import licenser

# =============================================================================
# LICENSE ENFORCEMENT MIDDLEWARE
# =============================================================================


@app.before_request
def check_system_activation():
    """
    Verifica l'attivazione della licenza prima di ogni richiesta.
    Controlla sia la validità della chiave che la scadenza temporale.
    Esclude rotte di login, static e la pagina di attivazione stessa.
    """
    allowed_routes = ["activation", "static", "auth.login", "auth.logout"]
    if request.endpoint in allowed_routes or not request.endpoint:
        return

    license_status = licenser.get_license_status()

    if not license_status["valid"]:
        if license_status.get("expired"):
            flash(license_status["message"], "error")
        if request.endpoint != "activation":
            return redirect(url_for("activation"))


@app.route("/activation", methods=["GET", "POST"])
def activation():
    """Pagina di blocco e attivazione licenza"""
    machine_code = licenser.get_machine_code()

    if request.method == "POST":
        email = request.form.get("email")
        key = request.form.get("key")

        if licenser.verify_license(key, email):
            # Salva licenza con scadenza (default 365 giorni, perpetua se 0)
            duration_days = request.form.get("duration_days", type=int) or 365
            licenser.save_license(email, key, duration_days=duration_days)

            # Auto-creazione utente se non esiste
            from auth_manager import bcrypt, User
            from flask_login import login_user

            existing_user = knowledge_manager.store.get_user_by_email(email)
            if not existing_user:
                # Genera password temporanea basata su parte della license key
                temp_password = key[:8]  # Primi 8 caratteri della chiave
                password_hash = bcrypt.generate_password_hash(temp_password).decode('utf-8')

                # Crea utente con ruolo 'manager' e crediti iniziali
                user_id = knowledge_manager.store.create_user(
                    email=email,
                    password_hash=password_hash,
                    full_name="",  # L'utente può aggiornarlo dopo
                    role="manager"  # Ruolo di default per clienti con licenza
                )
                # Assegna crediti iniziali (es. 10 piani)
                knowledge_manager.store.update_user_credits(user_id, 10)

                # Recupera l'utente appena creato
                existing_user = knowledge_manager.store.get_user_by_email(email)

                flash(f"Account creato! Password temporanea: {temp_password} (cambiala nelle impostazioni)", "success")

            # Auto-login dell'utente
            if existing_user:
                user = User(existing_user)
                login_user(user)

            flash("Sistema Attivato con Successo!", "success")
            return redirect(url_for("index"))
        else:
            flash("Chiave di Licenza non valida per questo PC.", "error")

    return render_template("activation.html", machine_code=machine_code)


@app.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    """Pagina impostazioni - configurazione API keys"""
    if request.method == "POST":
        gemini_key = request.form.get("gemini_api_key", "").strip()
        serper_key = request.form.get("serper_api_key", "").strip()
        openrouter_key = request.form.get("openrouter_api_key", "").strip()
        openrouter_model = request.form.get("openrouter_model", "").strip()
        ai_provider = request.form.get("ai_provider", "gemini").strip()

        # Salva configurazione usando lo stesso path di config.py
        from config import get_config_path
        config_path = get_config_path()
        print(f"[CONFIG SAVE] Saving to: {config_path}")
        local_config = {}
        if config_path.exists():
            try:
                with open(config_path, "r") as f:
                    local_config = json.load(f)
            except:
                pass

        # Aggiorna solo le chiavi non vuote e non mascherate
        # I valori mascherati iniziano con "..." e non devono sovrascrivere le chiavi reali
        def is_real_key(key):
            return key and not key.startswith("...")

        if is_real_key(gemini_key):
            local_config["gemini_api_key"] = gemini_key
            os.environ["GEMINI_API_KEY"] = gemini_key
        if is_real_key(serper_key):
            local_config["serper_api_key"] = serper_key
            os.environ["SERPER_API_KEY"] = serper_key
        if is_real_key(openrouter_key):
            local_config["openrouter_api_key"] = openrouter_key
            os.environ["OPENROUTER_API_KEY"] = openrouter_key
        if openrouter_model:
            local_config["openrouter_model"] = openrouter_model
            os.environ["OPENROUTER_MODEL"] = openrouter_model

        # Salva provider AI selezionato
        local_config["ai_provider"] = ai_provider
        os.environ["AI_PROVIDER"] = ai_provider

        # Salva
        with open(config_path, "w") as f:
            json.dump(local_config, f, indent=2)

        # Reinizializza gli agenti con le nuove API key
        try:
            orchestrator.reinit()
            structured_orchestrator.reinit()
            logger.info("Agenti reinizializzati con nuove API key")
            flash("Impostazioni salvate e applicate con successo!", "success")
        except Exception as e:
            logger.error(f"Errore reinizializzazione agenti: {e}")
            flash("Impostazioni salvate. Riavvia l'applicazione se i cambiamenti non sono attivi.", "warning")

        return redirect(url_for("settings"))

    # Carica configurazione attuale
    from config import OPENROUTER_MODELS, OPENROUTER_DEFAULT_MODEL as OR_DEFAULT
    config_data = {
        "gemini_api_key": os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY") or "",
        "serper_api_key": os.environ.get("SERPER_API_KEY") or "",
        "openrouter_api_key": os.environ.get("OPENROUTER_API_KEY") or "",
        "openrouter_model": os.environ.get("OPENROUTER_MODEL") or OR_DEFAULT,
        "ai_provider": os.environ.get("AI_PROVIDER") or "gemini",
    }

    # Maschera le chiavi per sicurezza (mostra solo ultimi 4 caratteri)
    for key_name in ("gemini_api_key", "serper_api_key", "openrouter_api_key"):
        val = config_data[key_name]
        if val and len(val) > 8:
            config_data[key_name] = "..." + val[-4:]

    return render_template(
        "settings.html",
        config=config_data,
        license_valid=check_license_valid(),
        license_status=licenser.get_license_status(),
        hwid=licenser.get_machine_code(),
        openrouter_models=OPENROUTER_MODELS,
    )


@app.route("/api/test-gemini-key", methods=["POST"])
@login_required
def test_gemini_key():
    """Testa se una chiave Gemini API funziona"""
    data = request.get_json()
    api_key = data.get("api_key", "")

    if not api_key:
        return jsonify({"success": False, "error": "Chiave API mancante"})

    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-2.0-flash")
        response = model.generate_content("Rispondi solo 'OK' se funziona.")
        if response and response.text:
            return jsonify({"success": True, "message": "Connessione riuscita"})
        else:
            return jsonify({"success": False, "error": "Risposta vuota dal modello"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


@app.route("/api/test-openrouter-key", methods=["POST"])
@login_required
def test_openrouter_key():
    """Testa se una chiave OpenRouter API funziona"""
    data = request.get_json()
    api_key = data.get("api_key", "")
    model_name = data.get("model", "google/gemini-2.0-flash-exp:free")

    if not api_key:
        return jsonify({"success": False, "error": "Chiave API mancante"})

    try:
        from agents import OpenRouterClient
        client = OpenRouterClient(api_key=api_key, model=model_name)
        if not client.available:
            return jsonify({"success": False, "error": "Libreria openai non installata. Installa con: pip install openai"})
        result = client.generate_content("Rispondi solo 'OK' se funziona.", temperature=0.1, max_tokens=50)
        if result and len(result.strip()) > 0:
            return jsonify({"success": True, "message": f"Connessione riuscita ({model_name})"})
        else:
            return jsonify({"success": False, "error": "Risposta vuota dal modello"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


def check_license_valid():
    """Verifica se la licenza è valida (chiave + scadenza)"""
    status = licenser.get_license_status()
    return status["valid"]


# Registra routes n8n
register_n8n_routes(app)


# Aggiungi 'now' al contesto Jinja2
@app.context_processor
def inject_now():
    return {"now": datetime.now}


# =============================================================================
# AI PROVIDERS — ADAPTER LAYER
# Crea i provider giusti in base alle env vars. Zero impatto se LOCAL_RAG=0.
# =============================================================================

try:
    from ai_providers.factory import create_all_providers
    _ai_embedding_provider, _ai_generation_provider, _ai_vector_store = create_all_providers()
    logger.info(
        f"AI Providers inizializzati: "
        f"embedding={type(_ai_embedding_provider).__name__}, "
        f"generation={type(_ai_generation_provider).__name__}, "
        f"vector_store={type(_ai_vector_store).__name__ if _ai_vector_store else 'SQLite(default)'}"
    )
except Exception as e:
    logger.warning(f"AI Providers non inizializzati (fallback a Gemini): {e}")
    _ai_embedding_provider = None
    _ai_generation_provider = None
    _ai_vector_store = None


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

# Knowledge manager (per apprendimento)
# Se LOCAL_RAG=1, inietta ProviderKnowledgeRAG al posto di GeminiKnowledgeRAG
_rag_override = None
if _ai_embedding_provider is not None and os.environ.get("LOCAL_RAG", "0").strip() == "1":
    try:
        from knowledge_store import ProviderKnowledgeRAG
        _rag_override = ProviderKnowledgeRAG(
            embedding_provider=_ai_embedding_provider,
            vector_store=_ai_vector_store,
        )
        logger.info("KnowledgeManager: usando ProviderKnowledgeRAG (LOCAL_RAG=1)")
    except Exception as e:
        logger.warning(f"ProviderKnowledgeRAG non inizializzato: {e}")

knowledge_manager = KnowledgeManager(
    file_search_manager=file_search_manager,
    rag_override=_rag_override,
)

# Session Manager (REF-003 / UX-001b)
from session_manager import init_session_manager
session_manager = init_session_manager(store=knowledge_manager.store)

# Init Auth
init_auth(app, knowledge_manager.store)

# Multi-Agent Orchestrator
orchestrator = MultiAgentOrchestrator(
    knowledge_store=knowledge_manager,  # Pass full manager for RAG access
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
    file_search_store_name=file_search_store_name, knowledge_store=knowledge_manager
) # Sistema strutturato v6.0

# =============================================================================
# LEGAL & GDPR
# =============================================================================


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
# PAYMENTS - STRIPE INTEGRATION
# =============================================================================


@app.route("/api/payments/create-checkout", methods=["POST"])
@login_required
def create_checkout_session():
    """Crea una sessione di pagamento Stripe per l'acquisto di crediti"""
    try:
        data = request.json
        quantity = data.get("quantity", 1)

        checkout_session = stripe.checkout.Session.create(
            customer_email=current_user.email,
            payment_method_types=["card"],
            line_items=[
                {
                    "price": CREDIT_PRICE_ID,
                    "quantity": quantity,
                }
            ],
            mode="payment",
            success_url=url_for("index", _external=True) + "?payment=success",
            cancel_url=url_for("index", _external=True) + "?payment=cancel",
            metadata={"user_id": current_user.id, "credits_to_add": quantity},
        )
        return jsonify({"sessionId": checkout_session.id})
    except Exception as e:
        logger.error(f"Stripe error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/payments/webhook", methods=["POST"])
def stripe_webhook():
    """Webhook per confermare l'acquisto e accreditare i punti"""
    payload = request.get_data()
    sig_header = request.headers.get("Stripe-Signature")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except Exception as e:
        return "Invalid payload", 400

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        user_id = session["metadata"].get("user_id")
        credits_to_add = int(session["metadata"].get("credits_to_add", 0))

        if user_id and credits_to_add > 0:
            knowledge_manager.store.update_user_credits(int(user_id), credits_to_add)
            logger.info(
                f"CREDITI ACCREDITATI: {credits_to_add} aggiunti all'utente {user_id}"
            )

    return "OK", 200


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
        stripe_public_key=STRIPE_PUBLIC_KEY,
    )


@app.route("/test")
def test_route():
    """Route di test per verificare che Flask funzioni"""
    return """
    <!DOCTYPE html>
    <html>
    <head><title>Test OK</title></head>
    <body style="background:#0f172a;color:#10b981;font-family:sans-serif;padding:50px;text-align:center;">
        <h1>Server Flask Funzionante!</h1>
        <p>Se vedi questa pagina, il server e' attivo.</p>
        <p><a href="/" style="color:#3b82f6;">Vai alla Dashboard</a></p>
        <p><a href="/legacy" style="color:#3b82f6;">Dashboard Legacy</a></p>
    </body>
    </html>
    """


@app.route("/legacy")
@login_required
def legacy_index():
    """Dashboard legacy (vecchia versione)"""
    stats = editor.get_dashboard_stats()

    return render_template(
        "index.html",
        stats=stats,
        categories=CATEGORIE_CALCIO_ITALIANO,
        regions=REGIONI_ITALIANE,
        countries=COUNTRIES,
        countries_leagues=COUNTRIES_LEAGUES,
        tiers=FOOTBALL_TIERS,
        user=current_user,
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


@app.route("/admin/assign", methods=["POST"])
@login_required
def admin_assign_plan():
    """Assegna un piano a un utente (Admin o Super Admin)"""
    if current_user.role not in ["super_admin", "admin"]:
        return jsonify({"success": False, "error": "Unauthorized"}), 403

    data = request.json
    plan_id = data.get("plan_id")
    user_id = data.get("user_id")

    if not plan_id or not user_id:
        return jsonify({"success": False, "error": "plan_id and user_id required"}), 400

    success = knowledge_manager.store.assign_plan(
        plan_id, int(user_id), int(current_user.id)
    )

    if success:
        # Registra sviluppo
        knowledge_manager.store.add_development_log(
            plan_id,
            int(current_user.id),
            "assignment",
            f"Piano assegnato all'utente ID {user_id}",
        )
        return jsonify({"success": True})

    return jsonify({"success": False, "error": "Assignment failed"}), 500


# =============================================================================
# ADMIN CONSOLE (The Pyramid Control)
# =============================================================================


@app.route("/api/admin/plans")
@login_required
def admin_list_plans():
    """Lista tutti i piani del sistema (Solo Admin)"""
    if current_user.role != "super_admin":
        return jsonify({"success": False, "error": "Accesso negato"}), 403

    status = request.args.get("status", "")
    category = request.args.get("category", "")
    query = request.args.get("query", "")
    limit = int(request.args.get("limit", 100))
    offset = int(request.args.get("offset", 0))

    plans, total = knowledge_manager.store.list_plans(
        status=status, category=category, club_name=query, limit=limit, offset=offset
    )

    return jsonify(
        {"success": True, "plans": [p.to_dict() for p in plans], "total": total}
    )


@app.route("/api/admin/users")
@login_required
def admin_list_users():
    """Lista tutti gli utenti per l'assegnazione (Solo Admin)"""
    if current_user.role != "super_admin":
        return jsonify({"success": False, "error": "Accesso negato"}), 403

    users = knowledge_manager.store.list_users()
    # Rimuoviamo password_hash per sicurezza
    for u in users:
        u.pop("password_hash", None)

    return jsonify({"success": True, "users": users})


@app.route("/api/admin/assign_plan", methods=["POST"])
@login_required
def api_admin_assign_plan():
    """Assegna un piano a un Temporary Manager (Solo Admin)"""
    if current_user.role != "super_admin":
        return jsonify({"success": False, "error": "Accesso negato"}), 403

    data = request.json
    plan_id = data.get("plan_id")
    user_id = data.get("user_id")

    if not all([plan_id, user_id]):
        return jsonify({"success": False, "error": "Dati mancanti"}), 400

    success = knowledge_manager.store.assign_plan(
        plan_id, int(user_id), int(current_user.id)
    )

    if success:
        logger.info(
            f"Plan {plan_id} assigned to user {user_id} by {current_user.email}"
        )
        return jsonify({"success": True, "message": "Piano assegnato con successo"})

    return jsonify({"success": False, "error": "Errore durante l'assegnazione"}), 500


@app.route("/admin")
@login_required
def admin_dashboard():
    """Admin Console Dashboard"""
    if current_user.role != "super_admin":
        flash("Accesso negato. Area riservata al Super Admin.", "error")
        return redirect(url_for("index"))

    return render_template("admin_panel.html", user=current_user)


@app.route("/api/admin/users", methods=["GET"])
@login_required
def api_admin_list_users():
    """API: Lista tutti gli utenti"""
    if current_user.role != "super_admin":
        return jsonify({"success": False, "error": "Unauthorized"}), 403

    users = knowledge_manager.store.list_users()
    return jsonify({"success": True, "users": users})


@app.route("/api/admin/users", methods=["POST"])
@login_required
def api_admin_create_user():
    """API: Crea nuovo Temporary Manager"""
    if current_user.role != "super_admin":
        return jsonify({"success": False, "error": "Unauthorized"}), 403

    data = request.json
    email = data.get("email")
    password = data.get("password")
    full_name = data.get("full_name")
    credits = int(data.get("credits", 0))

    if not email or not password:
        return jsonify({"success": False, "error": "Email e Password richieste"}), 400

    # Check esistenza
    existing = knowledge_manager.store.get_user_by_email(email)
    if existing:
        return jsonify({"success": False, "error": "Utente già esistente"}), 400

    # Crea
    from auth_manager import bcrypt

    pw_hash = bcrypt.generate_password_hash(password).decode("utf-8")
    user_id = knowledge_manager.store.create_user(
        email, pw_hash, full_name, role="user"
    )

    # Aggiungi crediti iniziali
    if credits > 0:
        knowledge_manager.store.update_user_credits(user_id, credits)

    return jsonify({"success": True, "user_id": user_id})


@app.route("/api/admin/generate-license", methods=["POST"])
@login_required
def api_admin_generate_license():
    """API: Genera chiave di licenza per un cliente"""
    if current_user.role != "super_admin":
        return jsonify({"success": False, "error": "Unauthorized"}), 403

    data = request.json
    hwid = data.get("hwid", "").strip()
    email = data.get("email", "").strip()

    if not hwid or not email:
        return jsonify({"success": False, "error": "HWID e email sono obbligatori"})

    # Genera la chiave usando lo stesso algoritmo del LicenseManager
    key = licenser.generate_license_key(email, hwid)
    formatted_key = "-".join([key[i:i+6] for i in range(0, len(key), 6)])

    # Durata licenza (default 365 giorni, 0 = perpetua)
    duration_days = data.get("duration_days", 365)

    # Log della generazione
    duration_label = f"{duration_days} giorni" if duration_days else "perpetua"
    logger.info(f"[LICENSE] Generated key for {email} (HWID: {hwid[:8]}..., durata: {duration_label})")

    # Salva record nel database per tracciamento admin
    license_id = knowledge_manager.store.save_license_record(
        email=email,
        hwid=hwid,
        license_key=formatted_key,
        duration_days=duration_days if duration_days else None,
        notes=data.get("notes", "")
    )

    return jsonify({
        "success": True,
        "key": formatted_key,
        "email": email,
        "hwid": hwid,
        "duration_days": duration_days,
        "license_id": license_id
    })


@app.route("/api/admin/licenses", methods=["GET"])
@login_required
def api_admin_list_licenses():
    """API: Lista tutte le licenze generate"""
    if current_user.role != "super_admin":
        return jsonify({"success": False, "error": "Unauthorized"}), 403

    status = request.args.get("status")  # 'active', 'revoked', or None for all
    licenses = knowledge_manager.store.list_licenses(status=status)
    stats = knowledge_manager.store.get_license_stats()

    return jsonify({
        "success": True,
        "licenses": licenses,
        "stats": stats
    })


@app.route("/api/admin/licenses/<int:license_id>/revoke", methods=["POST"])
@login_required
def api_admin_revoke_license(license_id):
    """API: Revoca una licenza"""
    if current_user.role != "super_admin":
        return jsonify({"success": False, "error": "Unauthorized"}), 403

    success = knowledge_manager.store.revoke_license(license_id)
    if success:
        logger.info(f"[LICENSE] Revoked license ID {license_id} by {current_user.email}")
        return jsonify({"success": True, "message": "Licenza revocata"})
    else:
        return jsonify({"success": False, "error": "Errore durante la revoca"})


@app.route("/api/admin/market-intelligence")
@login_required
def admin_market_intelligence():
    """
    Dashboard di Intelligence per il Super Admin.
    Aggrega i dati reali raccolti da tutti i club per creare benchmark proprietari 'Rooting Future'.
    """
    if current_user.role != "super_admin":
        return jsonify({"success": False, "error": "Unauthorized"}), 403

    try:
        # Recupera tutti i piani per analisi aggregata
        plans, _ = knowledge_manager.store.list_plans(limit=1000)

        stats_by_category = {}

        for p in plans:
            cat = p.category or "Sconosciuta"
            if cat not in stats_by_category:
                stats_by_category[cat] = {
                    "count": 0,
                    "avg_budget": [],
                    "avg_youth_players": [],
                    "total_credibility": 0,
                }

            stats = stats_by_category[cat]
            stats["count"] += 1
            stats["total_credibility"] += p.credibility_score

            # Estrai dati finanziari se presenti (da stime o reali)
            financials = p.plan_data.get("financial_estimates", {})
            if financials:
                budget = financials.get("fatturato", {}).get("value", 0)
                if budget:
                    stats["avg_budget"].append(budget)

        # Calcola medie finali
        for cat, data in stats_by_category.items():
            if data["avg_budget"]:
                data["real_market_avg_budget"] = sum(data["avg_budget"]) / len(
                    data["avg_budget"]
                )
            data["avg_credibility"] = data["total_credibility"] / data["count"]
            # Pulisci liste grezze per il JSON
            data.pop("avg_budget")

        return jsonify(
            {
                "success": True,
                "intelligence_report": stats_by_category,
                "timestamp": datetime.now().isoformat(),
            }
        )

    except Exception as e:
        logger.error(f"Market Intelligence error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


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
        plan, club_data, metadata.get("financial_estimates", {})
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

    # 5. Genera pacchetto report (Auto-produce results) - ROBUST & ARMOR-PLATED
    pdf_url = None
    onepager_url = None
    executive_url = None
    scientific_url = None

    export_paths = []
    safe_name = club_name.replace(" ", "_").replace("/", "_")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # 5x. DOCX Piano Strategico (Master)
    try:
        generated_docx_path = docx_exporter.create_document(
            plan_data=plan,
            club_name=club_name,
            sources=sources,
            metadata=metadata,
        )
        # Ensure it matches the template link: plan_id.docx
        target_docx_filename = f"{review.plan_id}.docx"
        target_docx_path = OUTPUT_DIR / target_docx_filename

        import shutil

        shutil.copy(generated_docx_path, target_docx_path)

        export_paths.append(target_docx_filename)
        logger.info(f"DOCX generated and mapped to: {target_docx_filename}")
    except Exception as e:
        logger.error(f"Failed to auto-generate DOCX: {e}", exc_info=True)

    # 5a. PDF Piano Strategico (Server-side WeasyPrint)
    try:
        from export_pdf_server import PdfServerExporter

        pdf_exporter = PdfServerExporter()
        pdf_path = pdf_exporter.export(
            plan_data=plan,
            club_name=club_name,
            sources=sources,
            metadata=metadata,
        )
        pdf_url = f"/download/{pdf_path.name}"
        export_paths.append(pdf_path.name)
        logger.info(f"PDF generated: {pdf_path.name}")
    except Exception as e:
        logger.error(f"Failed to auto-generate PDF: {e}", exc_info=True)

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
            sources=sources,
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

    # 5d. Scientific Report (Structured)
    try:
        if structured_plan:
            sci_path_str = plan_renderer.render_structured(structured_plan)
            sci_path = Path(sci_path_str)
            scientific_url = f"/download/{sci_path.name}"
            export_paths.append(sci_path.name)
            logger.info(f"Scientific Report generated: {sci_path.name}")
    except Exception as e:
        logger.error(
            f"Failed to auto-generate Scientific Report: {e}", exc_info=True
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


@app.route("/api/upload-docx", methods=["POST"])
@login_required
def api_upload_docx():
    """
    Endpoint per caricamento file DOCX e analisi preliminare.
    Esegue l'analisi nel ThreadPoolExecutor per gestire il carico su AWS.
    """
    if not hasattr(app, "analysis_results"):
        app.analysis_results = {}

    project_id = f"docx_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    update_project_status(project_id, "processing", 5, "Ricezione file in corso...")

    try:
        files = request.files.getlist("files[]") or request.files.getlist("files")
        club_name = request.form.get("club_name", "Club")

        # Salviamo i file in memoria
        files_to_process = []
        import io

        for f in files:
            content = io.BytesIO(f.read())
            files_to_process.append((content, f.filename))

        def run_analysis(p_id, f_to_process, c_name):
            try:
                import zipfile
                import tempfile
                from data_ingestor import DocxIngestor

                update_project_status(
                    p_id, "processing", 15, "Preparazione documenti..."
                )

                final_files = []
                for content, filename in f_to_process:
                    if filename.lower().endswith(".docx"):
                        final_files.append((content, filename))
                    elif filename.lower().endswith(".zip"):
                        update_project_status(
                            p_id, "processing", 20, "Estrazione file ZIP..."
                        )
                        with tempfile.TemporaryDirectory() as temp_dir:
                            zip_path = os.path.join(temp_dir, "upload.zip")
                            with open(zip_path, "wb") as f_zip:
                                f_zip.write(content.getvalue())

                            with zipfile.ZipFile(zip_path, "r") as zip_ref:
                                zip_ref.extractall(temp_dir)
                                for root, _, filenames in os.walk(temp_dir):
                                    for fname in filenames:
                                        if fname.lower().endswith(".docx"):
                                            f_path = os.path.join(root, fname)
                                            with open(f_path, "rb") as df:
                                                final_files.append(
                                                    (
                                                        io.BytesIO(df.read()),
                                                        os.path.relpath(
                                                            f_path, temp_dir
                                                        ),
                                                    )
                                                )

                update_project_status(
                    p_id,
                    "processing",
                    40,
                    f"Lettura di {len(final_files)} file Word...",
                )
                ing = DocxIngestor()
                ext = ing.ingest_multiple_files(final_files)

                update_project_status(
                    p_id,
                    "processing",
                    70,
                    "Identificazione Stakeholder e SWOT Board...",
                )
                stk = ing.merge_to_stakeholder_inputs(ext)

                # Prepara il payload completo
                payload = {
                    "project_id": p_id,
                    "club_name": c_name,
                    "extracted_files_data": [
                        d.__dict__ for d in ext
                    ],  # Salva i dati originali completi
                    "stakeholders_inputs": [
                        {
                            "name": s.name,
                            "role": s.role.label,
                            "swot_strengths": s.swot_strengths,
                            "swot_weaknesses": s.swot_weaknesses,
                            "additional_notes": s.additional_notes,
                        }
                        for s in stk
                    ],
                    "files_processed": [d.filename for d in ext],
                    "document_types_detected": ["SWOT"],
                }

                app.analysis_results[p_id] = payload
                update_project_status(
                    p_id,
                    "completed",
                    100,
                    "Analisi completata con successo!",
                    data=payload,
                )
                add_to_log_history("info", f"✅ Analisi {p_id} completata.")
            except Exception as e:
                logger.error(f"Background analysis error: {e}")
                update_project_status(p_id, "error", 0, f"Errore: {str(e)}")
                add_to_log_history("error", f"Errore analisi: {str(e)}")

        # Avvia l'analisi nel pool di thread (max 2 contemporanee su AWS)
        analysis_executor.submit(run_analysis, project_id, files_to_process, club_name)

        return jsonify(
            {
                "success": True,
                "message": "Analisi messa in coda ed avviata",
                "project_id": project_id,
            }
        )
    except Exception as e:
        logger.exception(f"[DOCX Upload] Error: {e}")
        update_project_status(
            project_id, "error", 0, f"Errore critico upload: {str(e)}"
        )
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/ingest-local", methods=["POST"])
def api_ingest_local():
    """
    Endpoint per caricamento diretto da cartella locale (Technical Mode).
    """
    try:
        data = request.json
        local_path = data.get("path")
        club_name = data.get("club_name", "Club")

        if not local_path or not os.path.exists(local_path):
            return jsonify(
                {"success": False, "error": "Percorso non valido o inesistente"}
            ), 400

        logger.info(f"[Local Ingest] Analisi cartella: {local_path}")

        # Inizializza ingestor
        docx_ingestor = DocxIngestor()

        # 1. Scansiona cartella locale
        extracted_data = docx_ingestor.scan_local_directory(
            local_path, club_name=club_name
        )

        # 2. Converti in StakeholderInput con validazione web mirata
        stakeholder_inputs = docx_ingestor.merge_to_stakeholder_inputs(
            extracted_data, club_name=club_name
        )

        # 3. Genera Dashboard di Allineamento
        from data_ingestor import generate_alignment_dashboard_html

        alignment_dashboard_html = generate_alignment_dashboard_html(stakeholder_inputs)

        project_id = f"local_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # Converti i dati in dict per il frontend
        stakeholders_dict = []
        for s in stakeholder_inputs:
            stakeholders_dict.append(
                {
                    "name": s.name,
                    "role": s.role.label,
                    "vision": s.vision,
                    "swot_strengths": s.swot_strengths,
                    "swot_weaknesses": s.swot_weaknesses,
                    "swot_opportunities": s.swot_opportunities,
                    "swot_threats": s.swot_threats,
                    "priorities": s.priorities,
                    "answers": s.answers,
                }
            )

        return jsonify(
            {
                "success": True,
                "stakeholders_extracted": len(stakeholders_dict),
                "alignment_dashboard": alignment_dashboard_html,
                "extracted_data": {
                    "stakeholders": stakeholders_dict,
                    "project_id": project_id,
                    "club_name": club_name,
                },
            }
        )
    except Exception as e:
        logger.exception(f"[Local Ingest] Errore: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/browse-folder", methods=["POST"])
def api_browse_folder():
    """
    Apre una finestra di dialogo nativa (Windows) per selezionare una cartella.
    """
    try:
        import tkinter as tk
        from tkinter import filedialog

        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        folder_path = filedialog.askdirectory(
            title="Seleziona la cartella dei questionari"
        )
        root.destroy()

        if folder_path:
            return jsonify({"success": True, "path": folder_path})
        return jsonify({"success": False, "error": "Selezione annullata"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/generate-from-docx", methods=["POST"])
@route_error_handler
def api_generate_from_docx():
    """
    Endpoint completo: upload DOCX + generazione piano.
    """
    # Verifica disponibilità python-docx
    if not DOCX_AVAILABLE:
        return jsonify(
            {
                "success": False,
                "error": "python-docx non installato. Eseguire: pip install python-docx",
            }
        ), 500

    # Verifica files
    if "files[]" not in request.files and "files" not in request.files:
        return jsonify({"success": False, "error": "Nessun file caricato."}), 400

    files = request.files.getlist("files[]") or request.files.getlist("files")

    valid_files = [
        f for f in files if f.filename and f.filename.lower().endswith(".docx")
    ]

    if not valid_files:
        return jsonify(
            {"success": False, "error": "Nessun file .docx valido trovato."}
        ), 400

    # Parametri
    club_name = request.form.get("club_name", "Club")
    project_id = request.form.get("project_id")
    request_mode = request.form.get("request_mode", "production")

    # Hard data
    hard_data = {}
    if request.form.get("hard_data"):
        try:
            hard_data = json.loads(request.form.get("hard_data"))
        except json.JSONDecodeError:
            pass

    logger.info(
        f"[DOCX Generate] Processing {len(valid_files)} files for {club_name}"
    )

    # Prepara file per processing
    import io

    files_to_process = []
    for f in valid_files:
        content = io.BytesIO(f.read())
        files_to_process.append((content, f.filename))

    # 1. Processa DOCX -> Payload
    payload = process_docx_files_to_payload(
        files=files_to_process,
        club_name=club_name,
        project_id=project_id,
        hard_data=hard_data,
    )
    payload["request_mode"] = request_mode

    logger.info(
        f"[DOCX Generate] Extracted {len(payload['stakeholders_inputs'])} stakeholders"
    )

    # 2. Process con Data Ingestor (Conflict Resolution)
    synthesized, generation_params = process_n8n_webhook_payload(payload)

    logger.info(
        f"[DOCX Generate] Synthesis complete. Alignment: {synthesized.stakeholder_alignment_score}"
    )

    # 3. Web Research (se production mode)
    research_data = {}
    if request_mode == "production":
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
            logger.warning(f"[DOCX Generate] Research failed: {e}")

    # 4. Genera piano
    logger.info(
        "[DOCX Generate] Activating Multi-Agent Orchestrator (Recipe #RF-2026)..."
    )

    club_data = generation_params.copy()
    club_data["synthesized_vision"] = synthesized.unified_vision
    club_data["swot_aggregated"] = {
        k: [item for item, _, _ in v[:5]]
        for k, v in synthesized.swot_aggregated.items()
    }
    club_data["priority_ranking"] = []
    for p in synthesized.priority_ranking[:5]:
        if isinstance(p, (list, tuple)) and len(p) >= 1:
            club_data["priority_ranking"].append(p[0])
        else:
            club_data["priority_ranking"].append(p)

    result = orchestrator.generate_strategic_plan(
        club_data=club_data,
        research_data=research_data.get("club", {}),
        parallel=True,
    )

    # 4b. Genera Piano Strutturato (Scientifico) v6.0
    logger.info("[DOCX Generate] Extracting Scientific Data Points...")
    try:
        structured_plan = structured_orchestrator.generate_plan(
            club_data=club_data, research_data=research_data
        )
    except Exception as e:
        logger.error(f"Structured generation failed: {e}")
        structured_plan = None

    plan = result["plan"]
    sources = result["sources"]
    metadata = result["metadata"]

    # 4c. Merge structured sections into plan_data
    if structured_plan:
        from utils.structured_converter import structured_plan_to_markdown
        structured_sections = structured_plan_to_markdown(structured_plan)
        plan.update(structured_sections)  # Sovrascrivi/aggiungi sezioni strutturate
        logger.info(f"[DOCX Generate] Merged {len(structured_sections)} structured sections into plan_data")

    # Aggiungi info DOCX al metadata
    metadata["source"] = "docx_upload"
    metadata["files_processed"] = payload["files_processed"]
    metadata["document_types"] = payload["document_types_detected"]
    metadata["stakeholder_count"] = len(payload["stakeholders_inputs"])
    metadata["stakeholder_alignment"] = synthesized.stakeholder_alignment_score
    metadata["conflicts_count"] = len(synthesized.conflicts_detected)
    metadata["project_id"] = payload.get("project_id")

    # Conteggio questionari compilati
    metadata["total_questionnaires"] = len(payload["files_processed"])
    total_fields = sum(
        len(si.get("answers", {})) for si in payload.get("stakeholders_inputs", [])
    )
    metadata["verified_data_count"] = max(
        total_fields, len(payload["files_processed"]) * 15
    )
    metadata["questionnaire_completion"] = min(0.95, 0.6 + (total_fields / 100))

    # 5. Ottieni colori club
    club_identity = get_club_identity(
        club_name=generation_params["club_name"],
        custom_primary=hard_data.get("primary_color"),
        custom_secondary=hard_data.get("secondary_color"),
    )
    metadata["primary_color"] = club_identity["primary"]
    metadata["secondary_color"] = club_identity["secondary"]
    metadata["category"] = generation_params.get("category", "")

    # 6. Crea review
    review = editor.create_review_from_plan(
        plan_data=plan,
        club_name=generation_params["club_name"],
        sources=sources,
        metadata=metadata,
    )

    # 7. Salva in knowledge store
    plan_record = PlanRecord(
        id=review.plan_id,
        club_name=generation_params["club_name"],
        category=generation_params.get("category", ""),
        region=generation_params.get("region", ""),
        created_at=datetime.now().isoformat(),
        status="draft",
        plan_data=plan,
        sources_count=len(sources),
        credibility_score=metadata.get("credibility_score", 0),
    )
    knowledge_manager.add_plan_to_knowledge(
        plan_record, owner_id=int(current_user.id)
    )

    logger.info(f"[DOCX Generate] Plan successfully locked: {review.plan_id}")

    # Structured logging (STAB-004)
    log_plan_generation_completed(
        plan_id=review.plan_id,
        club_name=generation_params["club_name"],
        duration_seconds=0,  # TODO: Add timing
        agent_count=6,
        sections_count=len(plan),
        stakeholder_count=len(payload.get("stakeholders_inputs", [])),
        source="docx_upload"
    )

    # 8. Genera report automaticamente
    pdf_url = None
    onepager_url = None
    executive_url = None
    scientific_url = None
    export_paths = []

    if request_mode == "production":  # Genera tutti i report
        safe_name = generation_params["club_name"].replace(" ", "_").replace("/", "_")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # 8a. PDF (può fallire se Playwright non è installato)
        try:
            from export_pdf_server import PdfServerExporter
            pdf_exporter = PdfServerExporter()
            pdf_path = pdf_exporter.export(
                plan_data=plan,
                club_name=generation_params["club_name"],
                sources=sources,
                metadata=metadata,
            )
            pdf_url = f"/download/{pdf_path.name}"
            export_paths.append(pdf_path.name)
            logger.info(f"PDF generato: {pdf_path.name}")
        except Exception as pdf_error:
            logger.warning(f"[DOCX Generate] PDF generation failed (non-blocking): {pdf_error}")

        # 8b. One-Pager (non richiede Playwright)
        try:
            from export_onepager import create_onepager
            from stw_analyzer import STWAnalyzer
            analyzer = STWAnalyzer()
            full_stw_data = analyzer.analyze_plan_coverage(plan)
            onepager_path = create_onepager(
                plan_data=plan,
                club_name=generation_params["club_name"],
                metadata=metadata,
                stw_progress=full_stw_data,
            )
            onepager_url = f"/download/{onepager_path.name}"
            export_paths.append(onepager_path.name)
            logger.info(f"One-Pager generato: {onepager_path.name}")
        except Exception as op_error:
            logger.warning(f"[DOCX Generate] One-Pager generation failed: {op_error}")

        # 8c. Executive Report (non richiede Playwright)
        try:
            exec_html = plan_renderer.render_executive_html(
                plan_data=plan,
                club_name=generation_params["club_name"],
                category=generation_params.get("category", "Eccellenza"),
                metadata=metadata,
            )
            exec_filename = f"{safe_name}_ExecutiveReport_{timestamp}.html"
            exec_path = OUTPUT_DIR / exec_filename
            with open(exec_path, "w", encoding="utf-8") as f:
                f.write(exec_html)
            executive_url = f"/download/{exec_filename}"
            export_paths.append(exec_filename)
            logger.info(f"Executive Report generato: {exec_filename}")
        except Exception as exec_error:
            logger.warning(f"[DOCX Generate] Executive Report generation failed: {exec_error}")

        # 8d. Scientific Report
        try:
            if structured_plan:
                sci_path_str = plan_renderer.render_structured(structured_plan)
                sci_path = Path(sci_path_str)
                scientific_url = f"/download/{sci_path.name}"
                export_paths.append(sci_path.name)
                logger.info(f"Scientific Report generato: {sci_path.name}")
        except Exception as sci_error:
            logger.warning(f"[DOCX Generate] Scientific Report generation failed: {sci_error}")

    # Salva export_paths anche se vuoto (in caso di errore)
    if export_paths:
        plan_record.export_paths = export_paths
        knowledge_manager.store.save_plan(
            plan_record, owner_id=int(current_user.id)
        )

    # Response
    return jsonify(
        {
            "success": True,
            "plan_id": review.plan_id,
            "project_id": payload.get("project_id"),
            "club_name": generation_params["club_name"],
            "docx_processing": {
                "files_processed": payload["files_processed"],
                "document_types_detected": payload["document_types_detected"],
                "stakeholders_extracted": len(payload["stakeholders_inputs"]),
            },
            "synthesis_report": {
                "stakeholders_processed": len(payload["stakeholders_inputs"]),
                "alignment_score": synthesized.stakeholder_alignment_score,
                "unified_vision_preview": synthesized.unified_vision[:500] + "...",
                "top_priorities": [
                    p[0] if isinstance(p, (list, tuple)) else p
                    for p in synthesized.priority_ranking[:3]
                ],
            },
            "conflicts_detected": [
                {
                    "area": c.area,
                    "description": c.description,
                    "severity": c.severity,
                    "resolution": c.resolution_applied,
                }
                for c in synthesized.conflicts_detected
            ],
            "sections_count": len(plan),
            "sources_count": len(sources),
            "pdf_url": pdf_url,
            "onepager_url": onepager_url,
            "executive_url": executive_url,
            "scientific_url": scientific_url,
            "edit_url": f"/success/{review.plan_id}",
            "view_url": f"/view/{review.plan_id}",
            "next_steps": {
                "export_pdf": f"/api/export/{review.plan_id}/pdf",
                "export_package": f"/api/export/{review.plan_id}/package",
                "finalize": f"/api/plan/{review.plan_id}/finalize",
            },
        }
    )


# =============================================================================
# API - EDITING
# =============================================================================


@app.route("/api/section/<plan_id>/<section_id>", methods=["GET"])
def api_get_section(plan_id: str, section_id: str):
    """Recupera sezione"""
    section = editor.get_section(plan_id, section_id)
    if section:
        return jsonify(
            {
                "success": True,
                "section": section.to_dict(),
            }
        )
    return jsonify({"success": False, "error": "Section not found"}), 404


@app.route("/api/section/<plan_id>/<section_id>", methods=["PUT"])
def api_update_section(plan_id: str, section_id: str):
    """Aggiorna contenuto sezione"""
    try:
        data = request.json
        new_content = data.get("content")
        reason = data.get("reason", "")
        editor_name = data.get("editor", "user")

        if not new_content:
            return jsonify({"success": False, "error": "content required"}), 400

        success = editor.update_section_content(
            plan_id=plan_id,
            section_id=section_id,
            new_content=new_content,
            editor=editor_name,
            reason=reason,
        )

        return jsonify({"success": success})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/section/<plan_id>/<section_id>/approve", methods=["POST"])
def api_approve_section(plan_id: str, section_id: str):
    """Approva sezione"""
    data = request.json or {}
    approver = data.get("approver", "user")

    success = editor.approve_section(plan_id, section_id, approver)
    return jsonify({"success": success})


@app.route("/api/section/<plan_id>/<section_id>/note", methods=["POST"])
def api_add_note(plan_id: str, section_id: str):
    """Aggiunge nota a sezione"""
    data = request.json
    note = data.get("note", "")
    editor_name = data.get("editor", "user")

    success = editor.add_section_note(plan_id, section_id, note, editor_name)
    return jsonify({"success": success})


# =============================================================================
# API - EXPORT
# =============================================================================


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


@app.route("/api/export/<plan_id>/pdf", methods=["GET"])
@route_error_handler
def api_export_pdf_server(plan_id: str):
    """
    Esporta piano in formato PDF via Playwright/Chromium (lato server).
    Garantisce stabilità totale e layout professionale senza crash del browser.
    """
    review = editor.reviews.get(plan_id)
    if not review:
        raise PlanNotFoundError(details={"plan_id": plan_id})

    plan_data = editor.export_plan_for_final(plan_id)
    if not plan_data:
        raise PDFExportError(
            message="No content to export",
            user_message="Nessun contenuto disponibile per l'esportazione PDF."
        )

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

    # Usa il nuovo PdfServerExporter (Playwright PRIMARY)
    from export_pdf_server import PdfServerExporter
    import time

    start_time = time.time()
    pdf_exporter = PdfServerExporter()
    pdf_path = pdf_exporter.export(
        plan_data=plan_data,
        club_name=review.club_name,
        sources=[],  # Fonti integrate nel PDF
        metadata=metadata,
    )
    duration = time.time() - start_time

    # Structured logging (STAB-004)
    log_export_event(
        export_type="pdf",
        plan_id=plan_id,
        success=True,
        duration_seconds=duration,
        file_size_kb=int(pdf_path.stat().st_size / 1024) if pdf_path.exists() else 0,
        engine="playwright"
    )

    return send_file(
        pdf_path,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=pdf_path.name,
    )


@app.route("/api/export/<plan_id>/html", methods=["GET"])
@route_error_handler
def api_export_html_only(plan_id: str):
    """
    Esporta piano in formato HTML con Bento Grid infografico e Paged.js.
    Layout responsive: A4 paginato su desktop, scrollabile su mobile.
    """
    review = editor.reviews.get(plan_id)
    if not review:
        raise PlanNotFoundError(details={"plan_id": plan_id})

    plan_data = editor.export_plan_for_final(plan_id)
    if not plan_data:
        raise ExportError(
            message="No content to export",
            user_message="Nessun contenuto disponibile per l'esportazione."
        )

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

    # Usa il nuovo PdfServerExporter per un export PDF stabile
    from export_pdf_server import PdfServerExporter

    pdf_exporter = PdfServerExporter()
    pdf_path = pdf_exporter.export(
        plan_data=plan_data,
        club_name=review.club_name,
        sources=[],
        metadata=metadata,
    )

    return send_file(
        pdf_path,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=pdf_path.name.replace(".pdf", "_Report.pdf"),
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
    review = editor.reviews.get(plan_id)
    if not review:
        raise PlanNotFoundError(details={"plan_id": plan_id})

    plan_data = editor.export_plan_for_final(plan_id)
    if not plan_data:
        raise ExportError(
            message="No content to export",
            user_message="Nessun contenuto disponibile per l'esportazione Executive Report."
        )

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
        sources=[],
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
    review = editor.reviews.get(plan_id)
    if not review:
        raise PlanNotFoundError(details={"plan_id": plan_id})

    plan_data = editor.export_plan_for_final(plan_id)
    if not plan_data:
        raise ExportError(
            message="No content to export",
            user_message="Nessun contenuto disponibile per l'esportazione One-Pager."
        )

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

    # Analisi copertura STW per infografica
    from stw_analyzer import STWAnalyzer

    analyzer = STWAnalyzer()
    stw_progress = analyzer.analyze_plan_coverage(plan_data)

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

        stw_progress = calculate_stw_progress(plan)
        from export_onepager import create_onepager

        html_path = create_onepager(plan_data, review.club_name, metadata, stw_progress)

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


# DUPLICATE REMOVED: @app.route("/api/export/<plan_id>/pdf", methods=["GET"])
# DUPLICATE REMOVED: def api_export_pdf_only(plan_id: str):
# DUPLICATE REMOVED:     """
# DUPLICATE REMOVED:     Esporta piano solo in formato PDF.
# DUPLICATE REMOVED:     Usa WeasyPrint per alta qualità.
# DUPLICATE REMOVED:     """
# DUPLICATE REMOVED:     temp_dir = None
# DUPLICATE REMOVED:     try:
# DUPLICATE REMOVED:         review = editor.reviews.get(plan_id)
# DUPLICATE REMOVED:         if not review:
# DUPLICATE REMOVED:             return jsonify({"success": False, "error": "Plan not found"}), 404
# DUPLICATE REMOVED: 
# DUPLICATE REMOVED:         plan_data = editor.export_plan_for_final(plan_id)
# DUPLICATE REMOVED:         if not plan_data:
# DUPLICATE REMOVED:             return jsonify({"success": False, "error": "No content to export"}), 400
# DUPLICATE REMOVED: 
# DUPLICATE REMOVED:         sources = []
# DUPLICATE REMOVED:         metadata = {
# DUPLICATE REMOVED:             "category": review.category,
# DUPLICATE REMOVED:             "credibility_score": sum(
# DUPLICATE REMOVED:                 s.credibility_score for s in review.sections.values()
# DUPLICATE REMOVED:             )
# DUPLICATE REMOVED:             / len(review.sections)
# DUPLICATE REMOVED:             if review.sections
# DUPLICATE REMOVED:             else 0,
# DUPLICATE REMOVED:         }
# DUPLICATE REMOVED: 
# DUPLICATE REMOVED:         html_content = _generate_printable_html(
# DUPLICATE REMOVED:             plan_data, review.club_name, sources, metadata
# DUPLICATE REMOVED:         )
# DUPLICATE REMOVED: 
# DUPLICATE REMOVED:         safe_name = review.club_name.replace(" ", "_").replace("/", "_")
# DUPLICATE REMOVED:         timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
# DUPLICATE REMOVED:         pdf_filename = f"{safe_name}_PianoStrategico_{timestamp}"
# DUPLICATE REMOVED: 
# DUPLICATE REMOVED:         temp_dir = tempfile.mkdtemp(prefix="pdf_export_")
# DUPLICATE REMOVED: 
# DUPLICATE REMOVED:         from export_pdf_server import create_pdf_from_html
# DUPLICATE REMOVED: 
# DUPLICATE REMOVED:         pdf_success = create_pdf_from_html(
# DUPLICATE REMOVED:             html_content=html_content, output_path=temp_dir, plan_name=pdf_filename
# DUPLICATE REMOVED:         )
# DUPLICATE REMOVED: 
# DUPLICATE REMOVED:         if not pdf_success:
# DUPLICATE REMOVED:             if temp_dir and os.path.exists(temp_dir):
# DUPLICATE REMOVED:                 shutil.rmtree(temp_dir)
# DUPLICATE REMOVED:             return jsonify({"success": False, "error": "Generazione PDF fallita"}), 500
# DUPLICATE REMOVED: 
# DUPLICATE REMOVED:         pdf_temp_path = os.path.join(temp_dir, f"{pdf_filename}.pdf")
# DUPLICATE REMOVED: 
# DUPLICATE REMOVED:         # Copia in output directory
# DUPLICATE REMOVED:         final_pdf_path = OUTPUT_DIR / f"{pdf_filename}.pdf"
# DUPLICATE REMOVED:         shutil.copy2(pdf_temp_path, final_pdf_path)
# DUPLICATE REMOVED: 
# DUPLICATE REMOVED:         # ===== GENERA ANCHE ONE-PAGER E EXECUTIVE REPORT =====
# DUPLICATE REMOVED:         try:
# DUPLICATE REMOVED:             # Prepara metadata comuni
# DUPLICATE REMOVED:             club_identity = get_club_identity(review.club_name)
# DUPLICATE REMOVED:             credibility = (
# DUPLICATE REMOVED:                 sum(s.credibility_score for s in review.sections.values())
# DUPLICATE REMOVED:                 / len(review.sections)
# DUPLICATE REMOVED:                 if review.sections
# DUPLICATE REMOVED:                 else 70
# DUPLICATE REMOVED:             )
# DUPLICATE REMOVED: 
# DUPLICATE REMOVED:             common_metadata = {
# DUPLICATE REMOVED:                 "category": review.category or "Eccellenza",
# DUPLICATE REMOVED:                 "primary_color": club_identity.get("primary", "#1a365d"),
# DUPLICATE REMOVED:                 "secondary_color": club_identity.get("secondary", "#c9a227"),
# DUPLICATE REMOVED:                 "credibility_score": int(credibility),
# DUPLICATE REMOVED:                 "sources_count": sum(s.sources_count for s in review.sections.values())
# DUPLICATE REMOVED:                 if review.sections
# DUPLICATE REMOVED:                 else 10,
# DUPLICATE REMOVED:             }
# DUPLICATE REMOVED: 
# DUPLICATE REMOVED:             # 1. Genera One-Pager
# DUPLICATE REMOVED:             from export_onepager import create_onepager
# DUPLICATE REMOVED: 
# DUPLICATE REMOVED:             stw_progress = calculate_stw_progress(plan)
# DUPLICATE REMOVED:             onepager_path = create_onepager(
# DUPLICATE REMOVED:                 plan_data=plan_data,
# DUPLICATE REMOVED:                 club_name=review.club_name,
# DUPLICATE REMOVED:                 metadata=common_metadata,
# DUPLICATE REMOVED:                 stw_progress=stw_progress,
# DUPLICATE REMOVED:             )
# DUPLICATE REMOVED:             logger.info(f"One-Pager generato: {onepager_path}")
# DUPLICATE REMOVED: 
# DUPLICATE REMOVED:             # 2. Genera Executive Report
# DUPLICATE REMOVED:             exec_metadata = {
# DUPLICATE REMOVED:                 "category": review.category or "Eccellenza",
# DUPLICATE REMOVED:                 "primary_color": common_metadata.get("primary_color", "#1a365d"),
# DUPLICATE REMOVED:                 "secondary_color": common_metadata.get("secondary_color", "#ffffff"),
# DUPLICATE REMOVED:                 "dimensione_rosa": getattr(review, "squad_size", 22),
# DUPLICATE REMOVED:                 "capienza_stadio": getattr(review, "stadium_capacity", 0),
# DUPLICATE REMOVED:                 "known_financials": {},
# DUPLICATE REMOVED:                 "estimated_fields": {
# DUPLICATE REMOVED:                     "fatturato": "tier3_estimated",
# DUPLICATE REMOVED:                     "monte_ingaggi": "tier2_deduced",
# DUPLICATE REMOVED:                     "valore_rosa": "tier2_deduced",
# DUPLICATE REMOVED:                 },
# DUPLICATE REMOVED:             }
# DUPLICATE REMOVED:             exec_html = plan_renderer.render_executive_html(
# DUPLICATE REMOVED:                 plan_data=plan_data,
# DUPLICATE REMOVED:                 club_name=review.club_name,
# DUPLICATE REMOVED:                 category=review.category or "Eccellenza",
# DUPLICATE REMOVED:                 metadata=exec_metadata,
# DUPLICATE REMOVED:                 sources=[],
# DUPLICATE REMOVED:             )
# DUPLICATE REMOVED:             exec_filename = f"{safe_name}_ExecutiveReport_{timestamp}.html"
# DUPLICATE REMOVED:             exec_path = OUTPUT_DIR / exec_filename
# DUPLICATE REMOVED:             with open(exec_path, "w", encoding="utf-8") as f:
# DUPLICATE REMOVED:                 f.write(exec_html)
# DUPLICATE REMOVED:             logger.info(f"Executive Report generato: {exec_path}")
# DUPLICATE REMOVED: 
# DUPLICATE REMOVED:         except Exception as e:
# DUPLICATE REMOVED:             logger.warning(
# DUPLICATE REMOVED:                 f"Generazione One-Pager/Executive fallita (non bloccante): {e}"
# DUPLICATE REMOVED:             )
# DUPLICATE REMOVED:         # ===== FINE GENERAZIONE EXTRA =====
# DUPLICATE REMOVED: 
# DUPLICATE REMOVED:         # Pulisci temp
# DUPLICATE REMOVED:         if temp_dir and os.path.exists(temp_dir):
# DUPLICATE REMOVED:             try:
# DUPLICATE REMOVED:                 shutil.rmtree(temp_dir)
# DUPLICATE REMOVED:             except:
# DUPLICATE REMOVED:                 pass
# DUPLICATE REMOVED: 
# DUPLICATE REMOVED:         return send_file(
# DUPLICATE REMOVED:             final_pdf_path,
# DUPLICATE REMOVED:             mimetype="application/pdf",
# DUPLICATE REMOVED:             as_attachment=True,
# DUPLICATE REMOVED:             download_name=f"{pdf_filename}.pdf",
# DUPLICATE REMOVED:         )
# DUPLICATE REMOVED: 
# DUPLICATE REMOVED:     except Exception as e:
# DUPLICATE REMOVED:         logger.exception(f"PDF export error: {e}")
# DUPLICATE REMOVED:         if temp_dir and os.path.exists(temp_dir):
# DUPLICATE REMOVED:             try:
# DUPLICATE REMOVED:                 shutil.rmtree(temp_dir)
# DUPLICATE REMOVED:             except:
# DUPLICATE REMOVED:                 pass
# DUPLICATE REMOVED:         return jsonify({"success": False, "error": str(e)}), 500
# DUPLICATE REMOVED: 
# DUPLICATE REMOVED: 
# DUPLICATE REMOVED: @app.route("/api/export/<plan_id>/paged", methods=["GET"])
def api_export_paged_html(plan_id: str):
    """
    Esporta piano come HTML Print-First con Paged.js.
    Documento pronto per Stampa -> PDF con layout A4 paginato.
    Branding automatico basato sul nome del club.
    """
    try:
        review = editor.reviews.get(plan_id)
        if not review:
            return jsonify({"success": False, "error": "Plan not found"}), 404

        plan_data = editor.export_plan_for_final(plan_id)
        if not plan_data:
            return jsonify({"success": False, "error": "No content to export"}), 400

        # === BRANDING AUTOMATICO ===
        # Prova a ottenere colori custom dai metadata del review
        custom_primary = getattr(review, "primary_color", None)
        custom_secondary = getattr(review, "secondary_color", None)

        # Se non ci sono colori custom, deducili dal nome del club
        club_identity = get_club_identity(
            club_name=review.club_name,
            custom_primary=custom_primary,
            custom_secondary=custom_secondary,
        )

        logger.info(
            f"Club branding: {review.club_name} -> {club_identity['primary']} (custom: {club_identity['is_custom']})"
        )

        sources = []
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
            sources=sources,
            metadata=metadata,
        )

        return send_file(
            filepath,
            mimetype="text/html",
            as_attachment=True,
            download_name=filepath.name,
        )

    except Exception as e:
        logger.exception(f"Paged HTML export error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


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


@app.route("/api/bulk-approve", methods=["POST"])
def api_bulk_approve():
    """Auto-approva sezioni ad alta credibilità"""
    data = request.json or {}
    min_credibility = data.get("min_credibility", 80.0)

    count = batch_manager.auto_approve_high_credibility(min_credibility)
    return jsonify(
        {
            "success": True,
            "approved_count": count,
        }
    )


# =============================================================================
# API - STATS
# =============================================================================


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
    logger.exception(f"Server error: {e}")
    if request.path.startswith("/api/"):
        return jsonify({"success": False, "error": str(e)}), 500
    return (
        f"""
    <html><head><title>500 - Errore</title></head>
    <body style="font-family: sans-serif; text-align: center; padding: 50px;">
        <h1>500 - Errore interno</h1>
        <p>Si e verificato un errore: {str(e)}</p>
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

_lab_access: Dict[str, str] = {"lan": "", "tunnel": "", "tunnel_status": "inactive"}
_WIN_NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0


def _get_local_ip() -> str:
    try:
        s = _socket.socket(_socket.AF_INET, _socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def _try_start_tunnel(port: int) -> None:
    """Try cloudflared then ngrok. Updates _lab_access in-place."""
    import subprocess, re, time as _t
    _lab_access["tunnel_status"] = "starting"

    # --- cloudflared ---
    try:
        proc = subprocess.Popen(
            ["cloudflared", "tunnel", "--url", f"http://localhost:{port}",
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
                print(f"\n[LAB] ✓ Tunnel pubblico attivo: {url}/lab\n")
                return
            _t.sleep(0.5)
    except FileNotFoundError:
        pass
    except Exception as e:
        app.logger.debug(f"cloudflared error: {e}")

    # --- ngrok ---
    try:
        import json as _j, urllib.request as _ur
        subprocess.Popen(
            ["ngrok", "http", str(port)],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            creationflags=_WIN_NO_WINDOW,
        )
        _t.sleep(3)
        data = _j.loads(_ur.urlopen("http://localhost:4040/api/tunnels", timeout=3).read())
        for t in data.get("tunnels", []):
            if t.get("proto") == "https":
                url = t["public_url"]
                _lab_access["tunnel"] = url
                _lab_access["tunnel_status"] = "active"
                print(f"\n[LAB] ✓ Tunnel ngrok attivo: {url}/lab\n")
                return
    except FileNotFoundError:
        pass
    except Exception as e:
        app.logger.debug(f"ngrok error: {e}")

    _lab_access["tunnel_status"] = "unavailable"
    print("[LAB] Nessun tunnel (installa cloudflared per accesso fuori rete).")


@app.route("/api/lab/urls")
def lab_urls():
    return jsonify(_lab_access)


@app.route("/api/lab/qr")
def lab_qr():
    """Return a QR code SVG for the given ?url= parameter."""
    url = request.args.get("url", "").strip()
    if not url:
        return "", 400
    try:
        import qrcode, qrcode.image.svg, io
        img = qrcode.make(url, image_factory=qrcode.image.svg.SvgImage, box_size=8)
        buf = io.BytesIO()
        img.save(buf)
        return Response(buf.getvalue(), mimetype="image/svg+xml",
                        headers={"Cache-Control": "max-age=3600"})
    except ImportError:
        # Minimal fallback SVG with text only
        safe = url.replace("&", "&amp;").replace("<", "&lt;")
        svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="200" height="60">'
               f'<rect width="200" height="60" fill="#f7fafc" rx="8"/>'
               f'<text x="10" y="36" font-size="11" font-family="monospace" fill="#1a365d">{safe}</text>'
               f'</svg>')
        return Response(svg, mimetype="image/svg+xml")


# ============================================================
# LAB — Model comparison UI
# ============================================================

_lab_runs: Dict[str, dict] = {}        # run_id -> run data
_lab_club_data: Dict = {}               # in-memory Riccione cache
_LAB_DATA_FILE = Path(__file__).parent / "lab_data" / "riccione.json"


@app.route("/lab")
def lab():
    return render_template("lab.html")


@app.route("/api/lab/models", methods=["GET"])
def lab_models():
    """Discover: OpenRouter free models, Ollama local models, Gemini available."""
    import requests as _req
    result: Dict[str, list] = {"openrouter": [], "ollama": [], "gemini": []}

    # OpenRouter free models (no auth needed for public list)
    try:
        r = _req.get("https://openrouter.ai/api/v1/models", timeout=8)
        if r.ok:
            for m in r.json().get("data", []):
                p = m.get("pricing", {})
                if str(p.get("prompt", "1")) == "0" and str(p.get("completion", "1")) == "0":
                    result["openrouter"].append({
                        "id": m["id"],
                        "name": m.get("name", m["id"]),
                        "context": m.get("context_length", 0),
                    })
    except Exception as e:
        app.logger.warning(f"lab_models OpenRouter: {e}")

    # Ollama local models
    ollama_base = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
    if ollama_base.endswith("/v1"):
        ollama_base = ollama_base[:-3]
    try:
        r = _req.get(f"{ollama_base}/api/tags", timeout=4)
        if r.ok:
            result["ollama"] = [m["name"] for m in r.json().get("models", [])]
    except Exception:
        pass

    # Gemini — list available via API
    gemini_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY", "")
    if gemini_key:
        try:
            import google.generativeai as _genai
            from ai_providers.gemini_provider import _PREFERRED_MODELS
            _genai.configure(api_key=gemini_key)
            avail = {m.name for m in _genai.list_models()}
            result["gemini"] = [m for m in _PREFERRED_MODELS if f"models/{m}" in avail]
        except Exception:
            from ai_providers.gemini_provider import detect_best_gemini_model
            result["gemini"] = [detect_best_gemini_model(gemini_key)]

    return jsonify(result)


@app.route("/api/lab/club-data", methods=["GET"])
def lab_club_data_info():
    """Status of cached club data."""
    global _lab_club_data
    if not _lab_club_data and _LAB_DATA_FILE.exists():
        try:
            with open(_LAB_DATA_FILE, encoding="utf-8") as f:
                _lab_club_data = json.load(f).get("club_data", {})
        except Exception:
            pass
    if _lab_club_data:
        return jsonify({
            "loaded": True,
            "club_name": _lab_club_data.get("club_name", "N/A"),
            "has_interviews": bool(_lab_club_data.get("interviste_board")),
        })
    return jsonify({"loaded": False})


@app.route("/api/lab/save-interviews", methods=["POST"])
def lab_save_interviews():
    """Load .docx interviews from a folder path and persist to lab_data/riccione.json."""
    global _lab_club_data
    body = request.get_json(force=True)
    path = body.get("path", "").strip()
    if not path:
        return jsonify({"error": "path mancante"}), 400
    try:
        import importlib.util
        _ab_spec = importlib.util.spec_from_file_location(
            "ab_test", Path(__file__).parent / "ab_test.py"
        )
        _ab = importlib.util.module_from_spec(_ab_spec)
        _ab_spec.loader.exec_module(_ab)

        interviews = _ab.load_interviews(path)
        if not interviews:
            return jsonify({"error": f"Nessun .docx trovato in: {path}"}), 404

        club_data = _ab.build_club_data(interviews)
        _LAB_DATA_FILE.parent.mkdir(exist_ok=True)
        cache = {
            "saved_at": datetime.now().isoformat(),
            "path": path,
            "file_count": len(interviews),
            "total_chars": sum(len(v) for v in interviews.values()),
            "club_data": club_data,
        }
        with open(_LAB_DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
        _lab_club_data = club_data
        return jsonify({
            "ok": True,
            "file_count": cache["file_count"],
            "total_chars": cache["total_chars"],
            "club_name": club_data.get("club_name", "N/A"),
        })
    except Exception as e:
        app.logger.error(f"lab_save_interviews: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/lab/run", methods=["POST"])
def lab_run():
    """Generate a plan with one model; stream per-agent progress via SSE."""
    global _lab_club_data

    body = request.get_json(force=True)
    provider_type = body.get("provider", "gemini")   # gemini | openrouter | ollama
    model_id      = body.get("model", "")
    api_key_ov    = body.get("api_key", "")
    run_label     = body.get("label") or f"{provider_type} / {model_id or 'auto'}"

    # Ensure club data
    if not _lab_club_data and _LAB_DATA_FILE.exists():
        try:
            with open(_LAB_DATA_FILE, encoding="utf-8") as f:
                _lab_club_data = json.load(f).get("club_data", {})
        except Exception:
            pass
    if not _lab_club_data:
        return jsonify({"error": "Dati club non caricati. Usa 'Carica Interviste'."}), 400

    import uuid
    run_id = str(uuid.uuid4())[:8]
    club_data_snapshot = dict(_lab_club_data)

    def _stream():
        q: queue.Queue = queue.Queue()

        def _worker():
            orig_env: Dict[str, str] = {}

            def _setenv(k, v):
                orig_env[k] = os.environ.get(k, "")
                if v:
                    os.environ[k] = v
                elif k in os.environ:
                    del os.environ[k]

            try:
                if provider_type == "openrouter":
                    _setenv("OLLAMA_BASE_URL", "https://openrouter.ai/api/v1")
                    _setenv("OLLAMA_MODEL", model_id)
                    _setenv("OLLAMA_API_KEY",
                            api_key_ov or os.environ.get("OPENROUTER_API_KEY", ""))
                elif provider_type == "ollama":
                    _setenv("OLLAMA_BASE_URL",
                            os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434"))
                    _setenv("OLLAMA_MODEL", model_id)
                elif provider_type == "gemini":
                    _setenv("OLLAMA_BASE_URL", "")   # force Gemini path
                    if api_key_ov:
                        _setenv("GEMINI_API_KEY", api_key_ov)

                q.put({"event": "start", "run_id": run_id, "label": run_label})

                # Fresh orchestrator (reads env vars at init)
                from agents import MultiAgentOrchestrator as _Orch

                orch = _Orch()
                agent_metrics: List[dict] = []

                # Disable AI cache and patch generate() for timing
                class _NoCache:
                    def get(self, _): return None
                    def set(self, _k, _v): pass

                for role, ag in orch.agents.items():
                    ag.cache = _NoCache()
                    _rname = role.value if hasattr(role, "value") else str(role)
                    _orig  = ag.generate

                    def _patch(rn, orig):
                        def _w(*a, **kw):
                            q.put({"event": "agent_start", "agent": rn})
                            t0 = time.time()
                            res = orig(*a, **kw)
                            dt = round(time.time() - t0, 1)
                            ch = len((res or {}).get("content", ""))
                            agent_metrics.append({"agent": rn, "seconds": dt, "chars": ch})
                            q.put({"event": "agent_done", "agent": rn,
                                   "seconds": dt, "chars": ch})
                            return res
                        return _w

                    ag.generate = _patch(_rname, _orig)

                t_start = time.time()
                plan_result = orch.generate_strategic_plan(club_data=club_data_snapshot)
                total = round(time.time() - t_start, 1)

                _lab_runs[run_id] = {
                    "run_id": run_id, "label": run_label,
                    "provider": provider_type, "model": model_id,
                    "agents": agent_metrics, "plan": plan_result.get("plan", {}),
                    "total_seconds": total,
                    "started_at": datetime.now().isoformat(),
                }
                q.put({"event": "complete", "run_id": run_id,
                       "total_seconds": total, "agents": agent_metrics,
                       "plan_keys": list(plan_result.get("plan", {}).keys())})

            except Exception as exc:
                app.logger.error(f"lab_run worker: {exc}", exc_info=True)
                q.put({"event": "error", "message": str(exc)})
            finally:
                for k, v in orig_env.items():
                    if v:
                        os.environ[k] = v
                    elif k in os.environ:
                        del os.environ[k]
                q.put(None)

        threading.Thread(target=_worker, daemon=True).start()

        while True:
            item = q.get()
            if item is None:
                break
            yield f"data: {json.dumps(item, ensure_ascii=False)}\n\n"

    return Response(
        _stream(),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.route("/api/lab/runs", methods=["GET"])
def lab_runs_list():
    runs = [
        {k: v for k, v in r.items() if k != "plan"}
        for r in sorted(_lab_runs.values(), key=lambda x: x["started_at"], reverse=True)
    ]
    return jsonify(runs)


@app.route("/api/lab/runs/<run_id>", methods=["GET"])
def lab_run_detail(run_id):
    run = _lab_runs.get(run_id)
    if not run:
        return jsonify({"error": "Run non trovata"}), 404
    return jsonify(run)


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

    # Detect local IP and populate access info
    _local_ip = _get_local_ip()
    _lab_access["lan"] = f"http://{_local_ip}:{PORT}"

    print("[OK] SSE Log Streaming attivo (Global)")
    print(f"""
    ===============================================================
    |     Rooting Future Strategy Engine v6.0                     |
    |-------------------------------------------------------------|
    |  PC locale :  http://127.0.0.1:{PORT}                        |
    |  Rete LAN  :  http://{_local_ip}:{PORT}               |
    |  Lab mobile:  http://{_local_ip}:{PORT}/lab            |
    ===============================================================
    """)
    print("[*] Premi Ctrl+C per terminare")
    print("[*] Avvio tunnel pubblico in background (cloudflared/ngrok)…\n")

    # Start public tunnel in background (non-blocking)
    threading.Thread(target=_try_start_tunnel, args=(PORT,), daemon=True).start()

    # AUTO-OPEN BROWSER
    import webbrowser
    from threading import Timer

    def open_browser():
        webbrowser.open_new(f"http://127.0.0.1:{PORT}/lab")

    Timer(1.5, open_browser).start()

    # Bind 0.0.0.0 so mobile devices on the same network can connect
    app.run(host="0.0.0.0", port=PORT, debug=False, threaded=True, use_reloader=False)
