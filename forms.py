from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField
from wtforms.validators import DataRequired, Email, Length

class LoginForm(FlaskForm):
    email = StringField('Email o NIF', validators=[DataRequired(), Email()])
    password = PasswordField('Contraseña', validators=[DataRequired()])
    submit = SubmitField('Entrar')

class EmpresaForm(FlaskForm):
    nombrecomercial = StringField('Nombre Comercial', validators=[DataRequired(), Length(max=100)])
    cif = StringField('CIF', validators=[DataRequired(), Length(max=20)])
    lat = StringField('Latitud (Ej: 36.5126)', validators=[DataRequired()])
    lng = StringField('Longitud (Ej: -4.8845)', validators=[DataRequired()])
    radio = StringField('Radio permitido (metros)', validators=[DataRequired()])
    domicilio = StringField('Domicilio', validators=[Length(max=100)])
    localidad = StringField('Localidad', validators=[Length(max=50)])
    cp = StringField('Código Postal', validators=[Length(max=10)])
    provincia = StringField('Provincia', validators=[Length(max=50)])
    email = StringField('Email', validators=[Length(max=100)])
    telefono = StringField('Teléfono', validators=[Length(max=20)])
    submit = SubmitField('Guardar Empresa')

class RolForm(FlaskForm):
    nombre_rol = StringField('Nombre del Rol', validators=[DataRequired(), Length(max=50)])
    submit = SubmitField('Guardar Rol')

class TrabajadorForm(FlaskForm):
    nif = StringField('NIF', validators=[DataRequired(), Length(max=20)])
    nombre = StringField('Nombre', validators=[DataRequired(), Length(max=50)])
    apellidos = StringField('Apellidos', validators=[DataRequired(), Length(max=100)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Contraseña (dejar vacía si no se quiere cambiar)')
    telef = StringField('Teléfono')
    direccion = StringField('Dirección', validators=[Length(max=100)])
    localidad = StringField('Localidad', validators=[Length(max=50)])
    cp = StringField('Código Postal', validators=[Length(max=10)])
    provincia = StringField('Provincia', validators=[Length(max=50)])

    rol_id = SelectField('Rol', coerce=int)
    horario_id = SelectField('Horario', coerce=int)

    submit = SubmitField('Guardar Empleado')

class HorarioForm(FlaskForm):
    nombre_horario = StringField('Nombre del Horario', validators=[DataRequired(), Length(max=50)])
    descripcion = StringField('Descripción', validators=[Length(max=200)])
    submit = SubmitField('Guardar Horario')

class FranjaForm(FlaskForm):
    dia_id = SelectField('Día de la semana', coerce=int)
    hora_entrada = StringField('Hora Entrada', validators=[DataRequired()], render_kw={"type": "time"})
    hora_salida = StringField('Hora Salida', validators=[DataRequired()], render_kw={"type": "time"})
    submit = SubmitField('Añadir Franja')

# Registro para poder crear una cuenta nueva, en el caso de que no la sepas.
class RegistroForm(FlaskForm):
    nombre = StringField('Nombre', validators=[DataRequired(), Length(max=50)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Contraseña', validators=[DataRequired()])
    rol_id = SelectField('Rol', coerce=int)
    submit = SubmitField('Registrarse')