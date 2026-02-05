from flask.views import MethodView
from flask_smorest import Blueprint, abort
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from datetime import datetime
import pytz
from app.extensions import db
from app.models import Trabajador, Registro, Incidencia, Empresa, Franja
from app.utils import calcular_distancia
from app.schemas import (LoginSchema, TokenSchema, PresenceInputSchema,
                         IncidenciaInputSchema, EstadoResponseSchema, MessageSchema)

# El Blueprint ahora es de flask_smorest
api_bp = Blueprint('api', __name__, url_prefix='/api', description='Operaciones de la API móvil')
timezone_esp = pytz.timezone('Europe/Madrid')

@api_bp.route('/auth/login')
class ApiLogin(MethodView):
    @api_bp.arguments(LoginSchema) # Valida los datos de entrada automáticamente
    @api_bp.response(200, TokenSchema) # Formatea la salida
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

@api_bp.route('/presencia/entrada')
class ApiFicharEntrada(MethodView):
    @jwt_required()
    @api_bp.arguments(PresenceInputSchema)
    @api_bp.response(201, MessageSchema)
    def post(self, data):
        user_id = int(get_jwt_identity())
        trabajador = Trabajador.query.get(user_id)

        # Lógica de GPS
        empresa = Empresa.query.get(1)
        distancia = calcular_distancia(data.get('lat'), data.get('lng'), empresa.lat, empresa.lng)
        if distancia > empresa.radio:
            abort(400, message=f"Fuera de radio ({int(distancia)}m)")

        # Lógica de Horario
        ahora_local = datetime.now(timezone_esp)
        dia_semana = ahora_local.weekday() + 1
        hora_actual_str = ahora_local.strftime("%H:%M")
        franjas = Franja.query.filter_by(id_horario=trabajador.idHorario, id_dia=dia_semana).all()

        if not franjas: abort(403, message="Hoy no es día laboral")
        if not any(f.hora_entrada <= hora_actual_str <= f.hora_salida for f in franjas):
            abort(403, message="Fuera de horario de turno")

        if Registro.query.filter_by(id_trabajador=user_id, hora_salida=None).first():
            abort(400, message="Ya tienes una entrada activa")

        nuevo = Registro(id_trabajador=user_id, hora_entrada=datetime.utcnow())
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

        # VALIDACIÓN GPS (Igual que en la entrada)
        empresa = Empresa.query.get(1)
        distancia = calcular_distancia(data.get('lat'), data.get('lng'), empresa.lat, empresa.lng)
        if distancia > empresa.radio:
            abort(400, message=f"Fuera de radio para fichar salida ({int(distancia)}m)")

        registro = Registro.query.filter_by(id_trabajador=user_id, hora_salida=None).first()
        if not registro:
            abort(400, message="No tienes una entrada activa para cerrar")

        registro.hora_salida = datetime.utcnow()
        db.session.commit()
        return {"msg": "Salida registrada correctamente"}

@api_bp.route('/incidencias')
class ApiRegistrarIncidencia(MethodView):
    @jwt_required()
    @api_bp.arguments(IncidenciaInputSchema)
    @api_bp.response(201, MessageSchema)
    def post(self, data):
        user_id = int(get_jwt_identity())
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

        ultima_entrada_local = None
        if en_activo:
            # 1. Obtenemos la hora UTC de la base de datos
            dt_utc = en_activo.hora_entrada.replace(tzinfo=pytz.UTC)
            # 2. La convertimos a la zona horaria de Madrid definida arriba
            ultima_entrada_local = dt_utc.astimezone(timezone_esp)

        return {
            "fichado": True if en_activo else False,
            "ultima_entrada": ultima_entrada_local
        }