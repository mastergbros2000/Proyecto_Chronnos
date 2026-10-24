from audio import hablar, escuchar
from cerebro import generar_con_respaldo

# Saludo inicial del sistema
hablar("Sistemas en línea. Llámame por mi nombre si me necesitas.")
print("[Modo reposo: Esperando la palabra 'Chronnos'...]")

while True:
    activacion = escuchar(silencioso=True)
    variantes_nombre = ["cronos", "chronos", "chronnos", "crono"]
    
    # Aseguramos que la activación se compare en minúsculas
    if activacion and any(nombre in activacion.lower() for nombre in variantes_nombre):
        hablar("Te escucho.")
        
        while True:
            comando = escuchar(silencioso=False)
            
            # Si el reconocedor devuelve None, volvemos al modo reposo
            if comando is None:
                hablar("Entrando en reposo.")
                break
            
            comando_min = comando.lower()
                
            # Comando de salida original (exit)
            if "exit" in comando_min or "salir" in comando_min:
                hablar("Desconectando el sistema. Hasta luego.")
                exit()
                
            # Comandos para mandar a Chronnos a segundo plano / reposo
            comandos_dormir = ["descansa", "eso es todo", "gracias", "duerme", "adiós"]
            if any(palabra in comando_min for palabra in comandos_dormir):
                hablar("De acuerdo, me quedo en segundo plano.")
                break 
                
            print("[Chronnos está pensando...]")
            
            # El cerebro multi-API procesa la consulta y el audio la lee en voz alta
            respuesta = generar_con_respaldo(comando, None)
            hablar(respuesta.text)
            
        print("\n[Volviendo al modo reposo... Esperando a 'Chronnos']")