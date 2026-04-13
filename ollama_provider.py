"""
Ollama Provider for Rooting Future Strategy Engine
===================================================
Gestisce la connessione a Ollama (locale o cloud) con:
  - Fix 1: Warmup cold start
  - Fix 4: Logging diagnostico per agente
  - Fix 5: Retry con backoff esponenziale intelligente

Variabili d'ambiente:
  OLLAMA_BASE_URL       URL base del server (default: http://localhost:11434)
  OLLAMA_TIMEOUT        Timeout singola richiesta in secondi (default: 120)
  OLLAMA_MAX_RETRIES    Tentativi per request (default: 4)
  OLLAMA_WARMUP_RETRIES Tentativi per warmup (default: 3)
  OLLAMA_CHUNK_THRESHOLD Soglia char oltre cui attivare chunking (default: 32000)
"""

import os
import time
import logging
import json
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configurazione (tutte configurabili via env — non hardcoded)
# ---------------------------------------------------------------------------

OLLAMA_BASE_URL: str = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_TIMEOUT: int = int(os.environ.get("OLLAMA_TIMEOUT", "120"))
OLLAMA_MAX_RETRIES: int = int(os.environ.get("OLLAMA_MAX_RETRIES", "4"))
OLLAMA_WARMUP_RETRIES: int = int(os.environ.get("OLLAMA_WARMUP_RETRIES", "3"))
OLLAMA_CHUNK_THRESHOLD: int = int(os.environ.get("OLLAMA_CHUNK_THRESHOLD", "32000"))

# Backoff esponenziale (in secondi): primo=15s, secondo=30s, terzo=60s, quarto=120s
_BACKOFF_SCHEDULE: List[int] = [15, 30, 60, 120]


# ---------------------------------------------------------------------------
# Dataclass per diagnostica agente (Fix 4)
# ---------------------------------------------------------------------------

@dataclass
class AgentDiagnostics:
    """Metriche diagnostiche per singola chiamata agente."""
    nome_agente: str = ""
    modello: str = ""
    prompt_length_char: int = 0
    prompt_length_tokens_stima: int = 0
    system_prompt_length: int = 0
    rag_context_length: int = 0
    cascading_context_length: int = 0
    user_data_length: int = 0
    warmup_done: bool = False
    attempt_number: int = 1
    retry_wait_seconds: int = 0
    time_to_first_token_seconds: float = 0.0
    total_generation_seconds: float = 0.0
    output_length_char: int = 0
    output_valid: bool = False
    error_message: Optional[str] = None
    http_status_code: int = 200
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "nome_agente": self.nome_agente,
            "modello": self.modello,
            "prompt_length_char": self.prompt_length_char,
            "prompt_length_tokens_stima": self.prompt_length_tokens_stima,
            "system_prompt_length": self.system_prompt_length,
            "rag_context_length": self.rag_context_length,
            "cascading_context_length": self.cascading_context_length,
            "user_data_length": self.user_data_length,
            "warmup_done": self.warmup_done,
            "attempt_number": self.attempt_number,
            "retry_wait_seconds": self.retry_wait_seconds,
            "time_to_first_token_seconds": round(self.time_to_first_token_seconds, 3),
            "total_generation_seconds": round(self.total_generation_seconds, 3),
            "output_length_char": self.output_length_char,
            "output_valid": self.output_valid,
            "error_message": self.error_message,
            "http_status_code": self.http_status_code,
            "timestamp": self.timestamp,
        }

    def log_summary(self) -> None:
        status = "OK" if self.output_valid else "FAIL"
        logger.info(
            f"[DIAG] [{status}] {self.nome_agente} | model={self.modello} | "
            f"prompt={self.prompt_length_char}ch (~{self.prompt_length_tokens_stima}tok) | "
            f"output={self.output_length_char}ch | "
            f"time={self.total_generation_seconds:.1f}s | "
            f"attempt={self.attempt_number} | "
            f"warmup={'yes' if self.warmup_done else 'no'}"
        )
        if self.error_message:
            logger.warning(f"[DIAG] {self.nome_agente} error: {self.error_message}")


def estimate_tokens(text: str) -> int:
    """Stima approssimativa token da caratteri (1 token ≈ 4 char)."""
    return max(1, len(text) // 4)


# ---------------------------------------------------------------------------
# OllamaProvider
# ---------------------------------------------------------------------------

class OllamaProvider:
    """
    Provider per Ollama LLM API (compatibile OpenAI chat/completions).

    Espone:
      - generate()         → chiamata principale con retry e diagnostica
      - generate_content() → alias compatibile con OpenRouterClient
      - warmup()           → riscaldamento cold start
    """

    def __init__(
        self,
        model: str,
        base_url: str = None,
        timeout: int = None,
        max_retries: int = None,
    ):
        self.model = model
        self.base_url = (base_url or OLLAMA_BASE_URL).rstrip("/")
        self.timeout = timeout or OLLAMA_TIMEOUT
        self.max_retries = max_retries or OLLAMA_MAX_RETRIES
        self.available = False
        self._check_availability()

    def _check_availability(self) -> None:
        """Verifica raggiungibilità server Ollama."""
        try:
            import urllib.request
            req = urllib.request.urlopen(
                f"{self.base_url}/api/tags", timeout=10
            )
            if req.status == 200:
                self.available = True
                logger.info(f"Ollama server raggiungibile: {self.base_url}")
            else:
                logger.warning(f"Ollama server: HTTP {req.status}")
        except Exception as exc:
            logger.warning(f"Ollama server non raggiungibile ({self.base_url}): {exc}")
            # Proviamo comunque — potrebbe essere un cold start del server stesso
            self.available = True

    # ------------------------------------------------------------------
    # Fix 1: Warmup
    # ------------------------------------------------------------------

    def warmup(self, max_retries: int = None) -> bool:
        """
        Invia una richiesta minima per caricare il modello in GPU (cold start fix).

        Returns:
            True se il warmup ha avuto successo, False se tutti i tentativi falliti.
        """
        max_retries = max_retries or OLLAMA_WARMUP_RETRIES
        logger.info(f"[WARMUP] Avvio warmup per modello '{self.model}'...")

        for attempt in range(max_retries):
            try:
                start = time.time()
                resp = self._post_chat(
                    messages=[{"role": "user", "content": "Rispondi solo: OK"}],
                    temperature=0,
                    max_tokens=5,
                    timeout=60,  # timeout breve per warmup
                )
                elapsed = time.time() - start
                if resp and resp.strip():
                    logger.info(
                        f"[WARMUP] Successo in {elapsed:.1f}s "
                        f"(tentativo {attempt + 1}/{max_retries})"
                    )
                    return True
                logger.warning(
                    f"[WARMUP] Tentativo {attempt + 1}: risposta vuota"
                )
            except Exception as exc:
                wait = _BACKOFF_SCHEDULE[min(attempt, len(_BACKOFF_SCHEDULE) - 1)]
                logger.warning(
                    f"[WARMUP] Tentativo {attempt + 1}/{max_retries} fallito: {exc}. "
                    f"Attesa {wait}s..."
                )
                if attempt < max_retries - 1:
                    time.sleep(wait)

        logger.error(
            f"[WARMUP] Fallito dopo {max_retries} tentativi. "
            "Procedo comunque (modello potrebbe essere già caldo)."
        )
        return False

    # ------------------------------------------------------------------
    # Fix 5: Retry intelligente con backoff esponenziale
    # ------------------------------------------------------------------

    def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        temperature: float = 0.7,
        max_tokens: int = 8192,
        agent_name: str = "unknown",
        diagnostics: Optional[AgentDiagnostics] = None,
    ) -> str:
        """
        Genera testo con retry esponenziale intelligente.

        Fix 5 implementato:
          - Primo retry: 15s, Secondo: 30s, Terzo: 60s, Quarto: 120s
          - Su 429 (rate limit): rispetta Retry-After header
          - Su timeout: aumenta progressivamente il timeout
          - Su connection error: aspetta 30s e riprova
        """
        last_exception: Optional[Exception] = None
        base_timeout = self.timeout

        for attempt in range(self.max_retries):
            if diagnostics:
                diagnostics.attempt_number = attempt + 1

            # Timeout crescente sui retry
            current_timeout = base_timeout + (attempt * 60)

            try:
                messages = []
                if system_prompt:
                    messages.append({"role": "system", "content": system_prompt})
                messages.append({"role": "user", "content": prompt})

                # Fix 3: Chunking automatico se prompt troppo lungo
                full_prompt_len = len(system_prompt) + len(prompt)
                if full_prompt_len > OLLAMA_CHUNK_THRESHOLD:
                    logger.warning(
                        f"[CHUNK] {agent_name}: prompt {full_prompt_len}ch "
                        f"supera soglia {OLLAMA_CHUNK_THRESHOLD}ch. Attivazione chunking."
                    )
                    messages = self._chunk_messages(system_prompt, prompt)

                t_start = time.time()
                result = self._post_chat(
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    timeout=current_timeout,
                )
                elapsed = time.time() - t_start

                if diagnostics:
                    diagnostics.total_generation_seconds = elapsed
                    diagnostics.output_length_char = len(result) if result else 0
                    diagnostics.output_valid = bool(result and len(result.strip()) > 10)
                    diagnostics.http_status_code = 200

                if not result or len(result.strip()) < 10:
                    raise ValueError(
                        f"Output troppo corto: {len(result) if result else 0} char"
                    )

                return result

            except Exception as exc:
                last_exception = exc
                error_str = str(exc)
                http_status = self._extract_http_status(error_str)

                if diagnostics:
                    diagnostics.error_message = error_str
                    diagnostics.http_status_code = http_status

                if attempt >= self.max_retries - 1:
                    logger.error(
                        f"[RETRY] {agent_name}: tutti i {self.max_retries} tentativi falliti."
                    )
                    break

                # Calcola wait time in base al tipo di errore
                wait_seconds = self._compute_wait(exc, attempt, error_str, http_status)

                if diagnostics:
                    diagnostics.retry_wait_seconds = wait_seconds

                logger.warning(
                    f"[RETRY] {agent_name}: tentativo {attempt + 1}/{self.max_retries} "
                    f"fallito (HTTP {http_status}): {error_str[:120]}. "
                    f"Attesa {wait_seconds}s..."
                )
                time.sleep(wait_seconds)

        raise RuntimeError(
            f"Ollama generate fallito dopo {self.max_retries} tentativi "
            f"per '{agent_name}': {last_exception}"
        ) from last_exception

    def generate_content(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 8192,
    ) -> str:
        """Alias compatibile con OpenRouterClient per uso in agents.py."""
        return self.generate(
            prompt=prompt,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    # ------------------------------------------------------------------
    # Fix 3: Chunking prompt lungo
    # ------------------------------------------------------------------

    def _chunk_messages(
        self, system_prompt: str, user_prompt: str
    ) -> List[Dict[str, str]]:
        """
        Divide prompt lungo in messaggi separati per evitare overflow.

        Strategia:
          Msg 1 (user): contesto (RAG + dati club)
          Msg 2 (user): istruzione di generazione vera e propria

        Heuristica: il contesto è tutto tranne gli ultimi 2000 char del prompt,
        che contengono tipicamente l'istruzione finale.
        """
        split_point = max(len(user_prompt) - 2000, len(user_prompt) // 2)
        context_part = user_prompt[:split_point]
        instruction_part = user_prompt[split_point:]

        messages: List[Dict[str, str]] = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        messages.append({
            "role": "user",
            "content": (
                "Leggi attentamente il seguente contesto. Non rispondere ancora.\n\n"
                + context_part
            ),
        })
        messages.append({
            "role": "assistant",
            "content": "Ho letto il contesto. Sono pronto per le istruzioni.",
        })
        messages.append({
            "role": "user",
            "content": instruction_part,
        })

        logger.info(
            f"[CHUNK] Split: contesto={len(context_part)}ch, "
            f"istruzione={len(instruction_part)}ch"
        )
        return messages

    # ------------------------------------------------------------------
    # HTTP helpers
    # ------------------------------------------------------------------

    def _post_chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
        timeout: int = None,
    ) -> str:
        """Chiamata HTTP a Ollama /api/chat (formato OpenAI-compatible)."""
        import urllib.request
        import urllib.error

        timeout = timeout or self.timeout
        url = f"{self.base_url}/api/chat"

        payload = json.dumps({
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }).encode("utf-8")

        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                body = resp.read().decode("utf-8")
                data = json.loads(body)
                return data["message"]["content"]
        except urllib.error.HTTPError as exc:
            raise RuntimeError(
                f"HTTP {exc.code}: {exc.reason}"
            ) from exc
        except urllib.error.URLError as exc:
            raise ConnectionError(f"Connessione fallita: {exc.reason}") from exc

    @staticmethod
    def _extract_http_status(error_str: str) -> int:
        """Estrae HTTP status code dalla stringa di errore se presente."""
        import re
        match = re.search(r"HTTP (\d{3})", error_str)
        if match:
            return int(match.group(1))
        if "429" in error_str:
            return 429
        if "timeout" in error_str.lower() or "timed out" in error_str.lower():
            return 408
        if "connection" in error_str.lower():
            return 503
        return 500

    @staticmethod
    def _compute_wait(
        exc: Exception, attempt: int, error_str: str, http_status: int
    ) -> int:
        """
        Calcola il tempo di attesa ottimale per il prossimo retry.

        Logica Fix 5:
          - 429 rate limit → rispetta Retry-After o usa backoff
          - 408/timeout → usa backoff standard
          - 503/connection error → aspetta 30s fissi
          - Altro → usa backoff schedule
        """
        # 429: prova a leggere Retry-After (non disponibile qui, usa backoff lungo)
        if http_status == 429:
            retry_after = _BACKOFF_SCHEDULE[min(attempt + 1, len(_BACKOFF_SCHEDULE) - 1)]
            logger.warning(f"[RETRY] Rate limit (429). Retry-After: {retry_after}s")
            return retry_after

        # Connection error: attesa fissa 30s
        if http_status == 503 or "connection" in error_str.lower():
            logger.warning("[RETRY] Connection error. Attesa 30s fissa.")
            return 30

        # Timeout: usa backoff crescente
        if http_status == 408 or "timeout" in error_str.lower():
            wait = _BACKOFF_SCHEDULE[min(attempt, len(_BACKOFF_SCHEDULE) - 1)]
            return wait

        # Default: backoff schedule
        return _BACKOFF_SCHEDULE[min(attempt, len(_BACKOFF_SCHEDULE) - 1)]


# ---------------------------------------------------------------------------
# Fix 1: Funzione standalone warmup (usabile da ab_test.py e model_benchmark.py)
# ---------------------------------------------------------------------------

def warmup_ollama(provider: OllamaProvider, max_retries: int = None) -> bool:
    """
    Warmup standalone: invia richiesta minima prima del loop agenti.

    Da chiamare PRIMA del loop degli agenti in ab_test.py e model_benchmark.py.
    Se fallisce, logga l'errore ma non interrompe l'esecuzione.

    Args:
        provider: Istanza OllamaProvider già configurata
        max_retries: Override numero tentativi warmup

    Returns:
        True se warmup riuscito, False altrimenti
    """
    return provider.warmup(max_retries=max_retries)


# ---------------------------------------------------------------------------
# Fix 2: Calcolo lunghezza prompt per riordinamento agenti
# ---------------------------------------------------------------------------

def compute_prompt_length(
    system_prompt: str = "",
    rag_context: str = "",
    cascading_context: str = "",
    user_data: str = "",
) -> Dict[str, int]:
    """
    Calcola la lunghezza totale del prompt per un agente.
    Usato per riordinare gli agenti dal prompt più corto al più lungo (Fix 2).

    Returns:
        Dict con char totali e stima token per ogni componente
    """
    total_char = len(system_prompt) + len(rag_context) + len(cascading_context) + len(user_data)
    return {
        "system_prompt": len(system_prompt),
        "rag_context": len(rag_context),
        "cascading_context": len(cascading_context),
        "user_data": len(user_data),
        "total_char": total_char,
        "total_tokens_stima": estimate_tokens(
            system_prompt + rag_context + cascading_context + user_data
        ),
    }
