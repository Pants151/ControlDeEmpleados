from app import app, db
from models import Dia

dias_semana = [
    (1, "Lunes"), (2, "Martes"), (3, "Miércoles"), (4, "Jueves"), 
    (5, "Viernes"), (6, "Sábado"), (7, "Domingo")
]

with app.app_context():
    for id_d, nombre in dias_semana:
        dia_existente = Dia.query.get(id_d)
        if not dia_existente:
            nuevo_dia = Dia(id=id_d, nombre=nombre)
            db.session.add(nuevo_dia)
    
    db.session.commit()
    print("Días de la semana creados correctamente.")