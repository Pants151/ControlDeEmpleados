# app/tasks.py
from datetime import datetime, timedelta
from app.models import Trabajador, Registro, Franja # Importamos Franja según tu models.py
from app.utils_notifications import enviar_notificacion_fcm

def verificar_fichajes_olvidados():
    ahora = datetime.now()

    id_dia_hoy = ahora.weekday() + 1

    # Buscamos trabajadores que tengan el token del móvil guardado
    trabajadores = Trabajador.query.filter(Trabajador.fcm_token.isnot(None)).all()
    print(f"[{ahora}] Iniciando chequeo para {len(trabajadores)} trabajadores...")

    for t in trabajadores:
        # Buscamos la franja de entrada para este trabajador y para el día de hoy
        franja_hoy = Franja.query.filter_by(id_horario=t.idHorario, id_dia=id_dia_hoy).first()

        if not franja_hoy or not franja_hoy.hora_entrada:
            continue # No tiene turno hoy

        try:
            # Convertimos la hora de entrada a un objeto datetime para comparar
            # Usamos strip() por si acaso hay espacios en el String
            h_entrada_obj = datetime.strptime(franja_hoy.hora_entrada.strip(), "%H:%M").time()

            # Creamos un datetime completo de hoy con esa hora de entrada
            dt_entrada_hoy = ahora.replace(hour=h_entrada_obj.hour, minute=h_entrada_obj.minute, second=0, microsecond=0)

            # Calculamos la hora límite (Hora de entrada + 10 minutos)
            limite_aviso = dt_entrada_hoy + timedelta(minutes=10)

            # ¿Ya han pasado los 10 minutos de cortesía?
            if ahora >= limite_aviso:

                # ¿Ha fichado ya hoy?
                # Buscamos registros de este trabajador creados desde las 00:00 de hoy
                hoy_inicio = ahora.replace(hour=0, minute=0, second=0, microsecond=0)
                fichaje_hoy = Registro.query.filter(
                    Registro.id_trabajador == t.id_trabajador,
                    Registro.hora_entrada >= hoy_inicio
                ).first()

                if not fichaje_hoy:
                    # ¡ALERTA! No ha fichado.
                    print(f"   > Notificando a {t.nombre} (Entrada: {franja_hoy.hora_entrada})")
                    enviar_notificacion_fcm(
                        t.fcm_token,
                        "⚠️ Olvido de Fichaje",
                        f"Hola {t.nombre}, tu jornada empezaba a las {franja_hoy.hora_entrada}. ¡No olvides fichar!"
                    )
                else:
                    print(f"   > {t.nombre} ya tiene registro de hoy.")
            else:
                print(f"   > {t.nombre} entra a las {franja_hoy.hora_entrada}, aún falta para el aviso.")

        except Exception as e:
            print(f"   > Error procesando a {t.nombre}: {str(e)}")