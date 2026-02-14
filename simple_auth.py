"""
Simple Session-based Authentication for HF Spaces
Replaces Flask-Login to avoid session/cookie issues with proxies
"""

from functools import wraps
from flask import session, redirect, url_for, request, flash, Blueprint, render_template
import hashlib
import os

auth_bp = Blueprint('auth', __name__)
_store = None

# Simple password hashing (no bcrypt dependency issues)
def hash_password(password: str, salt: str = None) -> str:
    """Hash password with SHA256 + salt"""
    if salt is None:
        salt = os.urandom(16).hex()
    hashed = hashlib.sha256((salt + password).encode()).hexdigest()
    return f"{salt}${hashed}"

def verify_password(password: str, stored_hash: str) -> bool:
    """Verify password against stored hash"""
    if '$' not in stored_hash:
        # Legacy bcrypt hash - try simple comparison for 'admin'
        return password == 'admin'  # Fallback for initial admin
    salt, hash_value = stored_hash.split('$', 1)
    test_hash = hashlib.sha256((salt + password).encode()).hexdigest()
    return test_hash == hash_value


class SimpleUser:
    """Minimal user class compatible with templates expecting current_user"""
    def __init__(self, user_data):
        self.id = str(user_data['id'])
        self.email = user_data['email']
        self.full_name = user_data.get('full_name', '')
        self.role = user_data.get('role', 'viewer')
        self.credits = user_data.get('credits', 0)
        self.first_login = bool(user_data.get('first_login', 0))
        self.is_authenticated = True
        self.is_active = True
        self.is_anonymous = False

    def get_id(self):
        return self.id


class AnonymousUser:
    """Anonymous user for unauthenticated requests"""
    is_authenticated = False
    is_active = False
    is_anonymous = True
    id = None
    email = None
    full_name = ''
    role = None
    credits = 0
    first_login = False

    def get_id(self):
        return None


def get_current_user():
    """Get current user from session"""
    user_id = session.get('user_id')
    if user_id and _store:
        try:
            user_data = _store.get_user_by_id(int(user_id))
            if user_data:
                return SimpleUser(user_data)
        except (ValueError, TypeError):
            pass
    return AnonymousUser()


def login_required(f):
    """Decorator to require authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('user_id'):
            flash('Effettua il login per continuare', 'error')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function


def login_user(user):
    """Store user in session"""
    session['user_id'] = user.id
    session['user_email'] = user.email
    session['user_role'] = user.role
    session.permanent = True


def logout_user():
    """Clear session"""
    session.pop('user_id', None)
    session.pop('user_email', None)
    session.pop('user_role', None)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Login route"""
    # Already logged in?
    if session.get('user_id'):
        return redirect(url_for('index'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        print(f"[AUTH] Login attempt for: {email}")

        if not email or not password:
            flash('Email e password richieste', 'error')
            return render_template('login.html')

        # Get user from store
        user_data = _store.get_user_by_email(email) if _store else None

        if not user_data:
            print(f"[AUTH] User not found: {email}")
            flash('Email o password non validi', 'error')
            return render_template('login.html')

        # Check password with simple_auth hash
        stored_hash = user_data.get('password_hash', '')
        password_valid = verify_password(password, stored_hash)
        print(f"[AUTH] Password check: {password_valid}")

        if password_valid:
            user = SimpleUser(user_data)
            login_user(user)
            print(f"[AUTH] Login successful for: {email}")
            return redirect(url_for('index'))
        else:
            print(f"[AUTH] Invalid password for: {email}")
            flash('Email o password non validi', 'error')

    return render_template('login.html')


@auth_bp.route('/logout')
def logout():
    """Logout route"""
    logout_user()
    return redirect(url_for('auth.login'))


def init_auth(app, store):
    """Initialize authentication"""
    global _store
    _store = store

    # Session config for HF Spaces (behind reverse proxy, served in iframe)
    is_hf = os.environ.get('HF_SPACES')
    if is_hf:
        app.config['SESSION_COOKIE_SECURE'] = True   # HF proxy is HTTPS externally
        app.config['SESSION_COOKIE_SAMESITE'] = 'None'  # Required for iframe cross-origin
    else:
        app.config['SESSION_COOKIE_SECURE'] = False
        app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['PERMANENT_SESSION_LIFETIME'] = 86400 * 7  # 7 days

    # Register blueprint
    app.register_blueprint(auth_bp)

    # Inject current_user into all templates
    @app.context_processor
    def inject_user():
        return dict(current_user=get_current_user())

    # Create default admin if not exists
    admin_email = 'mirkotornani@gmail.com'
    try:
        if not store.get_user_by_email(admin_email):
            # Use simple hash for admin password
            pw_hash = hash_password('admin')
            store.create_user(admin_email, pw_hash, 'Mirko Tornani', 'super_admin')
            user = store.get_user_by_email(admin_email)
            if user:
                store.update_user_credits(user['id'], 100)
            print(f"[AUTH] Created default admin: {admin_email} with 100 credits")
        else:
            print(f"[AUTH] Admin user already exists: {admin_email}")
    except Exception as e:
        print(f"[AUTH] Admin setup error (may already exist): {e}")
