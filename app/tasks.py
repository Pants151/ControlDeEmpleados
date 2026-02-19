from datetime import datetime, timedelta
import pytz
from app.models import Trabajador, Registro, Franja 
from app.utils_notifications import enviar_notificacion_fcm

def verificar_fichajes_olvidados():
    # Usamos la zona horaria de España para evitar fallos con el servidor
    timezone_esp = pytz.timezone('Europe/Madrid')
    ahora = datetime.now(timezone_esp)
    id_dia_hoy = ahora.weekday() + 1
    hoy_inicio = ahora.replace(hour=0, minute=0, second=0, microsecond=0)

    trabajadores = Trabajador.query.filter(Trabajador.fcm_token.isnot(None)).all()
    print(f"[{ahora.strftime('%H:%M:%S')}] Chequeo de notificaciones para {len(trabajadores)} trabajadores...")

    for t in trabajadores:
        franja_hoy = Franja.query.filter_by(id_horario=t.idHorario, id_dia=id_dia_hoy).first()
        if not franja_hoy:
            continue # No trabaja hoy

        try:
            # COMPROBAR OLVIDO DE ENTRADA
            if franja_hoy.hora_entrada:
                h_entrada_obj = datetime.strptime(franja_hoy.hora_entrada.strip(), "%H:%M").time()
                dt_entrada = ahora.replace(hour=h_entrada_obj.hour, minute=h_entrada_obj.minute, second=0, microsecond=0)
                limite_aviso_ent = dt_entrada + timedelta(minutes=10) # 10 min de cortesía
                fin_ventana_ent = limite_aviso_ent + timedelta(minutes=50) # Dejamos de spamear tras 1 hora

                # Si estamos dentro de la ventana donde debemos avisar
                if limite_aviso_ent <= ahora <= fin_ventana_ent:
                    fichaje_hoy = Registro.query.filter(
                        Registro.id_trabajador == t.id_trabajador,
                        Registro.hora_entrada >= hoy_inicio
                    ).first()

                    if not fichaje_hoy:
                        print(f"   > Aviso ENTRADA a {t.nombre}")
                        enviar_notificacion_fcm(
                            t.fcm_token,
                            "⚠️ Olvido de Fichaje",
                            f"Hola {t.nombre}, tu turno empezó a las {franja_hoy.hora_entrada} y no has fichado."
                        )

            # 2. COMPROBAR OLVIDO DE SALIDA
            if franja_hoy.hora_salida:
                h_salida_obj = datetime.strptime(franja_hoy.hora_salida.strip(), "%H:%M").time()
                dt_salida = ahora.replace(hour=h_salida_obj.hour, minute=h_salida_obj.minute, second=0, microsecond=0)
                limite_aviso_sal = dt_salida + timedelta(minutes=10) # 10 min de cortesía
                fin_ventana_sal = limite_aviso_sal + timedelta(minutes=50) # Evitar spam

                if limite_aviso_sal <= ahora <= fin_ventana_sal:
                    # Buscamos un registro de HOY que siga ABIERTO (hora_salida == None)
                    registro_abierto = Registro.query.filter(
                        Registro.id_trabajador == t.id_trabajador,
                        Registro.hora_entrada >= hoy_inicio,
                        Registro.hora_salida == None
                    ).first()

                    if registro_abierto:
                        print(f"   > Aviso SALIDA a {t.nombre}")
                        enviar_notificacion_fcm(
                            t.fcm_token,
                            "⚠️ Olvido de Salida",
                            f"{t.nombre}, tu turno acabó a las {franja_hoy.hora_salida}. ¡No olvides cerrar el fichaje!"
                        )

        except Exception as e:
            print(f"   > Error procesando a {t.nombre}: {str(e)}")