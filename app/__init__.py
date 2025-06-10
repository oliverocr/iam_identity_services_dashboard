from flask import Flask
from flask_login import LoginManager
from .routes.auth import auth_bp
from .routes.dashboard import dashboard_bp
from .models.user import User
from datetime import datetime

login_manager = LoginManager()
login_manager.login_view = 'auth.login'

def format_datetime(value):
    try:
        return datetime.fromtimestamp(value).strftime('%d/%m/%Y %H:%M:%S')
    except Exception:
        return '-'

def create_app():
    app = Flask(__name__)
    app.secret_key = 'super_chave_secreta_123456'
    app.config['PERMANENT_SESSION_LIFETIME'] = 900

    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return User(user_id)

    app.jinja_env.filters['datetime'] = format_datetime

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp, url_prefix='/dashboard')

    return app
