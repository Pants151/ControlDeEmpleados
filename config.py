import os

class Config:
    SECRET_KEY = 'pon_aqui_una_clave_secreta'
    # Editado con mis credenciales para que lo detecte la web
    SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://jvalnun3004:recursos2002@jvalnun3004.mysql.eu.pythonanywhere-services.com/jvalnun3004$recursos_humanos'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_POOL_RECYCLE = 299
    SQLALCHEMY_ENGINE_OPTIONS = {'pool_pre_ping': True}
    JWT_SECRET_KEY = 'mi_clave_super_secreta'