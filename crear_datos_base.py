from app import app, db
from models import Horario

with app.app_context():
    # Buscamos si existe el horario 1
    horario_base = Horario.query.get(1)
    if not horario_base:
        # Si no existe, lo creamos
        horario_base = Horario(
            nombre_horario="Horario General", 
            descripcion="Horario estándar de 8h"
        )
        db.session.add(horario_base)
        db.session.commit()
        print("Horario Base (ID 1) creado correctamente.")
    else:
        print("El Horario Base ya existía.")