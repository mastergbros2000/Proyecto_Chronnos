import os
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "hide"

import speech_recognition as sr
import pygame
import io
import asyncio
import edge_tts
import re
import threading
import queue
import time as _time
import math
import struct
import wave

pygame.mixer.init()

reproduciendo_audio = False
interrupcion_solicitada = False

def _crear_chime_wav(frecuencias: list[tuple[float, float]], duracion_total: float = 0.15) -> io.BytesIO:
    """Genera en memoria RAM un micro-buffer WAV senoidal con envolvente suave para chimes en 0 ms."""
    samplerate = 22050
    buffer = io.BytesIO()
    with wave.open(buffer, 'wb') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(samplerate)
        
        n_muestras = int(samplerate * duracion_total)
        muestras = []
        for i in range(n_muestras):
            t = i / samplerate
            envolvente = math.exp(-4.0 * (t / duracion_total))
            muestra = 0.0
            for freq, amp in frecuencias:
                muestra += amp * math.sin(2.0 * math.pi * freq * t)
            muestra = int(max(-32767, min(32767, muestra * envolvente * 16000)))
            muestras.append(struct.pack('<h', muestra))
        wav_file.writeframes(b''.join(muestras))
    buffer.seek(0)
    return buffer

chime_activacion_sound = None
chime_ejecucion_sound = None

try:
    buf_act = _crear_chime_wav([(1046.50, 0.6), (1318.51, 0.4)], duracion_total=0.12)
    chime_activacion_sound = pygame.mixer.Sound(buf_act)
    
    buf_ejec = _crear_chime_wav([(587.33, 0.5), (880.00, 0.5)], duracion_total=0.16)
    chime_ejecucion_sound = pygame.mixer.Sound(buf_ejec)
except Exception as e:
    print(f"[Audio Chimes: Inicialización]: {e}")

def reproducir_chime_activacion():
    """Chime instantáneo en 0 ms al detectar la wake-word 'Chronnos'."""
    if chime_activacion_sound:
        try:
            chime_activacion_sound.play()
        except Exception:
            pass

def reproducir_chime_ejecucion():
    """Chime suave al concluir exitosamente una acción física o herramienta."""
    if chime_ejecucion_sound:
        try:
            chime_ejecucion_sound.play()
        except Exception:
            pass

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

async def _generar_bytes_voz(texto: str, voz: str = "es-CL-LorenzoNeural", rate: str = "+0%") -> io.BytesIO:
    texto_limpio = texto.replace("*", "").replace("#", "").replace("`", "")
    communicate = edge_tts.Communicate(texto_limpio, voz, rate=rate)
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

def hablar(texto: str, voz: str = "es-CL-LorenzoNeural", rate: str = None):
    """Sintetiza y reproduce audio con velocidad dinámica y escucha de interrupción."""
    global reproduciendo_audio, interrupcion_solicitada
    interrupcion_solicitada = False
    
    if not texto or not texto.strip():
        return

    # Escalamiento dinámico: confirmaciones breves más rápidas (+15%), explicaciones a ritmo normal (+0%)
    if rate is None:
        rate = "+15%" if len(texto.split()) <= 7 else "+0%"

    print(f"Chronnos: {texto}")
    buffer_audio = None
    stop_event = threading.Event()
    hilo_barge_in = None
    
    try:
        buffer_audio = asyncio.run(_generar_bytes_voz(texto, voz, rate=rate))
        
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

def hablar_stream(iterador_oraciones, voz: str = "es-CL-LorenzoNeural"):
    """
    Reproduce oraciones en streaming con latencia mínima.
    Consume un iterador/generador de cadenas de texto (oraciones completas),
    sintetiza cada una con edge-tts y la reproduce en cuanto esté lista.
    El audio de la oración N+1 se prepara en un hilo de prefetch mientras
    se reproduce la oración N, eliminando el tiempo muerto entre frases.
    Soporta interrupción por Barge-In igual que hablar().
    """
    global reproduciendo_audio, interrupcion_solicitada
    interrupcion_solicitada = False

    cola_buffers: queue.Queue = queue.Queue(maxsize=2)  # prefetch de máximo 2 oraciones adelante
    SENTINEL = object()

    def _sintetizar_worker():
        """Hilo productor: convierte cada oración a bytes MP3 y los encola."""
        for oracion in iterador_oraciones:
            if not oracion or not oracion.strip():
                continue
            if interrupcion_solicitada:
                break
            try:
                buf = asyncio.run(_generar_bytes_voz(oracion, voz))
                cola_buffers.put((oracion, buf))
            except Exception as e:
                print(f"[Hablar Stream: Error al sintetizar '{oracion[:40]}': {e}]")
        cola_buffers.put(SENTINEL)

    hilo_sintetizador = threading.Thread(target=_sintetizar_worker, daemon=True)
    hilo_sintetizador.start()

    stop_event = threading.Event()
    reconocedor_barge_in = sr.Recognizer()
    hilo_barge_in = threading.Thread(
        target=_monitor_barge_in,
        args=(reconocedor_barge_in, stop_event),
        daemon=True
    )
    hilo_barge_in.start()

    reproduciendo_audio = True
    buffer_actual = None

    try:
        while True:
            if interrupcion_solicitada:
                pygame.mixer.music.stop()
                break

            item = cola_buffers.get()
            if item is SENTINEL:
                break

            oracion_texto, buffer_actual = item
            print(f"Chronnos: {oracion_texto}")

            try:
                pygame.mixer.music.load(buffer_actual)
                pygame.mixer.music.play()

                while pygame.mixer.music.get_busy():
                    if interrupcion_solicitada:
                        pygame.mixer.music.stop()
                        break
                    pygame.time.wait(25)

            except Exception as e:
                print(f"[Hablar Stream: Error al reproducir: {e}]")
            finally:
                try:
                    pygame.mixer.music.unload()
                except Exception:
                    pass
                try:
                    buffer_actual.close()
                except Exception:
                    pass
                buffer_actual = None

    except Exception as e:
        print(f"[Error en hablar_stream: {e}]")
    finally:
        stop_event.set()
        reproduciendo_audio = False
        try:
            pygame.mixer.music.stop()
            pygame.mixer.music.unload()
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
    """Captura audio del micrófono con calibración anti-eco y re-bind autónomo."""
    try:
        reconocedor = sr.Recognizer()
        # Calibración estricta anti-eco: umbral fijo de 1200 y pausa de 1.0s para ignorar eco de altavoces
        reconocedor.dynamic_energy_threshold = False
        reconocedor.energy_threshold = 1200
        reconocedor.pause_threshold = 1.0
        reconocedor.non_speaking_duration = 0.4
        
        with sr.Microphone() as fuente:
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
            except sr.RequestError as e:
                print(f"[Audio: Error de conexión en servicio de voz]: {e}")
                return None
    except Exception as hardware_err:
        # Re-bind autónomo ante desconexiones de hardware o micro Bluetooth/USB
        print(f"[Audio: Alerta de hardware en micrófono, re-intentando enlace]: {hardware_err}")
        _time.sleep(0.5)
        return None
