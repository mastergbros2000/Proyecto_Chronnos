import subprocess
import pyautogui
import time
import pyperclip
import webbrowser
import psutil
import os
import pygetwindow as gw

PROGRAMAS_DIRECTOS = {
    "bloc de notas": "notepad.exe",
    "notepad": "notepad.exe",
    "calculadora": "calc.exe",
    "paint": "mspaint.exe",
    "cmd": "cmd.exe",
    "terminal": "wt.exe",
    "edge": "msedge.exe",
    "microsoft edge": "msedge.exe",
    "chrome": "chrome.exe",
    "google chrome": "chrome.exe",
    "explorador": "explorer.exe"
}

def _opera_esta_abierto() -> bool:
    for proc in psutil.process_iter(['name']):
        try:
            if proc.info['name'] and 'opera' in proc.info['name'].lower():
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return False

def _traer_al_frente(nombre_app: str) -> bool:
    """Focus Manager: Busca una ventana existente y la trae al frente evitando duplicar procesos."""
    try:
        ventanas = gw.getAllWindows()
        nombre_min = nombre_app.lower().strip()
        for v in ventanas:
            if v.title and nombre_min in v.title.lower():
                try:
                    if v.isMinimized:
                        v.restore()
                    v.activate()
                    time.sleep(0.3)
                    return True
                except Exception as err:
                    print(f"[Focus Manager: Aviso al activar ventana]: {err}")
                    return False
    except Exception as e:
        print(f"[Focus Manager: Error general]: {e}")
    return False

def abrir_aplicacion(aplicacion: str) -> str:
    app_min = aplicacion.lower().strip()
    print(f"\n[Sistema: Procesando apertura para '{aplicacion}'...]")
    
    # 0. Verificación por Focus Manager si ya está abierta
    if _traer_al_frente(app_min):
        return f"He traído '{aplicacion}' al frente de tu pantalla."
    
    # 1. Atajo directo infalible para Configuración / Ajustes de Windows
    palabras_configuracion = ["configuracion", "configuración", "ajustes", "settings", "panel de configuracion", "panel de configuración"]
    if any(termino in app_min for termino in palabras_configuracion):
        try:
            subprocess.Popen("start ms-settings:", shell=True)
            time.sleep(1.5)
            return "He abierto la Configuración de Windows."
        except Exception as e:
            print(f"[Error al abrir configuración]: {e}")

    # 2. Direcciones URL o búsquedas directas
    if "http://" in app_min or "https://" in app_min or "wikipedia" in app_min:
        url = aplicacion if aplicacion.startswith("http") else f"https://es.wikipedia.org/wiki/{aplicacion.replace('wikipedia', '').strip()}"
        webbrowser.open(url)
        return f"He abierto la página {url} en tu navegador."

    # 3. Navegador Opera GX
    if "opera" in app_min:
        if _opera_esta_abierto():
            if _traer_al_frente("opera"):
                return "Opera GX ya se encontraba abierto y lo traje al frente."
            return "Opera GX ya se encuentra abierto en tu pantalla."
        else:
            perfil_usuario = os.path.expanduser("~")
            ruta_opera = os.path.join(perfil_usuario, r"AppData\Local\Programs\Opera GX\launcher.exe")
            if os.path.exists(ruta_opera):
                subprocess.Popen([ruta_opera])
            else:
                webbrowser.open("https://www.google.com")
            time.sleep(2.0)
            return "He abierto Opera GX."

    # 4. Programas directos por ejecutable nativo
    for nombre, ejecutable in PROGRAMAS_DIRECTOS.items():
        if nombre in app_min:
            try:
                subprocess.Popen(ejecutable)
                time.sleep(1.5)
                return f"He abierto {aplicacion}."
            except Exception:
                pass

    if any(web_term in app_min for web_term in ["pestaña", "pestana", "chrome", "navegador", "internet"]):
        webbrowser.open("https://www.google.com")
        return "He abierto tu navegador web por defecto."

    # 5. Respaldo por Menú Inicio para otras aplicaciones con pausa optimizada
    pyautogui.press('win')
    time.sleep(0.6)
    pyperclip.copy(aplicacion)
    pyautogui.hotkey('ctrl', 'v')
    time.sleep(1.8)  # Pausa aumentada para asegurar que Windows indexe, seleccione y resalte la aplicación
    pyautogui.press('enter')
    time.sleep(2.0) 
    return f"He intentado abrir {aplicacion}."

def escribir_texto(texto: str) -> str:
    print(f"\n[Sistema: Escribiendo texto en la ventana activa...]")
    time.sleep(1.0)
    pyperclip.copy(texto)
    pyautogui.hotkey('ctrl', 'v')
    return "He escrito el texto solicitado."

def presionar_tecla(tecla: str) -> str:
    print(f"\n[Sistema: Presionando tecla '{tecla}'...]")
    time.sleep(0.3)
    pyautogui.press(tecla.lower())
    return f"He presionado la tecla {tecla}."

def cerrar_ventana() -> str:
    print(f"\n[Sistema: Cerrando ventana activa...]")
    time.sleep(0.3)
    pyautogui.hotkey('alt', 'f4')
    return "He cerrado la ventana activa."

def consultar_estado_pc() -> str:
    """Telemetría PC: Obtiene el uso de CPU, RAM, batería y espacio en disco C:."""
    try:
        uso_cpu = psutil.cpu_percent(interval=0.4)
        memoria = psutil.virtual_memory()
        disco_c = psutil.disk_usage("C:\\")
        
        ram_usada_gb = round(memoria.used / (1024**3), 1)
        ram_total_gb = round(memoria.total / (1024**3), 1)
        disco_libre_gb = round(disco_c.free / (1024**3), 1)
        
        resumen = (
            f"Telemetría del sistema: Uso de CPU al {uso_cpu}%, "
            f"memoria RAM al {memoria.percent}% ({ram_usada_gb} GB de {ram_total_gb} GB), "
            f"espacio libre en disco C: {disco_libre_gb} GB."
        )
        
        bateria = psutil.sensors_battery()
        if bateria is not None:
            estado_bat = "conectado a corriente" if bateria.power_plugged else "usando batería"
            resumen += f" Batería al {int(bateria.percent)}% ({estado_bat})."
            
        return resumen
    except Exception as e:
        print(f"[Telemetría: Error al consultar estado de la PC]: {e}")
        return "No pude obtener la telemetría del sistema en este momento."

def subir_volumen() -> str:
    """Aumenta el volumen general del sistema."""
    try:
        for _ in range(3):
            pyautogui.press('volumeup')
            time.sleep(0.04)
        return "He subido el volumen."
    except Exception as e:
        return f"Error al subir volumen: {e}"

def bajar_volumen() -> str:
    """Disminuye el volumen general del sistema."""
    try:
        for _ in range(3):
            pyautogui.press('volumedown')
            time.sleep(0.04)
        return "He bajado el volumen."
    except Exception as e:
        return f"Error al bajar volumen: {e}"

def silenciar_audio() -> str:
    """Alterna el silencio de audio del sistema."""
    try:
        pyautogui.press('volumemute')
        return "He alternado el estado de silencio del sistema."
    except Exception as e:
        return f"Error al silenciar audio: {e}"

def pausar_multimedia() -> str:
    """Pausa o reanuda la reproducción multimedia activa."""
    try:
        pyautogui.press('playpause')
        return "He alternado la reproducción multimedia."
    except Exception as e:
        return f"Error en control multimedia: {e}"

