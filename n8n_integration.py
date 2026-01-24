"""
n8n Integration Module
======================

Infrastruttura per collegare n8n con Rooting Future.
Gestisce:
1. Ricezione questionari da n8n
2. Autenticazione multi-tenant
3. Webhook per trigger generazione piani
4. Callback per notifiche stato

Configurazione n8n: http://localhost:5678
App Flask: http://localhost:5000
"""

import os
import json
import hmac
import hashlib
import secrets
from datetime import datetime, timedelta
from functools import wraps
from typing import Dict, Optional, List, Any
import logging

import jwt
from flask import request, jsonify, g

logger = logging.getLogger(__name__)

# =============================================================================
# CONFIGURAZIONE
# =============================================================================

# Chiavi sicurezza (in produzione usare variabili ambiente)
N8N_WEBHOOK_SECRET = os.environ.get('N8N_WEBHOOK_SECRET', 'n8n-rooting-future-secret-change-me')
JWT_SECRET = os.environ.get('JWT_SECRET', 'jwt-rooting-future-secret-change-me')
JWT_EXPIRY_HOURS = 24
JWT_REFRESH_DAYS = 7

# Storage temporaneo (in produzione usare database)
# Struttura: {club_id: {data}}
_clubs_store: Dict[str, Dict] = {}
_users_store: Dict[str, Dict] = {}
_questionnaires_store: Dict[str, Dict] = {}
_sessions_store: Dict[str, Dict] = {}


# =============================================================================
# UTILITIES
# =============================================================================

def generate_id() -> str:
    """Genera ID univoco."""
    return secrets.token_hex(16)


def hash_password(password: str) -> str:
    """Hash password con salt."""
    salt = secrets.token_hex(16)
    hashed = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
    return f"{salt}:{hashed.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    """Verifica password."""
    try:
        salt, hashed = stored_hash.split(':')
        new_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
        return new_hash.hex() == hashed
    except:
        return False


def verify_n8n_signature(payload: bytes, signature: str) -> bool:
    """Verifica firma webhook n8n."""
    expected = hmac.new(
        N8N_WEBHOOK_SECRET.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


# =============================================================================
# JWT AUTHENTICATION
# =============================================================================

def create_access_token(user_id: str, club_id: str, role: str) -> str:
    """Crea JWT access token."""
    payload = {
        'user_id': user_id,
        'club_id': club_id,
        'role': role,
        'type': 'access',
        'exp': datetime.utcnow() + timedelta(hours=JWT_EXPIRY_HOURS),
        'iat': datetime.utcnow()
    }
    return jwt.encode(payload, JWT_SECRET, algorithm='HS256')


def create_refresh_token(user_id: str) -> str:
    """Crea JWT refresh token."""
    payload = {
        'user_id': user_id,
        'type': 'refresh',
        'exp': datetime.utcnow() + timedelta(days=JWT_REFRESH_DAYS),
        'iat': datetime.utcnow()
    }
    return jwt.encode(payload, JWT_SECRET, algorithm='HS256')


def decode_token(token: str) -> Optional[Dict]:
    """Decodifica e valida JWT."""
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


# =============================================================================
# DECORATORS
# =============================================================================

def require_auth(f):
    """Decorator: richiede autenticazione JWT."""
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization')

        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'success': False, 'error': 'Token mancante'}), 401

        token = auth_header.split(' ')[1]
        payload = decode_token(token)

        if not payload:
            return jsonify({'success': False, 'error': 'Token invalido o scaduto'}), 401

        if payload.get('type') != 'access':
            return jsonify({'success': False, 'error': 'Token type invalido'}), 401

        # Aggiungi user info al contesto
        g.user_id = payload['user_id']
        g.club_id = payload['club_id']
        g.role = payload['role']

        return f(*args, **kwargs)
    return decorated


def require_role(*allowed_roles):
    """Decorator: richiede ruolo specifico."""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if not hasattr(g, 'role'):
                return jsonify({'success': False, 'error': 'Non autenticato'}), 401

            if g.role not in allowed_roles:
                return jsonify({'success': False, 'error': 'Permessi insufficienti'}), 403

            return f(*args, **kwargs)
        return decorated
    return decorator


def require_n8n_signature(f):
    """Decorator: verifica firma webhook n8n."""
    @wraps(f)
    def decorated(*args, **kwargs):
        signature = request.headers.get('X-N8N-Signature')

        # In sviluppo, permetti richieste senza firma
        if not signature and os.environ.get('FLASK_ENV') == 'development':
            logger.warning("n8n signature check skipped (development mode)")
            return f(*args, **kwargs)

        if not signature:
            return jsonify({'success': False, 'error': 'Firma mancante'}), 401

        if not verify_n8n_signature(request.data, signature):
            return jsonify({'success': False, 'error': 'Firma invalida'}), 401

        return f(*args, **kwargs)
    return decorated


# =============================================================================
# CLUB & USER MANAGEMENT (in-memory, sostituire con DB)
# =============================================================================

def create_club(name: str, category: str, colors: Dict = None) -> Dict:
    """Crea nuovo club."""
    club_id = generate_id()
    club = {
        'id': club_id,
        'name': name,
        'category': category,
        'colors': colors or {'primary': '#1a365d', 'secondary': '#ffffff'},
        'created_at': datetime.utcnow().isoformat(),
        'active': True
    }
    _clubs_store[club_id] = club
    return club


def get_club(club_id: str) -> Optional[Dict]:
    """Ottieni club per ID."""
    return _clubs_store.get(club_id)


def create_user(email: str, password: str, role: str, club_id: str = None) -> Dict:
    """Crea nuovo utente."""
    user_id = generate_id()
    user = {
        'id': user_id,
        'email': email.lower(),
        'password_hash': hash_password(password),
        'role': role,  # 'super_admin', 'club_admin', 'club_staff', 'viewer'
        'club_id': club_id,
        'created_at': datetime.utcnow().isoformat(),
        'active': True
    }
    _users_store[user_id] = user
    return {k: v for k, v in user.items() if k != 'password_hash'}


def get_user_by_email(email: str) -> Optional[Dict]:
    """Trova utente per email."""
    email = email.lower()
    for user in _users_store.values():
        if user['email'] == email:
            return user
    return None


def authenticate_user(email: str, password: str) -> Optional[Dict]:
    """Autentica utente."""
    user = get_user_by_email(email)
    if not user:
        return None
    if not user['active']:
        return None
    if not verify_password(password, user['password_hash']):
        return None
    return {k: v for k, v in user.items() if k != 'password_hash'}


# =============================================================================
# QUESTIONNAIRE MANAGEMENT
# =============================================================================

def save_questionnaire(club_id: str, data: Dict, status: str = 'submitted') -> Dict:
    """Salva questionario."""
    q_id = generate_id()
    questionnaire = {
        'id': q_id,
        'club_id': club_id,
        'data': data,
        'status': status,  # 'draft', 'submitted', 'processing', 'completed'
        'created_at': datetime.utcnow().isoformat(),
        'updated_at': datetime.utcnow().isoformat()
    }
    _questionnaires_store[q_id] = questionnaire
    return questionnaire


def get_questionnaire(q_id: str) -> Optional[Dict]:
    """Ottieni questionario."""
    return _questionnaires_store.get(q_id)


def get_club_questionnaires(club_id: str) -> List[Dict]:
    """Ottieni tutti i questionari di un club."""
    return [q for q in _questionnaires_store.values() if q['club_id'] == club_id]


def update_questionnaire_status(q_id: str, status: str) -> Optional[Dict]:
    """Aggiorna stato questionario."""
    if q_id in _questionnaires_store:
        _questionnaires_store[q_id]['status'] = status
        _questionnaires_store[q_id]['updated_at'] = datetime.utcnow().isoformat()
        return _questionnaires_store[q_id]
    return None


# =============================================================================
# FLASK ROUTES - Da registrare in app.py
# =============================================================================

def register_n8n_routes(app):
    """
    Registra tutte le routes n8n nell'app Flask.

    Chiamare in app.py:
        from n8n_integration import register_n8n_routes
        register_n8n_routes(app)
    """

    # =========================================================================
    # WEBHOOK: Ricezione Questionario da n8n
    # =========================================================================

    @app.route('/api/n8n/questionnaire', methods=['POST'])
    @require_n8n_signature
    def n8n_receive_questionnaire():
        """
        Riceve questionario da n8n.

        n8n Workflow:
        1. Google Forms/Tally submit → Webhook
        2. n8n trasforma dati → POST qui
        3. Questo endpoint salva e triggera generazione

        Payload atteso:
        {
            "club_id": "xxx",  // Opzionale se nuovo club
            "club_name": "AC Example",
            "category": "Serie B",
            "questionnaire_data": {
                "section_anagrafica": {...},
                "section_sportiva": {...},
                "section_infrastrutture": {...},
                "section_finanze": {...},
                "section_marketing": {...},
                "section_obiettivi": {...}
            }
        }
        """
        try:
            data = request.get_json()

            if not data:
                return jsonify({'success': False, 'error': 'Payload vuoto'}), 400

            club_id = data.get('club_id')
            club_name = data.get('club_name')
            category = data.get('category', 'Serie D')
            questionnaire_data = data.get('questionnaire_data', {})

            # Se club_id non fornito, crea nuovo club
            if not club_id:
                if not club_name:
                    return jsonify({'success': False, 'error': 'club_name richiesto per nuovo club'}), 400
                club = create_club(club_name, category)
                club_id = club['id']

            # Salva questionario
            questionnaire = save_questionnaire(club_id, questionnaire_data, 'submitted')

            # Ritorna info per n8n (può triggerare step successivi)
            return jsonify({
                'success': True,
                'questionnaire_id': questionnaire['id'],
                'club_id': club_id,
                'status': 'submitted',
                'message': 'Questionario ricevuto, pronto per generazione piano',
                'next_step': f'/api/n8n/generate/{questionnaire["id"]}'
            })

        except Exception as e:
            logger.exception(f"Errore ricezione questionario: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500


    @app.route('/api/n8n/generate/<questionnaire_id>', methods=['POST'])
    @require_n8n_signature
    def n8n_trigger_generation(questionnaire_id):
        """
        Triggera generazione piano da questionario.

        Chiamato da n8n dopo conferma/validazione questionario.
        """
        try:
            questionnaire = get_questionnaire(questionnaire_id)

            if not questionnaire:
                return jsonify({'success': False, 'error': 'Questionario non trovato'}), 404

            # Aggiorna stato
            update_questionnaire_status(questionnaire_id, 'processing')

            club = get_club(questionnaire['club_id'])

            # Prepara dati per generazione (mapping da questionario a formato app)
            generation_params = {
                'club_name': club['name'] if club else 'Club',
                'category': club['category'] if club else 'Serie D',
                'questionnaire_data': questionnaire['data'],
                'source': 'n8n_questionnaire',
                'questionnaire_id': questionnaire_id
            }

            # Ritorna i parametri - n8n può chiamare /api/generate con questi
            return jsonify({
                'success': True,
                'status': 'ready_for_generation',
                'generation_params': generation_params,
                'generate_endpoint': '/api/generate'
            })

        except Exception as e:
            logger.exception(f"Errore trigger generazione: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500


    @app.route('/api/n8n/status/<questionnaire_id>', methods=['GET'])
    def n8n_get_status(questionnaire_id):
        """
        Ottieni stato questionario/generazione.

        n8n può fare polling qui per aggiornamenti.
        """
        questionnaire = get_questionnaire(questionnaire_id)

        if not questionnaire:
            return jsonify({'success': False, 'error': 'Non trovato'}), 404

        return jsonify({
            'success': True,
            'questionnaire_id': questionnaire_id,
            'status': questionnaire['status'],
            'updated_at': questionnaire['updated_at']
        })


    @app.route('/api/n8n/callback', methods=['POST'])
    @require_n8n_signature
    def n8n_callback():
        """
        Callback generico da n8n.

        Usato per notifiche, aggiornamenti stato, etc.
        """
        try:
            data = request.get_json()
            event_type = data.get('event')
            payload = data.get('payload', {})

            logger.info(f"n8n callback: {event_type} - {payload}")

            # Gestisci diversi tipi di evento
            if event_type == 'questionnaire_validated':
                q_id = payload.get('questionnaire_id')
                if q_id:
                    update_questionnaire_status(q_id, 'validated')

            elif event_type == 'generation_completed':
                q_id = payload.get('questionnaire_id')
                if q_id:
                    update_questionnaire_status(q_id, 'completed')

            elif event_type == 'notification_sent':
                # Log notifica inviata
                pass

            return jsonify({'success': True, 'received': event_type})

        except Exception as e:
            logger.exception(f"Errore callback: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500


    # =========================================================================
    # AUTH: Registrazione e Login
    # =========================================================================

    @app.route('/api/auth/register', methods=['POST'])
    def auth_register():
        """
        Registra nuovo club + admin.

        Payload:
        {
            "club_name": "AC Example",
            "category": "Serie B",
            "admin_email": "admin@example.com",
            "admin_password": "securepassword",
            "colors": {"primary": "#ff0000", "secondary": "#ffffff"}
        }
        """
        try:
            data = request.get_json()

            club_name = data.get('club_name')
            category = data.get('category', 'Serie D')
            admin_email = data.get('admin_email')
            admin_password = data.get('admin_password')
            colors = data.get('colors')

            if not all([club_name, admin_email, admin_password]):
                return jsonify({'success': False, 'error': 'Campi obbligatori mancanti'}), 400

            # Verifica email non già usata
            if get_user_by_email(admin_email):
                return jsonify({'success': False, 'error': 'Email già registrata'}), 400

            # Crea club
            club = create_club(club_name, category, colors)

            # Crea admin
            user = create_user(admin_email, admin_password, 'club_admin', club['id'])

            # Genera tokens
            access_token = create_access_token(user['id'], club['id'], 'club_admin')
            refresh_token = create_refresh_token(user['id'])

            return jsonify({
                'success': True,
                'club': club,
                'user': user,
                'access_token': access_token,
                'refresh_token': refresh_token
            })

        except Exception as e:
            logger.exception(f"Errore registrazione: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500


    @app.route('/api/auth/login', methods=['POST'])
    def auth_login():
        """
        Login utente.

        Payload:
        {
            "email": "admin@example.com",
            "password": "securepassword"
        }
        """
        try:
            data = request.get_json()

            email = data.get('email')
            password = data.get('password')

            if not email or not password:
                return jsonify({'success': False, 'error': 'Email e password richiesti'}), 400

            user = authenticate_user(email, password)

            if not user:
                return jsonify({'success': False, 'error': 'Credenziali non valide'}), 401

            club = get_club(user['club_id']) if user['club_id'] else None

            access_token = create_access_token(user['id'], user['club_id'] or '', user['role'])
            refresh_token = create_refresh_token(user['id'])

            return jsonify({
                'success': True,
                'user': user,
                'club': club,
                'access_token': access_token,
                'refresh_token': refresh_token
            })

        except Exception as e:
            logger.exception(f"Errore login: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500


    @app.route('/api/auth/refresh', methods=['POST'])
    def auth_refresh():
        """
        Refresh access token.

        Payload:
        {
            "refresh_token": "xxx"
        }
        """
        try:
            data = request.get_json()
            refresh_token = data.get('refresh_token')

            if not refresh_token:
                return jsonify({'success': False, 'error': 'Refresh token richiesto'}), 400

            payload = decode_token(refresh_token)

            if not payload or payload.get('type') != 'refresh':
                return jsonify({'success': False, 'error': 'Token invalido'}), 401

            user_id = payload['user_id']
            user = _users_store.get(user_id)

            if not user:
                return jsonify({'success': False, 'error': 'Utente non trovato'}), 401

            access_token = create_access_token(user['id'], user['club_id'] or '', user['role'])

            return jsonify({
                'success': True,
                'access_token': access_token
            })

        except Exception as e:
            logger.exception(f"Errore refresh: {e}")
            return jsonify({'success': False, 'error': str(e)}), 500


    @app.route('/api/auth/me', methods=['GET'])
    @require_auth
    def auth_me():
        """Ottieni info utente corrente."""
        user = _users_store.get(g.user_id)
        club = get_club(g.club_id) if g.club_id else None

        return jsonify({
            'success': True,
            'user': {k: v for k, v in user.items() if k != 'password_hash'} if user else None,
            'club': club
        })


    # =========================================================================
    # PROTECTED ROUTES (esempi)
    # =========================================================================

    @app.route('/api/club/questionnaires', methods=['GET'])
    @require_auth
    def get_my_questionnaires():
        """Ottieni questionari del proprio club."""
        if g.role == 'super_admin':
            # Super admin vede tutto
            questionnaires = list(_questionnaires_store.values())
        else:
            # Altri vedono solo il proprio club
            questionnaires = get_club_questionnaires(g.club_id)

        return jsonify({
            'success': True,
            'questionnaires': questionnaires
        })


    @app.route('/api/n8n/admin/clubs', methods=['GET'])
    @require_auth
    @require_role('super_admin')
    def n8n_admin_list_clubs():
        """Lista tutti i club (solo super admin)."""
        return jsonify({
            'success': True,
            'clubs': list(_clubs_store.values())
        })


    @app.route('/api/n8n/admin/users', methods=['GET'])
    @require_auth
    @require_role('super_admin')
    def n8n_admin_list_users():
        """Lista tutti gli utenti (solo super admin)."""
        users = [{k: v for k, v in u.items() if k != 'password_hash'} for u in _users_store.values()]
        return jsonify({
            'success': True,
            'users': users
        })


    logger.info("n8n routes registered successfully")


# =============================================================================
# SCHEMA QUESTIONARIO (per n8n/frontend)
# =============================================================================

QUESTIONNAIRE_SCHEMA = {
    "version": "1.0",
    "sections": [
        {
            "id": "anagrafica",
            "title": "Anagrafica Club",
            "fields": [
                {"id": "nome_ufficiale", "label": "Nome Ufficiale", "type": "text", "required": True},
                {"id": "anno_fondazione", "label": "Anno Fondazione", "type": "number"},
                {"id": "categoria", "label": "Categoria", "type": "select", "options": ["Serie A", "Serie B", "Serie C", "Serie D", "Eccellenza", "Promozione"]},
                {"id": "regione", "label": "Regione", "type": "text"},
                {"id": "citta", "label": "Città", "type": "text"},
                {"id": "colori_sociali", "label": "Colori Sociali", "type": "text"},
            ]
        },
        {
            "id": "sportiva",
            "title": "Area Sportiva",
            "fields": [
                {"id": "dimensione_rosa", "label": "Dimensione Rosa Prima Squadra", "type": "number"},
                {"id": "eta_media", "label": "Età Media Rosa", "type": "number"},
                {"id": "settore_giovanile", "label": "Settore Giovanile Attivo", "type": "boolean"},
                {"id": "categorie_giovanili", "label": "Categorie Giovanili (es: Primavera, U17, U15)", "type": "text"},
                {"id": "staff_tecnico", "label": "Numero Staff Tecnico", "type": "number"},
            ]
        },
        {
            "id": "infrastrutture",
            "title": "Infrastrutture",
            "fields": [
                {"id": "nome_stadio", "label": "Nome Stadio", "type": "text"},
                {"id": "capienza_stadio", "label": "Capienza Stadio", "type": "number"},
                {"id": "proprieta_stadio", "label": "Proprietà Stadio", "type": "select", "options": ["Proprietà", "Concessione", "Affitto"]},
                {"id": "centro_sportivo", "label": "Centro Sportivo Dedicato", "type": "boolean"},
                {"id": "numero_campi", "label": "Numero Campi Allenamento", "type": "number"},
            ]
        },
        {
            "id": "finanze",
            "title": "Dati Finanziari",
            "fields": [
                {"id": "fatturato_annuo", "label": "Fatturato Annuo (€)", "type": "number"},
                {"id": "monte_ingaggi", "label": "Monte Ingaggi (€)", "type": "number"},
                {"id": "debiti", "label": "Debiti Totali (€)", "type": "number"},
                {"id": "sponsor_principale", "label": "Sponsor Principale", "type": "text"},
                {"id": "ricavi_stadio", "label": "Ricavi da Stadio (€)", "type": "number"},
            ]
        },
        {
            "id": "marketing",
            "title": "Marketing e Tifoseria",
            "fields": [
                {"id": "abbonati", "label": "Numero Abbonati", "type": "number"},
                {"id": "media_spettatori", "label": "Media Spettatori Casa", "type": "number"},
                {"id": "follower_social", "label": "Follower Social Totali", "type": "number"},
                {"id": "merchandising", "label": "Ricavi Merchandising (€)", "type": "number"},
            ]
        },
        {
            "id": "obiettivi",
            "title": "Obiettivi Strategici",
            "fields": [
                {"id": "obiettivo_sportivo_1y", "label": "Obiettivo Sportivo Anno 1", "type": "text"},
                {"id": "obiettivo_sportivo_3y", "label": "Obiettivo Sportivo Anno 3", "type": "text"},
                {"id": "priorita_investimento", "label": "Priorità Investimento", "type": "select", "options": ["Stadio", "Settore Giovanile", "Prima Squadra", "Marketing", "Infrastrutture"]},
                {"id": "sfide_principali", "label": "Sfide Principali (descrizione)", "type": "textarea"},
            ]
        }
    ]
}


def get_questionnaire_schema():
    """Ritorna schema questionario."""
    return QUESTIONNAIRE_SCHEMA
