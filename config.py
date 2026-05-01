"""
Rooting Future Strategy Engine v5.4
Configurazione centralizzata

Sistema AI multi-agente per generare piani strategici professionali
per società calcistiche di tutto il mondo.
"""

import os
from pathlib import Path
from typing import List, Dict
from dataclasses import dataclass, field


# =============================================================================
# LOAD .env FILE AND config.local.json
# =============================================================================

import json
import logging

_config_logger = logging.getLogger(__name__)


def load_dotenv():
    """Carica variabili da .env file"""
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip().lstrip('\ufeff')
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip()
                    # Rimuovi virgolette se presenti
                    if value.startswith('"') and value.endswith('"'):
                        value = value[1:-1]
                    elif value.startswith("'") and value.endswith("'"):
                        value = value[1:-1]
                    os.environ.setdefault(key, value)


def get_config_dir():
    """Ritorna la directory per i file di configurazione utente.
    Usa sempre la stessa cartella di config.py (_internal/ per exe)."""
    return Path(__file__).parent


def get_config_path():
    """Ritorna il path per config.local.json"""
    return get_config_dir() / "config.local.json"


def load_local_config():
    """Carica config.local.json se esiste (impostazioni salvate da Settings)"""
    config_path = get_config_path()
    print(f"[CONFIG] Looking for: {config_path}")

    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                local_config = json.load(f)

            # Mappa chiavi config.local.json → env vars
            key_mapping = {
                "gemini_api_key": "GEMINI_API_KEY",
                "serper_api_key": "SERPER_API_KEY",
                "tavily_api_key": "TAVILY_API_KEY",
                "openrouter_api_key": "OPENROUTER_API_KEY",
                "openrouter_model": "OPENROUTER_MODEL",
                "ai_provider": "AI_PROVIDER",
            }

            loaded_keys = []
            for config_key, env_key in key_mapping.items():
                if config_key in local_config and local_config[config_key]:
                    os.environ[env_key] = local_config[config_key]
                    loaded_keys.append(config_key)

            if loaded_keys:
                print(f"[CONFIG] OK Loaded {len(loaded_keys)} keys: {loaded_keys}")
            return True
        except Exception as e:
            print(f"[CONFIG] FAIL Failed to load: {e}")

    print("[CONFIG] No config.local.json found")
    return False


# Carica all'import (ordine importante!)
load_dotenv()       # Prima .env (valori base/development)
load_local_config() # Poi config.local.json (sovrascrive con impostazioni utente)


# =============================================================================
# PATHS
# =============================================================================

BASE_DIR = Path(__file__).parent

# On HF Spaces, /data is the persistent volume (survives restarts).
# Fall back to BASE_DIR when not running in a Space.
_HF_DATA = Path("/data")
_PERSISTENT_ROOT = _HF_DATA if _HF_DATA.exists() else BASE_DIR

OUTPUT_DIR = _PERSISTENT_ROOT / "output"
KNOWLEDGE_DIR = _PERSISTENT_ROOT / "knowledge_base"
QUESTIONNAIRE_DATA_DIR = _PERSISTENT_ROOT / "questionnaires"
ASSETS_DIR = BASE_DIR / "assets"
TEMPLATES_DIR = BASE_DIR / "templates"

# Path per memorizzare l'ID del File Search Store
FILE_SEARCH_STORE_ID_PATH = KNOWLEDGE_DIR / "file_search_store_id.txt"

# Crea directories se non esistono
OUTPUT_DIR.mkdir(exist_ok=True)
KNOWLEDGE_DIR.mkdir(exist_ok=True)
QUESTIONNAIRE_DATA_DIR.mkdir(exist_ok=True)
ASSETS_DIR.mkdir(exist_ok=True)


# =============================================================================
# API KEYS (da .env o variabili ambiente)
# =============================================================================

# La nuova libreria google-genai usa GOOGLE_API_KEY
# Supportiamo entrambi i nomi per retrocompatibilità
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "") or os.environ.get("GEMINI_API_KEY", "")
GEMINI_API_KEY = GOOGLE_API_KEY  # Alias per retrocompatibilità
SERPER_API_KEY = os.environ.get("SERPER_API_KEY", "")
TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY", "")

# OpenRouter (provider AI alternativo - OpenAI-compatible)
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")

# NVIDIA NIM (OpenAI-compatible, free Gemma endpoint — fallback when Gemini rate-limited)
NVIDIA_API_KEY = os.environ.get("NVIDIA_API_KEY", "")

# HuggingFace Inference API (same-network, no external deps on HF Spaces)
HF_TOKEN = os.environ.get("HF_TOKEN", "")
HF_MODEL = os.environ.get("HF_MODEL", "Qwen/Qwen2.5-72B-Instruct")
HF_MODEL_CHAIN = [
    "meta-llama/Llama-3.3-70B-Instruct",   # primary: confirmed working on together
    "Qwen/Qwen2.5-72B-Instruct",           # 72B fallback, multilingual
    "Qwen/Qwen2.5-32B-Instruct",           # 32B fallback, fast
    "mistralai/Mistral-Nemo-Instruct-2407", # 12B, lightweight fallback
    "Qwen/Qwen2.5-7B-Instruct",            # 7B, last resort
]

# Provider AI attivo: prefer gemini_direct when key available (HF free models all broken)
# Override con env var AI_PROVIDER se esplicito
_has_gemini = bool(os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY"))
if _has_gemini:
    _default_provider = "gemini_direct"
elif HF_TOKEN:
    _default_provider = "huggingface"
else:
    _default_provider = "openrouter"
AI_PROVIDER = os.environ.get("AI_PROVIDER", _default_provider)

# STRIPE PAYMENTS
STRIPE_PUBLIC_KEY = os.environ.get("STRIPE_PUBLIC_KEY", "pk_test_placeholder")
STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "sk_test_placeholder")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "whsec_placeholder")
CREDIT_PRICE_ID = os.environ.get("STRIPE_CREDIT_PRICE_ID", "price_placeholder") # ID del prodotto "1 Piano Strategico"

# Assicura che GOOGLE_API_KEY sia settata nell'ambiente
if GOOGLE_API_KEY:
    os.environ["GOOGLE_API_KEY"] = GOOGLE_API_KEY


# =============================================================================
# MODEL SETTINGS
# =============================================================================

@dataclass
class ModelConfig:
    """Configurazione modello AI"""
    name: str = "gemini-2.0-flash"  # Versione stabile e veloce
    temperature: float = 0.7
    max_tokens: int = 8192
    top_p: float = 0.95

    # Per RAG/File Search
    embedding_model: str = "models/embedding-001"
    chunk_size: int = 1000
    chunk_overlap: int = 200


MODEL_CONFIG = ModelConfig()


# Modelli OpenRouter
OPENROUTER_MODELS = {
    "google/gemma-3-27b-it:free": "Gemma 3 27B (primary, free)",
    "google/gemini-flash-1.5": "Gemini Flash 1.5 (fallback, paid)",
    "google/gemini-2.0-flash-001": "Gemini 2.0 Flash (fallback, paid)",
}

# Catena di modelli gratuiti: tentati in ordine su quota/errore
# Ordinati per capacità (testo lungo strutturato in italiano)
FREE_MODEL_CHAIN = [
    "google/gemma-3-27b-it:free",                   # primary (27B, 131K ctx)
    "qwen/qwen3-coder-480b-a35b-instruct:free",     # 480B MoE, 35B active, 262K ctx
    "nousresearch/hermes-3-405b-instruct:free",     # 405B Llama fine-tune, 131K ctx
    "meta-llama/llama-3.3-70b-instruct:free",       # 70B, multilingual + italiano, 66K ctx
    "google/gemma-3-12b-it:free",                   # 12B fallback minimo, 33K ctx
]

# Motore principale: Gemma 3 27B via OpenRouter (gratuito, open source)
# Fallback: Gemini Flash (a pagamento, solo su errore Gemma)
OPENROUTER_DEFAULT_MODEL = os.environ.get(
    "OPENROUTER_MODEL", "google/gemma-3-27b-it:free"
)
OPENROUTER_FALLBACK_MODEL = os.environ.get(
    "OPENROUTER_FALLBACK_MODEL", "google/gemini-flash-1.5"
)


# =============================================================================
# SOURCING SETTINGS - CRITICO PER CREDIBILITÀ
# =============================================================================

@dataclass
class SourceConfig:
    """Configurazione verifica fonti"""
    min_sources_for_verified: int = 2  # Minimo fonti per "VERIFIED"
    min_sources_for_single: int = 1    # Minimo fonti per "SINGLE_SOURCE"
    source_freshness_days: int = 365   # Dati più vecchi = warning
    max_search_results: int = 10       # Risultati per query

    # Timeout per ricerche web
    search_timeout_seconds: int = 30

    # Cache settings
    cache_enabled: bool = True
    cache_ttl_hours: int = 24


SOURCE_CONFIG = SourceConfig()


# =============================================================================
# FONTI AUTOREVOLI PER VERIFICA
# =============================================================================

TRUSTED_SOURCES: List[str] = [
    # Istituzioni calcistiche
    "figc.it",
    "lega-pro.com",
    "legaseriea.it",
    "legab.it",
    "coni.it",
    "uefa.com",
    "fifa.com",

    # Statistiche ufficiali
    "istat.it",
    "transfermarkt.it",
    "transfermarkt.com",
    "soccerway.com",
    "whoscored.com",
    "fbref.com",

    # Media sportivi autorevoli
    "gazzetta.it",
    "corrieredellosport.it",
    "tuttosport.com",
    "sportmediaset.mediaset.it",
    "sky.it",

    # Consulenza e report
    "deloitte.com",
    "kpmg.com",
    "pwc.com",
    "ey.com",

    # Banche dati economiche
    "reportcalcio.figc.it",
    "football-observatory.com",
]


# Pesi per tipo fonte (per scoring credibilità)
SOURCE_WEIGHTS: Dict[str, float] = {
    "figc.it": 1.0,
    "reportcalcio.figc.it": 1.0,
    "istat.it": 1.0,
    "lega-pro.com": 0.95,
    "legaseriea.it": 0.95,
    "deloitte.com": 0.9,
    "kpmg.com": 0.9,
    "transfermarkt.it": 0.85,
    "gazzetta.it": 0.75,
    "default": 0.5,
}


# =============================================================================
# BENCHMARK DI SETTORE - DA REPORT CALCIO FIGC
# =============================================================================

@dataclass
class BenchmarkData:
    """
    Benchmark verificati da Report Calcio FIGC e fonti ufficiali.
    Ogni dato ha fonte esplicita.
    """

    # Fonte: Report Calcio 2024 FIGC
    settore_giovanile_media_tesserati: Dict[str, Dict] = field(default_factory=lambda: {
        "Serie A": {
            "media": 350,
            "range": (280, 450),
            "fonte": "Report Calcio FIGC 2024, p.127"
        },
        "Serie B": {
            "media": 280,
            "range": (200, 350),
            "fonte": "Report Calcio FIGC 2024, p.128"
        },
        "Serie C": {
            "media": 220,
            "range": (150, 300),
            "fonte": "Report Calcio FIGC 2024, p.129"
        },
        "Serie D": {
            "media": 150,
            "range": (80, 250),
            "fonte": "Stima LND 2024"
        },
        "Promozione": {
            "media": 100,
            "range": (50, 180),
            "fonte": "Stima interna - da verificare"
        },
    })

    # Fonte: Deloitte Football Money League 2024
    budget_medio_per_categoria: Dict[str, Dict] = field(default_factory=lambda: {
        "Serie A": {
            "min": 50_000_000,
            "max": 400_000_000,
            "media": 120_000_000,
            "fonte": "Deloitte Football Money League 2024"
        },
        "Serie B": {
            "min": 8_000_000,
            "max": 35_000_000,
            "media": 18_000_000,
            "fonte": "Report Calcio FIGC 2024, p.45"
        },
        "Serie C": {
            "min": 2_000_000,
            "max": 10_000_000,
            "media": 4_500_000,
            "fonte": "Report Calcio FIGC 2024, p.47"
        },
        "Serie D": {
            "min": 300_000,
            "max": 2_000_000,
            "media": 800_000,
            "fonte": "Stima LND - elaborazione interna"
        },
    })

    # Fonte: CONI - Monitoraggio impianti sportivi 2023
    standard_infrastrutture: Dict[str, Dict] = field(default_factory=lambda: {
        "Serie A": {
            "capienza_minima_stadio": 16000,
            "campi_allenamento_minimi": 3,
            "centro_sportivo_richiesto": True,
            "fonte": "Regolamento FIGC Serie A 2024-25"
        },
        "Serie B": {
            "capienza_minima_stadio": 10000,
            "campi_allenamento_minimi": 2,
            "centro_sportivo_richiesto": True,
            "fonte": "Regolamento FIGC Serie B 2024-25"
        },
        "Serie C": {
            "capienza_minima_stadio": 4000,
            "campi_allenamento_minimi": 1,
            "centro_sportivo_richiesto": False,
            "fonte": "Regolamento Lega Pro 2024-25"
        },
    })


BENCHMARKS = BenchmarkData()


# =============================================================================
# EXPORT SETTINGS
# =============================================================================

@dataclass
class ExportConfig:
    """Configurazione export documenti"""
    # HTML chunking
    max_section_tokens: int = 4000
    generate_multipage_threshold: int = 5  # Sezioni

    # DOCX styling
    docx_template: str = "assets/docx_template.docx"
    primary_color: str = "#1a365d"  # Blu scuro
    secondary_color: str = "#2c5282"  # Blu medio
    accent_color: str = "#3182ce"  # Blu accent

    # Font settings
    heading_font: str = "Calibri"
    body_font: str = "Calibri"
    heading1_size: int = 24
    heading2_size: int = 18
    body_size: int = 11


EXPORT_CONFIG = ExportConfig()


# =============================================================================
# AGENT SETTINGS
# =============================================================================

@dataclass
class AgentConfig:
    """Configurazione sistema multi-agente"""
    max_retries: int = 3
    retry_delay_seconds: float = 2.0
    parallel_execution: bool = True
    max_parallel_agents: int = 4

    # Timeout per singolo agente
    agent_timeout_seconds: int = 120

    # Post-processing linguistico
    enable_language_cleanup: bool = True


AGENT_CONFIG = AgentConfig()


# =============================================================================
# CLUB DEFAULTS
# =============================================================================

DEFAULT_COUNTRY = "Italia"
DEFAULT_LANGUAGE = "italiano"
DEFAULT_PLAN_HORIZON_YEARS = 3  # Piano triennale


# =============================================================================
# INTERNATIONAL FOOTBALL CATEGORIES
# =============================================================================

# Tier system (applicable worldwide)
FOOTBALL_TIERS = [
    "Tier 1 - Top League (e.g., Serie A, Premier League, La Liga)",
    "Tier 2 - Second Division (e.g., Serie B, Championship, Segunda)",
    "Tier 3 - Third Division (e.g., Serie C, League One)",
    "Tier 4 - Fourth Division (e.g., Serie D, League Two)",
    "Tier 5 - Regional/Amateur",
    "Tier 6 - Local/Grassroots",
]

# Major football countries and their league structures
COUNTRIES_LEAGUES: Dict[str, List[str]] = {
    "Italy": ["Serie A", "Serie B", "Serie C", "Serie D", "Eccellenza", "Promozione"],
    "England": ["Premier League", "Championship", "League One", "League Two", "National League"],
    "Spain": ["La Liga", "Segunda Division", "Primera Federacion", "Segunda Federacion"],
    "Germany": ["Bundesliga", "2. Bundesliga", "3. Liga", "Regionalliga"],
    "France": ["Ligue 1", "Ligue 2", "National", "National 2"],
    "Netherlands": ["Eredivisie", "Eerste Divisie", "Tweede Divisie"],
    "Portugal": ["Primeira Liga", "Liga Portugal 2", "Campeonato de Portugal"],
    "Belgium": ["Pro League", "Challenger Pro League", "First Amateur Division"],
    "Brazil": ["Serie A", "Serie B", "Serie C", "Serie D"],
    "Argentina": ["Liga Profesional", "Primera Nacional", "Primera B Metropolitana"],
    "USA": ["MLS", "USL Championship", "USL League One", "USL League Two"],
    "Mexico": ["Liga MX", "Liga de Expansion MX", "Liga Premier"],
    "Japan": ["J1 League", "J2 League", "J3 League"],
    "Saudi Arabia": ["Saudi Pro League", "First Division", "Second Division"],
    "Other": ["Custom League Level"],
}

# Legacy support for Italian-specific code
CATEGORIE_CALCIO_ITALIANO = [
    "Serie A",
    "Serie B",
    "Serie C - Girone A",
    "Serie C - Girone B",
    "Serie C - Girone C",
    "Serie D",
    "Eccellenza",
    "Promozione",
    "Prima Categoria",
    "Seconda Categoria",
    "Terza Categoria",
]


# =============================================================================
# COUNTRIES AND REGIONS
# =============================================================================

# Countries for dropdown
COUNTRIES = list(COUNTRIES_LEAGUES.keys())

# Italian regions (for backward compatibility)
REGIONI_ITALIANE = [
    "Abruzzo", "Basilicata", "Calabria", "Campania", "Emilia-Romagna",
    "Friuli-Venezia Giulia", "Lazio", "Liguria", "Lombardia", "Marche",
    "Molise", "Piemonte", "Puglia", "Sardegna", "Sicilia", "Toscana",
    "Trentino-Alto Adige", "Umbria", "Valle d'Aosta", "Veneto"
]


# =============================================================================
# LOGGING
# =============================================================================

@dataclass
class LogConfig:
    """Configurazione logging"""
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file_enabled: bool = True
    file_path: str = str(OUTPUT_DIR / "rooting_future.log")
    max_file_size_mb: int = 10
    backup_count: int = 5


LOG_CONFIG = LogConfig()


# =============================================================================
# VALIDATION
# =============================================================================

def validate_config() -> Dict[str, bool]:
    """Valida configurazione critica"""
    validation = {
        "gemini_api_key": bool(GEMINI_API_KEY),
        "serper_api_key": bool(SERPER_API_KEY),
        "output_dir_writable": OUTPUT_DIR.exists() and os.access(OUTPUT_DIR, os.W_OK),
        "knowledge_dir_writable": KNOWLEDGE_DIR.exists() and os.access(KNOWLEDGE_DIR, os.W_OK),
    }

    return validation


def get_missing_config() -> List[str]:
    """Restituisce lista configurazioni mancanti"""
    validation = validate_config()
    return [key for key, valid in validation.items() if not valid]
