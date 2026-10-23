import speech_recognition as sr
import pyttsx3
from google import genai
import os
from dotenv import load_dotenv

load_dotenv()  
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
client = genai.Client(api_key=GOOGLE_API_KEY)
MODELO_RAPIDO = "gemini-3.6-flash"
MODELO_COMPLEJO = "gemini-3.6-flash"

# --- NUEVO: Memoria Base (Personalidad) ---
memoria_conversacion = (
    "Eres Chronnos, mi asistente de voz de Inteligencia Artificial. "
    "Responde siempre de forma natural, directa, muy concisa y humana. "
    "JAMÁS uses formatos matemáticos complejos, variables algebraicas, ecuaciones, ni símbolos especiales "
    "(como asteriscos, guiones, o $$) porque tus respuestas serán leídas en voz alta por un motor de audio. "
    "Actúa de forma proactiva y amigable.\n\n"
)

def enrutar_consulta(mensaje):
    palabras_complejas = ["analiza", "informe", "profundidad", "código", "resumen detallado"]
    if any(palabra in mensaje for palabra in palabras_complejas):
        return MODELO_COMPLEJO
    return MODELO_RAPIDO

# 2. Configuración de la Voz (TTS)
def hablar(texto):
    texto_limpio = texto.replace("*", "").replace("#", "")
    print(f"Chronnos: {texto_limpio}")
    motor_voz = pyttsx3.init('sapi5')
    motor_voz.setProperty('volume', 1.0)
    motor_voz.setProperty('rate', 150)
    motor_voz.say(texto_limpio)
    motor_voz.runAndWait()

# 3. Configuración de los Oídos (STT) adaptada para Wake-word
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

# 4. Ciclo Principal de Wake-word
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
            
            # --- NUEVO: Memoria de Corto Plazo (Historial en vivo) ---
            # Agregamos lo que tú dijiste a la memoria
            memoria_conversacion += f"Usuario: {comando}\nChronnos: "
            
            modelo_elegido = enrutar_consulta(comando)
            
            # Ahora enviamos TODA LA MEMORIA a Gemini, no solo el comando aislado
            respuesta = client.models.generate_content(
                model=modelo_elegido, 
                contents=memoria_conversacion 
            )
            
            # Agregamos la respuesta a la memoria para que la recuerde en la siguiente ronda
            memoria_conversacion += f"{respuesta.text}\n\n"
            # ---------------------------------------------------------
            
            hablar(respuesta.text)
            
        print("\n[Volviendo al modo reposo... Esperando a 'Chronnos']")