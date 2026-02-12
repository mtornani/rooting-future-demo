# FEAT-008: Public Plan Sharing

## Obiettivo
Permettere la condivisione sicura della webapp del piano strategico con clienti esterni senza richiedere login.

## Problema
Attualmente la route `/view/<plan_id>` richiede autenticazione (@login_required), rendendo impossibile condividere il piano con stakeholder esterni (presidenti, investitori, sponsor).

## Soluzione

### 1. Public Share System
Sistema di condivisione pubblica con token sicuri e scadenza configurabile.

### 2. Database Schema
Aggiungere tabella `public_shares` in `knowledge_store.py`:

```sql
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
```

### 3. Share Manager Class
Creare `utils/share_manager.py`:

```python
"""
Public Plan Sharing Manager
Gestisce la creazione e validazione di link pubblici
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
        if share['password_hash'] and password:
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
```

### 4. Routes in app.py

```python
# ============================================================
# FEAT-008: Public Plan Sharing
# ============================================================

from utils.share_manager import ShareManager

# Initialize share manager
share_manager = ShareManager(db_path=os.path.join(basedir, "strategic_plans.db"))

@app.route("/share/<plan_id>", methods=["POST"])
@login_required
def create_plan_share(plan_id):
    """
    Crea un link di condivisione pubblico per il piano.
    POST /share/<plan_id>
    Body: {expires_days: 30, password: "optional", allow_download: false}
    """
    # Verifica autorizzazione
    plan_record = knowledge_manager.store.get_plan(plan_id)
    if not plan_record:
        return jsonify({"error": "Plan not found"}), 404

    if current_user.role != "super_admin":
        if plan_record.owner_id != int(current_user.id):
            return jsonify({"error": "Unauthorized"}), 403

    # Parametri
    data = request.get_json() or {}
    expires_days = data.get("expires_days", 30)
    password = data.get("password")
    allow_download = data.get("allow_download", False)

    # Crea share
    share_token = share_manager.create_share(
        plan_id=plan_id,
        created_by=int(current_user.id),
        expires_days=expires_days,
        password=password,
        allow_download=allow_download
    )

    share_url = url_for('view_public_plan', share_token=share_token, _external=True)

    return jsonify({
        "success": True,
        "share_token": share_token,
        "share_url": share_url,
        "expires_days": expires_days
    })


@app.route("/public/<share_token>")
def view_public_plan(share_token):
    """
    Visualizza piano tramite link pubblico (NO LOGIN REQUIRED).
    Route: /public/<share_token>
    """
    logger.info(f"[PUBLIC SHARE] Accessing public plan with token: {share_token}")

    # Valida token
    share = share_manager.validate_share(share_token)

    if not share:
        return render_template("share_invalid.html"), 404

    # Recupera piano
    plan_record = knowledge_manager.store.get_plan(share['plan_id'])

    if not plan_record:
        logger.error(f"[PUBLIC SHARE] Plan {share['plan_id']} not found")
        return render_template("share_invalid.html"), 404

    # Format contenuti (UX-001)
    from utils.content_formatter import ContentFormatter
    formatter = ContentFormatter()
    formatted_plan = {}

    for section_key, content in plan_record.plan_data.items():
        if isinstance(content, str):
            formatted_plan[section_key] = formatter.format_section_content(content)
        else:
            formatted_plan[section_key] = content

    # Metadata
    metadata = {
        "category": plan_record.category,
        "primary_color": "#1a365d",
        "secondary_color": "#ffffff",
        "is_public_share": True,
        "allow_download": bool(share['allow_download']),
        "view_count": share['view_count']
    }

    return render_template(
        "public_plan_viewer.html",  # Template pubblico
        plan=formatted_plan,
        plan_id=share['plan_id'],
        club_name=plan_record.club_name,
        category=plan_record.category,
        metadata=metadata,
        share_token=share_token
    )


@app.route("/api/shares/<plan_id>")
@login_required
def get_plan_shares(plan_id):
    """Ottiene lista shares attivi per un piano"""
    shares = share_manager.get_plan_shares(plan_id, int(current_user.id))

    # Format dates
    for share in shares:
        share['share_url'] = url_for('view_public_plan', share_token=share['share_token'], _external=True)

    return jsonify({"shares": shares})


@app.route("/api/shares/<share_token>/revoke", methods=["POST"])
@login_required
def revoke_plan_share(share_token):
    """Revoca un link di condivisione"""
    success = share_manager.revoke_share(share_token, int(current_user.id))

    if success:
        return jsonify({"success": True})
    else:
        return jsonify({"error": "Share not found or unauthorized"}), 404
```

### 5. Template pubblico
Creare `templates/public_plan_viewer.html` (clone di strategic_plan_viewer.html ma senza sidebar actions per share/edit, e con watermark "Condiviso da Rooting Future")

### 6. UI per Share Management
Aggiungere nella webapp `/view/<plan_id>` un bottone "Condividi Piano" nella sidebar che apre modal:

```html
<!-- Share Modal -->
<div id="shareModal" class="modal-overlay" style="display: none;">
    <div class="modal-content">
        <h3>Condividi Piano Strategico</h3>
        <form id="shareForm">
            <label>Scadenza</label>
            <select name="expires_days">
                <option value="7">7 giorni</option>
                <option value="30" selected>30 giorni</option>
                <option value="90">90 giorni</option>
                <option value="365">1 anno</option>
            </select>

            <label>Password (opzionale)</label>
            <input type="password" name="password" placeholder="Lascia vuoto per nessuna password">

            <label>
                <input type="checkbox" name="allow_download">
                Permetti download PDF/DOCX
            </label>

            <button type="submit" class="btn btn-primary">Genera Link</button>
        </form>

        <div id="shareResult" style="display: none;">
            <p>Link generato con successo!</p>
            <input type="text" id="shareUrl" readonly>
            <button onclick="copyShareUrl()">Copia Link</button>
        </div>
    </div>
</div>
```

## Implementation Steps

1. **Create ShareManager** (utils/share_manager.py) - +220 LOC
2. **Add routes** (app.py) - +120 LOC
3. **Create public template** (templates/public_plan_viewer.html) - +210 LOC
4. **Create share invalid template** (templates/share_invalid.html) - +40 LOC
5. **Add share UI to viewer** (strategic_plan_viewer.html + JS) - +80 LOC
6. **CSS for share modal** (plan_viewer.css) - +60 LOC

## Benefits
- ✅ Condivisione sicura con clienti esterni
- ✅ Scadenza automatica (7/30/90/365 giorni)
- ✅ Password opzionale per protezione extra
- ✅ Tracking views (analytics)
- ✅ Revoca istantanea
- ✅ No login richiesto per cliente
- ✅ Professional user experience

## Expected LOC
- utils/share_manager.py: +220 LOC (new)
- app.py: +120 LOC (routes)
- templates/public_plan_viewer.html: +210 LOC (new)
- templates/share_invalid.html: +40 LOC (new)
- strategic_plan_viewer.html: +80 LOC (share UI)
- static/css/plan_viewer.css: +60 LOC (modal)
- static/js/plan_viewer.js: +100 LOC (share logic)
- Total: +830 LOC

## Security
- UUID tokens (impossibili da indovinare)
- Scadenza automatica
- Password hashing (SHA-256)
- Revoca manuale disponibile
- Tracking accessi per audit
- Rate limiting su route pubbliche (TODO)

## Testing
1. Create share link → verify token generato
2. Access public link → verify no login required
3. Access expired link → verify 404
4. Access with wrong password → verify denied
5. Revoke link → verify 404
6. Test view counter → verify incremento
7. Test download permissions → verify rispettati
