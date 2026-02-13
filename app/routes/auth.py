from flask import Blueprint, render_template, redirect, url_for, flash, session, request, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from flask_mail import Message
from app.extensions import db, mail
from app.models import Trabajador, Rol
from app.forms import LoginForm, RegistroForm

import random
import string

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    form = LoginForm()
    if form.validate_on_submit():
        # Login dual: email o NIF
        user = Trabajador.query.filter((Trabajador.email == form.email.data) | (Trabajador.nif == form.email.data)).first()

        if user is not None and user.verify_password(form.password.data):
            # Verificamos que sea Admin o Superadmin
            if user.rol.nombre_rol in ['Administrador', 'Superadministrador']:
                login_user(user)
                # Fijamos siempre la empresa 1 en la sesión
                session['contexto_empresa'] = 1
                flash(f'Bienvenido {user.nombre}. Panel de gestión activado.')
                return redirect(url_for('main.index'))
            else:
                flash('Acceso denegado. Solo personal de administración.')
        else:
            flash('Email o contraseña incorrectos.')

    return render_template('login.html', form=form)

@auth_bp.route('/registro', methods=['GET', 'POST'])
def registro():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    form = RegistroForm()
    # CARGAR ROLES (Solo permitimos Admin y Superadmin para el registro público)
    roles_permitidos = Rol.query.filter(Rol.nombre_rol.in_(['Administrador', 'Superadministrador'])).all()
    form.rol_id.choices = [(r.id_rol, r.nombre_rol) for r in roles_permitidos]

    if form.validate_on_submit():
        if Trabajador.query.filter_by(email=form.email.data).first():
            flash('Error: Ese email ya está registrado.')
        else:
            nuevo_usuario = Trabajador(
                nombre=form.nombre.data,
                email=form.email.data,
                password=form.password.data,
                idRol=form.rol_id.data,
                idHorario=1 # Horario por defecto
            )
            nuevo_usuario.idEmpresa = None # Sin empresa asignada aún

            db.session.add(nuevo_usuario)
            db.session.commit()

            flash('Cuenta creada correctamente. Por favor, inicia sesión.')
            return redirect(url_for('auth.login'))

    return render_template('registro.html', form=form)

@auth_bp.route('/api/auth/forgot-password', methods=['POST'])
def forgot_password():
    data = request.get_json()
    email = data.get('email')
    print(f"DEBUG: Intentando recuperar para '{email}'")
    if not email:
        return jsonify({"msg": "El email es obligatorio"}), 400
    # Buscamos al trabajador por su email
    trabajador = Trabajador.query.filter(Trabajador.email.ilike(email)).first()
    if trabajador:
        print(f"DEBUG: Usuario ENCONTRADO: ID {trabajador.id_trabajador}")
    else:
        print(f"DEBUG: Usuario NO encontrado en la BD.") # <--- IMPORTANTE
    if not trabajador:
        # Por seguridad, si el email no existe, respondemos con éxito igual
        return jsonify({"msg": "Si el email existe, se enviará una clave temporal"}), 200
    # Generar una clave temporal aleatoria (letras y números)
    nueva_clave = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
    # Actualizar la contraseña en la Base de Datos
    trabajador.password = nueva_clave
    try:
        db.session.commit()
        # Preparar el correo para Mailtrap
        msg = Message(
            subject="Recuperación de Contraseña - Control de Presencia",
            recipients=[trabajador.email],
            body=f"Hola {trabajador.nombre},\n\n"
                 f"Has solicitado una recuperación de contraseña.\n"
                 f"Tu nueva clave temporal es: {nueva_clave}\n\n"
                 f"Por seguridad, cámbiala en cuanto accedas a la aplicación."
        )
        mail.send(msg)
        print("DEBUG: Correo enviado correctamente a Mailtrap")
        return jsonify({"msg": "Correo enviado con éxito"}), 200
    except Exception as e:
        db.session.rollback()
        print(f"DEBUG ERROR: {str(e)}")
        return jsonify({"msg": "Error interno al procesar la solicitud"}), 500

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Has cerrado sesión.')
    return redirect(url_for('auth.login'))