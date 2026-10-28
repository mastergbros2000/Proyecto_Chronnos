import speech_recognition as sr
import pygame
import io
import asyncio
import edge_tts
import re

# Inicializamos el mezclador de Pygame para audio directo en memoria RAM
pygame.mixer.init()

reproduciendo_audio = False
interrupcion_solicitada = False

def restaurar_puntuacion(texto: str) -> str:
    """
    Analiza la transcripción del micrófono e inserta signos de interrogación (¿?) 
    únicamente si la frase es verdaderamente una pregunta.
    """
    if not texto:
        return ""
    
    texto = texto.strip()
    texto_lower = texto.lower()
    
    # Comandos explícitos de acción (NUNCA son preguntas)
    ordenes_imperativas = ("abre", "busca", "pon", "escribe", "haz", "reproduce", "cierra", "ejecuta", "inicia")
    es_orden = texto_lower.startswith(ordenes_imperativas)
    
    # Palabras que inician una pregunta real al comienzo de la frase
    inicio_pregunta = (
        "qué ", "que ", "cómo ", "como ", "cuál ", "cual ", "cuánto ", "cuanto ",
        "dónde ", "donde ", "quién ", "quien ", "por qué ", "porque ", "puedes ",
        "podrías ", "sabes ", "sería ", "es ", "cuánto ", "cuanto "
    )
    
    es_pregunta = not es_orden and (
        texto_lower.startswith(inicio_pregunta) or 
        texto_lower.endswith(("?", "cuánto", "cuanto"))
    )
    
    # Inserción de comas en conectores
    conectores = [r"\bpero\b", r"\bademás\b", r"\bsin embargo\b", r"\bya que\b", r"\bporque\b", r"\baunque\b"]
    for conector in conectores:
        texto = re.sub(rf"(?<!,)\s+({conector.replace(r'\b', '')})", r", \1", texto, flags=re.IGNORECASE)
        
    # Primera letra en mayúscula
    texto = texto[0].upper() + texto[1:]
    
    if es_pregunta and not texto.endswith("?"):
        if not texto.startswith("¿"):
            texto = "¿" + texto
        texto = texto.rstrip(".") + "?"
    elif not es_pregunta and not texto.endswith((".", "?", "!")):
        texto += "."
            
    return texto

async def _generar_bytes_voz(texto: str, voz: str = "es-CL-LorenzoNeural") -> io.BytesIO:
    """Sintetiza la voz mediante Edge-TTS en un buffer de memoria RAM (BytesIO)."""
    texto_limpio = texto.replace("*", "").replace("#", "").replace("`", "")
    communicate = edge_tts.Communicate(texto_limpio, voz)
    
    buffer = io.BytesIO()
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            buffer.write(chunk["data"])
            
    buffer.seek(0)
    return buffer

def hablar(texto: str, voz: str = "es-CL-LorenzoNeural"):
    """
    Sintetiza y reproduce la voz desde la memoria RAM.
    Permite interrupción instantánea si el usuario habla encima.
    """
    global reproduciendo_audio, interrupcion_solicitada
    interrupcion_solicitada = False
    
    if not texto or not texto.strip():
        return

    print(f"Chronnos: {texto}")
    
    try:
        # Generar audio en memoria RAM usando asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        buffer_audio = loop.run_until_complete(_generar_bytes_voz(texto, voz))
        loop.close()
        
        # Cargar en el reproductor de Pygame
        pygame.mixer.music.load(buffer_audio)
        pygame.mixer.music.play()
        reproduciendo_audio = True
        
        # Bucle de monitoreo para corte inmediato por voz
        while pygame.mixer.music.get_busy():
            if interrupcion_solicitada:
                pygame.mixer.music.stop()
                print("\n[Hablar: Reproducción interrumpida por voz del usuario]")
                break
            pygame.time.wait(30)
            
    except Exception as e:
        print(f"[Error de Voz TTS]: {e}")
    finally:
        reproduciendo_audio = False

def detener_habla():
    """Cancela inmediatamente la reproducción de audio actual."""
    global interrupcion_solicitada
    interrupcion_solicitada = True
    pygame.mixer.music.stop()

def escuchar(silencioso=False) -> str | None:
    """
    Escucha el micrófono con optimización de latencia, cancelación de interrupción 
    y formateo de puntuación automático.
    """
    global reproduciendo_audio
    reconocedor = sr.Recognizer()
    
    # Latencia ultra baja
    reconocedor.pause_threshold = 0.7
    reconocedor.non_speaking_duration = 0.4
    
    with sr.Microphone() as fuente:
        # Calibración veloz del ruido ambiente
        reconocedor.adjust_for_ambient_noise(fuente, duration=0.3)
        reconocedor.dynamic_energy_threshold = False
        reconocedor.energy_threshold = 300 
        
        if not silencioso:
            print("\n[Escuchando... Ya puedes hablar]")
        
        try:
            audio = reconocedor.listen(fuente, timeout=5, phrase_time_limit=15)
            
            # Si estabas hablando mientras Chronnos daba su respuesta, la detiene al instante
            if reproduciendo_audio:
                detener_habla()
                
            texto_bruto = reconocedor.recognize_google(audio, language="es-ES")
            
            # Aplicamos la estructuración automática de puntuación
            texto_procesado = restaurar_puntuacion(texto_bruto)
            
            if not silencioso and texto_procesado:
                print(f"Tú: {texto_procesado}")
                
            return texto_procesado
            
        except (sr.WaitTimeoutError, sr.UnknownValueError):
            return None
        except sr.RequestError:
            print("[Error de conexión en el micrófono]")
            return None