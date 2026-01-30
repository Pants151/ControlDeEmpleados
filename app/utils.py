import math
from functools import wraps
from flask import abort
from flask_login import current_user

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