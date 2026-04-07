"""
Rooting Future — ChromaDB Vector Store Provider
VectorStoreProvider via ChromaDB persistente.
Riceve un EmbeddingProvider all'init — non hardcoda il modello.
"""

import logging
import os
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

from .interfaces import EmbeddingProvider, VectorStoreProvider

logger = logging.getLogger(__name__)

_DEFAULT_CHROMA_PATH = "knowledge_base/chromadb/"
_CHROMA_COLLECTION_NAME = "rooting_future_knowledge"


class ChromaVectorStore(VectorStoreProvider):
    """
    VectorStoreProvider con ChromaDB persistente.

    Configurazione env vars:
      CHROMA_DB_PATH  — Path per il DB (default: knowledge_base/chromadb/)
                        Su HuggingFace Spaces usare /data/chromadb/

    Il provider di embedding viene passato all'init.
    ChromaDB gestisce la persistenza: niente pickle.
    """

    def __init__(
        self,
        embedding_provider: EmbeddingProvider,
        db_path: Optional[str] = None,
        collection_name: str = _CHROMA_COLLECTION_NAME,
    ):
        self._embedding_provider = embedding_provider
        self._db_path = db_path or os.environ.get("CHROMA_DB_PATH", _DEFAULT_CHROMA_PATH)
        self._collection_name = collection_name
        self._client = None
        self._collection = None
        self._available = False

        try:
            import chromadb
            Path(self._db_path).mkdir(parents=True, exist_ok=True)
            self._client = chromadb.PersistentClient(path=self._db_path)
            self._collection = self._client.get_or_create_collection(
                name=self._collection_name,
                metadata={"hnsw:space": "cosine"},
            )
            self._available = True
            logger.info(
                f"ChromaVectorStore: pronto (path={self._db_path}, "
                f"docs={self._collection.count()})"
            )
        except ImportError:
            logger.warning("ChromaVectorStore: chromadb non installato. pip install chromadb")
        except Exception as e:
            logger.error(f"ChromaVectorStore init error: {e}")

    @property
    def available(self) -> bool:
        return self._available

    def _embed(self, text: str) -> Optional[List[float]]:
        return self._embedding_provider.embed_text(text)

    def add_document(
        self,
        doc_id: str,
        text: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        if not self._available or self._collection is None:
            return
        embedding = self._embed(text)
        if embedding is None:
            logger.warning(f"ChromaVectorStore: embedding fallito per doc_id={doc_id}")
            return
        try:
            self._collection.upsert(
                ids=[doc_id],
                embeddings=[embedding],
                documents=[text],
                metadatas=[metadata or {}],
            )
        except Exception as e:
            logger.error(f"ChromaVectorStore.add_document error: {e}")

    def add_documents(self, docs: List[Dict[str, Any]]) -> None:
        """docs: lista di {id, text, metadata (opzionale)}."""
        if not self._available or self._collection is None:
            return

        ids, texts, metadatas = [], [], []
        for doc in docs:
            ids.append(doc["id"])
            texts.append(doc["text"])
            metadatas.append(doc.get("metadata") or {})

        embeddings = self._embedding_provider.embed_batch(texts)
        # Filtra i docs con embedding valido
        valid = [
            (i, t, m, e)
            for i, t, m, e in zip(ids, texts, metadatas, embeddings)
            if e is not None
        ]
        if not valid:
            return

        v_ids, v_texts, v_metas, v_embs = zip(*valid)
        try:
            self._collection.upsert(
                ids=list(v_ids),
                embeddings=list(v_embs),
                documents=list(v_texts),
                metadatas=list(v_metas),
            )
            logger.info(f"ChromaVectorStore: aggiunti {len(v_ids)}/{len(docs)} documenti")
        except Exception as e:
            logger.error(f"ChromaVectorStore.add_documents error: {e}")

    def search(
        self,
        query: str,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Restituisce lista di {id, text, score, metadata}."""
        if not self._available or self._collection is None:
            return []

        query_embedding = self._embedding_provider.embed_text(query)
        if query_embedding is None:
            return []

        try:
            where = filters if filters else None
            results = self._collection.query(
                query_embeddings=[query_embedding],
                n_results=min(top_k, max(self._collection.count(), 1)),
                where=where,
                include=["documents", "distances", "metadatas"],
            )
            output = []
            for i, doc_id in enumerate(results["ids"][0]):
                output.append({
                    "id": doc_id,
                    "text": results["documents"][0][i],
                    "score": 1.0 - results["distances"][0][i],  # cosine: converti distanza → similarità
                    "metadata": results["metadatas"][0][i],
                })
            return output
        except Exception as e:
            logger.error(f"ChromaVectorStore.search error: {e}")
            return []

    def delete_document(self, doc_id: str) -> None:
        if not self._available or self._collection is None:
            return
        try:
            self._collection.delete(ids=[doc_id])
        except Exception as e:
            logger.error(f"ChromaVectorStore.delete_document error: {e}")

    def count(self) -> int:
        if not self._available or self._collection is None:
            return 0
        try:
            return self._collection.count()
        except Exception:
            return 0

    def migrate_from_sqlite(self, sqlite_path: str) -> int:
        """
        Migra documenti da knowledge.db (SQLite) a ChromaDB.
        Restituisce il numero di documenti migrati.
        Sicuro da eseguire più volte (upsert).
        """
        if not self._available:
            logger.error("ChromaVectorStore: non disponibile per migrazione")
            return 0

        db_path = Path(sqlite_path)
        if not db_path.exists():
            logger.warning(f"migrate_from_sqlite: file non trovato: {sqlite_path}")
            return 0

        migrated = 0
        try:
            with sqlite3.connect(str(db_path)) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    "SELECT id, content, doc_type, category, section_type, metadata "
                    "FROM documents"
                )
                rows = cursor.fetchall()

            batch = []
            for row in rows:
                meta = {}
                for col in ["doc_type", "category", "section_type"]:
                    if row[col]:
                        meta[col] = row[col]
                if row["metadata"]:
                    try:
                        import json
                        extra = json.loads(row["metadata"])
                        meta.update(extra)
                    except Exception:
                        pass
                batch.append({
                    "id": str(row["id"]),
                    "text": row["content"] or "",
                    "metadata": meta,
                })

                if len(batch) >= 50:
                    self.add_documents(batch)
                    migrated += len(batch)
                    batch = []

            if batch:
                self.add_documents(batch)
                migrated += len(batch)

            logger.info(f"migrate_from_sqlite: migrati {migrated} documenti da {sqlite_path}")
        except Exception as e:
            logger.error(f"migrate_from_sqlite error: {e}")

        return migrated
