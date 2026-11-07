import sys
import pygame
import time
import re
import unicodedata

from audio import (
    hablar, 
    hablar_stream, 
    escuchar, 
    reproducir_chime_activacion, 
    reproducir_chime_ejecucion
)
from cerebro import procesar_respuesta, generar_stream_oraciones, interrupcion_stream
from agenda_y_tiempo import registrar_callback_voz, cargar_y_reprogramar_recordatorios_existentes
from navegador_web import cerrar_navegador

# Enlace proactivo de alarmas y agenda con el sintetizador de voz
registrar_callback_voz(hablar)
cargar_y_reprogramar_recordatorios_existentes()

hablar("Sistemas en línea. Llámame por mi nombre si me necesitas.")
print("[Modo reposo: Esperando la palabra 'Chronnos'...]")

def apagar_sistema():
    hablar("Desconectando el sistema. Hasta luego.")
    time.sleep(2.0)
    cerrar_navegador()
    pygame.mixer.quit()
    sys.exit(0)

VARIANTES_CRONOS = {
    "cronos", "chronos", "chronnos", "crono", "chrono", "kronos", "krono", 
    "clonos", "clono", "coronos", "trono", "tronos", "cronus", "kronus",
    "prono", "pronos", "conos", "cono", "colonos"
}

def normalizar_wake_word(texto: str) -> list[str]:
    """Limpia estrictamente signos de puntuación, acentos y símbolos dejando palabras limpias."""
    if not texto:
        return []
    texto_sin_acentos = "".join(
        c for c in unicodedata.normalize('NFD', texto.lower().strip())
        if unicodedata.category(c) != 'Mn'
    )
    tokens = re.findall(r'[a-z0-9]+', texto_sin_acentos)
    return tokens

try:
    while True:
        # Escucha en reposo optimizada para captar la palabra aislada en milisegundos
        activacion = escuchar(silencioso=True, es_wake_word=True)
        
        if activacion:
            palabras = normalizar_wake_word(activacion)
            # Detección ultra-sensible de Cronos aislado o en frase
            cadena_unida = "".join(palabras)
            es_cronos = (
                any(p in VARIANTES_CRONOS for p in palabras) or 
                any(raiz in cadena_unida for raiz in ["crono", "chrono", "krono", "clono"])
            )
            
            if es_cronos:
                reproducir_chime_activacion()
                hablar("Te escucho.")
                
                while True:
                    comando = escuchar(silencioso=False)
                    
                    if comando is None:
                        hablar("Entrando en reposo.")
                        break
                    
                    comando_min = comando.lower()
                    
                    palabras_apagar = ["apaga", "apagar", "desconectar", "desconecta", "desconéctate", "salir", "finalizar"]
                    es_orden_apagar = any(p in comando_min for p in palabras_apagar)
                    no_es_cerrar_app = not any(app in comando_min for app in ["ventana", "calculadora", "bloc", "pestana", "pestaña"])
                    
                    if es_orden_apagar and no_es_cerrar_app:
                        apagar_sistema()
                        
                    comandos_dormir = ["descansa", "eso es todo", "gracias", "duerme", "adiós", "adios"]
                    if any(palabra in comando_min for palabra in comandos_dormir):
                        hablar("De acuerdo, me quedo en segundo plano.")
                        break 
                        
                    print("[Chronnos está pensando...]")
                    interrupcion_stream.clear()
                    respuesta = procesar_respuesta(comando)
                    # Si procesar_respuesta devuelve texto plano (ruta de herramientas/visión),
                    # se reproduce el chime de ejecución exitosa y se habla directamente.
                    # Si devuelve un generador (ruta conversacional), se usa hablar_stream.
                    if isinstance(respuesta, str):
                        reproducir_chime_ejecucion()
                        hablar(respuesta)
                    else:
                        hablar_stream(respuesta)
                    
                print("\n[Volviendo al modo reposo... Esperando a 'Chronnos']")

except KeyboardInterrupt:
    print("\n[Sistema: Interrupción manual detectada (Ctrl+C). Apagando Chronnos de forma segura...]")
    cerrar_navegador()
    pygame.mixer.quit()
    sys.exit(0)
