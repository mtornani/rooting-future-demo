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
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict
import logging
import sqlite3
import pickle
from cryptography.fernet import Fernet
from domain.error_handling import DatabaseError

# =============================================================================
# ENCRYPTION HELPER
# =============================================================================

# In produzione, ENCRYPTION_KEY deve essere in .env
# Generabile con: Fernet.generate_key().decode()
ENCRYPTION_KEY = os.environ.get("ENCRYPTION_KEY", "bW995M4DtsehWjIlmLvxYbY6nUpViBhqolsWlliQxHI=")

def encrypt_data(data: str) -> str:
    """Cifra una stringa usando Fernet"""
    if not data: return ""
    f = Fernet(ENCRYPTION_KEY.encode())
    return f.encrypt(data.encode()).decode()

def decrypt_data(token: str) -> str:
    """Decifra un token Fernet"""
    if not token: return ""
    
    # Backward compatibility: se sembra JSON, non decifrare
    stripped = token.strip()
    if stripped.startswith("{") or stripped.startswith("["):
        return token

    try:
        f = Fernet(ENCRYPTION_KEY.encode())
        return f.decrypt(token.encode()).decode()
    except Exception as e:
        logger.error(f"Decryption error: {e}")
        return "{}" # Return empty json as fallback

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
    section_type: str = ""  # "sportivi", "marketing", etc. (OPT-001)
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
    owner_id: Optional[int] = None

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

    def _init_db(self) -> None:
        """Inizializza database con schema e ottimizzazioni (OPT-001)"""
        with sqlite3.connect(self.db_path) as conn:
            # Performance Optimizations (OPT-001)
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")

            conn.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    content TEXT,
                    doc_type TEXT,
                    section_type TEXT,
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
                    owner_id INTEGER,
                    created_at TEXT,
                    updated_at TEXT
                )
            """)
            
            # Migration: Add columns if missing (OPT-001)
            try:
                conn.execute("ALTER TABLE plans ADD COLUMN owner_id INTEGER")
            except sqlite3.OperationalError:
                pass 

            try:
                conn.execute("ALTER TABLE documents ADD COLUMN section_type TEXT")
            except sqlite3.OperationalError:
                pass

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

            conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    full_name TEXT,
                    role TEXT DEFAULT 'viewer',
                    credits INTEGER DEFAULT 0, -- Sistema di crediti per piani
                    first_login INTEGER DEFAULT 1, -- Flag per onboarding
                    is_active INTEGER DEFAULT 1,
                    created_at TEXT
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS plan_assignments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    plan_id TEXT NOT NULL,
                    user_id INTEGER NOT NULL,
                    assigned_by INTEGER,
                    created_at TEXT,
                    FOREIGN KEY(plan_id) REFERENCES plans(id),
                    FOREIGN KEY(user_id) REFERENCES users(id)
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS plan_developments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    plan_id TEXT NOT NULL,
                    user_id INTEGER NOT NULL,
                    activity_type TEXT, -- "update", "note", "task_completed"
                    description TEXT,
                    created_at TEXT,
                    FOREIGN KEY(plan_id) REFERENCES plans(id),
                    FOREIGN KEY(user_id) REFERENCES users(id)
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS system_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """)

            # Initial setup for killswitch
            conn.execute("INSERT OR IGNORE INTO system_settings (key, value) VALUES ('global_lockout', '0')")

            # REF-003: Generation Sessions for checkpoint/recovery
            conn.execute("""
                CREATE TABLE IF NOT EXISTS generation_sessions (
                    session_id TEXT PRIMARY KEY,
                    club_name TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    completed_sections TEXT,
                    pending_sections TEXT,
                    partial_plan TEXT,
                    metadata TEXT,
                    error_log TEXT,
                    owner_id INTEGER,
                    FOREIGN KEY(owner_id) REFERENCES users(id)
                )
            """)

            # Indici per ricerche veloci (OPT-001 Optimized)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_docs_type ON documents(doc_type)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_docs_club ON documents(club_name)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_docs_category_section ON documents(category, section_type)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_plans_club ON plans(club_name)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_plans_status ON plans(status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_plans_owner ON plans(owner_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_plans_created ON plans(created_at DESC)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_benchmarks_metric ON benchmarks(metric, category)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)")

            # REF-003: Indices for sessions
            conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_status ON generation_sessions(status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_owner ON generation_sessions(owner_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_updated ON generation_sessions(updated_at DESC)")

            # Licenses table for admin management
            conn.execute("""
                CREATE TABLE IF NOT EXISTS licenses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT NOT NULL,
                    hwid TEXT NOT NULL,
                    license_key TEXT NOT NULL,
                    duration_days INTEGER,
                    created_at TEXT NOT NULL,
                    expires_at TEXT,
                    status TEXT DEFAULT 'active',
                    revoked_at TEXT,
                    notes TEXT
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_licenses_email ON licenses(email)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_licenses_status ON licenses(status)")

            conn.commit()
            logger.info("Database SQLite inizializzato con ottimizzazioni WAL e indici OPT-001.")

    # -------------------------------------------------------------------------
    # DOCUMENTS CRUD
    # -------------------------------------------------------------------------

    def add_document(self, doc: Document) -> str:
        """Aggiunge documento al knowledge store"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO documents
                (id, title, content, doc_type, section_type, club_name, category, tags, metadata, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                doc.id,
                doc.title,
                doc.content,
                doc.doc_type,
                doc.section_type,
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
                    section_type=dict(row).get("section_type", ""),
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
        section_type: str = "",
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
        if section_type:
            conditions.append("section_type = ?")
            params.append(section_type)
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
                    section_type=dict(row).get("section_type", ""),
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
    # USERS CRUD (Multi-Tenancy)
    # -------------------------------------------------------------------------

    def create_user(self, email: str, password_hash: str, full_name: str = "", role: str = "viewer") -> int:
        """Crea nuovo utente"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO users (email, password_hash, full_name, role, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (email, password_hash, full_name, role, datetime.now().isoformat()))
            conn.commit()
            return cursor.lastrowid

    def get_user_by_email(self, email: str) -> Optional[Dict]:
        """Recupera utente per email"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
            return dict(row) if row else None

    def get_user_by_id(self, user_id: int) -> Optional[Dict]:
        """Recupera utente per ID"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
            return dict(row) if row else None

    def get_user_credits(self, user_id: int) -> int:
        """Recupera il saldo crediti di un utente"""
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute("SELECT credits FROM users WHERE id = ?", (user_id,)).fetchone()
            return row[0] if row else 0

    def list_users(self) -> List[Dict]:
        """Lista tutti gli utenti con statistiche"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            # Recupera utenti e conta piani assegnati/posseduti
            query = """
                SELECT 
                    u.id, u.email, u.full_name, u.role, u.credits, u.last_login, u.created_at,
                    (SELECT COUNT(*) FROM plan_assignments pa WHERE pa.user_id = u.id) as assigned_plans_count,
                    (SELECT COUNT(*) FROM plans p WHERE p.owner_id = u.id) as owned_plans_count
                FROM users u
                ORDER BY u.created_at DESC
            """
            # Nota: 'last_login' potrebbe non esistere se non aggiunto alla tabella users, 
            # gestiamo l'errore o assumiamo che la colonna esista/venga ignorata se la query è generica.
            # Per sicurezza usiamo una query più semplice se la colonna manca, 
            # ma qui assumiamo che lo schema sia coerente o che lo aggiorniamo.
            
            # Controllo preventivo colonna last_login (migration on the fly "soft")
            cursor = conn.execute("PRAGMA table_info(users)")
            columns = [col[1] for col in cursor.fetchall()]
            
            final_query = query
            if 'last_login' not in columns:
                final_query = query.replace("u.last_login,", "NULL as last_login,")

            rows = conn.execute(final_query).fetchall()
            return [dict(row) for row in rows]


    def update_user_credits(self, user_id: int, amount: int) -> bool:
        """Aggiunge o sottrae crediti a un utente"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("UPDATE users SET credits = credits + ? WHERE id = ?", (amount, user_id))
            conn.commit()
            return conn.total_changes > 0

    def has_sufficient_credits(self, user_id: int, required: int = 1) -> bool:
        """Verifica se l'utente ha crediti sufficienti"""
        # Super Admin ha crediti infiniti
        user = self.get_user_by_id(user_id)
        if user and user['role'] == 'super_admin':
            return True
        return self.get_user_credits(user_id) >= required

    # -------------------------------------------------------------------------
    # ASSIGNMENTS & DEVELOPMENTS
    # -------------------------------------------------------------------------

    def assign_plan(self, plan_id: str, user_id: int, assigned_by: int) -> bool:
        """Assegna un piano a un Temporary Manager"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO plan_assignments (plan_id, user_id, assigned_by, created_at)
                VALUES (?, ?, ?, ?)
            """, (plan_id, user_id, assigned_by, datetime.now().isoformat()))
            conn.commit()
            return True

    def get_assigned_plans(self, user_id: int) -> List[str]:
        """Recupera IDs dei piani assegnati a un utente"""
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute("SELECT plan_id FROM plan_assignments WHERE user_id = ?", (user_id,)).fetchall()
            return [row[0] for row in rows]

    def add_development_log(self, plan_id: str, user_id: int, activity_type: str, description: str):
        """Registra un'attività di sviluppo sul piano"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO plan_developments (plan_id, user_id, activity_type, description, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (plan_id, user_id, activity_type, description, datetime.now().isoformat()))
            conn.commit()

    def get_plan_developments(self, plan_id: str) -> List[Dict]:
        """Recupera la cronologia degli sviluppi di un piano"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT d.*, u.full_name as user_name 
                FROM plan_developments d
                JOIN users u ON d.user_id = u.id
                WHERE d.plan_id = ?
                ORDER BY d.created_at DESC
            """, (plan_id,)).fetchall()
            return [dict(row) for row in rows]

    # -------------------------------------------------------------------------
    # SYSTEM SETTINGS & KILLSWITCH
    # -------------------------------------------------------------------------

    def set_system_setting(self, key: str, value: str):
        """Imposta un parametro di sistema"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("INSERT OR REPLACE INTO system_settings (key, value) VALUES (?, ?)", (key, value))
            conn.commit()

    def get_system_setting(self, key: str, default: str = None) -> str:
        """Recupera un parametro di sistema"""
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute("SELECT value FROM system_settings WHERE key = ?", (key,)).fetchone()
            return row[0] if row else default

    def is_killswitch_active(self) -> bool:
        """Controlla se il sistema è in modalità blocco totale"""
        return self.get_system_setting('global_lockout', '0') == '1'

    # -------------------------------------------------------------------------
    # PLANS CRUD
    # -------------------------------------------------------------------------

    def get_plan(self, plan_id: str) -> Optional[PlanRecord]:
        """Recupera un piano per ID"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                row = conn.execute("SELECT * FROM plans WHERE id = ?", (plan_id,)).fetchone()
                
                if row:
                    # DECIFRATURA: Decifriamo i dati del piano prima di restituirli
                    decrypted_json = decrypt_data(row["plan_data"])
                    try:
                        plan_data = json.loads(decrypted_json)
                    except:
                        plan_data = {}

                    return PlanRecord(
                        id=row["id"],
                        club_name=row["club_name"],
                        category=row["category"],
                        region=row["region"],
                        status=row["status"],
                        plan_data=plan_data,
                        sources_count=row["sources_count"],
                        credibility_score=row["credibility_score"],
                        export_paths=json.loads(row["export_paths"]) if row["export_paths"] else [],
                        notes=row["notes"],
                        last_edited_by=row["last_edited_by"],
                        owner_id=row["owner_id"],
                        created_at=row["created_at"],
                    )
            return None
        except Exception as e:
            logger.error(f"Database error in get_plan: {e}")
            raise DatabaseError(message=f"Errore durante il recupero del piano {plan_id}", details=str(e))

    def save_plan(self, plan: PlanRecord, owner_id: int = None) -> str:
        """Salva piano strategico con cifratura del contenuto"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Check if plan exists to preserve owner_id if not provided
                existing_owner = None
                if not owner_id:
                    row = conn.execute("SELECT owner_id FROM plans WHERE id = ?", (plan.id,)).fetchone()
                    if row:
                        existing_owner = row[0]
                
                final_owner = owner_id if owner_id else existing_owner
                
                # CIFRATURA: Cifriamo il contenuto sensibile del piano
                encrypted_plan_data = encrypt_data(json.dumps(plan.plan_data))

                conn.execute("""
                    INSERT OR REPLACE INTO plans
                    (id, club_name, category, region, status, plan_data, sources_count,
                     credibility_score, export_paths, notes, last_edited_by, owner_id, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    plan.id,
                    plan.club_name,
                    plan.category,
                    plan.region,
                    plan.status,
                    encrypted_plan_data,
                    plan.sources_count,
                    plan.credibility_score,
                    json.dumps(plan.export_paths),
                    plan.notes,
                    plan.last_edited_by,
                    final_owner,
                    plan.created_at,
                    datetime.now().isoformat(),
                ))
                conn.commit()
            return plan.id
        except Exception as e:
            logger.error(f"Database error in save_plan: {e}")
            raise DatabaseError(message=f"Errore durante il salvataggio del piano {plan.id}", details=str(e))

        def list_plans(

            self,

            status: str = "",

            category: str = "",

            club_name: str = "",

            owner_id: int = None,

            plan_ids: List[str] = None,

            limit: int = 50,

            offset: int = 0,

            exclude_status: str = ""

        ) -> Tuple[List[PlanRecord], int]:

            """

            Lista piani con filtri e paginazione.

            Isolamento stretto: l'utente vede solo i propri piani o quelli a lui assegnati.

            """

            conditions = []

            params = []

    

            # SICUREZZA: Filtro obbligatorio per owner_id (tranne Super Admin gestito a livello app)

            if owner_id:

                # Mostra i piani di cui è owner O quelli che gli sono stati assegnati

                assigned_ids = self.get_assigned_plans(owner_id)

                if assigned_ids:

                    placeholders = ",".join(["?" for _ in assigned_ids])

                    conditions.append(f"(owner_id = ? OR id IN ({placeholders}))")

                    params.append(owner_id)

                    params.extend(assigned_ids)

                else:

                    conditions.append("owner_id = ?")

                    params.append(owner_id)

    

            if status:

                conditions.append("status = ?")

                params.append(status)

            

            if exclude_status:

                conditions.append("status != ?")

                params.append(exclude_status)

    

            if category:

                conditions.append("category = ?")

                params.append(category)

            if club_name:

                conditions.append("club_name LIKE ?")

                params.append(f"%{club_name}%")
        
        if plan_ids is not None:
            if not plan_ids: 
                return [], 0
            placeholders = ",".join(["?" for _ in plan_ids])
            conditions.append(f"id IN ({placeholders})")
            params.extend(plan_ids)

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            total = conn.execute(
                f"SELECT COUNT(*) FROM plans WHERE {where_clause}",
                params
            ).fetchone()[0]

            rows = conn.execute(f"""
                SELECT * FROM plans
                WHERE {where_clause}
                ORDER BY updated_at DESC
                LIMIT ? OFFSET ?
            """, params + [limit, offset]).fetchall()

            plans = []
            for row in rows:
                # DECIFRATURA: Decifriamo i dati del piano prima di restituirli
                decrypted_json = decrypt_data(row["plan_data"])
                try:
                    plan_data = json.loads(decrypted_json)
                except:
                    plan_data = {}

                plans.append(PlanRecord(
                    id=row["id"],
                    club_name=row["club_name"],
                    category=row["category"],
                    region=row["region"],
                    status=row["status"],
                    plan_data=plan_data,
                    sources_count=row["sources_count"],
                    credibility_score=row["credibility_score"],
                    export_paths=json.loads(row["export_paths"]) if row["export_paths"] else [],
                    notes=row["notes"],
                    last_edited_by=row["last_edited_by"],
                    owner_id=row["owner_id"],
                    created_at=row["created_at"],
                ))

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

    def __init__(self, file_search_manager: Any = None):
        self.store = SQLiteKnowledgeStore()
        self.rag = GeminiKnowledgeRAG()
        self.file_search_manager = file_search_manager

    def add_plan_to_knowledge(self, plan_record: PlanRecord, owner_id: int = None) -> str:
        """Salva piano e indicizza per RAG (Aggiornato OPT-001)"""
        # Salva in SQLite
        plan_id = self.store.save_plan(plan_record, owner_id)

        # Crea documenti separati per sezione per RAG granulare
        for section, text in plan_record.plan_data.items():
            content = ""
            if isinstance(text, str):
                content = text
            elif isinstance(text, dict) and 'content' in text:
                content = text['content']
            
            if len(content) < 200: continue

            doc = Document(
                id=f"plan_{plan_id}_{section}",
                title=f"Piano {plan_record.club_name} - Sezione {section}",
                content=content,
                doc_type="plan",
                section_type=section,
                club_name=plan_record.club_name,
                category=plan_record.category,
                metadata={
                    "plan_id": plan_id,
                    "credibility_score": plan_record.credibility_score,
                }
            )
            self.store.add_document(doc)

        # Carica su Gemini File Search Store (RAG a servizio)
        if self.file_search_manager:
            try:
                # Costruisci contenuto completo del piano per l'upload
                full_content_parts = [f"Piano Strategico: {plan_record.club_name}\n"]
                for section, text in plan_record.plan_data.items():
                    content = ""
                    if isinstance(text, str):
                        content = text
                    elif isinstance(text, dict) and 'content' in text:
                        content = text['content']
                    
                    if content:
                        full_content_parts.append(f"\n--- SEZIONE: {section} ---\n{content}")
                
                full_content = "\n".join(full_content_parts)

                # Crea un file temporaneo per l'upload
                temp_dir = Path(KNOWLEDGE_DIR / "temp_uploads")
                temp_dir.mkdir(exist_ok=True)
                temp_file = temp_dir / f"{plan_id}.txt"
                temp_file.write_text(full_content, encoding="utf-8")
                
                success = self.file_search_manager.upload_file(temp_file)
                if success:
                    logger.info(f"Plan {plan_id} uploaded to Gemini File Search Store")
                else:
                    logger.warning(f"Failed to upload plan {plan_id} to Gemini File Search Store")
                
                # Rimuovi file temporaneo
                # temp_file.unlink() 
            except Exception as e:
                logger.error(f"Error during Gemini File Search upload: {e}")

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
        Recupera contesto per generazione sezione (Ottimizzato OPT-001).
        Utile per template e esempi da piani precedenti.
        """
        # Cerca piani della stessa categoria e tipo sezione usando l'indice
        docs = self.store.search_documents(
            doc_type="plan",
            category=club_category,
            section_type=section_type,
            limit=5
        )

        if not docs:
            # Fallback: cerca per categoria e filtra nel contenuto
            docs = self.store.search_documents(
                doc_type="plan",
                category=club_category,
                limit=10
            )
            # Filtra per sezione nel contenuto
            filtered = []
            for doc in docs:
                if section_type.lower() in doc.content.lower():
                    filtered.append(doc)
            return filtered[:3] if filtered else docs[:3]

        return docs[:3]

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

    # -------------------------------------------------------------------------
    # GENERATION SESSIONS (REF-003)
    # -------------------------------------------------------------------------

    def save_generation_session(self, session_data: Dict) -> bool:
        """
        Save or update a generation session.

        Args:
            session_data: Dictionary with session fields

        Returns:
            True if saved successfully
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO generation_sessions
                    (session_id, club_name, status, created_at, updated_at,
                     completed_sections, pending_sections, partial_plan, metadata, error_log, owner_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    session_data['session_id'],
                    session_data['club_name'],
                    session_data['status'],
                    session_data['created_at'],
                    session_data['updated_at'],
                    json.dumps(session_data.get('completed_sections', [])),
                    json.dumps(session_data.get('pending_sections', [])),
                    json.dumps(session_data.get('partial_plan', {})),
                    json.dumps(session_data.get('metadata', {})),
                    json.dumps(session_data.get('error_log', [])),
                    session_data.get('owner_id')
                ))
                conn.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to save session: {e}")
            return False

    def get_generation_session(self, session_id: str) -> Optional[Dict]:
        """
        Retrieve a generation session by ID.

        Args:
            session_id: Session identifier

        Returns:
            Session data dict or None
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("""
                SELECT * FROM generation_sessions WHERE session_id = ?
            """, (session_id,)).fetchone()

            if not row:
                return None

            return {
                'session_id': row['session_id'],
                'club_name': row['club_name'],
                'status': row['status'],
                'created_at': row['created_at'],
                'updated_at': row['updated_at'],
                'completed_sections': json.loads(row['completed_sections'] or '[]'),
                'pending_sections': json.loads(row['pending_sections'] or '[]'),
                'partial_plan': json.loads(row['partial_plan'] or '{}'),
                'metadata': json.loads(row['metadata'] or '{}'),
                'error_log': json.loads(row['error_log'] or '[]'),
                'owner_id': row['owner_id']
            }

    def get_user_sessions(self, owner_id: int, status_filter: Optional[str] = None) -> List[Dict]:
        """
        Get all sessions for a user.

        Args:
            owner_id: User ID
            status_filter: Optional status to filter by

        Returns:
            List of session summary dicts
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            if status_filter:
                rows = conn.execute("""
                    SELECT session_id, club_name, status, created_at, updated_at
                    FROM generation_sessions
                    WHERE owner_id = ? AND status = ?
                    ORDER BY updated_at DESC
                """, (owner_id, status_filter)).fetchall()
            else:
                rows = conn.execute("""
                    SELECT session_id, club_name, status, created_at, updated_at
                    FROM generation_sessions
                    WHERE owner_id = ?
                    ORDER BY updated_at DESC
                """, (owner_id,)).fetchall()

            return [dict(row) for row in rows]

    def delete_expired_sessions(self, cutoff_time: str) -> int:
        """
        Delete sessions older than cutoff time.

        Args:
            cutoff_time: ISO format datetime string

        Returns:
            Number of sessions deleted
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                DELETE FROM generation_sessions
                WHERE updated_at < ? AND status IN ('completed', 'failed', 'cancelled')
            """, (cutoff_time,))
            conn.commit()
            return cursor.rowcount

    def delete_generation_session(self, session_id: str) -> bool:
        """
        Delete a specific session.

        Args:
            session_id: Session identifier

        Returns:
            True if deleted
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("DELETE FROM generation_sessions WHERE session_id = ?", (session_id,))
                conn.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to delete session {session_id}: {e}")
            return False

    # -------------------------------------------------------------------------
    # LICENSE MANAGEMENT (Admin Panel)
    # -------------------------------------------------------------------------

    def save_license_record(
        self,
        email: str,
        hwid: str,
        license_key: str,
        duration_days: int = None,
        notes: str = None
    ) -> int:
        """
        Salva un record di licenza generata nel database.
        Usato dall'admin per tracciare le licenze emesse.
        """
        from datetime import datetime, timedelta

        created_at = datetime.now().isoformat()
        expires_at = None
        if duration_days and duration_days > 0:
            expires_at = (datetime.now() + timedelta(days=duration_days)).isoformat()

        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    INSERT INTO licenses (email, hwid, license_key, duration_days, created_at, expires_at, status, notes)
                    VALUES (?, ?, ?, ?, ?, ?, 'active', ?)
                """, (email, hwid, license_key, duration_days, created_at, expires_at, notes))
                conn.commit()
                return cursor.lastrowid
        except Exception as e:
            logger.error(f"Failed to save license record: {e}")
            return None

    def list_licenses(self, status: str = None, limit: int = 100) -> list:
        """
        Lista tutte le licenze. Filtra per status se specificato.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                if status:
                    cursor = conn.execute(
                        "SELECT * FROM licenses WHERE status = ? ORDER BY created_at DESC LIMIT ?",
                        (status, limit)
                    )
                else:
                    cursor = conn.execute(
                        "SELECT * FROM licenses ORDER BY created_at DESC LIMIT ?",
                        (limit,)
                    )
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Failed to list licenses: {e}")
            return []

    def revoke_license(self, license_id: int) -> bool:
        """
        Revoca una licenza (imposta status='revoked').
        """
        from datetime import datetime
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "UPDATE licenses SET status = 'revoked', revoked_at = ? WHERE id = ?",
                    (datetime.now().isoformat(), license_id)
                )
                conn.commit()
            return True
        except Exception as e:
            logger.error(f"Failed to revoke license {license_id}: {e}")
            return False

    def get_license_stats(self) -> dict:
        """
        Statistiche sulle licenze per dashboard admin.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                total = conn.execute("SELECT COUNT(*) FROM licenses").fetchone()[0]
                active = conn.execute("SELECT COUNT(*) FROM licenses WHERE status = 'active'").fetchone()[0]
                revoked = conn.execute("SELECT COUNT(*) FROM licenses WHERE status = 'revoked'").fetchone()[0]
                # Licenze in scadenza nei prossimi 30 giorni
                from datetime import datetime, timedelta
                soon = (datetime.now() + timedelta(days=30)).isoformat()
                expiring = conn.execute(
                    "SELECT COUNT(*) FROM licenses WHERE status = 'active' AND expires_at IS NOT NULL AND expires_at < ?",
                    (soon,)
                ).fetchone()[0]
                return {
                    "total": total,
                    "active": active,
                    "revoked": revoked,
                    "expiring_soon": expiring
                }
        except Exception as e:
            logger.error(f"Failed to get license stats: {e}")
            return {"total": 0, "active": 0, "revoked": 0, "expiring_soon": 0}
