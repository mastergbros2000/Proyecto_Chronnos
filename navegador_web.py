from playwright.sync_api import sync_playwright
import time
import os
import subprocess
import concurrent.futures
import psutil

# Hilo dedicado para evitar bloqueos con asyncio/audio
executor_web = concurrent.futures.ThreadPoolExecutor(max_workers=1)

motor_playwright = None
contexto_actual = None
pagina_actual = None

def _buscar_ejecutable_opera() -> str | None:
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

def _opera_esta_abierto() -> bool:
    """Verifica si el navegador Opera o Opera GX está en ejecución."""
    for proc in psutil.process_iter(['name']):
        try:
            if proc.info['name'] and 'opera' in proc.info['name'].lower():
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return False

def _obtener_pagina_navegador(es_incognito: bool = False):
    global motor_playwright, contexto_actual, pagina_actual
    
    ruta_opera = _buscar_ejecutable_opera()
    
    if contexto_actual is None or not contexto_actual.browser.is_connected():
        motor_playwright = sync_playwright().start()
        
        if es_incognito:
            print("\n[Agente Web: Abriendo ventana de Incógnito...]")
            browser = motor_playwright.chromium.launch(
                headless=False, 
                executable_path=ruta_opera, 
                args=["--incognito"]
            )
            contexto_actual = browser.new_context()
            pagina_actual = contexto_actual.new_page()
        else:
            print("\n[Agente Web: Abriendo ventana normal con perfil guardado...]")
            perfil_dir = os.path.join(os.path.expanduser("~"), ".chronnos_opera_profile")
            contexto_actual = motor_playwright.chromium.launch_persistent_context(
                user_data_dir=perfil_dir,
                headless=False,
                executable_path=ruta_opera
            )
            pagina_actual = contexto_actual.pages[0] if contexto_actual.pages else contexto_actual.new_page()
            
    return pagina_actual

# =========================================================================
# FLUJOS DE TRABAJO ESPECIALIZADOS
# =========================================================================

def _tarea_reproducir_youtube(busqueda: str, comando_original: str = "") -> str:
    try:
        es_incognito = any(p in comando_original.lower() for p in ["incognito", "incógnito", "privada", "ventana privada"])
        ruta_opera = _buscar_ejecutable_opera()
        
        # 1. Si Opera ya está abierto y no se pidió incógnito, abre una pestaña directa
        if _opera_esta_abierto() and not es_incognito and contexto_actual is None:
            print("\n[Agente Web: Opera activo detectado. Abriendo nueva pestaña...]")
            url_busqueda = f"https://www.youtube.com/results?search_query={busqueda.replace(' ', '+')}"
            if ruta_opera:
                subprocess.Popen([ruta_opera, url_busqueda])
            else:
                import webbrowser
                webbrowser.open(url_busqueda)
            return f"He abierto la búsqueda de '{busqueda}' en tu navegador."

        # 2. Si está cerrado o se requiere modo incógnito / automatización por Playwright
        page = _obtener_pagina_navegador(es_incognito=es_incognito)
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
        return f"He navegado con éxito a '{url}'. Título: '{titulo}'."
    except Exception as e:
        print(f"[Error del Agente Web (Navegar): {e}]")
        return f"Ocurrió un error al intentar navegar a '{url}'."

def navegar_a_url(url: str) -> str:
    future = executor_web.submit(_tarea_navegar_a_url, url)
    return future.result()

def _tarea_hacer_clic_web(elemento: str) -> str:
    try:
        page = _obtener_pagina_navegador()
        try:
            page.get_by_text(elemento, exact=False).first.click(timeout=5000)
        except Exception:
            page.click(elemento, timeout=5000)
        return f"He hecho clic en '{elemento}'."
    except Exception as e:
        print(f"[Error del Agente Web (Clic): {e}]")
        return f"No pude hacer clic en '{elemento}'."

def hacer_clic_web(elemento: str) -> str:
    future = executor_web.submit(_tarea_hacer_clic_web, elemento)
    return future.result()

def _tarea_escribir_y_buscar_web(texto: str) -> str:
    try:
        page = _obtener_pagina_navegador()
        page.keyboard.type(texto)
        page.keyboard.press("Enter")
        return f"He escrito '{texto}' y presionado Enter."
    except Exception as e:
        print(f"[Error del Agente Web (Escribir): {e}]")
        return "Ocurrió un error al escribir en la página."

def escribir_y_buscar_web(texto: str) -> str:
    future = executor_web.submit(_tarea_escribir_y_buscar_web, texto)
    return future.result()