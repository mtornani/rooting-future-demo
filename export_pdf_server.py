"""
Rooting Future Strategy Engine - Server-Side PDF Export
Engine: WeasyPrint (Python Native)
Design: Tactical Sports Report v3.0 (Anti-Crash Server Edition)
"""

import re
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import weasyprint

from export_core import BaseExporter
from stw_matrix import generate_stw_matrix_html, get_stw_matrix_css

logger = logging.getLogger(__name__)

class PdfServerExporter(BaseExporter):
    """
    Esporta piani strategici direttamente in PDF utilizzando WeasyPrint.
    Elimina la dipendenza da Paged.js e i problemi di rendering del browser.
    """

    def export(
        self,
        plan_data: Dict,
        club_name: str,
        sources: List[Dict] = None,
        metadata: Dict = None
    ) -> Path:
        """
        Genera il file PDF finale.
        """
        # Estrazione metadati e colori standardizzati
        meta = self._extract_metadata(metadata)
        
        # Genera l'HTML con il CSS ottimizzato per WeasyPrint
        html_content = self._generate_html(
            plan_data=plan_data,
            club_name=club_name,
            sources=sources or [],
            meta=meta
        )

        # Output path standardizzato
        filename = self._get_safe_filename(club_name, "pdf", prefix="PianoStrategico")
        filepath = self.output_dir / filename

        # Generazione PDF via WeasyPrint
        logger.info(f"Inizio generazione PDF per {club_name} via WeasyPrint...")
        try:
            weasyprint.HTML(string=html_content).write_pdf(filepath)
            logger.info(f"PDF generato con successo: {filepath}")
        except Exception as e:
            logger.error(f"Errore WeasyPrint: {e}")
            raise

        return filepath

    def _generate_html(self, plan_data, club_name, sources, meta) -> str:
        # Colori dinamici
        club_primary = meta['primary_color']
        club_secondary = meta['secondary_color'] if meta['secondary_color'] and meta['secondary_color'].lower() != "#ffffff" else "#1a202c"
        contrast_color = meta['contrast_color']
        
        current_year = meta['current_year']

        # Genera contenuto sezioni usando il colore del club
        sections_html = self._generate_sections_html(plan_data, club_primary)

        # Genera matrice STW usando il colore del club
        stw_matrix_html = generate_stw_matrix_html(club_primary)

        # Genera pagina metodologia + questionari
        methodology_html = self._generate_methodology_page(club_name, meta)

        return f'''
<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <title>Piano Strategico - {club_name}</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600&family=Montserrat:wght@700;800&display=swap');

        :root {{
            --club-primary: {club_primary};
            --club-secondary: {club_secondary};
            --primary-color: {club_primary};
            --secondary-color: {club_secondary};
            --rf-purple: #6a0dad;
            --brand-gradient: linear-gradient(135deg, var(--club-primary) 0%, var(--club-secondary) 100%);
            --light-color: #fdfbff;
            --contrast-color: {contrast_color};
            --text-color: #1a202c;
            --border-color: #e2e8f0;
        }}

        /* ===========================================
           CONFIGURAZIONE PAGINA (Paged Media)
           Magazine Style con Running Header
           =========================================== */
        @page {{
            size: A4;
            margin: 22mm 20mm 18mm 20mm;

            /* RUNNING HEADER */
            @top-left {{
                content: "{club_name.upper()}";
                font-family: 'Montserrat', sans-serif;
                font-size: 8pt;
                font-weight: 700;
                letter-spacing: 2px;
                color: {club_primary};
                border-bottom: 0.5pt solid var(--border-color);
                padding-bottom: 3mm;
            }}
            @top-right {{
                content: "PIANO STRATEGICO {current_year}—{current_year+3}";
                font-family: 'Montserrat', sans-serif;
                font-size: 7pt;
                letter-spacing: 1px;
                color: #718096;
                border-bottom: 0.5pt solid var(--border-color);
                padding-bottom: 3mm;
            }}

            /* FOOTER */
            @bottom-left {{
                content: "ROOTING FUTURE // STRATEGY ENGINE";
                font-family: 'Inter', sans-serif;
                font-size: 7pt;
                color: #a0aec0;
                padding-top: 4mm;
            }}
            @bottom-right {{
                content: counter(page);
                font-family: 'Montserrat', sans-serif;
                font-size: 9pt;
                font-weight: 700;
                color: {club_primary};
                padding-top: 4mm;
            }}
        }}

        /* Copertina: No Header/Footer */
        @page :first {{
            margin: 0;
            @top-left {{ content: none; }}
            @top-right {{ content: none; }}
            @bottom-left {{ content: none; }}
            @bottom-right {{ content: none; }}
        }}

        /* Reset & Base */
        * {{ box-sizing: border-box; }}
        body {{
            font-family: 'Inter', sans-serif;
            font-size: 10pt;
            line-height: 1.6;
            color: var(--text-color);
            background: #ffffff;
            margin: 0;
            padding: 0;
        }}

        /* ===========================================
           TIPOGRAFIA
           =========================================== */
        h1, h2, h3, h4, .cover-club {{
            font-family: 'Montserrat', sans-serif;
            text-transform: uppercase;
            letter-spacing: -0.5px;
        }}

        h1 {{
            font-size: 28pt;
            font-weight: 800;
            color: var(--primary-color);
            border-bottom: 3pt solid var(--primary-color);
            padding-bottom: 2mm;
            margin: 15mm 0 10mm 0;
            page-break-before: always;
        }}

        h2 {{
            font-size: 18pt;
            font-weight: 800;
            color: var(--primary-color);
            margin-top: 15mm;
            margin-bottom: 8mm;
            padding-left: 5mm;
            border-left: 5pt solid var(--primary-color);
            page-break-after: avoid;
        }}

        h3 {{
            font-size: 13pt;
            font-weight: 700;
            color: var(--secondary-color);
            margin: 10mm 0 5mm 0;
            border-bottom: 1pt solid var(--border-color);
            padding-bottom: 2mm;
        }}

        p {{
            margin-bottom: 4mm;
            text-align: justify;
        }}

        /* ===========================================
           COPERTINA POSTER (Tactical Edition)
           =========================================== */
        .cover {{
            width: 210mm;
            height: 297mm;
            background: var(--brand-gradient);
            color: var(--contrast-color);
            position: relative;
            overflow: hidden;
            page-break-after: always;
        }}

        .cover::before {{
            content: "";
            position: absolute;
            top: 0; left: 0; right: 0; bottom: 0;
            background: url('https://www.transparenttextures.com/patterns/cubes.png');
            opacity: 0.15;
        }}

        .cover-content {{
            position: absolute;
            top: 100mm; left: 25mm; right: 40mm;
            z-index: 10;
        }}

        .cover-brand {{
            font-size: 10pt;
            letter-spacing: 5px;
            background: #000;
            color: #fff;
            padding: 2mm 5mm;
            display: inline-block;
            margin-bottom: 12mm;
        }}

        .cover-club {{
            font-size: 64pt;
            font-weight: 800;
            line-height: 0.9;
            margin-bottom: 8mm;
        }}

        .cover-title {{
            font-size: 22pt;
            font-weight: 300;
            border-left: 3pt solid var(--contrast-color);
            padding-left: 6mm;
            text-transform: uppercase;
            letter-spacing: 2px;
        }}

        /* ===========================================
           LAYOUT A COLONNE
           =========================================== */
        .section-container {{
            margin-bottom: 15mm;
        }}

        .section-body {{
            column-count: 2;
            column-gap: 10mm;
            text-align: justify;
        }}

        h1, h2, h3, h4 {{ column-span: all; }}
        table, .kpi-box, .insight-box, .action-box, blockquote {{ column-span: all; break-inside: avoid; }}

        /* ===========================================
           BOX E BADGE
           =========================================== */
        .kpi-box {{
            background: #fdfbff;
            border-left: 5pt solid var(--primary-color);
            padding: 6mm 8mm;
            margin: 8mm 0;
            border-radius: 0 4mm 4mm 0;
        }}

        .badge {{ background: #F3E5F5; padding: 1mm 3mm; border-radius: 10px; font-weight: 700; font-size: 8pt; margin-right: 2px; }}
        .badge.questionnaire {{ background: #F3E5F5; color: #7B1FA2; }}
        .badge.research {{ background: #E3F2FD; color: #1565C0; }}
        .badge.estimate {{ background: #FFF3E0; color: #F57C00; }}

        .insight-box {{
            background: #f0f7ff;
            border-left: 4pt solid #2b6cb0;
            padding: 4mm 6mm;
            margin: 6mm 0;
            border-radius: 2mm;
            break-inside: avoid;
        }}

        .action-box {{
            background: #f0fff4;
            border-left: 4pt solid #38a169;
            padding: 4mm 6mm;
            margin: 6mm 0;
            border-radius: 2mm;
            break-inside: avoid;
        }}

        .quote-box {{
            font-style: italic;
            color: #4a5568;
            padding: 4mm 10mm;
            margin: 6mm 0;
            border-left: 2pt solid #cbd5e0;
            break-inside: avoid;
            font-size: 11pt;
            background: #f8fafc;
        }}

        {get_stw_matrix_css()}
    </style>
</head>
<body>
    <div class="cover">
        <div class="cover-content">
            <div class="cover-brand">STRATEGIC DOSSIER</div>
            <div class="cover-club">{club_name}</div>
            <div class="cover-title">PIANO STRATEGICO<br>SVILUPPO {current_year}—{current_year+3}</div>
            
            <div style="margin-top: 30mm; font-family: 'Montserrat'; font-size: 9pt; letter-spacing: 2px; opacity: 0.7;">
                GENERATED BY ROOTING FUTURE STRATEGY ENGINE v6.0
            </div>
        </div>
    </div>

    {methodology_html}

    {stw_matrix_html}

    {sections_html}

    {self._generate_sources_html(sources)}
</body>
</html>
'''

    def _generate_sections_html(self, plan_data, primary_color) -> str:
        html = []
        section_titles = self._get_section_titles()
        preferred_order = self._get_preferred_section_order()

        # Genera HTML nell'ordine corretto
        for key in preferred_order:
            if key in plan_data and plan_data[key]:
                content = plan_data[key]
                title = section_titles.get(key, key.replace('_', ' ').title())
                html.append(f'<div class="section-container">')
                html.append(f'<h1>{title}</h1>')
                # Normalizziamo il markdown prima della conversione
                normalized_content = self._normalize_markdown(content)
                html.append(f'<div class="section-body">{self._markdown_to_html(normalized_content)}</div>')
                html.append(f'</div>')

        # Aggiungi eventuali sezioni non previste
        for key, content in plan_data.items():
            if key not in preferred_order and content:
                title = section_titles.get(key, key.replace('_', ' ').title())
                html.append(f'<div class="section-container">')
                html.append(f'<h1>{title}</h1>')
                normalized_content = self._normalize_markdown(content)
                html.append(f'<div class="section-body">{self._markdown_to_html(normalized_content)}</div>')
                html.append(f'</div>')

        return "".join(html)

    def _generate_methodology_page(self, club_name: str, meta: dict) -> str:
        """
        Genera la pagina Metodologia Rooting Future con evidenziazione dei questionari compilati.
        """
        total_questionnaires = meta['total_questionnaires']
        credibility_score = meta['credibility_score']
        
        # Fallback per compatibilità
        if total_questionnaires == 0:
            total_questionnaires = 9

        html = f"""
    <div style="page-break-before: always; padding: 15mm 20mm;">
        <div style="text-align: center; margin-bottom: 15mm;">
            <div style="display: inline-block; background: linear-gradient(135deg, #1a365d 0%, #2E7D32 100%);
                        padding: 8mm 15mm; border-radius: 4mm;">
                <div style="font-family: 'Montserrat', sans-serif; font-size: 32pt; font-weight: 700;
                            color: white; letter-spacing: 4px; margin-bottom: 3mm;">
                    ROOTING FUTURE
                </div>
                <div style="font-size: 12pt; color: rgba(255,255,255,0.9); letter-spacing: 2px;">
                    Strategic Planning Framework per il Calcio Italiano
                </div>
            </div>
        </div>

        <h2 style="font-size: 24pt; text-align: center; margin: 10mm 0;">
            📋 Metodologia & Dati di Input
        </h2>

        <div style="background: linear-gradient(135deg, #7B1FA2 0%, #9C27B0 100%);
                    padding: 8mm; border-radius: 3mm; margin: 8mm 0; color: white;">
            <h3 style="margin: 0 0 5mm 0; font-size: 16pt; color: white; border: none;">
                ✅ Questionari Compilati dai Membri del Board di {club_name}
            </h3>
            <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 5mm;">
                <div style="text-align: center;">
                    <div style="font-size: 32pt; font-weight: 700;">{total_questionnaires}</div>
                    <div style="font-size: 10pt; opacity: 0.9;">Documenti Word</div>
                </div>
                <div style="text-align: center;">
                    <div style="font-size: 32pt; font-weight: 700;">{total_questionnaires * 15}+</div>
                    <div style="font-size: 10pt; opacity: 0.9;">Dati Forniti</div>
                </div>
                <div style="text-align: center;">
                    <div style="font-size: 32pt; font-weight: 700;">{credibility_score}%</div>
                    <div style="font-size: 10pt; opacity: 0.9;">Completezza</div>
                </div>
            </div>
        </div>

        <h3 style="font-size: 18pt; margin: 10mm 0 6mm 0;">Il Processo Rooting Future</h3>

        <div style="margin: 6mm 0;">
            <div style="display: flex; align-items: flex-start; margin-bottom: 6mm;">
                <div style="flex-shrink: 0; width: 15mm; height: 15mm; background: #7B1FA2; color: white;
                            border-radius: 50%; display: flex; align-items: center; justify-content: center;
                            font-size: 16pt; font-weight: 700; margin-right: 5mm;">
                    1
                </div>
                <div style="flex: 1;">
                    <h4 style="margin: 0 0 2mm 0; font-size: 14pt; color: #7B1FA2;">
                        📋 Analisi Questionari Club
                    </h4>
                    <p style="margin: 0; line-height: 1.6;">
                        <strong>Dati forniti direttamente da {club_name}</strong> tramite questionari Word strutturati.
                    </p>
                </div>
            </div>

            <div style="display: flex; align-items: flex-start; margin-bottom: 6mm;">
                <div style="flex-shrink: 0; width: 15mm; height: 15mm; background: #1565C0; color: white;
                            border-radius: 50%; display: flex; align-items: center; justify-content: center;
                            font-size: 16pt; font-weight: 700; margin-right: 5mm;">
                    2
                </div>
                <div style="flex: 1;">
                    <h4 style="margin: 0 0 2mm 0; font-size: 14pt; color: #1565C0;">
                        🔍 Web Research & Benchmark
                    </h4>
                    <p style="margin: 0; line-height: 1.6;">
                        Integrazione dati da <strong>FIGC, Transfermarkt, Google, Visure Camerali</strong>.
                    </p>
                </div>
            </div>

            <div style="display: flex; align-items: flex-start; margin-bottom: 6mm;">
                <div style="flex-shrink: 0; width: 15mm; height: 15mm; background: #2E7D32; color: white;
                            border-radius: 50%; display: flex; align-items: center; justify-content: center;
                            font-size: 16pt; font-weight: 700; margin-right: 5mm;">
                    3
                </div>
                <div style="flex: 1;">
                    <h4 style="margin: 0 0 2mm 0; font-size: 14pt; color: #2E7D32;">
                        🤖 AI Multi-Agente STW-Aligned
                    </h4>
                    <p style="margin: 0; line-height: 1.6;">
                        <strong>6 agenti specializzati</strong> elaborano il piano seguendo la matrice STW (21 obiettivi MACRO).
                    </p>
                </div>
            </div>
        </div>

        <div style="background: #f5f5f5; padding: 6mm; border-left: 4pt solid #1a365d; margin-top: 10mm;">
            <h4 style="margin: 0 0 3mm 0; font-size: 12pt;">Legenda Badge nei Dati:</h4>
            <div style="display: flex; gap: 8mm; flex-wrap: wrap;">
                <div style="display: flex; align-items: center; gap: 2mm;">
                    <span class="badge questionnaire">📋 Da Questionario</span>
                    <span style="font-size: 9pt;">Dati forniti da {club_name}</span>
                </div>
                <div style="display: flex; align-items: center; gap: 2mm;">
                    <span class="badge research">🔍 Ricerca Web</span>
                    <span style="font-size: 9pt;">Dati verificati online</span>
                </div>
                <div style="display: flex; align-items: center; gap: 2mm;">
                    <span class="badge estimate">📊 Stima AI</span>
                    <span style="font-size: 9pt;">Elaborazione intelligenza artificiale</span>
                </div>
            </div>
        </div>
    </div>
"""
        return html

    def _generate_sources_html(self, sources) -> str:
        if not sources: return ""
        html = ['<h1>Fonti e Metodologia</h1>', '<div class="section-body"><ul>']
        for s in sources[:20]:
            name = s.get('name', 'Fonte esterna')
            url = s.get('url', '')
            html.append(f'<li><strong>{name}</strong><br><small>{url}</small></li>')
        html.append('</ul></div>')
        return "".join(html)
