"""
Rooting Future — Gemini Provider
Wrapper delle chiamate Gemini esistenti, conforme alle interfacce astratte.
NON importa da knowledge_store o agents (evita dipendenze circolari).
"""

import json
import logging
import os
from typing import Any, Dict, List, Optional

from .interfaces import EmbeddingProvider, GenerationProvider

logger = logging.getLogger(__name__)

try:
    import google.generativeai as genai
    import google.genai as genai_new
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False
    genai = None
    genai_new = None

# Modelli preferiti in ordine decrescente di preferenza
_PREFERRED_MODELS = [
    "gemini-2.5-flash",
    "gemini-2.0-flash-001",
    "gemini-2.0-flash-lite",
    "gemini-1.5-flash",
]


def detect_best_gemini_model(api_key: str) -> str:
    """Interroga l'API Gemini e restituisce il miglior modello disponibile."""
    if not GENAI_AVAILABLE or not api_key:
        return "gemini-2.0-flash-001"
    try:
        genai.configure(api_key=api_key)
        available = {m.name for m in genai.list_models()}
        for model in _PREFERRED_MODELS:
            if f"models/{model}" in available:
                logger.info(f"detect_best_gemini_model: selezionato {model}")
                return model
    except Exception as e:
        logger.warning(f"detect_best_gemini_model: impossibile listare modelli ({e}), uso default")
    return "gemini-2.0-flash-001"


class GeminiEmbeddingProvider(EmbeddingProvider):
    """
    Genera embedding via google-genai (stessa logica di knowledge_store.py:1112).
    Usa il client google.genai nuovo, NON google.generativeai.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        embedding_model: str = "models/embedding-001",
    ):
        self._api_key = api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY", "")
        self._embedding_model = embedding_model
        self._available = False
        self._client = None

        if not GENAI_AVAILABLE:
            logger.warning("GeminiEmbeddingProvider: google-genai non installato.")
            return
        if not self._api_key:
            logger.warning("GeminiEmbeddingProvider: GEMINI_API_KEY mancante.")
            return

        try:
            self._client = genai_new.Client(api_key=self._api_key)
            self._available = True
        except Exception as e:
            logger.error(f"GeminiEmbeddingProvider init error: {e}")

    def embed_text(self, text: str) -> Optional[List[float]]:
        if not self._available or not self._client:
            return None
        try:
            result = self._client.models.embed_content(
                model=self._embedding_model,
                contents=text,
                config={"task_type": "RETRIEVAL_DOCUMENT"},
            )
            return list(result.embeddings[0].values)
        except Exception as e:
            logger.error(f"GeminiEmbeddingProvider.embed_text error: {e}")
            return None

    def embed_batch(self, texts: List[str]) -> List[Optional[List[float]]]:
        return [self.embed_text(t) for t in texts]


class GeminiGenerationProvider(GenerationProvider):
    """
    Genera testo via google.generativeai (stessa logica di agents.py).
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
    ):
        self._api_key = api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY", "")
        self._available = False
        self._model = None
        self._model_name = model_name or ""

        if not GENAI_AVAILABLE:
            logger.warning("GeminiGenerationProvider: google-generativeai non installato.")
            return
        if not self._api_key:
            logger.warning("GeminiGenerationProvider: GEMINI_API_KEY mancante.")
            return

        # Auto-detect se il nome non è specificato o è quello deprecato
        _deprecated = {"gemini-2.0-flash", "gemini-pro"}
        if not self._model_name or self._model_name in _deprecated:
            self._model_name = detect_best_gemini_model(self._api_key)

        try:
            genai.configure(api_key=self._api_key)
            self._model = genai.GenerativeModel(self._model_name)
            self._available = True
            logger.info(f"GeminiGenerationProvider: pronto (model={self._model_name})")
        except Exception as e:
            logger.error(f"GeminiGenerationProvider init error: {e}")

    @property
    def available(self) -> bool:
        return self._available

    def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        temperature: float = 0.7,
        max_tokens: int = 8192,
    ) -> str:
        if not self._available or not self._model:
            raise RuntimeError("GeminiGenerationProvider non disponibile")

        full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
        response = self._model.generate_content(
            full_prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=temperature,
                max_output_tokens=max_tokens,
            ),
        )
        return response.text

    def generate_structured(
        self,
        prompt: str,
        system_prompt: str = "",
        temperature: float = 0.7,
        max_tokens: int = 8192,
    ) -> Dict[str, Any]:
        raw = self.generate(prompt, system_prompt, temperature, max_tokens)
        # Prova a parsare JSON dal testo
        try:
            # Rimuovi eventuali markdown code fences
            cleaned = raw.strip()
            if cleaned.startswith("```"):
                lines = cleaned.split("\n")
                cleaned = "\n".join(lines[1:-1])
            return json.loads(cleaned)
        except Exception:
            return {"raw_content": raw}
