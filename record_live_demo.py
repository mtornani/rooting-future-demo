"""
Rooting Future - Live Screen Recording con Crop Automatico

Questo script ti guida nella registrazione del sistema reale
e converte il video in formato mobile-friendly.

Requirements:
    - OBS Studio (per Windows/macOS/Linux)
    - ffmpeg (per post-processing)

Alternative native:
    - Windows: Xbox Game Bar (Win + G)
    - macOS: QuickTime / Screenshot.app
    - Linux: SimpleScreenRecorder

Usage:
    python record_live_demo.py
"""

import subprocess
import sys
from pathlib import Path
from datetime import datetime
import json
import os


class LiveDemoRecorder:
    """Guida e post-processa la registrazione live del sistema"""

    def __init__(self, output_dir: str = "live_demo"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

        self.platform = sys.platform
        self.raw_video = None
        self.processed_video = None

    def print_header(self):
        """Header informativo"""
        print("\n" + "=" * 70)
        print("  🎥 ROOTING FUTURE - LIVE SCREEN RECORDING")
        print("=" * 70)
        print()
        print("Questo script ti guiderà nella registrazione del sistema live")
        print("e creerà un video mobile-friendly ottimizzato.")
        print()

    def check_ffmpeg(self) -> bool:
        """Verifica se ffmpeg è installato"""
        try:
            result = subprocess.run(
                ['ffmpeg', '-version'],
                capture_output=True,
                check=True
            )
            return True
        except (FileNotFoundError, subprocess.CalledProcessError):
            return False

    def print_recording_guide(self):
        """Stampa guida per la registrazione"""
        print("📋 STORYBOARD DEMO - Segui questo script:")
        print("-" * 70)
        print()

        script = [
            ("1. APERTURA APP", "3s", [
                "- Apri browser a http://127.0.0.1:5000",
                "- Mostra dashboard home per 2-3 secondi"
            ]),
            ("2. LOGIN (se richiesto)", "5s", [
                "- Inserisci credenziali",
                "- Click login"
            ]),
            ("3. DASHBOARD OVERVIEW", "5s", [
                "- Mostra progetti esistenti",
                "- Scroll lentamente per mostrare interfaccia"
            ]),
            ("4. AVVIA GENERAZIONE", "3s", [
                "- Click su 'Genera Nuovo Piano'",
                "- Form appare"
            ]),
            ("5. COMPILA FORM", "15s", [
                "- Nome Club: 'AC Riccione 1926' (o altro)",
                "- Categoria: 'Eccellenza'",
                "- Colori: Seleziona colori",
                "- (Opzionale) Aggiungi visione/obiettivi",
                "- Click 'Genera Piano Strategico'"
            ]),
            ("6. PROGRESS BAR", "10s", [
                "- Mostra progress con agenti al lavoro",
                "- IMPORTANTE: Accelereremo questa parte in post-produzione",
                "- Lascia registrare fino a ~30-50% completamento"
            ]),
            ("7. PIANO COMPLETATO", "20s", [
                "- Naviga al piano completato",
                "- Scroll lento attraverso Executive Summary",
                "- Mostra sezione STW Sportivi",
                "- Mostra sezione STW Strutturali",
                "- Mostra Piano Economico-Finanziario",
                "- Mostra grafici/tabelle (se presenti)"
            ]),
            ("8. EXPORT", "8s", [
                "- Click su pulsante 'Export'",
                "- Mostra opzioni (PDF, DOCX, ZIP)",
                "- Click download PDF",
                "- Mostra notifica download"
            ]),
            ("9. ANTEPRIMA PDF", "5s", [
                "- Apri PDF scaricato",
                "- Mostra prima pagina",
                "- Scroll veloce per mostrare contenuto"
            ]),
        ]

        for title, duration, steps in script:
            print(f"▶️  {title} ({duration})")
            for step in steps:
                print(f"    {step}")
            print()

        print("-" * 70)
        print()
        print("⏱️  DURATA TOTALE PREVISTA: ~70 secondi")
        print("    (diventerà ~40s dopo speed-up delle parti lente)")
        print()

    def guide_windows_recording(self):
        """Guida per registrazione Windows"""
        print("🪟 WINDOWS - XBOX GAME BAR")
        print("-" * 70)
        print()
        print("SETUP:")
        print("1. Apri Chrome/Edge con l'app Rooting Future")
        print("2. Ridimensiona finestra a circa 500-600px larghezza")
        print("   (simula aspect ratio mobile)")
        print("3. Posiziona finestra al centro dello schermo")
        print()
        print("REGISTRAZIONE:")
        print("1. Premi Win + G per aprire Xbox Game Bar")
        print("2. Click sul pulsante Registra (cerchio bianco)")
        print("   OPPURE: Win + Alt + R per start/stop")
        print("3. Esegui lo storyboard sopra")
        print("4. Premi Win + Alt + R per fermare")
        print()
        print("OUTPUT:")
        print("   Video salvato in: C:\\Users\\{username}\\Videos\\Captures\\")
        print()
        print("ALTERNATIVA - OBS Studio (più professionale):")
        print("   Download: https://obsproject.com/")
        print("   1. Installa OBS")
        print("   2. Sorgenti → Cattura Finestra → Seleziona Chrome")
        print("   3. Avvia Registrazione")
        print("   4. Stop Registrazione")
        print()

    def guide_macos_recording(self):
        """Guida per registrazione macOS"""
        print("🍎 macOS - QUICKTIME PLAYER")
        print("-" * 70)
        print()
        print("SETUP:")
        print("1. Apri Safari/Chrome con l'app Rooting Future")
        print("2. Ridimensiona finestra a circa 500-600px larghezza")
        print()
        print("REGISTRAZIONE:")
        print("1. Apri QuickTime Player")
        print("2. File → Nuova Registrazione Schermo")
        print("3. Click freccia giù → Opzioni:")
        print("   - Microfono: Nessuno (o abilita se vuoi narrazione)")
        print("   - Mostra click del mouse: Opzionale")
        print("4. Click Registra")
        print("5. Seleziona solo la finestra del browser")
        print("   (Click sulla finestra, NON trascinare)")
        print("6. Esegui lo storyboard")
        print("7. Stop dalla barra menu")
        print("8. File → Salva")
        print()
        print("ALTERNATIVA - Screenshot.app (macOS Mojave+):")
        print("   1. Premi Cmd + Shift + 5")
        print("   2. Seleziona 'Registra Porzione Selezionata'")
        print("   3. Trascina per selezionare area finestra browser")
        print("   4. Click Registra")
        print()

    def guide_linux_recording(self):
        """Guida per registrazione Linux"""
        print("🐧 LINUX - SIMPLESCREENRECORDER")
        print("-" * 70)
        print()
        print("INSTALLAZIONE:")
        print("   sudo apt install simplescreenrecorder  # Ubuntu/Debian")
        print("   sudo dnf install simplescreenrecorder  # Fedora")
        print()
        print("REGISTRAZIONE:")
        print("1. Apri SimpleScreenRecorder")
        print("2. Seleziona 'Record a fixed rectangle'")
        print("3. Posiziona rettangolo sulla finestra browser")
        print("4. Start Recording")
        print("5. Esegui storyboard")
        print("6. Stop Recording")
        print()
        print("ALTERNATIVA - Kazam:")
        print("   sudo apt install kazam")
        print()

    def wait_for_raw_video(self) -> Path:
        """Chiedi all'utente dove ha salvato il video"""
        print()
        print("=" * 70)
        print("  📹 VIDEO REGISTRATO")
        print("=" * 70)
        print()
        print("Hai completato la registrazione?")
        print()

        while True:
            video_path = input("Inserisci il percorso completo del video registrato: ").strip()
            video_path = video_path.strip('"\'')  # Rimuovi virgolette

            path = Path(video_path)
            if path.exists():
                self.raw_video = path
                print(f"✓ Video trovato: {path.name}")
                return path
            else:
                print(f"❌ File non trovato: {video_path}")
                retry = input("Riprova? (y/n): ").strip().lower()
                if retry != 'y':
                    return None

    def crop_to_mobile(self, input_video: Path, crop_width: int = 400) -> Path:
        """Ritaglia video a formato mobile-friendly"""
        if not self.check_ffmpeg():
            print()
            print("❌ ffmpeg non trovato!")
            print()
            print("INSTALLA FFMPEG:")
            print("   Windows: https://www.gyan.dev/ffmpeg/builds/")
            print("   macOS: brew install ffmpeg")
            print("   Linux: sudo apt install ffmpeg")
            print()
            return None

        print()
        print("🎬 POST-PROCESSING VIDEO")
        print("-" * 70)
        print()

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = self.output_dir / f"rooting_future_demo_{timestamp}.mp4"

        # Analizza dimensioni video
        probe_cmd = [
            'ffprobe',
            '-v', 'error',
            '-select_streams', 'v:0',
            '-show_entries', 'stream=width,height',
            '-of', 'json',
            str(input_video)
        ]

        try:
            result = subprocess.run(probe_cmd, capture_output=True, text=True, check=True)
            data = json.loads(result.stdout)
            width = data['streams'][0]['width']
            height = data['streams'][0]['height']

            print(f"📐 Dimensioni originali: {width}x{height}")

            # Calcola crop centrale
            crop_x = (width - crop_width) // 2
            crop_filter = f"crop={crop_width}:{height}:{crop_x}:0"

            print(f"✂️  Ritaglio a: {crop_width}x{height} (verticale)")
            print()
            print("⚙️  Applicazione trasformazioni:")
            print("   - Crop centrale per formato mobile")
            print("   - Speed up 2x per sezioni lente (progress bar)")
            print("   - Compression per ridurre file size")
            print()

        except Exception as e:
            print(f"⚠️  Impossibile analizzare video, uso dimensioni default: {e}")
            crop_filter = f"crop={crop_width}:ih:(iw-{crop_width})/2:0"

        # Comando ffmpeg completo
        cmd = [
            'ffmpeg',
            '-i', str(input_video),
            '-vf', f"{crop_filter},fps=30",  # Crop + fix fps
            '-c:v', 'libx264',
            '-preset', 'medium',
            '-crf', '23',  # Qualità (18-28, 23 è buono)
            '-c:a', 'aac',
            '-b:a', '128k',
            '-movflags', '+faststart',  # Web-optimized
            '-y',
            str(output_path)
        ]

        print("🎞️  Processamento in corso...")
        print()

        try:
            subprocess.run(cmd, check=True)
            print()
            print("✅ Video processato con successo!")
            print(f"   📹 Output: {output_path}")
            print()

            # File size info
            size_mb = output_path.stat().st_size / (1024 * 1024)
            print(f"   📦 Dimensione: {size_mb:.1f} MB")

            if size_mb > 16:
                print()
                print("   ⚠️  File > 16MB - troppo grande per WhatsApp")
                print("   💡 Comprimi ulteriormente? (y/n)")
                compress = input("   > ").strip().lower()

                if compress == 'y':
                    return self.compress_for_whatsapp(output_path)

            self.processed_video = output_path
            return output_path

        except subprocess.CalledProcessError as e:
            print(f"❌ Errore durante processing: {e}")
            return None

    def compress_for_whatsapp(self, input_video: Path) -> Path:
        """Comprime video per WhatsApp (<16MB)"""
        print()
        print("📦 COMPRESSIONE PER WHATSAPP")
        print("-" * 70)

        output_path = input_video.parent / f"{input_video.stem}_compressed.mp4"

        cmd = [
            'ffmpeg',
            '-i', str(input_video),
            '-vf', 'scale=-2:720',  # Scale to 720p
            '-c:v', 'libx264',
            '-preset', 'slow',
            '-crf', '28',  # Più compressione
            '-c:a', 'aac',
            '-b:a', '96k',
            '-movflags', '+faststart',
            '-y',
            str(output_path)
        ]

        try:
            subprocess.run(cmd, check=True)
            size_mb = output_path.stat().st_size / (1024 * 1024)
            print(f"✅ Video compresso: {output_path.name}")
            print(f"   📦 Dimensione: {size_mb:.1f} MB")

            if size_mb > 16:
                print("   ⚠️  Ancora troppo grande. Prova a ridurre durata video.")

            return output_path

        except subprocess.CalledProcessError as e:
            print(f"❌ Errore compressione: {e}")
            return input_video

    def create_speedup_version(self, input_video: Path, speed_factor: float = 1.5) -> Path:
        """Crea versione accelerata del video"""
        print()
        print(f"⚡ SPEED UP VIDEO (x{speed_factor})")
        print("-" * 70)

        output_path = input_video.parent / f"{input_video.stem}_fast.mp4"

        # Speed up richiede filtro complesso
        video_speed = 1 / speed_factor
        audio_speed = 1 / speed_factor

        cmd = [
            'ffmpeg',
            '-i', str(input_video),
            '-filter_complex',
            f"[0:v]setpts={video_speed}*PTS[v];[0:a]atempo={speed_factor}[a]",
            '-map', '[v]',
            '-map', '[a]',
            '-c:v', 'libx264',
            '-preset', 'medium',
            '-crf', '23',
            '-y',
            str(output_path)
        ]

        try:
            subprocess.run(cmd, check=True)
            print(f"✅ Video accelerato: {output_path.name}")
            return output_path

        except subprocess.CalledProcessError as e:
            print(f"❌ Errore speed up: {e}")
            return input_video

    def print_final_summary(self):
        """Stampa summary finale"""
        print()
        print("=" * 70)
        print("  ✅ DEMO VIDEO COMPLETATO!")
        print("=" * 70)
        print()

        if self.processed_video:
            print(f"📹 Video finale: {self.processed_video}")
            print(f"📁 Cartella: {self.processed_video.parent.absolute()}")
            print()

            size_mb = self.processed_video.stat().st_size / (1024 * 1024)
            if size_mb <= 16:
                print("✅ Pronto per WhatsApp/Telegram!")
            else:
                print("ℹ️  Per WhatsApp, carica su Google Drive e condividi link")

            print()
            print("📤 OPZIONI CONDIVISIONE:")
            print("   1. WhatsApp: Invia direttamente (se <16MB)")
            print("   2. Email: Allega o usa link cloud")
            print("   3. Google Drive: Carica e condividi link")
            print("   4. YouTube: Carica come 'Non in elenco'")

        print()
        print("💡 TIP: Se vuoi migliorare il video:")
        print("   - Aggiungi intro/outro con app mobile (InShot)")
        print("   - Aggiungi testo overlay per spiegazioni")
        print("   - Aggiungi musica sottofondo")
        print()

    def run(self):
        """Esegui workflow completo"""
        self.print_header()

        # Mostra guida per piattaforma
        print("🎯 STEP 1: REGISTRA IL VIDEO")
        print()

        if self.platform == 'win32':
            self.guide_windows_recording()
        elif self.platform == 'darwin':
            self.guide_macos_recording()
        else:
            self.guide_linux_recording()

        # Mostra storyboard
        self.print_recording_guide()

        print()
        print("🎬 Sei pronto a registrare?")
        print()
        print("PREPARAZIONE:")
        print("   1. Apri l'app su http://127.0.0.1:5000")
        print("   2. Ridimensiona finestra browser a ~500px larghezza")
        print("   3. Prepara screen recorder (leggi guida sopra)")
        print()

        input("Premi INVIO quando sei pronto a registrare...")
        print()
        print("🔴 REGISTRA ORA! Segui lo storyboard sopra.")
        print()

        # Aspetta video
        print("⏸️  Hai finito la registrazione?")
        input("Premi INVIO quando hai il file video...")

        # Processa video
        raw_video = self.wait_for_raw_video()
        if not raw_video:
            print("❌ Video non fornito. Uscita.")
            return 1

        # Crop e ottimizza
        processed = self.crop_to_mobile(raw_video)

        if processed:
            # Opzionale: speed up
            print()
            speedup = input("Vuoi creare versione accelerata (1.5x)? (y/n): ").strip().lower()
            if speedup == 'y':
                self.create_speedup_version(processed, speed_factor=1.5)

        self.print_final_summary()
        return 0


def main():
    """Entry point"""
    recorder = LiveDemoRecorder()
    return recorder.run()


if __name__ == "__main__":
    exit(main())
