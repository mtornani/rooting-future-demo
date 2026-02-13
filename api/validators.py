"""
Input Validation Layer - Rooting Future Strategy Engine v6.0
Uses Pydantic for strict schema validation of API requests.

STAB-003: Complete input validation for all endpoints.
"""

import re
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator
from datetime import datetime

# =============================================================================
# CONSTANTS
# =============================================================================

MAX_FILE_SIZE_MB = 10
ALLOWED_FILE_EXTENSIONS = {'.docx', '.zip'}
ALLOWED_CATEGORIES = [
    'Serie A', 'Serie B', 'Serie C', 'Serie D',
    'Eccellenza', 'Promozione', 'Prima Categoria', 'Seconda Categoria', 'Terza Categoria',
    'Juniores', 'Allievi', 'Giovanissimi', 'Pulcini',
    'Femminile Serie A', 'Femminile Serie B', 'Femminile Serie C',
    'Altro'
]
HEX_COLOR_PATTERN = re.compile(r'^#[0-9A-Fa-f]{6}$')


# =============================================================================
# PLAN GENERATION
# =============================================================================

class GeneratePlanRequest(BaseModel):
    """Validation for plan generation endpoint."""
    club_name: str = Field(..., min_length=2, max_length=100)
    city: str = Field(default="Sconosciuta", max_length=100)
    region: str = Field(default="Italia", max_length=100)
    category: str = Field(..., min_length=2, max_length=50)
    foundation_year: Optional[int] = Field(None, ge=1800, le=datetime.now().year)
    competitors: List[str] = Field(default_factory=list, max_length=10)
    enable_research: bool = True
    additional_data: Dict[str, Any] = Field(default_factory=dict)

    @field_validator('club_name')
    @classmethod
    def club_name_must_not_be_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError('Il nome del club non può essere vuoto')
        # Remove potentially dangerous characters
        cleaned = re.sub(r'[<>"\']', '', v.strip())
        return cleaned

    @field_validator('category')
    @classmethod
    def validate_category(cls, v: str) -> str:
        # Allow any category but sanitize
        return v.strip()[:50]

    @field_validator('competitors')
    @classmethod
    def validate_competitors(cls, v: List[str]) -> List[str]:
        # Limit to 10 competitors, sanitize each
        return [re.sub(r'[<>"\']', '', c.strip())[:100] for c in v[:10]]


# =============================================================================
# SECTION EDITING
# =============================================================================

class SaveSectionRequest(BaseModel):
    """Validation for saving edited section content."""
    plan_id: str = Field(..., min_length=10, max_length=50)
    section_key: str = Field(..., min_length=2, max_length=50)
    content: str = Field(..., min_length=1, max_length=50000)

    @field_validator('plan_id')
    @classmethod
    def validate_plan_id(cls, v: str) -> str:
        # Plan IDs follow pattern: plan_XXXXXX_YYYYMMDDHHMMSS
        if not re.match(r'^plan_[a-f0-9]{6}_\d{14}$', v):
            raise ValueError('ID piano non valido')
        return v


class RegenerateSectionRequest(BaseModel):
    """Validation for section regeneration."""
    plan_id: str = Field(..., min_length=10, max_length=50)
    section_id: str = Field(..., min_length=2, max_length=50)
    context: Optional[str] = Field(default="", max_length=1000)

    @field_validator('plan_id')
    @classmethod
    def validate_plan_id(cls, v: str) -> str:
        if not re.match(r'^plan_[a-f0-9]{6}_\d{14}$', v):
            raise ValueError('ID piano non valido')
        return v


# =============================================================================
# SHARING
# =============================================================================

class SharePlanRequest(BaseModel):
    """Validation for public plan sharing."""
    plan_id: str = Field(..., min_length=10, max_length=50)
    expires_in_days: int = Field(default=30, ge=1, le=365)
    password: Optional[str] = Field(default=None, min_length=4, max_length=100)
    allow_download: bool = True

    @field_validator('plan_id')
    @classmethod
    def validate_plan_id(cls, v: str) -> str:
        if not re.match(r'^plan_[a-f0-9]{6}_\d{14}$', v):
            raise ValueError('ID piano non valido')
        return v

    @field_validator('password')
    @classmethod
    def validate_password(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and len(v) < 4:
            raise ValueError('La password deve avere almeno 4 caratteri')
        return v


# =============================================================================
# FILE UPLOAD
# =============================================================================

class FileUploadRequest(BaseModel):
    """Validation for file uploads (metadata only - actual file validation in route)."""
    club_name: str = Field(..., min_length=2, max_length=100)
    project_id: Optional[str] = Field(default=None, max_length=50)
    request_mode: str = Field(default="production", pattern=r'^(production|test|debug)$')

    @field_validator('club_name')
    @classmethod
    def validate_club_name(cls, v: str) -> str:
        cleaned = re.sub(r'[<>"\']', '', v.strip())
        if not cleaned:
            raise ValueError('Il nome del club non può essere vuoto')
        return cleaned


class HardDataRequest(BaseModel):
    """Validation for hard data (colors, financial info)."""
    primary_color: Optional[str] = Field(default=None, max_length=7)
    secondary_color: Optional[str] = Field(default=None, max_length=7)
    budget_annuale: Optional[float] = Field(default=None, ge=0, le=1_000_000_000)
    numero_tesserati: Optional[int] = Field(default=None, ge=0, le=10000)
    anno_fondazione: Optional[int] = Field(default=None, ge=1800, le=datetime.now().year)

    @field_validator('primary_color', 'secondary_color')
    @classmethod
    def validate_hex_color(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if not HEX_COLOR_PATTERN.match(v):
            raise ValueError('Colore non valido (formato: #RRGGBB)')
        return v.upper()


# =============================================================================
# USER MANAGEMENT
# =============================================================================

class CreateUserRequest(BaseModel):
    """Validation for user creation (admin only)."""
    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., min_length=5, max_length=100)
    password: str = Field(..., min_length=8, max_length=100)
    role: str = Field(default="user", pattern=r'^(super_admin|admin|user|viewer)$')

    @field_validator('username')
    @classmethod
    def validate_username(cls, v: str) -> str:
        if not re.match(r'^[a-zA-Z0-9_.-]+$', v):
            raise ValueError('Username può contenere solo lettere, numeri, _ . -')
        return v.lower()

    @field_validator('email')
    @classmethod
    def validate_email(cls, v: str) -> str:
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', v):
            raise ValueError('Email non valida')
        return v.lower()

    @field_validator('password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError('La password deve avere almeno 8 caratteri')
        if not any(c.isupper() for c in v):
            raise ValueError('La password deve contenere almeno una lettera maiuscola')
        if not any(c.isdigit() for c in v):
            raise ValueError('La password deve contenere almeno un numero')
        return v


class AssignPlanRequest(BaseModel):
    """Validation for plan assignment."""
    plan_id: str = Field(..., min_length=10, max_length=50)
    user_id: int = Field(..., ge=1)
    can_edit: bool = Field(default=False)

    @field_validator('plan_id')
    @classmethod
    def validate_plan_id(cls, v: str) -> str:
        if not re.match(r'^plan_[a-f0-9]{6}_\d{14}$', v):
            raise ValueError('ID piano non valido')
        return v


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def validate_file_upload(filename: str, file_size: int) -> tuple[bool, str]:
    """
    Validate uploaded file.

    Args:
        filename: Name of the uploaded file
        file_size: Size in bytes

    Returns:
        Tuple of (is_valid, error_message)
    """
    from pathlib import Path

    if not filename:
        return False, "Nome file mancante"

    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_FILE_EXTENSIONS:
        return False, f"Formato non supportato. Usa: {', '.join(ALLOWED_FILE_EXTENSIONS)}"

    max_size_bytes = MAX_FILE_SIZE_MB * 1024 * 1024
    if file_size > max_size_bytes:
        return False, f"File troppo grande. Massimo: {MAX_FILE_SIZE_MB}MB"

    # Check for suspicious filename patterns
    if '..' in filename or '/' in filename or '\\' in filename:
        return False, "Nome file non valido"

    return True, ""


def sanitize_input(text: str, max_length: int = 1000) -> str:
    """
    Sanitize user input text.

    Args:
        text: Input text to sanitize
        max_length: Maximum allowed length

    Returns:
        Sanitized text
    """
    if not text:
        return ""

    # Remove HTML tags and dangerous characters
    cleaned = re.sub(r'<[^>]+>', '', text)
    cleaned = re.sub(r'[<>"\']', '', cleaned)

    # Truncate if needed
    return cleaned[:max_length].strip()
