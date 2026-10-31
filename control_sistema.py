import subprocess
import pyautogui
import time
import pyperclip
import webbrowser
import psutil
import os

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

def abrir_aplicacion(aplicacion: str) -> str:
    app_min = aplicacion.lower().strip()
    print(f"\n[Sistema: Procesando apertura para '{aplicacion}'...]")
    
    if "http://" in app_min or "https://" in app_min or "wikipedia" in app_min:
        url = aplicacion if aplicacion.startswith("http") else f"https://es.wikipedia.org/wiki/{aplicacion.replace('wikipedia', '').strip()}"
        webbrowser.open(url)
        return f"He abierto la página {url} en tu navegador."

    if "opera" in app_min:
        if _opera_esta_abierto():
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

    # Apertura por Menú Inicio usando el portapapeles para soportar acentos y caracteres especiales
    pyautogui.press('win')
    time.sleep(0.5)
    pyperclip.copy(aplicacion)
    pyautogui.hotkey('ctrl', 'v')
    time.sleep(1.0)
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
