import cv2
import time
import os
from pathlib import Path
from PIL import Image

def capturar_imagen() -> str | None:
    """Enciende la cámara, calibra la exposición, toma una fotografía y la guarda temporalmente."""
    print("\n[Sistema: Encendiendo cámara para observar...]")
    camara = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    
    if not camara.isOpened():
        camara = cv2.VideoCapture(0)
        
    if not camara.isOpened():
        print("[Sistema: Error al acceder a la cámara]")
        return None

    # Descarta los primeros cuadros para permitir la calibración de exposición y balance
    for _ in range(5):
        camara.read()
        time.sleep(0.05)
        
    ret, frame = camara.read()
    camara.release()
    
    if ret:
        ruta = "captura_temporal.jpg"
        cv2.imwrite(ruta, frame)
        print("[Sistema: Fotografía capturada con éxito. Apagando cámara]")
        return ruta
    else:
        print("[Sistema: Error al capturar imagen del sensor]")
        return None

def inspeccionar_imagen_local(ruta: str) -> dict | None:
    """Obtiene metadatos detallados de una imagen local sin bloquear el archivo."""
    try:
        ruta_p = Path(ruta).expanduser()
        if not ruta_p.exists() or not ruta_p.is_file():
            return None
            
        stats = ruta_p.stat()
        with Image.open(ruta_p) as img:
            datos = {
                "nombre": ruta_p.name,
                "ruta_absoluta": str(ruta_p.resolve()),
                "formato": img.format or ruta_p.suffix.replace('.', '').upper(),
                "ancho": img.width,
                "alto": img.height,
                "modo": img.mode,
                "tamano_kb": round(stats.st_size / 1024, 2)
            }
        return datos
    except Exception as e:
        print(f"[Visión: Error al inspeccionar imagen {ruta}]: {e}")
        return None

def cargar_imagen_segura(ruta: str) -> Image.Image | None:
    """Carga una imagen en memoria RAM desconectándola del descriptor de archivo en disco."""
    try:
        ruta_p = Path(ruta).expanduser()
        if not ruta_p.exists() or not ruta_p.is_file():
            return None
        with Image.open(ruta_p) as img:
            return img.copy()
    except Exception as e:
        print(f"[Visión: Error al cargar imagen en memoria {ruta}]: {e}")
        return None
