from app import app, db
from models import Rol, Trabajador

with app.app_context():
    # Creo el Rol Administrador si no existe
    rol_admin = Rol.query.filter_by(nombre_rol='Administrador').first()
    if not rol_admin:
        rol_admin = Rol(nombre_rol='Administrador')
        db.session.add(rol_admin)
        print("Rol 'Administrador' creado.")
    
    # Pongo email y contraseña
    email_admin = "joseavn2002@gmail.com"
    pass_admin = "1234"

    admin = Trabajador.query.filter_by(email=email_admin).first()
    if not admin:
        admin = Trabajador(
            nif="12345678A",
            nombre="José Antonio",
            apellidos="Valenzuela Núñez",
            email=email_admin,
            password=pass_admin, # Esto usa el setter que hashea la contraseña
            rol=rol_admin # Asigno el objeto rol directamente
        )
        db.session.add(admin)
        db.session.commit()
        print(f"Usuario Administrador creado. Email: {email_admin}, Pass: {pass_admin}")
    else:
        print("El usuario administrador ya existía.")