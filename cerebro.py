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

# Módulos locales de herramientas
from control_sistema import abrir_aplicacion, escribir_texto, presionar_tecla, cerrar_ventana
from navegador_web import buscar_y_reproducir_youtube, buscar_mercadolibre
from gestor_archivos import (
    buscar_archivo_en_disco,
    explorar_carpeta,
    leer_archivo_local,
    crear_o_modificar_archivo,
    comparar_archivos_locales
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

# System prompt reforzado contra alucinaciones de archivos
memoria_conversacion = (
    "Eres Chronnos, un agente de IA que controla aplicaciones y explora el sistema de archivos local. "
    "Responde siempre en español de forma natural, directa y concisa.\n"
    "REGLA ESTRICTA DE ARCHIVOS: JAMÁS inventes ni alucines el contenido de una carpeta o archivo. "
    "Menciona ÚNICAMENTE los elementos que figuren explícitamente en las respuestas del sistema. "
    "Si encuentras la ruta de una carpeta y el usuario quiere saber qué contiene, DEBES llamar a 'explorar_carpeta' antes de responder.\n\n"
)

class RespuestaFalsa:
    def __init__(self, mensaje):
        self.text = mensaje
        self.function_calls = None

def _convertir_herramientas_a_json():
    return [
        {"type": "function", "function": {"name": "abrir_aplicacion", "description": "Abre una aplicacion basica en Windows.", "parameters": {"type": "object", "properties": {"aplicacion": {"type": "string"}}, "required": ["aplicacion"]}}},
        {"type": "function", "function": {"name": "escribir_texto", "description": "Escribe texto o numeros en la aplicacion activa.", "parameters": {"type": "object", "properties": {"texto": {"type": "string"}}, "required": ["texto"]}}},
        {"type": "function", "function": {"name": "presionar_tecla", "description": "Presiona una tecla especial.", "parameters": {"type": "object", "properties": {"tecla": {"type": "string"}}, "required": ["tecla"]}}},
        {"type": "function", "function": {"name": "cerrar_ventana", "description": "Cierra la aplicacion activa simulando Alt+F4.", "parameters": {"type": "object", "properties": {}}}},
        {"type": "function", "function": {"name": "buscar_y_reproducir_youtube", "description": "Abre YouTube y busca/reproduce un video.", "parameters": {"type": "object", "properties": {"busqueda": {"type": "string"}}, "required": ["busqueda"]}}},
        {"type": "function", "function": {"name": "buscar_mercadolibre", "description": "Busca un producto en Mercado Libre.", "parameters": {"type": "object", "properties": {"producto": {"type": "string"}}, "required": ["producto"]}}},
        {"type": "function", "function": {"name": "buscar_archivo_en_disco", "description": "Busca la ruta de archivos o carpetas en el disco.", "parameters": {"type": "object", "properties": {"nombre_o_patron": {"type": "string"}, "ruta_inicio": {"type": "string"}}, "required": ["nombre_o_patron"]}}},
        {"type": "function", "function": {"name": "explorar_carpeta", "description": "Muestra el contenido real de una carpeta dada su ruta.", "parameters": {"type": "object", "properties": {"ruta": {"type": "string"}}, "required": ["ruta"]}}},
        {"type": "function", "function": {"name": "leer_archivo_local", "description": "Lee el contenido de un archivo.", "parameters": {"type": "object", "properties": {"ruta": {"type": "string"}}, "required": ["ruta"]}}},
        {"type": "function", "function": {"name": "crear_o_modificar_archivo", "description": "Crea o modifica un archivo.", "parameters": {"type": "object", "properties": {"ruta": {"type": "string"}, "contenido": {"type": "string"}, "modo": {"type": "string"}}, "required": ["ruta", "contenido"]}}},
        {"type": "function", "function": {"name": "comparar_archivos_locales", "description": "Compara dos archivos locales.", "parameters": {"type": "object", "properties": {"ruta1": {"type": "string"}, "ruta2": {"type": "string"}}, "required": ["ruta1", "ruta2"]}}}
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
    
    kwargs = {
        "model": modelo,
        "messages": [{"role": "system", "content": memoria_conversacion}, {"role": "user", "content": texto_prompt}],
        "stream": False
    }
    if herramientas_json:
        kwargs["tools"] = herramientas_json
        kwargs["tool_choice"] = "auto"
        
    respuesta = client_sambanova.chat.completions.create(**kwargs)
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
            
    configuracion_herramientas = None if requiere_vision else types.GenerateContentConfig(
        tools=[
            abrir_aplicacion, escribir_texto, presionar_tecla, cerrar_ventana,
            buscar_y_reproducir_youtube, buscar_mercadolibre,
            buscar_archivo_en_disco, explorar_carpeta, leer_archivo_local,
            crear_o_modificar_archivo, comparar_archivos_locales
        ]
    )

    # Bucle encadenado de hasta 3 ejecuciones automáticas de herramientas
    for _ in range(3):
        respuesta = generar_con_respaldo(contenido_a_enviar, configuracion_herramientas)
        
        if not getattr(respuesta, 'function_calls', None):
            break
            
        resultados_multiples = [] 
        for function_call in respuesta.function_calls:
            resultado_accion = ""
            fn_name = function_call.name
            args = function_call.args
            
            if fn_name == "abrir_aplicacion": resultado_accion = abrir_aplicacion(args.get("aplicacion", ""))
            elif fn_name == "escribir_texto": resultado_accion = escribir_texto(args.get("texto", ""))
            elif fn_name == "presionar_tecla": resultado_accion = presionar_tecla(args.get("tecla", ""))
            elif fn_name == "cerrar_ventana": resultado_accion = cerrar_ventana()
            elif fn_name == "buscar_y_reproducir_youtube": resultado_accion = buscar_y_reproducir_youtube(args.get("busqueda", ""))
            elif fn_name == "buscar_mercadolibre": resultado_accion = buscar_mercadolibre(args.get("producto", ""))
            elif fn_name == "buscar_archivo_en_disco": resultado_accion = buscar_archivo_en_disco(**args)
            elif fn_name == "explorar_carpeta": resultado_accion = explorar_carpeta(**args)
            elif fn_name == "leer_archivo_local": resultado_accion = leer_archivo_local(**args)
            elif fn_name == "crear_o_modificar_archivo": resultado_accion = crear_o_modificar_archivo(**args)
            elif fn_name == "comparar_archivos_locales": resultado_accion = comparar_archivos_locales(**args)
            
            resultados_multiples.append(resultado_accion)
            
        resumen_total = " ".join(resultados_multiples)
        contenido_a_enviar = [f"{memoria_conversacion}\n[Sistema: {resumen_total}]\nInstrucción: Si el resultado anterior devolvió la ruta de una carpeta que el usuario quiere revisar, ejecuta la herramienta 'explorar_carpeta'. De lo contrario, resume brevemente lo que encontraste en español sin inventar datos."]

    texto_final = respuesta.text if hasattr(respuesta, 'text') else ""
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

    apis_a_probar = [
        {"nombre": f"SambaNova ({modelo_sambanova})", "funcion": lambda cont, conf: llamar_api_sambanova(cont, conf, modelo_sambanova)},
        {"nombre": f"GitHub Models ({modelo_github})", "funcion": lambda cont, conf: llamar_api_github(cont, conf, modelo_github)},
        {"nombre": f"OpenRouter ({modelo_openrouter})", "funcion": lambda cont, conf: llamar_api_openrouter(cont, conf, modelo_openrouter)},
        {"nombre": f"Gemini ({modelo_gemini})", "funcion": lambda cont, conf: llamar_api_gemini(cont, conf, modelo_gemini)}
    ]
    
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