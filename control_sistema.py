import subprocess
import pyautogui
import time
import webbrowser

def abrir_aplicacion(aplicacion: str) -> str:
    """Abre aplicaciones locales o páginas web utilizando el navegador predeterminado del sistema."""
    print(f"\n[Sistema: Procesando solicitud para: {aplicacion}]")
    app_limpia = aplicacion.lower()
    
    # Si el usuario pide YouTube o páginas web, usamos el módulo nativo webbrowser
    if "youtube" in app_limpia:
        webbrowser.open("https://www.youtube.com")
        return "He abierto YouTube en tu navegador."
    elif "google" in app_limpia:
        webbrowser.open("https://www.google.com")
        return "He abierto Google en tu navegador."
    elif "navegador" in app_limpia or "internet" in app_limpia:
        webbrowser.open("https://www.google.com")
        return "He abierto el navegador web."
        
    # Para programas locales (Bloc de notas, calculadora, Paint, etc.) usando el menú de inicio
    pyautogui.press('win')
    time.sleep(1)
    pyautogui.write(aplicacion, interval=0.05)
    time.sleep(1.5)
    pyautogui.press('enter')
    
    time.sleep(3) 
    return f"He intentado abrir {aplicacion} en tu pantalla."

def escribir_texto(texto: str) -> str:
    """Escribe un texto usando el teclado virtual en la ventana activa."""
    print(f"\n[Sistema: Escribiendo texto...]")
    time.sleep(1)
    pyautogui.write(texto, interval=0.05)
    return "He escrito el texto solicitado."

def presionar_tecla(tecla: str) -> str:
    """Presiona una tecla especial (enter, tab, etc.)."""
    print(f"\n[Sistema: Presionando tecla '{tecla}'...]")
    time.sleep(0.5)
    pyautogui.press(tecla.lower())
    return f"He presionado la tecla {tecla}."

def cerrar_ventana() -> str:
    """Cierra la aplicación activa simulando Alt + F4."""
    print(f"\n[Sistema: Cerrando ventana activa...]")
    time.sleep(0.5)
    pyautogui.hotkey('alt', 'f4')
    return "He cerrado la aplicación activa."