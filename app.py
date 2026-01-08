"""
Rooting Future Strategy Engine v5.4
Flask Application Principale

API e interfaccia web per generazione piani strategici.
"""

import os
import json
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
    send_file,
    redirect,
    url_for,
    flash,
    session,
    Response,
)
import queue
import threading
import time

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
from agents import MultiAgentOrchestrator
from web_research import WebResearcher, ResearchAggregator
from data_sourcing import SourcedContentGenerator
from knowledge_store import KnowledgeManager, PlanRecord
from export_docx import ProfessionalDocxExporter
from export_html import ChunkedHTMLExporter, HTMLSection
# Importa il nuovo modulo per il PDF
from export_pdf import create_pdf_from_html
# Nuovo export Print-First con Paged.js
from export_paged import create_paged_html
from export_pdf_server import PdfServerExporter
from club_identity import get_club_colors, get_club_identity
from post_production_editor import (
    PostProductionEditor,
    BatchReviewManager,
    PlanStatus,
    SectionStatus,
)

# Nuovo sistema strutturato v5.4
from structured_agent import StructuredOrchestrator, SECTION_DATA_TEMPLATES
from structured_renderer import StructuredHTMLRenderer
from data_models import StructuredPlan, DataType, ConfidenceLevel
# Nuovo sistema RAG
from file_search_manager import FileSearchManager
# Dashboard Strategica
from dashboard_module import generate_strategic_dashboard
# Metodologia e Fonti
from methodology_section import generate_methodology_section_html, get_default_sources_for_report
# Data Estimator e Charts
from data_estimator import estimate_missing_financials, DataTier
from chart_generator import generate_financial_charts_for_report
# Executive Report A4
from executive_report import generate_executive_report_html
# n8n Integration
from n8n_integration import register_n8n_routes, get_questionnaire_schema
# Data Ingestor for Multi-Stakeholder Conflict Resolution
from data_ingestor import (
    DataIngestor,
    process_n8n_webhook_payload,
    generate_conflict_report_html,
    process_docx_files_to_payload,
    DocxIngestor,
    DOCX_AVAILABLE
)


# =============================================================================
# SETUP
# =============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# =============================================================================
# SSE LOG STREAMING SYSTEM
# =============================================================================

# Buffer per gli ultimi N log
log_history: List[Dict] = []
LOG_HISTORY_SIZE = 50
log_history_lock = threading.Lock()

# Placeholder per SSE handler (inizializzato in __main__ per evitare deadlock)
log_stream_handler = None


class LogStreamHandler(logging.Handler):
    """
    Custom logging handler che invia log a tutti i client SSE connessi.
    Thread-safe con queue per ogni client.
    """

    def __init__(self):
        super().__init__()
        self.clients: Dict[str, queue.Queue] = {}
        self.lock = threading.Lock()
        self.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

    def emit(self, record):
        """Invia log a tutti i client connessi."""
        try:
            msg = self.format(record)
            log_entry = {
                'timestamp': datetime.now().isoformat(),
                'level': record.levelname,
                'message': msg,
                'logger': record.name
            }

            # Salva nella history
            add_to_log_history(log_entry)

            with self.lock:
                dead_clients = []
                for client_id, client_queue in self.clients.items():
                    try:
                        client_queue.put_nowait(log_entry)
                    except queue.Full:
                        dead_clients.append(client_id)

                for client_id in dead_clients:
                    del self.clients[client_id]

        except Exception:
            self.handleError(record)

    def register_client(self, client_id: str) -> queue.Queue:
        """Registra un nuovo client SSE."""
        with self.lock:
            client_queue = queue.Queue(maxsize=100)
            self.clients[client_id] = client_queue
            return client_queue

    def unregister_client(self, client_id: str):
        """Rimuovi client SSE."""
        with self.lock:
            if client_id in self.clients:
                del self.clients[client_id]


def add_to_log_history(entry: Dict):
    """Aggiunge entry alla history dei log."""
    with log_history_lock:
        log_history.append(entry)
        if len(log_history) > LOG_HISTORY_SIZE:
            log_history.pop(0)


def broadcast_log(level: str, message: str, source: str = "system"):
    """
    Funzione helper per inviare log custom alla dashboard.
    """
    if level.upper() == "INFO":
        logger.info(f"[{source}] {message}")
    elif level.upper() == "WARNING":
        logger.warning(f"[{source}] {message}")
    elif level.upper() == "ERROR":
        logger.error(f"[{source}] {message}")
    else:
        logger.info(f"[{source}] {message}")


# =============================================================================
# FLASK APP SETUP
# =============================================================================

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'rooting-future-dev-key-change-in-prod')

# Registra routes n8n
register_n8n_routes(app)

# Aggiungi 'now' al contesto Jinja2
@app.context_processor
def inject_now():
    return {'now': datetime.now}


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
knowledge_manager = KnowledgeManager()

# Multi-Agent Orchestrator
orchestrator = MultiAgentOrchestrator(
    knowledge_store=knowledge_manager.store,
    file_search_store_name=file_search_store_name
)

# Componenti base
researcher = WebResearcher()
research_aggregator = ResearchAggregator()
docx_exporter = ProfessionalDocxExporter()
html_exporter = ChunkedHTMLExporter()
editor = PostProductionEditor()
batch_manager = BatchReviewManager()

# Sistema strutturato v5.4
structured_orchestrator = StructuredOrchestrator(file_search_store_name=file_search_store_name)
structured_renderer = StructuredHTMLRenderer()


# =============================================================================
# ROUTES - PAGINE
# =============================================================================

@app.route('/')
def index():
    """Homepage con dashboard - versione stabile"""
    # Stats fissi per evitare blocchi
    stats = {
        'total_plans': 0,
        'by_status': {'draft': 0},
        'sections_needing_review': 0,
        'average_credibility': 0,
        'recent_plans': []
    }

    return render_template(
        'dashboard_simple.html',
        stats=stats,
        categories=CATEGORIE_CALCIO_ITALIANO,
        regions=REGIONI_ITALIANE,
        countries=COUNTRIES,
        countries_leagues=COUNTRIES_LEAGUES,
        tiers=FOOTBALL_TIERS,
        docx_available=DOCX_AVAILABLE,
    )


@app.route('/test')
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


@app.route('/legacy')
def legacy_index():
    """Dashboard legacy (vecchia versione)"""
    stats = editor.get_dashboard_stats()

    return render_template(
        'index.html',
        stats=stats,
        categories=CATEGORIE_CALCIO_ITALIANO,
        regions=REGIONI_ITALIANE,
        countries=COUNTRIES,
        countries_leagues=COUNTRIES_LEAGUES,
        tiers=FOOTBALL_TIERS,
    )


# =============================================================================
# SSE - SERVER SENT EVENTS (Log Streaming)
# =============================================================================

@app.route('/api/stream/logs')
def stream_logs():
    """
    Endpoint SSE per streaming dei log in tempo reale.
    I client si connettono qui per ricevere log live.
    """
    import uuid

    def generate():
        client_id = str(uuid.uuid4())

        # Se SSE handler non disponibile, usa solo polling
        if log_stream_handler is None:
            with log_history_lock:
                for entry in log_history[-20:]:
                    yield f"data: {json.dumps(entry)}\n\n"
            yield f"data: {json.dumps({'level': 'WARNING', 'message': 'SSE non disponibile, usa polling', 'timestamp': datetime.now().isoformat()})}\n\n"
            return

        client_queue = log_stream_handler.register_client(client_id)

        try:
            # Invia prima la history
            with log_history_lock:
                for entry in log_history[-20:]:
                    yield f"data: {json.dumps(entry)}\n\n"

            # Poi stream continuo
            while True:
                try:
                    entry = client_queue.get(timeout=30)
                    yield f"data: {json.dumps(entry)}\n\n"
                except queue.Empty:
                    yield f": keepalive\n\n"

        except GeneratorExit:
            pass
        finally:
            if log_stream_handler:
                log_stream_handler.unregister_client(client_id)

    return Response(
        generate(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'X-Accel-Buffering': 'no'
        }
    )


@app.route('/api/logs/history')
def get_log_history():
    """Endpoint per ottenere la history dei log (polling fallback)."""
    with log_history_lock:
        return jsonify({
            'success': True,
            'logs': list(log_history),
            'count': len(log_history)
        })


@app.route('/api/system/status')
def system_status():
    """Stato del sistema per la dashboard."""
    stats = editor.get_dashboard_stats()

    connected = 0
    if log_stream_handler:
        connected = len(log_stream_handler.clients)

    return jsonify({
        'success': True,
        'status': 'online',
        'timestamp': datetime.now().isoformat(),
        'docx_available': DOCX_AVAILABLE,
        'stats': {
            'total_plans': stats.get('total_plans', 0),
            'draft_plans': stats.get('by_status', {}).get('draft', 0),
            'ready_plans': stats.get('by_status', {}).get('ready', 0),
            'sections_to_review': stats.get('sections_needing_review', 0),
            'avg_credibility': stats.get('average_credibility', 0)
        },
        'connected_clients': connected
    })


@app.route('/plans')
def plans_list():
    """Lista piani strategici"""
    status_filter = request.args.get('status', '')
    category_filter = request.args.get('category', '')
    page = request.args.get('page', 1, type=int)
    per_page = 20

    plans, total = knowledge_manager.store.list_plans(
        status=status_filter,
        category=category_filter,
        limit=per_page,
        offset=(page - 1) * per_page
    )

    return render_template(
        'plans_list.html',
        plans=plans,
        total=total,
        page=page,
        per_page=per_page,
        status_filter=status_filter,
        category_filter=category_filter,
        categories=CATEGORIE_CALCIO_ITALIANO,
    )


@app.route('/plan/<plan_id>')
def plan_detail(plan_id: str):
    """Dettaglio piano con editor"""
    review = editor.reviews.get(plan_id)
    if not review:
        # Prova a caricare dal database
        plan_record = knowledge_manager.store.get_plan(plan_id)
        if not plan_record:
            flash('Piano non trovato', 'error')
            return redirect(url_for('plans_list'))

        # Crea review se non esiste
        review = editor.create_review_from_plan(
            plan_data=plan_record.plan_data,
            club_name=plan_record.club_name,
            metadata={'category': plan_record.category}
        )

    sections_needing_review = editor.get_sections_needing_review(plan_id)

    return render_template(
        'plan_detail.html',
        review=review,
        sections_needing_review=sections_needing_review,
    )


@app.route('/new')
def new_plan():
    """Form nuovo piano"""
    return render_template(
        'new_plan.html',
        categories=CATEGORIE_CALCIO_ITALIANO,
        regions=REGIONI_ITALIANE,
        countries=COUNTRIES,
        countries_leagues=COUNTRIES_LEAGUES,
        tiers=FOOTBALL_TIERS,
    )


@app.route('/review-queue')
def review_queue():
    """Coda di review prioritizzata"""
    queue = batch_manager.get_priority_queue()
    workload = batch_manager.get_workload_summary()

    return render_template(
        'review_queue.html',
        queue=queue[:50],  # Top 50
        workload=workload,
    )


# =============================================================================
# API - GENERAZIONE
# =============================================================================

@app.route('/api/generate', methods=['POST'])
def api_generate_plan():
    """
    Genera piano strategico completo.

    Request body:
    {
        "club_name": "AC Riccione",
        "city": "Riccione",
        "region": "Emilia-Romagna",
        "category": "Promozione",
        "foundation_year": 1926,
        "competitors": ["Bellaria", "Cattolica"],
        "enable_research": true,
        "additional_data": {...}
    }
    """
    try:
        data = request.json
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400

        club_name = data.get('club_name', 'Club')
        if not club_name:
            return jsonify({'success': False, 'error': 'club_name required'}), 400

        logger.info(f"Generating plan for: {club_name}")

        # 1. Web Research (opzionale)
        research_data = {}
        if data.get('enable_research', True):
            logger.info("Starting web research...")
            research_data = research_aggregator.comprehensive_club_research(
                club_name=club_name,
                city=data.get('city', ''),
                category=data.get('category', ''),
                competitors=data.get('competitors', []),
                region=data.get('region', '')
            )
            # Esporta research per audit
            research_aggregator.export_research_report(research_data)

        # 2. Genera piano con multi-agent
        logger.info("Generating strategic plan...")
        result = orchestrator.generate_strategic_plan(
            club_data=data,
            research_data=research_data.get('club', {}),
            parallel=True
        )

        plan = result['plan']
        sources = result['sources']
        metadata = result['metadata']

        # Aggiungi colori e categoria dal form al metadata
        metadata['primary_color'] = data.get('primary_color')
        metadata['secondary_color'] = data.get('secondary_color')
        metadata['category'] = data.get('category', '')

        # 3. Crea review per editing
        review = editor.create_review_from_plan(
            plan_data=plan,
            club_name=club_name,
            sources=sources,
            metadata=metadata
        )

        # 4. Salva in knowledge store
        plan_record = PlanRecord(
            id=review.plan_id,
            club_name=club_name,
            category=data.get('category', ''),
            region=data.get('region', ''),
            created_at=datetime.now().isoformat(),
            status='draft',
            plan_data=plan,
            sources_count=len(sources),
            credibility_score=metadata.get('credibility_score', 0),
        )
        knowledge_manager.add_plan_to_knowledge(plan_record)

        logger.info(f"Plan generated successfully: {review.plan_id}")

        return jsonify({
            'success': True,
            'plan_id': review.plan_id,
            'club_name': club_name,
            'sections_count': len(plan),
            'sources_count': len(sources),
            'sections_needing_review': len(editor.get_sections_needing_review(review.plan_id)),
        })

    except Exception as e:
        logger.exception(f"Generation error: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
        }), 500


@app.route('/api/regenerate-section', methods=['POST'])
def api_regenerate_section():
    """Rigenera singola sezione"""
    try:
        data = request.json
        plan_id = data.get('plan_id')
        section_id = data.get('section_id')
        additional_context = data.get('context', '')

        if not plan_id or not section_id:
            return jsonify({'success': False, 'error': 'plan_id and section_id required'}), 400

        # Recupera dati club originali
        plan_record = knowledge_manager.store.get_plan(plan_id)
        if not plan_record:
            return jsonify({'success': False, 'error': 'Plan not found'}), 404

        club_data = {
            'club_name': plan_record.club_name,
            'category': plan_record.category,
            'region': plan_record.region,
        }

        new_content = editor.regenerate_section(
            plan_id=plan_id,
            section_id=section_id,
            club_data=club_data,
            additional_context=additional_context
        )

        if new_content:
            return jsonify({
                'success': True,
                'content': new_content,
            })
        else:
            return jsonify({'success': False, 'error': 'Regeneration failed'}), 500

    except Exception as e:
        logger.exception(f"Regeneration error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/generate-from-webhook', methods=['POST'])
def api_generate_from_webhook():
    """
    Endpoint per n8n: genera piano da input multi-stakeholder.

    Riceve payload con visioni di molteplici stakeholder,
    applica conflict resolution e genera piano unificato.

    Request body (da n8n):
    {
        "project_id": "AC_Riccione_2025",
        "club_name": "AC Riccione 1926",
        "request_mode": "production",  // or "draft"
        "stakeholders_inputs": [
            {
                "name": "Giorgio Veschi",
                "role": "Socio",
                "vision": "Serie D, orgoglio locale...",
                "swot_strengths": ["Passione", "Tifosi"],
                "swot_weaknesses": ["Pochi soldi"],
                "swot_opportunities": ["Turismo"],
                "swot_threats": ["Concorrenza"],
                "priorities": ["Settore giovanile", "Marketing"]
            },
            // ... altri stakeholder
        ],
        "hard_data": {
            "budget_available": "500000",
            "current_league": "Promozione",
            "youth_members": 400,
            "city": "Riccione",
            "region": "Emilia-Romagna"
        }
    }

    Response:
    {
        "success": true,
        "plan_id": "xxx",
        "synthesis_report": {...},
        "conflicts_detected": [...],
        "stakeholder_alignment_score": 85
    }
    """
    try:
        payload = request.json
        if not payload:
            return jsonify({'success': False, 'error': 'No payload provided'}), 400

        # Validazione base
        if not payload.get('club_name'):
            return jsonify({'success': False, 'error': 'club_name is required'}), 400

        if not payload.get('stakeholders_inputs'):
            return jsonify({'success': False, 'error': 'stakeholders_inputs is required (at least 1)'}), 400

        logger.info(f"[Webhook] Processing multi-stakeholder request for: {payload.get('club_name')}")
        logger.info(f"[Webhook] Stakeholders count: {len(payload.get('stakeholders_inputs', []))}")

        # 1. Process con Data Ingestor (Conflict Resolution)
        synthesized, generation_params = process_n8n_webhook_payload(payload)

        logger.info(f"[Webhook] Synthesis complete. Alignment score: {synthesized.stakeholder_alignment_score}")
        logger.info(f"[Webhook] Conflicts detected: {len(synthesized.conflicts_detected)}")

        # 2. Web Research (se production mode)
        research_data = {}
        if generation_params.get('enable_research', True):
            logger.info("[Webhook] Starting web research...")
            try:
                research_data = research_aggregator.comprehensive_club_research(
                    club_name=generation_params['club_name'],
                    city=generation_params.get('city', ''),
                    category=generation_params.get('category', ''),
                    competitors=[],
                    region=generation_params.get('region', '')
                )
                research_aggregator.export_research_report(research_data)
            except Exception as e:
                logger.warning(f"[Webhook] Research failed (continuing): {e}")

        # 3. Genera piano con multi-agent
        logger.info("[Webhook] Generating strategic plan...")

        # Arricchisci club_data con dati sintetizzati
        club_data = generation_params.copy()
        club_data['synthesized_vision'] = synthesized.unified_vision
        club_data['swot_aggregated'] = {
            k: [item for item, _, _ in v[:5]]
            for k, v in synthesized.swot_aggregated.items()
        }
        club_data['priority_ranking'] = [p for p, _ in synthesized.priority_ranking[:5]]

        result = orchestrator.generate_strategic_plan(
            club_data=club_data,
            research_data=research_data.get('club', {}),
            parallel=True
        )

        plan = result['plan']
        sources = result['sources']
        metadata = result['metadata']

        # Aggiungi info stakeholder al metadata
        metadata['stakeholder_count'] = len(payload.get('stakeholders_inputs', []))
        metadata['stakeholder_alignment'] = synthesized.stakeholder_alignment_score
        metadata['conflicts_count'] = len(synthesized.conflicts_detected)
        metadata['project_id'] = payload.get('project_id')
        metadata['source'] = 'n8n_webhook'

        # 4. Ottieni colori club
        hard_data = payload.get('hard_data', {})
        club_identity = get_club_identity(
            club_name=generation_params['club_name'],
            custom_primary=hard_data.get('primary_color'),
            custom_secondary=hard_data.get('secondary_color')
        )
        metadata['primary_color'] = club_identity['primary']
        metadata['secondary_color'] = club_identity['secondary']
        metadata['category'] = generation_params.get('category', '')

        # 5. Crea review per editing
        review = editor.create_review_from_plan(
            plan_data=plan,
            club_name=generation_params['club_name'],
            sources=sources,
            metadata=metadata
        )

        # 6. Salva in knowledge store
        plan_record = PlanRecord(
            id=review.plan_id,
            club_name=generation_params['club_name'],
            category=generation_params.get('category', ''),
            region=generation_params.get('region', ''),
            created_at=datetime.now().isoformat(),
            status='draft',
            plan_data=plan,
            sources_count=len(sources),
            credibility_score=metadata.get('credibility_score', 0),
        )
        knowledge_manager.add_plan_to_knowledge(plan_record)

        logger.info(f"[Webhook] Plan generated successfully: {review.plan_id}")

        # 7. Genera PDF automaticamente (se production mode)
        pdf_url = None
        if payload.get('request_mode') == 'production':
            try:
                pdf_exporter = PdfServerExporter()
                pdf_path = pdf_exporter.export(
                    plan_data=plan,
                    club_name=generation_params['club_name'],
                    sources=sources,
                    metadata=metadata
                )
                pdf_url = f"/download/{pdf_path.name}"
                logger.info(f"[Webhook] PDF generated: {pdf_path.name}")
            except Exception as pdf_error:
                logger.warning(f"[Webhook] PDF generation failed: {pdf_error}")

        # 8. Prepara response
        return jsonify({
            'success': True,
            'plan_id': review.plan_id,
            'project_id': payload.get('project_id'),
            'club_name': generation_params['club_name'],

            # Synthesis report
            'synthesis_report': {
                'stakeholders_processed': len(payload.get('stakeholders_inputs', [])),
                'alignment_score': synthesized.stakeholder_alignment_score,
                'unified_vision_preview': synthesized.unified_vision[:500] + '...' if len(synthesized.unified_vision) > 500 else synthesized.unified_vision,
                'top_priorities': [p for p, _ in synthesized.priority_ranking[:3]],
                'swot_summary': {
                    'strengths': len(synthesized.swot_aggregated.get('strengths', [])),
                    'weaknesses': len(synthesized.swot_aggregated.get('weaknesses', [])),
                    'opportunities': len(synthesized.swot_aggregated.get('opportunities', [])),
                    'threats': len(synthesized.swot_aggregated.get('threats', []))
                }
            },

            # Conflicts
            'conflicts_detected': [
                {
                    'area': c.area,
                    'description': c.description,
                    'severity': c.severity,
                    'stakeholders': c.stakeholders_involved,
                    'resolution': c.resolution_applied
                }
                for c in synthesized.conflicts_detected
            ],

            # Plan info
            'sections_count': len(plan),
            'sources_count': len(sources),

            # URLs
            'pdf_url': pdf_url,
            'edit_url': f"/plan/{review.plan_id}",
            'view_url': f"/view/{review.plan_id}",

            # Next steps for n8n
            'next_steps': {
                'export_pdf': f"/api/export/{review.plan_id}/pdf",
                'export_package': f"/api/export/{review.plan_id}/package",
                'finalize': f"/api/plan/{review.plan_id}/finalize"
            }
        })

    except Exception as e:
        logger.exception(f"[Webhook] Generation error: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'project_id': payload.get('project_id') if payload else None
        }), 500


@app.route('/api/upload-docx', methods=['POST'])
def api_upload_docx():
    """
    Endpoint per upload e processing di file Word (.docx).

    Riceve uno o più file DOCX contenenti template SWOT, PEST, VISION,
    li processa ed estrae dati strutturati per la generazione del piano.

    Request:
        - multipart/form-data con:
            - files[]: uno o più file .docx
            - club_name: nome del club
            - project_id: (opzionale) ID progetto
            - hard_data: (opzionale) JSON con dati aggiuntivi

    Response:
    {
        "success": true,
        "files_processed": ["SWOT_Presidente.docx", "Vision.docx"],
        "document_types_detected": ["SWOT", "VISION"],
        "stakeholders_extracted": 2,
        "extracted_data": {...},
        "ready_for_generation": true
    }
    """
    try:
        # Verifica disponibilità python-docx
        if not DOCX_AVAILABLE:
            return jsonify({
                'success': False,
                'error': 'python-docx non installato. Eseguire: pip install python-docx'
            }), 500

        # Verifica files
        if 'files[]' not in request.files and 'files' not in request.files:
            return jsonify({
                'success': False,
                'error': 'Nessun file caricato. Usa il campo "files[]" o "files".'
            }), 400

        # Ottieni lista files
        files = request.files.getlist('files[]') or request.files.getlist('files')

        if not files or all(f.filename == '' for f in files):
            return jsonify({
                'success': False,
                'error': 'Nessun file valido caricato.'
            }), 400

        # Valida estensione
        valid_files = []
        for f in files:
            if f.filename and f.filename.lower().endswith('.docx'):
                valid_files.append(f)
            else:
                logger.warning(f"File ignorato (non .docx): {f.filename}")

        if not valid_files:
            return jsonify({
                'success': False,
                'error': 'Nessun file .docx valido trovato.'
            }), 400

        # Parametri
        club_name = request.form.get('club_name', 'Club')
        project_id = request.form.get('project_id')

        # Hard data (JSON opzionale)
        hard_data = {}
        if request.form.get('hard_data'):
            try:
                hard_data = json.loads(request.form.get('hard_data'))
            except json.JSONDecodeError:
                logger.warning("hard_data non è JSON valido, ignorato")

        logger.info(f"[DOCX Upload] Processing {len(valid_files)} files for {club_name}")

        # Prepara file per processing
        import io
        files_to_process = []
        for f in valid_files:
            # Leggi contenuto in BytesIO
            content = io.BytesIO(f.read())
            files_to_process.append((content, f.filename))

        # Processa tutti i file DOCX
        payload = process_docx_files_to_payload(
            files=files_to_process,
            club_name=club_name,
            project_id=project_id,
            hard_data=hard_data
        )

        logger.info(f"[DOCX Upload] Extracted {len(payload['stakeholders_inputs'])} stakeholders")
        logger.info(f"[DOCX Upload] Document types: {payload['document_types_detected']}")

        # Prepara response
        return jsonify({
            'success': True,
            'files_processed': payload['files_processed'],
            'document_types_detected': payload['document_types_detected'],
            'stakeholders_extracted': len(payload['stakeholders_inputs']),
            'extracted_data': {
                'stakeholders': [
                    {
                        'name': s['name'],
                        'role': s['role'],
                        'swot_count': {
                            'strengths': len(s.get('swot_strengths', [])),
                            'weaknesses': len(s.get('swot_weaknesses', [])),
                            'opportunities': len(s.get('swot_opportunities', [])),
                            'threats': len(s.get('swot_threats', []))
                        },
                        'priorities_count': len(s.get('priorities', [])),
                        'has_vision': bool(s.get('vision', '').strip())
                    }
                    for s in payload['stakeholders_inputs']
                ],
                'project_id': payload['project_id'],
                'club_name': payload['club_name']
            },
            'ready_for_generation': True,
            'payload': payload  # Payload completo per uso diretto
        })

    except Exception as e:
        logger.exception(f"[DOCX Upload] Error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/generate-from-docx', methods=['POST'])
def api_generate_from_docx():
    """
    Endpoint completo: upload DOCX + generazione piano.

    Combina upload-docx e generate-from-webhook in un unico endpoint
    per flusso semplificato.

    Request:
        - multipart/form-data con:
            - files[]: uno o più file .docx
            - club_name: nome del club
            - project_id: (opzionale) ID progetto
            - hard_data: (opzionale) JSON con dati aggiuntivi
            - request_mode: "production" o "draft"

    Response:
        Come /api/generate-from-webhook + info sui file processati
    """
    try:
        # Verifica disponibilità python-docx
        if not DOCX_AVAILABLE:
            return jsonify({
                'success': False,
                'error': 'python-docx non installato. Eseguire: pip install python-docx'
            }), 500

        # Verifica files
        if 'files[]' not in request.files and 'files' not in request.files:
            return jsonify({
                'success': False,
                'error': 'Nessun file caricato.'
            }), 400

        files = request.files.getlist('files[]') or request.files.getlist('files')

        valid_files = [f for f in files if f.filename and f.filename.lower().endswith('.docx')]

        if not valid_files:
            return jsonify({
                'success': False,
                'error': 'Nessun file .docx valido trovato.'
            }), 400

        # Parametri
        club_name = request.form.get('club_name', 'Club')
        project_id = request.form.get('project_id')
        request_mode = request.form.get('request_mode', 'production')

        # Hard data
        hard_data = {}
        if request.form.get('hard_data'):
            try:
                hard_data = json.loads(request.form.get('hard_data'))
            except json.JSONDecodeError:
                pass

        logger.info(f"[DOCX Generate] Processing {len(valid_files)} files for {club_name}")

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
            hard_data=hard_data
        )
        payload['request_mode'] = request_mode

        logger.info(f"[DOCX Generate] Extracted {len(payload['stakeholders_inputs'])} stakeholders")

        # 2. Process con Data Ingestor (Conflict Resolution)
        synthesized, generation_params = process_n8n_webhook_payload(payload)

        logger.info(f"[DOCX Generate] Synthesis complete. Alignment: {synthesized.stakeholder_alignment_score}")

        # 3. Web Research (se production mode)
        research_data = {}
        if request_mode == 'production':
            try:
                research_data = research_aggregator.comprehensive_club_research(
                    club_name=generation_params['club_name'],
                    city=generation_params.get('city', ''),
                    category=generation_params.get('category', ''),
                    competitors=[],
                    region=generation_params.get('region', '')
                )
                research_aggregator.export_research_report(research_data)
            except Exception as e:
                logger.warning(f"[DOCX Generate] Research failed: {e}")

        # 4. Genera piano
        logger.info("[DOCX Generate] Generating strategic plan...")

        club_data = generation_params.copy()
        club_data['synthesized_vision'] = synthesized.unified_vision
        club_data['swot_aggregated'] = {
            k: [item for item, _, _ in v[:5]]
            for k, v in synthesized.swot_aggregated.items()
        }
        club_data['priority_ranking'] = [p for p, _ in synthesized.priority_ranking[:5]]

        result = orchestrator.generate_strategic_plan(
            club_data=club_data,
            research_data=research_data.get('club', {}),
            parallel=True
        )

        plan = result['plan']
        sources = result['sources']
        metadata = result['metadata']

        # Aggiungi info DOCX al metadata
        metadata['source'] = 'docx_upload'
        metadata['files_processed'] = payload['files_processed']
        metadata['document_types'] = payload['document_types_detected']
        metadata['stakeholder_count'] = len(payload['stakeholders_inputs'])
        metadata['stakeholder_alignment'] = synthesized.stakeholder_alignment_score
        metadata['conflicts_count'] = len(synthesized.conflicts_detected)
        metadata['project_id'] = payload.get('project_id')

        # 5. Ottieni colori club
        club_identity = get_club_identity(
            club_name=generation_params['club_name'],
            custom_primary=hard_data.get('primary_color'),
            custom_secondary=hard_data.get('secondary_color')
        )
        metadata['primary_color'] = club_identity['primary']
        metadata['secondary_color'] = club_identity['secondary']
        metadata['category'] = generation_params.get('category', '')

        # 6. Crea review
        review = editor.create_review_from_plan(
            plan_data=plan,
            club_name=generation_params['club_name'],
            sources=sources,
            metadata=metadata
        )

        # 7. Salva in knowledge store
        plan_record = PlanRecord(
            id=review.plan_id,
            club_name=generation_params['club_name'],
            category=generation_params.get('category', ''),
            region=generation_params.get('region', ''),
            created_at=datetime.now().isoformat(),
            status='draft',
            plan_data=plan,
            sources_count=len(sources),
            credibility_score=metadata.get('credibility_score', 0),
        )
        knowledge_manager.add_plan_to_knowledge(plan_record)

        logger.info(f"[DOCX Generate] Plan generated: {review.plan_id}")

        # 8. Genera PDF automaticamente (se production mode)
        pdf_url = None
        if request_mode == 'production':
            try:
                pdf_exporter = PdfServerExporter()
                pdf_path = pdf_exporter.export(
                    plan_data=plan,
                    club_name=generation_params['club_name'],
                    sources=sources,
                    metadata=metadata
                )
                pdf_url = f"/download/{pdf_path.name}"
            except Exception as pdf_error:
                logger.warning(f"[DOCX Generate] PDF failed: {pdf_error}")

        # Response
        return jsonify({
            'success': True,
            'plan_id': review.plan_id,
            'project_id': payload.get('project_id'),
            'club_name': generation_params['club_name'],

            # DOCX info
            'docx_processing': {
                'files_processed': payload['files_processed'],
                'document_types_detected': payload['document_types_detected'],
                'stakeholders_extracted': len(payload['stakeholders_inputs'])
            },

            # Synthesis report
            'synthesis_report': {
                'stakeholders_processed': len(payload['stakeholders_inputs']),
                'alignment_score': synthesized.stakeholder_alignment_score,
                'unified_vision_preview': synthesized.unified_vision[:500] + '...' if len(synthesized.unified_vision) > 500 else synthesized.unified_vision,
                'top_priorities': [p for p, _ in synthesized.priority_ranking[:3]],
            },

            # Conflicts
            'conflicts_detected': [
                {
                    'area': c.area,
                    'description': c.description,
                    'severity': c.severity,
                    'resolution': c.resolution_applied
                }
                for c in synthesized.conflicts_detected
            ],

            # Plan info
            'sections_count': len(plan),
            'sources_count': len(sources),

            # URLs
            'pdf_url': pdf_url,
            'edit_url': f"/plan/{review.plan_id}",
            'view_url': f"/view/{review.plan_id}",

            # Next steps
            'next_steps': {
                'export_pdf': f"/api/export/{review.plan_id}/pdf",
                'export_package': f"/api/export/{review.plan_id}/package",
                'finalize': f"/api/plan/{review.plan_id}/finalize"
            }
        })

    except Exception as e:
        logger.exception(f"[DOCX Generate] Error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# =============================================================================
# API - EDITING
# =============================================================================

@app.route('/api/section/<plan_id>/<section_id>', methods=['GET'])
def api_get_section(plan_id: str, section_id: str):
    """Recupera sezione"""
    section = editor.get_section(plan_id, section_id)
    if section:
        return jsonify({
            'success': True,
            'section': section.to_dict(),
        })
    return jsonify({'success': False, 'error': 'Section not found'}), 404


@app.route('/api/section/<plan_id>/<section_id>', methods=['PUT'])
def api_update_section(plan_id: str, section_id: str):
    """Aggiorna contenuto sezione"""
    try:
        data = request.json
        new_content = data.get('content')
        reason = data.get('reason', '')
        editor_name = data.get('editor', 'user')

        if not new_content:
            return jsonify({'success': False, 'error': 'content required'}), 400

        success = editor.update_section_content(
            plan_id=plan_id,
            section_id=section_id,
            new_content=new_content,
            editor=editor_name,
            reason=reason
        )

        return jsonify({'success': success})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/section/<plan_id>/<section_id>/approve', methods=['POST'])
def api_approve_section(plan_id: str, section_id: str):
    """Approva sezione"""
    data = request.json or {}
    approver = data.get('approver', 'user')

    success = editor.approve_section(plan_id, section_id, approver)
    return jsonify({'success': success})


@app.route('/api/section/<plan_id>/<section_id>/note', methods=['POST'])
def api_add_note(plan_id: str, section_id: str):
    """Aggiunge nota a sezione"""
    data = request.json
    note = data.get('note', '')
    editor_name = data.get('editor', 'user')

    success = editor.add_section_note(plan_id, section_id, note, editor_name)
    return jsonify({'success': success})


# =============================================================================
# API - EXPORT
# =============================================================================

@app.route('/api/export/<plan_id>', methods=['POST'])
def api_export_plan(plan_id: str):
    """
    Esporta piano nei formati richiesti.
    Default: HTML Print-Ready (Paged.js) con branding automatico.
    Opzionale: DOCX per editing.
    """
    try:
        data = request.json or {}
        formats = data.get('formats', ['paged', 'docx'])  # Default: Paged.js + DOCX

        # Recupera piano
        review = editor.reviews.get(plan_id)
        if not review:
            return jsonify({'success': False, 'error': 'Plan not found'}), 404

        plan_data = editor.export_plan_for_final(plan_id)
        if not plan_data:
            return jsonify({'success': False, 'error': 'No content to export'}), 400

        sources = []  # TODO: recuperare fonti salvate

        # === BRANDING AUTOMATICO ===
        club_identity = get_club_identity(
            club_name=review.club_name,
            custom_primary=getattr(review, 'primary_color', None),
            custom_secondary=getattr(review, 'secondary_color', None)
        )
        logger.info(f"Export branding: {review.club_name} -> {club_identity['primary']}")

        metadata = {
            'category': review.category,
            'primary_color': club_identity['primary'],
            'secondary_color': club_identity['secondary'],
            'accent_color': club_identity.get('accent'),
            'credibility_score': sum(s.credibility_score for s in review.sections.values()) / len(review.sections) if review.sections else 0
        }

        files = {}

        # HTML Print-Ready (Paged.js) - FORMATO PRINCIPALE
        if 'paged' in formats or 'html' in formats:
            paged_path = create_paged_html(
                plan_data=plan_data,
                club_name=review.club_name,
                sources=sources,
                metadata=metadata
            )
            files['paged'] = paged_path.name
            files['html'] = paged_path.name  # Alias per compatibilità

        # DOCX (opzionale, per editing)
        if 'docx' in formats:
            # Passa anche i colori al DOCX
            docx_path = docx_exporter.create_document(
                plan_data=plan_data,
                club_name=review.club_name,
                sources=sources,
                metadata=metadata
            )
            files['docx'] = docx_path.name

        # Marca come esportato
        editor.mark_exported(plan_id, str(files))

        return jsonify({
            'success': True,
            'files': files,
        })

    except Exception as e:
        logger.exception(f"Export error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/download/<filename>')
def download_file(filename: str):
    """Download file esportato"""
    filepath = OUTPUT_DIR / filename
    if filepath.exists():
        return send_file(
            filepath,
            as_attachment=True,
            download_name=filename
        )
    return "File not found", 404


@app.route('/api/export/<plan_id>/package', methods=['POST'])
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
        if not review:
            return jsonify({'success': False, 'error': 'Plan not found'}), 404

        plan_data = editor.export_plan_for_final(plan_id)
        if not plan_data:
            return jsonify({'success': False, 'error': 'No content to export'}), 400

        sources = []

        # === BRANDING AUTOMATICO ===
        club_identity = get_club_identity(
            club_name=review.club_name,
            custom_primary=getattr(review, 'primary_color', None),
            custom_secondary=getattr(review, 'secondary_color', None)
        )
        logger.info(f"Package export branding: {review.club_name} -> {club_identity['primary']}")

        metadata = {
            'category': review.category,
            'primary_color': club_identity['primary'],
            'secondary_color': club_identity['secondary'],
            'accent_color': club_identity.get('accent'),
            'credibility_score': sum(s.credibility_score for s in review.sections.values()) / len(review.sections) if review.sections else 0
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
                metadata=metadata
            )
            files_added.append(('pdf', str(pdf_path)))
            logger.info(f"PDF Server-side generato: {pdf_path}")
        except Exception as pdf_error:
            logger.error(f"Errore generazione PDF Server-side: {pdf_error}", exc_info=True)

        # --- DOCX (per editing) ---
        try:
            docx_exporter.output_dir = Path(temp_dir)
            docx_path = docx_exporter.create_document(
                plan_data=plan_data,
                club_name=review.club_name,
                sources=sources,
                metadata=metadata
            )
            files_added.append(('docx', str(docx_path)))
            logger.info(f"DOCX generato: {docx_path}")
        except Exception as docx_error:
            logger.error(f"Errore generazione DOCX: {docx_error}", exc_info=True)

        # Verifica che almeno un file sia stato generato
        if not files_added:
            return jsonify({'success': False, 'error': 'Nessun file generato'}), 500

        # --- Creazione Archivio ZIP ---
        zip_filename_base = f"{safe_name}_StrategyPack_{timestamp}"
        zip_path = os.path.join(temp_dir, f"{zip_filename_base}.zip")

        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
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
            mimetype='application/zip',
            as_attachment=True,
            download_name=f"{zip_filename_base}.zip"
        )

    except Exception as e:
        logger.exception(f"Package export error: {e}")
        if temp_dir and os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
            except:
                pass
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/export/<plan_id>/pdf', methods=['GET'])
def api_export_pdf_server(plan_id: str):
    """
    Esporta piano in formato PDF via WeasyPrint (lato server).
    Garantisce stabilità totale e layout professionale senza crash del browser.
    """
    try:
        review = editor.reviews.get(plan_id)
        if not review:
            return jsonify({'success': False, 'error': 'Plan not found'}), 404

        plan_data = editor.export_plan_for_final(plan_id)
        if not plan_data:
            return jsonify({'success': False, 'error': 'No content to export'}), 400

        # Ottieni colori del club
        club_identity = get_club_identity(review.club_name)

        metadata = {
            'category': review.category,
            'primary_color': club_identity.get('primary', '#1a365d'),
            'secondary_color': club_identity.get('secondary', '#ffffff'),
            'credibility_score': sum(s.credibility_score for s in review.sections.values()) / len(review.sections) if review.sections else 0
        }

        # Usa il nuovo PdfServerExporter
        from export_pdf_server import PdfServerExporter
        pdf_exporter = PdfServerExporter()
        pdf_path = pdf_exporter.export(
            plan_data=plan_data,
            club_name=review.club_name,
            sources=[], # Fonti integrate nel PDF
            metadata=metadata
        )

        return send_file(
            pdf_path,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=pdf_path.name
        )

    except Exception as e:
        logger.exception(f"PDF Server export error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/export/<plan_id>/html', methods=['GET'])
def api_export_html_only(plan_id: str):
    """
    Esporta piano in formato HTML con Bento Grid infografico e Paged.js.
    Layout responsive: A4 paginato su desktop, scrollabile su mobile.
    """
    try:
        review = editor.reviews.get(plan_id)
        if not review:
            return jsonify({'success': False, 'error': 'Plan not found'}), 404

        plan_data = editor.export_plan_for_final(plan_id)
        if not plan_data:
            return jsonify({'success': False, 'error': 'No content to export'}), 400

        # Ottieni colori del club
        club_identity = get_club_identity(review.club_name)

        metadata = {
            'category': review.category,
            'primary_color': club_identity.get('primary', '#1a365d'),
            'secondary_color': club_identity.get('secondary', '#ffffff'),
            'credibility_score': sum(s.credibility_score for s in review.sections.values()) / len(review.sections) if review.sections else 0
        }

        # Usa il nuovo PdfServerExporter per un export PDF stabile
        pdf_exporter = PdfServerExporter()
        pdf_path = pdf_exporter.export(
            plan_data=plan_data,
            club_name=review.club_name,
            sources=[],
            metadata=metadata
        )

        return send_file(
            pdf_path,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=pdf_path.name.replace('.pdf', '_Report.pdf')
        )

    except Exception as e:
        logger.exception(f"HTML export error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/view/<plan_id>')
def view_plan_html(plan_id: str):
    """
    Visualizza piano in HTML nel browser (per anteprima e stampa).
    """
    try:
        review = editor.reviews.get(plan_id)
        if not review:
            return "Piano non trovato", 404

        plan_data = editor.export_plan_for_final(plan_id)
        if not plan_data:
            return "Nessun contenuto disponibile", 400

        sources = []
        metadata = {
            'category': review.category,
            'credibility_score': sum(s.credibility_score for s in review.sections.values()) / len(review.sections) if review.sections else 0
        }

        html_content = _generate_printable_html(plan_data, review.club_name, sources, metadata)
        return html_content

    except Exception as e:
        logger.exception(f"View error: {e}")
        return f"Errore: {str(e)}", 500


@app.route('/api/export/<plan_id>/executive', methods=['GET'])
def api_export_executive_report(plan_id: str):
    """
    Esporta Executive Report A4 - sintesi ottimizzata per stampa.
    Formato compatto (3-4 pagine) con tutti i dati essenziali.
    """
    try:
        review = editor.reviews.get(plan_id)
        if not review:
            return jsonify({'success': False, 'error': 'Plan not found'}), 404

        plan_data = editor.export_plan_for_final(plan_id)
        if not plan_data:
            return jsonify({'success': False, 'error': 'No content to export'}), 400

        # Prepara metadata con colori e stime
        metadata = {
            'category': review.category,
            'primary_color': getattr(review, 'primary_color', None) or '#1a365d',
            'secondary_color': getattr(review, 'secondary_color', None) or '#ffffff',
            'dimensione_rosa': getattr(review, 'squad_size', 22),
            'capienza_stadio': getattr(review, 'stadium_capacity', 0),
            'known_financials': {},
            'estimated_fields': {
                'fatturato': 'tier3_estimated',
                'monte_ingaggi': 'tier2_deduced',
                'valore_rosa': 'tier2_deduced'
            }
        }

        # Genera Executive Report HTML
        html_content = generate_executive_report_html(
            plan_data=plan_data,
            club_name=review.club_name,
            category=review.category,
            metadata=metadata,
            sources=[]
        )

        safe_name = review.club_name.replace(" ", "_").replace("/", "_")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{safe_name}_ExecutiveReport_{timestamp}.html"

        # Salva in OUTPUT_DIR
        html_path = OUTPUT_DIR / filename
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html_content)

        return send_file(
            html_path,
            mimetype='text/html',
            as_attachment=True,
            download_name=filename
        )

    except Exception as e:
        logger.exception(f"Executive report export error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/view/<plan_id>/executive')
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
            'category': review.category,
            'primary_color': getattr(review, 'primary_color', None) or '#1a365d',
            'secondary_color': getattr(review, 'secondary_color', None) or '#ffffff',
            'dimensione_rosa': getattr(review, 'squad_size', 22),
            'capienza_stadio': getattr(review, 'stadium_capacity', 0),
            'known_financials': {},
            'estimated_fields': {}
        }

        html_content = generate_executive_report_html(
            plan_data=plan_data,
            club_name=review.club_name,
            category=review.category,
            metadata=metadata,
            sources=[]
        )

        return html_content

    except Exception as e:
        logger.exception(f"Executive view error: {e}")
        return f"Errore: {str(e)}", 500


def _hex_to_rgb(hex_color: str) -> tuple:
    """Converte colore hex in RGB."""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


def _get_contrast_color(hex_color: str) -> str:
    """Restituisce bianco o nero in base al contrasto."""
    r, g, b = _hex_to_rgb(hex_color)
    luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
    return '#ffffff' if luminance < 0.5 else '#1a202c'


def _darken_color(hex_color: str, factor: float = 0.2) -> str:
    """Scurisce un colore."""
    r, g, b = _hex_to_rgb(hex_color)
    r = int(r * (1 - factor))
    g = int(g * (1 - factor))
    b = int(b * (1 - factor))
    return f'#{r:02x}{g:02x}{b:02x}'


def _lighten_color(hex_color: str, factor: float = 0.2) -> str:
    """Schiarisce un colore."""
    r, g, b = _hex_to_rgb(hex_color)
    r = min(255, int(r + (255 - r) * factor))
    g = min(255, int(g + (255 - g) * factor))
    b = min(255, int(b + (255 - b) * factor))
    return f'#{r:02x}{g:02x}{b:02x}'


def _generate_printable_html(plan_data: dict, club_name: str, sources: list, metadata: dict) -> str:
    """
    Genera HTML completo con stili di stampa ottimizzati, branding del club
    e tecniche di guerrilla marketing (colori societari, elementi visivi distintivi).
    """
    current_year = datetime.now().year
    category = metadata.get('category', '') or ''
    credibility = metadata.get('credibility_score', 0) or 0

    # Colori del club (guerrilla marketing: identità visiva)
    primary_color = metadata.get('primary_color') or '#1a365d'
    secondary_color = metadata.get('secondary_color') or '#ffffff'

    # Genera varianti colore per design coerente
    primary_dark = _darken_color(primary_color, 0.2)
    primary_light = _lighten_color(primary_color, 0.85)
    accent_color = _lighten_color(primary_color, 0.3)
    text_on_primary = _get_contrast_color(primary_color)

    # Genera sezioni HTML
    sections_html = ""
    section_configs = [
        ('executive_summary', 'Executive Summary', '📋'),
        ('technical_sporting', 'Area Tecnico-Sportiva', '⚽'),
        ('youth_development', 'Settore Giovanile', '🌱'),
        ('infrastructure', 'Infrastrutture', '🏟️'),
        ('marketing_commercial', 'Marketing e Commerciale', '📈'),
        ('social_sustainability', 'Sostenibilità Sociale', '🤝'),
        ('governance', 'Governance', '🏛️'),
        ('financial', 'Piano Finanziario', '💰'),
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
    dashboard_html = generate_strategic_dashboard(plan_data, primary_color, secondary_color)
    # Inserisci dopo Executive Summary
    if 'id="technical_sporting"' in sections_html:
        sections_html = sections_html.replace(
            '<section class="section" id="technical_sporting">',
            f'{dashboard_html}<section class="section" id="technical_sporting">'
        )
    else:
        sections_html = dashboard_html + sections_html

    # === SEZIONE METODOLOGIA E FONTI ===
    # Genera sezione trasparenza con fonti dati e disclaimer
    try:
        estimated_fields = metadata.get('estimated_fields', {})
        if not estimated_fields:
            # Default: assume alcuni campi sono stimati per club piccoli
            estimated_fields = {
                'fatturato': 'tier3_estimated',
                'monte_ingaggi': 'tier2_deduced',
                'valore_rosa': 'tier2_deduced'
            }
        
        methodology_html = generate_methodology_section_html(
            club_name=club_name,
            category=category,
            data_sources_used=get_default_sources_for_report(),
            estimated_fields=estimated_fields,
            primary_color=primary_color
        )
        # Aggiungi alla fine delle sezioni
        sections_html += methodology_html
    except Exception as e:
        logger.warning(f"Errore generazione sezione metodologia: {e}")

    # === GRAFICI FINANZIARI ===
    # Genera grafici se abbiamo dati finanziari
    try:
        club_data = {
            'dimensione_rosa': metadata.get('dimensione_rosa', 22),
            'capienza_stadio': metadata.get('capienza_stadio', 0)
        }
        known_financials = metadata.get('known_financials', {})
        
        estimates = estimate_missing_financials(club_data, category, known_financials)
        charts = generate_financial_charts_for_report(
            club_name=club_name,
            category=category,
            estimated_financials=estimates,
            primary_color=primary_color
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
                {charts.get('kpi_dashboard', '')}
                <h3>Composizione Ricavi Stimata</h3>
                {charts.get('revenue_pie', '')}
                <h3>Confronto con Benchmark {category}</h3>
                {charts.get('benchmark_comparison', '')}
                <h3>Gap Analysis</h3>
                {charts.get('gap_analysis', '')}
            </div>
        </section>
        """
        
        # Inserisci prima della metodologia
        if 'id="methodology"' in sections_html:
            sections_html = sections_html.replace(
                '<section class="section methodology-section"',
                f'{charts_html}<section class="section methodology-section"'
            )
        else:
            sections_html += charts_html
            
    except Exception as e:
        logger.warning(f"Errore generazione grafici: {e}")

    # Anno fondazione (se disponibile)
    foundation_year = metadata.get('foundation_year', '')
    foundation_text = f" • Fondato nel {foundation_year}" if foundation_year else ""

    return f'''<!DOCTYPE html>
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
            Documento generato da Rooting Future Strategy Engine v5.4<br>
            {datetime.now().strftime('%d/%m/%Y alle %H:%M')}
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
</html>'''


def _simple_markdown_to_html(content: str) -> str:
    """Converte markdown semplice in HTML."""
    import re

    if not content:
        return "<p><em>Contenuto non disponibile</em></p>"

    # Escape HTML
    content = content.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

    lines = content.split('\n')
    html_parts = []
    in_list = False
    list_type = None

    for line in lines:
        line = line.strip()

        if not line:
            if in_list:
                html_parts.append(f'</{list_type}>')
                in_list = False
            continue

        # Headers
        if line.startswith('### '):
            if in_list:
                html_parts.append(f'</{list_type}>')
                in_list = False
            html_parts.append(f'<h4>{line[4:]}</h4>')
            continue
        if line.startswith('## '):
            if in_list:
                html_parts.append(f'</{list_type}>')
                in_list = False
            html_parts.append(f'<h3>{line[3:]}</h3>')
            continue

        # Bullet lists
        if line.startswith('- ') or line.startswith('* '):
            if not in_list or list_type != 'ul':
                if in_list:
                    html_parts.append(f'</{list_type}>')
                html_parts.append('<ul>')
                in_list = True
                list_type = 'ul'
            text = _format_inline(line[2:])
            html_parts.append(f'<li>{text}</li>')
            continue

        # Numbered lists
        if line and line[0].isdigit() and len(line) > 1:
            for i, c in enumerate(line[:5]):
                if c in '.):':
                    if not in_list or list_type != 'ol':
                        if in_list:
                            html_parts.append(f'</{list_type}>')
                        html_parts.append('<ol>')
                        in_list = True
                        list_type = 'ol'
                    text = _format_inline(line[i+1:].strip())
                    html_parts.append(f'<li>{text}</li>')
                    break
            else:
                if in_list:
                    html_parts.append(f'</{list_type}>')
                    in_list = False
                html_parts.append(f'<p>{_format_inline(line)}</p>')
            continue

        # Regular paragraph
        if in_list:
            html_parts.append(f'</{list_type}>')
            in_list = False
        html_parts.append(f'<p>{_format_inline(line)}</p>')

    if in_list:
        html_parts.append(f'</{list_type}>')

    return '\n'.join(html_parts)


def _format_inline(text: str) -> str:
    """Formatta bold e italic."""
    import re
    # Bold **text**
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    # Italic *text*
    text = re.sub(r'\*([^\*]+?)\*', r'<em>\1</em>', text)
    return text


@app.route('/api/export/<plan_id>/pdf', methods=['GET'])
def api_export_pdf_only(plan_id: str):
    """
    Esporta piano solo in formato PDF.
    Usa WeasyPrint per alta qualità.
    """
    temp_dir = None
    try:
        review = editor.reviews.get(plan_id)
        if not review:
            return jsonify({'success': False, 'error': 'Plan not found'}), 404

        plan_data = editor.export_plan_for_final(plan_id)
        if not plan_data:
            return jsonify({'success': False, 'error': 'No content to export'}), 400

        sources = []
        metadata = {
            'category': review.category,
            'credibility_score': sum(s.credibility_score for s in review.sections.values()) / len(review.sections) if review.sections else 0
        }

        html_content = _generate_printable_html(plan_data, review.club_name, sources, metadata)

        safe_name = review.club_name.replace(" ", "_").replace("/", "_")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        pdf_filename = f"{safe_name}_PianoStrategico_{timestamp}"

        temp_dir = tempfile.mkdtemp(prefix="pdf_export_")

        pdf_success = create_pdf_from_html(
            html_content=html_content,
            output_path=temp_dir,
            plan_name=pdf_filename
        )

        if not pdf_success:
            if temp_dir and os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
            return jsonify({'success': False, 'error': 'Generazione PDF fallita'}), 500

        pdf_temp_path = os.path.join(temp_dir, f"{pdf_filename}.pdf")

        # Copia in output directory
        final_pdf_path = OUTPUT_DIR / f"{pdf_filename}.pdf"
        shutil.copy2(pdf_temp_path, final_pdf_path)

        # Pulisci temp
        if temp_dir and os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
            except:
                pass

        return send_file(
            final_pdf_path,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f"{pdf_filename}.pdf"
        )

    except Exception as e:
        logger.exception(f"PDF export error: {e}")
        if temp_dir and os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
            except:
                pass
        return jsonify({'success': False, 'error': str(e)}), 500




@app.route('/api/export/<plan_id>/paged', methods=['GET'])
def api_export_paged_html(plan_id: str):
    """
    Esporta piano come HTML Print-First con Paged.js.
    Documento pronto per Stampa -> PDF con layout A4 paginato.
    Branding automatico basato sul nome del club.
    """
    try:
        review = editor.reviews.get(plan_id)
        if not review:
            return jsonify({'success': False, 'error': 'Plan not found'}), 404

        plan_data = editor.export_plan_for_final(plan_id)
        if not plan_data:
            return jsonify({'success': False, 'error': 'No content to export'}), 400

        # === BRANDING AUTOMATICO ===
        # Prova a ottenere colori custom dai metadata del review
        custom_primary = getattr(review, 'primary_color', None)
        custom_secondary = getattr(review, 'secondary_color', None)

        # Se non ci sono colori custom, deducili dal nome del club
        club_identity = get_club_identity(
            club_name=review.club_name,
            custom_primary=custom_primary,
            custom_secondary=custom_secondary
        )

        logger.info(f"Club branding: {review.club_name} -> {club_identity['primary']} (custom: {club_identity['is_custom']})")

        sources = []
        metadata = {
            'category': review.category,
            'primary_color': club_identity['primary'],
            'secondary_color': club_identity['secondary'],
            'accent_color': club_identity.get('accent'),
        }

        # Genera HTML Paged.js
        filepath = create_paged_html(
            plan_data=plan_data,
            club_name=review.club_name,
            sources=sources,
            metadata=metadata
        )

        return send_file(
            filepath,
            mimetype='text/html',
            as_attachment=True,
            download_name=filepath.name
        )

    except Exception as e:
        logger.exception(f"Paged HTML export error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/preview/<plan_id>', methods=['GET'])
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
            custom_primary=getattr(review, 'primary_color', None),
            custom_secondary=getattr(review, 'secondary_color', None)
        )

        logger.info(f"Preview branding: {review.club_name} -> {club_identity['primary']}")

        metadata = {
            'category': review.category,
            'primary_color': club_identity['primary'],
            'secondary_color': club_identity['secondary'],
            'accent_color': club_identity.get('accent'),
        }

        # Genera HTML Paged.js
        filepath = create_paged_html(
            plan_data=plan_data,
            club_name=review.club_name,
            sources=[],
            metadata=metadata
        )

        # Restituisce HTML inline (visualizza nel browser, non download)
        return send_file(
            filepath,
            mimetype='text/html',
            as_attachment=False  # Inline, non download
        )

    except Exception as e:
        logger.exception(f"Preview error: {e}")
        return f"Errore: {str(e)}", 500


# =============================================================================
# API - WORKFLOW
# =============================================================================

@app.route('/api/plan/<plan_id>/finalize', methods=['POST'])
def api_finalize_plan(plan_id: str):
    """
    Finalizza il piano e lo carica nella knowledge base di Gemini File Search.
    """
    data = request.json or {}
    notes = data.get('notes', '')

    success = editor.finalize_plan(plan_id, notes)
    if not success:
        return jsonify({
            'success': False,
            'error': 'Cannot finalize: some sections not approved'
        }), 400

    # Se la finalizzazione ha successo, carica il piano nella Knowledge Base RAG
    try:
        logger.info(f"Piano '{plan_id}' finalizzato. Preparazione per upload nella Knowledge Base RAG...")
        review = editor.reviews.get(plan_id)
        if not review:
            raise ValueError("Review non trovata dopo finalizzazione.")

        plan_data = editor.export_plan_for_final(plan_id)
        
        # Esporta il piano come PDF in una directory temporanea
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_dir_path = Path(temp_dir)
            
            # Genera HTML
            html_exporter_instance = ChunkedHTMLExporter()
            html_content = html_exporter_instance._assemble_document(review.club_name, {})

            # Crea PDF
            safe_name = review.club_name.replace(" ", "_")
            pdf_success = create_pdf_from_html(html_content, str(temp_dir_path), safe_name)
            
            if pdf_success:
                pdf_path = temp_dir_path / f"{safe_name}.pdf"
                # Carica il PDF usando il FileSearchManager
                upload_success = file_search_manager.upload_file(pdf_path)
                if not upload_success:
                    logger.warning(f"Finalizzazione riuscita, ma upload nella RAG KB fallito per il piano '{plan_id}'.")
            else:
                logger.warning(f"Finalizzazione riuscita, ma creazione PDF per RAG KB fallita per il piano '{plan_id}'.")

    except Exception as e:
        logger.error(f"Errore durante l'upload del piano finalizzato '{plan_id}' nella RAG KB: {e}")
        # Non bloccare la risposta all'utente per questo, ma logga l'errore.
        
    return jsonify({'success': True})


@app.route('/api/plan/<plan_id>/archive', methods=['POST'])
def api_archive_plan(plan_id: str):
    """Archivia piano"""
    success = editor.archive_plan(plan_id)
    return jsonify({'success': success})


@app.route('/api/bulk-approve', methods=['POST'])
def api_bulk_approve():
    """Auto-approva sezioni ad alta credibilità"""
    data = request.json or {}
    min_credibility = data.get('min_credibility', 80.0)

    count = batch_manager.auto_approve_high_credibility(min_credibility)
    return jsonify({
        'success': True,
        'approved_count': count,
    })


# =============================================================================
# API - STATS
# =============================================================================

@app.route('/api/stats')
def api_stats():
    """Statistiche sistema"""
    dashboard_stats = editor.get_dashboard_stats()
    workload = batch_manager.get_workload_summary()
    knowledge_stats = knowledge_manager.store.get_statistics()

    return jsonify({
        'dashboard': dashboard_stats,
        'workload': workload,
        'knowledge': knowledge_stats,
    })


@app.route('/api/agents')
def api_agents():
    """Info agenti disponibili"""
    return jsonify({
        'agents': orchestrator.get_agent_info()
    })


# =============================================================================
# API - SISTEMA STRUTTURATO v5.4
# =============================================================================

@app.route('/api/structured/generate', methods=['POST'])
def api_structured_generate():
    """
    Genera piano con sistema strutturato (benchmark + validazione scientifica).
    Questo e' il nuovo sistema v5.4 che produce dati tracciabili.
    """
    try:
        data = request.json or {}

        # Valida input
        club_name = data.get('club_name')
        category = data.get('category')

        if not club_name or not category:
            return jsonify({
                'success': False,
                'error': 'club_name e category sono obbligatori'
            }), 400

        # Prepara club data
        club_data = {
            'club_name': club_name,
            'category': category,
            'city': data.get('city', ''),
            'region': data.get('region', ''),
            # Dati finanziari
            'revenue': data.get('revenue'),
            'wage_bill': data.get('wage_bill'),
            'net_assets': data.get('net_assets'),
            # Dati sportivi
            'squad_size': data.get('squad_size'),
            'average_age': data.get('average_age'),
            # Infrastrutture
            'stadium_capacity': data.get('stadium_capacity'),
            'training_fields': data.get('training_fields'),
            # Settore giovanile
            'youth_players': data.get('youth_players'),
            'youth_teams': data.get('youth_teams'),
        }

        # Ricerca web se richiesta
        research_data = None
        if data.get('enable_research', True):
            try:
                research_results = researcher.research_club(club_name)
                research_data = research_aggregator.aggregate(research_results)
            except Exception as e:
                logger.warning(f"Research failed: {e}")

        # Genera piano strutturato
        plan = structured_orchestrator.generate_plan(club_data, research_data)

        # Render HTML
        filepath = structured_renderer.render(plan)

        return jsonify({
            'success': True,
            'plan_id': plan.plan_id,
            'output_file': os.path.basename(filepath),
            'stats': {
                'total_data_points': plan.total_data_points,
                'verified_data_points': plan.verified_data_points,
                'missing_data_points': plan.missing_data_points,
                'overall_credibility': plan.overall_credibility,
                'sources_count': len(plan.bibliography)
            }
        })

    except Exception as e:
        logger.exception(f"Structured generation error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/structured/benchmarks/<category>')
def api_structured_benchmarks(category: str):
    """
    Restituisce i benchmark per una categoria.
    Utile per il frontend per mostrare cosa ci aspettiamo.
    """
    from data_models import BenchmarkDatabase

    benchmarks = {
        'financial': BenchmarkDatabase.FINANCIAL_BENCHMARKS.get(category, {}),
        'sporting': BenchmarkDatabase.SPORTING_BENCHMARKS.get(category, {}),
        'youth': BenchmarkDatabase.YOUTH_BENCHMARKS.get(category, {}),
        'infrastructure': BenchmarkDatabase.INFRASTRUCTURE_BENCHMARKS.get(category, {}),
    }

    return jsonify({
        'success': True,
        'category': category,
        'benchmarks': benchmarks
    })


@app.route('/api/structured/templates')
def api_structured_templates():
    """
    Restituisce i template dei data points richiesti per ogni sezione.
    """
    return jsonify({
        'success': True,
        'templates': SECTION_DATA_TEMPLATES
    })


@app.route('/api/questionnaire/schema')
def api_questionnaire_schema():
    """
    Restituisce lo schema del questionario per n8n/frontend.
    """
    return jsonify({
        'success': True,
        'schema': get_questionnaire_schema()
    })


# =============================================================================
# ERROR HANDLERS
# =============================================================================

@app.errorhandler(404)
def not_found(e):
    if request.path.startswith('/api/'):
        return jsonify({'success': False, 'error': 'Not found'}), 404
    # Simple HTML response instead of template
    return '''
    <html><head><title>404 - Non trovato</title></head>
    <body style="font-family: sans-serif; text-align: center; padding: 50px;">
        <h1>404 - Pagina non trovata</h1>
        <p><a href="/">Torna alla Dashboard</a></p>
    </body></html>
    ''', 404


@app.errorhandler(500)
def server_error(e):
    logger.exception(f"Server error: {e}")
    if request.path.startswith('/api/'):
        return jsonify({'success': False, 'error': str(e)}), 500
    return f'''
    <html><head><title>500 - Errore</title></head>
    <body style="font-family: sans-serif; text-align: center; padding: 50px;">
        <h1>500 - Errore interno</h1>
        <p>Si e verificato un errore: {str(e)}</p>
        <p><a href="/">Torna alla Dashboard</a></p>
    </body></html>
    ''', 500


# =============================================================================
# CLI COMMANDS
# =============================================================================

@app.cli.command('init-db')
def init_db():
    """Inizializza database"""
    knowledge_manager.store._init_db()
    print("Database initialized")


@app.cli.command('export-knowledge')
def export_knowledge():
    """Esporta knowledge base"""
    path = knowledge_manager.export_full_knowledge_base()
    print(f"Exported to: {path}")


@app.cli.command('auto-approve')
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
            s.bind(('127.0.0.1', port))
            return True
        except OSError:
            return False


def kill_process_on_port(port: int) -> bool:
    """Tenta di terminare il processo che occupa la porta (Windows)."""
    import subprocess
    try:
        # Trova PID del processo sulla porta
        result = subprocess.run(
            f'netstat -ano | findstr :{port}',
            shell=True, capture_output=True, text=True
        )
        if result.stdout:
            lines = result.stdout.strip().split('\n')
            for line in lines:
                if 'LISTENING' in line:
                    parts = line.split()
                    pid = parts[-1]
                    print(f"[!] Porta {port} occupata da PID {pid}. Tentativo di terminazione...")
                    subprocess.run(f'taskkill /F /PID {pid}', shell=True, capture_output=True)
                    import time
                    time.sleep(1)
                    return True
        return False
    except Exception as e:
        print(f"[!] Errore durante kill processo: {e}")
        return False


if __name__ == '__main__':
    PORT = 5000

    # Verifica configurazione
    missing = get_missing_config()
    if missing:
        print(f"WARNING: Missing config: {missing}")
        print("Some features may not work correctly.")

    # Assicura directories
    OUTPUT_DIR.mkdir(exist_ok=True)
    KNOWLEDGE_DIR.mkdir(exist_ok=True)

    # Inizializza SSE handler ORA che tutti gli import sono completati
    # Questo evita deadlock durante il caricamento dei moduli
    try:
        log_stream_handler = LogStreamHandler()
        log_stream_handler.setLevel(logging.INFO)
        # Aggiungi solo al logger dell'app, non al root
        logger.addHandler(log_stream_handler)
        print("[*] SSE Log Streaming attivo")
    except Exception as e:
        print(f"[!] SSE handler non disponibile: {e}")
        log_stream_handler = None

    print(f"""
    ===============================================================
    |                                                             |
    |     ROOTING FUTURE STRATEGY ENGINE v5.4                     |
    |     Dashboard Hybrid - Live Console + Upload                |
    |                                                             |
    |     Server: http://127.0.0.1:{PORT}                          |
    |                                                             |
    ===============================================================
    """)

    print("[*] Avvio server Flask...")
    print(f"[*] Aprire nel browser: http://127.0.0.1:{PORT}")
    print("[*] Premi Ctrl+C per terminare\n")

    # Usa 127.0.0.1 per evitare problemi firewall Windows
    # Il controllo porta viene gestito dal batch file
    app.run(
        host='127.0.0.1',
        port=PORT,
        debug=False,
        threaded=True,
        use_reloader=False
    )
