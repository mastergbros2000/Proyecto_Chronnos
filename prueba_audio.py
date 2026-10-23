import speech_recognition as sr

def escuchar():
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        print("Ajustando el ruido de fondo... un segundo.")
        recognizer.adjust_for_ambient_noise(source)
        print("Escuchando... ¡Di algo a Chronnos!")
        
        try:
            # Agregamos phrase_time_limit por si hablas mucho rato
            audio = recognizer.listen(source, timeout=5, phrase_time_limit=15)
            texto = recognizer.recognize_google(audio, language="es-ES")
            print(f"Has dicho: {texto}")
        
        except sr.WaitTimeoutError:
            print("No detecté ninguna voz. El tiempo de espera se agotó.")
        except sr.UnknownValueError:
            print("El sistema no pudo entender el audio.")
        except sr.RequestError:
            print("Error al conectar con el servicio de reconocimiento.")

escuchar()