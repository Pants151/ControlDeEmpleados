from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_bootstrap import Bootstrap
from flask_login import LoginManager
from flask_jwt_extended import JWTManager
from flask_mail import Mail

# Inicializamos las extensiones vacías, se conectarán a la app más tarde
db = SQLAlchemy()
migrate = Migrate()
bootstrap = Bootstrap()
login_manager = LoginManager()
jwt = JWTManager()
mail = Mail()