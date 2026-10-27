from audio import hablar, escuchar
from cerebro import procesar_respuesta
import sys
import pygame
import time

hablar("Sistemas en línea. Llámame por mi nombre si me necesitas.")
print("[Modo reposo: Esperando la palabra 'Chronnos'...]")

try:
    while True:
        activacion = escuchar(silencioso=True)
        variantes_nombre = ["cronos", "chronos", "chronnos", "crono"]
        
        if activacion and any(nombre in activacion.lower() for nombre in variantes_nombre):
            hablar("Te escucho.")
            
            while True:
                comando = escuchar(silencioso=False)
                
                if comando is None:
                    hablar("Entrando en reposo.")
                    break
                
                comando_min = comando.lower()
                
                # Lista flexible de apagado total del programa
                palabras_apagar = ["apaga", "apagar", "desconectar", "desconecta", "desconéctate", "salir", "finalizar"]
                es_orden_apagar = any(p in comando_min for p in palabras_apagar)
                no_es_cerrar_app = not any(app in comando_min for app in ["ventana", "calculadora", "bloc", "pestana", "pestaña"])
                
                if es_orden_apagar and no_es_cerrar_app:
                    hablar("Desconectando el sistema. Hasta luego.")
                    time.sleep(3.5)
                    pygame.mixer.quit()
                    sys.exit(0)
                    
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
    pygame.mixer.quit()
    sys.exit(0)