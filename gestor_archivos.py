import os
import difflib
from pathlib import Path

# Tipos de archivos de texto compatibles
EXTENSIONES_TEXTO = ('.txt', '.md', '.py', '.json', '.csv', '.log', '.html', '.css', '.js', '.c', '.cpp', '.java')

def _es_similar(busqueda: str, objetivo: str, umbral: float = 0.70) -> bool:
    """Calcula si dos nombres son fonética o visualmente similares usando difflib."""
    b_min, o_min = busqueda.lower(), objetivo.lower()
    
    # 1. Coincidencia directa por subcadena
    if b_min in o_min or o_min in b_min:
        return True
        
    # 2. Ratio de similitud general
    similitud = difflib.SequenceMatcher(None, b_min, o_min).ratio()
    if similitud >= umbral:
        return True
        
    # 3. Comprobación de palabras individuales (ej: 'firecamp' vs 'firecam')
    palabras_busqueda = b_min.split()
    palabras_objetivo = o_min.split()
    for p1 in palabras_busqueda:
        for p2 in palabras_objetivo:
            if difflib.SequenceMatcher(None, p1, p2).ratio() >= umbral:
                return True
                
    return False

def buscar_archivo_en_disco(nombre_o_patron: str, ruta_inicio: str = None) -> str:
    """
    Busca archivos o carpetas en el disco tolerando errores fonéticos del micrófono.
    """
    user_home = os.path.expanduser("~")
    
    if not ruta_inicio or not os.path.exists(ruta_inicio):
        rutas_a_buscar = [
            os.path.join(user_home, "Desktop"),
            os.path.join(user_home, "Escritorio"),
            os.path.join(user_home, "Documents"),
            os.path.join(user_home, "Documentos"),
            os.path.join(user_home, "Downloads"),
            os.path.join(user_home, "Descargas"),
            os.path.join(user_home, "Videos"),
            os.path.join(user_home, "Pictures"),
            os.path.join(user_home, "Imágenes")
        ]
        rutas_a_buscar = [r for r in rutas_a_buscar if os.path.exists(r)]
    else:
        rutas_a_buscar = [ruta_inicio]

    print(f"\n[Gestor de Archivos: Buscando con tolerancia fonética para '{nombre_o_patron}'...]")
    coincidencias = []
    carpetas_ignoradas = {
        '$Recycle.Bin', 'System Volume Information', 'AppData', 'node_modules', 
        '.git', 'venv', '__pycache__', 'Local', 'Roaming', 'Cache'
    }

    for base_path in rutas_a_buscar:
        for raiz, dirs, archivos in os.walk(base_path):
            dirs[:] = [d for d in dirs if d not in carpetas_ignoradas and not d.startswith('.')]
            
            # 1. Evaluar carpetas con similitud difusa
            for d in dirs:
                if _es_similar(nombre_o_patron, d):
                    coincidencias.append(f"[Carpeta] {os.path.join(raiz, d)}")
                    if len(coincidencias) >= 10:
                        break
            
            # 2. Evaluar archivos con similitud difusa
            for archivo in archivos:
                if _es_similar(nombre_o_patron, archivo):
                    coincidencias.append(f"[Archivo] {os.path.join(raiz, archivo)}")
                    if len(coincidencias) >= 10:
                        break

            if len(coincidencias) >= 10:
                break
        if len(coincidencias) >= 10:
            break

    if coincidencias:
        lista_fmt = "\n".join([f"- {r}" for r in coincidencias])
        return f"Encontré los siguientes elementos (incluyendo variantes similares):\n{lista_fmt}"
    
    return f"No se encontraron archivos ni carpetas similares a '{nombre_o_patron}' en las ubicaciones habituales."

def explorar_carpeta(ruta: str) -> str:
    """Lista todos los archivos y subcarpetas dentro de un directorio específico."""
    try:
        ruta_p = Path(ruta).expanduser()
        if not ruta_p.exists():
            return f"La ruta '{ruta}' no existe en la PC."
        
        elementos = os.listdir(ruta_p)
        archivos = [e for e in elementos if os.path.isfile(ruta_p / e)]
        carpetas = [e for e in elementos if os.path.isdir(ruta_p / e)]
        
        res = f"Contenido de '{ruta}':\n"
        if carpetas:
            res += "Carpetas:\n" + "\n".join([f" [DIR] {c}" for c in carpetas]) + "\n"
        if archivos:
            res += "Archivos:\n" + "\n".join([f" [FILE] {a}" for a in archivos])
            
        if not archivos and not carpetas:
            res += "(La carpeta está vacía)"
            
        return res
    except Exception as e:
        return f"Error al explorar la carpeta: {e}"

def leer_archivo_local(ruta: str) -> str:
    """Lee y extrae el texto de un archivo (.txt, .md, .py, .pdf, .docx, etc.)."""
    try:
        ruta_p = Path(ruta).expanduser()
        if not ruta_p.exists():
            return f"El archivo '{ruta}' no fue encontrado."

        ext = ruta_p.suffix.lower()

        if ext == '.pdf':
            try:
                import pypdf
                reader = pypdf.PdfReader(ruta_p)
                texto = "\n".join([page.extract_text() for page in reader.pages if page.extract_text()])
                return f"Contenido del PDF '{ruta_p.name}':\n{texto[:4000]}"
            except ImportError:
                return "Para leer PDFs, instala 'pypdf' usando: pip install pypdf"

        elif ext == '.docx':
            try:
                import docx
                doc = docx.Document(ruta_p)
                texto = "\n".join([p.text for p in doc.paragraphs])
                return f"Contenido del documento Word '{ruta_p.name}':\n{texto[:4000]}"
            except ImportError:
                return "Para leer archivos DOCX, instala 'python-docx' usando: pip install python-docx"

        elif ext in EXTENSIONES_TEXTO or ext == '':
            with open(ruta_p, 'r', encoding='utf-8', errors='ignore') as f:
                contenido = f.read(4000)
            return f"Contenido de '{ruta_p.name}':\n{contenido}"

        else:
            return f"Formato '{ext}' no soportado directamente para lectura de texto."

    except Exception as e:
        return f"Error al leer el archivo '{ruta}': {e}"

def crear_o_modificar_archivo(ruta: str, contenido: str, modo: str = "sobreescribir") -> str:
    """Crea un nuevo archivo o actualiza uno existente."""
    try:
        ruta_p = Path(ruta).expanduser()
        os.makedirs(ruta_p.parent, exist_ok=True)
        
        modo_archivo = 'a' if modo.lower() == 'anexar' else 'w'
        
        with open(ruta_p, modo_archivo, encoding='utf-8') as f:
            f.write(contenido + "\n")
            
        accion = "actualizado (anexado)" if modo.lower() == 'anexar' else "creado/sobreescrito"
        return f"El archivo '{ruta_p.name}' fue {accion} con éxito en '{ruta_p.parent}'."
    except Exception as e:
        return f"Error al guardar el archivo en '{ruta}': {e}"

def comparar_archivos_locales(ruta1: str, ruta2: str) -> str:
    """Lee dos archivos locales para comparar su contenido."""
    c1 = leer_archivo_local(ruta1)
    c2 = leer_archivo_local(ruta2)
    return f"--- CONTENIDO ARCHIVO 1 ({ruta1}) ---\n{c1}\n\n--- CONTENIDO ARCHIVO 2 ({ruta2}) ---\n{c2}"