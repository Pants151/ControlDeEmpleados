from flask import Flask
from config import Config
from app.extensions import db, migrate, bootstrap, login_manager, jwt, mail
from flask_smorest import Api
from app.models import TokenBlocklist

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Configuración obligatoria para Smorest
    app.config["API_TITLE"] = "RRHH API"
    app.config["API_VERSION"] = "v1"
    app.config["OPENAPI_VERSION"] = "3.0.3"
    app.config["OPENAPI_URL_PREFIX"] = "/"
    app.config["OPENAPI_SWAGGER_UI_PATH"] = "/swagger-ui"
    app.config["OPENAPI_SWAGGER_UI_URL"] = "https://cdn.jsdelivr.net/npm/swagger-ui-dist/"

    # Inicializar extensiones con la app
    db.init_app(app)
    migrate.init_app(app, db)
    bootstrap.init_app(app)
    login_manager.init_app(app)
    jwt.init_app(app)
    mail.init_app(app)
    
    # CONFIGURACIÓN DE LA LISTA NEGRA DE JWT (Revocación de tokens)
    @jwt.token_in_blocklist_loader
    def check_if_token_revoked(jwt_header, jwt_payload):
        jti = jwt_payload["jti"]
        # Busca en la base de datos si este JTI (ID único del token) está en la lista negra
        with app.app_context():
            token = db.session.query(TokenBlocklist.id).filter_by(jti=jti).scalar()
        return token is not None # Si devuelve True, bloquea el acceso con un error 401

    # Inicializamos Smorest
    api = Api(app)

    # Configuración del Login
    login_manager.login_view = 'auth.login'
    login_manager.login_message = "Por favor inicia sesión para acceder."

    # Función para cargar usuario (necesaria para Flask-Login)
    from app.models import Trabajador
    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(Trabajador, int(user_id))

    # Registrar los Blueprints
    from app.routes.auth import auth_bp
    from app.routes.main import main_bp
    from app.routes.empresas import empresas_bp
    from app.routes.empleados import empleados_bp
    from app.routes.roles import roles_bp
    from app.routes.horarios import horarios_bp
    from app.routes.api import api_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(empresas_bp)
    app.register_blueprint(empleados_bp)
    app.register_blueprint(roles_bp)
    app.register_blueprint(horarios_bp)

    # Los blueprints de Smorest se registran en el objeto "api"
    api.register_blueprint(api_bp)

    # Crear tablas si no existen
    with app.app_context():
        db.create_all()

    return app