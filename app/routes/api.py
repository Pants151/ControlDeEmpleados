from flask import Blueprint, jsonify, request
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from datetime import datetime
import pytz
from app.extensions import db
from app.models import Trabajador, Registro, Incidencia, Empresa, Franja
from app.utils import calcular_distancia

api_bp = Blueprint('api', __name__, url_prefix='/api')
timezone_esp = pytz.timezone('Europe/Madrid')

@api_bp.route('/auth/login', methods=['POST'])
def api_login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    user = Trabajador.query.filter((Trabajador.email == email) | (Trabajador.nif == email)).first()
    if user and user.verify_password(password):
        access_token = create_access_token(identity=str(user.id_trabajador), additional_claims={"rol": user.rol.nombre_rol})
        return {"token": access_token, "usuario": user.nombre}, 200
    return {"msg": "Credenciales incorrectas"}, 401

@api_bp.route('/presencia/entrada', methods=['POST'])
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

    # 3. Validar entrada abierta
    if Registro.query.filter_by(id_trabajador=user_id, hora_salida=None).first():
        return {"msg": "Ya tienes una entrada activa"}, 400

    nuevo = Registro(id_trabajador=user_id, hora_entrada=datetime.utcnow())
    db.session.add(nuevo)
    db.session.commit()
    return {"msg": "Entrada registrada correctamente"}, 201

@api_bp.route('/presencia/salida', methods=['POST'])
@jwt_required()
def api_fichar_salida():
    user_id = int(get_jwt_identity())
    ultimo_registro = Registro.query.filter_by(id_trabajador=user_id, hora_salida=None).first()

    if not ultimo_registro:
        return {"msg": "No hay entrada previa abierta"}, 400

    ultimo_registro.hora_salida = datetime.utcnow()
    db.session.commit()
    return {"msg": "Salida registrada correctamente"}, 200

@api_bp.route('/incidencias', methods=['POST'])
@jwt_required()
def api_registrar_incidencia():
    user_id = int(get_jwt_identity())
    data = request.get_json()
    
    if not data.get('descripcion'):
        return {"msg": "Falta descripción"}, 400

    incidencia = Incidencia(id_trabajador=user_id, descripcion=data.get('descripcion'), fecha_hora=datetime.utcnow())
    db.session.add(incidencia)
    db.session.commit()
    return {"msg": "Incidencia reportada"}, 201

@api_bp.route('/presencia/estado', methods=['GET'])
@jwt_required()
def api_obtener_estado():
    user_id = int(get_jwt_identity())
    en_activo = Registro.query.filter_by(id_trabajador=user_id, hora_salida=None).first()
    return {
        "fichado": True if en_activo else False,
        "ultima_entrada": en_activo.hora_entrada.isoformat() if en_activo else None
    }, 200