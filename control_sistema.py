import subprocess
import pyautogui
import time
import os

def abrir_aplicacion(aplicacion: str) -> str:
    """Abre cualquier aplicación en Windows usando el menú de inicio."""
    print(f"\n[Sistema: Buscando y abriendo {aplicacion}...]")
    
    # 1. Presionamos la tecla Windows para abrir el menú de inicio
    pyautogui.press('win')
    time.sleep(1) # Pequeña pausa para que el menú cargue
    
    # 2. Escribimos el nombre de la aplicación
    pyautogui.write(aplicacion, interval=0.05)
    time.sleep(1.5) # Damos tiempo a que Windows encuentre el programa
    
    # 3. Presionamos Enter para abrir el mejor resultado
    pyautogui.press('enter')
    
    # Damos tiempo a que el programa se abra en pantalla
    time.sleep(3) 
    
    return f"He intentado abrir {aplicacion} en tu pantalla."

def escribir_texto(texto: str) -> str:
    """Escribe un texto usando el teclado virtual en la ventana que esté activa."""
    print(f"\n[Sistema: Escribiendo texto...]")
    time.sleep(1)
    pyautogui.write(texto, interval=0.05)
    return f"He escrito el texto solicitado."