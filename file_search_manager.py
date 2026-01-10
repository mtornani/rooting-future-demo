# rooting_future/file_search_manager.py

import time
import os
from pathlib import Path
import logging
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError

logger = logging.getLogger(__name__)

try:
    from google import genai
    from google.genai import types
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False

from config import GEMINI_API_KEY, FILE_SEARCH_STORE_ID_PATH

# Timeout per le operazioni API (in secondi)
API_TIMEOUT = 10

class FileSearchManager:
    """
    Gestisce la creazione, il recupero e l'upload di file
    nel File Search Store di Google Gemini.
    """

    def __init__(self):
        if not GENAI_AVAILABLE or not (GEMINI_API_KEY or os.environ.get("GOOGLE_API_KEY")):
            self.store_name = None
            self.client = None
            logger.warning("Gemini API non configurata. FileSearchManager è disabilitato.")
            return

        # Crea il client Gemini
        try:
            api_key = GEMINI_API_KEY or os.environ.get("GOOGLE_API_KEY")
            if not api_key:
                logger.warning("API key non trovata. FileSearchManager disabilitato.")
                self.client = None
                self.store_name = None
                return

            self.client = genai.Client(api_key=api_key)
            self.store_name = self._get_or_create_store()
            logger.info("FileSearchManager inizializzato correttamente con RAG abilitato")
        except Exception as e:
            logger.error(f"Errore creazione client Gemini: {e}")
            self.client = None
            self.store_name = None

    def _get_or_create_store(self) -> str | None:
        """
        Recupera il nome dello store da un file locale. Se non esiste,
        ne crea uno nuovo e salva il suo nome.
        Usa timeout per evitare blocchi.
        """
        if FILE_SEARCH_STORE_ID_PATH.exists():
            store_id = FILE_SEARCH_STORE_ID_PATH.read_text().strip()
            logger.info(f"Trovato File Search Store esistente: {store_id}")
            # Verifica che lo store esista ancora (con timeout)
            try:
                with ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(self.client.file_search_stores.get, name=store_id)
                    future.result(timeout=API_TIMEOUT)
                return store_id
            except FutureTimeoutError:
                logger.warning(f"Timeout verificando store {store_id}, lo uso comunque")
                return store_id
            except Exception as e:
                logger.warning(f"Store {store_id} non trovato ({e}), ne creo uno nuovo...")

        logger.info("Nessun File Search Store trovato. Creazione in corso...")
        try:
            # Crea lo store usando il config (con timeout)
            def create_store():
                return self.client.file_search_stores.create(
                    config=types.CreateFileSearchStoreConfig(
                        display_name="RootingFuture-KnowledgeBase"
                    )
                )

            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(create_store)
                store = future.result(timeout=API_TIMEOUT * 2)

            store_name = store.name
            FILE_SEARCH_STORE_ID_PATH.write_text(store_name)
            logger.info(f"Nuovo File Search Store creato e salvato: {store_name}")
            return store_name
        except FutureTimeoutError:
            logger.error("Timeout durante creazione File Search Store")
            return None
        except Exception as e:
            logger.error(f"Impossibile creare il File Search Store: {e}")
            return None

    def upload_file(self, file_path: Path) -> bool:
        """
        Carica un file nel File Search Store.
        """
        if not self.store_name or not self.client:
            logger.error("FileSearchManager non inizializzato, impossibile caricare il file.")
            return False

        if not file_path.exists():
            logger.error(f"File non trovato per l'upload: {file_path}")
            return False

        logger.info(f"Inizio upload del file '{file_path.name}' nello store '{self.store_name}'...")

        try:
            # Upload del file nello store
            upload_op = self.client.file_search_stores.upload_to_file_search_store(
                file_search_store_name=self.store_name,
                file=str(file_path)
            )

            timeout_seconds = 300
            start_time = time.time()

            while not upload_op.done:
                if time.time() - start_time > timeout_seconds:
                    logger.error(f"Timeout upload file '{file_path.name}'.")
                    return False
                time.sleep(5)
                # Aggiorna lo stato dell'operazione
                upload_op = self.client.operations.get(upload_op)

            if upload_op.error:
                 logger.error(f"Errore durante l'upload del file: {upload_op.error.message}")
                 return False

            logger.info(f"File '{file_path.name}' caricato e indicizzato con successo.")
            return True

        except Exception as e:
            logger.error(f"Errore imprevisto durante l'upload: {e}")

        return False

    def get_store_name(self) -> str | None:
        """Restituisce il nome dello store gestito."""
        return self.store_name

if __name__ == '__main__':
    # Test di base per il modulo
    logging.basicConfig(level=logging.INFO)
    logger.info("Esecuzione test del FileSearchManager...")

    if not GENAI_AVAILABLE or not GEMINI_API_KEY:
        logger.error("Test saltato: Le librerie Google o la API Key non sono configurate.")
    else:
        # Crea un file fittizio per il test
        dummy_dir = Path("output_test_rag")
        dummy_dir.mkdir(exist_ok=True)
        dummy_file = dummy_dir / "test_plan.txt"
        dummy_file.write_text("Questo è un piano strategico di test per il Rimini FC.")

        manager = FileSearchManager()
        if manager.get_store_name():
            logger.info(f"Manager inizializzato con store: {manager.get_store_name()}")
            success = manager.upload_file(dummy_file)
            if success:
                logger.info("Test di upload completato con successo.")
            else:
                logger.error("Test di upload fallito.")
        else:
            logger.error("Inizializzazione del manager fallita.")
