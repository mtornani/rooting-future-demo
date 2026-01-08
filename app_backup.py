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
)

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


# =============================================================================
# SETUP
# =============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'rooting-future-dev-key-change-in-prod')

# Aggiungi 'now' al contesto Jinja2
@app.context_processor
def inject_now():
    return {'now': datetime.now}

# Inizializza componenti
file_search_manager = FileSearchManager()

# Knowledge manager prima, per passare store all'orchestrator (apprendimento)
knowledge_manager = KnowledgeManager()
orchestrator = MultiAgentOrchestrator(
    knowledge_store=knowledge_manager.store,
    file_search_store_name=file_search_manager.get_store_name() # Passa lo store name
)
researcher = WebResearcher()
research_aggregator = ResearchAggregator()
docx_exporter = ProfessionalDocxExporter()
html_exporter = ChunkedHTMLExporter()
editor = PostProductionEditor()
batch_manager = BatchReviewManager()

# Nuovo sistema strutturato v5.4
structured_orchestrator = StructuredOrchestrator(file_search_store_name=file_search_manager.get_store_name())
structured_renderer = StructuredHTMLRenderer()


# =============================================================================
# ROUTES - PAGINE
# =============================================================================

@app.route('/')
def index():
    """Homepage con dashboard"""
    # Config check
    missing = get_missing_config()
    if missing:
        flash(f"Configurazione incompleta: {', '.join(missing)}", 'warning')

    # Stats
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
    """Esporta piano in DOCX e HTML"""
    try:
        data = request.json or {}
        formats = data.get('formats', ['docx', 'html'])

        # Recupera piano
        review = editor.reviews.get(plan_id)
        if not review:
            return jsonify({'success': False, 'error': 'Plan not found'}), 404

        plan_data = editor.export_plan_for_final(plan_id)
        if not plan_data:
            return jsonify({'success': False, 'error': 'No content to export'}), 400

        # Recupera fonti
        plan_record = knowledge_manager.store.get_plan(plan_id)
        sources = []  # TODO: recuperare fonti salvate

        metadata = {
            'category': review.category,
            'credibility_score': sum(s.credibility_score for s in review.sections.values()) / len(review.sections) if review.sections else 0
        }

        files = {}

        if 'docx' in formats:
            docx_path = docx_exporter.create_document(
                plan_data=plan_data,
                club_name=review.club_name,
                sources=sources,
                metadata=metadata
            )
            files['docx'] = docx_path.name

        if 'html' in formats:
            html_path = html_exporter.export(
                plan_data=plan_data,
                club_name=review.club_name,
                sources=sources,
                metadata=metadata
            )
            files['html'] = html_path.name

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
    Esporta piano come pacchetto ZIP contenente PDF + DOCX + HTML.
    Singolo download, nessun popup blocker.
    Utilizza WeasyPrint per PDF di alta qualità.
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

        sources = []  # TODO: recuperare fonti salvate
        metadata = {
            'category': review.category,
            'credibility_score': sum(s.credibility_score for s in review.sections.values()) / len(review.sections) if review.sections else 0
        }

        # Crea una directory temporanea per i file
        temp_dir = tempfile.mkdtemp(prefix="export_")
        logger.info(f"Creata directory temporanea: {temp_dir}")

        safe_name = review.club_name.replace(" ", "_").replace("/", "_")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_filename = f"{safe_name}_PianoStrategico_{timestamp}"

        files_added = []

        # --- Generazione DOCX ---
        try:
            docx_exporter.output_dir = Path(temp_dir)
            docx_path = docx_exporter.create_document(
                plan_data=plan_data,
                club_name=review.club_name,
                sources=sources,
                metadata=metadata
            )
            files_added.append(('docx', docx_path))
            logger.info(f"DOCX generato: {docx_path}")
        except Exception as docx_error:
            logger.error(f"Errore generazione DOCX: {docx_error}", exc_info=True)

        # --- Generazione HTML ---
        html_content = None
        html_path = None
        try:
            html_content = _generate_printable_html(plan_data, review.club_name, sources, metadata)
            html_path = os.path.join(temp_dir, f"{base_filename}.html")
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            files_added.append(('html', html_path))
            logger.info(f"HTML generato: {html_path}")
        except Exception as html_error:
            logger.error(f"Errore generazione HTML: {html_error}", exc_info=True)

        # --- Generazione PDF da HTML ---
        if html_content:
            try:
                pdf_success = create_pdf_from_html(
                    html_content=html_content,
                    output_path=temp_dir,
                    plan_name=base_filename
                )
                if pdf_success:
                    pdf_path = os.path.join(temp_dir, f"{base_filename}.pdf")
                    files_added.append(('pdf', pdf_path))
                    logger.info(f"PDF generato: {pdf_path}")
                else:
                    logger.warning("Generazione PDF fallita")
            except Exception as pdf_error:
                logger.warning(f"Errore generazione PDF: {pdf_error}")

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

        # Copia lo ZIP nella directory output permanente prima di inviarlo
        final_zip_path = OUTPUT_DIR / f"{zip_filename_base}.zip"
        shutil.copy2(zip_path, final_zip_path)
        logger.info(f"ZIP copiato in: {final_zip_path}")

        # Pulisci directory temporanea
        if temp_dir and os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
                logger.info(f"Directory temporanea rimossa: {temp_dir}")
            except Exception as cleanup_error:
                logger.warning(f"Impossibile rimuovere dir temporanea: {cleanup_error}")

        # Invia file ZIP dalla directory output
        return send_file(
            final_zip_path,
            mimetype='application/zip',
            as_attachment=True,
            download_name=f"{zip_filename_base}.zip"
        )

    except Exception as e:
        logger.exception(f"Package export error: {e}")
        # Pulisci in caso di errore
        if temp_dir and os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
            except:
                pass
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/export/<plan_id>/html', methods=['GET'])
def api_export_html_only(plan_id: str):
    """
    Esporta piano in formato HTML con funzionalità di stampa integrata.
    L'utente può stampare in PDF direttamente dal browser (Ctrl+P -> Salva come PDF).
    """
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

        # Genera HTML con print button
        html_content = _generate_printable_html(plan_data, review.club_name, sources, metadata)

        safe_name = review.club_name.replace(" ", "_").replace("/", "_")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{safe_name}_PianoStrategico_{timestamp}.html"

        # Salva in OUTPUT_DIR per download
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
    category = metadata.get('category', '')
    credibility = metadata.get('credibility_score', 0)

    # Colori del club (guerrilla marketing: identità visiva)
    primary_color = metadata.get('primary_color', '#1a365d')
    secondary_color = metadata.get('secondary_color', '#ffffff')

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

        /* Print Styles */
        @media print {{
            .print-bar, .nav {{
                display: none !important;
            }}

            .header {{
                margin-top: 0;
                padding: 50px 20px;
                -webkit-print-color-adjust: exact;
                print-color-adjust: exact;
            }}

            body {{
                background: white;
            }}

            .section {{
                break-inside: avoid;
                box-shadow: none;
                border: 1px solid #ddd;
                page-break-inside: avoid;
            }}

            .section-header {{
                -webkit-print-color-adjust: exact;
                print-color-adjust: exact;
            }}

            .container {{
                padding: 20px;
                max-width: none;
            }}

            .footer {{
                -webkit-print-color-adjust: exact;
                print-color-adjust: exact;
            }}

            @page {{
                size: A4;
                margin: 1.5cm;
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

if __name__ == '__main__':
    # Verifica configurazione
    missing = get_missing_config()
    if missing:
        print(f"WARNING: Missing config: {missing}")
        print("Some features may not work correctly.")

    # Assicura directories
    OUTPUT_DIR.mkdir(exist_ok=True)
    KNOWLEDGE_DIR.mkdir(exist_ok=True)

    print("""
    ===============================================================
    |                                                             |
    |     ROOTING FUTURE STRATEGY ENGINE v5.4 (Production Mode)   |
    |     Server starting on http://127.0.0.1:5000                |
    |                                                             |
    ===============================================================
    """)
    
    from waitress import serve
    serve(app, host='0.0.0.0', port=5000)
