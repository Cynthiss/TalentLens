"""Pipeline de TalentLens: lectura, limpieza y extracción de información de CVs.

Son las mismas funciones del notebook, adaptadas para recibir archivos subidos
(bytes) en lugar de rutas.
"""
import io
import re
import unicodedata
from datetime import date
from pathlib import Path

import docx
import pymupdf
import pytesseract
import spacy
from PIL import Image

CARPETA = Path(__file__).parent


# ---------- 1. Captura ----------

def leer_pdf(datos):
    """Texto de un PDF; si una página no tiene texto, se lee con OCR."""
    paginas = []
    with pymupdf.open(stream=datos, filetype='pdf') as pdf:
        for pagina in pdf:
            texto = pagina.get_text()
            if len(texto.strip()) < 20:
                pix = pagina.get_pixmap(dpi=300)
                img = Image.frombytes('RGB', (pix.width, pix.height), pix.samples)
                texto = pytesseract.image_to_string(img, lang='spa', config='--psm 4')
            paginas.append(texto)
    return '\n'.join(paginas)


def leer_docx(datos):
    """Texto de un Word en orden, incluyendo tablas."""
    doc = docx.Document(io.BytesIO(datos))
    lineas = []
    for bloque in doc.iter_inner_content():
        if isinstance(bloque, docx.table.Table):
            for fila in bloque.rows:
                celdas = []
                for celda in fila.cells:
                    if celda.text not in celdas:  # celdas combinadas se repiten
                        celdas.append(celda.text)
                lineas.append('\n'.join(celdas))
        else:
            lineas.append(bloque.text)
    return '\n'.join(lineas)


def leer_cv(datos, nombre_archivo):
    extension = Path(nombre_archivo).suffix.lower()
    if extension == '.pdf':
        return leer_pdf(datos)
    if extension == '.docx':
        return leer_docx(datos)
    raise ValueError(f'Formato no soportado: {extension}')


# ---------- 2. Limpieza ----------

VINETAS = '•·«»*▪●■◦–—-'
DOMINIOS = r'(gmail|yahoo|outlook|hotmail)\.com'


def limpiar_texto(texto):
    texto = unicodedata.normalize('NFC', texto)
    texto = texto.replace('\xa0', ' ').replace('\t', ' ')
    # correos partidos en dos líneas (columnas angostas): "outlook.\ncom"
    texto = re.sub(r'(\S+@\S+)\n([a-z.]{1,4})$', r'\1\2', texto, flags=re.M)
    # OCR: la @ se lee como "0", "QW" o "GW" -> pedro.xicara890gmail.com
    texto = re.sub(r'\b([a-z][\w.]*?)[0OQGW]{1,2}' + DOMINIOS, r'\1@\2.com', texto)
    lineas = []
    for linea in texto.split('\n'):
        linea = linea.strip().lstrip(VINETAS).strip()  # viñetas al inicio
        linea = re.sub(r'\s*[–—]\s*', ' - ', linea)      # guiones largos
        linea = re.sub(r' {2,}', ' ', linea)
        if linea:
            lineas.append(linea)
    return '\n'.join(lineas)


SECCIONES = {
    'contacto': ['contacto', 'datos personales', 'informacion de contacto'],
    'perfil': ['perfil', 'perfil profesional', 'sobre mi', 'resumen', 'objetivo', 'acerca de mi', 'profile'],
    'experiencia': ['experiencia', 'experiencia laboral', 'experiencia profesional', 'trayectoria',
                    'trayectoria profesional', 'historial laboral', 'experience'],
    'educacion': ['educacion', 'formacion', 'formacion academica', 'preparacion academica', 'estudios', 'education'],
    'habilidades': ['habilidades', 'competencias', 'skills', 'aptitudes', 'conocimientos',
                    'conocimientos tecnicos', 'herramientas y conocimientos'],
    'idiomas': ['idiomas', 'lenguas', 'languages'],
    'cursos': ['cursos', 'certificaciones', 'cursos y certificaciones'],
    'referencias': ['referencias'],
    'otros': ['informacion adicional'],
}
ENCABEZADOS = {frase: sec for sec, frases in SECCIONES.items() for frase in frases}
# segunda palabra de un encabezado partido en dos líneas (tablas): "EXPERIENCIA\nPROFESIONAL"
CONTINUACION = {'profesional', 'laboral', 'academica', 'tecnicos'}


def sin_acentos(s):
    s = unicodedata.normalize('NFD', s.lower())
    return ''.join(ch for ch in s if unicodedata.category(ch) != 'Mn')


def detectar_encabezado(linea):
    """Devuelve (sección, resto de la línea) o (None, línea)."""
    clave = sin_acentos(linea).strip(' :')
    if clave in ENCABEZADOS:
        return ENCABEZADOS[clave], ''
    # OCR de tablas: encabezado en mayúsculas pegado al contenido, "PERFIL Coordinador ..."
    palabras = linea.split()
    for n in (2, 1):
        inicio = ' '.join(palabras[:n])
        if inicio.isupper() and sin_acentos(inicio) in ENCABEZADOS and len(palabras) > n:
            return ENCABEZADOS[sin_acentos(inicio)], ' '.join(palabras[n:])
    return None, linea


def separar_secciones(texto):
    secciones = {'encabezado': []}
    actual = 'encabezado'
    anterior_fue_encabezado = False
    for linea in texto.split('\n'):
        primera = sin_acentos(linea.split()[0])
        if anterior_fue_encabezado and primera in CONTINUACION and linea.split()[0].isupper():
            linea = ' '.join(linea.split()[1:])
            if not linea:
                continue
        seccion, resto = detectar_encabezado(linea)
        anterior_fue_encabezado = seccion is not None
        if seccion:
            actual = seccion
            secciones.setdefault(actual, [])
            linea = resto
        if linea:
            secciones[actual].append(linea)
    return {sec: '\n'.join(lineas) for sec, lineas in secciones.items()}


# ---------- 3. Extracción ----------

RE_EMAIL = re.compile(r'[\w.+-]+@[\w-]+\.[\w.]+')
RE_TELEFONO = re.compile(r'(?:\+502\s?)?\d{4}[-\s]?\d{4}')
CONECTORES = {'de', 'del', 'la', 'los', 'las', 'y'}


def cargar_modelos():
    """NER preentrenado (para el nombre) y NER ajustado (empresas, educación, habilidades)."""
    return spacy.load('es_core_news_sm'), spacy.load(CARPETA / 'modelo_ner')


def extraer_email(texto):
    m = RE_EMAIL.search(texto)
    return m.group().rstrip('.') if m else None


def extraer_telefono(texto):
    m = RE_TELEFONO.search(texto)
    return m.group() if m else None


def parece_nombre(linea):
    palabras = linea.split()
    if not 2 <= len(palabras) <= 6 or any(ch.isdigit() for ch in linea):
        return False
    if detectar_encabezado(linea)[0]:
        return False
    return all(p[0].isupper() or p.lower() in CONECTORES for p in palabras)


def extraer_nombre(secciones, nlp):
    """Nombre del candidato: línea con forma de nombre que el NER marca como persona."""
    candidatos = []
    posicion = 0
    for seccion, texto in secciones.items():
        if seccion in ('referencias', 'experiencia', 'educacion', 'cursos'):
            continue  # aquí aparecen otras personas, empresas o títulos
        for linea in texto.split('\n'):
            posicion += 1
            if not parece_nombre(linea):
                continue
            doc = nlp(linea.title() if linea.isupper() else linea)
            es_persona = any(e.label_ == 'PER' and len(e.text) >= 0.8 * len(doc.text) for e in doc.ents)
            puntaje = 2 * es_persona + (len(linea.split()) >= 3) - 0.1 * posicion
            candidatos.append((puntaje, linea))
    if not candidatos:
        return None
    nombre = max(candidatos)[1]
    return nombre.title() if nombre.isupper() else nombre


MESES = {'ene': 1, 'feb': 2, 'mar': 3, 'abr': 4, 'may': 5, 'jun': 6,
         'jul': 7, 'ago': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dic': 12}
ACTUAL = r'(?:actualidad|a la fecha|presente|actual)'
# "mar 2021", "Marzo de 2021", "03/2021" o solo "2021"
FECHA = r'(?:[a-záéíóú]+(?: de)? \d{4}|\d{1,2}/\d{4}|\d{4})'
RE_RANGO = re.compile(rf'({FECHA})\s*-\s*({FECHA}|{ACTUAL})')


def leer_fecha(texto, referencia):
    """Convierte una fecha a (año, mes). Si solo hay año, se usa mitad de año (julio)."""
    texto = texto.lower().strip()
    if re.fullmatch(ACTUAL, texto):
        return referencia
    if m := re.fullmatch(r'(\d{1,2})/(\d{4})', texto):
        return int(m[2]), int(m[1])
    if m := re.fullmatch(r'([a-záéíóú]+)(?: de)? (\d{4})', texto):
        return int(m[2]), MESES.get(m[1][:3], 7)
    return int(texto), 7


def anios_experiencia(secciones, referencia=None):
    """Suma los periodos de la sección de experiencia sin contar dos veces los traslapes.

    `referencia` es (año, mes) para "actualidad"; por defecto, el mes actual.
    """
    referencia = referencia or (date.today().year, date.today().month)
    periodos = []
    for inicio, fin in RE_RANGO.findall(secciones.get('experiencia', '').lower()):
        a, b = leer_fecha(inicio, referencia), min(leer_fecha(fin, referencia), referencia)
        if a < b:
            periodos.append((a[0] * 12 + a[1], b[0] * 12 + b[1]))
    meses, fin_anterior = 0, 0
    for inicio, fin in sorted(periodos):
        inicio = max(inicio, fin_anterior)
        if fin > inicio:
            meses += fin - inicio
            fin_anterior = fin
    return round(meses / 12, 1)


def extraer_entidades(texto, ner_cv):
    """Listas de EMPRESA, TITULO, INSTITUCION y HABILIDAD sin repetidos."""
    campos = {'EMPRESA': [], 'TITULO': [], 'INSTITUCION': [], 'HABILIDAD': []}
    for e in ner_cv(texto).ents:
        valor = ' '.join(e.text.split())  # une saltos de línea
        if valor.lower() not in [v.lower() for v in campos[e.label_]]:
            campos[e.label_].append(valor)
    return campos


def procesar_cv(datos, nombre_archivo, nlp, ner_cv):
    """Pipeline completo para un CV: devuelve un diccionario con los campos extraídos."""
    texto = limpiar_texto(leer_cv(datos, nombre_archivo))
    secciones = separar_secciones(texto)
    entidades = extraer_entidades(texto, ner_cv)
    return {
        'archivo': nombre_archivo,
        'nombre': extraer_nombre(secciones, nlp),
        'email': extraer_email(texto),
        'telefono': extraer_telefono(texto),
        'anios_experiencia': anios_experiencia(secciones),
        'empresas': entidades['EMPRESA'],
        'titulos': entidades['TITULO'],
        'instituciones': entidades['INSTITUCION'],
        'habilidades': entidades['HABILIDAD'],
        'texto': texto,
    }
