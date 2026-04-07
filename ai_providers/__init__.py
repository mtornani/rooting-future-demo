"""
Rooting Future — AI Providers Package
Adapter layer per switchare tra Gemini API e Ollama (Gemma 4) via env vars.

Uso:
    from ai_providers.factory import create_all_providers
    embedding, generation, vector_store = create_all_providers()

Env vars chiave:
    LOCAL_RAG=1          → embedding locale + ChromaDB
    OLLAMA_BASE_URL=...  → generazione via Ollama
"""

from .interfaces import EmbeddingProvider, GenerationProvider, VectorStoreProvider
from .factory import create_embedding_provider, create_generation_provider, create_vector_store, create_all_providers

__all__ = [
    "EmbeddingProvider",
    "GenerationProvider",
    "VectorStoreProvider",
    "create_embedding_provider",
    "create_generation_provider",
    "create_vector_store",
    "create_all_providers",
]
