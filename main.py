import sys
import pygame
import time
import re

from audio import hablar, escuchar
from cerebro import procesar_respuesta
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

try:
    while True:
        activacion = escuchar(silencioso=True)
        
        if activacion:
            activacion_limpia = re.sub(r'[^\w\s]', '', activacion.lower())
            variantes_nombre = ["cronos", "chronos", "chronnos", "crono", "kronos", "krono", "clonos"]
            
            if any(nombre in activacion_limpia for nombre in variantes_nombre):
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
                    respuesta_texto = procesar_respuesta(comando)
                    hablar(respuesta_texto)
                    
                print("\n[Volviendo al modo reposo... Esperando a 'Chronnos']")

except KeyboardInterrupt:
    print("\n[Sistema: Interrupción manual detectada (Ctrl+C). Apagando Chronnos de forma segura...]")
    cerrar_navegador()
    pygame.mixer.quit()
    sys.exit(0)
