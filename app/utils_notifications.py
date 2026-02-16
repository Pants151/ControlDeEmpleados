import firebase_admin
from firebase_admin import credentials, messaging
import os

# Ruta al archivo de Firebase
path_to_json = os.path.join(os.path.dirname(__file__), '../firebase-service-account.json')

if not firebase_admin._apps:
    cred = credentials.Certificate(path_to_json)
    firebase_admin.initialize_app(cred)

def enviar_notificacion_fcm(token_dispositivo, titulo, cuerpo):
    if not token_dispositivo:
        return

    message = messaging.Message(
        notification=messaging.Notification(
            title=titulo,
            body=cuerpo,
        ),
        token=token_dispositivo,
    )

    try:
        response = messaging.send(message)
        print('Notificación enviada con éxito:', response)
    except Exception as e:
        print('Error enviando notificación:', e)