# Rooting Future Strategy Engine v5.4 - Gemini Context

## Project Overview
**Rooting Future Strategy Engine** is a multi-agent AI system designed to generate 3-year strategic plans for Italian football clubs. It leverages **Google Gemini 2.0 Flash** to analyze club data, perform web research, and generate professional documents with scientific data validation.

The system addresses the need for objective, benchmarked strategic planning in football management, moving beyond generic AI outputs to provide verified data points and actionable insights.

## Technology Stack
*   **Backend:** Python 3.11+ with Flask (Web Framework)
*   **AI Engine:** Google Gemini 2.0 Flash (via `google-generativeai`)
*   **Database:** SQLite + JSON based Knowledge Base
*   **Frontend:** HTML/CSS/JS (Vanilla) with Jinja2 Templates
*   **Export:** `python-docx` (Word), Custom HTML, `xhtml2pdf`/`kaleido` (PDF/Charts)
*   **Production:** Waitress WSGI server

## Project Structure

### Core Application
*   `app.py`: Main Flask application entry point. Handles routing and API endpoints.
*   `config.py`: Configuration settings (API keys, paths).
*   `agents.py`: Implements the multi-agent system logic (8 specialized agents).
*   `web_research.py`: Handles automated web research using search APIs.
*   `knowledge_store.py`: Manages the knowledge base and learning mechanisms.

### Data & Validation (New "Scientific" System)
*   `data_models.py`: Defines structured data classes (`DataPoint`, `Benchmark`, etc.) for validated outputs.
*   `structured_agent.py`: Agents designed to output structured JSON data instead of free text.
*   `structured_renderer.py`: Renders structured data into professional HTML reports with credibility dashboards.
*   `stw_matrix.py`: Likely related to SWOT analysis or similar strategic matrices.

### Export Modules
*   `export_docx.py`: Generates professional DOCX reports.
*   `export_html.py`: Generates single and multi-page HTML reports.
*   `export_pdf.py`: (In Development/Existing) Module for PDF generation.
*   `export_package.py`: Handles packaging exports (likely ZIP creation).

### Directories
*   `templates/`: Jinja2 HTML templates for the web interface.
*   `static/`: CSS, JavaScript, and images.
*   `output/`: Destination for generated reports and strategy packs.
*   `knowledge_base/`: Stores research results (`.json`) and database (`.db`).
*   `venv/`: Python virtual environment.

## Setup and Execution

**Prerequisites:** Python 3.11+, Virtual Environment.

1.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

2.  **Run Application:**
    *   **Windows (PowerShell):** `./start.ps1`
    *   **Windows (Batch):** `start.bat`
    *   **Manual:**
        ```bash
        # Activate venv
        python app.py
        ```

3.  **Access:** The web interface is available at `http://localhost:5000`.

## Key Workflows

1.  **Plan Generation:**
    *   User inputs club data via the web form.
    *   `web_research.py` gathers external context.
    *   `agents.py` (or `structured_agent.py`) generates content for specific sections (Sporting, Youth, Finance, Marketing, etc.).
    *   `post_production_editor.py` handles review and refinement.
    *   Final output is exported to DOCX/HTML/ZIP.

2.  **Structured Data Pipeline:**
    *   Aims to replace generic text with `DataPoint` objects.
    *   Classifies data as `VERIFIED`, `BENCHMARK`, `ESTIMATE`, etc.
    *   Calculates deviation from benchmarks and assigns confidence levels.

## Current Development Goals
*   **Frontend Modernization:** Transitioning from vanilla JS/Jinja2 to a more modern UX (evaluating React/Vue vs. HTMX).
*   **Export Improvements:**
    *   Adding robust PDF export.
    *   Solving browser popup blocking issues (likely moving to server-side ZIP generation).
    *   Improving the visual quality of reports.
*   **Integration:** Fully integrating the new `structured_*` scientific validation system into the main application flow.

## Development Conventions
*   **Code Style:** Pythonic, using type hinting where possible (especially in new modules like `data_models.py`).
*   **Templates:** Jinja2 for server-side rendering.
*   **Storage:** File-based JSON for research cache, SQLite for structured app data.
