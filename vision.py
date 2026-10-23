import cv2

def capturar_imagen() -> str:
    """Enciende la cámara, toma una fotografía y la guarda temporalmente."""
    print("\n[Sistema: Encendiendo cámara para observar...]")
    # El 0 indica la cámara principal de tu computadora
    camara = cv2.VideoCapture(0) 
    
    # Damos un pequeño respiro para que la cámara enfoque (opcional pero recomendado)
    cv2.waitKey(500) 
    
    ret, frame = camara.read()
    camara.release()
    
    if ret:
        ruta = "captura_temporal.jpg"
        cv2.imwrite(ruta, frame)
        print("[Sistema: Fotografía capturada con éxito. Apagando cámara]")
        return ruta
    else:
        print("[Sistema: Error al acceder a la cámara]")
        return None