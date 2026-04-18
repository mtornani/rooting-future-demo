"""
Rooting Future — Ollama Provider
GenerationProvider via Ollama (API OpenAI-compatible).
Supporta Ollama locale e Ollama cloud con la stessa implementazione.
Fallback automatico a Gemini se Ollama non risponde.
"""

import json
import logging
import os
import time
from typing import Any, Dict, Optional

from .interfaces import GenerationProvider

logger = logging.getLogger(__name__)

try:
    from openai import OpenAI as _OpenAI
    OPENAI_LIB_AVAILABLE = True
except ImportError:
    OPENAI_LIB_AVAILABLE = False
    _OpenAI = None


class OllamaGenerationProvider(GenerationProvider):
    """
    Genera testo via Ollama (API /v1/chat/completions, formato OpenAI-compatible).

    Configurazione env vars:
      OLLAMA_BASE_URL  — URL base Ollama (default: http://localhost:11434)
      OLLAMA_MODEL     — Modello da usare (default: gemma4:26b)
      OLLAMA_API_KEY   — API key per Ollama cloud (opzionale)

    Se OLLAMA_BASE_URL=https://ollama.com e OLLAMA_API_KEY presente:
      → aggiunge header Authorization: Bearer <key>

    Fallback: se Ollama non risponde entro 60s e GEMINI_API_KEY presente,
    delega a GeminiGenerationProvider.
    """

    TIMEOUT = int(os.environ.get("OLLAMA_TIMEOUT", "300"))  # default 300s (configurabile)

    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        self._base_url = (
            base_url
            or os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
        ).rstrip("/")
        self._model = model or os.environ.get("OLLAMA_MODEL", "gemma3:27b")
        self._api_key = api_key or os.environ.get("OLLAMA_API_KEY", "")
        self._available = False
        self._client = None
        self._fallback: Optional[GenerationProvider] = None

        if not OPENAI_LIB_AVAILABLE:
            logger.warning("OllamaGenerationProvider: libreria 'openai' non installata. pip install openai")
            return

        try:
            # Non aggiungere /v1 se l'URL lo contiene già (Groq, OpenRouter, etc.)
            _base = self._base_url.rstrip("/")
            _api_base = _base if _base.endswith("/v1") else f"{_base}/v1"
            client_kwargs: Dict[str, Any] = {
                "base_url": _api_base,
                "api_key": self._api_key or "ollama",  # Ollama locale accetta qualsiasi stringa
                "timeout": self.TIMEOUT,
            }
            client_kwargs["max_retries"] = 3  # Ollama cloud droppa prima connessione
            self._client = _OpenAI(**client_kwargs)
            self._available = True
            logger.info(
                f"OllamaGenerationProvider: pronto (url={_api_base}, model={self._model})"
            )
        except Exception as e:
            logger.error(f"OllamaGenerationProvider init error: {e}")

        # Prepara fallback Gemini
        gemini_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY", "")
        if gemini_key:
            try:
                from .gemini_provider import GeminiGenerationProvider
                self._fallback = GeminiGenerationProvider(api_key=gemini_key)
                logger.info("OllamaGenerationProvider: fallback Gemini configurato")
            except Exception as e:
                logger.warning(f"OllamaGenerationProvider: fallback Gemini non disponibile: {e}")

    @property
    def available(self) -> bool:
        return self._available or (self._fallback is not None and self._fallback.available)

    def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        temperature: float = 0.7,
        max_tokens: int = 8192,
    ) -> str:
        if not self._available or not self._client:
            if self._fallback and self._fallback.available:
                logger.warning("OllamaGenerationProvider: non disponibile, uso fallback Gemini")
                return self._fallback.generate(prompt, system_prompt, temperature, max_tokens)
            raise RuntimeError("OllamaGenerationProvider non disponibile e nessun fallback")

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        # Retry con backoff per 429 (rate limit) — comune su modelli free OpenRouter
        max_retries = int(os.environ.get("OLLAMA_MAX_RETRIES", "5"))
        backoff = [10, 20, 40, 60, 90]  # secondi

        last_exc: Exception = RuntimeError("nessuna chiamata effettuata")
        for attempt in range(max_retries):
            try:
                t0 = time.time()
                response = self._client.chat.completions.create(
                    model=self._model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                elapsed = time.time() - t0
                logger.info(f"OllamaGenerationProvider: risposta in {elapsed:.1f}s")
                return response.choices[0].message.content

            except Exception as e:
                last_exc = e
                err_str = str(e)
                is_rate_limit = "429" in err_str or "rate" in err_str.lower() or "Rate" in err_str
                if is_rate_limit and attempt < max_retries - 1:
                    wait = backoff[min(attempt, len(backoff) - 1)]
                    logger.warning(f"OllamaGenerationProvider: rate limit (attempt {attempt+1}/{max_retries}), attendo {wait}s...")
                    print(f"    [rate limit] attendo {wait}s prima di riprovare...")
                    time.sleep(wait)
                    continue
                break

        logger.error(f"OllamaGenerationProvider.generate error: {last_exc}")
        if self._fallback and self._fallback.available:
            logger.warning("OllamaGenerationProvider: errore, uso fallback Gemini")
            return self._fallback.generate(prompt, system_prompt, temperature, max_tokens)
        raise last_exc

    def generate_structured(
        self,
        prompt: str,
        system_prompt: str = "",
        temperature: float = 0.7,
        max_tokens: int = 8192,
    ) -> Dict[str, Any]:
        raw = self.generate(prompt, system_prompt, temperature, max_tokens)
        try:
            cleaned = raw.strip()
            if cleaned.startswith("```"):
                lines = cleaned.split("\n")
                cleaned = "\n".join(lines[1:-1])
            return json.loads(cleaned)
        except Exception:
            return {"raw_content": raw}
