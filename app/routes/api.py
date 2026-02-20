from flask.views import MethodView
from flask_smorest import Blueprint, abort
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from flask import request, jsonify
from datetime import datetime
import pytz
from app.extensions import db
from app.models import Trabajador, Registro, Incidencia, Empresa, Franja
from app.utils import calcular_distancia, calcular_resumen_mensual
from app.schemas import (LoginSchema, TokenSchema, PresenceInputSchema,
                         IncidenciaInputSchema, EstadoResponseSchema, MessageSchema)

api_bp = Blueprint('api', __name__, url_prefix='/api', description='Operaciones de la API móvil')
timezone_esp = pytz.timezone('Europe/Madrid')

@api_bp.route('/auth/login')
class ApiLogin(MethodView):
    @api_bp.arguments(LoginSchema)
    @api_bp.response(200, TokenSchema)
    def post(self, login_data):
        email = login_data.get('email')
        password = login_data.get('password')

        user = Trabajador.query.filter((Trabajador.email == email) | (Trabajador.nif == email)).first()

        if user and user.verify_password(password):
            access_token = create_access_token(
                identity=str(user.id_trabajador),
                additional_claims={"rol": user.rol.nombre_rol}
            )
            return {"token": access_token, "usuario": user.nombre}

        abort(401, message="Credenciales incorrectas")

@api_bp.route('/empresa/config')
class ApiEmpresaConfig(MethodView):
    @jwt_required()
    def get(self):
        empresa = Empresa.query.get(1)
        if not empresa:
            abort(404, message="Configuración de empresa no encontrada")
        return {
            "lat": empresa.lat,
            "lng": empresa.lng,
            "radio": empresa.radio,
            "nombre": empresa.nombrecomercial
        }

# Método para modificar la empresa
    @jwt_required()
    def post(self):
        user_id = int(get_jwt_identity())
        trabajador_actual = Trabajador.query.get(user_id)

        # Validar si es admin
        if trabajador_actual.rol.nombre_rol not in ['Administrador', 'Superadministrador']:
            abort(403, message="No tienes permisos de administración")

        data = request.get_json()
        empresa = Empresa.query.get(1)

        if not empresa:
            abort(404, message="Configuración de empresa no encontrada")

        # Actualizamos los valores si se han enviado en el JSON
        if 'radio' in data:
            empresa.radio = float(data['radio'])
        if 'lat' in data:
            empresa.lat = float(data['lat'])
        if 'lng' in data:
            empresa.lng = float(data['lng'])

        db.session.commit()
        return {"msg": "Configuración de la empresa actualizada correctamente"}, 200

@api_bp.route('/auth/change-password')
class ApiChangePassword(MethodView):
    @jwt_required()
    def post(self):
        user_id = get_jwt_identity()
        data = request.get_json()
        trabajador = Trabajador.query.get(int(user_id))

        if trabajador is None:
            return jsonify({"msg": "Su usuario ya no existe en el sistema"}), 404

        current_password = data.get('current_password')
        new_password = data.get('new_password')

        if not trabajador.verify_password(current_password):
            return {"msg": "La contraseña actual es incorrecta"}, 401

        trabajador.password = new_password
        db.session.commit()
        return {"msg": "Contraseña actualizada correctamente"}, 200

@api_bp.route('/presencia/entrada')
class ApiFicharEntrada(MethodView):
    @jwt_required()
    @api_bp.arguments(PresenceInputSchema)
    @api_bp.response(201, MessageSchema)
    def post(self, data):
        user_id = int(get_jwt_identity())
        trabajador = Trabajador.query.get(user_id)
        if trabajador is None: return jsonify({"msg": "Su usuario ya no existe"}), 404

        empresa = Empresa.query.get(1)
        distancia = calcular_distancia(data.get('lat'), data.get('lng'), empresa.lat, empresa.lng)
        if distancia > empresa.radio: abort(400, message=f"Fuera de radio ({int(distancia)}m)")

        ahora_local = datetime.now(timezone_esp)
        dia_semana = ahora_local.weekday() + 1
        hora_actual_str = ahora_local.strftime("%H:%M")
        franjas = Franja.query.filter_by(id_horario=trabajador.idHorario, id_dia=dia_semana).all()

        if not franjas: abort(403, message="Hoy no es día laboral")
        if not any(f.hora_entrada <= hora_actual_str <= f.hora_salida for f in franjas):
            abort(403, message="Fuera de horario de turno")

        if Registro.query.filter_by(id_trabajador=user_id, hora_salida=None).first():
            abort(400, message="Ya tienes una entrada activa")

        # Usamos la hora de España directamente
        hora_exacta_espana = ahora_local.replace(tzinfo=None)
        nuevo = Registro(id_trabajador=user_id, hora_entrada=hora_exacta_espana)
        db.session.add(nuevo)
        db.session.commit()
        return {"msg": "Entrada registrada correctamente"}

@api_bp.route('/presencia/salida')
class ApiFicharSalida(MethodView):
    @jwt_required()
    @api_bp.arguments(PresenceInputSchema)
    @api_bp.response(200, MessageSchema)
    def post(self, data):
        user_id = int(get_jwt_identity())
        trabajador = Trabajador.query.get(int(user_id))
        if trabajador is None: return jsonify({"msg": "Su usuario ya no existe"}), 404

        empresa = Empresa.query.get(1)
        distancia = calcular_distancia(data.get('lat'), data.get('lng'), empresa.lat, empresa.lng)
        if distancia > empresa.radio: abort(400, message=f"Fuera de radio ({int(distancia)}m)")

        registro = Registro.query.filter_by(id_trabajador=user_id, hora_salida=None).first()
        if not registro: abort(400, message="No tienes una entrada activa para cerrar")

        # ARREGLO DE HORA: Usamos la hora de España
        hora_exacta_espana = datetime.now(timezone_esp).replace(tzinfo=None)
        registro.hora_salida = hora_exacta_espana
        db.session.commit()
        return {"msg": "Salida registrada correctamente"}

@api_bp.route('/incidencias')
class ApiRegistrarIncidencia(MethodView):
    @jwt_required()
    @api_bp.arguments(IncidenciaInputSchema)
    @api_bp.response(201, MessageSchema)
    def post(self, data):
        user_id = int(get_jwt_identity())
        trabajador = Trabajador.query.get(int(user_id))

        if trabajador is None:
            return jsonify({"msg": "Su usuario ya no existe en el sistema"}), 404

        incidencia = Incidencia(
            id_trabajador=user_id,
            descripcion=data.get('descripcion'),
            fecha_hora=datetime.utcnow()
        )
        db.session.add(incidencia)
        db.session.commit()
        return {"msg": "Incidencia reportada"}

@api_bp.route('/presencia/estado')
class ApiObtenerEstado(MethodView):
    @jwt_required()
    @api_bp.response(200, EstadoResponseSchema)
    def get(self):
        user_id = int(get_jwt_identity())
        en_activo = Registro.query.filter_by(id_trabajador=user_id, hora_salida=None).first()

        return {
            "fichado": True if en_activo else False,
            "ultima_entrada": en_activo.hora_entrada if en_activo else None
        }

@api_bp.route('/usuario/actualizar-fcm', methods=['POST'])
@jwt_required()
def actualizar_fcm():
    user_id = get_jwt_identity()
    token_fcm = request.json.get('fcm_token')
    if not token_fcm:
        return jsonify({"msg": "Token requerido"}), 400

    db.session.query(Trabajador).filter(Trabajador.fcm_token == token_fcm).update({Trabajador.fcm_token: None})
    trabajador = Trabajador.query.get(int(user_id))
    if trabajador:
        trabajador.fcm_token = token_fcm
        db.session.commit()
        return jsonify({"msg": "Token actualizado correctamente"}), 200
    return jsonify({"msg": "Usuario no encontrado"}), 404

@api_bp.route('/usuario/logout-fcm', methods=['POST'])
@jwt_required()
def logout_fcm():
    user_id = get_jwt_identity()
    trabajador = Trabajador.query.get(int(user_id))
    if trabajador:
        trabajador.fcm_token = None
        db.session.commit()
        return jsonify({"msg": "Sesión de notificaciones cerrada"}), 200
    return jsonify({"msg": "Error"}), 404

@api_bp.route('/presencia/resumen-mensual')
class ApiResumenMensual(MethodView):
    @jwt_required()
    def get(self):
        user_id = int(get_jwt_identity())
        mes = request.args.get('mes')

        if not mes or mes == 'null':
            mes = datetime.now(timezone_esp).strftime("%Y-%m")

        resumen = calcular_resumen_mensual(user_id, mes)
        if isinstance(resumen, tuple):
            return jsonify(resumen[0]), resumen[1]
        return jsonify(resumen), 200

@api_bp.route('/admin/trabajadores')
class ApiAdminTrabajadores(MethodView):
    @jwt_required()
    def get(self):
        user_id = int(get_jwt_identity())
        trabajador_actual = Trabajador.query.get(user_id)
        if not trabajador_actual:
            return {"msg": "Acceso denegado: el usuario ya no existe"}, 404

        if trabajador_actual.rol.nombre_rol not in ['Administrador', 'Superadministrador']:
             return {"msg": "No autorizado"}, 403
        trabajadores = Trabajador.query.all()
        return [{"id_trabajador": t.id_trabajador, "nombre": f"{t.nombre} {t.apellidos}", "email": t.email} for t in trabajadores]

@api_bp.route('/admin/registros')
class ApiAdminRegistros(MethodView):
    @jwt_required()
    def get(self):
        user_id = int(get_jwt_identity())
        trabajador_actual = Trabajador.query.get(user_id)

        if not trabajador_actual:
            return {"msg": "Acceso denegado"}, 404

        if trabajador_actual.rol.nombre_rol not in ['Administrador', 'Superadministrador']:
            return {"msg": "No tienes permisos"}, 403

        # Recogemos el ID del filtro de la URL
        id_filtro_str = request.args.get('id_trabajador')

        query = Registro.query

        # Comprobamos que no sea nulo, ni vacío, ni "null" (texto)
        if id_filtro_str and id_filtro_str.strip().lower() != 'null':
            try:
                # Forzamos la conversión a entero para que SQLAlchemy no falle
                id_entero = int(id_filtro_str.strip())
                query = query.filter(Registro.id_trabajador == id_entero)
            except ValueError:
                pass # Si no era un número válido, ignoramos el filtro

        registros = query.order_by(Registro.hora_entrada.desc()).all()

        resultado = []
        for r in registros:
            total_str = "En curso"
            if r.hora_salida:
                diff = r.hora_salida - r.hora_entrada
                total_seconds = int(diff.total_seconds())
                total_str = f"{total_seconds // 3600}h {(total_seconds % 3600) // 60}m"

            resultado.append({
                "empleado": f"{r.empleado.nombre} {r.empleado.apellidos}",
                "entrada": r.hora_entrada.strftime('%d/%m %H:%M'),
                "salida": r.hora_salida.strftime('%H:%M') if r.hora_salida else "Activo",
                "total": total_str
            })

        return resultado, 200

@api_bp.route('/empresa/configuracion-geo', methods=['GET'])
@jwt_required()
def get_geo_config():
    user_id = get_jwt_identity()
    trabajador = Trabajador.query.get(int(user_id))
    if not trabajador or not trabajador.empresa:
        return jsonify({"msg": "Empresa no encontrada"}), 404

    empresa = trabajador.empresa
    return jsonify({
        "latitud": empresa.lat,
        "longitud": empresa.lng,
        "radio": empresa.radio,
        "nombre": empresa.nombrecomercial
    }), 200

@api_bp.route('/mis-registros')
class ApiMisRegistros(MethodView):
    @jwt_required()
    def get(self):
        user_id = int(get_jwt_identity())
        trabajador_actual = Trabajador.query.get(user_id)

        if not trabajador_actual:
            return {"msg": "Usuario no encontrado"}, 404

        # Buscamos los registros de este usuario
        registros = Registro.query.filter_by(id_trabajador=user_id).order_by(Registro.hora_entrada.desc()).all()

        resultado = []
        for r in registros:
            total_str = "En curso"
            if r.hora_salida:
                diff = r.hora_salida - r.hora_entrada
                total_seconds = int(diff.total_seconds())
                total_str = f"{total_seconds // 3600}h {(total_seconds % 3600) // 60}m"

            resultado.append({
                "empleado": f"{trabajador_actual.nombre}",
                "entrada": r.hora_entrada.strftime('%d/%m %H:%M'),
                "salida": r.hora_salida.strftime('%H:%M') if r.hora_salida else "Activo",
                "total": total_str
            })

        return resultado, 200