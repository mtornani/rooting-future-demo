"""
Rooting Future - Simple Screenshot Demo Creator
Alternativa semplificata che guida l'utente a catturare screenshots manualmente

Requirements:
    pip install pillow

Usage:
    python create_simple_demo.py
"""

import time
from pathlib import Path
from datetime import datetime
import json

try:
    from PIL import Image, ImageDraw, ImageFont
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    print("⚠️  Pillow non installato. Installa con: pip install pillow")


DEMO_SCRIPT = [
    {
        "step": 1,
        "title": "🏠 Dashboard Home",
        "url": "http://127.0.0.1:5000/",
        "instructions": "Mostra la dashboard principale con i progetti attivi",
        "duration": 3
    },
    {
        "step": 2,
        "title": "➕ Form Generazione Piano",
        "url": "http://127.0.0.1:5000/",
        "instructions": "Clicca su 'Genera Nuovo Piano' e mostra il form vuoto",
        "duration": 2
    },
    {
        "step": 3,
        "title": "✍️ Compilazione Dati Club",
        "url": "http://127.0.0.1:5000/",
        "instructions": "Compila: Nome Club, Categoria, Colori",
        "duration": 4
    },
    {
        "step": 4,
        "title": "🎯 Avvio Generazione",
        "url": "http://127.0.0.1:5000/",
        "instructions": "Clicca su 'Genera Piano Strategico'",
        "duration": 2
    },
    {
        "step": 5,
        "title": "⚙️ Progress Bar - Agenti al lavoro",
        "url": "http://127.0.0.1:5000/",
        "instructions": "Mostra la progress bar con gli agenti STW in esecuzione",
        "duration": 5
    },
    {
        "step": 6,
        "title": "📊 Piano Completato - Executive Summary",
        "url": "http://127.0.0.1:5000/plan/xxx",
        "instructions": "Naviga al piano e mostra l'Executive Summary",
        "duration": 3
    },
    {
        "step": 7,
        "title": "⚽ Sezione Obiettivi Sportivi",
        "url": "http://127.0.0.1:5000/plan/xxx",
        "instructions": "Scroll alla sezione STW Sportivi con i MACRO obiettivi",
        "duration": 4
    },
    {
        "step": 8,
        "title": "🏗️ Sezione Obiettivi Strutturali",
        "url": "http://127.0.0.1:5000/plan/xxx",
        "instructions": "Mostra gli obiettivi infrastrutturali",
        "duration": 3
    },
    {
        "step": 9,
        "title": "📢 Sezione Marketing & Commerciale",
        "url": "http://127.0.0.1:5000/plan/xxx",
        "instructions": "Mostra la strategia di marketing",
        "duration": 3
    },
    {
        "step": 10,
        "title": "💰 Piano Economico-Finanziario",
        "url": "http://127.0.0.1:5000/plan/xxx",
        "instructions": "Mostra la tabella con budget e proiezioni",
        "duration": 4
    },
    {
        "step": 11,
        "title": "📥 Export Options",
        "url": "http://127.0.0.1:5000/plan/xxx",
        "instructions": "Clicca su 'Export' e mostra i formati disponibili (PDF, DOCX, ZIP)",
        "duration": 3
    },
    {
        "step": 12,
        "title": "📄 Anteprima PDF",
        "url": "file:///",
        "instructions": "Apri il PDF scaricato e mostra la prima pagina",
        "duration": 3
    }
]


class SimpleDemoCreator:
    """Guida interattiva per creare demo screenshots"""

    def __init__(self, output_dir: str = "demo_manual"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.script = DEMO_SCRIPT

    def print_header(self):
        """Stampa header"""
        print("\n" + "=" * 70)
        print("  📹 ROOTING FUTURE - DEMO SCREENSHOT GUIDE")
        print("=" * 70)
        print()
        print("Questo script ti guiderà passo-passo nella cattura degli screenshot")
        print("per creare un video demo del sistema.")
        print()
        print(f"📁 Screenshots verranno salvati in: {self.output_dir.absolute()}")
        print()
        print("🎬 SETUP:")
        print("   1. Apri Chrome/Edge in modalità finestra (NON fullscreen)")
        print("   2. Imposta dimensioni finestra ~400px larghezza (mobile-like)")
        print("   3. Assicurati che l'app sia running su http://127.0.0.1:5000")
        print("   4. Tieni pronto il tasto PrintScreen o Snipping Tool")
        print()

    def run_guided_demo(self):
        """Esegui demo guidata"""
        self.print_header()

        input("✅ Setup completato? Premi INVIO per iniziare...")
        print()

        for scene in self.script:
            self.guide_screenshot(scene)

        self.print_completion()

    def guide_screenshot(self, scene: dict):
        """Guida per singolo screenshot"""
        print("-" * 70)
        print(f"STEP {scene['step']}/12: {scene['title']}")
        print("-" * 70)
        print()
        print(f"📍 URL: {scene['url']}")
        print(f"📝 AZIONE: {scene['instructions']}")
        print(f"⏱️  Durata consigliata nel video: {scene['duration']}s")
        print()

        screenshot_name = f"{scene['step']:02d}_{scene['title'].replace(' ', '_').replace(':', '').replace('/', '')}.png"
        screenshot_path = self.output_dir / screenshot_name

        print(f"💾 Salva screenshot come: {screenshot_name}")
        print()
        print("   [Windows] Win + Shift + S → Seleziona area → Salva")
        print("   [macOS]   Cmd + Shift + 4 → Seleziona area")
        print(f"   [Path]    {screenshot_path}")
        print()

        input("   📸 Screenshot catturato? Premi INVIO per continuare...")
        print()

        # Crea file marker se screenshot esiste
        if screenshot_path.exists():
            print(f"   ✅ Screenshot trovato: {screenshot_path.name}")
        else:
            print(f"   ⚠️  Screenshot non trovato (continuo comunque)")

        print()

    def print_completion(self):
        """Stampa messaggio finale"""
        print("=" * 70)
        print("✅ DEMO SCREENSHOTS COMPLETATI!")
        print("=" * 70)
        print()
        print(f"📁 Verifica gli screenshots in: {self.output_dir.absolute()}")
        print()
        print("🎞️  PROSSIMI PASSI:")
        print()
        print("OPZIONE 1 - Video automatico (se hai OpenCV):")
        print("   python create_demo_video.py --manual")
        print()
        print("OPZIONE 2 - Montaggio manuale:")
        print("   1. Scarica app mobile (es. InShot, CapCut, iMovie)")
        print("   2. Importa screenshots dalla cartella demo_manual/")
        print("   3. Imposta durata 2-3s per screenshot")
        print("   4. Aggiungi transizioni smooth")
        print("   5. Aggiungi musica di sottofondo (opzionale)")
        print("   6. Esporta come MP4 720p o 1080p")
        print()
        print("OPZIONE 3 - PowerPoint → Video:")
        print("   1. Apri PowerPoint")
        print("   2. Inserisci ogni screenshot come slide")
        print("   3. File → Esporta → Crea video")
        print()

    def create_storyboard(self):
        """Crea PDF storyboard del demo"""
        print("📋 Creazione storyboard PDF...")
        storyboard_path = self.output_dir / "storyboard.txt"

        with open(storyboard_path, "w", encoding="utf-8") as f:
            f.write("ROOTING FUTURE - DEMO STORYBOARD\n")
            f.write("=" * 70 + "\n\n")

            for scene in self.script:
                f.write(f"STEP {scene['step']}: {scene['title']}\n")
                f.write(f"URL: {scene['url']}\n")
                f.write(f"Instructions: {scene['instructions']}\n")
                f.write(f"Duration: {scene['duration']}s\n")
                f.write("-" * 70 + "\n\n")

        print(f"✅ Storyboard salvato: {storyboard_path}")
        return storyboard_path


def main():
    """Entry point"""
    print()
    creator = SimpleDemoCreator()

    print("Vuoi:")
    print("1. Seguire la guida interattiva (consigliato)")
    print("2. Solo generare lo storyboard")
    print()

    choice = input("Scelta (1 o 2): ").strip()

    if choice == "1":
        creator.run_guided_demo()
        creator.create_storyboard()
    elif choice == "2":
        creator.create_storyboard()
    else:
        print("Scelta non valida")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
