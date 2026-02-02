from marshmallow import Schema, fields

class LoginSchema(Schema):
    email = fields.Str(required=True)
    password = fields.Str(required=True)

class TokenSchema(Schema):
    token = fields.Str(dump_only=True)
    usuario = fields.Str(dump_only=True)

class PresenceInputSchema(Schema):
    lat = fields.Float(required=True)
    lng = fields.Float(required=True)

class IncidenciaInputSchema(Schema):
    descripcion = fields.Str(required=True)

class EstadoResponseSchema(Schema):
    fichado = fields.Bool(dump_only=True)
    ultima_entrada = fields.DateTime(dump_only=True, format="%d/%m/%Y %H:%M")

class MessageSchema(Schema):
    msg = fields.Str(dump_only=True)