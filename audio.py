import os
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "hide"

import speech_recognition as sr
import pygame
import io
import asyncio
import edge_tts
import re
import threading

pygame.mixer.init()

reproduciendo_audio = False
interrupcion_solicitada = False

def restaurar_puntuacion(texto: str) -> str:
    """Restaura puntuación y preguntas preservando límites de palabras."""
    if not texto:
        return ""
    
    texto = texto.strip()
    texto_lower = texto.lower()
    
    ordenes_imperativas = ("abre", "busca", "pon", "escribe", "haz", "reproduce", "cierra", "ejecuta", "inicia")
    es_orden = texto_lower.startswith(ordenes_imperativas)
    
    inicio_pregunta = (
        "qué ", "que ", "cómo ", "como ", "cuál ", "cual ", "cuánto ", "cuanto ",
        "dónde ", "donde ", "quién ", "quien ", "por qué ", "porque ", "puedes ",
        "podrías ", "sabes ", "sería ", "es "
    )
    
    es_pregunta = not es_orden and (
        texto_lower.startswith(inicio_pregunta) or 
        texto_lower.endswith(("?", "cuánto", "cuanto"))
    )
    
    # Inserción segura de comas respetando word boundary \b
    conectores = [r"\bpero\b", r"\bademás\b", r"\bsin embargo\b", r"\bya que\b", r"\bporque\b", r"\baunque\b"]
    for conector in conectores:
        texto = re.sub(rf"(?<!,)\s+({conector})", r", \1", texto, flags=re.IGNORECASE)
        
    texto = texto[0].upper() + texto[1:]
    
    if es_pregunta and not texto.endswith("?"):
        if not texto.startswith("¿"):
            texto = "¿" + texto
        texto = texto.rstrip(".") + "?"
    elif not es_pregunta and not texto.endswith((".", "?", "!")):
        texto += "."
            
    return texto

async def _generar_bytes_voz(texto: str, voz: str = "es-CL-LorenzoNeural") -> io.BytesIO:
    texto_limpio = texto.replace("*", "").replace("#", "").replace("`", "")
    communicate = edge_tts.Communicate(texto_limpio, voz)
    buffer = io.BytesIO()
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            buffer.write(chunk["data"])
    buffer.seek(0)
    return buffer

def _monitor_barge_in(reconocedor, stop_event):
    """Monitorea el micrófono mientras Chronnos habla para permitir interrupción (Barge-In)."""
    global interrupcion_solicitada
    try:
        with sr.Microphone() as fuente:
            reconocedor.energy_threshold = max(reconocedor.energy_threshold, 3500)
            while not stop_event.is_set():
                try:
                    reconocedor.listen(fuente, timeout=0.4, phrase_time_limit=1.0)
                    if not stop_event.is_set():
                        interrupcion_solicitada = True
                        pygame.mixer.music.stop()
                        print("\n[Hablar: Interrupción de voz detectada (Barge-In)]")
                        break
                except sr.WaitTimeoutError:
                    continue
                except Exception:
                    break
    except Exception:
        pass

def hablar(texto: str, voz: str = "es-CL-LorenzoNeural"):
    """Sintetiza y reproduce audio con descarga de memoria y escucha de interrupción."""
    global reproduciendo_audio, interrupcion_solicitada
    interrupcion_solicitada = False
    
    if not texto or not texto.strip():
        return

    print(f"Chronnos: {texto}")
    buffer_audio = None
    stop_event = threading.Event()
    hilo_barge_in = None
    
    try:
        buffer_audio = asyncio.run(_generar_bytes_voz(texto, voz))
        
        pygame.mixer.music.load(buffer_audio)
        pygame.mixer.music.play()
        reproduciendo_audio = True
        
        # Inicia escucha en segundo plano para Barge-In
        reconocedor_barge_in = sr.Recognizer()
        hilo_barge_in = threading.Thread(target=_monitor_barge_in, args=(reconocedor_barge_in, stop_event), daemon=True)
        hilo_barge_in.start()
        
        while pygame.mixer.music.get_busy():
            if interrupcion_solicitada:
                pygame.mixer.music.stop()
                break
            pygame.time.wait(30)
            
    except Exception as e:
        print(f"[Error de Voz TTS]: {e}")
    finally:
        stop_event.set()
        reproduciendo_audio = False
        try:
            pygame.mixer.music.stop()
            pygame.mixer.music.unload()
        except Exception:
            pass
        if buffer_audio:
            try:
                buffer_audio.close()
            except Exception:
                pass

def detener_habla():
    global interrupcion_solicitada
    interrupcion_solicitada = True
    try:
        pygame.mixer.music.stop()
        pygame.mixer.music.unload()
    except Exception:
        pass

def escuchar(silencioso=False) -> str | None:
    reconocedor = sr.Recognizer()
    reconocedor.pause_threshold = 1.3
    reconocedor.non_speaking_duration = 0.5
    
    with sr.Microphone() as fuente:
        reconocedor.dynamic_energy_threshold = True
        reconocedor.adjust_for_ambient_noise(fuente, duration=0.3) 
        
        if not silencioso:
            print("\n[Escuchando... Ya puedes hablar]")
        
        try:
            audio = reconocedor.listen(fuente, timeout=5, phrase_time_limit=15)
            texto_bruto = reconocedor.recognize_google(audio, language="es-ES")
            texto_procesado = restaurar_puntuacion(texto_bruto)
            
            if not silencioso and texto_procesado:
                print(f"Tú: {texto_procesado}")
                
            return texto_procesado
            
        except (sr.WaitTimeoutError, sr.UnknownValueError):
            return None
        except sr.RequestError:
            print("[Error de conexión en el micrófono]")
            return None
