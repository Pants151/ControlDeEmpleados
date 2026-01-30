from flask import Blueprint, render_template, request, redirect, url_for
from flask_login import login_required, current_user
from app.models import Registro, Incidencia, Trabajador
from app.utils import calcular_duracion

main_bp = Blueprint('main', __name__)

@main_bp.route('/', methods=['GET', 'POST'])
def index():
    if current_user.is_authenticated:
        return render_template('index.html')
    return redirect(url_for('auth.login'))

@main_bp.route('/registros')
@login_required
def listar_registros():
    empleado_id = request.args.get('empleado_id', type=int)
    fecha_desde = request.args.get('fecha_desde')
    fecha_hasta = request.args.get('fecha_hasta')

    query = Registro.query

    if empleado_id:
        query = query.filter_by(id_trabajador=empleado_id)

    if fecha_desde:
        query = query.filter(Registro.hora_entrada >= f"{fecha_desde} 00:00:00")
    if fecha_hasta:
        query = query.filter(Registro.hora_entrada <= f"{fecha_hasta} 23:59:59")

    registros = query.order_by(Registro.hora_entrada.desc()).all()

    for reg in registros:
        reg.duracion = calcular_duracion(reg.hora_entrada, reg.hora_salida)

    empleados = Trabajador.query.all()
    return render_template('registros.html', registros=registros, empleados=empleados)

@main_bp.route('/incidencias')
@login_required
def listar_incidencias():
    empleado_id = request.args.get('empleado_id', type=int)

    query = Incidencia.query
    if empleado_id:
        query = query.filter_by(id_trabajador=empleado_id)

    incidencias = query.order_by(Incidencia.fecha_hora.desc()).all()
    empleados = Trabajador.query.all()

    return render_template('incidencias.html', incidencias=incidencias, empleados=empleados)