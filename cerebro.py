import os
import time
import datetime
import threading
import json
import base64
import io
from dotenv import load_dotenv
from google import genai
from google.genai import types
from PIL import Image

from openai import OpenAI
import cohere
from huggingface_hub import InferenceClient

from control_sistema import abrir_aplicacion, escribir_texto, presionar_tecla, cerrar_ventana
from navegador_web import (
    buscar_y_reproducir_youtube, 
    buscar_mercadolibre, 
    navegar_a_url, 
    hacer_clic_web, 
    escribir_y_buscar_web
)

load_dotenv() 

CLOUDFLARE_ACCOUNT_ID = os.getenv("CLOUDFLARE_ACCOUNT_ID")
CLOUDFLARE_API_KEY = os.getenv("CLOUDFLARE_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
COHERE_API_KEY = os.getenv("COHERE_API_KEY")
HUGGINGFACE_API_KEY = os.getenv("HUGGINGFACE_API_KEY")
GITHUB_MODELS_API_KEY = os.getenv("GITHUB_MODELS_API_KEY")
SAMBANOVA_API_KEY = os.getenv("SAMBANOVA_API_KEY")

client_cloudflare = OpenAI(api_key=CLOUDFLARE_API_KEY, base_url=f"https://api.cloudflare.com/client/v4/accounts/{CLOUDFLARE_ACCOUNT_ID}/ai/v1") if CLOUDFLARE_API_KEY and CLOUDFLARE_ACCOUNT_ID else None
client_gemini = genai.Client(api_key=GOOGLE_API_KEY) if GOOGLE_API_KEY else None
client_openrouter = OpenAI(api_key=OPENROUTER_API_KEY, base_url="https://openrouter.ai/api/v1") if OPENROUTER_API_KEY else None
client_cohere = cohere.ClientV2(COHERE_API_KEY) if COHERE_API_KEY else None
client_hf = InferenceClient(api_key=HUGGINGFACE_API_KEY) if HUGGINGFACE_API_KEY else None
client_github = OpenAI(api_key=GITHUB_MODELS_API_KEY, base_url="https://models.inference.ai.azure.com") if GITHUB_MODELS_API_KEY else None
client_sambanova = OpenAI(api_key=SAMBANOVA_API_KEY, base_url="https://api.sambanova.ai/v1") if SAMBANOVA_API_KEY else None

modo_reposo = False
hora_despertar = None
penalizaciones_api = {}
TIEMPO_CASTIGO = 20 

memoria_conversacion = (
    "Eres Chronnos, un agente de Inteligencia Artificial capaz de controlar aplicaciones locales y navegar de forma autónoma e interactiva por cualquier sitio web. "
    "Responde siempre de forma natural, directa y muy humana. "
    "REGLAS PARA NAVEGACIÓN WEB: "
    "1. Si te piden ir a cualquier sitio web o foro (ej: Wikipedia, Reddit, noticias), usa 'navegar_a_url'. "
    "2. Si te piden hacer clic en un enlace o botón visible, usa 'hacer_clic_web'. "
    "3. Si te piden buscar o escribir algo en la página activa, usa 'escribir_y_buscar_web'. "
    "4. Para reproducciones directas en YouTube usa 'buscar_y_reproducir_youtube' y para compras 'buscar_mercadolibre'. "
    "NUNCA simules en texto que usaste una herramienta si no la has ejecutado explícitamente.\n\n"
)

class RespuestaFalsa:
    def __init__(self, mensaje):
        self.text = mensaje
        self.function_calls = None

def _convertir_herramientas_a_json():
    return [
        {"type": "function", "function": {"name": "abrir_aplicacion", "description": "Abre una aplicacion basica en Windows.", "parameters": {"type": "object", "properties": {"aplicacion": {"type": "string"}}, "required": ["aplicacion"]}}},
        {"type": "function", "function": {"name": "escribir_texto", "description": "Escribe texto o numeros en la aplicacion activa de Windows.", "parameters": {"type": "object", "properties": {"texto": {"type": "string"}}, "required": ["texto"]}}},
        {"type": "function", "function": {"name": "presionar_tecla", "description": "Presiona una tecla especial (ej: enter, tab, esc).", "parameters": {"type": "object", "properties": {"tecla": {"type": "string"}}, "required": ["tecla"]}}},
        {"type": "function", "function": {"name": "cerrar_ventana", "description": "Cierra la aplicacion activa simulando Alt+F4.", "parameters": {"type": "object", "properties": {}}}},
        {"type": "function", "function": {"name": "buscar_y_reproducir_youtube", "description": "Abre YouTube, busca un video especifico y lo reproduce.", "parameters": {"type": "object", "properties": {"busqueda": {"type": "string"}}, "required": ["busqueda"]}}},
        {"type": "function", "function": {"name": "buscar_mercadolibre", "description": "Busca un producto especifico en Mercado Libre.", "parameters": {"type": "object", "properties": {"producto": {"type": "string"}}, "required": ["producto"]}}},
        {"type": "function", "function": {"name": "navegar_a_url", "description": "Abre cualquier sitio web o URL en el navegador.", "parameters": {"type": "object", "properties": {"url": {"type": "string"}}, "required": ["url"]}}},
        {"type": "function", "function": {"name": "hacer_clic_web", "description": "Hace clic en un texto, enlace o boton de la pagina web activa.", "parameters": {"type": "object", "properties": {"elemento": {"type": "string"}}, "required": ["elemento"]}}},
        {"type": "function", "function": {"name": "escribir_y_buscar_web", "description": "Escribe texto en la pagina web activa y presiona Enter.", "parameters": {"type": "object", "properties": {"texto": {"type": "string"}}, "required": ["texto"]}}}
    ]

class LectorFunctionCall:
    def __init__(self, nombre, args):
        self.name = nombre
        self.args = args

class AdaptadorRespuestaOpenAI:
    def __init__(self, mensaje_obj):
        self.text = mensaje_obj.content if mensaje_obj.content else ""
        self.function_calls = []
        if hasattr(mensaje_obj, 'tool_calls') and mensaje_obj.tool_calls:
            for tool in mensaje_obj.tool_calls:
                if tool.type == "function":
                    try:
                        args_diccionario = json.loads(tool.function.arguments)
                    except Exception:
                        args_diccionario = {}
                    self.function_calls.append(LectorFunctionCall(tool.function.name, args_diccionario))
        if not self.function_calls:
            self.function_calls = None

def llamar_api_sambanova(contenido_a_enviar, config_herramientas, modelo):
    if not client_sambanova: raise Exception("API Key de SambaNova no configurada")
    texto_prompt = contenido_a_enviar[0] if isinstance(contenido_a_enviar, list) else contenido_a_enviar
    herramientas_json = _convertir_herramientas_a_json() if config_herramientas else None
    respuesta = client_sambanova.chat.completions.create(
        model=modelo,
        messages=[{"role": "system", "content": memoria_conversacion}, {"role": "user", "content": texto_prompt}],
        tools=herramientas_json,
        tool_choice="auto" if herramientas_json else None,
        stream=False
    )
    return AdaptadorRespuestaOpenAI(respuesta.choices[0].message)

def llamar_api_github(contenido_a_enviar, config_herramientas, modelo):
    if not client_github: raise Exception("API Key de GitHub Models no configurada")
    mensajes = [{"role": "system", "content": memoria_conversacion}]
    herramientas_json = _convertir_herramientas_a_json() if config_herramientas else None

    if isinstance(contenido_a_enviar, list) and len(contenido_a_enviar) > 1:
        texto = contenido_a_enviar[0]
        imagen = contenido_a_enviar[1]
        buffered = io.BytesIO()
        imagen.save(buffered, format="JPEG")
        img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
        mensajes.append({"role": "user", "content": [{"type": "text", "text": texto}, {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_str}"}}]})
    else:
        texto_prompt = contenido_a_enviar[0] if isinstance(contenido_a_enviar, list) else contenido_a_enviar
        mensajes.append({"role": "user", "content": texto_prompt})
    
    respuesta = client_github.chat.completions.create(model=modelo, messages=mensajes, tools=herramientas_json, tool_choice="auto" if herramientas_json else None, stream=False)
    return AdaptadorRespuestaOpenAI(respuesta.choices[0].message)

def llamar_api_gemini(contenido_a_enviar, config_herramientas, modelo):
    if not client_gemini: raise Exception("API Key de Gemini no configurada")
    return client_gemini.models.generate_content(model=modelo, contents=contenido_a_enviar, config=config_herramientas)

def llamar_api_openrouter(contenido_a_enviar, config_herramientas, modelo):
    if not client_openrouter: raise Exception("API Key de OpenRouter no configurada")
    texto_prompt = contenido_a_enviar[0] if isinstance(contenido_a_enviar, list) else contenido_a_enviar
    herramientas_json = _convertir_herramientas_a_json() if config_herramientas else None
    respuesta = client_openrouter.chat.completions.create(model=modelo, messages=[{"role": "system", "content": memoria_conversacion}, {"role": "user", "content": texto_prompt}], tools=herramientas_json, tool_choice="auto" if herramientas_json else None, stream=False)
    return AdaptadorRespuestaOpenAI(respuesta.choices[0].message)

def llamar_api_cloudflare(contenido_a_enviar, config_herramientas, modelo):
    if not client_cloudflare: raise Exception("API Key de Cloudflare no configurada")
    mensajes = [{"role": "system", "content": memoria_conversacion}]
    texto_prompt = contenido_a_enviar[0] if isinstance(contenido_a_enviar, list) else contenido_a_enviar
    mensajes.append({"role": "user", "content": texto_prompt})
    respuesta = client_cloudflare.chat.completions.create(model=modelo, messages=mensajes, stream=False)
    return AdaptadorRespuestaOpenAI(respuesta.choices[0].message)

def llamar_api_cohere(contenido_a_enviar, config_herramientas, modelo):
    if not client_cohere: raise Exception("API Key de Cohere no configurada")
    texto_prompt = contenido_a_enviar[0] if isinstance(contenido_a_enviar, list) else contenido_a_enviar
    respuesta = client_cohere.chat(model=modelo, messages=[{"role": "system", "content": memoria_conversacion}, {"role": "user", "content": texto_prompt}])
    class AdaptadorRespuestaCohere:
        def __init__(self, texto):
            self.text = texto
            self.function_calls = None
    return AdaptadorRespuestaCohere(respuesta.message.content[0].text)

def llamar_api_huggingface(contenido_a_enviar, config_herramientas, modelo):
    if not client_hf: raise Exception("API Key de Hugging Face no configurada")
    texto_prompt = contenido_a_enviar[0] if isinstance(contenido_a_enviar, list) else contenido_a_enviar
    respuesta = client_hf.chat_completion(model=modelo, messages=[{"role": "system", "content": memoria_conversacion}, {"role": "user", "content": texto_prompt}], max_tokens=800)
    class AdaptadorRespuestaHF:
        def __init__(self, texto):
            self.text = texto
            self.function_calls = None
    return AdaptadorRespuestaHF(respuesta.choices[0].message.content)

def analizar_complejidad(texto_prompt):
    palabras_clave_complejas = ["analiza", "profundidad", "informe", "código", "programa", "resume", "compara", "explica"]
    texto_min = str(texto_prompt).lower()
    return "COMPLEJO" if any(p in texto_min for p in palabras_clave_complejas) else "RAPIDO"

def procesar_respuesta(comando):
    global memoria_conversacion
    comando_limpio = comando.lower()
    memoria_conversacion += f"Usuario: {comando}\nChronnos: "
    
    palabras_vision = ["mira", "observa", "qué es esto", "qué tengo en la mano", "ves esto", "analiza esta imagen", "cámara", "camara", "foto", "fotografía", "estoy mostrando"]
    requiere_vision = any(palabra in comando_limpio for palabra in palabras_vision)
    
    contenido_a_enviar = [memoria_conversacion]
    
    if requiere_vision:
        from vision import capturar_imagen
        ruta_imagen = capturar_imagen()
        if ruta_imagen:
            imagen = Image.open(ruta_imagen)
            contenido_a_enviar = [memoria_conversacion, imagen]
            
    if requiere_vision:
        configuracion_herramientas = None
    else:
        configuracion_herramientas = types.GenerateContentConfig(
            tools=[
                abrir_aplicacion, escribir_texto, presionar_tecla, cerrar_ventana,
                buscar_y_reproducir_youtube, buscar_mercadolibre,
                navegar_a_url, hacer_clic_web, escribir_y_buscar_web
            ]
        )
        
    respuesta = generar_con_respaldo(contenido_a_enviar, configuracion_herramientas)
    
    if getattr(respuesta, 'function_calls', None):
        resultados_multiples = [] 
        for function_call in respuesta.function_calls:
            resultado_accion = ""
            if function_call.name == "abrir_aplicacion": resultado_accion = abrir_aplicacion(function_call.args["aplicacion"])
            elif function_call.name == "escribir_texto": resultado_accion = escribir_texto(function_call.args["texto"])
            elif function_call.name == "presionar_tecla": resultado_accion = presionar_tecla(function_call.args["tecla"])
            elif function_call.name == "cerrar_ventana": resultado_accion = cerrar_ventana()
            elif function_call.name == "buscar_y_reproducir_youtube": resultado_accion = buscar_y_reproducir_youtube(function_call.args["busqueda"])
            elif function_call.name == "buscar_mercadolibre": resultado_accion = buscar_mercadolibre(function_call.args["producto"])
            elif function_call.name == "navegar_a_url": resultado_accion = navegar_a_url(function_call.args["url"])
            elif function_call.name == "hacer_clic_web": resultado_accion = hacer_clic_web(function_call.args["elemento"])
            elif function_call.name == "escribir_y_buscar_web": resultado_accion = escribir_y_buscar_web(function_call.args["texto"])
            resultados_multiples.append(resultado_accion)
            
        resumen_total = " ".join(resultados_multiples)
        respuesta_final = generar_con_respaldo([f"{memoria_conversacion}\n[Sistema: {resumen_total}]\nResponde confirmando las acciones brevemente."], None)
        texto_respuesta = respuesta_final.text
        memoria_conversacion += f"{texto_respuesta}\n\n"
        return texto_respuesta
                
    texto_final = respuesta.text
    if "user safety: safe" in texto_final.lower():
        texto_final = "Lo siento, mi red neuronal bloqueó la respuesta por seguridad."
    memoria_conversacion += f"{texto_final}\n\n"
    return texto_final

def generar_con_respaldo(contenido_a_enviar, config_herramientas):
    global penalizaciones_api
    texto_prompt = contenido_a_enviar[0] if isinstance(contenido_a_enviar, list) else contenido_a_enviar
    nivel_complejidad = analizar_complejidad(texto_prompt)
    print(f"\n[Cerebro Coordinador: Nivel de complejidad evaluado -> {nivel_complejidad}]")
    
    modelo_sambanova = "Meta-Llama-3.3-70B-Instruct"
    modelo_github = "gpt-4o" if nivel_complejidad == "COMPLEJO" else "gpt-4o-mini"
    modelo_openrouter = "google/gemma-4-31b-it:free" if nivel_complejidad == "COMPLEJO" else "openrouter/free"
    modelo_gemini = "gemini-3.6-flash"
    modelo_cloudflare = "@cf/meta/llama-3.1-8b-instruct-fp8"
    modelo_cohere = "command-r-plus-08-2024" if nivel_complejidad == "COMPLEJO" else "command-r-08-2024"
    modelo_hf = "mistralai/Mixtral-8x7B-Instruct-v0.1" if nivel_complejidad == "COMPLEJO" else "mistralai/Mistral-7B-Instruct-v0.3"

    apis_a_probar = [
        {"nombre": f"SambaNova ({modelo_sambanova})", "funcion": lambda cont, conf: llamar_api_sambanova(cont, conf, modelo_sambanova)},
        {"nombre": f"GitHub Models ({modelo_github})", "funcion": lambda cont, conf: llamar_api_github(cont, conf, modelo_github)},
        {"nombre": f"OpenRouter ({modelo_openrouter})", "funcion": lambda cont, conf: llamar_api_openrouter(cont, conf, modelo_openrouter)},
        {"nombre": f"Gemini ({modelo_gemini})", "funcion": lambda cont, conf: llamar_api_gemini(cont, conf, modelo_gemini)},
        {"nombre": f"Cloudflare ({modelo_cloudflare})", "funcion": lambda cont, conf: llamar_api_cloudflare(cont, conf, modelo_cloudflare)},
        {"nombre": f"Cohere ({modelo_cohere})", "funcion": lambda cont, conf: llamar_api_cohere(cont, conf, modelo_cohere)},
        {"nombre": f"Hugging Face ({modelo_hf})", "funcion": lambda cont, conf: llamar_api_huggingface(cont, conf, modelo_hf)}
    ]
    
    # REGLA CLAVE: Si la orden requiere ejecucion de herramientas, descartamos motores ciegos a herramientas
    if config_herramientas:
        apis_a_probar = [api for api in apis_a_probar if "Cloudflare" not in api['nombre'] and "Cohere" not in api['nombre']]
    
    if isinstance(contenido_a_enviar, list) and len(contenido_a_enviar) > 1:
        apis_a_probar = [api for api in apis_a_probar if "Gemini" in api['nombre'] or "GitHub" in api['nombre']]
    
    for api in apis_a_probar:
        nombre_api = api['nombre']
        if nombre_api in penalizaciones_api:
            tiempo_transcurrido = time.time() - penalizaciones_api[nombre_api]
            if tiempo_transcurrido < TIEMPO_CASTIGO:
                print(f"[Coordinador: Omitiendo {nombre_api} (Penalizada. Restan {int(TIEMPO_CASTIGO - tiempo_transcurrido)}s)]")
                continue
            else:
                del penalizaciones_api[nombre_api] 
        
        print(f"[Coordinador: Intentando procesar con {nombre_api}...]")
        try:
            respuesta = api["funcion"](contenido_a_enviar, config_herramientas)
            print(f"[Coordinador: ¡Éxito con {nombre_api}!]")
            return respuesta
        except Exception as e:
            print(f"[Coordinador: Fallo en {nombre_api} - {e}]")
            penalizaciones_api[nombre_api] = time.time()
            continue
                
    return RespuestaFalsa("Todas las redes neuronales están temporalmente ocupadas. Intenta nuevamente en unos segundos.")