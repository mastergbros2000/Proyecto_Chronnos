import subprocess
import pyautogui
import time
import pyperclip

# Programas nativos de Windows para apertura directa e inmediata
PROGRAMAS_DIRECTOS = {
    "bloc de notas": "notepad.exe",
    "notepad": "notepad.exe",
    "calculadora": "calc.exe",
    "paint": "mspaint.exe",
    "cmd": "cmd.exe",
    "terminal": "wt.exe"
}

def abrir_aplicacion(aplicacion: str) -> str:
    """Abre aplicaciones locales en Windows."""
    app_min = aplicacion.lower().strip()
    print(f"\n[Sistema: Buscando y abriendo {aplicacion}...]")
    
    # 1. Apertura directa e instantánea para programas nativos
    for nombre, ejecutable in PROGRAMAS_DIRECTOS.items():
        if nombre in app_min:
            subprocess.Popen(ejecutable)
            time.sleep(1.5) # Espera a que el programa obtenga el foco en pantalla
            return f"He abierto {aplicacion}."

    # 2. Respaldo por Menú Inicio para aplicaciones de terceros (Spotify, VS Code, etc.)
    pyautogui.press('win')
    time.sleep(0.5)
    pyautogui.write(aplicacion, interval=0.05)
    time.sleep(1.0)
    pyautogui.press('enter')
    time.sleep(2.5) 
    return f"He intentado abrir {aplicacion}."

def escribir_texto(texto: str) -> str:
    """Escribe cualquier texto (incluyendo tildes y caracteres especiales) mediante el portapapeles."""
    print(f"\n[Sistema: Escribiendo texto en la ventana activa...]")
    time.sleep(0.8)
    
    # Copiar al portapapeles y pegar evita errores con acentos o la 'ñ'
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
    return "He cerrado la aplicación mediante el atajo del sistema."