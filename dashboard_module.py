"""
Dashboard Strategica Module
Genera la matrice visuale con le 4 aree strategiche e obiettivi MACRO/MICRO.
"""
import re


def _extract_objectives_from_content(content: str) -> dict:
    """
    Estrae obiettivi MACRO e MICRO dal contenuto.

    Formati supportati:
    - MACRO: ## 1. TITOLO, ### 1. TITOLO, **1. TITOLO**
    - MICRO: ### 1.1 TITOLO, #### 1.1 TITOLO, **1.1 TITOLO**, * **1.1 TITOLO**
    """
    objectives = {'macro': [], 'micro': []}
    if not content:
        return objectives

    # Pattern per MACRO: ## N. TITOLO o ### N. TITOLO o **N. TITOLO**
    # Più permissivo: cerca numeri seguiti da punto e testo
    macro_patterns = [
        r'#{2,3}\s*(\d+)\.\s*([A-Z][A-Za-z\s\-\(\)]+?)(?:\n|$)',  # ## 1. TITOLO
        r'\*\*(\d+)\.\s*([A-Z][A-Za-z\s\-\(\)]+?)\*\*',  # **1. TITOLO**
        r'^#{2,3}\s*([A-Z][A-Z\s\-]+)$',  # ## OBIETTIVI SPORTIVI (senza numero)
    ]

    # Pattern per MICRO: ### N.N TITOLO o #### N.N TITOLO o **N.N TITOLO**
    micro_patterns = [
        r'#{3,4}\s*(\d+\.\d+)\s*([A-Z][A-Za-z\s\-\(\):]+?)(?:\n|$)',  # ### 1.1 TITOLO
        r'\*\*(\d+\.\d+)\s*([A-Z][A-Za-z\s\-\(\):]+?)\*\*',  # **1.1 TITOLO**
        r'\*\s*\*\*(\d+\.\d+)\s*([A-Z][A-Za-z\s\-\(\):]+?)\*\*',  # * **1.1 TITOLO**
    ]

    seen_macro = set()
    for pattern in macro_patterns:
        for match in re.finditer(pattern, content, re.MULTILINE):
            groups = match.groups()
            if len(groups) == 2:
                num, title = groups
            else:
                num = str(len(seen_macro) + 1)
                title = groups[0]
            title = title.strip().title()
            # NON troncare in Python - lascia testo completo
            key = f"{num}_{title[:20]}"
            if key not in seen_macro:
                seen_macro.add(key)
                objectives['macro'].append({'num': num, 'title': title})

    seen_micro = set()
    for pattern in micro_patterns:
        for match in re.finditer(pattern, content, re.MULTILINE):
            num, title = match.groups()
            title = title.strip().title()
            # NON troncare in Python - lascia testo completo
            key = f"{num}_{title[:20]}"
            if key not in seen_micro:
                seen_micro.add(key)
                objectives['micro'].append({'num': num, 'title': title})

    return objectives


def _darken_color_local(hex_color: str, factor: float = 0.2) -> str:
    """Scurisce un colore."""
    hex_color = hex_color.lstrip('#')
    r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    r = int(r * (1 - factor))
    g = int(g * (1 - factor))
    b = int(b * (1 - factor))
    return f'#{r:02x}{g:02x}{b:02x}'


def generate_strategic_dashboard(plan_data: dict, primary_color: str, secondary_color: str) -> str:
    """
    Genera la Dashboard Strategica con matrice visuale delle 4 aree.

    Args:
        plan_data: Dict con i contenuti delle sezioni del piano
        primary_color: Colore primario del club (hex)
        secondary_color: Colore secondario del club (hex)

    Returns:
        HTML della dashboard strategica
    """
    # Valori di default per evitare None
    if not primary_color or not isinstance(primary_color, str):
        primary_color = '#1a365d'
    if not secondary_color or not isinstance(secondary_color, str):
        secondary_color = '#ffffff'
    if not plan_data:
        plan_data = {}

    # Definizione delle 4 aree strategiche
    areas = [
        {'key': 'technical_sporting', 'title': 'SPORTIVI', 'icon': '⚽', 'color': '#2E7D32'},
        {'key': 'infrastructure', 'title': 'STRUTTURALI', 'icon': '🏗️', 'color': '#1565C0'},
        {'key': 'marketing_commercial', 'title': 'MARKETING', 'icon': '📈', 'color': '#F57C00'},
        {'key': 'social_sustainability', 'title': 'SOCIALI', 'icon': '🤝', 'color': '#7B1FA2'}
    ]

    area_cards = ""
    modals_html = ""

    for area in areas:
        content = plan_data.get(area['key'], '') or ''
        if not isinstance(content, str):
            content = ''
        objectives = _extract_objectives_from_content(content)

        modal_id = f"dashboard-modal-{area['key']}"

        # Preview: max 4 items per la card (troncamento CSS solo su schermo)
        macro_preview = ""
        for obj in objectives['macro'][:4]:
            macro_preview += f'<div class="obj-item obj-macro truncate-screen"><span class="obj-num">{obj["num"]}</span><span class="obj-text">{obj["title"]}</span></div>'

        micro_preview = ""
        for obj in objectives['micro'][:4]:
            micro_preview += f'<div class="obj-item obj-micro truncate-screen"><span class="obj-num">{obj["num"]}</span><span class="obj-text">{obj["title"]}</span></div>'

        # Full content per modal (senza troncamento)
        macro_full = ""
        for obj in objectives['macro']:
            macro_full += f'<div class="obj-item obj-macro"><span class="obj-num">{obj["num"]}</span>{obj["title"]}</div>'

        micro_full = ""
        for obj in objectives['micro']:
            micro_full += f'<div class="obj-item obj-micro"><span class="obj-num">{obj["num"]}</span>{obj["title"]}</div>'

        if not macro_preview and not micro_preview:
            macro_preview = '<div class="obj-item obj-empty">Obiettivi in definizione</div>'

        # Card cliccabile
        area_cards += f'''
        <div class="area-card clickable-card" style="border-top-color: {area['color']}" onclick="openDashboardModal('{modal_id}')">
            <div class="area-header" style="background: {area['color']}">
                <span class="area-icon">{area['icon']}</span>
                <span class="area-title">{area['title']}</span>
                <span class="card-expand-icon">🔍</span>
            </div>
            <div class="area-content">
                <div class="obj-section">
                    <div class="obj-label obj-label-macro">MACRO</div>
                    {macro_preview}
                </div>
                <div class="obj-section">
                    <div class="obj-label obj-label-micro">MICRO</div>
                    {micro_preview}
                </div>
            </div>
            <div class="card-click-hint">Clicca per espandere</div>
        </div>'''

        # Modal con contenuto completo
        modals_html += f'''
        <div id="{modal_id}" class="dashboard-modal">
            <div class="dashboard-modal-content" style="border-top: 5px solid {area['color']};">
                <span class="dashboard-modal-close" onclick="closeDashboardModal('{modal_id}')">&times;</span>
                <div class="dashboard-modal-header" style="background: {area['color']};">
                    <span class="modal-area-icon">{area['icon']}</span>
                    <h2>{area['title']}</h2>
                </div>
                <div class="dashboard-modal-body">
                    <div class="modal-obj-section">
                        <h3><span class="obj-label obj-label-macro">OBIETTIVI MACRO</span></h3>
                        {macro_full if macro_full else '<p class="no-obj">Nessun obiettivo macro definito</p>'}
                    </div>
                    <div class="modal-obj-section">
                        <h3><span class="obj-label obj-label-micro">OBIETTIVI MICRO</span></h3>
                        {micro_full if micro_full else '<p class="no-obj">Nessun obiettivo micro definito</p>'}
                    </div>
                </div>
            </div>
        </div>
        '''

    dark_primary = _darken_color_local(primary_color, 0.15)

    dashboard = f'''
    <section class="section dashboard-section" id="strategic_dashboard">
        <div class="section-header dashboard-header">
            <span class="section-number">00</span>
            <h2><span class="section-icon">🎯</span> Dashboard Strategica</h2>
        </div>
        <div class="dashboard-intro">
            <p>Metodologia <strong>Macro-Micro</strong>: ogni area strategica è articolata in obiettivi
            <span class="badge-macro">MACRO</span> (traguardi triennali) e
            <span class="badge-micro">MICRO</span> (azioni operative immediate).</p>
        </div>
        <div class="strategic-matrix">
            {area_cards}
        </div>
        <style>
            .dashboard-section {{
                background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
            }}
            .dashboard-header {{
                background: linear-gradient(135deg, {primary_color}, {dark_primary}) !important;
            }}
            .dashboard-intro {{
                padding: 20px 30px;
                background: white;
                border-left: 4px solid {primary_color};
                margin: 0 30px 25px;
                border-radius: 0 8px 8px 0;
            }}
            .dashboard-intro p {{
                margin: 0;
                color: #4a5568;
                font-size: 0.95rem;
            }}
            .badge-macro {{
                background: #C8E6C9;
                color: #2E7D32;
                padding: 2px 8px;
                border-radius: 4px;
                font-weight: 600;
                font-size: 0.85rem;
            }}
            .badge-micro {{
                background: #FFF9C4;
                color: #F57F17;
                padding: 2px 8px;
                border-radius: 4px;
                font-weight: 600;
                font-size: 0.85rem;
            }}
            .strategic-matrix {{
                display: grid;
                grid-template-columns: repeat(4, 1fr);
                gap: 20px;
                padding: 0 30px 30px;
            }}
            .area-card {{
                background: white;
                border-radius: 12px;
                box-shadow: 0 4px 15px rgba(0,0,0,0.08);
                overflow: hidden;
                border-top: 4px solid;
                transition: transform 0.2s, box-shadow 0.2s;
            }}
            .area-card:hover {{
                transform: translateY(-3px);
                box-shadow: 0 8px 25px rgba(0,0,0,0.12);
            }}
            .area-header {{
                padding: 15px;
                color: white;
                display: flex;
                align-items: center;
                gap: 10px;
            }}
            .area-icon {{
                font-size: 1.5rem;
            }}
            .area-title {{
                font-weight: 700;
                font-size: 0.9rem;
                letter-spacing: 1px;
            }}
            .area-content {{
                padding: 15px;
            }}
            .obj-section {{
                margin-bottom: 15px;
            }}
            .obj-section:last-child {{
                margin-bottom: 0;
            }}
            .obj-label {{
                font-size: 0.7rem;
                font-weight: 700;
                letter-spacing: 1px;
                padding: 4px 8px;
                border-radius: 4px;
                display: inline-block;
                margin-bottom: 8px;
            }}
            .obj-label-macro {{
                background: #C8E6C9;
                color: #2E7D32;
            }}
            .obj-label-micro {{
                background: #FFF9C4;
                color: #F57F17;
            }}
            .obj-item {{
                padding: 8px 10px;
                border-radius: 6px;
                margin-bottom: 6px;
                font-size: 0.8rem;
                display: flex;
                align-items: flex-start;
                gap: 8px;
            }}
            .obj-item:last-child {{
                margin-bottom: 0;
            }}
            .obj-macro {{
                background: #E8F5E9;
                border-left: 3px solid #4CAF50;
            }}
            .obj-micro {{
                background: #FFFDE7;
                border-left: 3px solid #FFC107;
            }}
            .obj-empty {{
                background: #f5f5f5;
                color: #9e9e9e;
                font-style: italic;
                border-left: 3px solid #e0e0e0;
            }}
            .obj-num {{
                background: rgba(0,0,0,0.1);
                padding: 2px 6px;
                border-radius: 4px;
                font-weight: 700;
                font-size: 0.75rem;
                flex-shrink: 0;
            }}
            .obj-text {{
                flex: 1;
                min-width: 0;
            }}
            /* Troncamento CSS solo su schermo */
            .obj-item.truncate-screen .obj-text {{
                white-space: nowrap;
                overflow: hidden;
                text-overflow: ellipsis;
            }}

            /* === CLICKABLE CARDS === */
            .clickable-card {{
                cursor: pointer;
            }}
            .card-expand-icon {{
                margin-left: auto;
                font-size: 1rem;
                opacity: 0.5;
            }}
            .clickable-card:hover .card-expand-icon {{
                opacity: 1;
            }}
            .card-click-hint {{
                text-align: center;
                font-size: 0.7rem;
                color: #999;
                padding: 8px;
                border-top: 1px solid #eee;
                font-style: italic;
            }}

            /* === DASHBOARD MODAL === */
            .dashboard-modal {{
                display: none;
                position: fixed;
                z-index: 2000;
                left: 0;
                top: 0;
                width: 100%;
                height: 100%;
                background-color: rgba(0,0,0,0.6);
                backdrop-filter: blur(3px);
            }}
            .dashboard-modal.active {{
                display: flex;
                align-items: center;
                justify-content: center;
            }}
            .dashboard-modal-content {{
                background: white;
                width: 90%;
                max-width: 600px;
                max-height: 80vh;
                border-radius: 12px;
                overflow: hidden;
                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                animation: dashModalSlideIn 0.3s ease;
            }}
            @keyframes dashModalSlideIn {{
                from {{ opacity: 0; transform: translateY(-30px) scale(0.95); }}
                to {{ opacity: 1; transform: translateY(0) scale(1); }}
            }}
            .dashboard-modal-close {{
                position: absolute;
                right: 15px;
                top: 10px;
                font-size: 28px;
                font-weight: bold;
                color: white;
                cursor: pointer;
                z-index: 10;
                text-shadow: 0 1px 3px rgba(0,0,0,0.3);
            }}
            .dashboard-modal-close:hover {{
                color: #eee;
            }}
            .dashboard-modal-header {{
                padding: 20px 25px;
                color: white;
                display: flex;
                align-items: center;
                gap: 15px;
                position: relative;
            }}
            .modal-area-icon {{
                font-size: 2rem;
            }}
            .dashboard-modal-header h2 {{
                margin: 0;
                font-size: 1.4rem;
                font-weight: 700;
                letter-spacing: 1px;
            }}
            .dashboard-modal-body {{
                padding: 25px;
                max-height: 55vh;
                overflow-y: auto;
            }}
            .modal-obj-section {{
                margin-bottom: 20px;
            }}
            .modal-obj-section:last-child {{
                margin-bottom: 0;
            }}
            .modal-obj-section h3 {{
                margin-bottom: 12px;
            }}
            .no-obj {{
                color: #999;
                font-style: italic;
            }}

            @media (max-width: 1024px) {{
                .strategic-matrix {{
                    grid-template-columns: repeat(2, 1fr);
                }}
            }}
            @media (max-width: 600px) {{
                .strategic-matrix {{
                    grid-template-columns: 1fr;
                }}
            }}
            /* ================================================================
               PRINT STYLES - Dashboard Strategica
               ================================================================ */
            @media print {{
                /* === NASCONDI ELEMENTI INTERATTIVI === */
                .dashboard-modal,
                .card-click-hint,
                .card-expand-icon {{
                    display: none !important;
                }}

                /* === FORZA COLORI STAMPA === */
                * {{
                    -webkit-print-color-adjust: exact !important;
                    print-color-adjust: exact !important;
                }}

                /* === DASHBOARD SECTION === */
                .dashboard-section {{
                    background: white !important;
                    break-after: page;
                    page-break-after: always;
                }}

                .dashboard-intro {{
                    break-after: avoid;
                    page-break-after: avoid;
                }}

                /* === GRIGLIA 2x2 PER STAMPA === */
                .strategic-matrix {{
                    display: grid !important;
                    grid-template-columns: repeat(2, 1fr) !important;
                    gap: 12px !important;
                }}

                /* === CARD AREA === */
                .area-card {{
                    break-inside: avoid !important;
                    page-break-inside: avoid !important;
                    box-shadow: none !important;
                    border: 1px solid #ccc !important;
                    border-radius: 6px !important;
                }}

                .clickable-card {{
                    cursor: default;
                }}

                .clickable-card:hover {{
                    transform: none !important;
                    box-shadow: none !important;
                }}

                /* === RIMUOVI TRONCAMENTO - MOSTRA TESTO COMPLETO === */
                .obj-item.truncate-screen .obj-text {{
                    white-space: normal !important;
                    overflow: visible !important;
                    text-overflow: clip !important;
                    word-wrap: break-word !important;
                }}

                /* === BADGE E LABELS === */
                .obj-label,
                .badge-macro,
                .badge-micro,
                .obj-macro,
                .obj-micro {{
                    border: none !important;
                }}
            }}
        </style>
    </section>

    <!-- Dashboard Modals -->
    {modals_html}

    <script>
    function openDashboardModal(modalId) {{
        document.getElementById(modalId).classList.add('active');
        document.body.style.overflow = 'hidden';
    }}

    function closeDashboardModal(modalId) {{
        document.getElementById(modalId).classList.remove('active');
        document.body.style.overflow = 'auto';
    }}

    // Close modal clicking outside
    document.addEventListener('click', function(e) {{
        if (e.target.classList.contains('dashboard-modal')) {{
            e.target.classList.remove('active');
            document.body.style.overflow = 'auto';
        }}
    }});

    // Close modal with ESC
    document.addEventListener('keydown', function(e) {{
        if (e.key === 'Escape') {{
            document.querySelectorAll('.dashboard-modal.active').forEach(m => {{
                m.classList.remove('active');
            }});
            document.body.style.overflow = 'auto';
        }}
    }});
    </script>
    '''

    return dashboard
