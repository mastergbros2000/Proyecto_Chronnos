import os
import time
import datetime
import threading
from dotenv import load_dotenv
from google import genai
from google.genai import types
from PIL import Image

from openai import OpenAI

from control_sistema import abrir_aplicacion, escribir_texto 
from vision import capturar_imagen

load_dotenv() 

# Cargamos las credenciales
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# Inicializamos los clientes
client_gemini = genai.Client(api_key=GOOGLE_API_KEY)

client_deepseek = OpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url="https://api.deepseek.com"
) if DEEPSEEK_API_KEY else None

# Cliente universal de OpenRouter (apunta a su pasarela)
client_openrouter = OpenAI(
    api_key=OPENROUTER_API_KEY,
    base_url="https://openrouter.ai/api/v1"
) if OPENROUTER_API_KEY else None

# Modelos gratuitos de Gemini para el enrutador de complejidad
MODELO_RAPIDO = "gemini-1.5-flash"
MODELO_COMPLEJO = "gemini-1.5-pro"

modo_reposo = False
hora_despertar = None

memoria_conversacion = (
    "Eres Chronnos, mi asistente de voz de Inteligencia Artificial. "
    "Responde siempre de forma natural, directa, muy concisa y humana. "
    "Actúa de forma proactiva y amigable.\n\n"
)

class RespuestaFalsa:
    def __init__(self, mensaje):
        self.text = mensaje
        self.function_calls = None

# ==========================================
# CONEXIONES DE APIS
# ==========================================
def llamar_api_gemini(contenido_a_enviar, config_herramientas, modelo=MODELO_RAPIDO):
    """Llama a Gemini permitiendo elegir entre Flash (rápido) y Pro (complejo)."""
    return client_gemini.models.generate_content(
        model=modelo, 
        contents=contenido_a_enviar,
        config=config_herramientas
    )

def llamar_api_deepseek(contenido_a_enviar, config_herramientas):
    """Mantenemos la función de DeepSeek por si le agregas saldo a la API en el futuro."""
    if not client_deepseek:
        raise Exception("API Key de DeepSeek no configurada")
    
    texto_prompt = contenido_a_enviar[0] if isinstance(contenido_a_enviar, list) else contenido_a_enviar
    
    respuesta = client_deepseek.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "user", "content": texto_prompt}],
        stream=False
    )
    
    class AdaptadorRespuestaDeepSeek:
        def __init__(self, texto):
            self.text = texto
            self.function_calls = None
            
    return AdaptadorRespuestaDeepSeek(respuesta.choices[0].message.content)

def llamar_api_openrouter(contenido_a_enviar, config_herramientas, modelo="openrouter/free"):
    """Llama a modelos 100% gratuitos a través de OpenRouter."""
    if not client_openrouter:
        raise Exception("API Key de OpenRouter no configurada")
    
    texto_prompt = contenido_a_enviar[0] if isinstance(contenido_a_enviar, list) else contenido_a_enviar
    
    respuesta = client_openrouter.chat.completions.create(
        model=modelo, 
        messages=[
            {"role": "system", "content": memoria_conversacion},
            {"role": "user", "content": texto_prompt}
        ],
        stream=False
    )
    
    class AdaptadorRespuestaOpenRouter:
        def __init__(self, texto):
            self.text = texto
            self.function_calls = None
            
    return AdaptadorRespuestaOpenRouter(respuesta.choices[0].message.content)

# ==========================================
# EL COORDINADOR MULTI-API (ENRUTADOR INTELIGENTE)
# ==========================================
def analizar_complejidad(texto_prompt):
    """Decide automáticamente qué modelo de Gemini usar según la complejidad."""
    palabras_clave_complejas = ["analiza", "profundidad", "informe", "código", "programa", "resume", "compara", "explica"]
    texto_min = str(texto_prompt).lower()
    
    for palabra in palabras_clave_complejas:
        if palabra in texto_min:
            return MODELO_COMPLEJO # Tarea difícil -> Usar Gemini 1.5 Pro
            
    return MODELO_RAPIDO # Tarea fácil -> Usar Gemini 1.5 Flash

def generar_con_respaldo(contenido_a_enviar, config_herramientas):
    texto_prompt = contenido_a_enviar[0] if isinstance(contenido_a_enviar, list) else contenido_a_enviar
    
    # 1. Enrutamiento automático por complejidad
    modelo_gemini_elegido = analizar_complejidad(texto_prompt)
    print(f"\n[Cerebro Coordinador: Evaluando complejidad... Asignado a {modelo_gemini_elegido}]")
    
    # 2. Lista de APIs a probar (100% Gratuitas)
    apis_a_probar = [
        {"nombre": f"Gemini ({modelo_gemini_elegido})", "funcion": lambda cont, conf: llamar_api_gemini(cont, conf, modelo_gemini_elegido)},
        {"nombre": "OpenRouter Automático (:free)", "funcion": lambda cont, conf: llamar_api_openrouter(cont, conf, "openrouter/free")},
        {"nombre": "Gemma (vía OpenRouter)", "funcion": lambda cont, conf: llamar_api_openrouter(cont, conf, "google/gemma-4-31b-it:free")}
    ]
    
    # 3. Tolerancia a fallos: Intenta cada una hasta tener éxito
    for api in apis_a_probar:
        print(f"[Coordinador: Intentando procesar con {api['nombre']}...]")
        try:
            respuesta = api["funcion"](contenido_a_enviar, config_herramientas)
            print(f"[Coordinador: ¡Éxito con {api['nombre']}!]")
            return respuesta
        except Exception as e:
            # Corregido el salto de línea que generaba el error de sintaxis
            print(f"[Coordinador: Fallo en {api['nombre']} - {str(e)}]")
            
    return RespuestaFalsa("Lo siento, todas mis conexiones gratuitas fallaron en este momento.")