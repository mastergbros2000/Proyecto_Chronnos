import speech_recognition as sr
import edge_tts
import asyncio
import os
import threading
import time
import pygame
import uuid

# Inicializamos el motor de audio de forma segura
pygame.mixer.init()

hablando_actualmente = False
parar_audio = False
texto_actual_voz = ""

async def _generar_y_reproducir_audio(texto_limpio):
    global hablando_actualmente, parar_audio
    # Generamos un archivo único para evitar el error "Permission denied"
    archivo_unico = f"voz_{uuid.uuid4().hex[:8]}.mp3"
    
    try:
        voz_seleccionada = "es-ES-AlvaroNeural" 
        comunicador = edge_tts.Communicate(texto_limpio, voz_seleccionada)
        await comunicador.save(archivo_unico)
        
        if os.path.exists(archivo_unico) and not parar_audio:
            pygame.mixer.music.load(archivo_unico)
            pygame.mixer.music.play()
            
            # Mantenemos el hilo vivo mientras habla
            while pygame.mixer.music.get_busy():
                if parar_audio:
                    pygame.mixer.music.stop()
                    break
                time.sleep(0.1)
            
            # Liberamos el archivo de la memoria de forma segura
            try: pygame.mixer.music.unload()
            except: pass
            
            # Intentamos limpiar el archivo del disco
            try: os.remove(archivo_unico)
            except: pass
            
    except Exception as e:
        print(f"[Error en motor de voz neuronal: {e}]")
    finally:
        hablando_actualmente = False
        parar_audio = False

def hablar(texto):
    """Inicia la síntesis de voz en un hilo separado (Asíncrono)."""
    global hablando_actualmente, parar_audio, texto_actual_voz
    
    if hablando_actualmente:
        parar_audio = True
        pygame.mixer.music.stop()
        try: pygame.mixer.music.unload()
        except: pass
        threading.Event().wait(0.2)

    texto_limpio = texto.replace("*", "").replace("#", "")
    print(f"Chronnos: {texto_limpio}")
    
    texto_actual_voz = texto_limpio.lower()
    hablando_actualmente = True
    parar_audio = False
    
    def correr_async():
        asyncio.run(_generar_y_reproducir_audio(texto_limpio))

    # Ejecución asíncrona mediante hilos
    hilo_voz = threading.Thread(target=correr_async)
    hilo_voz.daemon = True
    hilo_voz.start()

def _es_eco(texto_escuchado, texto_dicho):
    """Filtro inteligente para ignorar la propia voz de Chronnos por los altavoces."""
    escuchado_limpio = texto_escuchado.replace(",", "").replace(".", "").lower()
    dicho_limpio = texto_dicho.replace(",", "").replace(".", "").lower()
    
    if escuchado_limpio in dicho_limpio:
        return True
        
    palabras_escuchadas = escuchado_limpio.split()
    palabras_dichas = dicho_limpio.split()
    variantes_nombre = ["chrono", "kronno", "chronos", "chronnos", "crono", "soy", "hola"]
    
    coincidencias = sum(1 for p in palabras_escuchadas if p in palabras_dichas or p in variantes_nombre)
    if len(palabras_escuchadas) > 0 and (coincidencias / len(palabras_escuchadas)) >= 0.5:
        return True
    return False

def _escuchar_interrupcion(reconocedor, fuente):
    """Vigila el micrófono mientras Chronnos está hablando."""
    global hablando_actualmente, parar_audio, texto_actual_voz
    time.sleep(0.8) # Pequeño respiro inicial
    
    while hablando_actualmente:
        try:
            audio_interrupcion = reconocedor.listen(fuente, timeout=0.3, phrase_time_limit=2.0)
            texto_interrupcion = reconocedor.recognize_google(audio_interrupcion, language="es-ES").lower()
            
            if texto_interrupcion.strip():
                if _es_eco(texto_interrupcion, texto_actual_voz):
                    continue 
                
                print(f"\n[Interrupción detectada con orden nueva]: {texto_interrupcion}")
                parar_audio = True
                pygame.mixer.music.stop()
                try: pygame.mixer.music.unload()
                except: pass
                hablando_actualmente = False
                return texto_interrupcion
        except:
            continue
    return None

def escuchar(silencioso=False):
    """Maneja la entrada del micrófono optimizada."""
    global hablando_actualmente
    reconocedor = sr.Recognizer()
    reconocedor.pause_threshold = 0.8 # Respiro ajustado para que no te corte
    
    with sr.Microphone() as fuente:
        reconocedor.adjust_for_ambient_noise(fuente, duration=0.4)
        reconocedor.dynamic_energy_threshold = False
        reconocedor.energy_threshold = 280 
        
        try:
            while True:
                if hablando_actualmente:
                    resultado_interrupcion = _escuchar_interrupcion(reconocedor, fuente)
                    if resultado_interrupcion:
                        return resultado_interrupcion
                else:
                    if not silencioso:
                        print("\n[Escuchando... Ya puedes hablar]")
                    
                    audio = reconocedor.listen(fuente, timeout=6, phrase_time_limit=12)
                    texto = reconocedor.recognize_google(audio, language="es-ES")
                    if not silencioso:
                        print(f"Tú: {texto}")
                    return texto.lower()
                    
        except sr.WaitTimeoutError:
            return None
        except Exception:
            return None