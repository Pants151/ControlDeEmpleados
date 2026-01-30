from flask import Blueprint, render_template, redirect, url_for, flash, session
from flask_login import login_user, logout_user, login_required, current_user
from app.extensions import db
from app.models import Trabajador, Rol
from app.forms import LoginForm, RegistroForm

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
    # 1. CARGAR ROLES (Solo permitimos Admin y Superadmin para el registro público)
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

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Has cerrado sesión.')
    return redirect(url_for('auth.login'))