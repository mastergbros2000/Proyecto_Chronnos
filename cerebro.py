import os
import time
import datetime
import threading
import json
import base64
import io
import re
from pathlib import Path
from dotenv import load_dotenv
from google import genai
from google.genai import types
from PIL import Image

from openai import OpenAI
import cohere
from huggingface_hub import InferenceClient

# Fase 3: Control de sistema y navegador
from control_sistema import abrir_aplicacion, escribir_texto, presionar_tecla, cerrar_ventana
from navegador_web import (
    buscar_y_reproducir_youtube, 
    buscar_mercadolibre, 
    navegar_a_url, 
    hacer_clic_web, 
    escribir_y_buscar_web
)
# Fase 3: Archivos y Agenda/Clima integrados
from gestor_archivos import (
    buscar_archivo_en_disco,
    explorar_carpeta,
    explorar_archivo_comprimido,
    leer_archivo_local,
    crear_o_modificar_archivo,
    comparar_archivos_locales
)
from agenda_y_tiempo import (
    obtener_fecha_y_hora_actual,
    consultar_clima,
    establecer_temporizador,
    agendar_evento,
    consultar_agenda
)
from vision import capturar_imagen, cargar_imagen_segura

load_dotenv() 

CLOUDFLARE_ACCOUNT_ID = os.getenv("CLOUDFLARE_ACCOUNT_ID")
CLOUDFLARE_API_KEY = os.getenv("CLOUDFLARE_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
COHERE_API_KEY = os.getenv("COHERE_API_KEY")
HUGGINGFACE_API_KEY = os.getenv("HUGGINGFACE_API_KEY")
GITHUB_MODELS_API_KEY = os.getenv("GITHUB_MODELS_API_KEY")
SAMBANOVA_API_KEY = os.getenv("SAMBANOVA_API_KEY")

TIMEOUT_RED = 8.0

client_cloudflare = OpenAI(api_key=CLOUDFLARE_API_KEY, base_url=f"https://api.cloudflare.com/client/v4/accounts/{CLOUDFLARE_ACCOUNT_ID}/ai/v1", timeout=TIMEOUT_RED) if CLOUDFLARE_API_KEY and CLOUDFLARE_ACCOUNT_ID else None
client_gemini = genai.Client(api_key=GOOGLE_API_KEY) if GOOGLE_API_KEY else None
client_openrouter = OpenAI(api_key=OPENROUTER_API_KEY, base_url="https://openrouter.ai/api/v1", timeout=TIMEOUT_RED) if OPENROUTER_API_KEY else None
client_cohere = cohere.ClientV2(COHERE_API_KEY, timeout=TIMEOUT_RED) if COHERE_API_KEY else None
client_hf = InferenceClient(api_key=HUGGINGFACE_API_KEY, timeout=TIMEOUT_RED) if HUGGINGFACE_API_KEY else None
client_github = OpenAI(api_key=GITHUB_MODELS_API_KEY, base_url="https://models.inference.ai.azure.com", timeout=TIMEOUT_RED) if GITHUB_MODELS_API_KEY else None
client_sambanova = OpenAI(api_key=SAMBANOVA_API_KEY, base_url="https://api.sambanova.ai/v1", timeout=TIMEOUT_RED) if SAMBANOVA_API_KEY else None

penalizaciones_api = {}
TIEMPO_CASTIGO = 25 

PROMPT_SISTEMA_BASE = (
    "Eres Chronnos, un agente de IA autónomo para Windows capaz de controlar aplicaciones locales, "
    "navegar por la web, inspeccionar y analizar todo tipo de archivos del disco (documentos, tablas Excel, "
    "presentaciones PowerPoint, comprimidos .zip/.7z, imágenes, multimedia), gestionar la agenda y consultar el clima.\n"
    "REGLAS:\n"
    "1. Usa las herramientas especializadas cuando la tarea lo amerite.\n"
    "2. Responde en español de forma directa, concisa y profesional.\n"
)
historial_conversacion = []

class RespuestaFalsa:
    def __init__(self, mensaje):
        self.text = mensaje
        self.function_calls = None

def _convertir_herramientas_a_json():
    """Registra todas las herramientas de la Fase 3 en formato compatible con OpenAI."""
    return [
        {"type": "function", "function": {"name": "abrir_aplicacion", "description": "Abre programas locales de Windows (Bloc de notas, Calculadora, Paint, Terminal).", "parameters": {"type": "object", "properties": {"aplicacion": {"type": "string"}}, "required": ["aplicacion"]}}},
        {"type": "function", "function": {"name": "escribir_texto", "description": "Escribe texto en la aplicacion activa.", "parameters": {"type": "object", "properties": {"texto": {"type": "string"}}, "required": ["texto"]}}},
        {"type": "function", "function": {"name": "presionar_tecla", "description": "Presiona una tecla especial.", "parameters": {"type": "object", "properties": {"tecla": {"type": "string"}}, "required": ["tecla"]}}},
        {"type": "function", "function": {"name": "cerrar_ventana", "description": "Cierra la aplicacion activa.", "parameters": {"type": "object", "properties": {}}}},
        {"type": "function", "function": {"name": "buscar_y_reproducir_youtube", "description": "Busca y reproduce videos en YouTube.", "parameters": {"type": "object", "properties": {"busqueda": {"type": "string"}}, "required": ["busqueda"]}}},
        {"type": "function", "function": {"name": "buscar_mercadolibre", "description": "Busca un producto en Mercado Libre.", "parameters": {"type": "object", "properties": {"producto": {"type": "string"}}, "required": ["producto"]}}},
        {"type": "function", "function": {"name": "navegar_a_url", "description": "Abre y navega a un sitio web en el navegador.", "parameters": {"type": "object", "properties": {"url": {"type": "string"}}, "required": ["url"]}}},
        {"type": "function", "function": {"name": "hacer_clic_web", "description": "Hace clic en un enlace o boton web.", "parameters": {"type": "object", "properties": {"elemento": {"type": "string"}}, "required": ["elemento"]}}},
        {"type": "function", "function": {"name": "escribir_y_buscar_web", "description": "Escribe en la pagina web activa y presiona Enter.", "parameters": {"type": "object", "properties": {"texto": {"type": "string"}}, "required": ["texto"]}}},
        {"type": "function", "function": {"name": "buscar_archivo_en_disco", "description": "Busca archivos o carpetas en el disco.", "parameters": {"type": "object", "properties": {"nombre_o_patron": {"type": "string"}, "ruta_inicio": {"type": "string"}}, "required": ["nombre_o_patron"]}}},
        {"type": "function", "function": {"name": "explorar_carpeta", "description": "Lista archivos y carpetas dentro de un directorio.", "parameters": {"type": "object", "properties": {"ruta": {"type": "string"}}, "required": ["ruta"]}}},
        {"type": "function", "function": {"name": "explorar_archivo_comprimido", "description": "Explora e inspecciona el árbol de contenidos de un archivo comprimido .zip o .7z.", "parameters": {"type": "object", "properties": {"ruta": {"type": "string"}}, "required": ["ruta"]}}},
        {"type": "function", "function": {"name": "leer_archivo_local", "description": "Lee y analiza el contenido de archivos locales (texto, código, PDF, Word, Excel .xlsx, PowerPoint .pptx, comprimidos .zip/.7z, imágenes o multimedia).", "parameters": {"type": "object", "properties": {"ruta": {"type": "string"}}, "required": ["ruta"]}}},
        {"type": "function", "function": {"name": "crear_o_modificar_archivo", "description": "Crea o anexa contenido a un archivo.", "parameters": {"type": "object", "properties": {"ruta": {"type": "string"}, "contenido": {"type": "string"}, "modo": {"type": "string"}}, "required": ["ruta", "contenido"]}}},
        {"type": "function", "function": {"name": "comparar_archivos_locales", "description": "Compara el contenido de dos archivos.", "parameters": {"type": "object", "properties": {"ruta1": {"type": "string"}, "ruta2": {"type": "string"}}, "required": ["ruta1", "ruta2"]}}},
        {"type": "function", "function": {"name": "obtener_fecha_y_hora_actual", "description": "Obtiene la fecha y hora exacta actual.", "parameters": {"type": "object", "properties": {}}}},
        {"type": "function", "function": {"name": "consultar_clima", "description": "Consulta el clima actual o pronóstico.", "parameters": {"type": "object", "properties": {"dias_adelante": {"type": "integer"}}, "required": []}}},
        {"type": "function", "function": {"name": "establecer_temporizador", "description": "Establece un temporizador con alarma de voz.", "parameters": {"type": "object", "properties": {"minutos": {"type": "number"}, "motivo": {"type": "string"}}, "required": ["minutos"]}}},
        {"type": "function", "function": {"name": "agendar_evento", "description": "Agenda una cita o recordatorio.", "parameters": {"type": "object", "properties": {"titulo": {"type": "string"}, "fecha": {"type": "string"}, "hora": {"type": "string"}}, "required": ["titulo", "fecha", "hora"]}}},
        {"type": "function", "function": {"name": "consultar_agenda", "description": "Consulta compromisos en la agenda.", "parameters": {"type": "object", "properties": {"fecha_busqueda": {"type": "string"}}, "required": []}}}
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
                    
        if not self.function_calls and ("<function=" in self.text or "<parameter=" in self.text):
            match_url = re.search(r'https?://[^\s<"]+', self.text)
            if match_url:
                url_encontrada = match_url.group(0)
                self.function_calls.append(LectorFunctionCall("navegar_a_url", {"url": url_encontrada}))
                self.text = ""
            else:
                self.text = re.sub(r'<[^>]+>', '', self.text).strip()

        if not self.function_calls:
            self.function_calls = None

def _armar_mensajes_openai(texto_prompt):
    """Genera una ventana de contexto limpia sin duplicaciones."""
    mensajes = [{"role": "system", "content": PROMPT_SISTEMA_BASE}]
    for h in historial_conversacion[-6:]:
        mensajes.append(h)
    mensajes.append({"role": "user", "content": str(texto_prompt)})
    return mensajes

def llamar_api_gemini(contenido_a_enviar, config_herramientas, modelo):
    if not client_gemini: raise Exception("API Key de Gemini no configurada")
    return client_gemini.models.generate_content(model=modelo, contents=contenido_a_enviar, config=config_herramientas)

def llamar_api_sambanova(contenido_a_enviar, config_herramientas, modelo):
    if not client_sambanova: raise Exception("API Key de SambaNova no configurada")
    texto_prompt = contenido_a_enviar[0] if isinstance(contenido_a_enviar, list) else contenido_a_enviar
    herramientas_json = _convertir_herramientas_a_json() if config_herramientas else None
    mensajes = _armar_mensajes_openai(texto_prompt)
    kwargs = {"model": modelo, "messages": mensajes, "stream": False}
    if herramientas_json:
        kwargs["tools"] = herramientas_json
        kwargs["tool_choice"] = "auto"
    respuesta = client_sambanova.chat.completions.create(**kwargs)
    return AdaptadorRespuestaOpenAI(respuesta.choices[0].message)

def llamar_api_openrouter(contenido_a_enviar, config_herramientas, modelo):
    if not client_openrouter: raise Exception("API Key de OpenRouter no configurada")
    texto_prompt = contenido_a_enviar[0] if isinstance(contenido_a_enviar, list) else contenido_a_enviar
    herramientas_json = _convertir_herramientas_a_json() if config_herramientas else None
    mensajes = _armar_mensajes_openai(texto_prompt)
    kwargs = {"model": modelo, "messages": mensajes, "stream": False}
    if herramientas_json:
        kwargs["tools"] = herramientas_json
        kwargs["tool_choice"] = "auto"
    respuesta = client_openrouter.chat.completions.create(**kwargs)
    return AdaptadorRespuestaOpenAI(respuesta.choices[0].message)

def llamar_api_cloudflare(contenido_a_enviar, config_herramientas, modelo):
    if not client_cloudflare: raise Exception("API Key de Cloudflare no configurada")
    texto_prompt = contenido_a_enviar[0] if isinstance(contenido_a_enviar, list) else contenido_a_enviar
    mensajes = _armar_mensajes_openai(texto_prompt)
    respuesta = client_cloudflare.chat.completions.create(model=modelo, messages=mensajes, stream=False)
    return AdaptadorRespuestaOpenAI(respuesta.choices[0].message)

def llamar_api_github(contenido_a_enviar, config_herramientas, modelo):
    if not client_github: raise Exception("API Key de GitHub Models no configurada")
    texto_prompt = contenido_a_enviar[0] if isinstance(contenido_a_enviar, list) else contenido_a_enviar
    herramientas_json = _convertir_herramientas_a_json() if config_herramientas else None
    
    if isinstance(contenido_a_enviar, list) and len(contenido_a_enviar) > 1:
        texto = contenido_a_enviar[0]
        imagen = contenido_a_enviar[1]
        buffered = io.BytesIO()
        imagen.save(buffered, format="JPEG")
        img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
        mensajes = [{"role": "system", "content": PROMPT_SISTEMA_BASE}, {"role": "user", "content": [{"type": "text", "text": texto}, {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_str}"}}]}]
    else:
        mensajes = _armar_mensajes_openai(texto_prompt)
    
    respuesta = client_github.chat.completions.create(model=modelo, messages=mensajes, tools=herramientas_json, tool_choice="auto" if herramientas_json else None, stream=False)
    return AdaptadorRespuestaOpenAI(respuesta.choices[0].message)

def llamar_api_cohere(contenido_a_enviar, config_herramientas, modelo):
    if not client_cohere: raise Exception("API Key de Cohere no configurada")
    texto_prompt = contenido_a_enviar[0] if isinstance(contenido_a_enviar, list) else contenido_a_enviar
    mensajes = [{"role": "system", "content": PROMPT_SISTEMA_BASE}, {"role": "user", "content": str(texto_prompt)}]
    respuesta = client_cohere.chat(model=modelo, messages=mensajes)
    class AdaptadorRespuestaCohere:
        def __init__(self, texto):
            self.text = texto
            self.function_calls = None
    return AdaptadorRespuestaCohere(respuesta.message.content[0].text)

def llamar_api_huggingface(contenido_a_enviar, config_herramientas, modelo):
    if not client_hf: raise Exception("API Key de Hugging Face no configurada")
    texto_prompt = contenido_a_enviar[0] if isinstance(contenido_a_enviar, list) else contenido_a_enviar
    mensajes = [{"role": "system", "content": PROMPT_SISTEMA_BASE}, {"role": "user", "content": str(texto_prompt)}]
    respuesta = client_hf.chat_completion(model=modelo, messages=mensajes, max_tokens=600)
    class AdaptadorRespuestaHF:
        def __init__(self, texto):
            self.text = texto
            self.function_calls = None
    return AdaptadorRespuestaHF(respuesta.choices[0].message.content)

def analizar_complejidad(texto_prompt):
    palabras_clave_complejas = ["analiza", "profundidad", "informe", "código", "programa", "resume", "compara", "explica", "describe la imagen"]
    texto_min = str(texto_prompt).lower()
    return "COMPLEJO" if any(p in texto_min for p in palabras_clave_complejas) else "RAPIDO"

def procesar_respuesta(comando):
    global historial_conversacion
    comando_limpio = comando.lower()
    
    # 1. Comprobación de si el comando cita directamente un archivo de imagen en el disco
    imagen_directa = None
    coincidencia_img = re.search(r'([a-zA-Z]:[\\/][^:*?"<>|\r\n]+\.(?:png|jpg|jpeg|bmp|webp)|[\w\-.]+\.(?:png|jpg|jpeg|bmp|webp))', comando, re.IGNORECASE)
    if coincidencia_img:
        posible_ruta = coincidencia_img.group(1).strip()
        if os.path.exists(posible_ruta) and os.path.isfile(posible_ruta):
            imagen_directa = cargar_imagen_segura(posible_ruta)
            
    palabras_vision = ["mira", "observa", "qué es esto", "que es esto", "qué tengo en la mano", "ves esto", "analiza esta imagen", "cámara", "camara", "foto", "fotografía"]
    requiere_vision = imagen_directa is not None or any(palabra in comando_limpio for palabra in palabras_vision)
    
    contenido_a_enviar = [comando]
    
    if imagen_directa:
        contenido_a_enviar = [comando, imagen_directa]
    elif requiere_vision:
        ruta_camara = capturar_imagen()
        if ruta_camara and os.path.exists(ruta_camara):
            img_cam = cargar_imagen_segura(ruta_camara)
            if img_cam:
                contenido_a_enviar = [comando, img_cam]
            
    if requiere_vision and len(contenido_a_enviar) > 1:
        configuracion_herramientas = None
    else:
        configuracion_herramientas = types.GenerateContentConfig(
            tools=[
                abrir_aplicacion, escribir_texto, presionar_tecla, cerrar_ventana,
                buscar_y_reproducir_youtube, buscar_mercadolibre,
                navegar_a_url, hacer_clic_web, escribir_y_buscar_web,
                buscar_archivo_en_disco, explorar_carpeta, explorar_archivo_comprimido,
                leer_archivo_local, crear_o_modificar_archivo, comparar_archivos_locales,
                obtener_fecha_y_hora_actual, consultar_clima, establecer_temporizador,
                agendar_evento, consultar_agenda
            ]
        )
        
    respuesta = generar_con_respaldo(contenido_a_enviar, configuracion_herramientas)
    
    if getattr(respuesta, 'function_calls', None):
        resultados_multiples = []
        imagen_extraida_de_archivo = None
        
        for function_call in respuesta.function_calls:
            resultado_accion = ""
            args = function_call.args if isinstance(function_call.args, dict) else {}
            fn = function_call.name
            
            if fn == "abrir_aplicacion": resultado_accion = abrir_aplicacion(args.get("aplicacion", ""))
            elif fn == "escribir_texto": resultado_accion = escribir_texto(args.get("texto", ""))
            elif fn == "presionar_tecla": resultado_accion = presionar_tecla(args.get("tecla", ""))
            elif fn == "cerrar_ventana": resultado_accion = cerrar_ventana()
            elif fn == "buscar_y_reproducir_youtube": resultado_accion = buscar_y_reproducir_youtube(args.get("busqueda", ""))
            elif fn == "buscar_mercadolibre": resultado_accion = buscar_mercadolibre(args.get("producto", ""))
            elif fn == "navegar_a_url": resultado_accion = navegar_a_url(args.get("url", ""))
            elif fn == "hacer_clic_web": resultado_accion = hacer_clic_web(args.get("elemento", ""))
            elif fn == "escribir_y_buscar_web": resultado_accion = escribir_y_buscar_web(args.get("texto", ""))
            elif fn == "buscar_archivo_en_disco": resultado_accion = buscar_archivo_en_disco(args.get("nombre_o_patron", ""), args.get("ruta_inicio"))
            elif fn == "explorar_carpeta": resultado_accion = explorar_carpeta(args.get("ruta", ""))
            elif fn == "explorar_archivo_comprimido": resultado_accion = explorar_archivo_comprimido(args.get("ruta", ""))
            elif fn == "leer_archivo_local":
                resultado_accion = leer_archivo_local(args.get("ruta", ""))
                # Si la lectura corresponde a una imagen local, se activa el pipeline multimodal
                if "[IMAGEN_LOCAL:" in resultado_accion:
                    match_img = re.search(r'\[IMAGEN_LOCAL:(.+?)\]', resultado_accion)
                    if match_img:
                        ruta_extraida = match_img.group(1).strip()
                        imagen_extraida_de_archivo = cargar_imagen_segura(ruta_extraida)
            elif fn == "crear_o_modificar_archivo": resultado_accion = crear_o_modificar_archivo(args.get("ruta", ""), args.get("contenido", ""), args.get("modo", "sobreescribir"))
            elif fn == "comparar_archivos_locales": resultado_accion = comparar_archivos_locales(args.get("ruta1", ""), args.get("ruta2", ""))
            elif fn == "obtener_fecha_y_hora_actual": resultado_accion = obtener_fecha_y_hora_actual()
            elif fn == "consultar_clima": resultado_accion = consultar_clima(args.get("dias_adelante", 0))
            elif fn == "establecer_temporizador": resultado_accion = establecer_temporizador(args.get("minutos", 1), args.get("motivo", "Temporizador"))
            elif fn == "agendar_evento": resultado_accion = agendar_evento(args.get("titulo", ""), args.get("fecha", "hoy"), args.get("hora", ""))
            elif fn == "consultar_agenda": resultado_accion = consultar_agenda(args.get("fecha_busqueda", "hoy"))
            resultados_multiples.append(resultado_accion)
            
        resumen_total = " ".join(resultados_multiples)
        
        # Si se detectó una imagen física en el disco, se delega su interpretación a los modelos visuales
        if imagen_extraida_de_archivo:
            prompt_confirmacion = (
                f"Instrucción del usuario: {comando}\n"
                f"[Resultado de inspección de archivo: {resumen_total}]\n"
                "Describe con claridad y detalle lo que observas en la imagen adjunta, indicando elementos visuales, textos o contexto principal."
            )
            contenido_confirmacion = [prompt_confirmacion, imagen_extraida_de_archivo]
        else:
            prompt_confirmacion = f"Instrucción del usuario: {comando}\n[Resultado de la acción: {resumen_total}]\nConfirma brevemente al usuario la acción realizada."
            contenido_confirmacion = [prompt_confirmacion]
            
        respuesta_final = generar_con_respaldo(contenido_confirmacion, None)
        texto_respuesta = getattr(respuesta_final, 'text', '') or resumen_total
        
        historial_conversacion.append({"role": "user", "content": comando})
        historial_conversacion.append({"role": "assistant", "content": texto_respuesta})
        return texto_respuesta
                
    texto_final = getattr(respuesta, 'text', '') or "No pude procesar la respuesta."
    if "user safety: safe" in texto_final.lower():
        texto_final = "La respuesta fue filtrada por las políticas de seguridad del modelo."
        
    historial_conversacion.append({"role": "user", "content": comando})
    historial_conversacion.append({"role": "assistant", "content": texto_final})
    return texto_final

def generar_con_respaldo(contenido_a_enviar, config_herramientas):
    global penalizaciones_api
    texto_prompt = contenido_a_enviar[0] if isinstance(contenido_a_enviar, list) else contenido_a_enviar
    nivel_complejidad = analizar_complejidad(texto_prompt)
    print(f"\n[Cerebro Coordinador: Nivel de complejidad evaluado -> {nivel_complejidad}]")
    
    modelo_gemini = "gemini-3.6-flash"
    modelo_sambanova = "Meta-Llama-3.3-70B-Instruct"
    modelo_github = "gpt-4o" if nivel_complejidad == "COMPLEJO" else "gpt-4o-mini"
    modelo_openrouter = "openrouter/free"
    modelo_cloudflare = "@cf/meta/llama-3.1-8b-instruct-fp8"
    modelo_cohere = "command-r-plus-08-2024" if nivel_complejidad == "COMPLEJO" else "command-r-08-2024"
    modelo_hf = "meta-llama/Llama-3.2-3B-Instruct"

    # Enrutamiento dinámico: prioriza Gemini / Cloudflare para tareas rápidas y directas
    if nivel_complejidad == "RAPIDO":
        apis_a_probar = [
            {"nombre": f"Gemini ({modelo_gemini})", "funcion": lambda cont, conf: llamar_api_gemini(cont, conf, modelo_gemini)},
            {"nombre": f"Cloudflare ({modelo_cloudflare})", "funcion": lambda cont, conf: llamar_api_cloudflare(cont, conf, modelo_cloudflare)},
            {"nombre": f"OpenRouter ({modelo_openrouter})", "funcion": lambda cont, conf: llamar_api_openrouter(cont, conf, modelo_openrouter)},
            {"nombre": f"SambaNova ({modelo_sambanova})", "funcion": lambda cont, conf: llamar_api_sambanova(cont, conf, modelo_sambanova)},
            {"nombre": f"GitHub Models ({modelo_github})", "funcion": lambda cont, conf: llamar_api_github(cont, conf, modelo_github)},
            {"nombre": f"Cohere ({modelo_cohere})", "funcion": lambda cont, conf: llamar_api_cohere(cont, conf, modelo_cohere)},
            {"nombre": f"Hugging Face ({modelo_hf})", "funcion": lambda cont, conf: llamar_api_huggingface(cont, conf, modelo_hf)}
        ]
    else:
        apis_a_probar = [
            {"nombre": f"Gemini ({modelo_gemini})", "funcion": lambda cont, conf: llamar_api_gemini(cont, conf, modelo_gemini)},
            {"nombre": f"GitHub Models ({modelo_github})", "funcion": lambda cont, conf: llamar_api_github(cont, conf, modelo_github)},
            {"nombre": f"SambaNova ({modelo_sambanova})", "funcion": lambda cont, conf: llamar_api_sambanova(cont, conf, modelo_sambanova)},
            {"nombre": f"Cohere ({modelo_cohere})", "funcion": lambda cont, conf: llamar_api_cohere(cont, conf, modelo_cohere)},
            {"nombre": f"OpenRouter ({modelo_openrouter})", "funcion": lambda cont, conf: llamar_api_openrouter(cont, conf, modelo_openrouter)},
            {"nombre": f"Cloudflare ({modelo_cloudflare})", "funcion": lambda cont, conf: llamar_api_cloudflare(cont, conf, modelo_cloudflare)},
            {"nombre": f"Hugging Face ({modelo_hf})", "funcion": lambda cont, conf: llamar_api_huggingface(cont, conf, modelo_hf)}
        ]
    
    # Excluye modelos que no soportan llamadas a funciones JSON
    if config_herramientas:
        apis_a_probar = [api for api in apis_a_probar if "Cloudflare" not in api['nombre'] and "Cohere" not in api['nombre'] and "Hugging Face" not in api['nombre']]
    
    # Visión multimodality: solo Gemini y GitHub soportan imágenes en este pipeline
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
