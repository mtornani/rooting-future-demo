"""
Rooting Future Strategy Engine v5.4

Sistema AI Multi-Agente per generare piani strategici professionali
per società calcistiche italiane.

Collaborazione:
- Mirko (technical co-founder): architettura AI
- Nardoni (sports consultant): expertise consulenziale e metodologia STW
"""

__version__ = "5.4.0"
__author__ = "Mirko & Nardoni"

from .config import (
    GEMINI_API_KEY,
    SERPER_API_KEY,
    MODEL_CONFIG,
    BENCHMARKS,
    TRUSTED_SOURCES,
)

from .agents import (
    MultiAgentOrchestrator,
    StrategicAgent,
    AgentRole,
)

from .web_research import (
    WebResearcher,
    ResearchAggregator,
)

from .data_sourcing import (
    DataSourcer,
    SourcedContentGenerator,
    SourceConfidence,
    SourcedData,
)

from .knowledge_store import (
    KnowledgeManager,
    SQLiteKnowledgeStore,
    GeminiKnowledgeRAG,
)

from .export_docx import (
    ProfessionalDocxExporter,
    BatchDocxExporter,
)

from .export_html import (
    ChunkedHTMLExporter,
)

from .post_production_editor import (
    PostProductionEditor,
    BatchReviewManager,
    PlanStatus,
    SectionStatus,
)

__all__ = [
    # Config
    "GEMINI_API_KEY",
    "SERPER_API_KEY",
    "MODEL_CONFIG",
    "BENCHMARKS",
    "TRUSTED_SOURCES",

    # Agents
    "MultiAgentOrchestrator",
    "StrategicAgent",
    "AgentRole",

    # Research
    "WebResearcher",
    "ResearchAggregator",

    # Sourcing
    "DataSourcer",
    "SourcedContentGenerator",
    "SourceConfidence",
    "SourcedData",

    # Knowledge
    "KnowledgeManager",
    "SQLiteKnowledgeStore",
    "GeminiKnowledgeRAG",

    # Export
    "ProfessionalDocxExporter",
    "BatchDocxExporter",
    "ChunkedHTMLExporter",

    # Editor
    "PostProductionEditor",
    "BatchReviewManager",
    "PlanStatus",
    "SectionStatus",
]
