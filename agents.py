"""
Rooting Future Strategy Engine v5.4
Sistema Multi-Agente - 8 Agenti Specializzati

Architettura ispirata a metodologia consulenziale STW.
Ogni agente è esperto di un'area strategica specifica.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Callable, Tuple
from enum import Enum
from datetime import datetime
import logging
import asyncio
import json
import re
import time
from concurrent.futures import ThreadPoolExecutor
from threading import Semaphore

import os
try:
    import google.generativeai as genai
    from google.api_core.exceptions import InvalidArgument
    GENAI_AVAILABLE = True
except ImportError as e:
    logging.error(f"GENAI IMPORT ERROR: {e}")
    GENAI_AVAILABLE = False
    genai = None
    InvalidArgument = Exception  # Fallback type if import fails
except Exception as e:
    logging.error(f"GENAI UNEXPECTED ERROR: {e}")
    GENAI_AVAILABLE = False
    genai = None

# Serialize + throttle Gemini calls — free tier ~10 RPM = min 6s between calls
_gemini_semaphore = Semaphore(1)
_gemini_last_call = [0.0]   # mutable so inner methods can write without `global`
_GEMINI_MIN_INTERVAL = 7.0  # seconds between calls → max ~8 RPM, within free tier

from wiki_reader import WikiReader
from config import (
    GEMINI_API_KEY,
    MODEL_CONFIG,
    AGENT_CONFIG,
    BENCHMARKS,
    AI_PROVIDER,
    OPENROUTER_API_KEY,
    OPENROUTER_DEFAULT_MODEL,
    OPENROUTER_FALLBACK_MODEL,
    FREE_MODEL_CHAIN,
    HF_TOKEN,
    HF_MODEL,
    HF_MODEL_CHAIN,
    NVIDIA_API_KEY,
)
from data_sourcing import SourcedContentGenerator, DataSourcer
from data_estimator import estimate_missing_financials, DataTier
from domain.error_handling import (
    GeminiAPIError,
    GeminiRateLimitError,
    GeminiTimeoutError,
    GenerationError,
    AgentError,
    handle_exception,
    log_exception,
)

# Structured Logging (STAB-004)
try:
    from utils.logging_config import get_logger, log_agent_execution, timed_operation
    struct_logger = get_logger("agents")
except ImportError:
    struct_logger = None
    log_agent_execution = None
    timed_operation = None

logger = logging.getLogger(__name__)


# =============================================================================
# OPENROUTER CLIENT (compatibile OpenAI)
# =============================================================================

try:
    from openai import OpenAI as _OpenAI
    OPENAI_LIB_AVAILABLE = True
except ImportError:
    OPENAI_LIB_AVAILABLE = False
    _OpenAI = None

try:
    from huggingface_hub import InferenceClient as _HFInferenceClient
    HF_HUB_AVAILABLE = True
except ImportError:
    HF_HUB_AVAILABLE = False
    _HFInferenceClient = None


class OpenRouterClient:
    """
    Client per OpenRouter API (compatibile OpenAI).
    Usa la libreria openai puntando a https://openrouter.ai/api/v1
    """

    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or OPENROUTER_API_KEY
        self.model = model or OPENROUTER_DEFAULT_MODEL
        self.available = False

        if OPENAI_LIB_AVAILABLE and self.api_key:
            try:
                self.client = _OpenAI(
                    base_url="https://openrouter.ai/api/v1",
                    api_key=self.api_key,
                )
                self.available = True
            except Exception as e:
                logger.error(f"Errore inizializzazione OpenRouter client: {e}")
        else:
            if not OPENAI_LIB_AVAILABLE:
                logger.warning("Libreria openai non installata. Installa con: pip install openai")

    def generate_content(self, prompt: str, temperature: float = 0.7,
                         max_tokens: int = 8192) -> str:
        """
        Genera contenuto tramite OpenRouter.
        Tenta la catena FREE_MODEL_CHAIN in ordine su quota esaurita (429) o risposta vuota.
        """
        if not self.available:
            raise RuntimeError("OpenRouter client non disponibile")

        # Build chain: preferred model first, then rest of free chain (deduped)
        chain = [self.model] + [m for m in FREE_MODEL_CHAIN if m != self.model]

        last_error = None
        for model in chain:
            try:
                response = self.client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=temperature,
                    max_tokens=max_tokens,
                    extra_headers={
                        "HTTP-Referer": "https://rootingfuture.app",
                        "X-Title": "Rooting Future Strategy Engine",
                    },
                )
                content = response.choices[0].message.content or ""
                if content.strip():
                    if model != self.model:
                        logger.info(f"OpenRouter: fallback model {model} succeeded")
                    return content
                # Empty response → try next model
                logger.warning(f"OpenRouter: model {model} returned empty response, trying next")
            except Exception as e:
                logger.warning(f"OpenRouter: model {model} failed ({type(e).__name__}: {str(e)[:120]}), trying next")
                last_error = e

        raise RuntimeError(
            f"All models in FREE_MODEL_CHAIN exhausted. Last error: {last_error}"
        )


class HFInferenceClient:
    """
    Client per HuggingFace Serverless Inference API.
    Stessa rete di HF Spaces — nessuna dipendenza esterna.
    Usa HF_TOKEN env var (disponibile automaticamente su HF Spaces).
    """

    def __init__(self, token: str = None, model: str = None):
        self.token = token or HF_TOKEN
        self.model = model or HF_MODEL
        self.available = False

        if HF_HUB_AVAILABLE and self.token:
            try:
                self.client = _HFInferenceClient(token=self.token)
                self.available = True
            except Exception as e:
                logger.error(f"HF InferenceClient init error: {e}")
        else:
            if not HF_HUB_AVAILABLE:
                logger.warning("huggingface_hub non installato.")
            elif not self.token:
                logger.warning("HF_TOKEN mancante — HF provider non disponibile.")

    def generate_content(self, prompt: str, temperature: float = 0.7,
                         max_tokens: int = 8192) -> str:
        """
        Genera contenuto via HF Inference.
        Prova ogni modello con provider multipli (rutati attraverso HF → nessun blocco di rete).
        Ordine provider: together → fireworks-ai → hf-inference (fallback piccoli modelli).
        """
        if not self.available:
            raise RuntimeError("HF InferenceClient non disponibile")

        chain = [self.model] + [m for m in HF_MODEL_CHAIN if m != self.model]
        providers = ["together", "fireworks-ai", "hf-inference"]
        last_error = None

        for model in chain:
            for provider in providers:
                try:
                    tmp_client = _HFInferenceClient(provider=provider, token=self.token)
                    response = tmp_client.chat_completion(
                        model=model,
                        messages=[{"role": "user", "content": prompt}],
                        max_tokens=max_tokens,
                        temperature=temperature,
                    )
                    content = response.choices[0].message.content or ""
                    if content.strip():
                        logger.info(f"HF [{provider}/{model}] succeeded")
                        return content
                    logger.warning(f"HF [{provider}/{model}] empty response, trying next")
                except Exception as e:
                    logger.warning(f"HF [{provider}/{model}] failed: {str(e)[:100]}")
                    last_error = e

        raise RuntimeError(f"All HF models/providers exhausted. Last error: {last_error}")


def get_active_provider() -> str:
    """Restituisce il provider AI attivo corrente."""
    return os.environ.get("AI_PROVIDER", AI_PROVIDER)


# =============================================================================
# ASYNC GEMINI CLIENT (OPT-002)
# =============================================================================

class AsyncGeminiClient:
    """
    Wrapper per esecuzione parallela reale di chiamate Gemini usando ThreadPoolExecutor.

    Features:
    - True parallel execution (max 6 workers)
    - Rate limiting (60 requests/min)
    - Retry logic with exponential backoff
    - Thread-safe operation
    """

    def __init__(self, max_workers: int = 6, rate_limit: int = 60):
        """
        Args:
            max_workers: Number of concurrent threads (default 6)
            rate_limit: Max requests per minute (default 60)
        """
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.rate_limit = rate_limit
        self.request_times = []
        self.semaphore = Semaphore(max_workers)
        logger.info(f"AsyncGeminiClient initialized with {max_workers} workers, {rate_limit} req/min")

    def _check_rate_limit(self) -> None:
        """Check and enforce rate limiting"""
        now = time.time()
        # Remove requests older than 60 seconds
        self.request_times = [t for t in self.request_times if now - t < 60]

        # If at limit, wait
        if len(self.request_times) >= self.rate_limit:
            sleep_time = 60 - (now - self.request_times[0])
            if sleep_time > 0:
                logger.warning(f"Rate limit reached, sleeping {sleep_time:.1f}s")
                time.sleep(sleep_time)
                # Clean up again after sleep
                now = time.time()
                self.request_times = [t for t in self.request_times if now - t < 60]

        self.request_times.append(now)

    def _execute_with_retry(
        self,
        func: Callable,
        max_retries: int = 3,
        backoff_factor: float = 2.0,
        max_sleep: float = 10.0
    ) -> Any:
        """
        Execute function with exponential backoff retry logic.

        Args:
            func: Function to execute
            max_retries: Maximum number of retries
            backoff_factor: Multiplier for exponential backoff
            max_sleep: Maximum sleep time between retries (default 10s)

        Returns:
            Function result

        Raises:
            GeminiAPIError if all retries fail
        """
        last_exception = None
        for attempt in range(max_retries):
            try:
                self._check_rate_limit()
                result = func()
                return result
            except Exception as e:
                last_exception = e
                if attempt == max_retries - 1:
                    logger.error(f"All {max_retries} retries failed: {e}")
                    raise GeminiAPIError(
                        message=f"Gemini API failed after {max_retries} attempts: {str(e)}",
                        details={"attempts": max_retries, "last_error": str(e)}
                    ) from e

                sleep_time = min(backoff_factor ** attempt, max_sleep)
                logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {sleep_time:.1f}s...")
                time.sleep(sleep_time)

    async def execute_parallel(
        self,
        tasks: List[Callable],
        task_names: List[str] = None,
        timeout: int = 300
    ) -> List[Any]:
        """
        Execute multiple tasks in parallel using ThreadPoolExecutor.

        Args:
            tasks: List of callables (sync functions)
            task_names: Optional names for logging
            timeout: Maximum seconds to wait for all tasks (default 300s = 5min)

        Returns:
            List of results in same order as tasks
        """
        if task_names is None:
            task_names = [f"Task-{i}" for i in range(len(tasks))]

        loop = asyncio.get_event_loop()
        futures = []

        for task, name in zip(tasks, task_names):
            logger.info(f"🚀 Scheduling {name} for parallel execution")
            future = loop.run_in_executor(
                self.executor,
                self._execute_with_retry,
                task
            )
            futures.append(future)

        logger.info(f"⏳ Waiting for {len(futures)} tasks to complete (timeout={timeout}s)...")

        # Wait for all to complete WITH TIMEOUT
        try:
            results = await asyncio.wait_for(
                asyncio.gather(*futures, return_exceptions=True),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            logger.error(f"⏱️ TIMEOUT after {timeout}s - cancelling all pending tasks")
            for future in futures:
                future.cancel()
            # Return timeout exceptions for all tasks
            results = [TimeoutError(f"Task exceeded {timeout}s timeout") for _ in tasks]

        # Log results
        for name, result in zip(task_names, results):
            if isinstance(result, Exception):
                logger.error(f"{name} failed with exception: {result}")
            else:
                logger.info(f"{name} completed successfully")

        return results

    def shutdown(self):
        """Cleanup executor"""
        self.executor.shutdown(wait=True)
        logger.info("AsyncGeminiClient shutdown complete")


# =============================================================================
# AGENT ROLES - Allineati alla Matrice STW
# =============================================================================

class AgentRole(Enum):
    """Ruoli degli agenti allineati alle 4 categorie STW + coordinator + consistency"""
    COORDINATOR = "coordinator"           # Executive Summary
    STW_SPORTIVI = "stw_sportivi"         # ⚽ Obiettivi Sportivi (8 MACRO)
    STW_STRUTTURALI = "stw_strutturali"   # 🏗️ Obiettivi Strutturali (2 MACRO)
    STW_MARKETING = "stw_marketing"       # 📢 Obiettivi Marketing (4 MACRO)
    STW_SOCIALI = "stw_sociali"           # 🤝 Obiettivi Sociali (7 MACRO)
    CONSISTENCY = "consistency"           # Allineamento inter-sezione
    FINANCIAL = "financial"               # Piano Economico-Finanziario


# =============================================================================
# AGENT CONFIG
# =============================================================================

@dataclass
class AgentSpec:
    """Specifica di un agente"""
    role: AgentRole
    name: str
    expertise: List[str]
    system_prompt: str
    output_sections: List[str] = field(default_factory=list)
    priority: int = 1  # Per ordinamento esecuzione


# =============================================================================
# GLOBAL VOICE DIRECTIVE - Impersonal Club Voice
# =============================================================================

GLOBAL_VOICE_DIRECTIVE = """
---
## DIRETTIVA VOCE ISTITUZIONALE (OBBLIGATORIA)

Scrivi SEMPRE a nome del CLUB come istituzione, MAI a nome di singoli stakeholder o soci.

**REGOLE FONDAMENTALI:**
1. **NESSUN NOME PROPRIO**: Non menzionare MAI nomi di soci, presidente, DG o altri individui.
2. **VOCE ISTITUZIONALE**: Usa sempre "Il Club", "La Società", "La Direzione", "L'Organo Amministrativo".
3. **DECISIONI COLLEGIALI**: Presenta ogni decisione come frutto di analisi strategica, non di opinioni personali.
   - SBAGLIATO: "Il presidente Carnevali vuole la Serie D"
   - CORRETTO: "La direzione strategica prevede un percorso verso la Serie D"
4. **CONFLITTI → SINTESI**: Se esistono visioni divergenti tra stakeholder, sintetizzale in UNA direzione strategica chiara.
   - SBAGLIATO: "Alcuni soci preferiscono X, altri Y"
   - CORRETTO: "L'analisi comparata ha portato alla definizione di un approccio bilanciato che..."
5. **TONO CONSULENZIALE**: Scrivi come se fossi McKinsey/BCG che presenta al board, non come verbale di assemblea.

**FORMULE DA USARE:**
- "Il Club ha stabilito..."
- "La direzione strategica prevede..."
- "L'analisi condotta evidenzia..."
- "Si raccomanda l'adozione di..."
- "La Società intende perseguire..."
- "Il piano triennale delinea..."

**DIRETTIVA TRASPARENZA DATI (OBBLIGATORIA):**
Sii trasparente sulla provenienza dei dati:
1. Se un dato proviene dal Board, scrivi "(fonte: questionario)".
2. Se un dato è frutto di stima basata su benchmark, scrivi "(fonte: stima AI)".
3. Se un dato è tratto da ricerca web, scrivi "(fonte: ricerca web)".
4. Se non hai un dato, scrivi "(dato da acquisire)".
---
"""

GLOBAL_FORMAT_DIRECTIVE = """
---
## FORMATO OUTPUT (OBBLIGATORIO)

Per ogni MACRO obiettivo usa ESATTAMENTE questo blocco:

```
### MACRO N: Titolo

**Obiettivo:** Una frase. Cosa il Club vuole ottenere.

**Azioni chiave:**
- Azione 1 concreta e misurabile (fonte: ...)
- Azione 2
- Azione 3

**KPI:** Metrica → Target numerico entro Anno X
**Timeline:** Anno 1 | Anno 2 | Anno 3
**Budget:** €range (fonte: benchmark club simili categoria)
```

**VINCOLI ASSOLUTI:**
- Max 3-4 azioni per MACRO (non di più)
- KPI: sempre una metrica numerica con target (es. "+15% iscritti", "Top 3 classifica")
- Budget: sempre un range, mai un numero preciso
- Niente paragrafi lunghi — solo blocchi strutturati
- Nessun requisito minimo di caratteri: qualità > quantità
---
"""

# =============================================================================
# AGENT SPECIFICATIONS - 6 AGENTI STW-NATIVE
# Struttura allineata alla Matrice STW (Sport To Win)
# =============================================================================

AGENT_SPECS: Dict[AgentRole, AgentSpec] = {

    # =========================================================================
    # COORDINATOR - Executive Summary
    # =========================================================================
    AgentRole.COORDINATOR: AgentSpec(
        role=AgentRole.COORDINATOR,
        name="Strategic Coordinator",
        expertise=["sintesi strategica", "executive summary", "visione d'insieme", "matrice STW"],
        priority=0,
        output_sections=["executive_summary"],
        system_prompt=GLOBAL_VOICE_DIRECTIVE + GLOBAL_FORMAT_DIRECTIVE + """
Sei il COORDINATORE STRATEGICO. Crei l'Executive Summary sintetizzando le 4 aree STW.

**STRUTTURA OBBLIGATORIA:**

## EXECUTIVE SUMMARY

### VISIONE STRATEGICA TRIENNALE
Definisci la visione del Club a 3 anni come decisione unitaria della Società.

### SINTESI MATRICE STW
Riassumi in un paragrafo per ciascuna delle 4 categorie STW:
- ⚽ **SPORTIVI**: Sintesi obiettivi tecnico-sportivi
- 🏗️ **STRUTTURALI**: Sintesi infrastrutture e HR
- 📢 **MARKETING**: Sintesi comunicazione e commerciale
- 🤝 **SOCIALI**: Sintesi impatto sociale e sostenibilità

### TOP 5 PRIORITÀ MACRO
Elenca i 5 obiettivi MACRO prioritari con codice STW (es. "SPORTIVI MACRO 4: Miglioramento Competitivo"). 
Per ogni priorità, aggiungi una brevissima motivazione (max 15 parole) che spieghi PERCHÈ è stata scelta o l'ordine di importanza.
Formato: "CODICE: Titolo - Motivazione"

### QUICK WINS (Azioni Micro Immediate)
Identifica 5 azioni MICRO ad alto impatto da avviare entro 6 mesi, con codice STW.

### ROADMAP TRIENNALE
Timeline sintetica: Anno 1 (Setup) → Anno 2 (Sviluppo) → Anno 3 (Consolidamento)

**STILE:** Tono McKinsey/BCG. Voce istituzionale. Zero nomi propri.
"""
    ),

    # =========================================================================
    # STW SPORTIVI - 8 Obiettivi MACRO
    # =========================================================================
    AgentRole.STW_SPORTIVI: AgentSpec(
        role=AgentRole.STW_SPORTIVI,
        name="STW Sportivi Analyst",
        expertise=["settore tecnico", "prima squadra", "settore giovanile", "scouting", "club affiliati"],
        priority=1,
        output_sections=["stw_sportivi"],
        system_prompt=GLOBAL_VOICE_DIRECTIVE + GLOBAL_FORMAT_DIRECTIVE + """
Sei l'ANALISTA AREA SPORTIVA STW. Redigi la sezione OBIETTIVI SPORTIVI secondo la Matrice STW.

**STRUTTURA OBBLIGATORIA - USA ESATTAMENTE QUESTI CODICI:**

## ⚽ OBIETTIVI SPORTIVI

### MACRO 1: CREAZIONE E SVILUPPO IDENTITÀ TECNICA
- **1.1 Organigramma tecnico**: Figure attuali e gap da colmare (licenze, ruoli)
- **1.2 Piano formazione staff**: Programma aggiornamento continuo

### MACRO 2: INCREMENTO PARTECIPAZIONE ALL'AZIENDA SPORTIVA
- **2.1 Attività promozionali territorio**: Open day, sport in piazza
- **2.2 Partnership scuole**: Programmi educativi congiunti
- **2.3 Centri estivi**: Campus per giovani potenziali tesserati
- **2.4 Eventi settori minori**: Promozione discipline meno partecipate
- **2.5 Tornei non tesserati**: Apertura al territorio

### MACRO 3: POTENZIAMENTO STRUTTURA DIRIGENZIALE
- **3.1 Standard selezione dirigenti**: Criteri formalizzati
- **3.2 Formazione dirigenti**: Programmi aggiornamento manageriale
- **3.3 Completamento organigramma**: Ruoli e responsabilità

### MACRO 4: MIGLIORAMENTO COMPETITIVO
- **4.1 Strategia tecnica SG-Prima Squadra**: Modello di gioco unificato
- **4.2 Allenatori licenza massima**: Target qualifiche UEFA
- **4.3 Rete scouting**: Ampliamento osservatori e strumenti
- **4.4 Tornei qualificanti**: Partecipazione competizioni di livello

### MACRO 5: PROPOSTA DEL CLUB PER I TESSERATI
- **5.1 Programma tecnico/fisico**: Sviluppo e monitoraggio performance
- **5.2 Struttura medica**: Staff sanitario qualificato
- **5.3 Fisioterapia e macchinari**: Attrezzature recupero/prevenzione
- **5.4 Struttura logistica**: Trasporti, trasferte, organizzazione

### MACRO 6: RAFFORZAMENTO SETTORE SCOUTING
- **6.1 Responsabile scouting**: Figura dedicata
- **6.2 Budget e strumenti**: Risorse per osservazione
- **6.3 Metriche valutazione**: KPI efficacia scouting
- **6.4 Foresteria**: Alloggio atleti fuori sede

### MACRO 7: RAFFORZAMENTO CLUB AFFILIATI
- **7.1 Responsabile sviluppo affiliati**: Coordinamento rete
- **7.2 Progetto tecnico coerente**: Metodologia condivisa
- **7.3 Incontri tecnici/organizzativi**: Formazione e networking
- **7.4 Torneo affiliati**: Evento annuale
- **7.5 Ricavi dedicati**: Sostenibilità progetto
- **7.6 Standard allenatori**: Qualità uniforme nella rete

### MACRO 8: SVILUPPO AREA TECNICO-SPORTIVA SPECIFICA
- **8.1 Competizioni competitive**: Tornei di livello
- **8.2 Formazione allenatori/arbitri**: Staff adeguato
- **8.3 Eventi dedicati**: Competizioni locali
- **8.4 Collaboratori di livello**: Professionisti per sviluppo
- **8.5 Legame istituzioni**: Partnership strategiche
- **8.6 Entrate commerciali dedicate**: Sostenibilità economica

**REGOLE:**
- Ogni MICRO deve avere: situazione attuale, gap, azione proposta, KPI
- Dati mancanti: `(dato da acquisire)`
- Voce istituzionale: "Il Club prevede...", "La Società implementerà..."
- IMPORTANTE: Completa tutte le MACRO. Usa il blocco formato definito per ognuna.
"""
    ),

    # =========================================================================
    # STW STRUTTURALI - 2 Obiettivi MACRO
    # =========================================================================
    AgentRole.STW_STRUTTURALI: AgentSpec(
        role=AgentRole.STW_STRUTTURALI,
        name="STW Strutturali Analyst",
        expertise=["infrastrutture", "impianti sportivi", "risorse umane", "HR", "welfare"],
        priority=2,
        output_sections=["stw_strutturali"],
        system_prompt=GLOBAL_VOICE_DIRECTIVE + GLOBAL_FORMAT_DIRECTIVE + """
Sei l'ANALISTA AREA STRUTTURALE STW. Redigi la sezione OBIETTIVI STRUTTURALI secondo la Matrice STW.

**STRUTTURA OBBLIGATORIA - USA ESATTAMENTE QUESTI CODICI:**

## 🏗️ OBIETTIVI STRUTTURALI E INFRASTRUTTURALI

### MACRO 1: COSTRUZIONE E RINNOVAMENTO STRUTTURE
- **1.1 Rinnovamento campi attuali**: Manutenzione e upgrade impianti esistenti
  - Stato attuale: [descrizione]
  - Gap identificati: [elenco]
  - Piano interventi: [azioni con timeline]
  - Budget stimato: [range con fonte]

- **1.2 Costruzione nuovi impianti sportivi**: Espansione capacità
  - Necessità identificate: [elenco]
  - Priorità: [alta/media/bassa]
  - Investimento stimato: [range]
  - Timeline: [fasi]

- **1.3 Progetto retail store**: Punto vendita merchandising ufficiale
  - Location proposta: [opzioni]
  - Business case: [sintesi]
  - ROI atteso: [stima]

- **1.4 Sede operativa**: Uffici e spazi amministrativi
  - Situazione attuale: [descrizione]
  - Esigenze: [elenco]
  - Opzioni: [soluzioni proposte]

### MACRO 2: RISORSE UMANE
- **2.1 Policy aziendali**: Standardizzazione processi HR
  - Policy esistenti: [elenco]
  - Gap: [cosa manca]
  - Piano implementazione: [azioni]

- **2.2 Monitoraggio lavoro**: Performance management e feedback
  - Strumenti attuali: [elenco]
  - Miglioramenti proposti: [azioni]
  - KPI HR: [metriche]

- **2.3 Programmi benessere**: Welfare aziendale
  - Iniziative proposte: [elenco]
  - Budget: [stima]
  - Beneficiari: [target]

**REGOLE ASSOLUTE:**
- Questa sezione ha ESATTAMENTE 2 MACRO (MACRO 1 e MACRO 2). NON aggiungere MACRO 3, MACRO 4 o altri obiettivi macro.
- Finanziario e marketing NON appartengono a questa sezione.
- Costi SEMPRE come range con fonte (es. "€50.000-80.000 - benchmark club simili")
- Dati mancanti: `(dato da acquisire)`
- Voce istituzionale
"""
    ),

    # =========================================================================
    # STW MARKETING - 4 Obiettivi MACRO
    # =========================================================================
    AgentRole.STW_MARKETING: AgentSpec(
        role=AgentRole.STW_MARKETING,
        name="STW Marketing Analyst",
        expertise=["comunicazione", "marketing sportivo", "brand identity", "commerciale", "CRM"],
        priority=3,
        output_sections=["stw_marketing"],
        system_prompt=GLOBAL_VOICE_DIRECTIVE + GLOBAL_FORMAT_DIRECTIVE + """
Sei l'ANALISTA AREA MARKETING STW. Redigi la sezione OBIETTIVI MARKETING secondo la Matrice STW.

**STRUTTURA OBBLIGATORIA - USA ESATTAMENTE QUESTI CODICI:**

## 📢 OBIETTIVI MARKETING E COMMERCIALI

### MACRO 1: SVILUPPO AREA COMUNICAZIONE
- **1.1 Ufficio stampa strutturato**: Responsabile con adeguati titoli
  - Situazione attuale: [descrizione]
  - Profilo richiesto: [competenze]
  - Piano assunzione/formazione: [azioni]

- **1.2 Strumentazione adeguata**: Tool per social media e media monitoring
  - Strumenti attuali: [elenco]
  - Gap: [cosa manca]
  - Investimento: [budget]

- **1.3 Strumenti misurazione**: KPI comunicazione
  - Metriche proposte: reach, engagement, sentiment
  - Tool di analytics: [proposta]
  - Reporting: [frequenza e format]

### MACRO 2: SVILUPPO AREA MARKETING
- **2.1 Responsabile qualificato**: Profilo marketing sportivo
  - Competenze richieste: [elenco]
  - Opzioni: [interno/esterno]

- **2.2 Piano marketing annuale**: Documento formale
  - Componenti chiave: [elenco]
  - Processo approvazione: [iter]
  - Budget: [allocazione]

- **2.3 Verifica relazione club-utenti**: Survey e feedback
  - Metodologia: [descrizione]
  - Frequenza: [timing]
  - Azioni correttive: [processo]

- **2.4 Implementazione CRM**: Gestione relazioni e privacy
  - Piattaforma proposta: [opzioni]
  - GDPR compliance: [requisiti]
  - Timeline implementazione: [fasi]

### MACRO 3: SVILUPPO BRAND IDENTITY
- **3.1 Valorizzazione patrimonio storico**: Museo, archivio, eventi legacy
  - Asset esistenti: [elenco]
  - Iniziative proposte: [azioni]

- **3.2 Potenziamento dotazioni sportive**: Merchandising
  - Catalogo attuale: [analisi]
  - Espansione proposta: [nuovi prodotti]
  - Canali vendita: [online/retail]

- **3.3 Marketing automation**: Profilazione utenti e tifosi
  - Segmenti target: [elenco]
  - Workflow automatizzati: [esempi]
  - ROI atteso: [stima]

### MACRO 4: SVILUPPO AREA COMMERCIALE
- **4.1 Piano commerciale formale**: In accordo col marketing
  - Obiettivi ricavi: [target per fonte]
  - Strategia sponsor: [approccio]
  - Ticketing: [ottimizzazione]

- **4.2 Strutturazione area commerciale**: Team dedicato
  - Organigramma proposto: [ruoli]
  - Competenze: [profili]
  - Incentivi: [struttura]

- **4.3 Revisione periodica obiettivi**: Monitoraggio
  - Frequenza review: [timing]
  - Dashboard KPI: [metriche]
  - Processo escalation: [iter]

**REGOLE:**
- Usa benchmark di mercato per ogni proposta
- Quantifica sempre (follower, engagement rate, ricavi)
- Voce istituzionale
"""
    ),

    # =========================================================================
    # STW SOCIALI - 7 Obiettivi MACRO
    # =========================================================================
    AgentRole.STW_SOCIALI: AgentSpec(
        role=AgentRole.STW_SOCIALI,
        name="STW Sociali Analyst",
        expertise=["CSR", "inclusione", "sostenibilità", "impatto sociale", "ambiente"],
        priority=4,
        output_sections=["stw_sociali"],
        system_prompt=GLOBAL_VOICE_DIRECTIVE + GLOBAL_FORMAT_DIRECTIVE + """
Sei l'ANALISTA AREA SOCIALE STW. Redigi la sezione OBIETTIVI SOCIALI secondo la Matrice STW.

**STRUTTURA OBBLIGATORIA - USA ESATTAMENTE QUESTI CODICI:**

## 🤝 OBIETTIVI SOCIALI E SOSTENIBILITÀ

### MACRO 1: SVILUPPO PROGETTI ANTI-RAZZISMO
- **1.1 Campagne istituzionali**: Adesione iniziative nazionali/internazionali
- **1.2 Attività preventive**: Formazione e sensibilizzazione interna
- **1.3 Partnership associazioni**: Collaborazioni con organizzazioni anti-discriminazione
- **1.4 Procedure segnalazione**: Canali sicuri e confidenziali
- **1.5 Eventi dedicati**: Giornate tematiche e iniziative

### MACRO 2: PROTEZIONE BAMBINI/E E GIOVANI
- **2.1 Certificazioni staff**: Allenatori ed educatori verificati
- **2.2 Policy safeguarding**: Procedure di protezione minori
- **2.3 Formazione giovani**: Educazione e consapevolezza

### MACRO 3: SVILUPPO INCLUSIONE E UGUAGLIANZA
- **3.1 Accessibilità strutture**: Adeguamento per tutti
- **3.2 Programmi inclusione**: Attività dedicate
- **3.3 Policy uguaglianza**: Documento formale

### MACRO 4: ADEGUATEZZA A QUALSIASI ABILITÀ
- **4.1 Sport per tutti**: Programmi paralimpici e adattati
- **4.2 Formazione specifica**: Staff competente
- **4.3 Partner esterni**: Collaborazioni con associazioni

### MACRO 5: SALUTE E BENESSERE
- **5.1 Progetti terza età**: Programmi over 65 e riabilitazione
- **5.2 Campagne salute**: Prevenzione e stili di vita sani
- **5.3 Programmi nutrizionali**: Educazione alimentare

### MACRO 6: SOLIDARIETÀ E DIRITTI
- **6.1 Collaborazione istituzioni**: Supporto campagne statali
- **6.2 Policy diritti umani**: Documento formale
- **6.3 Opportunità rifugiati**: Programmi integrazione
- **6.4 Privacy garantita**: Protezione dati

### MACRO 7: ADEGUAMENTO ECONOMIA CIRCOLARE
- **7.1 Campagne ambientali**: Collaborazione istituzioni
- **7.2 Riduzione impatto**: Acqua, plastica, gas, riciclo
- **7.3 Strutture eco-sostenibili**: Adeguamento impianti
- **7.4 Progetti green**: Iniziative per giovani e partner

**REGOLE:**
- QUANTIFICA SEMPRE l'impatto (es. "500 beneficiari", "-20% plastica", "3 eventi/anno")
- Per ogni MICRO: situazione attuale → azione proposta → impatto atteso
- Voce istituzionale: "Il Club si impegna a...", "La Società promuove..."
"""
    ),

    # =========================================================================
    # CONSISTENCY - Allineamento inter-sezione (Gemini recommendation)
    # Gira DOPO le 4 aree STW, PRIMA del Financial
    # =========================================================================
    AgentRole.CONSISTENCY: AgentSpec(
        role=AgentRole.CONSISTENCY,
        name="Consistency Reviewer",
        expertise=["coerenza strategica", "allineamento obiettivi", "cross-reference"],
        priority=4,
        output_sections=["consistency_review"],
        system_prompt=GLOBAL_VOICE_DIRECTIVE + GLOBAL_FORMAT_DIRECTIVE + """
Sei il REVISORE DI COERENZA. Analizzi le 4 sezioni STW gia' generate e produci:

**STRUTTURA OBBLIGATORIA:**

## ANALISI DI COERENZA INTER-SEZIONE

### 1. ALLINEAMENTO OBIETTIVI
Per ogni obiettivo sportivo, verifica che:
- Esista un supporto strutturale corrispondente
- Esista una strategia marketing collegata
- Esista un impatto sociale previsto

### 2. CONFLITTI RILEVATI
Elenca eventuali contraddizioni tra sezioni:
- Obiettivi sportivi non supportati da risorse strutturali
- Strategie marketing non allineate alla mission
- Impegni sociali senza copertura finanziaria prevista

### 3. RACCOMANDAZIONI DI ALLINEAMENTO
Per ogni conflitto, suggerisci come riconciliare le sezioni.

### 4. FLAG PER FINANCIAL STRATEGIST
Elenca gli obiettivi che richiedono budget specifico, organizzati per priorita':
- **Priorita' 1 (Anno 1)**: [obiettivi urgenti]
- **Priorita' 2 (Anno 2)**: [obiettivi di consolidamento]
- **Priorita' 3 (Anno 3)**: [obiettivi di crescita]

**REGOLE:**
- Riferisciti SEMPRE ai codici MACRO delle sezioni STW
- Non riscrivere le sezioni, solo analizzare coerenza
- Sii specifico: cita obiettivi per nome/codice
- Voce istituzionale
"""
    ),

    # =========================================================================
    # FINANCIAL - Piano Economico-Finanziario
    # =========================================================================
    AgentRole.FINANCIAL: AgentSpec(
        role=AgentRole.FINANCIAL,
        name="Financial Strategist",
        expertise=["bilancio", "budget", "investimenti", "sostenibilità economica", "proiezioni"],
        priority=6,
        output_sections=["financial_plan"],
        system_prompt=GLOBAL_VOICE_DIRECTIVE + GLOBAL_FORMAT_DIRECTIVE + """
Sei lo STRATEGA FINANZIARIO. Redigi il PIANO ECONOMICO-FINANZIARIO a supporto della Matrice STW.

**STRUTTURA OBBLIGATORIA:**

## 💰 PIANO ECONOMICO-FINANZIARIO

### 1. ANALISI SITUAZIONE ATTUALE
- **Ricavi**: [solo dati verificati o "dato riservato"]
- **Costi operativi**: [struttura costi]
- **Margine operativo**: [se disponibile]
- **Posizione finanziaria**: [sintesi]

### 2. BUDGET INVESTIMENTI STW
Stima investimenti per categoria STW:

| Categoria | Anno 1 | Anno 2 | Anno 3 | Totale |
|-----------|--------|--------|--------|--------|
| ⚽ Sportivi | €... | €... | €... | €... |
| 🏗️ Strutturali | €... | €... | €... | €... |
| 📢 Marketing | €... | €... | €... | €... |
| 🤝 Sociali | €... | €... | €... | €... |
| **TOTALE** | €... | €... | €... | €... |

### 3. PROIEZIONE RICAVI TRIENNALE
- **Anno 1**: [stima con assunzioni]
- **Anno 2**: [stima con assunzioni]
- **Anno 3**: [stima con assunzioni]

Fonti ricavi:
- Sponsor e partnership
- Ticketing e abbonamenti
- Merchandising
- Settore giovanile
- Eventi e hospitality
- Contributi federali

### 4. SOSTENIBILITÀ ECONOMICA
- **Break-even**: [analisi]
- **Cash flow**: [proiezione]
- **Rischi finanziari**: [identificazione e mitigazione]
- **Fonti finanziamento**: [equity, debito, contributi]

### 5. KPI FINANZIARI
- Rapporto costi/ricavi
- ROI per area STW
- Costo per tesserato
- Revenue per tifoso

**REGOLA CRITICA**:
- MAI inventare numeri specifici
- Dati non noti = `(dato riservato)` o range benchmark
- Proiezioni SEMPRE con assunzioni esplicite
- Voce istituzionale
"""
    ),
}


import hashlib
from pathlib import Path

# =============================================================================
# AI CACHE SYSTEM
# =============================================================================

class AICache:
    """
    Cache persistente per le risposte dell'AI.
    Evita chiamate ridondanti a Gemini per gli stessi prompt.
    """
    def __init__(self):
        self.cache_dir = Path("knowledge_base/ai_cache")
        self.cache_dir.mkdir(exist_ok=True, parents=True)

    def _get_hash(self, prompt: str) -> str:
        return hashlib.md5(prompt.encode("utf-8")).hexdigest()

    def get(self, prompt: str) -> Optional[str]:
        cache_path = self.cache_dir / f"{self._get_hash(prompt)}.txt"
        if cache_path.exists():
            try:
                with open(cache_path, "r", encoding="utf-8") as f:
                    return f.read()
            except Exception as e:
                logger.warning(f"Cache read error: {e}")
        return None

    def set(self, prompt: str, response: str):
        cache_path = self.cache_dir / f"{self._get_hash(prompt)}.txt"
        try:
            with open(cache_path, "w", encoding="utf-8") as f:
                f.write(response)
        except Exception as e:
            logger.warning(f"Cache write error: {e}")


# =============================================================================
# STRATEGIC AGENT
# =============================================================================

class StrategicAgent:
    """
    Singolo agente specializzato.
    Usa il File Search Tool di Gemini per basare le risposte sulla knowledge base.
    Supporta conflict-aware generation basata su alignment score stakeholder.
    """

    def __init__(self, spec: AgentSpec, file_search_store_name: str | None = None):
        self.spec = spec
        self.sourcer = SourcedContentGenerator()
        self.file_search_store_name = file_search_store_name
        self.model = None
        self.cache = AICache() # Inizializza cache
        self._provider = get_active_provider()  # "gemini", "openrouter", "huggingface"
        self._openrouter_client = None
        self._hf_client = None
        self._generation_provider = None  # ai_providers.GenerationProvider (Ollama o Gemini)
        logger.info(f"Agent {spec.name}: provider='{self._provider}'")

        # --- Ollama path: OLLAMA_BASE_URL presente → usa adapter layer ---
        _ollama_url = os.environ.get("OLLAMA_BASE_URL", "").strip()
        if _ollama_url:
            try:
                from ai_providers.ollama_provider import OllamaGenerationProvider
                self._generation_provider = OllamaGenerationProvider(base_url=_ollama_url)
                self.available = self._generation_provider.available
                if self.available:
                    _model = os.environ.get("OLLAMA_MODEL", "gemma4:26b")
                    logger.info(f"Agent {spec.name}: Ollama inizializzato (url={_ollama_url}, model={_model})")
                else:
                    logger.warning(f"Agent {spec.name}: OllamaGenerationProvider non disponibile")
            except Exception as e:
                logger.error(f"Agent {spec.name}: Errore init Ollama: {e}")
                self._generation_provider = None
                self.available = False

        elif self._provider == "gemini_direct":
            # --- Gemini Direct (skip HF: all free-tier models broken) ---
            _gkey = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY") or GEMINI_API_KEY
            if GENAI_AVAILABLE and _gkey:
                self.available = True
                logger.info(f"Agent {spec.name}: Gemini Direct v2 inizializzato")
            else:
                self.available = False
                logger.warning(f"Agent {spec.name}: Gemini Direct — chiave mancante")

        elif self._provider == "huggingface":
            # --- HuggingFace Serverless Inference API ---
            hf_token = HF_TOKEN or os.environ.get("HF_TOKEN", "")
            hf_model = os.environ.get("HF_MODEL", HF_MODEL)
            if hf_token:
                try:
                    self._hf_client = HFInferenceClient(token=hf_token, model=hf_model)
                    self.available = self._hf_client.available
                    if self.available:
                        logger.info(f"Agent {spec.name}: HF Inference inizializzato (model={hf_model})")
                    else:
                        logger.warning(f"Agent {spec.name}: HF client non disponibile")
                except Exception as e:
                    logger.error(f"Agent {spec.name}: Errore init HF: {e}")
                    self.available = False
            else:
                self.available = False
                logger.warning(f"Agent {spec.name}: HF_TOKEN mancante.")

        elif self._provider == "openrouter":
            # --- OpenRouter provider ---
            or_key = OPENROUTER_API_KEY or os.environ.get("OPENROUTER_API_KEY", "")
            or_model = os.environ.get("OPENROUTER_MODEL", OPENROUTER_DEFAULT_MODEL)
            if or_key:
                try:
                    self._openrouter_client = OpenRouterClient(api_key=or_key, model=or_model)
                    self.available = self._openrouter_client.available
                    if self.available:
                        logger.info(f"Agent {spec.name}: OpenRouter inizializzato (model={or_model})")
                    else:
                        logger.warning(f"Agent {spec.name}: OpenRouter client non disponibile")
                except Exception as e:
                    logger.error(f"Agent {spec.name}: Errore init OpenRouter: {e}")
                    self.available = False
            else:
                self.available = False
                logger.warning(f"Agent {spec.name}: OpenRouter API key mancante.")
        else:
            # --- Gemini provider (default) ---
            # Priorità: env vars dinamiche prima del valore importato (statico)
            api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY") or GEMINI_API_KEY
            if GENAI_AVAILABLE and api_key:
                try:
                    from ai_providers.gemini_provider import detect_best_gemini_model
                    _gemini_model_name = detect_best_gemini_model(api_key)
                    genai.configure(api_key=api_key)
                    self.model = genai.GenerativeModel(_gemini_model_name)
                    self.available = True
                    logger.info(f"Agent {spec.name}: Gemini model={_gemini_model_name}")
                except Exception as e:
                    logger.error(f"Errore durante l'inizializzazione del client Gemini: {e}")
                    self.model = None
                    self.available = False
            else:
                self.model = None
                self.available = False
                logger.warning(f"Agent {spec.name}: Gemini non disponibile o API key mancante.")

    def _get_tone_directive(self, alignment_score: float, conflicts: list = None) -> str:
        """
        Genera direttive di tono basate sull'alignment score stakeholder.

        Args:
            alignment_score: Score 0-100 di coesione tra stakeholder
            conflicts: Lista di conflitti rilevati

        Returns:
            Direttiva testuale per modulare il tono
        """
        if alignment_score >= 90:
            return """
**TONO DIRETTIVO - ALTO ALLINEAMENTO STAKEHOLDER (>90%)**
Gli stakeholder sono altamente allineati. Usa un tono deciso e propositivo:
- Afferma con sicurezza le raccomandazioni
- Usa linguaggio assertivo: "si procederà", "è necessario", "la strategia prevede"
- Evita condizionali e cautele eccessive
- Focus sull'execution immediata
"""
        elif alignment_score >= 70:
            return """
**TONO BILANCIATO - ALLINEAMENTO MODERATO (70-90%)**
C'è consenso sostanziale con alcune divergenze minori. Tono equilibrato:
- Presenta raccomandazioni con sicurezza ma riconosci alternative
- Usa: "si raccomanda", "l'analisi suggerisce"
- Evidenzia le aree di consenso come prioritarie
"""
        elif alignment_score >= 50:
            return f"""
**TONO PRUDENTE - ALLINEAMENTO BASSO (50-70%)**
Esistono divergenze significative tra gli stakeholder. Procedi con cautela:
- Usa linguaggio condizionale: "si suggerisce di valutare", "potrebbe essere opportuno"
- Evidenzia esplicitamente le aree che richiedono allineamento interno
- Proponi opzioni alternative dove c'è disaccordo
- Includi raccomandazioni per workshop di allineamento

{self._format_conflict_warnings(conflicts) if conflicts else ""}
"""
        else:
            return f"""
**TONO MOLTO PRUDENTE - BASSO ALLINEAMENTO (<50%)**
⚠️ ATTENZIONE: Gli stakeholder presentano visioni fortemente divergenti.
Prima di procedere con azioni strategiche, è CRITICO:
1. Organizzare sessioni di allineamento tra ownership e management
2. Definire priorità condivise attraverso processo strutturato
3. Risolvere i conflitti emersi prima di investire risorse

Le raccomandazioni di questa sezione sono da considerarsi PRELIMINARI
e soggette a revisione post-allineamento.

{self._format_conflict_warnings(conflicts) if conflicts else ""}
"""

    def _format_conflict_warnings(self, conflicts: list) -> str:
        """Formatta i conflitti come warning per l'agente."""
        if not conflicts:
            return ""

        warnings = ["**CONFLITTI RILEVATI DA GESTIRE:**"]
        for c in conflicts[:3]:  # Max 3 conflitti
            area = c.get('area', c.area if hasattr(c, 'area') else 'N/A')
            description = c.get('description', c.description if hasattr(c, 'description') else '')
            severity = c.get('severity', c.severity if hasattr(c, 'severity') else 'medium')

            severity_icon = {'high': '🔴', 'medium': '🟡', 'low': '🟢'}.get(severity, '⚪')
            warnings.append(f"- {severity_icon} **{area}**: {description}")

        return "\n".join(warnings)

    def generate(
        self,
        club_data: Dict,
        research_data: Dict = None,
        context: Dict = None,
        stakeholder_meta: Dict = None,
        rag_context: List[Any] = None,
        wiki_context: str = ""
    ) -> Dict[str, Any]:
        """
        Genera output per l'area di competenza, usando il File Search Tool.

        Args:
            club_data: Dati del club
            research_data: Dati da ricerca web
            context: Output di altri agenti (per coordinator)
            stakeholder_meta: Metadati stakeholder
            rag_context: Contesto RAG (documenti simili)
        """
        if not self.available:
            return self._generate_mock(club_data)

        prompt_content = self._build_simple_prompt(
            club_data,
            research_data,
            context,
            stakeholder_meta,
            rag_context,
            wiki_context
        )

        # === AI CACHE CHECK ===
        cached_response = self.cache.get(prompt_content)
        if cached_response:
            logger.info(f"⚡ AI Cache HIT for agent {self.spec.name}")
            raw_content = cached_response
            citations = [] # Citations not cached/needed for replay
        else:
            # === OLLAMA PATH (adapter layer) ===
            if self._generation_provider is not None:
                try:
                    logger.debug(f"Invio richiesta a Ollama per {self.spec.name}")
                    raw_content = self._generation_provider.generate(
                        prompt=prompt_content,
                        temperature=MODEL_CONFIG.temperature,
                        max_tokens=MODEL_CONFIG.max_tokens,
                    )
                    citations = []
                    self.cache.set(prompt_content, raw_content)
                except Exception as e:
                    wrapped = handle_exception(e, context=f"agent_{self.spec.name}_ollama")
                    log_exception(wrapped, context=f"agent_{self.spec.name}")
                    return {'content': '', 'sources': [], 'unverified_claims': [], 'metadata': {'error_id': wrapped.error_id, 'error_msg': wrapped.user_message}}

            # === GEMINI DIRECT PATH (primary when HF broken) ===
            elif self._provider == "gemini_direct":
                _gapi_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY") or GEMINI_API_KEY
                citations = []
                with _gemini_semaphore:
                    _since = time.time() - _gemini_last_call[0]
                    if _since < _GEMINI_MIN_INTERVAL:
                        _tw = _GEMINI_MIN_INTERVAL - _since
                        logger.info(f"Agent {self.spec.name}: Gemini throttle {_tw:.1f}s")
                        time.sleep(_tw)
                    _gemini_last_call[0] = time.time()
                    try:
                        genai.configure(api_key=_gapi_key)
                        _model = genai.GenerativeModel("gemini-2.0-flash")
                        _response = _model.generate_content(
                            prompt_content,
                            generation_config=genai.types.GenerationConfig(
                                temperature=MODEL_CONFIG.temperature,
                                max_output_tokens=MODEL_CONFIG.max_tokens,
                            )
                        )
                        raw_content = _response.text or ""
                        if raw_content.strip():
                            logger.info(f"Agent {self.spec.name}: Gemini Direct OK ({len(raw_content)} chars)")
                            self.cache.set(prompt_content, raw_content)
                        else:
                            logger.error(f"Agent {self.spec.name}: Gemini Direct risposta vuota")
                    except Exception as gemini_e:
                        logger.error(f"Agent {self.spec.name}: Gemini Direct FAILED — {type(gemini_e).__name__}: {gemini_e}")
                        # --- NVIDIA NIM fallback (Gemma 3 27B, free endpoint) ---
                        _nim_key = os.environ.get("NVIDIA_API_KEY") or NVIDIA_API_KEY
                        if _nim_key:
                            try:
                                logger.info(f"Agent {self.spec.name}: NIM fallback → google/gemma-3-27b-it")
                                _nim_client = _OpenAI(
                                    base_url="https://integrate.api.nvidia.com/v1",
                                    api_key=_nim_key,
                                )
                                _nim_resp = _nim_client.chat.completions.create(
                                    model="google/gemma-3-27b-it",
                                    messages=[{"role": "user", "content": prompt_content}],
                                    temperature=MODEL_CONFIG.temperature,
                                    max_tokens=MODEL_CONFIG.max_tokens,
                                )
                                raw_content = _nim_resp.choices[0].message.content or ""
                                if raw_content.strip():
                                    logger.info(f"Agent {self.spec.name}: NIM OK ({len(raw_content)} chars)")
                                    self.cache.set(prompt_content, raw_content)
                                else:
                                    logger.error(f"Agent {self.spec.name}: NIM risposta vuota")
                            except Exception as nim_e:
                                logger.error(f"Agent {self.spec.name}: NIM FAILED — {type(nim_e).__name__}: {nim_e}")
                                wrapped = handle_exception(gemini_e, context=f"agent_{self.spec.name}_gemini_direct")
                                log_exception(wrapped, context=f"agent_{self.spec.name}")
                                return {'content': '', 'sources': [], 'unverified_claims': [], 'metadata': {'error_id': wrapped.error_id, 'error_msg': wrapped.user_message}}
                        else:
                            wrapped = handle_exception(gemini_e, context=f"agent_{self.spec.name}_gemini_direct")
                            log_exception(wrapped, context=f"agent_{self.spec.name}")
                            return {'content': '', 'sources': [], 'unverified_claims': [], 'metadata': {'error_id': wrapped.error_id, 'error_msg': wrapped.user_message}}

            # === HUGGINGFACE SERVERLESS INFERENCE PATH ===
            elif self._provider == "huggingface" and self._hf_client:
                try:
                    logger.debug(f"Invio richiesta a HF Inference [{self._hf_client.model}] per {self.spec.name}")
                    raw_content = self._hf_client.generate_content(
                        prompt_content,
                        temperature=MODEL_CONFIG.temperature,
                        max_tokens=MODEL_CONFIG.max_tokens,
                    )
                    citations = []
                    self.cache.set(prompt_content, raw_content)
                except Exception as e:
                    logger.warning(f"Agent {self.spec.name}: HF exhausted ({e}), trying Gemini fallback")
                    # Gemini fallback quando tutti i modelli HF falliscono
                    _gapi_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY") or GEMINI_API_KEY
                    if GENAI_AVAILABLE and _gapi_key:
                        citations = []
                        for _gemini_attempt in range(3):
                            try:
                                if _gemini_attempt > 0:
                                    # 429 rate limit clears after ~60s on free tier
                                    _retry_delay = __import__('random').uniform(55, 75)
                                    logger.warning(f"Agent {self.spec.name}: Gemini retry {_gemini_attempt}/2 in {_retry_delay:.1f}s (rate-limit backoff)")
                                    time.sleep(_retry_delay)
                                with _gemini_semaphore:
                                    # Rate-throttle: enforce min 7s between calls (≤8 RPM)
                                    _since = time.time() - _gemini_last_call[0]
                                    if _since < _GEMINI_MIN_INTERVAL:
                                        _tw = _GEMINI_MIN_INTERVAL - _since
                                        logger.info(f"Agent {self.spec.name}: Gemini throttle {_tw:.1f}s")
                                        time.sleep(_tw)
                                    _gemini_last_call[0] = time.time()
                                    genai.configure(api_key=_gapi_key)
                                    _fallback_model = genai.GenerativeModel("gemini-2.0-flash")
                                    _response = _fallback_model.generate_content(
                                        prompt_content,
                                        generation_config=genai.types.GenerationConfig(
                                            temperature=MODEL_CONFIG.temperature,
                                            max_output_tokens=MODEL_CONFIG.max_tokens,
                                        )
                                    )
                                raw_content = _response.text or ""
                                if not raw_content.strip():
                                    logger.error(f"Agent {self.spec.name}: Gemini fallback returned EMPTY content (finish_reason={getattr(_response.candidates[0] if _response.candidates else None, 'finish_reason', 'unknown')})")
                                else:
                                    logger.info(f"Agent {self.spec.name}: Gemini fallback OK ({len(raw_content)} chars)")
                                self.cache.set(prompt_content, raw_content)
                                break  # success — exit retry loop
                            except Exception as gemini_e:
                                _emsg = str(gemini_e).lower()
                                _etype = type(gemini_e).__name__.lower()
                                _is_rate_limit = (
                                    '429' in _emsg or 'exhausted' in _emsg or
                                    'quota' in _emsg or 'ratelimit' in _etype or
                                    'rate_limit' in _etype or 'resource' in _etype
                                )
                                logger.warning(f"Agent {self.spec.name}: Gemini exc type={type(gemini_e).__name__} is_rl={_is_rate_limit} attempt={_gemini_attempt}")
                                if _is_rate_limit and _gemini_attempt < 2:
                                    logger.warning(f"Agent {self.spec.name}: Gemini 429 attempt {_gemini_attempt+1}/3, will retry")
                                    continue
                                logger.error(f"Agent {self.spec.name}: Gemini fallback FAILED — {type(gemini_e).__name__}: {gemini_e}")
                                wrapped = handle_exception(gemini_e, context=f"agent_{self.spec.name}_gemini_fallback")
                                log_exception(wrapped, context=f"agent_{self.spec.name}")
                                return {'content': '', 'sources': [], 'unverified_claims': [], 'metadata': {'error_id': wrapped.error_id, 'error_msg': wrapped.user_message}}
                    else:
                        wrapped = handle_exception(e, context=f"agent_{self.spec.name}_hf")
                        log_exception(wrapped, context=f"agent_{self.spec.name}")
                        return {'content': '', 'sources': [], 'unverified_claims': [], 'metadata': {'error_id': wrapped.error_id, 'error_msg': wrapped.user_message}}

            # === OPENROUTER PATH (primary: Gemma, fallback: Gemini Flash) ===
            elif self._provider == "openrouter" and self._openrouter_client:
                try:
                    logger.debug(f"Invio richiesta a OpenRouter [{self._openrouter_client.model}] per {self.spec.name}")
                    raw_content = self._openrouter_client.generate_content(
                        prompt_content,
                        temperature=MODEL_CONFIG.temperature,
                        max_tokens=MODEL_CONFIG.max_tokens,
                    )
                    citations = []
                    self.cache.set(prompt_content, raw_content)
                except Exception as e:
                    # Gemma failed — attempt Gemini Flash fallback (paid, controlled)
                    logger.warning(f"Agent {self.spec.name}: Gemma failed ({e}), trying Gemini Flash fallback")
                    or_key = self._openrouter_client.api_key if hasattr(self._openrouter_client, 'api_key') else ""
                    try:
                        fallback_client = OpenRouterClient(api_key=or_key, model=OPENROUTER_FALLBACK_MODEL)
                        raw_content = fallback_client.generate_content(
                            prompt_content,
                            temperature=MODEL_CONFIG.temperature,
                            max_tokens=MODEL_CONFIG.max_tokens,
                        )
                        citations = []
                        logger.info(f"Agent {self.spec.name}: Gemini Flash fallback OK")
                        self.cache.set(prompt_content, raw_content)
                    except Exception as fallback_e:
                        wrapped = handle_exception(fallback_e, context=f"agent_{self.spec.name}_fallback")
                        log_exception(wrapped, context=f"agent_{self.spec.name}")
                        return {'content': '', 'sources': [], 'unverified_claims': [], 'metadata': {'error_id': wrapped.error_id, 'error_msg': wrapped.user_message}}

            # === GEMINI PATH (default) ===
            else:
              try:
                logger.debug(f"Invio richiesta a Gemini per {self.spec.name}")
                response = self.model.generate_content(
                    prompt_content,
                    generation_config=genai.types.GenerationConfig(
                        temperature=MODEL_CONFIG.temperature,
                        max_output_tokens=MODEL_CONFIG.max_tokens,
                    )
                )
                raw_content = response.text
                citations = []

                # Salva in cache
                self.cache.set(prompt_content, raw_content)

              except InvalidArgument as e:
                # FALLBACK: Se errore 400 (spesso per tools non supportati/deprecati), riprova senza tools
                if "google_search" in str(e) or "tool" in str(e) or "supported" in str(e):
                    logger.warning(f"Agent {self.spec.name} tool error (Fallback triggered): {e}")
                    try:
                        # Riprova SENZA tools
                        logger.info(f"Retrying Agent {self.spec.name} WITHOUT tools...")
                        fallback_model = self.model or genai.GenerativeModel(MODEL_CONFIG.name) # No tools
                        response = fallback_model.generate_content(
                            prompt_content,
                            generation_config=genai.types.GenerationConfig(
                                temperature=MODEL_CONFIG.temperature,
                                max_output_tokens=MODEL_CONFIG.max_tokens,
                            )
                        )
                        raw_content = response.text
                        citations = []
                        # Aggiungi nota al contenuto
                        raw_content += "\n\n*(Nota: Ricerca Google disabilitata per questa sezione a causa di restrizioni API)*"
                    except Exception as fallback_e:
                        err = AgentError(
                            message=f"Agent {self.spec.name} fallback failed: {fallback_e}",
                            details={"agent": self.spec.name, "fallback_error": str(fallback_e)}
                        )
                        log_exception(err, context=f"agent_{self.spec.name}")
                        return {'content': '', 'sources': [], 'unverified_claims': [], 'metadata': {'error_id': err.error_id, 'error_msg': err.user_message}}
                else:
                    err = AgentError(
                        message=f"Agent {self.spec.name} InvalidArgument: {e}",
                        details={"agent": self.spec.name, "error_type": "InvalidArgument"}
                    )
                    log_exception(err, context=f"agent_{self.spec.name}")
                    return {'content': '', 'sources': [], 'unverified_claims': [], 'metadata': {'error_id': err.error_id, 'error_msg': err.user_message}}

              except Exception as e:
                # Map to appropriate error type
                wrapped = handle_exception(e, context=f"agent_{self.spec.name}")
                log_exception(wrapped, context=f"agent_{self.spec.name}")
                return {'content': '', 'sources': [], 'unverified_claims': [], 'metadata': {'error_id': wrapped.error_id, 'error_msg': wrapped.user_message}}

        cleaned = self._post_process(raw_content)
        content, sources, unverified = self.sourcer.process_content(cleaned, context=club_data.get('club_name', ''))

        if citations:
            sources.append({"name": f"Riferimenti da Knowledge Base ({len(citations)} doc.)", "url": ", ".join(citations), "is_trusted": True})

        return {
            'content': content,
            'sources': sources,
            'unverified_claims': unverified,
            'metadata': {'agent': self.spec.name, 'role': self.spec.role.value}
        }

    def _build_simple_prompt(
        self,
        club_data: Dict,
        research_data: Dict = None,
        context: Dict = None,
        stakeholder_meta: Dict = None,
        rag_context: List[Any] = None,
        wiki_context: str = ""
    ) -> str:
        """
        Costruisce un prompt semplificato con supporto per conflict-aware generation e RAG.
        """
        club_info = f"DATI CLUB:\n- Nome: {club_data.get('club_name', 'N/A')}\n- Categoria: {club_data.get('category', 'N/A')}"
        benchmark_info = self._get_relevant_benchmarks(club_data.get('category', ''))

        # === RAG CONTEXT (BEST PRACTICES) ===
        rag_info = ""
        if rag_context:
            rag_info = "\n--- \n## 🧠 MEMORIA STORICA E BEST PRACTICE (RAG)\n"
            rag_info += "Il sistema ha recuperato i seguenti esempi da piani di successo simili. "
            rag_info += "Usa questi contenuti come ispirazione per tono, struttura e qualità, ma ADATTA rigorosamente al club attuale.\n\n"
            
            for idx, doc in enumerate(rag_context[:2]): # Max 2 docs per non inquinare
                # Gestisci sia oggetti Document che dict
                content = doc.content if hasattr(doc, 'content') else doc.get('content', '')
                club = doc.club_name if hasattr(doc, 'club_name') else doc.get('club_name', 'Altro Club')
                
                # Prendi solo la parte rilevante (prime 1000 parole)
                preview = content[:1500] + "..." if len(content) > 1500 else content
                rag_info += f"**ESEMPIO {idx+1} (da {club}):**\n{preview}\n\n"
            
            rag_info += "---\n"

        # === WIKI KNOWLEDGE BASE ===
        wiki_info = ""
        if wiki_context:
            wiki_info = "\n---\n" + wiki_context + "\n---\n"

        # === STAKEHOLDER CONTEXT (Multi-Stakeholder Conflict Awareness) ===
        stakeholder_info = ""
        tone_directive = ""

        if stakeholder_meta:
            alignment_score = stakeholder_meta.get('alignment_score', 100)
            conflicts = stakeholder_meta.get('conflicts', [])
            synthesized_vision = stakeholder_meta.get('synthesized_vision', '')
            swot = stakeholder_meta.get('swot_aggregated', {})
            priorities = stakeholder_meta.get('priority_ranking', [])

            # Direttiva di tono basata su alignment
            tone_directive = self._get_tone_directive(alignment_score, conflicts)

            # Info stakeholder per il prompt
            stakeholder_info = f"""
---
## CONTESTO MULTI-STAKEHOLDER

**Alignment Score:** {alignment_score:.0f}/100
**Stakeholder consultati:** {stakeholder_meta.get('stakeholder_count', 'N/A')}

{tone_directive}
"""
            # Aggiungi visione sintetizzata se presente
            if synthesized_vision:
                # Tronca se troppo lunga
                vision_preview = synthesized_vision[:800] + '...' if len(synthesized_vision) > 800 else synthesized_vision
                stakeholder_info += f"""
**VISIONE STRATEGICA SINTETIZZATA (da stakeholder):**
{vision_preview}
"""
            # Aggiungi SWOT aggregato
            if swot:
                stakeholder_info += "\n**SWOT AGGREGATO (consenso stakeholder):**\n"
                for category, items in swot.items():
                    if items:
                        items_list = items[:3] if isinstance(items[0], str) else [i[0] for i in items[:3]]
                        stakeholder_info += f"- {category.title()}: {', '.join(items_list)}\n"

            # Aggiungi priorità
            if priorities:
                prio_list = priorities[:5] if isinstance(priorities[0], str) else [p[0] for p in priorities[:5]]
                stakeholder_info += f"\n**PRIORITÀ STRATEGICHE (weighted ranking):** {', '.join(prio_list)}\n"

            stakeholder_info += "---\n"

        # Dati sintetizzati dal webhook (se presenti in club_data)
        synthesized_from_club = ""
        
        # Estrai dati specifici da questionario (additional_data in club_data)
        questionnaire_data = []
        for key, value in club_data.items():
            if club_data.get(f"{key}_source") == "questionnaire":
                label = key.replace('_', ' ').title()
                questionnaire_data.append(f"- {label}: {value}")
        
        if questionnaire_data:
            synthesized_from_club += "\n**DATI REALI DA QUESTIONARIO BOARD (OBBLIGATORIO CITARE FONTE):**\n"
            synthesized_from_club += "\n".join(questionnaire_data) + "\n"
            synthesized_from_club += "**ISTRUZIONE FONTE:** Quando usi uno di questi dati, scrivi sempre '(fonte: questionario)' subito dopo il dato.\n"

        if club_data.get('synthesized_vision'):
            synthesized_from_club += f"\n**VISIONE STRATEGICA SINTETIZZATA:**\n{club_data['synthesized_vision'][:600]}\n"
        if club_data.get('swot_aggregated'):
            synthesized_from_club += "\n**SWOT AGGREGATO:**\n"
            for cat, items in club_data['swot_aggregated'].items():
                if items:
                    synthesized_from_club += f"- {cat.title()}: {', '.join(items[:3])}\n"
        if club_data.get('priority_ranking'):
            synthesized_from_club += f"\n**PRIORITÀ:** {', '.join(club_data['priority_ranking'][:5])}\n"

        research_info = ""
        if research_data:
            research_text = json.dumps(research_data, indent=2, ensure_ascii=False)
            research_info = f"\nDATI DA RICERCA WEB (sintesi):\n{research_text[:1000]}"

        context_info = ""
        if context:
            context_text = json.dumps(context, indent=2, ensure_ascii=False)
            context_info = f"\nOUTPUT ALTRI AGENTI (per sintesi):\n{context_text[:1500]}"

        return f"{self.spec.system_prompt}\n\n{rag_info}{wiki_info}{stakeholder_info}{club_info}\n{synthesized_from_club}{benchmark_info}\n{research_info}\n{context_info}"
        
    def _get_relevant_benchmarks(self, category: str) -> str:
        """Recupera benchmark rilevanti per la categoria"""
        lines = ["\nBENCHMARK DI CATEGORIA:"]
        sg_data = BENCHMARKS.settore_giovanile_media_tesserati.get(category)
        if sg_data: lines.append(f"- Tesserati SG media: {sg_data['media']}")
        budget_data = BENCHMARKS.budget_medio_per_categoria.get(category)
        if budget_data: lines.append(f"- Budget medio: €{budget_data['media']:,}".replace(",", "."))
        return "\n".join(lines) if len(lines) > 1 else ""

    def _post_process(self, text: str) -> str:
        """Pulizia linguistica del testo generato."""
        # Guard contro None o tipi non validi
        if text is None:
            logger.warning(f"Agent {self.spec.name} returned None content")
            return f"## {self.spec.name}\n\nContenuto non disponibile - riprovare la generazione."
        if not isinstance(text, str):
            logger.warning(f"Agent {self.spec.name} returned non-string: {type(text)}")
            return str(text) if text else f"## {self.spec.name}\n\nContenuto non disponibile."
        # Pattern da rimuovere
        chatbot_patterns = [r'^OK\.?\s*', r'^Ecco[^.]+\.\s*', r'^Certo[,!.]?\s*']
        for pattern in chatbot_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE | re.MULTILINE)

        # Rimuovi spazi e newline eccessivi
        text = re.sub(r'\n\s*\n\s*\n', '\n\n', text).strip()
        return text

    def _generate_mock(self, club_data: Dict) -> Dict[str, Any]:
        """Genera output mock quando Gemini non disponibile"""
        return {
            'content': f"## {self.spec.name}\nSezione generata in modalità demo.",
            'sources': [], 'unverified_claims': [], 'metadata': {'mock': True}
        }


# =============================================================================
# MULTI-AGENT ORCHESTRATOR
# =============================================================================

class MultiAgentOrchestrator:
    """
    Orchestratore del sistema multi-agente.
    Usa il File Search Tool per il grounding.
    """

    def __init__(self, knowledge_store=None, file_search_store_name: str | None = None):
        self.agents: Dict[AgentRole, StrategicAgent] = {}
        self.knowledge_store = knowledge_store
        self.file_search_store_name = file_search_store_name
        self.async_client = AsyncGeminiClient(max_workers=6, rate_limit=60)  # OPT-002
        self.wiki_reader = WikiReader()
        self._init_agents()

    def _init_agents(self):
        """Inizializza agenti con il nome dello store RAG."""
        for role, spec in AGENT_SPECS.items():
            self.agents[role] = StrategicAgent(spec, file_search_store_name=self.file_search_store_name)
        logger.info(f"Initialized {len(self.agents)} agents (RAG learning enabled: {bool(self.file_search_store_name)})")

    def reinit(self):
        """Reinizializza tutti gli agenti (es. dopo cambio API key)."""
        logger.info("Reinitializing all agents...")
        self._init_agents()

    def generate_strategic_plan(
        self,
        club_data: Dict,
        research_data: Dict = None,
        parallel: bool = True,
        on_progress: Optional[Callable[[str, float], None]] = None
    ) -> Dict[str, Any]:
        """
        Genera piano strategico completo.

        Args:
            club_data: Dati del club
            research_data: Dati da web research
            parallel: Se eseguire agenti in parallelo
            on_progress: Callback opzionale (messaggio, progresso %)

        Returns:
            {
                'plan': Dict[str, str],  # Sezioni del piano
                'sources': List[Dict],    # Tutte le fonti
                'metadata': Dict (include 'generation_timings' e 'total_generation_time')
            }
        """
        import time

        start_time = time.time()
        club_name = club_data.get('club_name', 'Unknown')
        logger.info(f"Generating strategic plan for: {club_name}")
        
        if on_progress:
            on_progress(f"Avvio orchestrazione multi-agente per {club_name}...", 10)

        if parallel and AGENT_CONFIG.parallel_execution:
            result = self._generate_parallel(club_data, research_data, on_progress=on_progress)
        else:
            result = self._generate_sequential(club_data, research_data, on_progress=on_progress)

        # Aggiungi timing totale al metadata
        total_time = time.time() - start_time
        result['metadata']['total_generation_time'] = round(total_time, 2)
        logger.info(f"Plan generation completed in {total_time:.2f}s")
        
        if on_progress:
            on_progress("Generazione multi-agente completata.", 70)

        return result

    def _generate_sequential(
        self,
        club_data: Dict,
        research_data: Dict = None,
        on_progress: Optional[Callable[[str, float], None]] = None
    ) -> Dict[str, Any]:
        """Esecuzione sequenziale agenti"""
        import time

        results = {}
        all_sources = []
        all_unverified = []
        agent_timings = {}

        # Ordina per priorità
        sorted_agents = sorted(
            [(role, agent) for role, agent in self.agents.items() if role != AgentRole.COORDINATOR],
            key=lambda x: AGENT_SPECS[x[0]].priority
        )

        total_agents = len(sorted_agents)

        # Esegui agenti specializzati
        for i, (role, agent) in enumerate(sorted_agents):
            agent_start = time.time()
            if on_progress:
                progress = 10 + (i / total_agents) * 50
                on_progress(f"Esecuzione agente: {agent.spec.name}...", progress)
            
            logger.info(f"Running agent: {agent.spec.name}")
            
            # --- RAG CONTEXT FETCHING ---
            rag_context = []
            if self.knowledge_store:
                try:
                    category = club_data.get('category', 'Eccellenza')
                    # Usa il nome dell'agente o ruolo come filtro sezione
                    section_keyword = agent.spec.name.split()[0]  # Es. "STW", "Financial"
                    rag_context = self.knowledge_store.get_context_for_generation(
                        club_category=category,
                        section_type=section_keyword
                    )
                    if rag_context:
                        logger.info(f"RAG: Fetched {len(rag_context)} examples for {agent.spec.name}")
                except Exception as e:
                    logger.warning(f"RAG fetch failed for {agent.spec.name}: {e}")
            # ---------------------------

            # --- WIKI CONTEXT ---
            wiki_context = ""
            if self.wiki_reader.available:
                club_slug = club_data.get("club_slug", "")
                if not club_slug:
                    from wiki_reader import slugify
                    club_slug = slugify(club_data.get("club_name", ""))
                wiki_context = self.wiki_reader.get_context_for_agent(
                    agent.spec.name, club_slug, club_data.get("category", "eccellenza").lower()
                )
            # --------------------

            output = agent.generate(
                club_data,
                research_data,
                rag_context=rag_context,
                wiki_context=wiki_context
            )

            agent_time = time.time() - agent_start
            agent_timings[agent.spec.name] = round(agent_time, 2)
            logger.info(f"Agent {agent.spec.name} completed in {agent_time:.2f}s")

            # Structured logging (STAB-004)
            if log_agent_execution:
                log_agent_execution(
                    agent_name=agent.spec.name,
                    plan_id=club_data.get("plan_id", "unknown"),
                    duration_seconds=agent_time,
                    success="error_id" not in output.get("metadata", {})
                )

            results[role.value] = output['content']
            all_sources.extend(output.get('sources', []))
            all_unverified.extend(output.get('unverified_claims', []))

        # Esegui coordinator con contesto
        coord_start = time.time()
        coordinator = self.agents[AgentRole.COORDINATOR]
        coord_output = coordinator.generate(
            club_data,
            research_data,
            context=results
        )
        coord_time = time.time() - coord_start
        agent_timings['Coordinator'] = round(coord_time, 2)
        logger.info(f"Coordinator completed in {coord_time:.2f}s")

        results['executive_summary'] = coord_output['content']
        results['coordinator_summary'] = coord_output['content']  # Anche come sintesi strategica
        all_sources.extend(coord_output.get('sources', []))

        # Calcola stime finanziarie con sistema Tier 1/2/3
        category = club_data.get('category', 'Eccellenza')
        financial_estimates = estimate_missing_financials(club_data, category)

        # Converti EstimatedValue in dict serializzabili
        estimates_dict = {}
        estimated_fields = {}
        for key, est in financial_estimates.items():
            estimates_dict[key] = {
                'value': est.value,
                'tier': est.tier.value,
                'confidence': est.confidence,
                'source': est.source
            }
            estimated_fields[key] = est.tier.value  # Per sezione metodologia

        return {
            'plan': results,
            'sources': self._deduplicate_sources(all_sources),
            'unverified_claims': list(set(all_unverified)),
            'metadata': {
                'generated_at': datetime.now().isoformat(),
                'club_name': club_data.get('club_name', ''),
                'category': category,
                'agents_count': len(self.agents),
                'financial_estimates': estimates_dict,
                'estimated_fields': estimated_fields,
                'primary_color': club_data.get('primary_color', '#1a365d'),
                'secondary_color': club_data.get('secondary_color', '#ffffff'),
                'agent_timings': agent_timings,
            }
        }

    def _generate_parallel(
        self,
        club_data: Dict,
        research_data: Dict = None,
        on_progress: Optional[Callable[[str, float], None]] = None
    ) -> Dict[str, Any]:
        """
        Esecuzione parallela agenti usando ThreadPoolExecutor (OPT-002).
        TRUE parallel execution - 6 agents running concurrently.
        """
        import asyncio

        agent_timings = {}
        parallel_start = time.time()
        
        # Lock per aggiornamento thread-safe dei progressi
        import threading
        progress_lock = threading.Lock()
        completed_count = [0]
        total_parallel = len([r for r in self.agents if r != AgentRole.COORDINATOR])

        def make_agent_task(role: AgentRole, agent: StrategicAgent):
            """Create a closure that captures role and agent for parallel execution"""
            def task():
                agent_start = time.time()

                # --- RAG CONTEXT FETCHING ---
                rag_context = []
                if self.knowledge_store:
                    try:
                        category = club_data.get('category', 'Eccellenza')
                        section_keyword = agent.spec.name.split()[0]
                        rag_context = self.knowledge_store.get_context_for_generation(
                            club_category=category,
                            section_type=section_keyword
                        )
                    except Exception as e:
                        logger.warning(f"RAG fetch failed for {agent.spec.name}: {e}")
                # ---------------------------

                # --- WIKI CONTEXT ---
                wiki_context = ""
                if self.wiki_reader.available:
                    club_slug = club_data.get("club_slug", "")
                    if not club_slug:
                        from wiki_reader import slugify
                        club_slug = slugify(club_data.get("club_name", ""))
                    wiki_context = self.wiki_reader.get_context_for_agent(
                        agent.spec.name, club_slug, club_data.get("category", "eccellenza").lower()
                    )
                # --------------------

                output = agent.generate(
                    club_data,
                    research_data,
                    rag_context=rag_context,
                    wiki_context=wiki_context
                )

                agent_time = time.time() - agent_start
                agent_timings[agent.spec.name] = round(agent_time, 2)
                logger.info(f"Agent {agent.spec.name} completed in {agent_time:.2f}s")
                
                # Update progress
                if on_progress:
                    with progress_lock:
                        completed_count[0] += 1
                        current_progress = 10 + (completed_count[0] / total_parallel) * 50
                        on_progress(f"Agente {agent.spec.name} completato.", current_progress)

                # Structured logging (STAB-004)
                if log_agent_execution:
                    log_agent_execution(
                        agent_name=agent.spec.name,
                        plan_id=club_data.get("plan_id", "unknown"),
                        duration_seconds=agent_time,
                        success="error_id" not in output.get("metadata", {})
                    )

                return (role.value, output)
            return task

        # Prepare tasks for parallel execution
        tasks = []
        task_names = []
        roles_order = []

        for role, agent in self.agents.items():
            if role != AgentRole.COORDINATOR:
                tasks.append(make_agent_task(role, agent))
                task_names.append(agent.spec.name)
                roles_order.append(role.value)

        # Execute in TRUE parallel using ThreadPoolExecutor
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            # Timeout di 5 minuti (300s) per evitare loop infiniti
            results_list = loop.run_until_complete(
                self.async_client.execute_parallel(tasks, task_names, timeout=300)
            )
        except Exception as e:
            err = GenerationError(
                message=f"Fatal error in parallel execution: {e}",
                details={"parallel_tasks": task_names, "error": str(e)}
            )
            log_exception(err, context="parallel_execution")
            results_list = [Exception(err.user_message) for _ in tasks]
        finally:
            loop.close()

        # Convert results list to dict
        agent_results = {}
        for result in results_list:
            if isinstance(result, Exception):
                logger.error(f"Agent task failed: {result}")
                continue
            role_value, output = result
            agent_results[role_value] = output

        parallel_time = time.time() - parallel_start
        agent_timings['Parallel_Execution_Time'] = round(parallel_time, 2)
        logger.info(f"Parallel execution completed in {parallel_time:.2f}s")

        # Warn if all agents returned empty content (quota / timeout)
        empty_agents = [k for k, v in agent_results.items() if not v.get('content', '').strip()]
        if empty_agents:
            logger.warning(f"Agents returned empty content: {empty_agents} — possible quota exhaustion or timeout")

        # Estrai contenuti e fonti
        plan = {}
        all_sources = []
        all_unverified = []

        for role_value, output in agent_results.items():
            plan[role_value] = output['content']
            all_sources.extend(output.get('sources', []))
            all_unverified.extend(output.get('unverified_claims', []))

        # Coordinator
        coord_start = time.time()
        coordinator = self.agents[AgentRole.COORDINATOR]
        coord_output = coordinator.generate(club_data, research_data, context=plan)
        coord_time = time.time() - coord_start
        agent_timings['Coordinator'] = round(coord_time, 2)
        logger.info(f"Coordinator completed in {coord_time:.2f}s")

        plan['executive_summary'] = coord_output['content']
        plan['coordinator_summary'] = coord_output['content']
        all_sources.extend(coord_output.get('sources', []))

        non_empty = [k for k, v in plan.items() if v and v.strip()]
        logger.info(f"Plan assembled: {len(non_empty)}/{len(plan)} sections have content")
        if len(non_empty) == 0:
            logger.error("CRITICAL: All plan sections are empty. Check OpenRouter quota and model availability.")

        # Calcola stime finanziarie con sistema Tier 1/2/3
        category = club_data.get('category', 'Eccellenza')
        financial_estimates = estimate_missing_financials(club_data, category)

        # Converti EstimatedValue in dict serializzabili
        estimates_dict = {}
        estimated_fields = {}
        for key, est in financial_estimates.items():
            estimates_dict[key] = {
                'value': est.value,
                'tier': est.tier.value,
                'confidence': est.confidence,
                'source': est.source
            }
            estimated_fields[key] = est.tier.value

        return {
            'plan': plan,
            'sources': self._deduplicate_sources(all_sources),
            'unverified_claims': list(set(all_unverified)),
            'metadata': {
                'generated_at': datetime.now().isoformat(),
                'club_name': club_data.get('club_name', ''),
                'category': category,
                'agents_count': len(self.agents),
                'parallel_execution': True,
                'financial_estimates': estimates_dict,
                'estimated_fields': estimated_fields,
                'primary_color': club_data.get('primary_color', '#1a365d'),
                'secondary_color': club_data.get('secondary_color', '#ffffff'),
                'agent_timings': agent_timings,
            }
        }

    def _deduplicate_sources(self, sources: List[Dict]) -> List[Dict]:
        """Rimuove fonti duplicate"""
        seen = set()
        unique = []
        for s in sources:
            url = s.get('url', '')
            if url and url not in seen:
                unique.append(s)
                seen.add(url)
        return unique

    def generate_single_section(
        self,
        section: str,
        club_data: Dict,
        research_data: Dict = None
    ) -> Dict[str, Any]:
        """
        Genera singola sezione del piano.
        Utile per rigenerazione/editing.

        Args:
            section: Nome sezione (es. "technical_sporting")
            club_data: Dati club
            research_data: Dati ricerca

        Returns:
            Output agente per quella sezione
        """
        role_map = {
            'executive_summary': AgentRole.COORDINATOR,
            'technical_sporting': AgentRole.TECHNICAL_SPORTING,
            'youth_development': AgentRole.YOUTH_DEVELOPMENT,
            'infrastructure': AgentRole.INFRASTRUCTURE,
            'marketing_commercial': AgentRole.MARKETING_COMMERCIAL,
            'social_sustainability': AgentRole.SOCIAL_SUSTAINABILITY,
            'governance': AgentRole.GOVERNANCE,
            'financial': AgentRole.FINANCIAL,
        }

        role = role_map.get(section)
        if not role:
            raise ValueError(f"Unknown section: {section}")

        agent = self.agents[role]
        return agent.generate(club_data, research_data)

    def get_agent_info(self) -> List[Dict]:
        """Info su tutti gli agenti"""
        return [
            {
                'role': role.value,
                'name': agent.spec.name,
                'expertise': agent.spec.expertise,
                'available': agent.available,
            }
            for role, agent in self.agents.items()
        ]
