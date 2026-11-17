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

def texto_linea(linea):
    """Texto de una línea del PDF. Si las letras vienen espaciadas ("B A C H I L L E R E N"),
    las une y separa las palabras donde el espacio entre letras es mayor."""
    letras = [c for s in linea['spans'] for c in s['chars']]
    texto = ''.join(c['c'] for c in letras)
    fichas = texto.split()
    if len(fichas) < 4 or sum(len(f) == 1 for f in fichas) < 0.8 * len(fichas):
        return texto
    visibles = [c for c in letras if not c['c'].isspace()]
    huecos = [b['bbox'][0] - a['bbox'][2] for a, b in zip(visibles, visibles[1:])]
    normal = sorted(huecos)[len(huecos) // 2]
    palabras = visibles[0]['c']
    for hueco, c in zip(huecos, visibles[1:]):
        palabras += (' ' if hueco > 1.6 * normal + 1 else '') + c['c']
    return palabras


def ordenar_bloques(bloques, profundidad=0):
    """Orden de lectura de los bloques (x0, y0, x1, y1, texto) de una página: corte XY recursivo.

    Los CVs hechos con plantillas (Canva, por ejemplo) guardan los bloques en el orden en que
    se dibujaron, no en el que se leen. Se corta la región por su franja en blanco más ancha:
    un corte vertical separa columnas (se leen de izquierda a derecha) y uno horizontal separa
    filas (de arriba a abajo).
    """
    def por_posicion(grupo):
        return sorted(grupo, key=lambda b: (b[1], b[0]))

    if len(bloques) <= 1 or profundidad > 30:
        return por_posicion(bloques)

    def huecos(eje):
        intervalos = sorted((b[eje], b[eje + 2]) for b in bloques)
        resultado, alcance = [], intervalos[0][1]
        for inicio, fin in intervalos[1:]:
            if inicio > alcance:
                resultado.append((alcance, inicio))
            alcance = max(alcance, fin)
        return resultado

    verticales, horizontales = huecos(0), huecos(1)
    ancho_v = max((b - a for a, b in verticales), default=0)
    ancho_h = max((b - a for a, b in horizontales), default=0)
    if ancho_v >= 8 and ancho_v >= ancho_h:
        cortes, eje = verticales, 0
    elif horizontales:
        cortes, eje = horizontales, 1
    else:
        return por_posicion(bloques)

    limites = [inicio for inicio, _ in cortes] + [float('inf')]
    grupos = [[] for _ in limites]
    for b in bloques:
        grupos[next(i for i, limite in enumerate(limites) if b[eje] < limite)].append(b)
    return [b for g in grupos if g for b in ordenar_bloques(g, profundidad + 1)]


def texto_pagina(pagina):
    """Texto de una página en orden de lectura."""
    lineas = []
    for bloque in pagina.get_text('rawdict')['blocks']:
        for linea in bloque.get('lines', []):  # los bloques de imagen no tienen líneas
            texto = texto_linea(linea)
            if texto.strip():
                lineas.append((*linea['bbox'], texto))
    return '\n'.join(l[4] for l in ordenar_bloques(lineas))


def leer_pdf(datos):
    """Texto de un PDF; si una página no tiene texto, se lee con OCR."""
    paginas = []
    with pymupdf.open(stream=datos, filetype='pdf') as pdf:
        for pagina in pdf:
            texto = texto_pagina(pagina)
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
    # NFKC además separa ligaduras tipográficas de los PDF: "ﬁ" -> "fi", "ﬂ" -> "fl"
    texto = unicodedata.normalize('NFKC', texto)
    texto = texto.replace('\xa0', ' ').replace('\t', ' ')
    # correos partidos en dos líneas (columnas angostas): "outlook.\ncom"
    texto = re.sub(r'(\S+@\S+)\n([a-z.]{1,4})$', r'\1\2', texto, flags=re.M)
    # OCR: la @ se lee como "0", "QW", "GW" o un espacio -> pedro.xicara890gmail.com, maria.morales300 gmail.com
    texto = re.sub(r'\b([a-z][\w.]*?)(?:[0OQGW]{1,2} ?| )' + DOMINIOS, r'\1@\2.com', texto)
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
    'educacion': ['educacion', 'formacion', 'formacion academica', 'preparacion academica', 'estudios', 'education',
                  'datos academicos'],
    'habilidades': ['habilidades', 'competencias', 'skills', 'aptitudes', 'conocimientos',
                    'conocimientos tecnicos', 'herramientas y conocimientos'],
    'idiomas': ['idiomas', 'lenguas', 'languages'],
    'cursos': ['cursos', 'certificaciones', 'cursos y certificaciones', 'certificaciones y cursos', 'certificados',
               'diplomas', 'diplomados'],
    'referencias': ['referencias'],
    # no cuentan para los años de experiencia: voluntariados, eventos, viajes...
    'otros': ['informacion adicional', 'otros conocimientos', 'experiencia adicional', 'experiencias internacionales',
              'voluntariado', 'logros', 'premios'],
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


def unir_encabezados_partidos(lineas):
    """Une encabezados partidos en dos líneas que solo se reconocen juntos: "PREPARACIÓN\\nACADÉMICA"."""
    unidas, i = [], 0
    while i < len(lineas):
        linea = lineas[i]
        if i + 1 < len(lineas) and not detectar_encabezado(linea)[0]:
            juntas = f'{linea} {lineas[i + 1]}'
            if sin_acentos(juntas).strip(' :') in ENCABEZADOS:
                linea, i = juntas, i + 1
        unidas.append(linea)
        i += 1
    return unidas


def separar_secciones(texto):
    secciones = {'encabezado': []}
    actual = 'encabezado'
    anterior_fue_encabezado = False
    for linea in unir_encabezados_partidos(texto.split('\n')):
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
# 5632-6945, 5632 6945, 56326945 y también con espacios alrededor del guion: 4891 - 1973
RE_TELEFONO = re.compile(r'(?<!\d)(?:\+502\s?)?\d{4}(?:\s?-\s?|\s)?\d{4}(?!\d)')
RE_ANIO = re.compile(r'(19|20)\d\d')
CONECTORES = {'de', 'del', 'la', 'los', 'las', 'y'}


def cargar_modelos():
    """NER preentrenado (para el nombre) y NER ajustado (empresas, educación, habilidades)."""
    return spacy.load('es_core_news_sm'), spacy.load(CARPETA / 'modelo_ner')


def extraer_email(texto):
    m = RE_EMAIL.search(texto)
    return m.group().rstrip('.') if m else None


def extraer_telefono(texto):
    for m in RE_TELEFONO.finditer(texto):
        mitades = re.findall(r'\d{4}', m.group().removeprefix('+502'))
        if not all(RE_ANIO.fullmatch(d) for d in mitades):  # "2025 - 2026" es un rango de fechas
            return m.group()
    return None


def parece_nombre(linea):
    palabras = linea.split()
    if not 2 <= len(palabras) <= 6 or any(ch.isdigit() or ch in ',;|/:()@·' for ch in linea):
        return False  # listas como "Meta Ads, SEO, HubSpot" no son nombres
    if detectar_encabezado(linea)[0]:
        return False
    return all(p[0].isupper() or p.lower() in CONECTORES for p in palabras)


def extraer_nombre(secciones, nlp):
    """Nombre del candidato: línea con forma de nombre que el NER marca como persona."""
    candidatos = []
    posicion = 0
    todo = '\n'.join(secciones.values()).lower()
    for seccion, texto in secciones.items():
        if seccion in ('referencias', 'experiencia', 'educacion', 'cursos'):
            continue  # aquí aparecen otras personas, empresas o títulos
        lineas = texto.split('\n')
        for i, linea in enumerate(lineas):
            posicion += 1
            if not parece_nombre(linea):
                continue
            # nombre partido en dos líneas: "VANESSA VILLATORO\nMONROY", "Cynthia Michelle\nSantos Letona"
            # (solo si la segunda línea no aparece en otra parte del CV, como pasaría con un puesto: "DOCENTE")
            siguiente = lineas[i + 1] if i + 1 < len(lineas) else ''
            if siguiente and linea.isupper() == siguiente.isupper() and todo.count(siguiente.lower()) == 1 and \
                    len(linea.split()) + len(siguiente.split()) <= 5 and not detectar_encabezado(siguiente)[0] and \
                    (siguiente.isalpha() or parece_nombre(siguiente)):
                linea = f'{linea} {siguiente}'
            doc = nlp(linea.title() if linea.isupper() else linea)
            es_persona = any(e.label_ == 'PER' and len(e.text) >= 0.8 * len(doc.text) for e in doc.ents)
            # un puesto suele repetirse en el perfil o la experiencia; el nombre aparece una sola vez
            se_repite = todo.count(linea.lower()) > 1
            en_habilidades = seccion == 'habilidades'  # dos habilidades en líneas seguidas: "After Effects\nPhotoshop"
            puntaje = 2 * es_persona + (len(linea.split()) >= 3) - 2 * se_repite - 2 * en_habilidades - 0.1 * posicion
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


RE_NO_EMPRESA = re.compile(r'^(certificad[oa]|certificaci[oó]n|curso|diplomado|idioma)\b', re.I)


def es_ruido(valor, etiqueta, nombre):
    """Entidades que el NER marca por error en CVs reales."""
    if len(valor) < 3 and not valor.isupper():
        return True  # restos de íconos: "In" (LinkedIn)
    if re.search(r'[/@]|\.com\b|\+\d', valor):
        return True  # enlaces, correos y teléfonos: "Linkedin.com/in/..."
    if nombre and set(valor.lower().split()) <= set(nombre.lower().split()):
        return True  # parte del nombre del candidato: "Santos Letona"
    return etiqueta in ('EMPRESA', 'HABILIDAD') and RE_NO_EMPRESA.match(valor) is not None


def extraer_entidades(texto, ner_cv, nombre=None):
    """Listas de EMPRESA, TITULO, INSTITUCION y HABILIDAD sin repetidos."""
    campos = {'EMPRESA': [], 'TITULO': [], 'INSTITUCION': [], 'HABILIDAD': []}
    vistos = set()
    for e in ner_cv(texto_para_ner(texto)).ents:
        valor = ' '.join(e.text.split())  # une saltos de línea
        clave = (e.label_, sin_acentos(valor))  # "Marroquin" y "MARROQUÍN" son la misma
        if es_ruido(valor, e.label_, nombre) or clave in vistos:
            continue
        vistos.add(clave)
        campos[e.label_].append(valor)
    return campos


MINUSCULAS = {'de', 'del', 'en', 'con', 'y', 'e', 'la', 'las', 'el', 'los', 'a', 'por', 'para'}


def texto_para_ner(texto):
    """Las líneas en MAYÚSCULAS pasan a formato título ("BACHILLERATO EN CIENCIAS" -> "Bachillerato en
    Ciencias"): el NER se entrenó sobre todo con texto en formato título y no reconoce las mayúsculas.
    Las siglas cortas (UFM, SQL) se quedan igual. El texto conserva su largo, así que las posiciones no cambian."""
    lineas = []
    for linea in texto.split('\n'):
        if linea.isupper() and len(linea.split()) >= 2:
            linea = ' '.join(p.lower() if p.lower() in MINUSCULAS else p if len(p) <= 3 else p.title()
                             for p in linea.split(' '))
        lineas.append(linea)
    return '\n'.join(lineas)


def procesar_cv(datos, nombre_archivo, nlp, ner_cv):
    """Pipeline completo para un CV: devuelve un diccionario con los campos extraídos."""
    texto = limpiar_texto(leer_cv(datos, nombre_archivo))
    secciones = separar_secciones(texto)
    nombre = extraer_nombre(secciones, nlp)
    entidades = extraer_entidades(texto, ner_cv, nombre)
    return {
        'archivo': nombre_archivo,
        'nombre': nombre,
        'email': extraer_email(texto),
        'telefono': extraer_telefono(texto),
        'anios_experiencia': anios_experiencia(secciones),
        'empresas': entidades['EMPRESA'],
        'titulos': entidades['TITULO'],
        'instituciones': entidades['INSTITUCION'],
        'habilidades': entidades['HABILIDAD'],
        'texto': texto,
    }
