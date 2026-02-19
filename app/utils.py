import math
from functools import wraps
from flask import abort
from flask_login import current_user
from datetime import datetime, timedelta
from app.models import Registro, Franja, Trabajador
import calendar
import pytz

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
def calcular_resumen_mensual(user_id, mes_str):
    timezone_esp = pytz.timezone('Europe/Madrid')
    ahora_madrid = datetime.now(timezone_esp)

    # Si la app de Android nos manda 'null', forzamos el mes actual
    if not mes_str or mes_str == 'null':
        mes_str = ahora_madrid.strftime("%Y-%m")

    try:
        fecha_dt = datetime.strptime(mes_str, "%Y-%m")
        primer_dia = fecha_dt.replace(day=1, hour=0, minute=0, second=0)
        ultimo_dia_mes = calendar.monthrange(fecha_dt.year, fecha_dt.month)[1]
        ultimo_dia = fecha_dt.replace(day=ultimo_dia_mes, hour=23, minute=59, second=59)

        nombres_meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
                         "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
        nombre_visual_mes = f"{nombres_meses[fecha_dt.month - 1]} {fecha_dt.year}"
    except Exception:
        return {"msg": "Formato de mes inválido"}, 400

    trabajador = Trabajador.query.get(user_id)
    if not trabajador:
        return {"msg": "Usuario no encontrado"}, 404

    # 1. CÁLCULO DE HORAS REALES
    registros = Registro.query.filter(
        Registro.id_trabajador == user_id,
        Registro.hora_entrada >= primer_dia,
        Registro.hora_entrada <= ultimo_dia
    ).all()

    total_segundos_reales = 0
    dias_con_actividad = set()

    for r in registros:
        if r.hora_salida:
            diff_real = r.hora_salida - r.hora_entrada
            total_segundos_reales += diff_real.total_seconds()

            # EL ARREGLO ESTÁ AQUÍ:
            # Si un fichaje cruza la medianoche (ej. de Jueves a Viernes),
            # añadimos a la lista TANTO el jueves COMO el viernes.
            dia_actual = r.hora_entrada.date()
            dia_salida = r.hora_salida.date()
            while dia_actual <= dia_salida:
                dias_con_actividad.add(dia_actual)
                dia_actual += timedelta(days=1)
        else:
            # Si está trabajando ahora mismo, solo metemos hoy
            dias_con_actividad.add(r.hora_entrada.date())

    # 2. CÁLCULO DE HORAS TEÓRICAS (Solo de los días que fichó)
    total_segundos_teoricos = 0
    if trabajador.idHorario:
        for fecha_fichaje in dias_con_actividad:
            id_dia_semana = fecha_fichaje.weekday() + 1
            franja = Franja.query.filter_by(id_horario=trabajador.idHorario, id_dia=id_dia_semana).first()

            if franja and franja.hora_entrada and franja.hora_salida:
                try:
                    h_ent = datetime.strptime(str(franja.hora_entrada).strip()[:5], "%H:%M")
                    h_sal = datetime.strptime(str(franja.hora_salida).strip()[:5], "%H:%M")

                    # Arreglo para turnos de noche
                    if h_sal < h_ent:
                        h_sal += timedelta(days=1)

                    total_segundos_teoricos += (h_sal - h_ent).total_seconds()
                except ValueError:
                    pass

    # 3. EMPAQUETAR DATOS PARA ANDROID Y WEB
    horas_reales_float = total_segundos_reales / 3600
    horas_teoricas_float = total_segundos_teoricos / 3600

    # Solo damos horas extra si de verdad hizo más de las teóricas
    segundos_extra = max(0, total_segundos_reales - total_segundos_teoricos)

    def formatear(segundos):
        h = int(segundos // 3600)
        m = int((segundos % 3600) // 60)
        return f"{h}h {m}min"

    return {
        "mes": nombre_visual_mes,
        "horas_teoricas": round(horas_teoricas_float, 2),
        "horas_reales": round(horas_reales_float, 2),
        "diferencia": round(horas_reales_float - horas_teoricas_float, 2),
        "dias_trabajados": len(dias_con_actividad),
        "trabajado": formatear(total_segundos_reales),
        "teorico": formatear(total_segundos_teoricos),
        "extra": formatear(segundos_extra)
    }