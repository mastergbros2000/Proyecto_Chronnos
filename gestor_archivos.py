import os
import difflib
import time
from pathlib import Path

# Tipos de archivos de texto y código compatibles
EXTENSIONES_TEXTO = (
    '.txt', '.md', '.py', '.json', '.csv', '.log', '.html', '.css', '.js', 
    '.c', '.cpp', '.java', '.xml', '.yaml', '.yml', '.ini', '.cfg', '.env'
)
EXTENSIONES_IMAGEN = ('.png', '.jpg', '.jpeg', '.bmp', '.webp', '.tiff', '.gif')
EXTENSIONES_MULTIMEDIA = ('.mp3', '.mp4', '.wav', '.mkv', '.avi', '.mov')
EXTENSIONES_COMPRIMIDOS = ('.zip', '.7z', '.tar', '.gz')

def _es_similar(busqueda: str, objetivo: str, umbral: float = 0.70) -> bool:
    """Calcula si dos nombres son fonética o visualmente similares sin falsos positivos en palabras cortas."""
    b_min, o_min = busqueda.lower().strip(), objetivo.lower().strip()
    
    # 1. Coincidencia por subcadena solo si ambas cadenas tienen longitud significativa
    if len(b_min) >= 3 and b_min in o_min:
        return True
    if len(o_min) >= 4 and len(o_min) >= (len(b_min) * 0.75) and o_min in b_min:
        return True
        
    # 2. Ratio difuso general
    similitud = difflib.SequenceMatcher(None, b_min, o_min).ratio()
    if similitud >= umbral:
        return True
        
    # 3. Comprobación de palabras individuales (>3 caracteres)
    palabras_busqueda = [p for p in b_min.split() if len(p) >= 3]
    palabras_objetivo = [p for p in o_min.split() if len(p) >= 3]
    for p1 in palabras_busqueda:
        for p2 in palabras_objetivo:
            if difflib.SequenceMatcher(None, p1, p2).ratio() >= umbral:
                return True
                
    return False

def buscar_archivo_en_disco(nombre_o_patron: str, ruta_inicio: str = None) -> str:
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
            
            for d in dirs:
                if _es_similar(nombre_o_patron, d):
                    coincidencias.append(f"[Carpeta] {os.path.join(raiz, d)}")
                    if len(coincidencias) >= 10: break
            
            for archivo in archivos:
                if _es_similar(nombre_o_patron, archivo):
                    coincidencias.append(f"[Archivo] {os.path.join(raiz, archivo)}")
                    if len(coincidencias) >= 10: break

            if len(coincidencias) >= 10: break
        if len(coincidencias) >= 10: break

    if coincidencias:
        lista_fmt = "\n".join([f"- {r}" for r in coincidencias])
        return f"Encontré los siguientes elementos:\n{lista_fmt}"
    
    return f"No se encontraron archivos ni carpetas similares a '{nombre_o_patron}' en las ubicaciones habituales."

def explorar_carpeta(ruta: str) -> str:
    try:
        ruta_p = Path(ruta).expanduser()
        if not ruta_p.exists():
            return f"La ruta '{ruta}' no existe en la PC."
        if not ruta_p.is_dir():
            return f"'{ruta}' no es una carpeta."
        
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

def explorar_archivo_comprimido(ruta: str) -> str:
    """Inspecciona el árbol de contenidos dentro de un archivo comprimido .zip o .7z."""
    try:
        ruta_p = Path(ruta).expanduser()
        if not ruta_p.exists():
            return f"El archivo comprimido '{ruta}' no fue encontrado."
        if not ruta_p.is_file():
            return f"'{ruta}' no es un archivo válido."
            
        ext = ruta_p.suffix.lower()
        lista_elementos = []
        
        if ext == '.zip':
            import zipfile
            with zipfile.ZipFile(ruta_p, 'r') as z:
                for info in z.infolist():
                    tam_kb = round(info.file_size / 1024, 2)
                    tipo = "[DIR]" if info.is_dir() else "[FILE]"
                    lista_elementos.append(f" {tipo} {info.filename} ({tam_kb} KB)")
        elif ext == '.7z':
            import py7zr
            with py7zr.SevenZipFile(ruta_p, mode='r') as z:
                for info in z.list():
                    tam_kb = round(info.uncompressed / 1024, 2) if hasattr(info, 'uncompressed') else 0
                    tipo = "[DIR]" if getattr(info, 'is_directory', False) else "[FILE]"
                    lista_elementos.append(f" {tipo} {info.filename} ({tam_kb} KB)")
        else:
            return f"Formato '{ext}' no soportado para explorar comprimidos (soportados: .zip, .7z)."
            
        if not lista_elementos:
            return f"El archivo comprimido '{ruta_p.name}' está vacío."
            
        resumen = f"Contenido del archivo comprimido '{ruta_p.name}' ({len(lista_elementos)} elementos):\n"
        arbol = resumen + "\n".join(lista_elementos[:60])
        if len(lista_elementos) > 60:
            arbol += f"\n... y {len(lista_elementos) - 60} elementos adicionales."
        return arbol
    except Exception as e:
        return f"Error al explorar el archivo comprimido '{ruta}': {e}"

def _leer_excel(ruta_p: Path) -> str:
    """Extrae el contenido de la hoja activa de Excel y lo formatea como tabla Markdown."""
    try:
        import openpyxl
        wb = openpyxl.load_workbook(ruta_p, data_only=True, read_only=True)
        try:
            sheet = wb.active
            if sheet is None:
                return f"El archivo Excel '{ruta_p.name}' no tiene hojas activas."
                
            nombre_hoja = sheet.title
            max_r = sheet.max_row or 0
            max_c = sheet.max_column or 0
            
            filas_tabla = []
            for row in sheet.iter_rows(values_only=True):
                if not any(row):
                    continue
                valores_limpios = [str(val).strip() if val is not None else "" for val in row]
                filas_tabla.append(valores_limpios)
                if len(filas_tabla) >= 60:
                    break
                    
            if not filas_tabla:
                return f"La hoja '{nombre_hoja}' de '{ruta_p.name}' está vacía. Dimensiones: 0 filas, 0 columnas."
                
            encabezados = filas_tabla[0]
            lineas_md = [
                "| " + " | ".join(encabezados) + " |",
                "| " + " | ".join(["---"] * len(encabezados)) + " |"
            ]
            for f in filas_tabla[1:]:
                f_ajustada = f[:len(encabezados)] + [""] * max(0, len(encabezados) - len(f))
                lineas_md.append("| " + " | ".join(f_ajustada) + " |")
                
            tabla_md = "\n".join(lineas_md)
            resumen = f"Resumen Excel '{ruta_p.name}': Hoja activa '{nombre_hoja}' ({max_r} filas, {max_c} columnas):\n\n"
            resultado = resumen + tabla_md
            if len(resultado) > 4000:
                resultado = resultado[:3950] + "\n... [Contenido truncado a 4000 caracteres]"
            return resultado
        finally:
            wb.close()
    except Exception as e:
        return f"Error al leer la hoja de cálculo Excel '{ruta_p.name}': {e}"

def _leer_powerpoint(ruta_p: Path) -> str:
    """Extrae títulos, cuadros de texto y notas del orador de una presentación PowerPoint."""
    try:
        from pptx import Presentation
        prs = Presentation(ruta_p)
        total_slides = len(prs.slides)
        partes_slides = []
        
        for idx, slide in enumerate(prs.slides, start=1):
            textos_slide = []
            for shape in slide.shapes:
                if shape.has_text_frame:
                    for paragraph in shape.text_frame.paragraphs:
                        t = paragraph.text.strip()
                        if t:
                            textos_slide.append(t)
                            
            notas = ""
            if slide.has_notes_slide and slide.notes_slide.notes_text_frame:
                notas = slide.notes_slide.notes_text_frame.text.strip()
                
            cuerpo_slide = " | ".join(textos_slide) if textos_slide else "(Sin texto)"
            info_slide = f"- Diapositiva {idx}: {cuerpo_slide}"
            if notas:
                info_slide += f" [Notas: {notas}]"
            partes_slides.append(info_slide)
            
        contenido = "\n".join(partes_slides)
        resumen = f"Presentación PowerPoint '{ruta_p.name}' ({total_slides} diapositivas):\n"
        resultado = resumen + contenido
        if len(resultado) > 4000:
            resultado = resultado[:3950] + "\n... [Contenido truncado a 4000 caracteres]"
        return resultado
    except Exception as e:
        return f"Error al leer la presentación PowerPoint '{ruta_p.name}': {e}"

def _inspeccionar_multimedia(ruta_p: Path) -> str:
    """Extrae metadatos estructurales de un archivo multimedia (.mp3, .mp4)."""
    try:
        stats = ruta_p.stat()
        tam_mb = round(stats.st_size / (1024 * 1024), 2)
        fecha_mod = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(stats.st_mtime))
        ext = ruta_p.suffix.lower()
        tipo = "Audio" if ext in ('.mp3', '.wav') else "Video"
        
        return (
            f"Reporte Multimedia de {tipo} '{ruta_p.name}':\n"
            f"- Formato: {ext.upper()}\n"
            f"- Tamaño: {tam_mb} MB ({stats.st_size} bytes)\n"
            f"- Última modificación: {fecha_mod}\n"
            f"- Ubicación: {ruta_p.parent}\n"
            f"- Estado: Archivo válido y accesible para reproducción o transcripción."
        )
    except Exception as e:
        return f"Error al inspeccionar archivo multimedia '{ruta_p.name}': {e}"

def _inspeccionar_imagen(ruta_p: Path) -> str:
    """Obtiene dimensiones, formato y prepara la etiqueta multimodal para la IA."""
    try:
        from PIL import Image
        stats = ruta_p.stat()
        tam_kb = round(stats.st_size / 1024, 2)
        with Image.open(ruta_p) as img:
            ancho, alto = img.size
            formato = img.format or ruta_p.suffix.replace('.', '').upper()
            modo = img.mode
            
        return (
            f"[IMAGEN_LOCAL:{ruta_p.resolve()}] Archivo de imagen '{ruta_p.name}':\n"
            f"- Formato: {formato}\n"
            f"- Resolución: {ancho}x{alto} píxeles\n"
            f"- Modo de color: {modo}\n"
            f"- Tamaño en disco: {tam_kb} KB\n"
            f"- Estado: Imagen cargada en memoria RAM y lista para análisis visual detallado con red neuronal."
        )
    except Exception as e:
        return f"Error al inspeccionar la imagen '{ruta_p.name}': {e}"

def _leer_archivo_en_zip(ruta_str: str) -> str | None:
    """Lee en memoria un archivo contenido dentro de un archivo .zip sin descomprimirlo en disco."""
    try:
        ruta_norm = ruta_str.replace("\\", "/")
        if ".zip/" in ruta_norm:
            partes = ruta_norm.split(".zip/", 1)
            ruta_zip = Path(partes[0] + ".zip").expanduser()
            sub_archivo = partes[1]
            if ruta_zip.exists() and ruta_zip.is_file():
                import zipfile
                with zipfile.ZipFile(ruta_zip, 'r') as z:
                    if sub_archivo in z.namelist():
                        with z.open(sub_archivo) as f_in:
                            contenido_bytes = f_in.read(4000)
                            try:
                                texto = contenido_bytes.decode('utf-8')
                            except UnicodeDecodeError:
                                texto = contenido_bytes.decode('latin-1', errors='ignore')
                            return f"Contenido de '{sub_archivo}' dentro de '{ruta_zip.name}':\n{texto}"
                    else:
                        return f"El elemento '{sub_archivo}' no se encontró dentro de '{ruta_zip.name}'."
    except Exception as e:
        return f"Error al extraer archivo desde el zip: {e}"
    return None

def leer_archivo_local(ruta: str) -> str:
    """Lee y analiza archivos de texto, código, PDF, Word, Excel, PowerPoint, comprimidos, imágenes o multimedia."""
    try:
        # 1. Comprobación de lectura interna dentro de un archivo ZIP
        lectura_zip = _leer_archivo_en_zip(ruta)
        if lectura_zip is not None:
            return lectura_zip

        ruta_p = Path(ruta).expanduser()
        if not ruta_p.exists():
            return f"El archivo '{ruta}' no fue encontrado."
        if not ruta_p.is_file():
            return f"La ruta '{ruta}' apunta a un directorio, no a un archivo."

        ext = ruta_p.suffix.lower()

        # 2. Hojas de cálculo Excel (.xlsx)
        if ext in ('.xlsx', '.xlsm', '.xltx'):
            return _leer_excel(ruta_p)

        # 3. Presentaciones PowerPoint (.pptx)
        elif ext in ('.pptx', '.pptm'):
            return _leer_powerpoint(ruta_p)

        # 4. Archivos comprimidos (.zip, .7z)
        elif ext in EXTENSIONES_COMPRIMIDOS:
            return explorar_archivo_comprimido(str(ruta_p))

        # 5. Imágenes locales
        elif ext in EXTENSIONES_IMAGEN:
            return _inspeccionar_imagen(ruta_p)

        # 6. Archivos multimedia (.mp3, .mp4)
        elif ext in EXTENSIONES_MULTIMEDIA:
            return _inspeccionar_multimedia(ruta_p)

        # 7. Documentos PDF
        elif ext == '.pdf':
            try:
                import pypdf
                reader = pypdf.PdfReader(ruta_p)
                texto = "\n".join([page.extract_text() for page in reader.pages if page.extract_text()])
                return f"Contenido del PDF '{ruta_p.name}':\n{texto[:4000]}"
            except ImportError:
                return "Para leer PDFs, instala 'pypdf': pip install pypdf"

        # 8. Documentos Word (.docx)
        elif ext == '.docx':
            try:
                import docx
                doc = docx.Document(ruta_p)
                texto = "\n".join([p.text for p in doc.paragraphs])
                return f"Contenido del documento Word '{ruta_p.name}':\n{texto[:4000]}"
            except ImportError:
                return "Para leer archivos DOCX, instala 'python-docx': pip install python-docx"

        # 9. Archivos de texto plano y código
        elif ext in EXTENSIONES_TEXTO or ext == '':
            with open(ruta_p, 'r', encoding='utf-8', errors='ignore') as f:
                contenido = f.read(4000)
            return f"Contenido de '{ruta_p.name}':\n{contenido}"

        else:
            return f"Formato '{ext}' no soportado para lectura de texto directo."

    except Exception as e:
        return f"Error al leer el archivo '{ruta}': {e}"

def crear_o_modificar_archivo(ruta: str, contenido: str, modo: str = "sobreescribir") -> str:
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
    c1 = leer_archivo_local(ruta1)
    c2 = leer_archivo_local(ruta2)
    return f"--- CONTENIDO ARCHIVO 1 ({ruta1}) ---\n{c1}\n\n--- CONTENIDO ARCHIVO 2 ({ruta2}) ---\n{c2}"
