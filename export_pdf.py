# rooting_future/export_pdf.py

import logging
from pathlib import Path
from bs4 import BeautifulSoup
import io
import re
from datetime import datetime

logger = logging.getLogger(__name__)

# Prova WeasyPrint (preferito) o xhtml2pdf come fallback
WEASYPRINT_AVAILABLE = False
PISA_AVAILABLE = False

try:
    from weasyprint import HTML, CSS
    WEASYPRINT_AVAILABLE = True
    logger.info("WeasyPrint disponibile per generazione PDF")
except ImportError:
    logger.warning("WeasyPrint non disponibile, provo xhtml2pdf...")
    try:
        from xhtml2pdf import pisa
        PISA_AVAILABLE = True
        logger.info("xhtml2pdf disponibile come fallback per PDF")
    except ImportError:
        logger.warning("Nessun generatore PDF disponibile")


# CSS professionale per PDF
PDF_CSS = '''
@page {
    size: A4;
    margin: 2cm 2.5cm;
    @bottom-center {
        content: "Pagina " counter(page) " di " counter(pages);
        font-size: 9pt;
        color: #718096;
    }
}

body {
    font-family: "Segoe UI", Calibri, Arial, sans-serif;
    font-size: 11pt;
    line-height: 1.6;
    color: #2d3748;
}

/* Header styles */
h1 {
    font-size: 22pt;
    color: #1a365d;
    border-bottom: 3px solid #3182ce;
    padding-bottom: 12px;
    margin: 30px 0 20px 0;
    page-break-after: avoid;
}

h2 {
    font-size: 16pt;
    color: #2c5282;
    margin: 25px 0 15px 0;
    padding-top: 15px;
    border-top: 1px solid #e2e8f0;
    page-break-after: avoid;
}

h3 {
    font-size: 13pt;
    color: #3182ce;
    margin: 20px 0 12px 0;
    page-break-after: avoid;
}

h4 {
    font-size: 11pt;
    color: #4a5568;
    font-weight: bold;
    margin: 15px 0 8px 0;
    page-break-after: avoid;
}

/* Paragraphs */
p {
    margin: 0 0 12px 0;
    text-align: justify;
    orphans: 3;
    widows: 3;
}

/* Lists */
ul, ol {
    margin: 12px 0 12px 25px;
    padding: 0;
}

li {
    margin-bottom: 6px;
}

/* Tables */
table {
    width: 100%;
    border-collapse: collapse;
    margin: 15px 0;
    font-size: 10pt;
    page-break-inside: avoid;
}

th, td {
    border: 1px solid #cbd5e0;
    padding: 10px 12px;
    text-align: left;
}

th {
    background-color: #1a365d;
    color: white;
    font-weight: 600;
    text-transform: uppercase;
    font-size: 9pt;
}

tr:nth-child(even) {
    background-color: #f7fafc;
}

/* Special boxes */
.kpi-box, .info-box {
    background: linear-gradient(135deg, #ebf8ff, #e6fffa);
    border-left: 4px solid #3182ce;
    padding: 15px 20px;
    margin: 15px 0;
    page-break-inside: avoid;
}

blockquote {
    border-left: 4px solid #3182ce;
    padding: 12px 20px;
    margin: 15px 0;
    background: #f7fafc;
    font-style: italic;
    color: #4a5568;
}

/* Section */
.section {
    page-break-inside: avoid;
    margin-bottom: 25px;
}

/* Strong and emphasis */
strong, b {
    font-weight: 600;
    color: #1a365d;
}

em, i {
    font-style: italic;
}

/* Header for cover */
.header {
    text-align: center;
    padding: 60px 0;
    page-break-after: always;
}

.header h1 {
    font-size: 28pt;
    border: none;
    margin-bottom: 10px;
}

/* Navigation (hide in print) */
.nav {
    display: none;
}

/* Footer (hide, we use @page) */
.footer {
    display: none;
}

/* Sources */
.sources-section {
    background: #f8fafc;
    padding: 20px;
    margin-top: 30px;
}

.sources-list a {
    color: #3182ce;
    text-decoration: none;
}

.disclaimer {
    font-size: 9pt;
    color: #718096;
    font-style: italic;
    margin-top: 20px;
    padding-top: 15px;
    border-top: 1px solid #e2e8f0;
}
'''


def create_pdf_from_html(html_content: str, output_path: str, plan_name: str) -> bool:
    """
    Genera un PDF da HTML usando WeasyPrint (preferito) o xhtml2pdf.

    Args:
        html_content: Contenuto HTML completo
        output_path: Directory dove salvare il PDF
        plan_name: Nome del file (senza estensione)

    Returns:
        True se il PDF è stato generato con successo
    """
    # Validazione input
    if html_content is None:
        logger.error("html_content è None - impossibile generare PDF")
        return False

    if not isinstance(html_content, str):
        logger.error(f"html_content non è una stringa, tipo: {type(html_content)}")
        return False

    if not html_content.strip():
        logger.error("html_content è vuoto - impossibile generare PDF")
        return False

    pdf_filename = Path(output_path) / f"{plan_name}.pdf"
    logger.info(f"Generazione PDF: {pdf_filename}")

    # Pulisci e prepara HTML
    clean_html = _prepare_html_for_pdf(html_content)

    if WEASYPRINT_AVAILABLE:
        return _generate_with_weasyprint(clean_html, pdf_filename)
    elif PISA_AVAILABLE:
        return _generate_with_xhtml2pdf(clean_html, pdf_filename)
    else:
        logger.error("Nessun generatore PDF disponibile (installa weasyprint o xhtml2pdf)")
        return False


def _prepare_html_for_pdf(html_content: str) -> str:
    """Prepara l'HTML per la conversione PDF rimuovendo elementi problematici."""
    try:
        soup = BeautifulSoup(html_content, 'html.parser')

        # Rimuovi script, noscript, iframe
        for tag in soup.find_all(['script', 'noscript', 'iframe']):
            tag.decompose()

        # Rimuovi style tags interni (useremo il nostro CSS)
        for tag in soup.find_all('style'):
            tag.decompose()

        # Rimuovi navigazione
        for tag in soup.find_all(class_='nav'):
            tag.decompose()

        # Rimuovi footer originale
        for tag in soup.find_all('footer'):
            tag.decompose()
        for tag in soup.find_all(class_='footer'):
            tag.decompose()

        # === RIMUOVI ELEMENTI UI INTERATTIVI ===
        # Barra di stampa
        for tag in soup.find_all(class_='print-bar'):
            tag.decompose()

        # Modali
        for tag in soup.find_all(class_='modal'):
            tag.decompose()
        for tag in soup.find_all(class_='dashboard-modal'):
            tag.decompose()

        # Bottoni
        for tag in soup.find_all('button'):
            tag.decompose()
        for tag in soup.find_all(class_='btn'):
            tag.decompose()

        # Hint interattivi
        for tag in soup.find_all(class_='expand-hint'):
            tag.decompose()
        for tag in soup.find_all(class_='click-hint'):
            tag.decompose()
        for tag in soup.find_all(class_='card-click-hint'):
            tag.decompose()
        for tag in soup.find_all(class_='card-expand-icon'):
            tag.decompose()

        return str(soup)
    except Exception as e:
        logger.warning(f"Errore pulizia HTML: {e}, uso HTML originale")
        return html_content


def _generate_with_weasyprint(html_content: str, output_path: Path) -> bool:
    """Genera PDF usando WeasyPrint (alta qualità)."""
    try:
        logger.info("Generazione PDF con WeasyPrint...")

        # Crea documento con CSS personalizzato
        html_doc = HTML(string=html_content)
        css = CSS(string=PDF_CSS)

        # Genera PDF
        html_doc.write_pdf(str(output_path), stylesheets=[css])

        # Verifica
        if output_path.exists() and output_path.stat().st_size > 0:
            logger.info(f"PDF generato con WeasyPrint: {output_path} ({output_path.stat().st_size} bytes)")
            return True
        else:
            logger.error("PDF generato ma file vuoto o non esistente")
            return False

    except Exception as e:
        logger.error(f"Errore WeasyPrint: {e}", exc_info=True)
        return False


def _generate_with_xhtml2pdf(html_content: str, output_path: Path) -> bool:
    """Genera PDF usando xhtml2pdf (fallback)."""
    try:
        logger.info("Generazione PDF con xhtml2pdf...")

        # xhtml2pdf richiede un HTML molto pulito
        soup = BeautifulSoup(html_content, 'html.parser')

        # Estrai body
        body = soup.find('body')
        if body:
            body_content = str(body)
        else:
            body_content = str(soup)

        # HTML minimale per xhtml2pdf
        simple_html = f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        @page {{ size: A4; margin: 2cm; }}
        body {{ font-family: Helvetica, Arial, sans-serif; font-size: 11pt; line-height: 1.5; color: #333; }}
        h1 {{ font-size: 20pt; color: #1a365d; border-bottom: 2px solid #3182ce; padding-bottom: 10px; }}
        h2 {{ font-size: 16pt; color: #2c5282; margin-top: 25px; }}
        h3 {{ font-size: 13pt; color: #3182ce; margin-top: 20px; }}
        h4 {{ font-size: 11pt; color: #4a5568; margin-top: 15px; }}
        p {{ margin-bottom: 10px; text-align: justify; }}
        ul, ol {{ margin-left: 20px; margin-bottom: 15px; }}
        li {{ margin-bottom: 5px; }}
        table {{ width: 100%; border-collapse: collapse; margin: 15px 0; }}
        th, td {{ border: 1px solid #e2e8f0; padding: 8px; text-align: left; }}
        th {{ background-color: #edf2f7; font-weight: bold; }}
        strong {{ font-weight: bold; }}
    </style>
</head>
{body_content}
</html>'''

        with open(output_path, "w+b") as result_file:
            pisa_status = pisa.CreatePDF(simple_html, dest=result_file, encoding='utf-8')

        if pisa_status.err:
            logger.error(f"Errore xhtml2pdf: {pisa_status.err}")
            return False

        if output_path.exists() and output_path.stat().st_size > 0:
            logger.info(f"PDF generato con xhtml2pdf: {output_path} ({output_path.stat().st_size} bytes)")
            return True
        else:
            logger.error("PDF generato ma file vuoto")
            return False

    except Exception as e:
        logger.error(f"Errore xhtml2pdf: {e}", exc_info=True)
        return False


def get_pdf_generator_info() -> dict:
    """Restituisce info sul generatore PDF disponibile."""
    return {
        'weasyprint_available': WEASYPRINT_AVAILABLE,
        'xhtml2pdf_available': PISA_AVAILABLE,
        'preferred': 'weasyprint' if WEASYPRINT_AVAILABLE else ('xhtml2pdf' if PISA_AVAILABLE else None)
    }
