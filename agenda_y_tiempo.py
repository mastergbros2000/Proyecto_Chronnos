import os
import json
import time
import requests
import threading
from datetime import datetime, timedelta

DIRECTORIO_ACTUAL = os.path.dirname(os.path.abspath(__file__))
ARCHIVO_AGENDA = os.path.join(DIRECTORIO_ACTUAL, "agenda.json")
funcion_hablar_callback = None

def registrar_callback_voz(funcion_hablar):
    global funcion_hablar_callback
    funcion_hablar_callback = funcion_hablar

def obtener_fecha_y_hora_actual() -> str:
    ahora = datetime.now()
    dias = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
    meses = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
    dia_semana = dias[ahora.weekday()]
    mes = meses[ahora.month - 1]
    return f"Hoy es {dia_semana} {ahora.day} de {mes} de {ahora.year}, y son las {ahora.strftime('%H:%M')}."

def obtener_ubicacion_actual() -> dict:
    try:
        res = requests.get("http://ip-api.com/json/", timeout=5).json()
        if res.get("status") == "success":
            return {
                "ciudad": res.get("city"),
                "pais": res.get("country"),
                "lat": res.get("lat"),
                "lon": res.get("lon")
            }
    except Exception:
        pass
    return {"ciudad": "Desconocida", "pais": "Desconocido", "lat": 0.0, "lon": 0.0}

def consultar_clima(dias_adelante: int = 0) -> str:
    ubicacion = obtener_ubicacion_actual()
    if ubicacion["lat"] == 0.0:
        return "No pude determinar tu ubicación actual para consultar el clima."

    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={ubicacion['lat']}&longitude={ubicacion['lon']}&daily=temperature_2m_max,temperature_2m_min,precipitation_probability_max&current_weather=true&timezone=auto"
        datos = requests.get(url, timeout=5).json()
        ciudad = ubicacion["ciudad"]
        
        if dias_adelante == 0:
            actual = datos.get("current_weather", {})
            temp = actual.get("temperature")
            if temp is not None:
                return f"En {ciudad} la temperatura actual es de {temp}°C."
        else:
            diario = datos.get("daily", {})
            if len(diario.get("time", [])) > dias_adelante:
                t_max = diario["temperature_2m_max"][dias_adelante]
                t_min = diario["temperature_2m_min"][dias_adelante]
                prob_lluvia = diario["precipitation_probability_max"][dias_adelante]
                etiqueta_dia = "mañana" if dias_adelante == 1 else f"en {dias_adelante} días"
                return f"El pronóstico para {etiqueta_dia} en {ciudad} indica una temperatura máxima de {t_max}°C, mínima de {t_min}°C y {prob_lluvia}% de probabilidad de lluvia."
    except Exception as e:
        print(f"[Error Clima: {e}]")
        
    return "Ocurrió un error al consultar el servicio meteorológico."

def _ejecutar_alerta_temporizador(minutos: float, motivo: str):
    time.sleep(minutos * 60)
    mensaje = f"¡Atención! Ha finalizado el temporizador de {minutos} minutos para: {motivo}."
    print(f"\n🔔 [SISTEMA TEMPORIZADOR]: {mensaje}")
    if funcion_hablar_callback:
        funcion_hablar_callback(mensaje)

def establecer_temporizador(minutos: float, motivo: str = "Temporizador") -> str:
    hilo = threading.Thread(target=_ejecutar_alerta_temporizador, args=(minutos, motivo), daemon=True)
    hilo.start()
    return f"Temporizador programado para {minutos} minutos ({motivo})."

def _cargar_agenda() -> list:
    if os.path.exists(ARCHIVO_AGENDA):
        try:
            with open(ARCHIVO_AGENDA, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def _guardar_agenda(agenda: list):
    with open(ARCHIVO_AGENDA, "w", encoding="utf-8") as f:
        json.dump(agenda, f, ensure_ascii=False, indent=2)

def _programar_alarma_evento(evento: dict):
    try:
        fecha_evento = datetime.strptime(f"{evento['fecha']} {evento['hora']}", "%Y-%m-%d %H:%M")
        segundos_restantes = (fecha_evento - datetime.now()).total_seconds()
        
        if segundos_restantes > 0:
            def _alerta():
                time.sleep(segundos_restantes)
                mensaje = f"Recordatorio: Tienes programado '{evento['titulo']}' a esta hora ({evento['hora']})."
                print(f"\n📅 [SISTEMA AGENDA]: {mensaje}")
                if funcion_hablar_callback:
                    funcion_hablar_callback(mensaje)
                    
            threading.Thread(target=_alerta, daemon=True).start()
    except Exception as e:
        print(f"[Error programando alarma de agenda: {e}]")

def agendar_evento(titulo: str, fecha: str, hora: str) -> str:
    ahora = datetime.now()
    if fecha.lower() == "hoy":
        fecha_str = ahora.strftime("%Y-%m-%d")
    elif fecha.lower() == "mañana":
        fecha_str = (ahora + timedelta(days=1)).strftime("%Y-%m-%d")
    else:
        fecha_str = fecha

    nuevo_evento = {"titulo": titulo, "fecha": fecha_str, "hora": hora}
    agenda = _cargar_agenda()
    agenda.append(nuevo_evento)
    _guardar_agenda(agenda)
    _programar_alarma_evento(nuevo_evento)
    return f"He guardado en tu agenda '{titulo}' para el {fecha_str} a las {hora}."

def consultar_agenda(fecha_busqueda: str = "hoy") -> str:
    ahora = datetime.now()
    if fecha_busqueda.lower() == "hoy":
        fecha_target = ahora.strftime("%Y-%m-%d")
    elif fecha_busqueda.lower() == "mañana":
        fecha_target = (ahora + timedelta(days=1)).strftime("%Y-%m-%d")
    else:
        fecha_target = fecha_busqueda

    agenda = _cargar_agenda()
    eventos_dia = [e for e in agenda if e.get("fecha") == fecha_target]
    if not eventos_dia:
        return f"No tienes ningún compromiso ni recordatorio agendado para {fecha_busqueda}."
    
    res = f"Eventos en tu agenda para {fecha_busqueda}:\n"
    for e in eventos_dia:
        res += f"- {e['hora']}: {e['titulo']}\n"
    return res

def cargar_y_reprogramar_recordatorios_existentes():
    agenda = _cargar_agenda()
    ahora = datetime.now()
    for e in agenda:
        try:
            f_evt = datetime.strptime(f"{e['fecha']} {e['hora']}", "%Y-%m-%d %H:%M")
            if f_evt > ahora:
                _programar_alarma_evento(e)
        except Exception:
            pass
