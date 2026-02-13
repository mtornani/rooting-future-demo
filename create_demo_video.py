"""
Rooting Future - Demo Video Generator
Crea un video demo automatizzato del sistema per presentazioni mobile-friendly

Requirements:
    pip install selenium webdriver-manager pillow opencv-python

Usage:
    python create_demo_video.py
"""

import time
import json
from pathlib import Path
from datetime import datetime
from typing import List, Tuple
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from webdriver_manager.chrome import ChromeDriverManager
    SELENIUM_AVAILABLE = True
except ImportError:
    logger.warning("Selenium not available. Install with: pip install selenium webdriver-manager")
    SELENIUM_AVAILABLE = False

try:
    from PIL import Image
    import cv2
    import numpy as np
    CV_AVAILABLE = True
except ImportError:
    logger.warning("OpenCV/Pillow not available. Install with: pip install opencv-python pillow")
    CV_AVAILABLE = False


class DemoVideoCreator:
    """
    Automatizza la creazione di un video demo del sistema Rooting Future
    """

    def __init__(self, base_url: str = "http://127.0.0.1:5000",
                 output_dir: str = "demo_output"):
        self.base_url = base_url
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

        self.screenshots_dir = self.output_dir / "screenshots"
        self.screenshots_dir.mkdir(exist_ok=True)

        self.driver = None
        self.screenshot_index = 0

        # Demo scenario configuration
        self.demo_club = {
            "club_name": "AC Riccione 1926",
            "category": "Eccellenza",
            "primary_color": "#0066cc",
            "secondary_color": "#ffffff"
        }

    def setup_driver(self, mobile_view: bool = True):
        """Inizializza il browser con configurazione ottimizzata"""
        if not SELENIUM_AVAILABLE:
            raise RuntimeError("Selenium non disponibile. Installa con: pip install selenium webdriver-manager")

        logger.info("Inizializzazione Chrome driver...")

        chrome_options = Options()
        chrome_options.add_argument('--headless')  # Modalità headless
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')

        # Mobile viewport for mobile-friendly recording
        if mobile_view:
            # iPhone 12 Pro dimensions
            chrome_options.add_argument('--window-size=390,844')
            mobile_emulation = {
                "deviceMetrics": {"width": 390, "height": 844, "pixelRatio": 3.0},
                "userAgent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15"
            }
            chrome_options.add_experimental_option("mobileEmulation", mobile_emulation)
        else:
            chrome_options.add_argument('--window-size=1920,1080')

        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        self.driver.implicitly_wait(10)

        logger.info("✓ Driver pronto")

    def take_screenshot(self, name: str, delay: float = 1.0) -> Path:
        """Cattura screenshot con delay"""
        time.sleep(delay)

        filepath = self.screenshots_dir / f"{self.screenshot_index:03d}_{name}.png"
        self.driver.save_screenshot(str(filepath))
        self.screenshot_index += 1

        logger.info(f"📸 Screenshot salvato: {name}")
        return filepath

    def scroll_slowly(self, pixels: int = 300, steps: int = 5):
        """Scroll animato per mostrare contenuto"""
        for i in range(steps):
            self.driver.execute_script(f"window.scrollBy(0, {pixels // steps});")
            time.sleep(0.3)

    def simulate_typing(self, element, text: str, speed: float = 0.1):
        """Simula digitazione carattere per carattere"""
        for char in text:
            element.send_keys(char)
            time.sleep(speed)

    def record_demo_flow(self):
        """Registra il flusso completo della demo"""
        if not self.driver:
            raise RuntimeError("Driver non inizializzato. Chiama setup_driver() prima.")

        logger.info("🎬 Inizio registrazione demo flow...")

        # ==================================================================
        # SCENE 1: LOGIN PAGE
        # ==================================================================
        logger.info("Scene 1: Login page")
        self.driver.get(f"{self.base_url}/login")
        time.sleep(2)
        self.take_screenshot("01_login_page", delay=1)

        # Compila form login (se necessario)
        try:
            username_field = self.driver.find_element(By.NAME, "username")
            password_field = self.driver.find_element(By.NAME, "password")

            self.simulate_typing(username_field, "demo@rootingfuture.com", speed=0.05)
            self.take_screenshot("02_username_entered", delay=0.5)

            self.simulate_typing(password_field, "********", speed=0.05)
            self.take_screenshot("03_password_entered", delay=0.5)

            login_button = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
            login_button.click()
            time.sleep(2)
        except Exception as e:
            logger.warning(f"Login flow skipped: {e}")

        # ==================================================================
        # SCENE 2: DASHBOARD PRINCIPALE
        # ==================================================================
        logger.info("Scene 2: Dashboard")
        self.driver.get(f"{self.base_url}/")
        time.sleep(3)
        self.take_screenshot("04_dashboard_home", delay=1)

        # Scroll per mostrare features
        self.scroll_slowly(400, steps=8)
        self.take_screenshot("05_dashboard_scrolled", delay=1)

        # ==================================================================
        # SCENE 3: GENERAZIONE PIANO - FORM
        # ==================================================================
        logger.info("Scene 3: Form generazione piano")

        try:
            # Click sul pulsante "Genera Piano" o simile
            generate_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Genera') or contains(text(), 'Nuovo Piano')]"))
            )
            generate_button.click()
            time.sleep(2)
            self.take_screenshot("06_generation_form", delay=1)

            # Compila form
            club_name_input = self.driver.find_element(By.NAME, "club_name")
            self.simulate_typing(club_name_input, self.demo_club["club_name"], speed=0.08)
            self.take_screenshot("07_club_name_entered", delay=0.5)

            # Categoria
            category_select = self.driver.find_element(By.NAME, "category")
            category_select.click()
            time.sleep(0.5)
            category_option = self.driver.find_element(By.XPATH, f"//option[text()='{self.demo_club['category']}']")
            category_option.click()
            self.take_screenshot("08_category_selected", delay=0.5)

            # Scroll form
            self.scroll_slowly(300, steps=5)
            self.take_screenshot("09_form_scrolled", delay=1)

            # Submit
            submit_button = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
            submit_button.click()
            time.sleep(2)
            self.take_screenshot("10_generation_started", delay=1)

        except Exception as e:
            logger.warning(f"Form interaction failed: {e}")

        # ==================================================================
        # SCENE 4: PROGRESSO GENERAZIONE
        # ==================================================================
        logger.info("Scene 4: Progress monitoring")

        # Attendi e cattura progress (simulato, adatta al tuo sistema)
        for i in range(6):
            time.sleep(3)
            self.take_screenshot(f"11_progress_{i+1}", delay=0.5)

        # ==================================================================
        # SCENE 5: PIANO COMPLETATO
        # ==================================================================
        logger.info("Scene 5: Piano strategico generato")

        # Naviga al piano (se redirect automatico, skippa questo)
        try:
            self.driver.get(f"{self.base_url}/plans")
            time.sleep(3)
            self.take_screenshot("12_plans_list", delay=1)

            # Click sul primo piano
            first_plan = self.driver.find_element(By.CSS_SELECTOR, ".plan-card, .plan-item, tr[data-plan-id]")
            first_plan.click()
            time.sleep(3)
            self.take_screenshot("13_plan_detail", delay=2)

            # Scroll attraverso il piano
            for i in range(10):
                self.scroll_slowly(400, steps=3)
                self.take_screenshot(f"14_plan_section_{i+1}", delay=0.5)

        except Exception as e:
            logger.warning(f"Plan view failed: {e}")

        # ==================================================================
        # SCENE 6: EXPORT E DOWNLOAD
        # ==================================================================
        logger.info("Scene 6: Export options")

        try:
            # Cerca bottone export
            export_button = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Export') or contains(text(), 'Download')]")
            export_button.click()
            time.sleep(2)
            self.take_screenshot("15_export_menu", delay=1)

        except Exception as e:
            logger.warning(f"Export flow failed: {e}")

        logger.info("✅ Registrazione completata!")

    def create_video_from_screenshots(self, fps: int = 2, duration_per_frame: float = 2.0):
        """Crea video MP4 dagli screenshots"""
        if not CV_AVAILABLE:
            logger.error("OpenCV non disponibile. Installa con: pip install opencv-python")
            return None

        logger.info("🎞️ Creazione video da screenshots...")

        screenshots = sorted(self.screenshots_dir.glob("*.png"))
        if not screenshots:
            logger.error("Nessuno screenshot trovato!")
            return None

        # Leggi primo screenshot per dimensioni
        first_frame = cv2.imread(str(screenshots[0]))
        height, width, layers = first_frame.shape

        # Output video path
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_video = self.output_dir / f"rooting_future_demo_{timestamp}.mp4"

        # Video writer
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        video = cv2.VideoWriter(str(output_video), fourcc, fps, (width, height))

        # Aggiungi frames
        for screenshot in screenshots:
            img = cv2.imread(str(screenshot))

            # Ripeti frame per durata desiderata
            for _ in range(int(fps * duration_per_frame)):
                video.write(img)

        video.release()

        logger.info(f"✅ Video creato: {output_video}")
        logger.info(f"   Dimensioni: {width}x{height}")
        logger.info(f"   Frame: {len(screenshots)}")
        logger.info(f"   Durata: ~{len(screenshots) * duration_per_frame:.1f}s")

        return output_video

    def cleanup(self):
        """Chiudi browser"""
        if self.driver:
            self.driver.quit()
            logger.info("Browser chiuso")

    def run_full_demo(self, mobile_view: bool = True):
        """Esegui demo completa"""
        try:
            self.setup_driver(mobile_view=mobile_view)
            self.record_demo_flow()
            video_path = self.create_video_from_screenshots(fps=1, duration_per_frame=2.5)

            return video_path

        except Exception as e:
            logger.error(f"Errore durante demo: {e}")
            raise

        finally:
            self.cleanup()


def main():
    """Entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Genera video demo di Rooting Future")
    parser.add_argument("--url", default="http://127.0.0.1:5000", help="URL base dell'app")
    parser.add_argument("--mobile", action="store_true", default=True, help="Usa viewport mobile")
    parser.add_argument("--output", default="demo_output", help="Directory output")

    args = parser.parse_args()

    print("=" * 60)
    print("  ROOTING FUTURE - DEMO VIDEO CREATOR")
    print("=" * 60)
    print()
    print(f"🌐 URL: {args.url}")
    print(f"📱 Mobile view: {args.mobile}")
    print(f"📁 Output: {args.output}")
    print()
    print("⚠️  ASSICURATI CHE L'APP SIA RUNNING SU", args.url)
    print()

    input("Premi INVIO per iniziare la registrazione...")

    creator = DemoVideoCreator(base_url=args.url, output_dir=args.output)

    try:
        video_path = creator.run_full_demo(mobile_view=args.mobile)

        print()
        print("=" * 60)
        print("✅ DEMO COMPLETATA CON SUCCESSO!")
        print("=" * 60)
        print()
        if video_path:
            print(f"📹 Video salvato in: {video_path}")
        print(f"📸 Screenshots disponibili in: {creator.screenshots_dir}")
        print()
        print("💡 TIP: Condividi il video via WhatsApp, Email o cloud storage")
        print()

    except Exception as e:
        print()
        print(f"❌ Errore: {e}")
        print()
        print("TROUBLESHOOTING:")
        print("1. Verifica che l'app sia running su", args.url)
        print("2. Installa dipendenze: pip install selenium webdriver-manager opencv-python pillow")
        print("3. Verifica Chrome/Chromium installato")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
