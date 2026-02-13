from app import create_app
from app.tasks import verificar_fichajes_olvidados

app = create_app()
with app.app_context():
    verificar_fichajes_olvidados()