"""
Structured Logging Configuration - Rooting Future Strategy Engine v6.0

STAB-004: JSON structured logs for debugging and monitoring.

Features:
- JSON output for easy parsing and log aggregation
- Contextual logging with automatic metadata
- Performance timing helpers
- Error tracking with support codes
- Console output with colors (dev) vs JSON (prod)

Usage:
    from utils.logging_config import get_logger, log_event, timed_operation

    logger = get_logger(__name__)
    logger.info("plan_generated", plan_id=plan_id, duration=12.5)

    # Or use convenience functions
    log_event("plan_generated", plan_id=plan_id)

    # Timed operations
    with timed_operation("pdf_export", plan_id=plan_id):
        generate_pdf(...)
"""

import os
import sys
import time
import logging
from datetime import datetime
from typing import Any, Optional
from contextlib import contextmanager
from functools import wraps

import structlog
from structlog.stdlib import BoundLogger

# =============================================================================
# CONFIGURATION
# =============================================================================

# Environment: "development" or "production"
ENV = os.environ.get("ROOTING_ENV", "development")
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()
LOG_FILE = os.environ.get("LOG_FILE", "logs/rooting_future.log")

# Ensure logs directory exists
LOG_DIR = os.path.dirname(LOG_FILE) if LOG_FILE else "logs"
if LOG_DIR:
    os.makedirs(LOG_DIR, exist_ok=True)


# =============================================================================
# PROCESSORS
# =============================================================================

def add_app_context(logger, method_name, event_dict):
    """Add application context to every log entry."""
    event_dict["app"] = "rooting_future"
    event_dict["version"] = "6.0"
    event_dict["env"] = ENV
    return event_dict


def add_timestamp(logger, method_name, event_dict):
    """Add ISO timestamp to every log entry."""
    event_dict["timestamp"] = datetime.now().isoformat()
    return event_dict


def censor_sensitive_data(logger, method_name, event_dict):
    """Remove or mask sensitive data from logs."""
    sensitive_keys = {"password", "api_key", "token", "secret", "credential"}

    for key in list(event_dict.keys()):
        if any(s in key.lower() for s in sensitive_keys):
            event_dict[key] = "***REDACTED***"

    return event_dict


# =============================================================================
# STRUCTLOG CONFIGURATION
# =============================================================================

def configure_structlog():
    """Configure structlog with appropriate processors for the environment."""

    # Common processors
    shared_processors = [
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        add_app_context,
        censor_sensitive_data,
    ]

    if ENV == "development":
        # Development: colored console output
        processors = shared_processors + [
            structlog.dev.ConsoleRenderer(colors=True)
        ]
    else:
        # Production: JSON output
        processors = shared_processors + [
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer()
        ]

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, LOG_LEVEL, logging.INFO),
    )

    # Add file handler if specified
    if LOG_FILE:
        file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(logging.Formatter("%(message)s"))
        logging.getLogger().addHandler(file_handler)


# Initialize on import
configure_structlog()


# =============================================================================
# LOGGER FACTORY
# =============================================================================

def get_logger(name: str = None) -> BoundLogger:
    """
    Get a structured logger instance.

    Args:
        name: Logger name (usually __name__)

    Returns:
        Structured logger instance

    Usage:
        logger = get_logger(__name__)
        logger.info("event_name", key="value")
    """
    return structlog.get_logger(name or "rooting_future")


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

# Global logger for convenience functions
_logger = get_logger("rooting_future")


def log_event(
    event: str,
    level: str = "info",
    **kwargs: Any
) -> None:
    """
    Log a structured event.

    Args:
        event: Event name (e.g., "plan_generated", "pdf_export_started")
        level: Log level (debug, info, warning, error)
        **kwargs: Additional context data

    Usage:
        log_event("plan_generated", plan_id="plan_123", duration=12.5)
    """
    log_func = getattr(_logger, level, _logger.info)
    log_func(event, **kwargs)


def log_error(
    event: str,
    error: Exception = None,
    error_id: str = None,
    **kwargs: Any
) -> None:
    """
    Log an error event with exception details.

    Args:
        event: Error event name
        error: Exception object (optional)
        error_id: Support code (optional)
        **kwargs: Additional context

    Usage:
        log_error("pdf_generation_failed", error=e, plan_id=plan_id)
    """
    if error:
        kwargs["error_type"] = type(error).__name__
        kwargs["error_message"] = str(error)
    if error_id:
        kwargs["error_id"] = error_id
        kwargs["support_code"] = f"RF-{error_id}"

    _logger.error(event, **kwargs, exc_info=bool(error))


def log_api_request(
    endpoint: str,
    method: str,
    user_id: int = None,
    **kwargs: Any
) -> None:
    """
    Log an API request.

    Args:
        endpoint: API endpoint path
        method: HTTP method
        user_id: User ID if authenticated
        **kwargs: Additional context
    """
    _logger.info(
        "api_request",
        endpoint=endpoint,
        method=method,
        user_id=user_id,
        **kwargs
    )


def log_api_response(
    endpoint: str,
    status_code: int,
    duration_ms: float = None,
    **kwargs: Any
) -> None:
    """
    Log an API response.

    Args:
        endpoint: API endpoint path
        status_code: HTTP status code
        duration_ms: Request duration in milliseconds
        **kwargs: Additional context
    """
    level = "info" if status_code < 400 else "warning" if status_code < 500 else "error"
    log_func = getattr(_logger, level)
    log_func(
        "api_response",
        endpoint=endpoint,
        status_code=status_code,
        duration_ms=duration_ms,
        **kwargs
    )


# =============================================================================
# TIMING HELPERS
# =============================================================================

@contextmanager
def timed_operation(operation: str, **context: Any):
    """
    Context manager for timing operations.

    Args:
        operation: Operation name for logging
        **context: Additional context to log

    Usage:
        with timed_operation("pdf_export", plan_id=plan_id):
            generate_pdf(...)

    Yields:
        dict with "start_time" that gets populated with "duration_seconds" on exit
    """
    start_time = time.time()
    timing = {"start_time": start_time}

    _logger.info(f"{operation}_started", **context)

    try:
        yield timing
        duration = time.time() - start_time
        timing["duration_seconds"] = duration
        _logger.info(
            f"{operation}_completed",
            duration_seconds=round(duration, 3),
            **context
        )
    except Exception as e:
        duration = time.time() - start_time
        timing["duration_seconds"] = duration
        _logger.error(
            f"{operation}_failed",
            duration_seconds=round(duration, 3),
            error_type=type(e).__name__,
            error_message=str(e),
            **context
        )
        raise


def timed(operation: str = None):
    """
    Decorator for timing function execution.

    Args:
        operation: Operation name (defaults to function name)

    Usage:
        @timed("plan_generation")
        def generate_plan(club_data):
            ...
    """
    def decorator(func):
        op_name = operation or func.__name__

        @wraps(func)
        def wrapper(*args, **kwargs):
            with timed_operation(op_name):
                return func(*args, **kwargs)
        return wrapper
    return decorator


# =============================================================================
# PLAN-SPECIFIC LOGGING
# =============================================================================

def log_plan_generation_started(
    plan_id: str,
    club_name: str,
    user_id: int = None,
    stakeholder_count: int = 0,
    **kwargs: Any
) -> None:
    """Log the start of plan generation."""
    _logger.info(
        "plan_generation_started",
        plan_id=plan_id,
        club_name=club_name,
        user_id=user_id,
        stakeholder_count=stakeholder_count,
        **kwargs
    )


def log_plan_generation_completed(
    plan_id: str,
    club_name: str,
    duration_seconds: float,
    agent_count: int = 6,
    sections_count: int = 0,
    **kwargs: Any
) -> None:
    """Log successful plan generation."""
    _logger.info(
        "plan_generation_completed",
        plan_id=plan_id,
        club_name=club_name,
        duration_seconds=round(duration_seconds, 2),
        agent_count=agent_count,
        sections_count=sections_count,
        **kwargs
    )


def log_agent_execution(
    agent_name: str,
    plan_id: str,
    duration_seconds: float,
    success: bool = True,
    **kwargs: Any
) -> None:
    """Log individual agent execution."""
    level = "info" if success else "warning"
    log_func = getattr(_logger, level)
    log_func(
        "agent_execution",
        agent_name=agent_name,
        plan_id=plan_id,
        duration_seconds=round(duration_seconds, 2),
        success=success,
        **kwargs
    )


def log_export_event(
    export_type: str,
    plan_id: str,
    success: bool,
    duration_seconds: float = None,
    file_size_kb: int = None,
    engine: str = None,
    **kwargs: Any
) -> None:
    """Log export events (PDF, DOCX, HTML)."""
    level = "info" if success else "error"
    log_func = getattr(_logger, level)

    data = {
        "export_type": export_type,
        "plan_id": plan_id,
        "success": success,
    }
    if duration_seconds is not None:
        data["duration_seconds"] = round(duration_seconds, 2)
    if file_size_kb is not None:
        data["file_size_kb"] = file_size_kb
    if engine:
        data["engine"] = engine

    log_func("export_event", **data, **kwargs)


def log_share_event(
    event_type: str,  # "created", "accessed", "revoked"
    plan_id: str,
    share_token: str = None,
    user_id: int = None,
    **kwargs: Any
) -> None:
    """Log sharing events."""
    _logger.info(
        f"share_{event_type}",
        plan_id=plan_id,
        share_token=share_token[:8] + "..." if share_token else None,
        user_id=user_id,
        **kwargs
    )


# =============================================================================
# EXPORT FOR CONVENIENCE
# =============================================================================

__all__ = [
    "get_logger",
    "log_event",
    "log_error",
    "log_api_request",
    "log_api_response",
    "timed_operation",
    "timed",
    "log_plan_generation_started",
    "log_plan_generation_completed",
    "log_agent_execution",
    "log_export_event",
    "log_share_event",
]
