from audio import hablar, escuchar
from cerebro import procesar_respuesta

hablar("Sistemas en línea. Llámame por mi nombre si me necesitas.")
print("[Modo reposo: Esperando la palabra 'Chronnos'...]")

while True:
    activacion = escuchar(silencioso=True)
    variantes_nombre = ["cronos", "chronos", "chronnos", "crono"]
    
    if activacion and any(nombre in activacion for nombre in variantes_nombre):
        hablar("Te escucho.")
        
        while True:
            comando = escuchar(silencioso=False)
            
            if comando is None:
                hablar("Entrando en reposo.")
                break
                
            if "apagar sistema" in comando:
                hablar("Desconectando el sistema. Hasta luego.")
                exit()
                
            comandos_dormir = ["descansa", "eso es todo", "gracias", "duerme", "adiós"]
            if any(palabra in comando for palabra in comandos_dormir):
                hablar("De acuerdo, me quedo en segundo plano.")
                break 
                
            print("[Chronnos está pensando...]")
            
            # El cerebro procesa y recuerda, luego el audio lo lee
            respuesta = procesar_respuesta(comando)
            hablar(respuesta)
            
        print("\n[Volviendo al modo reposo... Esperando a 'Chronnos']")