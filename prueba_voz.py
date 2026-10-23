import pyttsx3

def hablar(texto):
    # Inicializar forzando el motor nativo de Windows ('sapi5')
    engine = pyttsx3.init('sapi5')
    
    # Asegurar que el volumen esté al 100% (1.0)
    engine.setProperty('volume', 1.0)
    
    # Ajustar la velocidad
    engine.setProperty('rate', 150) 
    
    print(f"Chronnos dice: {texto}")
    engine.say(texto)
    engine.runAndWait()

hablar("Hola. Soy Chronnos, y por fin tengo voz. ¿Me escuchas bien?")