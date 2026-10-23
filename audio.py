import speech_recognition as sr
import pyttsx3

def hablar(texto):
    texto_limpio = texto.replace("*", "").replace("#", "")
    print(f"Chronnos: {texto_limpio}")
    motor_voz = pyttsx3.init('sapi5')
    motor_voz.setProperty('volume', 1.0)
    motor_voz.setProperty('rate', 150)
    motor_voz.say(texto_limpio)
    motor_voz.runAndWait()

def escuchar(silencioso=False):
    reconocedor = sr.Recognizer()
    reconocedor.pause_threshold = 2.0 
    
    with sr.Microphone() as fuente:
        reconocedor.adjust_for_ambient_noise(fuente, duration=1.0)
        reconocedor.dynamic_energy_threshold = False
        reconocedor.energy_threshold = 250 
        
        if not silencioso:
            print("\n[Escuchando... Ya puedes hablar]")
        
        try:
            audio = reconocedor.listen(fuente, timeout=5)
            texto = reconocedor.recognize_google(audio, language="es-ES")
            if not silencioso:
                print(f"Tú: {texto}")
            return texto.lower()
        except:
            return None