from app import app, db
from models import Rol, Trabajador

with app.app_context():
    # Creo el rol Superadministrador
    rol_super = Rol.query.filter_by(nombre_rol='Superadministrador').first()
    if not rol_super:
        rol_super = Rol(nombre_rol='Superadministrador')
        db.session.add(rol_super)
        db.session.commit()
        print("Rol 'Superadministrador' creado.")
    
    # Asciendo a mi administrador a super
    mi_usuario = Trabajador.query.filter_by(email='joseavn2002@gmail.com').first()
    if mi_usuario:
        mi_usuario.rol = rol_super
        db.session.commit()
        print(f"El usuario {mi_usuario.email} ahora es Superadministrador.")
    else:
        print("No se encontró tu usuario. Crea uno nuevo o revisa el email.")