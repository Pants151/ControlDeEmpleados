from flask import Blueprint, render_template, redirect, url_for, flash, session, request, jsonify, current_app
from flask_login import login_user, logout_user, login_required, current_user
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadTimeSignature
from flask_mail import Message
from app.extensions import db, mail
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

    if not email:
        return jsonify({"msg": "El email es obligatorio"}), 400

    trabajador = Trabajador.query.filter(Trabajador.email.ilike(email)).first()

    if not trabajador:
        return jsonify({"msg": "Si el email existe, se enviará un enlace"}), 200

    # Generar token con tiempo de caducidad
    s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    token = s.dumps(trabajador.email, salt=trabajador.passw)

    # Crear el enlace a la aplicación web
    enlace = url_for('auth.reset_password', email=trabajador.email, token=token, _external=True)

    try:
        msg = Message(
            subject="Recuperación de Contraseña - Control de Presencia",
            recipients=[trabajador.email],
            body=f"Hola {trabajador.nombre},\n\n"
                 f"Has solicitado restablecer tu contraseña.\n"
                 f"Haz clic en el siguiente enlace (caduca en 1 hora):\n"
                 f"{enlace}\n\n"
                 f"Si no solicitaste este cambio, ignora este correo."
        )
        mail.send(msg)
        return jsonify({"msg": "Correo enviado con éxito"}), 200
    except Exception as e:
        print(f"DEBUG ERROR: {str(e)}")
        return jsonify({"msg": "Error interno al enviar el correo"}), 500

# La pantalla donde el usuario pone la contraseña nueva
@auth_bp.route('/reset-password/<email>/<token>', methods=['GET', 'POST'])
def reset_password(email, token):
    if current_user.is_authenticated:
        logout_user()

    trabajador = Trabajador.query.filter_by(email=email).first()
    if not trabajador:
        flash('Usuario no válido.')
        return redirect(url_for('auth.login'))

    s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    try:
        # Si ya la cambió, el hash es distinto y esto dará error (un solo uso real)
        s.loads(token, salt=trabajador.passw, max_age=3600)
    except SignatureExpired:
        flash('El enlace ha caducado. Solicita uno nuevo.')
        return redirect(url_for('auth.login'))
    except BadTimeSignature:
        flash('El enlace es inválido o ya ha sido utilizado.')
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        nueva_pass = request.form.get('password')
        trabajador.password = nueva_pass # Cambia el hash
        db.session.commit()
        flash('Tu contraseña ha sido actualizada correctamente.')
        return redirect(url_for('auth.login'))

    return render_template('reset_password.html', token=token, email=email)

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Has cerrado sesión.')
    return redirect(url_for('auth.login'))