"""
Rooting Future — AI Provider Interfaces
Interfacce astratte per i provider AI. Nessuna dipendenza da provider specifici.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any


class EmbeddingProvider(ABC):
    """Genera vettori embedding da testi."""

    @abstractmethod
    def embed_text(self, text: str) -> Optional[List[float]]:
        """Un testo → un vettore (None se errore)."""
        ...

    @abstractmethod
    def embed_batch(self, texts: List[str]) -> List[Optional[List[float]]]:
        """N testi → N vettori (None per gli errori individuali)."""
        ...


class GenerationProvider(ABC):
    """Genera testo da prompt."""

    @abstractmethod
    def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        temperature: float = 0.7,
        max_tokens: int = 8192,
    ) -> str:
        """Prompt → testo generato. Solleva eccezione se non disponibile."""
        ...

    @abstractmethod
    def generate_structured(
        self,
        prompt: str,
        system_prompt: str = "",
        temperature: float = 0.7,
        max_tokens: int = 8192,
    ) -> Dict[str, Any]:
        """Prompt → dict JSON (per structured_agent.py)."""
        ...

    @property
    @abstractmethod
    def available(self) -> bool:
        """True se il provider è pronto."""
        ...


class VectorStoreProvider(ABC):
    """Archivia e cerca documenti tramite vettori."""

    @abstractmethod
    def add_document(
        self,
        doc_id: str,
        text: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        ...

    @abstractmethod
    def add_documents(self, docs: List[Dict[str, Any]]) -> None:
        """docs: lista di {id, text, metadata}."""
        ...

    @abstractmethod
    def search(
        self,
        query: str,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Restituisce lista di {id, text, score, metadata}."""
        ...

    @abstractmethod
    def delete_document(self, doc_id: str) -> None:
        ...

    @abstractmethod
    def count(self) -> int:
        """Numero di documenti nel vettore store."""
        ...
