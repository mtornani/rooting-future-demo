# rooting_future/report_visualizer.py

import os
from pathlib import Path
import plotly.graph_objects as go
import plotly.io as pio
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)

# Imposta il motore di rendering per l'esportazione di immagini
pio.kaleido.scope.mathjax = None

# Template di stile per i grafici
pio.templates["rooting_future_theme"] = go.layout.Template(
    layout=go.Layout(
        font_color="#2d3748", # Grigio scuro per il testo
        title_font_color="#1a365d", # Blu scuro per i titoli
        paper_bgcolor="rgba(0,0,0,0)", # Sfondo trasparente
        plot_bgcolor="rgba(0,0,0,0)",
        colorway=['#3182ce', '#2c5282', '#63b3ed', '#4299e1'], # Palette blu
        xaxis=dict(gridcolor='#e2e8f0'),
        yaxis=dict(gridcolor='#e2e8f0'),
    )
)
pio.templates.default = "plotly_white+rooting_future_theme"

def create_bar_chart(data: List[Dict], title: str, output_dir: Path) -> str | None:
    """
    Crea un grafico a barre da dati strutturati e lo salva come immagine PNG.

    Args:
        data: Lista di dizionari, es. [{'label': 'Serie A', 'value': 100}, ...]
        title: Titolo del grafico.
        output_dir: Directory dove salvare l'immagine.

    Returns:
        Il percorso del file immagine generato, o None se fallisce.
    """
    if not data:
        logger.warning(f"Nessun dato fornito per il grafico: {title}")
        return None

    try:
        labels = [item.get('label', '') for item in data]
        values = []
        for item in data:
            # Tenta di convertire il valore in numero, ignorando ciò che non è numerico
            try:
                # Rimuovi simboli di valuta e spazi, converti virgola in punto
                value_str = str(item.get('value', '0')).replace('€', '').replace('K', '000').replace('M', '000000').strip()
                values.append(float(value_str))
            except (ValueError, TypeError):
                values.append(0) # Valore di default se la conversione fallisce

        fig = go.Figure(data=[go.Bar(x=labels, y=values, text=values, textposition='auto')])
        
        fig.update_layout(
            title_text=title,
            xaxis_title="Categoria",
            yaxis_title="Valore",
            uniformtext_minsize=8, 
            uniformtext_mode='hide'
        )

        # Genera un nome file sicuro
        safe_filename = "".join(c for c in title if c.isalnum() or c in (' ', '_')).rstrip()
        safe_filename = safe_filename.replace(' ', '_').lower()
        output_file = output_dir / f"chart_{safe_filename}.png"

        fig.write_image(str(output_file), scale=2) # Scala 2x per maggiore risoluzione

        logger.info(f"Grafico generato: {output_file}")
        return str(output_file)

    except Exception as e:
        logger.error(f"Errore durante la creazione del grafico '{title}': {e}", exc_info=True)
        return None

if __name__ == '__main__':
    # Esempio di utilizzo
    logger.basicConfig(level=logging.INFO)
    
    test_data = [
        {'label': 'Fatturato Stimato', 'value': '€586K'},
        {'label': 'Benchmark Serie C', 'value': '€4.5M'}
    ]
    
    output_directory = Path("output_test_charts")
    output_directory.mkdir(exist_ok=True)
    
    chart_path = create_bar_chart(test_data, "Confronto Fatturato", output_directory)
    
    if chart_path:
        print(f"Test completato. Grafico salvato in: {chart_path}")
    else:
        print("Test fallito.")

