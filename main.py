from audio import hablar, escuchar
from cerebro import generar_con_respaldo
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
                    
                if "apagar sistema" in comando_min:
                    hablar("Desconectando el sistema. Hasta luego.")
                    # 1. Damos tiempo para que termine de hablar
                    time.sleep(3.5)
                    # 2. Apagamos el motor de audio a la fuerza
                    pygame.mixer.quit()
                    # 3. Cerramos Python de forma absoluta
                    sys.exit(0)
                    
                comandos_dormir = ["descansa", "eso es todo", "gracias", "duerme", "adiós"]
                if any(palabra in comando_min for palabra in comandos_dormir):
                    hablar("De acuerdo, me quedo en segundo plano.")
                    break 
                    
                print("[Chronnos está pensando...]")
                
                respuesta = generar_con_respaldo(comando, None)
                hablar(respuesta.text)
                
            print("\n[Volviendo al modo reposo... Esperando a 'Chronnos']")

except KeyboardInterrupt:
    print("\n[Sistema: Interrupción manual detectada (Ctrl+C). Apagando Chronnos de forma segura...]")
    pygame.mixer.quit()
    sys.exit(0)