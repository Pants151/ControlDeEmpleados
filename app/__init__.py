from flask import Flask
from config import Config
from app.extensions import db, migrate, bootstrap, login_manager, jwt

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # 1. Inicializar extensiones con la app
    db.init_app(app)
    migrate.init_app(app, db)
    bootstrap.init_app(app)
    login_manager.init_app(app)
    jwt.init_app(app)

    # 2. Configuración del Login
    login_manager.login_view = 'auth.login'
    login_manager.login_message = "Por favor inicia sesión para acceder."

    # Función para cargar usuario (necesaria para Flask-Login)
    from app.models import Trabajador
    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(Trabajador, int(user_id))

    # 3. Registrar los Blueprints
    from app.routes.auth import auth_bp
    from app.routes.main import main_bp
    from app.routes.admin import admin_bp
    from app.routes.api import api_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(api_bp)

    # 4. Crear tablas si no existen
    with app.app_context():
        db.create_all()

    return app