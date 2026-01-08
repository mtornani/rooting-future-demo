"""
Rooting Future Strategy Engine v5.4
Knowledge Store - RAG con Gemini File Search

Sistema di persistenza conoscenza per:
- Piani strategici generati
- Benchmark di settore
- Template riutilizzabili
- Memoria progetti precedenti
"""

import json
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict
import logging
import sqlite3
import pickle

try:
    from google import genai
    from google.genai import types as genai_types
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False

from config import (
    GEMINI_API_KEY,
    MODEL_CONFIG,
    KNOWLEDGE_DIR,
    OUTPUT_DIR,
)

logger = logging.getLogger(__name__)


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class Document:
    """Documento nel knowledge store"""
    id: str
    title: str
    content: str
    doc_type: str  # "plan", "benchmark", "template", "research"
    metadata: Dict = field(default_factory=dict)
    created_at: str = ""
    updated_at: str = ""
    club_name: str = ""
    category: str = ""
    tags: List[str] = field(default_factory=list)

    def __post_init__(self):
        if not self.id:
            self.id = self._generate_id()
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        self.updated_at = datetime.now().isoformat()

    def _generate_id(self) -> str:
        content_hash = hashlib.md5(
            f"{self.title}{self.content[:100]}{self.created_at}".encode()
        ).hexdigest()[:12]
        return f"{self.doc_type}_{content_hash}"

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class SearchResult:
    """Risultato ricerca nel knowledge store"""
    document: Document
    score: float
    matched_chunks: List[str] = field(default_factory=list)


@dataclass
class PlanRecord:
    """Record di un piano strategico generato"""
    id: str
    club_name: str
    category: str
    region: str
    created_at: str
    status: str  # "draft", "review", "approved", "exported"
    plan_data: Dict = field(default_factory=dict)
    sources_count: int = 0
    credibility_score: float = 0.0
    export_paths: List[str] = field(default_factory=list)
    notes: str = ""
    last_edited_by: str = ""

    def to_dict(self) -> Dict:
        return asdict(self)


# =============================================================================
# SQLITE STORAGE
# =============================================================================

class SQLiteKnowledgeStore:
    """
    Storage persistente basato su SQLite.
    Per gestione 200+ piani strategici.
    """

    def __init__(self, db_path: Path = None):
        self.db_path = db_path or (KNOWLEDGE_DIR / "rooting_future.db")
        self._init_db()

    def _init_db(self):
        """Inizializza database con schema"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    content TEXT,
                    doc_type TEXT,
                    club_name TEXT,
                    category TEXT,
                    tags TEXT,
                    metadata TEXT,
                    created_at TEXT,
                    updated_at TEXT
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS plans (
                    id TEXT PRIMARY KEY,
                    club_name TEXT NOT NULL,
                    category TEXT,
                    region TEXT,
                    status TEXT DEFAULT 'draft',
                    plan_data TEXT,
                    sources_count INTEGER DEFAULT 0,
                    credibility_score REAL DEFAULT 0.0,
                    export_paths TEXT,
                    notes TEXT,
                    last_edited_by TEXT,
                    created_at TEXT,
                    updated_at TEXT
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS benchmarks (
                    id TEXT PRIMARY KEY,
                    metric TEXT NOT NULL,
                    category TEXT NOT NULL,
                    value TEXT,
                    source TEXT,
                    source_url TEXT,
                    valid_from TEXT,
                    valid_to TEXT,
                    created_at TEXT
                )
            """)

            # Indici per ricerche veloci
            conn.execute("CREATE INDEX IF NOT EXISTS idx_docs_type ON documents(doc_type)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_docs_club ON documents(club_name)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_plans_club ON plans(club_name)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_plans_status ON plans(status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_benchmarks_metric ON benchmarks(metric, category)")

            conn.commit()

    # -------------------------------------------------------------------------
    # DOCUMENTS CRUD
    # -------------------------------------------------------------------------

    def add_document(self, doc: Document) -> str:
        """Aggiunge documento al knowledge store"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO documents
                (id, title, content, doc_type, club_name, category, tags, metadata, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                doc.id,
                doc.title,
                doc.content,
                doc.doc_type,
                doc.club_name,
                doc.category,
                json.dumps(doc.tags),
                json.dumps(doc.metadata),
                doc.created_at,
                doc.updated_at,
            ))
            conn.commit()
        return doc.id

    def get_document(self, doc_id: str) -> Optional[Document]:
        """Recupera documento per ID"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM documents WHERE id = ?", (doc_id,)
            ).fetchone()

            if row:
                return Document(
                    id=row["id"],
                    title=row["title"],
                    content=row["content"],
                    doc_type=row["doc_type"],
                    club_name=row["club_name"],
                    category=row["category"],
                    tags=json.loads(row["tags"]) if row["tags"] else [],
                    metadata=json.loads(row["metadata"]) if row["metadata"] else {},
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                )
        return None

    def search_documents(
        self,
        query: str = "",
        doc_type: str = "",
        club_name: str = "",
        category: str = "",
        limit: int = 20
    ) -> List[Document]:
        """Cerca documenti con filtri"""
        conditions = []
        params = []

        if query:
            conditions.append("(title LIKE ? OR content LIKE ?)")
            params.extend([f"%{query}%", f"%{query}%"])
        if doc_type:
            conditions.append("doc_type = ?")
            params.append(doc_type)
        if club_name:
            conditions.append("club_name LIKE ?")
            params.append(f"%{club_name}%")
        if category:
            conditions.append("category = ?")
            params.append(category)

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(f"""
                SELECT * FROM documents
                WHERE {where_clause}
                ORDER BY updated_at DESC
                LIMIT ?
            """, params + [limit]).fetchall()

            return [
                Document(
                    id=row["id"],
                    title=row["title"],
                    content=row["content"],
                    doc_type=row["doc_type"],
                    club_name=row["club_name"],
                    category=row["category"],
                    tags=json.loads(row["tags"]) if row["tags"] else [],
                    metadata=json.loads(row["metadata"]) if row["metadata"] else {},
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                )
                for row in rows
            ]

    # -------------------------------------------------------------------------
    # PLANS CRUD
    # -------------------------------------------------------------------------

    def save_plan(self, plan: PlanRecord) -> str:
        """Salva piano strategico"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO plans
                (id, club_name, category, region, status, plan_data, sources_count,
                 credibility_score, export_paths, notes, last_edited_by, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                plan.id,
                plan.club_name,
                plan.category,
                plan.region,
                plan.status,
                json.dumps(plan.plan_data),
                plan.sources_count,
                plan.credibility_score,
                json.dumps(plan.export_paths),
                plan.notes,
                plan.last_edited_by,
                plan.created_at,
                datetime.now().isoformat(),
            ))
            conn.commit()
        return plan.id

    def get_plan(self, plan_id: str) -> Optional[PlanRecord]:
        """Recupera piano per ID"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM plans WHERE id = ?", (plan_id,)
            ).fetchone()

            if row:
                return PlanRecord(
                    id=row["id"],
                    club_name=row["club_name"],
                    category=row["category"],
                    region=row["region"],
                    status=row["status"],
                    plan_data=json.loads(row["plan_data"]) if row["plan_data"] else {},
                    sources_count=row["sources_count"],
                    credibility_score=row["credibility_score"],
                    export_paths=json.loads(row["export_paths"]) if row["export_paths"] else [],
                    notes=row["notes"],
                    last_edited_by=row["last_edited_by"],
                    created_at=row["created_at"],
                )
        return None

    def list_plans(
        self,
        status: str = "",
        category: str = "",
        club_name: str = "",
        limit: int = 50,
        offset: int = 0
    ) -> Tuple[List[PlanRecord], int]:
        """
        Lista piani con filtri e paginazione.

        Returns:
            (lista_piani, conteggio_totale)
        """
        conditions = []
        params = []

        if status:
            conditions.append("status = ?")
            params.append(status)
        if category:
            conditions.append("category = ?")
            params.append(category)
        if club_name:
            conditions.append("club_name LIKE ?")
            params.append(f"%{club_name}%")

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            # Count totale
            total = conn.execute(
                f"SELECT COUNT(*) FROM plans WHERE {where_clause}",
                params
            ).fetchone()[0]

            # Piani paginati
            rows = conn.execute(f"""
                SELECT * FROM plans
                WHERE {where_clause}
                ORDER BY updated_at DESC
                LIMIT ? OFFSET ?
            """, params + [limit, offset]).fetchall()

            plans = [
                PlanRecord(
                    id=row["id"],
                    club_name=row["club_name"],
                    category=row["category"],
                    region=row["region"],
                    status=row["status"],
                    plan_data=json.loads(row["plan_data"]) if row["plan_data"] else {},
                    sources_count=row["sources_count"],
                    credibility_score=row["credibility_score"],
                    export_paths=json.loads(row["export_paths"]) if row["export_paths"] else [],
                    notes=row["notes"],
                    last_edited_by=row["last_edited_by"],
                    created_at=row["created_at"],
                )
                for row in rows
            ]

            return plans, total

    def update_plan_status(self, plan_id: str, status: str, notes: str = "") -> bool:
        """Aggiorna status piano"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE plans
                SET status = ?, notes = ?, updated_at = ?
                WHERE id = ?
            """, (status, notes, datetime.now().isoformat(), plan_id))
            conn.commit()
            return conn.total_changes > 0

    def delete_plan(self, plan_id: str) -> bool:
        """Elimina piano"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM plans WHERE id = ?", (plan_id,))
            conn.commit()
            return conn.total_changes > 0

    def find_similar_plans(
        self,
        category: str,
        country: str = "",
        region: str = "",
        exclude_id: str = "",
        limit: int = 5
    ) -> List[PlanRecord]:
        """
        Trova piani simili per categoria/paese/regione.
        Usato per apprendimento: suggerisce contenuti da piani approvati simili.

        Priorita:
        1. Stessa categoria + stesso paese/regione (piu rilevante)
        2. Stessa categoria (qualsiasi paese)
        3. Categoria simile (es. Serie B -> Serie C)

        Solo piani con status 'approved' o 'exported' vengono considerati.
        """
        results = []

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            # Prima: stessa categoria, stesso paese/regione, approvati
            conditions = ["status IN ('approved', 'exported')", "category = ?"]
            params = [category]

            if exclude_id:
                conditions.append("id != ?")
                params.append(exclude_id)

            if region:
                conditions.append("region = ?")
                params.append(region)

            where_clause = " AND ".join(conditions)

            rows = conn.execute(f"""
                SELECT * FROM plans
                WHERE {where_clause}
                ORDER BY credibility_score DESC, updated_at DESC
                LIMIT ?
            """, params + [limit]).fetchall()

            for row in rows:
                results.append(PlanRecord(
                    id=row["id"],
                    club_name=row["club_name"],
                    category=row["category"],
                    region=row["region"],
                    status=row["status"],
                    plan_data=json.loads(row["plan_data"]) if row["plan_data"] else {},
                    sources_count=row["sources_count"],
                    credibility_score=row["credibility_score"],
                    export_paths=[],
                    notes=row["notes"],
                    last_edited_by=row["last_edited_by"],
                    created_at=row["created_at"],
                ))

            # Se non abbastanza, aggiungi da stessa categoria senza filtro regione
            if len(results) < limit:
                remaining = limit - len(results)
                existing_ids = [r.id for r in results]
                if exclude_id:
                    existing_ids.append(exclude_id)

                placeholders = ",".join(["?" for _ in existing_ids])
                rows = conn.execute(f"""
                    SELECT * FROM plans
                    WHERE status IN ('approved', 'exported')
                    AND category = ?
                    AND id NOT IN ({placeholders})
                    ORDER BY credibility_score DESC
                    LIMIT ?
                """, [category] + existing_ids + [remaining]).fetchall()

                for row in rows:
                    results.append(PlanRecord(
                        id=row["id"],
                        club_name=row["club_name"],
                        category=row["category"],
                        region=row["region"],
                        status=row["status"],
                        plan_data=json.loads(row["plan_data"]) if row["plan_data"] else {},
                        sources_count=row["sources_count"],
                        credibility_score=row["credibility_score"],
                        export_paths=[],
                        notes=row["notes"],
                        last_edited_by=row["last_edited_by"],
                        created_at=row["created_at"],
                    ))

        return results

    def get_section_examples(
        self,
        section_key: str,
        category: str,
        limit: int = 3
    ) -> List[Dict]:
        """
        Recupera esempi di sezioni da piani approvati.
        Usato per dare contesto agli agenti durante la generazione.

        Args:
            section_key: Chiave sezione (es. "technical_sporting", "governance")
            category: Categoria del club
            limit: Numero esempi

        Returns:
            Lista di {club_name, content, credibility_score}
        """
        examples = []

        similar_plans = self.find_similar_plans(category, limit=limit * 2)

        for plan in similar_plans:
            if plan.plan_data and section_key in plan.plan_data:
                section_content = plan.plan_data[section_key]
                if isinstance(section_content, dict) and 'content' in section_content:
                    content = section_content['content']
                elif isinstance(section_content, str):
                    content = section_content
                else:
                    continue

                # Prendi solo contenuto significativo (non errori o mock)
                if len(content) > 200 and 'errore' not in content.lower():
                    examples.append({
                        'club_name': plan.club_name,
                        'category': plan.category,
                        'content': content[:2000],  # Limita per non esplodere prompt
                        'credibility_score': plan.credibility_score,
                    })

                    if len(examples) >= limit:
                        break

        return examples

    # -------------------------------------------------------------------------
    # BENCHMARKS
    # -------------------------------------------------------------------------

    def save_benchmark(
        self,
        metric: str,
        category: str,
        value: str,
        source: str,
        source_url: str = "",
        valid_years: int = 1
    ) -> str:
        """Salva benchmark con validità temporale"""
        benchmark_id = hashlib.md5(f"{metric}_{category}".encode()).hexdigest()[:12]

        with sqlite3.connect(self.db_path) as conn:
            now = datetime.now()
            conn.execute("""
                INSERT OR REPLACE INTO benchmarks
                (id, metric, category, value, source, source_url, valid_from, valid_to, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                benchmark_id,
                metric,
                category,
                value,
                source,
                source_url,
                now.isoformat(),
                (now.replace(year=now.year + valid_years)).isoformat(),
                now.isoformat(),
            ))
            conn.commit()
        return benchmark_id

    def get_benchmark(self, metric: str, category: str) -> Optional[Dict]:
        """Recupera benchmark valido"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("""
                SELECT * FROM benchmarks
                WHERE metric = ? AND category = ?
                AND valid_to > ?
                ORDER BY created_at DESC LIMIT 1
            """, (metric, category, datetime.now().isoformat())).fetchone()

            if row:
                return dict(row)
        return None

    # -------------------------------------------------------------------------
    # STATISTICS
    # -------------------------------------------------------------------------

    def get_statistics(self) -> Dict[str, Any]:
        """Statistiche globali del knowledge store"""
        with sqlite3.connect(self.db_path) as conn:
            stats = {
                "documents": {
                    "total": conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0],
                    "by_type": {},
                },
                "plans": {
                    "total": conn.execute("SELECT COUNT(*) FROM plans").fetchone()[0],
                    "by_status": {},
                    "by_category": {},
                    "avg_credibility": 0,
                },
                "benchmarks": {
                    "total": conn.execute("SELECT COUNT(*) FROM benchmarks").fetchone()[0],
                    "valid": conn.execute(
                        "SELECT COUNT(*) FROM benchmarks WHERE valid_to > ?",
                        (datetime.now().isoformat(),)
                    ).fetchone()[0],
                },
            }

            # Documenti per tipo
            for row in conn.execute("SELECT doc_type, COUNT(*) FROM documents GROUP BY doc_type"):
                stats["documents"]["by_type"][row[0]] = row[1]

            # Piani per status
            for row in conn.execute("SELECT status, COUNT(*) FROM plans GROUP BY status"):
                stats["plans"]["by_status"][row[0]] = row[1]

            # Piani per categoria
            for row in conn.execute("SELECT category, COUNT(*) FROM plans GROUP BY category"):
                stats["plans"]["by_category"][row[0]] = row[1]

            # Media credibilità
            avg = conn.execute("SELECT AVG(credibility_score) FROM plans").fetchone()[0]
            stats["plans"]["avg_credibility"] = round(avg, 1) if avg else 0

            return stats


# =============================================================================
# GEMINI FILE SEARCH / RAG
# =============================================================================

class GeminiKnowledgeRAG:
    """
    RAG as a Service con Gemini File Search.
    Per ricerca semantica avanzata nella knowledge base.
    """

    def __init__(self, api_key: str = GEMINI_API_KEY):
        if not GENAI_AVAILABLE:
            logger.warning("google-generativeai not available. RAG features disabled.")
            self.available = False
            return

        if not api_key:
            logger.warning("GEMINI_API_KEY not set. RAG features disabled.")
            self.available = False
            return

        # Nuova API google-genai usa un client
        self.client = genai.Client()
        self.model_name = MODEL_CONFIG.name
        self.embedding_model = MODEL_CONFIG.embedding_model
        self.available = True

        # Storage per embeddings locali
        self.embeddings_path = KNOWLEDGE_DIR / "embeddings.pkl"
        self.embeddings_cache: Dict[str, List[float]] = {}
        self._load_embeddings()

    def _load_embeddings(self):
        """Carica embeddings cached"""
        if self.embeddings_path.exists():
            try:
                with open(self.embeddings_path, "rb") as f:
                    self.embeddings_cache = pickle.load(f)
            except Exception as e:
                logger.warning(f"Error loading embeddings cache: {e}")
                self.embeddings_cache = {}

    def _save_embeddings(self):
        """Salva embeddings cache"""
        try:
            with open(self.embeddings_path, "wb") as f:
                pickle.dump(self.embeddings_cache, f)
        except Exception as e:
            logger.warning(f"Error saving embeddings cache: {e}")

    def embed_text(self, text: str) -> Optional[List[float]]:
        """Genera embedding per testo"""
        if not self.available:
            return None

        # Check cache
        text_hash = hashlib.md5(text.encode()).hexdigest()
        if text_hash in self.embeddings_cache:
            return self.embeddings_cache[text_hash]

        try:
            result = self.client.models.embed_content(
                model=self.embedding_model,
                contents=text,
                config={'task_type': 'RETRIEVAL_DOCUMENT'}
            )
            embedding = result.embeddings[0].values

            # Cache
            self.embeddings_cache[text_hash] = embedding
            self._save_embeddings()

            return embedding
        except Exception as e:
            logger.error(f"Embedding error: {e}")
            return None

    def embed_query(self, query: str) -> Optional[List[float]]:
        """Genera embedding per query (ottimizzato per retrieval)"""
        if not self.available:
            return None

        try:
            result = self.client.models.embed_content(
                model=self.embedding_model,
                contents=query,
                config={'task_type': 'RETRIEVAL_QUERY'}
            )
            return result.embeddings[0].values
        except Exception as e:
            logger.error(f"Query embedding error: {e}")
            return None

    def semantic_search(
        self,
        query: str,
        documents: List[Document],
        top_k: int = 5
    ) -> List[SearchResult]:
        """
        Ricerca semantica nei documenti.

        Args:
            query: Query di ricerca
            documents: Lista documenti da cercare
            top_k: Numero risultati

        Returns:
            Lista SearchResult ordinata per score
        """
        if not self.available:
            # Fallback a ricerca keyword
            return self._keyword_search(query, documents, top_k)

        query_embedding = self.embed_query(query)
        if not query_embedding:
            return self._keyword_search(query, documents, top_k)

        results = []
        for doc in documents:
            doc_embedding = self.embed_text(doc.content[:2000])  # Limit per performance
            if doc_embedding:
                score = self._cosine_similarity(query_embedding, doc_embedding)
                results.append(SearchResult(
                    document=doc,
                    score=score,
                ))

        # Ordina per score
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:top_k]

    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        """Calcola cosine similarity"""
        import math
        dot_product = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot_product / (norm_a * norm_b)

    def _keyword_search(
        self,
        query: str,
        documents: List[Document],
        top_k: int
    ) -> List[SearchResult]:
        """Fallback a ricerca keyword"""
        query_words = set(query.lower().split())
        results = []

        for doc in documents:
            doc_words = set(doc.content.lower().split())
            overlap = len(query_words & doc_words)
            score = overlap / len(query_words) if query_words else 0

            if score > 0:
                results.append(SearchResult(document=doc, score=score))

        results.sort(key=lambda x: x.score, reverse=True)
        return results[:top_k]

    def generate_with_context(
        self,
        query: str,
        context_documents: List[Document],
        system_prompt: str = ""
    ) -> str:
        """
        Genera risposta usando RAG con contesto dai documenti.

        Args:
            query: Domanda/richiesta
            context_documents: Documenti per contesto
            system_prompt: Prompt di sistema opzionale
        """
        if not self.available:
            return "RAG non disponibile. Configurare GEMINI_API_KEY."

        # Costruisci contesto
        context_parts = []
        for doc in context_documents[:5]:  # Max 5 documenti
            context_parts.append(f"### {doc.title}\n{doc.content[:1500]}\n")

        context = "\n---\n".join(context_parts)

        prompt = f"""
{system_prompt}

CONTESTO DALLA KNOWLEDGE BASE:
{context}

---

RICHIESTA: {query}

Rispondi basandoti sul contesto fornito. Se l'informazione non è presente nel contesto, indicalo chiaramente.
"""

        try:
            response = self.client.models.generate_content(model=self.model_name, contents=prompt)
            return response.text
        except Exception as e:
            logger.error(f"Generation error: {e}")
            return f"Errore nella generazione: {e}"


# =============================================================================
# UNIFIED KNOWLEDGE MANAGER
# =============================================================================

class KnowledgeManager:
    """
    Manager unificato per knowledge store.
    Combina SQLite storage + Gemini RAG.
    """

    def __init__(self):
        self.store = SQLiteKnowledgeStore()
        self.rag = GeminiKnowledgeRAG()

    def add_plan_to_knowledge(self, plan_record: PlanRecord) -> str:
        """Salva piano e indicizza per RAG"""
        # Salva in SQLite
        plan_id = self.store.save_plan(plan_record)

        # Crea documento per RAG
        content_parts = []
        for section, text in plan_record.plan_data.items():
            if isinstance(text, str):
                content_parts.append(f"## {section}\n{text}")

        doc = Document(
            id=f"plan_{plan_id}",
            title=f"Piano Strategico {plan_record.club_name}",
            content="\n\n".join(content_parts),
            doc_type="plan",
            club_name=plan_record.club_name,
            category=plan_record.category,
            metadata={
                "plan_id": plan_id,
                "credibility_score": plan_record.credibility_score,
            }
        )
        self.store.add_document(doc)

        return plan_id

    def search_similar_plans(
        self,
        query: str = "",
        category: str = "",
        top_k: int = 5
    ) -> List[SearchResult]:
        """Cerca piani simili"""
        # Recupera documenti tipo plan
        docs = self.store.search_documents(
            query=query,
            doc_type="plan",
            category=category,
            limit=50
        )

        if self.rag.available and query:
            return self.rag.semantic_search(query, docs, top_k)

        return [SearchResult(document=d, score=1.0) for d in docs[:top_k]]

    def get_context_for_generation(
        self,
        club_category: str,
        section_type: str
    ) -> List[Document]:
        """
        Recupera contesto per generazione sezione.
        Utile per template e esempi da piani precedenti.
        """
        # Cerca piani della stessa categoria
        docs = self.store.search_documents(
            doc_type="plan",
            category=club_category,
            limit=10
        )

        # Filtra per sezione se possibile
        filtered = []
        for doc in docs:
            if section_type.lower() in doc.content.lower():
                filtered.append(doc)

        return filtered[:3] if filtered else docs[:3]

    def export_full_knowledge_base(self, output_path: Path = None) -> Path:
        """Esporta knowledge base completa per backup"""
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = OUTPUT_DIR / f"knowledge_backup_{timestamp}.json"

        with sqlite3.connect(self.store.db_path) as conn:
            conn.row_factory = sqlite3.Row

            export_data = {
                "exported_at": datetime.now().isoformat(),
                "statistics": self.store.get_statistics(),
                "documents": [dict(row) for row in conn.execute("SELECT * FROM documents").fetchall()],
                "plans": [dict(row) for row in conn.execute("SELECT * FROM plans").fetchall()],
                "benchmarks": [dict(row) for row in conn.execute("SELECT * FROM benchmarks").fetchall()],
            }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)

        logger.info(f"Knowledge base exported to: {output_path}")
        return output_path

    def import_knowledge_base(self, import_path: Path) -> Dict[str, int]:
        """Importa knowledge base da backup"""
        with open(import_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        counts = {"documents": 0, "plans": 0, "benchmarks": 0}

        with sqlite3.connect(self.store.db_path) as conn:
            for doc in data.get("documents", []):
                try:
                    conn.execute("""
                        INSERT OR REPLACE INTO documents VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, tuple(doc.values()))
                    counts["documents"] += 1
                except Exception as e:
                    logger.warning(f"Error importing document: {e}")

            for plan in data.get("plans", []):
                try:
                    conn.execute("""
                        INSERT OR REPLACE INTO plans VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, tuple(plan.values()))
                    counts["plans"] += 1
                except Exception as e:
                    logger.warning(f"Error importing plan: {e}")

            conn.commit()

        logger.info(f"Imported: {counts}")
        return counts
