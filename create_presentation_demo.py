"""
Rooting Future - Presentation Demo Creator
Crea una presentazione statica mobile-friendly con infografica e branding

Questo script bypassa il problema del design non responsive creando
slide statiche ottimizzate per mobile con testo, screenshot e grafici.

Requirements:
    pip install pillow

Usage:
    python create_presentation_demo.py
"""

from pathlib import Path
from datetime import datetime
from typing import List, Tuple
import textwrap

try:
    from PIL import Image, ImageDraw, ImageFont, ImageFilter
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    print("⚠️ Pillow non installato. Installa con: pip install pillow")
    exit(1)


class PresentationSlide:
    """Singola slide della presentazione"""

    def __init__(self, width: int = 1080, height: int = 1920):
        """
        Crea slide in formato mobile verticale (9:16)
        Default: 1080x1920 (Full HD verticale)
        """
        self.width = width
        self.height = height
        self.img = Image.new('RGB', (width, height), color='white')
        self.draw = ImageDraw.Draw(self.img)

        # Colori brand Rooting Future
        self.purple = '#6B46C1'  # Purple primario
        self.purple_light = '#9F7AEA'
        self.blue = '#1a365d'
        self.gold = '#D69E2E'
        self.gray = '#4A5568'
        self.white = '#FFFFFF'

        # Font sizes (relative to height)
        self.font_title = self._get_font(int(height * 0.055))  # ~100px su 1920
        self.font_subtitle = self._get_font(int(height * 0.035))  # ~65px
        self.font_body = self._get_font(int(height * 0.025))  # ~45px
        self.font_small = self._get_font(int(height * 0.020))  # ~35px

    def _get_font(self, size: int):
        """Carica font o usa default"""
        try:
            # Try Arial (Windows)
            return ImageFont.truetype("arial.ttf", size)
        except:
            try:
                # Try Helvetica (macOS)
                return ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", size)
            except:
                # Fallback to default
                return ImageFont.load_default()

    def _hex_to_rgb(self, hex_color: str) -> Tuple[int, int, int]:
        """Converti hex a RGB"""
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

    def add_header_bar(self, color: str = None):
        """Aggiungi barra header colorata"""
        color = color or self.purple
        rgb = self._hex_to_rgb(color)

        # Barra top
        bar_height = int(self.height * 0.08)
        self.draw.rectangle([(0, 0), (self.width, bar_height)], fill=rgb)

    def add_footer(self, text: str = "Rooting Future v5.5"):
        """Aggiungi footer con branding"""
        footer_y = int(self.height * 0.95)
        self.draw.text(
            (self.width // 2, footer_y),
            text,
            fill=self._hex_to_rgb(self.gray),
            font=self.font_small,
            anchor="mm"
        )

    def add_title(self, text: str, y_position: float = 0.15, color: str = None):
        """Aggiungi titolo centrato"""
        color = color or self.purple
        rgb = self._hex_to_rgb(color)

        y = int(self.height * y_position)
        self.draw.text(
            (self.width // 2, y),
            text,
            fill=rgb,
            font=self.font_title,
            anchor="mm"
        )

    def add_subtitle(self, text: str, y_position: float = 0.22, color: str = None):
        """Aggiungi sottotitolo"""
        color = color or self.gray
        rgb = self._hex_to_rgb(color)

        y = int(self.height * y_position)
        self.draw.text(
            (self.width // 2, y),
            text,
            fill=rgb,
            font=self.font_subtitle,
            anchor="mm"
        )

    def add_body_text(self, text: str, y_start: float = 0.3,
                      line_height: int = None, color: str = None):
        """Aggiungi testo body multilinea"""
        color = color or self.gray
        rgb = self._hex_to_rgb(color)
        line_height = line_height or int(self.height * 0.04)

        # Wrap text
        wrapped_lines = textwrap.wrap(text, width=35)

        y = int(self.height * y_start)
        padding_x = int(self.width * 0.1)

        for line in wrapped_lines:
            self.draw.text(
                (padding_x, y),
                line,
                fill=rgb,
                font=self.font_body
            )
            y += line_height

    def add_bullet_points(self, points: List[str], y_start: float = 0.35,
                          color: str = None, bullet_color: str = None):
        """Aggiungi lista bullet points"""
        color = color or self.gray
        bullet_color = bullet_color or self.purple
        rgb = self._hex_to_rgb(color)
        bullet_rgb = self._hex_to_rgb(bullet_color)

        y = int(self.height * y_start)
        padding_x = int(self.width * 0.12)
        bullet_x = int(self.width * 0.08)
        line_height = int(self.height * 0.06)

        for point in points:
            # Bullet
            self.draw.ellipse(
                [(bullet_x, y), (bullet_x + 20, y + 20)],
                fill=bullet_rgb
            )

            # Wrap text per punto
            wrapped = textwrap.wrap(point, width=32)
            for i, line in enumerate(wrapped):
                self.draw.text(
                    (padding_x, y + (i * int(line_height * 0.6))),
                    line,
                    fill=rgb,
                    font=self.font_body
                )

            y += line_height

    def add_number_badge(self, number: str, y_position: float = 0.4, size: int = None):
        """Aggiungi badge circolare con numero"""
        size = size or int(self.width * 0.25)
        x = self.width // 2 - size // 2
        y = int(self.height * y_position)

        # Cerchio
        self.draw.ellipse(
            [(x, y), (x + size, y + size)],
            fill=self._hex_to_rgb(self.purple),
            outline=self._hex_to_rgb(self.purple_light),
            width=8
        )

        # Numero
        font_huge = self._get_font(int(size * 0.5))
        self.draw.text(
            (self.width // 2, y + size // 2),
            number,
            fill=self._hex_to_rgb(self.white),
            font=font_huge,
            anchor="mm"
        )

    def add_icon_placeholder(self, emoji: str, y_position: float = 0.12):
        """Aggiungi emoji/icona grande"""
        font_icon = self._get_font(int(self.height * 0.08))
        y = int(self.height * y_position)

        self.draw.text(
            (self.width // 2, y),
            emoji,
            font=font_icon,
            anchor="mm"
        )

    def save(self, filepath: Path):
        """Salva slide"""
        self.img.save(filepath, quality=95)


class PresentationDemoCreator:
    """Crea presentazione completa per demo"""

    def __init__(self, output_dir: str = "presentation_demo"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.slides = []

    def create_slide_1_intro(self) -> Path:
        """Slide 1: Intro/Logo"""
        slide = PresentationSlide()

        slide.add_header_bar()

        # Logo placeholder (emoji)
        slide.add_icon_placeholder("⚽", y_position=0.25)

        # Titolo
        slide.add_title("ROOTING FUTURE", y_position=0.40)
        slide.add_subtitle("AI-Powered Strategic Planning", y_position=0.47)

        # Tagline
        slide.add_body_text(
            "Piani strategici professionali per società calcistiche\nGenerati in 60 secondi con AI",
            y_start=0.60
        )

        # Stats box
        slide.add_bullet_points([
            "🧠 6 Agenti AI Specializzati",
            "📊 Metodologia Sport To Win (STW)",
            "📄 Export Multi-Formato (PDF/DOCX/ZIP)",
            "⚡ Generazione in <60 secondi"
        ], y_start=0.70)

        slide.add_footer("v5.5 - Demo Presentation")

        filepath = self.output_dir / "01_intro.png"
        slide.save(filepath)
        self.slides.append(filepath)
        return filepath

    def create_slide_2_problem(self) -> Path:
        """Slide 2: Il Problema"""
        slide = PresentationSlide()
        slide.add_header_bar()

        slide.add_title("Il Problema", y_position=0.12, color='#E53E3E')
        slide.add_icon_placeholder("❌", y_position=0.20)

        slide.add_body_text(
            "I piani strategici tradizionali richiedono:",
            y_start=0.32
        )

        slide.add_bullet_points([
            "⏱️ Settimane di lavoro consulenziale",
            "💰 Budget elevati (€10.000+)",
            "📚 Competenze specialistiche multiple",
            "🔄 Revisioni continue e iterazioni",
            "📉 Qualità variabile e soggettiva"
        ], y_start=0.42)

        slide.add_footer()
        filepath = self.output_dir / "02_problem.png"
        slide.save(filepath)
        self.slides.append(filepath)
        return filepath

    def create_slide_3_solution(self) -> Path:
        """Slide 3: La Soluzione"""
        slide = PresentationSlide()
        slide.add_header_bar(color='#38A169')

        slide.add_title("La Soluzione", y_position=0.12, color='#38A169')
        slide.add_icon_placeholder("✅", y_position=0.20)

        slide.add_body_text(
            "Rooting Future automatizza l'intero processo:",
            y_start=0.32
        )

        slide.add_bullet_points([
            "🚀 60 secondi di generazione",
            "💎 Qualità consulenziale garantita",
            "🎯 Metodologia STW integrata",
            "📊 Dati reali + benchmark di mercato",
            "🔄 Iterazioni illimitate"
        ], y_start=0.42, bullet_color='#38A169')

        slide.add_footer()
        filepath = self.output_dir / "03_solution.png"
        slide.save(filepath)
        self.slides.append(filepath)
        return filepath

    def create_slide_4_how_it_works(self) -> Path:
        """Slide 4: Come Funziona - Step 1"""
        slide = PresentationSlide()
        slide.add_header_bar()

        slide.add_title("Come Funziona", y_position=0.10)
        slide.add_number_badge("1", y_position=0.20, size=200)

        slide.add_subtitle("Inserisci Dati Club", y_position=0.48)

        slide.add_body_text(
            "Form semplice con dati essenziali:\n\n"
            "• Nome società\n"
            "• Categoria (Eccellenza, D, C...)\n"
            "• Colori istituzionali\n"
            "• Visione e obiettivi (opzionale)",
            y_start=0.58
        )

        slide.add_footer()
        filepath = self.output_dir / "04_step1.png"
        slide.save(filepath)
        self.slides.append(filepath)
        return filepath

    def create_slide_5_step2(self) -> Path:
        """Slide 5: Step 2 - Generazione"""
        slide = PresentationSlide()
        slide.add_header_bar()

        slide.add_title("Come Funziona", y_position=0.10)
        slide.add_number_badge("2", y_position=0.20, size=200)

        slide.add_subtitle("AI Agents al Lavoro", y_position=0.48)

        slide.add_body_text(
            "6 agenti specializzati lavorano in parallelo:",
            y_start=0.56
        )

        slide.add_bullet_points([
            "⚽ STW Sportivi (8 macro obiettivi)",
            "🏗️ STW Strutturali (infrastrutture)",
            "📢 STW Marketing & Commerciale",
            "🤝 STW Sociali (CSR, inclusione)",
            "💰 Financial Planning",
            "🎯 Strategic Coordinator"
        ], y_start=0.64, bullet_color='#6B46C1')

        slide.add_footer()
        filepath = self.output_dir / "05_step2.png"
        slide.save(filepath)
        self.slides.append(filepath)
        return filepath

    def create_slide_6_step3(self) -> Path:
        """Slide 6: Step 3 - Output"""
        slide = PresentationSlide()
        slide.add_header_bar()

        slide.add_title("Come Funziona", y_position=0.10)
        slide.add_number_badge("3", y_position=0.20, size=200)

        slide.add_subtitle("Piano Strategico Completo", y_position=0.48)

        slide.add_bullet_points([
            "📄 Strategic Plan (40+ pagine)",
            "📊 Executive Report (6 pagine)",
            "📋 One-Pager infografico",
            "📈 Piano Economico-Finanziario",
            "📦 Strategy Pack (ZIP completo)"
        ], y_start=0.58)

        slide.add_footer()
        filepath = self.output_dir / "06_step3.png"
        slide.save(filepath)
        self.slides.append(filepath)
        return filepath

    def create_slide_7_features(self) -> Path:
        """Slide 7: Features Chiave"""
        slide = PresentationSlide()
        slide.add_header_bar()

        slide.add_title("Features Chiave", y_position=0.10)
        slide.add_icon_placeholder("🚀", y_position=0.18)

        slide.add_bullet_points([
            "🧠 RAG Learning (apprende da ogni piano)",
            "📊 Data Transparency (fonte per ogni dato)",
            "🎨 Brand Customization (colori club)",
            "🔍 Multi-Stakeholder Analysis",
            "📈 Benchmark Database proprietario",
            "🌐 Web Research integrata",
            "💾 Knowledge Base persistente"
        ], y_start=0.32)

        slide.add_footer()
        filepath = self.output_dir / "07_features.png"
        slide.save(filepath)
        self.slides.append(filepath)
        return filepath

    def create_slide_8_output_quality(self) -> Path:
        """Slide 8: Qualità Output"""
        slide = PresentationSlide()
        slide.add_header_bar()

        slide.add_title("Qualità Garantita", y_position=0.10, color='#D69E2E')
        slide.add_icon_placeholder("⭐", y_position=0.18)

        slide.add_body_text(
            "Standard professionali garantiti:",
            y_start=0.30
        )

        slide.add_bullet_points([
            "✅ Metodologia STW ufficiale",
            "✅ Tono istituzionale (no naming)",
            "✅ Dati verificati + trasparenza fonti",
            "✅ Design premium (McKinsey-style)",
            "✅ PDF/DOCX print-ready",
            "✅ Benchmark di mercato aggiornati"
        ], y_start=0.40, bullet_color='#D69E2E')

        slide.add_footer()
        filepath = self.output_dir / "08_quality.png"
        slide.save(filepath)
        self.slides.append(filepath)
        return filepath

    def create_slide_9_use_cases(self) -> Path:
        """Slide 9: Use Cases"""
        slide = PresentationSlide()
        slide.add_header_bar()

        slide.add_title("Chi Può Usarlo?", y_position=0.10)
        slide.add_icon_placeholder("🎯", y_position=0.18)

        slide.add_bullet_points([
            "🏆 Società Dilettantistiche (tutte categorie)",
            "💼 Consulenti Sportivi",
            "📊 Sport Management Agencies",
            "🏛️ Federazioni e Comitati",
            "🎓 Accademie e Scuole Calcio",
            "💰 Investitori (due diligence)"
        ], y_start=0.32)

        slide.add_footer()
        filepath = self.output_dir / "09_use_cases.png"
        slide.save(filepath)
        self.slides.append(filepath)
        return filepath

    def create_slide_10_cta(self) -> Path:
        """Slide 10: Call to Action"""
        slide = PresentationSlide()
        slide.add_header_bar(color='#6B46C1')

        slide.add_icon_placeholder("💬", y_position=0.25)
        slide.add_title("Contattaci", y_position=0.40, color='#6B46C1')

        slide.add_body_text(
            "Vuoi vedere il sistema in azione?\n\n"
            "📧 Email: info@rootingfuture.com\n"
            "🌐 Web: www.rootingfuture.com\n"
            "📱 WhatsApp: +39 XXX XXX XXXX",
            y_start=0.52
        )

        slide.add_subtitle("Richiedi Demo Personalizzata", y_position=0.75, color='#6B46C1')

        slide.add_footer("Rooting Future v5.5 - Powered by Gemini 2.0")
        filepath = self.output_dir / "10_cta.png"
        slide.save(filepath)
        self.slides.append(filepath)
        return filepath

    def create_all_slides(self):
        """Crea tutte le slide"""
        print("\n" + "=" * 70)
        print("  📊 CREAZIONE PRESENTATION DEMO")
        print("=" * 70)
        print()

        slides_methods = [
            ("Slide 1: Intro", self.create_slide_1_intro),
            ("Slide 2: Problem", self.create_slide_2_problem),
            ("Slide 3: Solution", self.create_slide_3_solution),
            ("Slide 4: Step 1", self.create_slide_4_how_it_works),
            ("Slide 5: Step 2", self.create_slide_5_step2),
            ("Slide 6: Step 3", self.create_slide_6_step3),
            ("Slide 7: Features", self.create_slide_7_features),
            ("Slide 8: Quality", self.create_slide_8_output_quality),
            ("Slide 9: Use Cases", self.create_slide_9_use_cases),
            ("Slide 10: CTA", self.create_slide_10_cta),
        ]

        for name, method in slides_methods:
            print(f"✏️  Creazione {name}...")
            filepath = method()
            print(f"   ✓ Salvata: {filepath.name}")

        print()
        print("=" * 70)
        print("✅ PRESENTATION COMPLETA!")
        print("=" * 70)
        print()
        print(f"📁 Slide salvate in: {self.output_dir.absolute()}")
        print(f"📊 Totale slide: {len(self.slides)}")
        print()
        print("🎞️  PROSSIMI PASSI:")
        print()
        print("OPZIONE 1 - App Mobile (CONSIGLIATO):")
        print("   1. Trasferisci cartella su smartphone")
        print("   2. Apri app InShot o CapCut")
        print("   3. Importa tutte le slide in ordine")
        print("   4. Durata: 3-4s per slide")
        print("   5. Transizioni: Dissolve")
        print("   6. Esporta video verticale 1080x1920")
        print()
        print("OPZIONE 2 - PowerPoint Desktop:")
        print("   1. Nuovo PowerPoint")
        print("   2. Inserisci → Immagine → importa tutte le slide")
        print("   3. File → Esporta → Crea Video")
        print("   4. Formato: Verticale (9:16)")
        print()
        print("OPZIONE 3 - Video automatico con ffmpeg:")
        print("   ffmpeg -framerate 1/3 -pattern_type glob -i '*.png' \\")
        print("          -c:v libx264 -pix_fmt yuv420p output.mp4")
        print()

    def create_video_with_ffmpeg(self, duration_per_slide: int = 3, output_name: str = "presentation.mp4"):
        """Crea video automaticamente con ffmpeg (se disponibile)"""
        import subprocess

        print("\n🎬 Tentativo creazione video con ffmpeg...")

        # Check ffmpeg disponibile
        try:
            subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
        except (FileNotFoundError, subprocess.CalledProcessError):
            print("❌ ffmpeg non trovato. Installa da: https://ffmpeg.org/download.html")
            return None

        # Crea file list per ffmpeg
        list_file = self.output_dir / "slides_list.txt"
        with open(list_file, 'w') as f:
            for slide in sorted(self.slides):
                f.write(f"file '{slide.name}'\n")
                f.write(f"duration {duration_per_slide}\n")

        # Comando ffmpeg
        output_path = self.output_dir / output_name
        cmd = [
            'ffmpeg',
            '-f', 'concat',
            '-safe', '0',
            '-i', str(list_file),
            '-vf', 'fps=30',
            '-pix_fmt', 'yuv420p',
            '-y',
            str(output_path)
        ]

        try:
            subprocess.run(cmd, check=True, cwd=self.output_dir)
            print(f"✅ Video creato: {output_path}")
            return output_path
        except subprocess.CalledProcessError as e:
            print(f"❌ Errore ffmpeg: {e}")
            return None


def main():
    """Entry point"""
    creator = PresentationDemoCreator()
    creator.create_all_slides()

    # Try video creation (opzionale)
    print()
    choice = input("Vuoi provare a creare il video automaticamente con ffmpeg? (y/n): ").strip().lower()
    if choice == 'y':
        creator.create_video_with_ffmpeg(duration_per_slide=3)

    return 0


if __name__ == "__main__":
    if not PIL_AVAILABLE:
        print("❌ Pillow richiesto. Installa con:")
        print("   pip install pillow")
        exit(1)

    exit(main())
