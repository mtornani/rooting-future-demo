"""
Rooting Future — Provider Factory
Crea i provider giusti in base alle env vars.

Logica:
  embedding:    LOCAL_RAG=1  → LocalEmbeddingProvider
                altrimenti   → GeminiEmbeddingProvider

  generation:   OLLAMA_BASE_URL presente → OllamaGenerationProvider (con fallback Gemini)
                altrimenti               → GeminiGenerationProvider

  vector_store: LOCAL_RAG=1  → ChromaVectorStore
                altrimenti   → None (il codice esistente usa SQLite + pickle)
"""

import logging
import os
from typing import Optional, Tuple

from .interfaces import EmbeddingProvider, GenerationProvider, VectorStoreProvider

logger = logging.getLogger(__name__)


def create_embedding_provider() -> EmbeddingProvider:
    """Crea e restituisce l'EmbeddingProvider corretto."""
    local_rag = os.environ.get("LOCAL_RAG", "0").strip() == "1"

    if local_rag:
        from .local_provider import LocalEmbeddingProvider
        logger.info("ProviderFactory: EmbeddingProvider → LocalEmbeddingProvider")
        return LocalEmbeddingProvider()
    else:
        from .gemini_provider import GeminiEmbeddingProvider
        logger.info("ProviderFactory: EmbeddingProvider → GeminiEmbeddingProvider")
        return GeminiEmbeddingProvider()


def create_generation_provider() -> GenerationProvider:
    """Crea e restituisce il GenerationProvider corretto."""
    ollama_url = os.environ.get("OLLAMA_BASE_URL", "").strip()

    if ollama_url:
        from .ollama_provider import OllamaGenerationProvider
        logger.info(f"ProviderFactory: GenerationProvider → OllamaGenerationProvider (url={ollama_url})")
        return OllamaGenerationProvider(base_url=ollama_url)
    else:
        from .gemini_provider import GeminiGenerationProvider
        logger.info("ProviderFactory: GenerationProvider → GeminiGenerationProvider")
        return GeminiGenerationProvider()


def create_vector_store(
    embedding_provider: Optional[EmbeddingProvider] = None,
) -> Optional[VectorStoreProvider]:
    """
    Crea e restituisce il VectorStoreProvider corretto.
    Restituisce None se LOCAL_RAG non è attivo (mantieni SQLite + pickle).
    """
    local_rag = os.environ.get("LOCAL_RAG", "0").strip() == "1"

    if not local_rag:
        logger.info("ProviderFactory: VectorStore → SQLite + pickle (default esistente)")
        return None

    if embedding_provider is None:
        embedding_provider = create_embedding_provider()

    from .chromadb_store import ChromaVectorStore
    logger.info("ProviderFactory: VectorStore → ChromaVectorStore")
    return ChromaVectorStore(embedding_provider=embedding_provider)


def create_all_providers() -> Tuple[EmbeddingProvider, GenerationProvider, Optional[VectorStoreProvider]]:
    """
    Crea tutti i provider in un'unica chiamata.
    Restituisce (embedding_provider, generation_provider, vector_store).
    vector_store è None se LOCAL_RAG=0.
    """
    embedding = create_embedding_provider()
    generation = create_generation_provider()
    vector_store = create_vector_store(embedding_provider=embedding)
    return embedding, generation, vector_store
