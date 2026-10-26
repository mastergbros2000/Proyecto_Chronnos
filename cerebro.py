import os
import time
import datetime
import threading
from dotenv import load_dotenv
from google import genai
from google.genai import types
from PIL import Image

from openai import OpenAI
import cohere
from huggingface_hub import InferenceClient

from control_sistema import abrir_aplicacion, escribir_texto 
from vision import capturar_imagen

load_dotenv() 

# Cargamos las credenciales 100% gratuitas
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
COHERE_API_KEY = os.getenv("COHERE_API_KEY")
HUGGINGFACE_API_KEY = os.getenv("HUGGINGFACE_API_KEY")
GITHUB_MODELS_API_KEY = os.getenv("GITHUB_MODELS_API_KEY")
SAMBANOVA_API_KEY = os.getenv("SAMBANOVA_API_KEY")

# Inicializamos los clientes
client_gemini = genai.Client(api_key=GOOGLE_API_KEY) if GOOGLE_API_KEY else None

client_openrouter = OpenAI(
    api_key=OPENROUTER_API_KEY,
    base_url="https://openrouter.ai/api/v1"
) if OPENROUTER_API_KEY else None

client_cohere = cohere.ClientV2(COHERE_API_KEY) if COHERE_API_KEY else None

client_hf = InferenceClient(api_key=HUGGINGFACE_API_KEY) if HUGGINGFACE_API_KEY else None

client_github = OpenAI(
    api_key=GITHUB_MODELS_API_KEY,
    base_url="https://models.inference.ai.azure.com"
) if GITHUB_MODELS_API_KEY else None

# Inicializamos SambaNova
client_sambanova = OpenAI(
    api_key=SAMBANOVA_API_KEY,
    base_url="https://api.sambanova.ai/v1"
) if SAMBANOVA_API_KEY else None

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
def llamar_api_gemini(contenido_a_enviar, config_herramientas, modelo):
    if not client_gemini:
        raise Exception("API Key de Gemini no configurada")
    return client_gemini.models.generate_content(
        model=modelo, 
        contents=contenido_a_enviar,
        config=config_herramientas
    )

def llamar_api_openrouter(contenido_a_enviar, config_herramientas, modelo):
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

def llamar_api_cohere(contenido_a_enviar, config_herramientas, modelo):
    if not client_cohere:
        raise Exception("API Key de Cohere no configurada")
    
    texto_prompt = contenido_a_enviar[0] if isinstance(contenido_a_enviar, list) else contenido_a_enviar
    respuesta = client_cohere.chat(
        model=modelo,
        messages=[
            {"role": "system", "content": memoria_conversacion},
            {"role": "user", "content": texto_prompt}
        ]
    )
    class AdaptadorRespuestaCohere:
        def __init__(self, texto):
            self.text = texto
            self.function_calls = None
    return AdaptadorRespuestaCohere(respuesta.message.content[0].text)

def llamar_api_huggingface(contenido_a_enviar, config_herramientas, modelo):
    if not client_hf:
        raise Exception("API Key de Hugging Face no configurada")
    
    texto_prompt = contenido_a_enviar[0] if isinstance(contenido_a_enviar, list) else contenido_a_enviar
    
    respuesta = client_hf.chat_completion(
        model=modelo,
        messages=[
            {"role": "system", "content": memoria_conversacion},
            {"role": "user", "content": texto_prompt}
        ],
        max_tokens=800
    )
    
    class AdaptadorRespuestaHF:
        def __init__(self, texto):
            self.text = texto
            self.function_calls = None
            
    return AdaptadorRespuestaHF(respuesta.choices[0].message.content)

def llamar_api_github(contenido_a_enviar, config_herramientas, modelo):
    if not client_github:
        raise Exception("API Key de GitHub Models no configurada")
    
    texto_prompt = contenido_a_enviar[0] if isinstance(contenido_a_enviar, list) else contenido_a_enviar
    
    respuesta = client_github.chat.completions.create(
        model=modelo,
        messages=[
            {"role": "system", "content": memoria_conversacion},
            {"role": "user", "content": texto_prompt}
        ],
        stream=False
    )
    
    class AdaptadorRespuestaGitHub:
        def __init__(self, texto):
            self.text = texto
            self.function_calls = None
            
    return AdaptadorRespuestaGitHub(respuesta.choices[0].message.content)

def llamar_api_sambanova(contenido_a_enviar, config_herramientas, modelo):
    if not client_sambanova:
        raise Exception("API Key de SambaNova no configurada")
    
    texto_prompt = contenido_a_enviar[0] if isinstance(contenido_a_enviar, list) else contenido_a_enviar
    
    respuesta = client_sambanova.chat.completions.create(
        model=modelo,
        messages=[
            {"role": "system", "content": memoria_conversacion},
            {"role": "user", "content": texto_prompt}
        ],
        stream=False
    )
    
    class AdaptadorRespuestaSambaNova:
        def __init__(self, texto):
            self.text = texto
            self.function_calls = None
            
    return AdaptadorRespuestaSambaNova(respuesta.choices[0].message.content)

# ==========================================
# EL COORDINADOR MULTI-API (ENRUTADOR INTELIGENTE)
# ==========================================
def analizar_complejidad(texto_prompt):
    palabras_clave_complejas = ["analiza", "profundidad", "informe", "código", "programa", "resume", "compara", "explica"]
    texto_min = str(texto_prompt).lower()
    for palabra in palabras_clave_complejas:
        if palabra in texto_min:
            return "COMPLEJO" 
    return "RAPIDO"

def generar_con_respaldo(contenido_a_enviar, config_herramientas):
    texto_prompt = contenido_a_enviar[0] if isinstance(contenido_a_enviar, list) else contenido_a_enviar
    
    nivel_complejidad = analizar_complejidad(texto_prompt)
    print(f"\n[Cerebro Coordinador: Nivel de complejidad evaluado -> {nivel_complejidad}]")
    
    if nivel_complejidad == "COMPLEJO":
        modelo_sambanova = "Meta-Llama-3.1-405B-Instruct" 
        modelo_github = "gpt-4o" 
        modelo_gemini = "gemini-1.5-pro"
        modelo_cohere = "command-r-plus-08-2024"
        modelo_openrouter = "google/gemma-4-31b-it:free"
        modelo_hf = "mistralai/Mixtral-8x7B-Instruct-v0.1"
        
        apis_a_probar = [
            {"nombre": f"SambaNova ({modelo_sambanova})", "funcion": lambda cont, conf: llamar_api_sambanova(cont, conf, modelo_sambanova)},
            {"nombre": f"GitHub Models ({modelo_github})", "funcion": lambda cont, conf: llamar_api_github(cont, conf, modelo_github)},
            {"nombre": f"Gemini ({modelo_gemini})", "funcion": lambda cont, conf: llamar_api_gemini(cont, conf, modelo_gemini)},
            {"nombre": f"Cohere ({modelo_cohere})", "funcion": lambda cont, conf: llamar_api_cohere(cont, conf, modelo_cohere)},
            {"nombre": f"OpenRouter ({modelo_openrouter})", "funcion": lambda cont, conf: llamar_api_openrouter(cont, conf, modelo_openrouter)},
            {"nombre": f"Hugging Face ({modelo_hf})", "funcion": lambda cont, conf: llamar_api_huggingface(cont, conf, modelo_hf)}
        ]
    else:
        modelo_github = "gpt-4o-mini" 
        modelo_gemini = "gemini-1.5-flash"
        modelo_sambanova = "Meta-Llama-3.1-8B-Instruct" 
        modelo_openrouter = "openrouter/free" 
        modelo_cohere = "command-r-08-2024" 
        modelo_hf = "mistralai/Mistral-7B-Instruct-v0.3" 
        
        apis_a_probar = [
            {"nombre": f"GitHub Models ({modelo_github})", "funcion": lambda cont, conf: llamar_api_github(cont, conf, modelo_github)},
            {"nombre": f"Gemini ({modelo_gemini})", "funcion": lambda cont, conf: llamar_api_gemini(cont, conf, modelo_gemini)},
            {"nombre": f"SambaNova ({modelo_sambanova})", "funcion": lambda cont, conf: llamar_api_sambanova(cont, conf, modelo_sambanova)},
            {"nombre": f"OpenRouter ({modelo_openrouter})", "funcion": lambda cont, conf: llamar_api_openrouter(cont, conf, modelo_openrouter)},
            {"nombre": f"Cohere ({modelo_cohere})", "funcion": lambda cont, conf: llamar_api_cohere(cont, conf, modelo_cohere)},
            {"nombre": f"Hugging Face ({modelo_hf})", "funcion": lambda cont, conf: llamar_api_huggingface(cont, conf, modelo_hf)}
        ]
    
    for api in apis_a_probar:
        print(f"[Coordinador: Intentando procesar con {api['nombre']}...]")
        try:
            respuesta = api["funcion"](contenido_a_enviar, config_herramientas)
            print(f"[Coordinador: ¡Éxito con {api['nombre']}!]")
            
            # FILTRO ANTI-ALUCINACIONES DE ERRORES EN INGLÉS
            if "user safety: safe" in respuesta.text.lower():
                return RespuestaFalsa("Lo siento, mi red neuronal de respaldo bloqueó la respuesta por un falso positivo de seguridad. Intenta preguntarme de otra forma.")
                
            return respuesta
        except Exception as e:
            print(f"[Coordinador: Fallo en {api['nombre']} - {str(e)}]")
            
    return RespuestaFalsa("Lo siento, todas mis conexiones a los diferentes cerebros han fallado en este momento.")