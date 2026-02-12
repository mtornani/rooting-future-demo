"""
Centralized Error Handling - Rooting Future Strategy Engine v6.0
Defines custom exceptions and utilities for robust error management.

STAB-002: Complete error handling system for Alpha release.
All external calls wrapped, user-friendly messages, support codes.
"""

import uuid
import logging
import traceback
from typing import Optional, Dict, Any, Callable
from functools import wraps
from datetime import datetime

logger = logging.getLogger(__name__)


# =============================================================================
# BASE EXCEPTION
# =============================================================================

class RootingFutureError(Exception):
    """
    Base exception for the application with user-friendly messages.

    All custom exceptions inherit from this class and provide:
    - user_message: Safe message to show to users
    - status_code: HTTP status code for API responses
    - error_id: Unique code for support/debugging
    - details: Technical details (hidden from users by default)
    """
    user_message = "Si è verificato un errore inaspettato. Riprova o contatta il supporto."
    status_code = 500
    recoverable = True  # Can the user retry?

    def __init__(
        self,
        message: Optional[str] = None,
        details: Optional[Any] = None,
        status_code: Optional[int] = None,
        user_message: Optional[str] = None,
        recoverable: Optional[bool] = None
    ):
        super().__init__(message or self.user_message)
        self.details = details
        self.error_id = str(uuid.uuid4())[:8].upper()
        self.timestamp = datetime.now().isoformat()
        if status_code:
            self.status_code = status_code
        if user_message:
            self.user_message = user_message
        if recoverable is not None:
            self.recoverable = recoverable

    def to_dict(self, include_details: bool = False) -> Dict[str, Any]:
        """Convert exception to JSON-serializable dict for API responses"""
        result = {
            "success": False,
            "error_type": self.__class__.__name__,
            "message": self.user_message,
            "error_id": self.error_id,
            "recoverable": self.recoverable,
            "support_code": f"RF-{self.error_id}"
        }
        if include_details and self.details:
            result["details"] = self.details if isinstance(self.details, (dict, list, str)) else str(self.details)
        return result

    def log(self, level: str = "error"):
        """Log the exception with full context"""
        log_func = getattr(logger, level, logger.error)
        log_func(
            f"[{self.error_id}] {self.__class__.__name__}: {str(self)}",
            extra={
                "error_id": self.error_id,
                "error_type": self.__class__.__name__,
                "details": self.details,
                "timestamp": self.timestamp
            }
        )

# =============================================================================
# DECORATORS
# =============================================================================

def route_error_handler(f):
    """
    Decorator for Flask routes to handle exceptions consistently.

    Usage:
        @app.route("/api/generate")
        @route_error_handler
        def generate():
            ...
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from flask import jsonify, request
        try:
            return f(*args, **kwargs)
        except RootingFutureError as e:
            e.log()
            return jsonify(e.to_dict()), e.status_code
        except Exception as e:
            wrapped = handle_exception(e)
            wrapped.log()
            logger.exception(f"Unhandled exception in {f.__name__}")
            return jsonify(wrapped.to_dict()), wrapped.status_code
    return decorated_function


def safe_operation(
    default_return: Any = None,
    error_class: type = None,
    log_level: str = "error",
    reraise: bool = False
):
    """
    Decorator for wrapping operations that may fail.

    Usage:
        @safe_operation(default_return={}, error_class=DatabaseError)
        def fetch_plan(plan_id):
            ...

    Args:
        default_return: Value to return on failure (if not reraising)
        error_class: Exception class to raise (wraps generic exceptions)
        log_level: Logging level for errors
        reraise: If True, raise the exception after logging
    """
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            try:
                return f(*args, **kwargs)
            except RootingFutureError:
                if reraise:
                    raise
                return default_return
            except Exception as e:
                if error_class:
                    wrapped = error_class(message=str(e), details={"function": f.__name__, "args": str(args)[:200]})
                else:
                    wrapped = handle_exception(e)
                wrapped.log(log_level)
                if reraise:
                    raise wrapped from e
                return default_return
        return wrapper
    return decorator

# =============================================================================
# SPECIFIC EXCEPTION CLASSES
# =============================================================================

# --- AI & Generation Errors ---

class GeminiAPIError(RootingFutureError):
    """Gemini API failures (rate limits, timeouts, model errors)"""
    user_message = "Il servizio AI (Gemini) è temporaneamente non disponibile. Riprova tra qualche minuto."
    status_code = 503
    recoverable = True


class GeminiRateLimitError(GeminiAPIError):
    """Specific: Rate limit exceeded"""
    user_message = "Limite richieste AI raggiunto. Attendi 1-2 minuti e riprova."
    status_code = 429


class GeminiTimeoutError(GeminiAPIError):
    """Specific: Request timeout"""
    user_message = "La richiesta AI ha impiegato troppo tempo. Riprova con meno dati o più tardi."
    status_code = 504


class GenerationError(RootingFutureError):
    """Plan generation failures (orchestrator, agents)"""
    user_message = "Errore durante la generazione del piano strategico. I dati parziali potrebbero essere stati salvati."
    status_code = 500
    recoverable = True


class AgentError(GenerationError):
    """Specific agent failure during generation"""
    user_message = "Un componente della generazione ha fallito. Il piano potrebbe essere incompleto."
    status_code = 500


# --- Export Errors ---

class ExportError(RootingFutureError):
    """Export generation failures (PDF, DOCX, ZIP)"""
    user_message = "Errore durante la creazione del documento. Puoi riprovare o usare un formato alternativo."
    status_code = 500
    recoverable = True


class PDFExportError(ExportError):
    """PDF-specific export failure"""
    user_message = "Impossibile generare il PDF. Prova a scaricare il formato DOCX come alternativa."


class DOCXExportError(ExportError):
    """DOCX-specific export failure"""
    user_message = "Impossibile generare il documento Word."


# --- Data & Storage Errors ---

class DatabaseError(RootingFutureError):
    """Database operations failures (SQLite locks, corruption)"""
    user_message = "Errore nel salvataggio dati. Riprova tra qualche secondo."
    status_code = 500
    recoverable = True


class DatabaseLockError(DatabaseError):
    """Database locked by concurrent access"""
    user_message = "Database temporaneamente occupato. Riprova tra qualche secondo."
    status_code = 503


class PlanNotFoundError(RootingFutureError):
    """Requested plan does not exist"""
    user_message = "Il piano strategico richiesto non esiste o è stato eliminato."
    status_code = 404
    recoverable = False


class PlanAccessDeniedError(RootingFutureError):
    """User doesn't have permission to access plan"""
    user_message = "Non hai i permessi per accedere a questo piano strategico."
    status_code = 403
    recoverable = False


# --- Input & Validation Errors ---

class ValidationError(RootingFutureError):
    """Input validation failures"""
    user_message = "I dati inseriti non sono validi. Controlla i campi evidenziati."
    status_code = 400
    recoverable = True


class StakeholderParsingError(RootingFutureError):
    """DOCX parsing failures"""
    user_message = "Impossibile leggere il file caricato. Assicurati che sia un documento DOCX valido e non protetto."
    status_code = 400
    recoverable = True


class FileUploadError(RootingFutureError):
    """File upload failures (size, format, corruption)"""
    user_message = "Errore nel caricamento del file. Verifica che sia un file valido (DOCX, max 10MB)."
    status_code = 400
    recoverable = True


class FileTooLargeError(FileUploadError):
    """File exceeds size limit"""
    user_message = "Il file è troppo grande. Dimensione massima consentita: 10MB."
    status_code = 413


class InvalidFileFormatError(FileUploadError):
    """Unsupported file format"""
    user_message = "Formato file non supportato. Usa file DOCX o ZIP."
    status_code = 415


# --- External Services Errors ---

class ResearchError(RootingFutureError):
    """Web research failures (Serper/Tavily APIs)"""
    user_message = "Ricerca web non disponibile. Il piano verrà generato con i dati interni."
    status_code = 200  # Non-critical, can proceed
    recoverable = True


class ExternalServiceError(RootingFutureError):
    """Generic external service failure"""
    user_message = "Un servizio esterno non è disponibile. Alcune funzionalità potrebbero essere limitate."
    status_code = 503
    recoverable = True


# --- Auth & Permission Errors ---

class AuthenticationError(RootingFutureError):
    """Login failures"""
    user_message = "Credenziali non valide o sessione scaduta. Effettua nuovamente l'accesso."
    status_code = 401
    recoverable = True


class AuthorizationError(RootingFutureError):
    """Permission failures"""
    user_message = "Non hai i permessi per eseguire questa operazione."
    status_code = 403
    recoverable = False


class InsufficientCreditsError(RootingFutureError):
    """User has no credits left"""
    user_message = "Crediti insufficienti per generare un nuovo piano. Contatta l'amministratore."
    status_code = 402
    recoverable = False


# --- Sharing Errors ---

class ShareError(RootingFutureError):
    """Public sharing failures"""
    user_message = "Errore nella condivisione del piano."
    status_code = 500


class ShareNotFoundError(ShareError):
    """Share link not found or expired"""
    user_message = "Il link di condivisione non è valido o è scaduto."
    status_code = 404
    recoverable = False


class SharePasswordError(ShareError):
    """Incorrect share password"""
    user_message = "Password non corretta per accedere al piano condiviso."
    status_code = 401
    recoverable = True

# =============================================================================
# EXCEPTION MAPPING & UTILITIES
# =============================================================================

def handle_exception(e: Exception, context: str = None) -> RootingFutureError:
    """
    Wraps generic exceptions into appropriate RootingFutureError subclasses.

    Args:
        e: The original exception
        context: Optional context string (e.g., "pdf_export", "gemini_call")

    Returns:
        A RootingFutureError instance with user-friendly message
    """
    if isinstance(e, RootingFutureError):
        return e

    error_str = str(e).lower()
    error_type = type(e).__name__.lower()
    details = {
        "raw_error": str(e),
        "error_type": type(e).__name__,
        "context": context
    }

    # --- Pydantic Validation Errors ---
    try:
        from pydantic import ValidationError as PydanticValidationError
        if isinstance(e, PydanticValidationError):
            errors = e.errors()
            field_errors = [{"field": ".".join(str(x) for x in err["loc"]), "message": err["msg"]} for err in errors]
            return ValidationError(
                message=str(e),
                details={"fields": field_errors},
                user_message=f"Dati non validi: {field_errors[0]['message']}" if field_errors else "Dati non validi."
            )
    except ImportError:
        pass

    # --- Gemini / AI Errors ---
    if any(x in error_str for x in ["api_key", "invalid_api_key", "api key"]):
        return GeminiAPIError(
            message=str(e),
            details=details,
            user_message="Chiave API Gemini non valida o mancante. Controlla la configurazione."
        )

    if any(x in error_str for x in ["quota", "rate_limit", "rate limit", "resource_exhausted", "429"]):
        return GeminiRateLimitError(message=str(e), details=details)

    if any(x in error_str for x in ["timeout", "deadline_exceeded", "timed out"]):
        return GeminiTimeoutError(message=str(e), details=details)

    if "gemini" in error_str or "google.generativeai" in error_str:
        return GeminiAPIError(message=str(e), details=details)

    # --- Database Errors ---
    if "database is locked" in error_str:
        return DatabaseLockError(message=str(e), details=details)

    if any(x in error_str for x in ["sqlite", "database", "disk i/o", "no such table"]):
        return DatabaseError(message=str(e), details=details)

    # --- Export Errors ---
    if any(x in error_str for x in ["weasyprint", "playwright", "chromium", "pdf"]):
        return PDFExportError(message=str(e), details=details)

    if any(x in error_str for x in ["wkhtmltopdf"]):
        return PDFExportError(message=str(e), details=details)

    if "docx" in error_str or "python-docx" in error_str:
        return DOCXExportError(message=str(e), details=details)

    # --- File Errors ---
    if any(x in error_str for x in ["file too large", "request entity too large", "413"]):
        return FileTooLargeError(message=str(e), details=details)

    if any(x in error_str for x in ["unsupported", "invalid file", "not a zip", "bad zipfile"]):
        return InvalidFileFormatError(message=str(e), details=details)

    if any(x in error_str for x in ["filenotfound", "no such file", "file not found"]):
        return FileUploadError(
            message=str(e),
            details=details,
            user_message="File non trovato. Potrebbe essere stato eliminato."
        )

    # --- Network / External Service Errors ---
    if any(x in error_str for x in ["connection", "network", "dns", "ssl", "certificate"]):
        return ExternalServiceError(
            message=str(e),
            details=details,
            user_message="Errore di connessione. Verifica la connessione internet."
        )

    if any(x in error_str for x in ["serper", "tavily", "search api"]):
        return ResearchError(message=str(e), details=details)

    # --- Permission Errors ---
    if any(x in error_str for x in ["permission denied", "access denied", "forbidden"]):
        return AuthorizationError(message=str(e), details=details)

    # --- Generic fallback ---
    return RootingFutureError(
        message=str(e),
        details=details,
        user_message="Si è verificato un errore. Se il problema persiste, contatta il supporto."
    )


def get_user_friendly_message(e: Exception) -> str:
    """
    Returns a user-friendly message for any exception.
    Useful for displaying errors in templates.
    """
    if isinstance(e, RootingFutureError):
        return e.user_message
    wrapped = handle_exception(e)
    return wrapped.user_message


def log_exception(e: Exception, context: str = None, level: str = "error"):
    """
    Logs any exception with full context.
    Use this instead of logger.exception() for consistent formatting.
    """
    if isinstance(e, RootingFutureError):
        e.log(level)
    else:
        wrapped = handle_exception(e, context)
        wrapped.log(level)
        logger.debug(f"Stack trace for {wrapped.error_id}:", exc_info=True)