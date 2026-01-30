import os
import math
import pytz
from flask import Flask, render_template, redirect, url_for, flash, request, abort, session
from flask_migrate import Migrate
from flask_bootstrap import Bootstrap
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from config import Config
from models import db, Trabajador, Rol, Empresa, Horario, Franja, Dia, Registro, Incidencia
from forms import LoginForm, EmpresaForm, RolForm, TrabajadorForm, HorarioForm, FranjaForm, RegistroForm
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from functools import wraps
from datetime import datetime
from flask_cors import CORS


# Configura la zona horaria de España
timezone_esp = pytz.timezone('Europe/Madrid')

basedir = os.path.abspath(os.path.dirname(__file__))
app = Flask(__name__, template_folder=os.path.join(basedir, 'templates'))
CORS(app)
app.config.from_object(Config)

# Inicio las extensiones
db.init_app(app)
migrate = Migrate(app, db)
bootstrap = Bootstrap(app)
login_manager = LoginManager(app)
jwt = JWTManager(app)
login_manager.login_view = 'login'

# Función auxiliar para calcular duración
def calcular_duracion(entrada, salida):
    if not entrada: return "---"
    if not salida: return "En curso"
    delta = salida - entrada
    segundos = int(delta.total_seconds())
    horas, rem = divmod(segundos, 3600)
    minutos, _ = divmod(rem, 60)
    return f"{horas}h {minutos}m"

# Metodo de Login con API
@app.route('/api/auth/login', methods=['POST'])
def api_login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    user = Trabajador.query.filter((Trabajador.email == email) | (Trabajador.nif == email)).first()
    if user and user.verify_password(password):
        # El token incluye info del usuario y su rol
        access_token = create_access_token(identity=str(user.id_trabajador),
                                          additional_claims={"rol": user.rol.nombre_rol})
        return {"token": access_token, "usuario": user.nombre}, 200

    return {"msg": "Credenciales incorrectas"}, 401

# Decorador personalizado para restringir acceso
def superadmin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.rol or current_user.rol.nombre_rol != 'Superadministrador':
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

@login_manager.user_loader
def load_user(user_id):
    # Usar session.get es más seguro para SQLAlchemy 2.0
    return db.session.get(Trabajador, int(user_id))

@app.route('/', methods=['GET', 'POST'])
def index():
    # Si ya está logueado, muestro el panel
    if current_user.is_authenticated:
        return render_template('index.html')
    # Si no, lo llevo al login
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    form = LoginForm()
    # Eliminamos la carga de empresas porque ahora solo hay una

    if form.validate_on_submit():
        user = Trabajador.query.filter((Trabajador.email == form.email.data) | (Trabajador.nif == form.email.data)).first()

        if user is not None and user.verify_password(form.password.data):
            # Verificamos que sea Admin o Superadmin
            if user.rol.nombre_rol in ['Administrador', 'Superadministrador']:
                login_user(user)
                # Fijamos siempre la empresa 1 en la sesión
                session['contexto_empresa'] = 1
                flash(f'Bienvenido {user.nombre}. Panel de gestión activado.')
                return redirect(url_for('index'))
            else:
                flash('Acceso denegado. Solo personal de administración.')
        else:
            flash('Email o contraseña incorrectos.')

    return render_template('login.html', form=form)

@app.route('/configuracion-empresa', methods=['GET', 'POST'])
@login_required
def configuracion_empresa():
    # Obtenemos la empresa única
    empresa = Empresa.query.get_or_404(1)
    form = EmpresaForm(obj=empresa)

    if form.validate_on_submit():
        # Guardamos los nuevos datos de geolocalización
        empresa.nombrecomercial = form.nombrecomercial.data
        empresa.cif = form.cif.data
        empresa.lat = float(form.lat.data)
        empresa.lng = float(form.lng.data)
        empresa.radio = float(form.radio.data)
        empresa.domicilio = form.domicilio.data
        empresa.localidad = form.localidad.data
        empresa.cp = form.cp.data
        empresa.provincia = form.provincia.data
        empresa.email = form.email.data
        empresa.telefono = form.telefono.data

        db.session.commit()
        flash('Datos de la empresa actualizados correctamente.')
        return redirect(url_for('index'))

    return render_template('editar_empresa.html', form=form, titulo="Configuración de Empresa")

@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    form = RegistroForm()

    # 1. CARGAR ROLES (Solo permitimos Admin y Superadmin para el registro)
    roles_permitidos = Rol.query.filter(Rol.nombre_rol.in_(['Administrador', 'Superadministrador'])).all()
    form.rol_id.choices = [(r.id_rol, r.nombre_rol) for r in roles_permitidos]

    if form.validate_on_submit():
        # Comprobamos si el email ya existe
        if Trabajador.query.filter_by(email=form.email.data).first():
            flash('Error: Ese email ya está registrado.')
        else:
            # 2. USAMOS EL ROL ELEGIDO EN EL FORMULARIO
            nuevo_usuario = Trabajador(
                nombre=form.nombre.data,
                email=form.email.data,
                password=form.password.data,
                idRol=form.rol_id.data,
                idHorario=1
            )

            # Al ser un registro nuevo, no tiene empresa asignada (None)
            nuevo_usuario.idEmpresa = None

            db.session.add(nuevo_usuario)
            db.session.commit()

            flash('Cuenta creada correctamente. Por favor, inicia sesión.')
            return redirect(url_for('login'))

    return render_template('registro.html', form=form)

# Ruta de registros
@app.route('/registros')
@login_required
def listar_registros():
    empleado_id = request.args.get('empleado_id', type=int)
    fecha_desde = request.args.get('fecha_desde')
    fecha_hasta = request.args.get('fecha_hasta')

    query = Registro.query

    if empleado_id:
        query = query.filter_by(id_trabajador=empleado_id)

    # Filtro de fechas: comparamos la columna hora_entrada
    if fecha_desde:
        query = query.filter(Registro.hora_entrada >= f"{fecha_desde} 00:00:00")
    if fecha_hasta:
        query = query.filter(Registro.hora_entrada <= f"{fecha_hasta} 23:59:59")

    registros = query.order_by(Registro.hora_entrada.desc()).all()

    for reg in registros:
        reg.duracion = calcular_duracion(reg.hora_entrada, reg.hora_salida)

    empleados = Trabajador.query.all()
    return render_template('registros.html', registros=registros, empleados=empleados)

# Ruta de incidencias
@app.route('/incidencias')
@login_required
def listar_incidencias():
    # Filtros opcionales
    empleado_id = request.args.get('empleado_id', type=int)

    query = Incidencia.query
    if empleado_id:
        query = query.filter_by(id_trabajador=empleado_id)

    incidencias = query.order_by(Incidencia.fecha_hora.desc()).all()
    empleados = Trabajador.query.all()

    return render_template('incidencias.html', incidencias=incidencias, empleados=empleados)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Has cerrado sesión.')
    return redirect(url_for('login'))

#[GESTION DE EMPRESAS]
# Listar las empresas
@app.route('/empresas')
@login_required
@superadmin_required
def listar_empresas():
    empresas = Empresa.query.all()
    return render_template('empresas.html', empresas=empresas)

# Crear una empresa
@app.route('/empresas/nueva', methods=['GET', 'POST'])
@login_required
@superadmin_required
def nueva_empresa():
    form = EmpresaForm()
    if form.validate_on_submit():
        empresa = Empresa(
            nombrecomercial=form.nombrecomercial.data,
            cif=form.cif.data,
            domicilio=form.domicilio.data,
            localidad=form.localidad.data,
            cp=form.cp.data,
            provincia=form.provincia.data,
            email=form.email.data,
            telefono=form.telefono.data
        )
        db.session.add(empresa)
        db.session.commit()
        flash('Empresa creada correctamente.')
        return redirect(url_for('listar_empresas'))
    return render_template('editar_empresa.html', form=form, titulo="Nueva Empresa")

# Editar una empresa
@app.route('/empresas/editar/<int:id>', methods=['GET', 'POST'])
@login_required
@superadmin_required
def editar_empresa(id):
    empresa = Empresa.query.get_or_404(id)
    form = EmpresaForm(obj=empresa) # Cargamos los datos existentes en el formulario

    if form.validate_on_submit():
        empresa.nombrecomercial = form.nombrecomercial.data
        empresa.domicilio = form.domicilio.data
        empresa.localidad = form.localidad.data
        empresa.cp = form.cp.data
        empresa.provincia = form.provincia.data
        empresa.email = form.email.data
        empresa.telefono = form.telefono.data
        empresa.cif = form.cif.data
        db.session.commit()
        flash('Empresa actualizada.')
        return redirect(url_for('listar_empresas'))

    return render_template('editar_empresa.html', form=form, titulo="Editar Empresa")

# Eliminar una empresa
@app.route('/empresas/eliminar/<int:id>')
@login_required
@superadmin_required
def eliminar_empresa(id):
    empresa = Empresa.query.get_or_404(id)
    # Comprobamos si tiene empleados antes de borrar
    if empresa.trabajadores.first():
        flash('Error: No se puede eliminar una empresa con empleados asociados.')
    else:
        db.session.delete(empresa)
        db.session.commit()
        flash('Empresa eliminada.')
    return redirect(url_for('listar_empresas'))

#[GESTION DE ROLES]
# Listar roles
@app.route('/roles')
@login_required
def listar_roles():
    roles = Rol.query.all()
    return render_template('roles.html', roles=roles)

# Crear roles
@app.route('/roles/nuevo', methods=['GET', 'POST'])
@login_required
def nuevo_rol():
    form = RolForm()
    if form.validate_on_submit():
        if Rol.query.filter_by(nombre_rol=form.nombre_rol.data).first():
            flash('Error: Ya existe un rol con ese nombre.')
        else:
            rol = Rol(nombre_rol=form.nombre_rol.data)
            db.session.add(rol)
            db.session.commit()
            flash('Rol creado.')
            return redirect(url_for('listar_roles'))
    return render_template('editar_rol.html', form=form, titulo="Nuevo Rol")

# Editar roles
@app.route('/roles/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_rol(id):
    rol = Rol.query.get_or_404(id)
    form = RolForm(obj=rol)
    if form.validate_on_submit():
        rol.nombre_rol = form.nombre_rol.data
        db.session.commit()
        flash('Rol actualizado.')
        return redirect(url_for('listar_roles'))
    return render_template('editar_rol.html', form=form, titulo="Editar Rol")

# Eliminar roles
@app.route('/roles/eliminar/<int:id>')
@login_required
def eliminar_rol(id):
    rol = Rol.query.get_or_404(id)
    # REQUISITO PDF: Un rol no se puede eliminar si hay empleados con dicho rol [cite: 16]
    if rol.trabajadores.first():
        flash('Error: No se puede eliminar este rol porque tiene empleados asignados.')
    else:
        db.session.delete(rol)
        db.session.commit()
        flash('Rol eliminado.')
    return redirect(url_for('listar_roles'))

#[GESTION DE EMPLEADOS]
# Listar empleados
@app.route('/empleados', methods=['GET', 'POST'])
@login_required
def listar_empleados():
    empresa_seleccionada_id = session.get('contexto_empresa')

    # lógica para convertir el 0 en None si fuera necesario
    if empresa_seleccionada_id == 0:
        empresa_seleccionada_id = None

    # Filtramos por la empresa del contexto (sea Admin o Superadmin)
    if empresa_seleccionada_id:
        empleados = Trabajador.query.filter_by(idEmpresa=empresa_seleccionada_id).all()
        empresa_obj = Empresa.query.get(empresa_seleccionada_id)
    else:
        # Si eligió gestionar "Ninguna" empresa, ve los empleados que no tienen empresa
        empleados = Trabajador.query.filter_by(idEmpresa=None).all()
        empresa_obj = None

    return render_template('empleados.html',
                           empleados=empleados,
                           empresa_actual=empresa_obj)

# Crear empleados
@app.route('/empleados/nuevo', methods=['GET', 'POST'])
@login_required
def nuevo_empleado():
    form = TrabajadorForm()
    roles_permitidos = Rol.query.filter(Rol.nombre_rol.notin_(['Administrador', 'Superadministrador'])).all()
    form.rol_id.choices = [(r.id_rol, r.nombre_rol) for r in roles_permitidos]
    form.horario_id.choices = [(h.id_horario, h.nombre_horario) for h in Horario.query.all()]

    if form.validate_on_submit():
        # 1. COMPROBACIÓN DE DUPLICADOS
        nif_existente = Trabajador.query.filter_by(nif=form.nif.data).first()
        email_existente = Trabajador.query.filter_by(email=form.email.data).first()

        if nif_existente:
            flash(f'Error: El NIF {form.nif.data} ya está registrado en el sistema.')
            return render_template('editar_empleado.html', form=form, titulo="Nuevo Empleado")

        if email_existente:
            flash(f'Error: El Email {form.email.data} ya está siendo usado por otro empleado.')
            return render_template('editar_empleado.html', form=form, titulo="Nuevo Empleado")

        # 2. SI NO HAY DUPLICADOS, CREAMOS EL OBJETO
        empleado = Trabajador(
            nif=form.nif.data,
            nombre=form.nombre.data,
            apellidos=form.apellidos.data,
            email=form.email.data,
            telef=form.telef.data,
            direccion=form.direccion.data,
            localidad=form.localidad.data,
            cp=form.cp.data,
            provincia=form.provincia.data,
            idRol=form.rol_id.data,
            idHorario=form.horario_id.data,
            idEmpresa=1 # Forzamos empresa única
        )

        if form.password.data:
            empleado.password = form.password.data

        db.session.add(empleado)
        try:
            db.session.commit()
            flash('Empleado creado correctamente.')
            return redirect(url_for('listar_empleados'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error inesperado en la base de datos: {str(e)}')

    return render_template('editar_empleado.html', form=form, titulo="Nuevo Empleado")

# Editar empleados
@app.route('/empleados/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_empleado(id):
    empleado = Trabajador.query.get_or_404(id)
    form = TrabajadorForm(obj=empleado)

    roles_basicos = Rol.query.filter(Rol.nombre_rol.notin_(['Administrador', 'Superadministrador'])).all()
    form.rol_id.choices = [(r.id_rol, r.nombre_rol) for r in roles_basicos]

    if request.method == 'GET':
        form.rol_id.data = empleado.idRol
        form.horario_id.data = empleado.idHorario

    # Configuración de roles según quién se edita
    if current_user.id_trabajador == id:
        roles_permitidos = Rol.query.filter(Rol.nombre_rol.in_(['Administrador', 'Superadministrador'])).all()
        form.rol_id.choices = [(r.id_rol, r.nombre_rol) for r in roles_permitidos]
    else:
        form.rol_id.choices = [(r.id_rol, r.nombre_rol) for r in Rol.query.all()]

    form.horario_id.choices = [(h.id_horario, h.nombre_horario) for h in Horario.query.all()]

    if form.validate_on_submit():
        empleado.nif = form.nif.data
        empleado.nombre = form.nombre.data
        empleado.apellidos = form.apellidos.data
        empleado.email = form.email.data
        empleado.telef = form.telef.data
        empleado.direccion = form.direccion.data
        empleado.localidad = form.localidad.data
        empleado.cp = form.cp.data
        empleado.provincia = form.provincia.data
        empleado.idRol = form.rol_id.data
        empleado.idHorario = form.horario_id.data

        # ASEGURAMOS ID 1: Garantiza que no falle la restricción de integridad de la BD
        empleado.idEmpresa = 1

        if form.password.data:
            empleado.password = form.password.data

        db.session.commit()
        flash('Datos actualizados correctamente.')
        return redirect(url_for('listar_empleados'))

    return render_template('editar_empleado.html', form=form, titulo="Editar Perfil")

# Eliminar empleados
@app.route('/empleados/eliminar/<int:id>')
@login_required
def eliminar_empleado(id):
    empleado = Trabajador.query.get_or_404(id)
    if empleado.id_trabajador == current_user.id_trabajador:
        flash('Error: No puedes eliminarte a ti mismo.')
    else:
        db.session.delete(empleado)
        db.session.commit()
        flash('Empleado eliminado.')
    return redirect(url_for('listar_empleados'))

#[GESTION DE HORARIOS]

# Listar horarios
@app.route('/horarios')
@login_required
def listar_horarios():
    horarios = Horario.query.all()
    return render_template('horarios.html', horarios=horarios)

# Crear horarios
@app.route('/horarios/nuevo', methods=['GET', 'POST'])
@login_required
def nuevo_horario():
    form = HorarioForm()
    if form.validate_on_submit():
        horario = Horario(
            nombre_horario=form.nombre_horario.data,
            descripcion=form.descripcion.data
        )
        db.session.add(horario)
        db.session.commit()
        flash('Horario creado. Ahora añade las franjas.')
        return redirect(url_for('ver_horario', id=horario.id_horario))
    return render_template('editar_horario.html', form=form, titulo="Nuevo Horario")

# Ver detalles y añadir franjas de horarios
@app.route('/horarios/ver/<int:id>', methods=['GET', 'POST'])
@login_required
def ver_horario(id):
    horario = Horario.query.get_or_404(id)
    form = FranjaForm()
    # Cargamos los días en el select
    form.dia_id.choices = [(d.id, d.nombre) for d in Dia.query.all()]

    if form.validate_on_submit():
        # DATOS DEL FORMULARIO
        nuevo_dia = form.dia_id.data
        nueva_entrada = form.hora_entrada.data
        nueva_salida = form.hora_salida.data

        # Validacion basica
        if nueva_salida <= nueva_entrada:
            flash('Error: La hora de salida debe ser posterior a la de entrada.')
        else:
            # Validacion de solapamiento
            # Obtenemos franjas de ESTE horario y ESTE día
            franjas_existentes = Franja.query.filter_by(id_horario=id, id_dia=nuevo_dia).all()
            solapa = False
            for f in franjas_existentes:
                if (nueva_entrada < f.hora_salida) and (nueva_salida > f.hora_entrada):
                    solapa = True
                    break

            if solapa:
                flash('Error: Las horas se solapan con otra franja existente en este día.')
            else:
                # CREAR FRANJA
                franja = Franja(
                    id_horario=id,
                    id_dia=nuevo_dia,
                    hora_entrada=nueva_entrada,
                    hora_salida=nueva_salida
                )
                db.session.add(franja)
                db.session.commit()
                flash('Franja añadida correctamente.')
                return redirect(url_for('ver_horario', id=id))

    return render_template('ver_horario.html', horario=horario, form=form)

# Eliminar horarios
@app.route('/horarios/eliminar/<int:id>')
@login_required
def eliminar_horario(id):
    horario = Horario.query.get_or_404(id)

    # No borrar si tiene un empleado
    if horario.trabajadores.first():
        flash('Error: No se puede eliminar un horario asignado a empleados.')
    else:
        # Borrar primero las franjas
        Franja.query.filter_by(id_horario=id).delete()
        db.session.delete(horario)
        db.session.commit()
        flash('Horario eliminado.')

    return redirect(url_for('listar_horarios'))

#[GESTION DE FRANJAS]
# Eliminar franjas
@app.route('/franjas/eliminar/<int:id_horario>/<int:id_dia>')
@login_required
def eliminar_franja(id_horario, id_dia):
    # Borro todas las franjas de ese día para ese horario
    franja = Franja.query.filter_by(id_horario=id_horario, id_dia=id_dia).first()
    if franja:
        db.session.delete(franja)
        db.session.commit()
        flash('Franja eliminada.')
    return redirect(url_for('ver_horario', id=id_horario))

#[GESTION DE GEOCALIZACION]

# Metodo para calcular la distancia de dos ubicaciones
def calcular_distancia(lat1, lon1, lat2, lon2):
    # Radio de la Tierra en metros
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1-a))

# Metodo para detectar la ficha de un trabajador
@app.route('/api/presencia/entrada', methods=['POST'])
@jwt_required()
def api_fichar_entrada():
    user_id = int(get_jwt_identity())
    trabajador = Trabajador.query.get(user_id)
    data = request.get_json()

    # 1. GPS
    empresa = Empresa.query.get(1)
    distancia = calcular_distancia(data.get('lat'), data.get('lng'), empresa.lat, empresa.lng)
    if distancia > empresa.radio:
        return {"msg": f"Fuera de radio ({int(distancia)}m)"}, 400

    # 2. Horario
    ahora_local = datetime.now(timezone_esp)
    dia_semana = ahora_local.weekday() + 1
    hora_actual_str = ahora_local.strftime("%H:%M")
    franjas = Franja.query.filter_by(id_horario=trabajador.idHorario, id_dia=dia_semana).all()

    if not franjas: return {"msg": "Hoy no es día laboral"}, 403
    if not any(f.hora_entrada <= hora_actual_str <= f.hora_salida for f in franjas):
        return {"msg": "Fuera de horario de turno"}, 403

    # 3. Comprobar si ya hay una entrada abierta (ESTO FALLABA ANTES)
    registro_abierto = Registro.query.filter_by(id_trabajador=user_id, hora_salida=None).first()
    if registro_abierto:
        return {"msg": "Ya tienes una entrada activa"}, 400

    # 4. Guardar
    nuevo = Registro(id_trabajador=user_id, hora_entrada=datetime.utcnow())
    db.session.add(nuevo)
    db.session.commit()
    return {"msg": "Entrada registrada correctamente"}, 201

# Busca el fichaje abierto del trabajador (donde la hora de salida es nula) y le asigna la hora actual
@app.route('/api/presencia/salida', methods=['POST'])
@jwt_required()
def api_fichar_salida():
    user_id = int(get_jwt_identity())

    # Buscamos el registro que tenga entrada pero no salida
    ultimo_registro = Registro.query.filter_by(id_trabajador=user_id, hora_salida=None).first()

    if not ultimo_registro:
        return {"msg": "No hay una entrada previa abierta para este usuario"}, 400

    ultimo_registro.hora_salida = datetime.utcnow()
    db.session.commit()

    return {"msg": "Salida registrada correctamente"}, 200

# Permite que el empleado envíe una descripción de cualquier problema desde la app
@app.route('/api/incidencias', methods=['POST'])
@jwt_required()
def api_registrar_incidencia():
    user_id = int(get_jwt_identity())
    data = request.get_json()
    descripcion = data.get('descripcion')

    if not descripcion:
        return {"msg": "La descripción es obligatoria"}, 400

    nueva_incidencia = Incidencia(
        id_trabajador=user_id,
        descripcion=descripcion,
        fecha_hora=datetime.utcnow()
    )

    db.session.add(nueva_incidencia)
    db.session.commit()

    return {"msg": "Incidencia reportada con éxito"}, 201

# Permite saber al abrirla si el usuario debe ver el botón de "Entrada" o el de "Salida"
@app.route('/api/presencia/estado', methods=['GET'])
@jwt_required()
def api_obtener_estado():
    user_id = int(get_jwt_identity())
    # Si tiene un registro sin salida, es que está "dentro"
    en_activo = Registro.query.filter_by(id_trabajador=user_id, hora_salida=None).first()

    return {
        "fichado": True if en_activo else False,
        "ultima_entrada": en_activo.hora_entrada.isoformat() if en_activo else None
    }, 200

if __name__ == '__main__':
    app.run()