import math
from functools import wraps
from flask import abort
from flask_login import current_user
from datetime import datetime, timedelta
from app.models import Registro, Franja, Trabajador

# Función auxiliar para calcular duración
def calcular_duracion(entrada, salida):
    if not entrada: return "---"
    if not salida: return "En curso"
    delta = salida - entrada
    segundos = int(delta.total_seconds())
    horas, rem = divmod(segundos, 3600)
    minutos, _ = divmod(rem, 60)
    return f"{horas}h {minutos}m"

# Metodo para calcular la distancia de dos ubicaciones
def calcular_distancia(lat1, lon1, lat2, lon2):
    # Radio de la Tierra en metros
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1-a))

# Decorador personalizado para restringir acceso
def superadmin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.rol or current_user.rol.nombre_rol != 'Superadministrador':
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

# Función de utilidad que recorre los fichajes del mes y los compara con el horario teórico.
def calcular_resumen_mensual(trabajador_id, mes_anio):
    # mes_anio en formato "YYYY-MM"
    inicio_mes = datetime.strptime(f"{mes_anio}-01", "%Y-%m-%d")

    # Obtenemos todos los registros cerrados del trabajador en ese mes
    registros = Registro.query.filter(
        Registro.id_trabajador == trabajador_id,
        Registro.hora_entrada >= inicio_mes,
        Registro.hora_salida.isnot(None)
    ).all()

    total_trabajado_segundos = 0
    total_teorico_segundos = 0

    for reg in registros:
        # Calcular tiempo real
        duracion_real = reg.hora_salida - reg.hora_entrada
        total_trabajado_segundos += duracion_real.total_seconds()

        # Buscar el horario teórico para ese día de la semana
        dia_semana = reg.hora_entrada.isoweekday() # 1=Lunes, 7=Domingo
        trabajador = Trabajador.query.get(trabajador_id)

        franja = Franja.query.filter_by(
            id_horario=trabajador.idHorario,
            id_dia=dia_semana
        ).first()

        if franja:
            # Convertimos strings "HH:MM" a objetos tiempo para restar
            h_ent = datetime.strptime(franja.hora_entrada, "%H:%M")
            h_sal = datetime.strptime(franja.hora_salida, "%H:%M")
            duracion_teorica = h_sal - h_ent
            total_teorico_segundos += duracion_teorica.total_seconds()

    horas_trabajadas = round(total_trabajado_segundos / 3600, 2)
    horas_teoricas = round(total_teorico_segundos / 3600, 2)
    horas_extra = max(0, round(horas_trabajadas - horas_teoricas, 2))

    return {
        "mes": mes_anio,
        "horas_trabajadas": horas_trabajadas,
        "horas_teoricas": horas_teoricas,
        "horas_extra": horas_extra
    }