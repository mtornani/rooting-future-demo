"""
Rooting Future - Public Plan Sharing Manager v1.0
Gestisce la creazione e validazione di link pubblici per condivisione piani strategici
"""

import uuid
import sqlite3
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import hashlib
import logging

logger = logging.getLogger(__name__)


class ShareManager:
    """Gestisce condivisione pubblica dei piani strategici"""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Crea tabella public_shares se non esiste"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS public_shares (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                share_token TEXT UNIQUE NOT NULL,
                plan_id TEXT NOT NULL,
                created_by INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL,
                is_active INTEGER DEFAULT 1,
                view_count INTEGER DEFAULT 0,
                last_viewed_at TIMESTAMP,
                password_hash TEXT,
                allow_download INTEGER DEFAULT 0,
                FOREIGN KEY(plan_id) REFERENCES strategic_plans(plan_id),
                FOREIGN KEY(created_by) REFERENCES users(id)
            )
        """)

        # Index per performance
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_share_token
            ON public_shares(share_token)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_plan_id_active
            ON public_shares(plan_id, is_active)
        """)

        conn.commit()
        conn.close()
        logger.info("[SHARE MANAGER] Database initialized")

    def create_share(
        self,
        plan_id: str,
        created_by: int,
        expires_days: int = 30,
        password: Optional[str] = None,
        allow_download: bool = False
    ) -> str:
        """
        Crea un link di condivisione pubblico.

        Args:
            plan_id: ID del piano da condividere
            created_by: User ID del creatore
            expires_days: Giorni prima della scadenza (default 30)
            password: Password opzionale per proteggere l'accesso
            allow_download: Permetti download PDF/DOCX (default False)

        Returns:
            share_token: Token univoco per l'accesso pubblico
        """
        share_token = str(uuid.uuid4())
        expires_at = datetime.now() + timedelta(days=expires_days)

        password_hash = None
        if password:
            password_hash = hashlib.sha256(password.encode()).hexdigest()

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO public_shares
            (share_token, plan_id, created_by, expires_at, password_hash, allow_download)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (share_token, plan_id, created_by, expires_at, password_hash, int(allow_download)))

        conn.commit()
        conn.close()

        logger.info(f"[SHARE MANAGER] Created share token for plan {plan_id}, expires {expires_at}")
        return share_token

    def validate_share(self, share_token: str, password: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Valida un token di condivisione.

        Returns:
            Dict con info share se valido, None se invalido/scaduto
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM public_shares
            WHERE share_token = ? AND is_active = 1
        """, (share_token,))

        row = cursor.fetchone()

        if not row:
            conn.close()
            logger.warning(f"[SHARE MANAGER] Invalid token: {share_token}")
            return None

        share = dict(row)

        # Check scadenza
        expires_at = datetime.fromisoformat(share['expires_at'])
        if datetime.now() > expires_at:
            conn.close()
            logger.warning(f"[SHARE MANAGER] Expired token: {share_token}")
            return None

        # Check password se presente
        if share['password_hash']:
            if not password:
                # Password richiesta ma non fornita
                share['requires_password'] = True
                conn.close()
                return share

            password_hash = hashlib.sha256(password.encode()).hexdigest()
            if password_hash != share['password_hash']:
                conn.close()
                logger.warning(f"[SHARE MANAGER] Wrong password for token: {share_token}")
                return None

        # Incrementa view count
        cursor.execute("""
            UPDATE public_shares
            SET view_count = view_count + 1,
                last_viewed_at = CURRENT_TIMESTAMP
            WHERE share_token = ?
        """, (share_token,))

        conn.commit()
        conn.close()

        logger.info(f"[SHARE MANAGER] Validated token {share_token}, views: {share['view_count'] + 1}")
        return share

    def revoke_share(self, share_token: str, user_id: int) -> bool:
        """Revoca un link di condivisione"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE public_shares
            SET is_active = 0
            WHERE share_token = ? AND created_by = ?
        """, (share_token, user_id))

        revoked = cursor.rowcount > 0
        conn.commit()
        conn.close()

        if revoked:
            logger.info(f"[SHARE MANAGER] Revoked share token: {share_token}")
        return revoked

    def get_plan_shares(self, plan_id: str, user_id: int) -> list:
        """Ottiene tutti i link attivi per un piano"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM public_shares
            WHERE plan_id = ? AND created_by = ? AND is_active = 1
            ORDER BY created_at DESC
        """, (plan_id, user_id))

        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def cleanup_expired(self) -> int:
        """Rimuove share scaduti (cron job)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE public_shares
            SET is_active = 0
            WHERE is_active = 1 AND expires_at < CURRENT_TIMESTAMP
        """)

        cleaned = cursor.rowcount
        conn.commit()
        conn.close()

        if cleaned > 0:
            logger.info(f"[SHARE MANAGER] Cleaned {cleaned} expired shares")
        return cleaned
