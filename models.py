from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

# Tabla de franjas
class Franja(db.Model):
    __tablename__ = 'franjas'
    id_dia = db.Column(db.Integer, db.ForeignKey('dia.id'), primary_key=True)
    id_horario = db.Column(db.Integer, db.ForeignKey('horario.id_horario'), primary_key=True)
    hora_entrada = db.Column(db.String(10))
    hora_salida = db.Column(db.String(10))

# Tabla de empresas
class Empresa(db.Model):
    __tablename__ = 'empresa'
    id_empresa = db.Column(db.Integer, primary_key=True)
    nombrecomercial = db.Column(db.String(100))
    cif = db.Column(db.String(20))
    lat = db.Column(db.Float)    # Latitud
    lng = db.Column(db.Float)    # Longitud
    radio = db.Column(db.Float)  # Radio máximo en metros

    domicilio = db.Column(db.String(100))
    localidad = db.Column(db.String(50))
    cp = db.Column(db.String(10))
    provincia = db.Column(db.String(50))
    email = db.Column(db.String(100))
    telefono = db.Column(db.String(20))
    trabajadores = db.relationship('Trabajador', backref='empresa', lazy='dynamic')

# tabla para el control de presencia
class Registro(db.Model):
    __tablename__ = 'registro'
    id_registro = db.Column(db.Integer, primary_key=True)
    hora_entrada = db.Column(db.DateTime, default=datetime.utcnow)
    hora_salida = db.Column(db.DateTime, nullable=True)
    id_trabajador = db.Column(db.Integer, db.ForeignKey('trabajador.id_trabajador'))

# tabla para incidencias
class Incidencia(db.Model):
    __tablename__ = 'incidencia'
    id_incidencia = db.Column(db.Integer, primary_key=True)
    fecha_hora = db.Column(db.DateTime, default=datetime.utcnow)
    descripcion = db.Column(db.String(200))
    id_trabajador = db.Column(db.Integer, db.ForeignKey('trabajador.id_trabajador'))

# Tablas de roles
class Rol(db.Model):
    __tablename__ = 'rol'
    id_rol = db.Column(db.Integer, primary_key=True)
    nombre_rol = db.Column(db.String(50), unique=True)
    trabajadores = db.relationship('Trabajador', backref='rol', lazy='dynamic')

# Tabla de horarios
class Horario(db.Model):
    __tablename__ = 'horario'
    id_horario = db.Column(db.Integer, primary_key=True)
    nombre_horario = db.Column(db.String(50))
    descripcion = db.Column(db.String(200))
    trabajadores = db.relationship('Trabajador', backref='horario', lazy='dynamic')
    franjas = db.relationship('Franja', backref='horario', lazy='dynamic')

# Tabla de dias
class Dia(db.Model):
    __tablename__ = 'dia'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(20))
    franjas = db.relationship('Franja', backref='dia', lazy='dynamic')

# Tabla de trabajadores
class Trabajador(UserMixin, db.Model):
    __tablename__ = 'trabajador'
    id_trabajador = db.Column(db.Integer, primary_key=True)
    nif = db.Column(db.String(20), unique=True)
    nombre = db.Column(db.String(50))
    apellidos = db.Column(db.String(100))
    passw = db.Column(db.String(200)) # Aumentamos longitud para el hash
    email = db.Column(db.String(100), unique=True)
    telef = db.Column(db.String(20))
    direccion = db.Column(db.String(100))
    localidad = db.Column(db.String(50))
    cp = db.Column(db.String(10))
    provincia = db.Column(db.String(50))

    registros = db.relationship('Registro', backref='empleado', lazy='dynamic', cascade="all, delete-orphan")
    incidencias = db.relationship('Incidencia', backref='empleado', lazy='dynamic', cascade="all, delete-orphan")

    idEmpresa = db.Column(db.Integer, db.ForeignKey('empresa.id_empresa'))
    idHorario = db.Column(db.Integer, db.ForeignKey('horario.id_horario'))
    idRol = db.Column(db.Integer, db.ForeignKey('rol.id_rol'))

    # Metodos de Flask-Login
    def get_id(self):
        return (self.id_trabajador)

    # Seguridad de contraseñas
    @property
    def password(self):
        raise AttributeError('La contraseña no es un atributo legible')

    @password.setter
    def password(self, password):
        self.passw = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.passw, password)