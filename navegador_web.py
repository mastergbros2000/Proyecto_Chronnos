from playwright.sync_api import sync_playwright
import time
import os
import concurrent.futures

# Hilo dedicado para ejecutar Playwright sin interferir con el bucle de audio
executor_web = concurrent.futures.ThreadPoolExecutor(max_workers=1)

motor_playwright = None
navegador_actual = None
pagina_actual = None

def _buscar_ejecutable_opera() -> str | None:
    """Busca la ruta ejecutable de Opera GX en las ubicaciones habituales de Windows."""
    perfil_usuario = os.path.expanduser("~")
    posibles_rutas = [
        os.path.join(perfil_usuario, r"AppData\Local\Programs\Opera GX\launcher.exe"),
        os.path.join(perfil_usuario, r"AppData\Local\Programs\Opera GX\opera.exe"),
        r"C:\Program Files\Opera GX\launcher.exe",
        r"C:\Program Files (x86)\Opera GX\launcher.exe",
    ]
    for ruta in posibles_rutas:
        if os.path.exists(ruta):
            return ruta
    return None

def _obtener_pagina_navegador():
    global motor_playwright, navegador_actual, pagina_actual
    
    if navegador_actual is None or not navegador_actual.is_connected():
        motor_playwright = sync_playwright().start()
        ruta_opera = _buscar_ejecutable_opera()
        
        if ruta_opera:
            print(f"\n[Agente Web: Ejecutando Opera GX desde '{ruta_opera}']")
            navegador_actual = motor_playwright.chromium.launch(headless=False, executable_path=ruta_opera)
        else:
            print("\n[Agente Web: Opera GX no localizado. Usando Microsoft Edge...]")
            try:
                navegador_actual = motor_playwright.chromium.launch(headless=False, channel="msedge")
            except Exception:
                navegador_actual = motor_playwright.chromium.launch(headless=False)
                
        pagina_actual = navegador_actual.new_page()
        
    return pagina_actual

# =========================================================================
# HERRAMIENTAS WEB UNIVERSALES
# =========================================================================

def _tarea_navegar_a_url(url: str) -> str:
    try:
        page = _obtener_pagina_navegador()
        if not url.startswith("http://") and not url.startswith("https://"):
            url = "https://" + url
        page.goto(url, timeout=20000)
        titulo = page.title()
        return f"He navegado con éxito a '{url}'. Título de la página: '{titulo}'."
    except Exception as e:
        print(f"[Error del Agente Web (Navegar): {e}]")
        return f"Ocurrió un error al intentar navegar a '{url}'."

def navegar_a_url(url: str) -> str:
    """Navega a cualquier sitio web indicado."""
    future = executor_web.submit(_tarea_navegar_a_url, url)
    return future.result()

def _tarea_hacer_clic_web(elemento: str) -> str:
    try:
        page = _obtener_pagina_navegador()
        # Intenta primero hacer clic por texto visible en pantalla
        try:
            page.get_by_text(elemento, exact=False).first.click(timeout=5000)
        except Exception:
            # Si falla el texto, intenta usar el selector directo
            page.click(elemento, timeout=5000)
        return f"He hecho clic en el elemento o enlace '{elemento}'."
    except Exception as e:
        print(f"[Error del Agente Web (Clic): {e}]")
        return f"No pude hacer clic en '{elemento}'."

def hacer_clic_web(elemento: str) -> str:
    """Hace clic en un texto, enlace o botón de la página activa."""
    future = executor_web.submit(_tarea_hacer_clic_web, elemento)
    return future.result()

def _tarea_escribir_y_buscar_web(texto: str) -> str:
    try:
        page = _obtener_pagina_navegador()
        page.keyboard.type(texto)
        page.keyboard.press("Enter")
        return f"He escrito '{texto}' y presionado Enter en la página activa."
    except Exception as e:
        print(f"[Error del Agente Web (Escribir): {e}]")
        return "Ocurrió un error al escribir en la página."

def escribir_y_buscar_web(texto: str) -> str:
    """Escribe texto en el campo activo de la página web y presiona Enter."""
    future = executor_web.submit(_tarea_escribir_y_buscar_web, texto)
    return future.result()

# =========================================================================
# FLUTOS DE TRABAJO ESPECIALIZADOS (YouTube / Mercado Libre)
# =========================================================================

def _tarea_reproducir_youtube(busqueda: str) -> str:
    try:
        page = _obtener_pagina_navegador()
        page.goto("https://www.youtube.com")
        
        try:
            page.click('button[aria-label*="Aceptar"]', timeout=3000)
        except Exception:
            pass

        page.wait_for_selector('input[name="search_query"]', timeout=15000)
        page.fill('input[name="search_query"]', busqueda)
        page.press('input[name="search_query"]', 'Enter')
        
        page.wait_for_selector('ytd-video-renderer', timeout=15000)
        time.sleep(1)
        
        primer_video = page.locator('ytd-video-renderer a#video-title').first
        primer_video.click()
        
        return f"He buscado y reproducido '{busqueda}' en YouTube exitosamente."
        
    except Exception as e:
        print(f"[Error del Agente Web (YouTube): {e}]")
        return "Ocurrió un error al intentar reproducir el video en YouTube."

def buscar_y_reproducir_youtube(busqueda: str) -> str:
    future = executor_web.submit(_tarea_reproducir_youtube, busqueda)
    return future.result()

def _tarea_buscar_mercadolibre(producto: str) -> str:
    try:
        page = _obtener_pagina_navegador()
        page.goto("https://www.mercadolibre.cl/")
        
        page.wait_for_selector('input.cb1-edit', timeout=15000)
        page.fill('input.cb1-edit', producto)
        page.press('input.cb1-edit', 'Enter')
        
        page.wait_for_selector('li.ui-search-layout__item', timeout=15000)
        return f"He realizado la búsqueda de '{producto}' en Mercado Libre."
        
    except Exception as e:
        print(f"[Error del Agente Web (Mercado Libre): {e}]")
        return "Ocurrió un error al buscar en Mercado Libre."

def buscar_mercadolibre(producto: str) -> str:
    future = executor_web.submit(_tarea_buscar_mercadolibre, producto)
    return future.result()