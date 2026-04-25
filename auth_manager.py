import os
from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_bcrypt import Bcrypt

auth_bp = Blueprint('auth', __name__)
login_manager = LoginManager()
bcrypt = Bcrypt()
_store = None

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
        if not _store: return None
        try:
            data = _store.get_user_by_id(int(user_id))
            return User(data) if data else None
        except (ValueError, TypeError):
            return None

@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user_data = _store.get_user_by_email(email)
        
        if user_data and bcrypt.check_password_hash(user_data['password_hash'], password):
            user = User(user_data)
            login_user(user)
            return redirect(url_for('index'))
        else:
            flash('Email o password non validi', 'error')
            
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
