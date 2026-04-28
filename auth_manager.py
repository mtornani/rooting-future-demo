import os
import logging
from flask import Blueprint, render_template, redirect, url_for, request, flash, session
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_bcrypt import Bcrypt

auth_bp = Blueprint('auth', __name__)
login_manager = LoginManager()
login_manager.session_protection = "basic"  # "strong" invalida sessioni dietro proxy
bcrypt = Bcrypt()
_store = None
_log = logging.getLogger("auth")

class User(UserMixin):
    def __init__(self, user_data):
        self.id = str(user_data['id'])
        self.email = user_data['email']
        self.full_name = user_data.get('full_name', '')
        self.role = user_data.get('role', 'viewer')
        self.credits = user_data.get('credits', 0)
        self.first_login = bool(user_data.get('first_login', 0))
        self.password_hash = user_data['password_hash']

    @staticmethod
    def get(user_id):
        if not _store:
            print(f"[AUTH] user_loader: _store is None", flush=True)
            return None
        try:
            data = _store.get_user_by_id(int(user_id))
            print(f"[AUTH] user_loader({user_id}): data={'found' if data else 'None'}", flush=True)
            return User(data) if data else None
        except Exception as e:
            print(f"[AUTH] user_loader({user_id}) ERROR: {type(e).__name__}: {e}", flush=True)
            return None

@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    print(f"[AUTH] /login {request.method}", flush=True)
    if current_user.is_authenticated:
        print(f"[AUTH] already authenticated, redirect to index", flush=True)
        return redirect(url_for('index'))

    if request.method == 'POST':
        email = request.form.get('email', '')
        password = request.form.get('password', '')
        print(f"[AUTH] Login attempt: {email}", flush=True)

        try:
            user_data = _store.get_user_by_email(email)
            print(f"[AUTH] User found: {bool(user_data)}", flush=True)
        except Exception as e:
            print(f"[AUTH] DB error: {e}", flush=True)
            user_data = None

        if user_data:
            try:
                pw_match = bcrypt.check_password_hash(user_data['password_hash'], password)
                print(f"[AUTH] Password match: {pw_match}", flush=True)
            except Exception as e:
                print(f"[AUTH] bcrypt error: {e}", flush=True)
                pw_match = False

            if pw_match:
                user = User(user_data)
                login_user(user)
                session.modified = True
                print(f"[AUTH] login_user OK, session keys: {list(session.keys())}", flush=True)
                return redirect(url_for('index'))

        flash('Email o password non validi', 'error')
        print(f"[AUTH] Login failed for {email}", flush=True)
            
    return render_template('login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))

def init_auth(app, store):
    global _store
    _store = store
    login_manager.init_app(app)
    bcrypt.init_app(app)
    login_manager.login_view = 'auth.login'
    app.register_blueprint(auth_bp)

    # Create or reset default admin (with app_context for proper bcrypt init)
    admin_email = 'mirkotornani@gmail.com'
    admin_password = os.environ.get('ADMIN_PASSWORD', 'admin')
    try:
        with app.app_context():
            pw_hash = bcrypt.generate_password_hash(admin_password).decode('utf-8')
            existing = store.get_user_by_email(admin_email)
            if not existing:
                store.create_user(admin_email, pw_hash, 'Mirko Tornani', 'super_admin')
                user = store.get_user_by_email(admin_email)
                if user:
                    store.update_user_credits(user['id'], 100)
                print(f"Created admin: {admin_email}")
            else:
                # Always sync password hash so restarts don't break login
                import sqlite3 as _sq
                with _sq.connect(store.db_path) as _conn:
                    _conn.execute(
                        "UPDATE users SET password_hash = ? WHERE email = ?",
                        (pw_hash, admin_email)
                    )
                    _conn.commit()
                print(f"Admin password synced: {admin_email}")
    except Exception as e:
        print(f"Admin init error: {e}")
