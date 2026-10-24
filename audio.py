import speech_recognition as sr
import edge_tts
import asyncio
import os
import threading
import time

# Control global del estado de voz
hablando_actualmente = False
parar_audio = False
archivo_audio_temporal = "voz_temporal.mp3"

async def _generar_y_reproducir_audio(texto_limpio):
    global hablando_actualmente, parar_audio
    try:
        # 1. Asegurarnos de limpiar cualquier archivo bloqueado previo antes de empezar
        if os.path.exists(archivo_audio_temporal):
            try:
                os.remove(archivo_audio_temporal)
            except:
                pass

        # Voz neuronal de alta calidad en español
        voz_seleccionada = "es-ES-AlvaroNeural" 
        
        comunicador = edge_tts.Communicate(texto_limpio, voz_seleccionada)
        await comunicador.save(archivo_audio_temporal)
        
        # 2. Reproducimos el audio usando el reproductor multimedia nativo de Windows por comando directo, 
        # evitando el bloqueo de permisos que causa 'playsound'
        if os.path.exists(archivo_audio_temporal) and not parar_audio:
            # Usamos un comando limpio de Windows para abrir y cerrar el stream rápidamente
            ruta_absoluta = os.path.abspath(archivo_audio_temporal)
            
            # Usamos un reproductor de Windows por línea de comandos invisible o directa sin app gráfica
            import winsound
            # Como winsound nativamente solo lee .wav, usaremos un truco con os.system sin bloqueos:
            os.system(f'powershell -c "(New-Object Media.SoundPlayer \'{ruta_absoluta}\').PlaySync();"')
            
    except Exception as e:
        print(f"[Error en motor de voz neuronal: {e}]")
    finally:
        hablando_actualmente = False
        parar_audio = False

def hablar(texto):
    """Inicia la síntesis de voz neuronal de alta naturalidad."""
    global hablando_actualmente, parar_audio
    
    if hablando_actualmente:
        parar_audio = True
        threading.Event().wait(0.1)

    texto_limpio = texto.replace("*", "").replace("#", "")
    print(f"Chronnos: {texto_limpio}")
    
    hablando_actualmente = True
    parar_audio = False
    
    def correr_async():
        asyncio.run(_generar_y_reproducir_audio(texto_limpio))

    hilo_voz = threading.Thread(target=correr_async)
    hilo_voz.daemon = True
    hilo_voz.start()

def escuchar(silencioso=False):
    """Maneja la entrada del micrófono optimizada para evitar falsos silencios."""
    global hablando_actualmente
    reconocedor = sr.Recognizer()
    reconocedor.pause_threshold = 0.8  # Un pequeño respiro extra para que no te corte al hablar
    
    with sr.Microphone() as fuente:
        reconocedor.adjust_for_ambient_noise(fuente, duration=0.4)
        reconocedor.dynamic_energy_threshold = False
        reconocedor.energy_threshold = 250 
        
        try:
            if not silencioso:
                print("\n[Escuchando... Ya puedes hablar]")
            
            # Subimos ligeramente el timeout a 7 segundos para darte más margen de hablar con tranquilidad
            audio = reconocedor.listen(fuente, timeout=7, phrase_time_limit=10)
            texto = reconocedor.recognize_google(audio, language="es-ES")
            if not silencioso:
                print(f"Tú: {texto}")
            return texto.lower()
                    
        except sr.WaitTimeoutError:
            return None
        except Exception:
            return None