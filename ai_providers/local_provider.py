"""
Rooting Future — Local Embedding Provider
EmbeddingProvider via sentence-transformers (lazy loading, no pickle cache).
Il modello si carica in RAM solo alla prima chiamata.
"""

import logging
import os
from typing import List, Optional

from .interfaces import EmbeddingProvider

logger = logging.getLogger(__name__)

# Modello di default: google/gemma-embedding-exp-03-07 o fallback leggero
# L'utente può sovrascrivere con env var EMBEDDING_MODEL
_DEFAULT_EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


class LocalEmbeddingProvider(EmbeddingProvider):
    """
    Genera embedding localmente via sentence-transformers.

    Configurazione env vars:
      EMBEDDING_MODEL  — Nome modello HuggingFace (default: all-MiniLM-L6-v2)
      EMBEDDING_DIM    — Dimensione vettore attesa (default: 768, 384 per MiniLM)

    Note:
      - Il modello viene scaricato da HuggingFace al primo utilizzo
      - Lazy loading: caricato in RAM solo alla prima chiamata embed_text/embed_batch
      - NON usa pickle: ChromaDB gestisce la persistenza dei vettori
      - I vettori sono normalizzati L2
    """

    def __init__(
        self,
        model_name: Optional[str] = None,
    ):
        self._model_name = (
            model_name
            or os.environ.get("EMBEDDING_MODEL", _DEFAULT_EMBEDDING_MODEL)
        )
        self._model = None  # lazy loading
        self._available: Optional[bool] = None  # None = non ancora verificato

        # Verifica che sentence-transformers sia installato (senza caricare il modello)
        try:
            import sentence_transformers  # noqa: F401
            self._lib_available = True
        except ImportError:
            self._lib_available = False
            logger.warning(
                "LocalEmbeddingProvider: sentence-transformers non installato. "
                "pip install sentence-transformers"
            )

    def _load_model(self) -> bool:
        """Carica il modello in RAM (solo alla prima chiamata). Restituisce True se ok."""
        if self._model is not None:
            return True
        if not self._lib_available:
            return False

        try:
            from sentence_transformers import SentenceTransformer
            logger.info(f"LocalEmbeddingProvider: carico modello '{self._model_name}'...")
            self._model = SentenceTransformer(self._model_name)
            self._available = True
            logger.info("LocalEmbeddingProvider: modello caricato.")
            return True
        except Exception as e:
            logger.error(f"LocalEmbeddingProvider: errore caricamento modello: {e}")
            self._available = False
            return False

    def embed_text(self, text: str) -> Optional[List[float]]:
        if not self._load_model() or self._model is None:
            return None
        try:
            embedding = self._model.encode(text, normalize_embeddings=True)
            return embedding.tolist()
        except Exception as e:
            logger.error(f"LocalEmbeddingProvider.embed_text error: {e}")
            return None

    def embed_batch(self, texts: List[str]) -> List[Optional[List[float]]]:
        if not self._load_model() or self._model is None:
            return [None] * len(texts)
        try:
            embeddings = self._model.encode(texts, normalize_embeddings=True)
            return [e.tolist() for e in embeddings]
        except Exception as e:
            logger.error(f"LocalEmbeddingProvider.embed_batch error: {e}")
            return [None] * len(texts)
