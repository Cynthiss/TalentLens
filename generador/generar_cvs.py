"""Genera CVs sintéticos en español (PDF, Word y escaneados) con su respuesta correcta.

Uso (desde la raíz del repo):
    .venv/bin/python generador/generar_cvs.py --entrenamiento 160 --prueba 40

Crea la carpeta CVs_sinteticos/ con pdf/, word/ y etiquetas_ground_truth.csv,
con las mismas columnas que el CSV de los CVs originales más la columna `conjunto`.
Los CVs de prueba usan empresas, instituciones, títulos y habilidades que no
aparecen en ningún CV de entrenamiento.
"""
import argparse
import csv
import html
import io
import random
import unicodedata
from pathlib import Path

import docx
import pymupdf
from docx.shared import Pt, RGBColor
from PIL import Image, ImageFilter

import vocabulario as voc

RAIZ = Path(__file__).resolve().parent.parent
FECHA_REFERENCIA = (2026, 9)  # igual que los CVs originales
MESES_CORTOS = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic']
MESES_LARGOS = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Septiembre',
                'Octubre', 'Noviembre', 'Diciembre']
PALABRAS_ACTUAL = ['actualidad', 'a la fecha', 'presente', 'actual']

FORMATOS = {  # formato: (peso, tipo de archivo)
    'clasico': (24, 'pdf'), 'dos_columnas': (18, 'pdf'), 'tabla': (12, 'pdf'), 'creativo': (12, 'pdf'),
    'varias_paginas': (6, 'pdf'), 'escaneado': (8, 'pdf'),
    'word_sencillo': (8, 'docx'), 'word_tablas': (6, 'docx'), 'word_prosa': (6, 'docx'),
}


# ---------- Datos de la persona ----------

def sin_acentos(texto):
    texto = unicodedata.normalize('NFD', texto)
    return ''.join(c for c in texto if unicodedata.category(c) != 'Mn')


def construir_grupos():
    """Valores de entrenamiento y de prueba, comprobando que los de prueba sean nuevos."""
    grupos = {'entrenamiento': {}, 'prueba': {}}
    for conjunto in grupos:
        g = grupos[conjunto]
        g['apellidos'] = voc.APELLIDOS[conjunto]
        g['empresas'] = voc.NOMBRES_EMPRESA[conjunto]
        g['universidades'] = voc.UNIVERSIDADES[conjunto]
        g['colegios'] = voc.COLEGIOS[conjunto]
        g['titulos'] = {p: d['titulos'][conjunto] for p, d in voc.PROFESIONES.items()}
        g['posgrados'] = {p: d['posgrados'][:1] if conjunto == 'entrenamiento' else d['posgrados'][1:]
                          for p, d in voc.PROFESIONES.items()}
        g['habilidades'] = {p: d['habilidades'][conjunto] for p, d in voc.PROFESIONES.items()}

    # lo que es "nuevo" en prueba = lo que nunca aparece en entrenamiento
    def todos(conjunto, clave):
        valor = grupos[conjunto][clave]
        return {v for vs in valor.values() for v in vs} if isinstance(valor, dict) else set(valor)

    for clave in ['empresas', 'universidades', 'colegios', 'titulos', 'habilidades']:
        repetidos = todos('prueba', clave) & todos('entrenamiento', clave)
        assert not repetidos, f'{clave} de prueba repetidos en entrenamiento: {repetidos}'
    nuevos_posgrados = todos('prueba', 'posgrados') - todos('entrenamiento', 'posgrados')
    grupos['prueba']['posgrados'] = {p: [t for t in ts if t in nuevos_posgrados]
                                     for p, ts in grupos['prueba']['posgrados'].items()}
    return grupos


def mes_a_numero(anio, mes):
    return anio * 12 + mes - 1


def numero_a_mes(n):
    return n // 12, n % 12 + 1


def crear_persona(rng, conjunto, grupos):
    g = grupos[conjunto]
    profesion = rng.choice(list(voc.PROFESIONES))
    datos = voc.PROFESIONES[profesion]
    mujer = rng.random() < 0.5
    nombre = rng.choice(voc.NOMBRES_MUJER if mujer else voc.NOMBRES_HOMBRE)
    apellidos = rng.sample(g['apellidos'], 2)
    nombre_completo = f'{nombre} {apellidos[0]} {apellidos[1]}'

    usuario = sin_acentos(f"{nombre.split()[0]}.{apellidos[0]}").lower().replace(' ', '')
    email = f"{usuario}{rng.randint(10, 99)}@{rng.choice(voc.DOMINIOS_CORREO)}"
    numero = f"{rng.choice([3, 4, 5])}{rng.randint(0, 999):03d}-{rng.randint(0, 9999):04d}"
    telefono = rng.choice([f'+502 {numero}', f'+502 {numero}', f'+502 {numero.replace("-", " ")}', numero])

    # Experiencia: de la más reciente a la más antigua
    n_trabajos = rng.choice([1, 2, 2, 3, 3, 4])
    fin = mes_a_numero(*FECHA_REFERENCIA) if rng.random() < 0.7 else \
        mes_a_numero(*FECHA_REFERENCIA) - rng.randint(1, 10)
    actual = fin == mes_a_numero(*FECHA_REFERENCIA)
    nombres_empresa = rng.sample(g['empresas'], n_trabajos)
    nivel = min(len(datos['puestos']) - 1, n_trabajos + rng.randint(-1, 1))
    trabajos = []
    for i in range(n_trabajos):
        duracion = rng.randint(8, 48)
        inicio = fin - duracion
        empresa = f"{rng.choice(voc.TIPOS_EMPRESA)} {nombres_empresa[i]}{rng.choice(voc.SUFIJOS_EMPRESA)}"
        trabajos.append({
            'puesto': datos['puestos'][max(0, nivel - i)], 'empresa': empresa,
            'ciudad': rng.choice(voc.CIUDADES), 'inicio': inicio, 'fin': fin,
            'actual': actual and i == 0, 'tareas': rng.sample(datos['tareas'], 2),
        })
        fin = inicio - rng.randint(1, 6)  # pausa entre trabajos
    meses = sum(t['fin'] - t['inicio'] for t in trabajos)  # no se traslapan

    # Educación: universidad, a veces posgrado, y colegio
    egreso = numero_a_mes(trabajos[-1]['inicio'])[0] - rng.randint(0, 1)
    educacion = []
    posgrados = g['posgrados'][profesion]
    if posgrados and rng.random() < 0.35:
        educacion.append({'titulo': rng.choice(posgrados), 'institucion': rng.choice(g['universidades']),
                          'inicio': min(egreso + 3, 2024), 'fin': min(egreso + 5, 2026)})
    educacion.append({'titulo': rng.choice(g['titulos'][profesion]), 'institucion': rng.choice(g['universidades']),
                      'inicio': egreso - 5, 'fin': egreso})
    educacion.append({'titulo': rng.choice(voc.TITULOS_COLEGIO), 'institucion': rng.choice(g['colegios']),
                      'inicio': egreso - 7, 'fin': egreso - 5})

    # Habilidades: en prueba al menos 3 nuevas, el resto conocidas
    if conjunto == 'prueba':
        nuevas = g['habilidades'][profesion]
        conocidas = grupos['entrenamiento']['habilidades'][profesion]
        habilidades = rng.sample(nuevas, min(3, len(nuevas))) + rng.sample(conocidas, rng.randint(1, 2))
    else:
        disponibles = g['habilidades'][profesion]
        habilidades = rng.sample(disponibles, min(rng.randint(4, 7), len(disponibles)))
    rng.shuffle(habilidades)

    idiomas = ['Español (nativo)'] + [f'{i} ({rng.choice(voc.NIVELES)})'
                                      for i in rng.sample(voc.IDIOMAS, rng.randint(1, 2))]
    return {
        'nombre': nombre_completo, 'mujer': mujer, 'email': email if rng.random() > 0.05 else '',
        'telefono': telefono, 'ciudad': rng.choice(voc.CIUDADES), 'profesion': profesion,
        'titulo_perfil': datos['perfil'], 'anios_redondeados': meses // 12,
        'trabajos': trabajos, 'educacion': educacion, 'habilidades': habilidades, 'idiomas': idiomas,
        'anios_experiencia': round(meses / 12, 1),
        'formato_fechas': rng.choice(['corto', 'num', 'largo', 'anio']),
        'palabra_actual': rng.choice(PALABRAS_ACTUAL),
        'educacion_primero': rng.random() < 0.15,
        'habilidades_en_perfil': rng.random() < 0.1,
        'guion': rng.choice([' - ', ' – ', ' — ']),
        'separador_habilidades': rng.choice([', ', ' / ', ' · ', ' | ', None]),  # None = lista
        'mayusculas_nombre': rng.random() < 0.4,
    }


# ---------- Texto común ----------

def fecha(p, n):
    anio, mes = numero_a_mes(n)
    formato = p['formato_fechas']
    if formato == 'corto':
        return f'{MESES_CORTOS[mes - 1]} {anio}'
    if formato == 'num':
        return f'{mes:02d}/{anio}'
    if formato == 'largo':
        return f'{MESES_LARGOS[mes - 1]} de {anio}'
    return str(anio)


def periodo(p, t):
    fin = p['palabra_actual'] if t['actual'] else fecha(p, t['fin'])
    return f"{fecha(p, t['inicio'])}{p['guion']}{fin}"


def perfil(p):
    anios = p['anios_redondeados']
    tiempo = 'menos de 1 año' if anios == 0 else '1 año' if anios == 1 else f'{anios} años'
    texto = (f"{p['titulo_perfil']} con {tiempo} de experiencia. "
             'Me interesa aportar en equipos que buscan resultados medibles y mejora continua.')
    if p['habilidades_en_perfil']:
        texto += f" Manejo {', '.join(p['habilidades'][:-1])} y {p['habilidades'][-1]}."
    return texto


def encabezado(rng, seccion, ingles=False):
    if ingles:
        return voc.ENCABEZADOS_INGLES[seccion]
    return rng.choice(voc.ENCABEZADOS[seccion])


def nombre_visible(p):
    return p['nombre'].upper() if p['mayusculas_nombre'] else p['nombre']


def orden_secciones(p):
    orden = ['perfil', 'experiencia', 'educacion', 'habilidades', 'idiomas']
    if p['educacion_primero']:
        orden = ['perfil', 'educacion', 'experiencia', 'habilidades', 'idiomas']
    if p['habilidades_en_perfil']:
        orden.remove('habilidades')
    return orden


# ---------- PDF (HTML con pymupdf.Story) ----------

CSS = """
* { font-family: sans-serif; font-size: 10.5px; color: #222; }
h1 { font-size: 22px; margin: 0 0 2px 0; }
h2 { font-size: 12.5px; margin: 12px 0 4px 0; color: #1c3d5a; }
p { margin: 0 0 4px 0; }
ul { margin: 0 0 6px 0; }
td { vertical-align: top; padding: 4px 8px; }
.sub { font-size: 12px; color: #555; }
.banner { background-color: #2d3e50; color: #ffffff; padding: 10px; }
.banner h1, .banner p { color: #ffffff; }
.etiqueta { font-weight: bold; color: #1c3d5a; width: 28%; }
"""


def e(texto):
    return html.escape(texto)


def html_experiencia(rng, p, mayusculas_fechas=False):
    estilo = rng.choice(['guion', 'coma', 'barra'])
    partes = []
    for t in p['trabajos']:
        fechas = periodo(p, t).upper() if mayusculas_fechas else periodo(p, t)
        if estilo == 'guion':
            partes.append(f"<p><b>{e(t['puesto'])}{e(p['guion'])}{e(t['empresa'])}</b><br/>{e(fechas)}</p>")
        elif estilo == 'coma':
            partes.append(f"<p><b>{e(t['puesto'])}, {e(t['empresa'])}{e(p['guion'])}{e(t['ciudad'])}</b>"
                          f"<br/>{e(fechas)}</p>")
        else:
            partes.append(f"<p><b>{e(t['puesto'])}</b><br/>{e(t['empresa'])} | {e(fechas)}</p>")
        partes.append('<ul>' + ''.join(f'<li>{e(x)}</li>' for x in t['tareas']) + '</ul>')
    return ''.join(partes)


def html_educacion(p):
    return ''.join(f"<p>{e(x['titulo'])}{e(p['guion'])}{e(x['institucion'])} ({x['inicio']}{e(p['guion'])}{x['fin']})</p>"
                   for x in p['educacion'])


def html_lista(p, valores, separador=None):
    if separador is None:
        return '<ul>' + ''.join(f'<li>{e(v)}</li>' for v in valores) + '</ul>'
    return f'<p>{e(separador.join(valores))}</p>'


def html_seccion(rng, p, seccion, ingles=False, mayusculas_fechas=False):
    contenido = {
        'perfil': lambda: f'<p>{e(perfil(p))}</p>',
        'experiencia': lambda: html_experiencia(rng, p, mayusculas_fechas),
        'educacion': lambda: html_educacion(p),
        'habilidades': lambda: html_lista(p, p['habilidades'], p['separador_habilidades']),
        'idiomas': lambda: html_lista(p, p['idiomas'], rng.choice([', ', '; ', None])),
    }[seccion]()
    titulo = encabezado(rng, seccion, ingles)
    titulo = titulo.upper() if rng.random() < 0.5 else titulo
    return f'<h2>{e(titulo)}</h2>{contenido}'


def contacto(p, separador=' | '):
    return separador.join(x for x in [p['ciudad'], p['telefono'], p['email']] if x)


def html_clasico(rng, p, extra=False):
    partes = [f"<h1>{e(nombre_visible(p))}</h1><p class='sub'>{e(p['titulo_perfil'])}</p><p>{e(contacto(p))}</p>"]
    partes += [html_seccion(rng, p, s) for s in orden_secciones(p)]
    if extra:  # varias páginas: tareas largas, cursos, referencias e información adicional
        partes.append(f"<p>{e(voc.TAREAS_EXTRA[0])}</p>" * 6)
        partes.append('<h2>CURSOS Y CERTIFICACIONES</h2>' + html_lista(p, rng.sample(voc.CURSOS, 4)))
        referencias = []
        for _ in range(3):
            persona = (f"{rng.choice(voc.TRATAMIENTOS)} {rng.choice(voc.NOMBRES_HOMBRE + voc.NOMBRES_MUJER)} "
                       f"{rng.choice(voc.APELLIDOS['entrenamiento'])}")
            referencias.append(f"{persona}, {rng.choice(voc.CARGOS_REFERENCIA)} - +502 "
                               f"{rng.randint(3000, 5999)}-{rng.randint(1000, 9999)}")
        partes.append('<h2>REFERENCIAS</h2>' + ''.join(f'<p>{e(r)}</p>' for r in referencias))
        partes.append('<h2>INFORMACIÓN ADICIONAL</h2><p>Disponibilidad inmediata. Licencia de conducir tipo B.</p>')
    return ''.join(partes)


def html_dos_columnas(rng, p):
    """Devuelve (barra lateral, columna principal)."""
    lateral = f"<h2>{e(rng.choice(['Contacto', 'CONTACTO']))}</h2>" + \
        ''.join(f'<p>{e(x)}</p>' for x in [p['telefono'], p['email'], p['ciudad']] if x)
    if not p['habilidades_en_perfil']:
        lateral += html_seccion(rng, p, 'habilidades')
    lateral += html_seccion(rng, p, 'idiomas')
    principal = f"<h1>{e(nombre_visible(p))}</h1><p class='sub'>{e(p['titulo_perfil'])}</p>"
    principal += ''.join(html_seccion(rng, p, s) for s in orden_secciones(p) if s not in ('habilidades', 'idiomas'))
    return lateral, principal


def html_tabla(rng, p):
    """Devuelve (cabecera, filas de la tabla [(etiqueta, contenido)])."""
    filas = [('DATOS PERSONALES', ''.join(f'<p>{e(x)}</p>' for x in
                                         [f"Teléfono: {p['telefono']}",
                                          f"Correo: {p['email']}" if p['email'] else '',
                                          f"Residencia: {p['ciudad']}"] if x))]
    for s in orden_secciones(p):
        seccion = html_seccion(rng, p, s)
        titulo, contenido = seccion[4:].split('</h2>', 1)
        filas.append((html.unescape(titulo).upper(), contenido))
    return f"<h1>{e(p['nombre'])}</h1><p class='sub'>{e(p['titulo_perfil'])}</p>", filas


def html_creativo(rng, p):
    banner = (f"<div class='banner'><h1>{e(p['nombre'].upper())}</h1>"
              f"<p>{e(p['titulo_perfil'].upper())}</p><p>{e(contacto(p, ' · '))}</p></div>")
    return banner + ''.join(html_seccion(rng, p, s, ingles=True, mayusculas_fechas=rng.random() < 0.5)
                            for s in orden_secciones(p))


PAGINA = pymupdf.paper_rect('letter')
AREA = PAGINA + (45, 45, -45, -45)


def historia(html_doc):
    return pymupdf.Story(html=f'<body>{html_doc}</body>', user_css=CSS)


def colocar(dispositivo, story, rect):
    """Dibuja una historia dentro de un rectángulo; devuelve (queda texto, rect usado)."""
    hay_mas, usado = story.place(rect)
    story.draw(dispositivo)
    return hay_mas, pymupdf.Rect(usado)


def escribir_pdf(html_doc, ruta):
    """Una sola columna, con saltos de página automáticos."""
    story = historia(html_doc)
    escritor = pymupdf.DocumentWriter(str(ruta))
    hay_mas = True
    while hay_mas:
        dispositivo = escritor.begin_page(PAGINA)
        hay_mas, _ = colocar(dispositivo, story, AREA)
        escritor.end_page()
    escritor.close()


def escribir_pdf_columnas(lateral, principal, ruta):
    """Barra lateral con fondo de color a la izquierda y columna principal a la derecha."""
    escritor = pymupdf.DocumentWriter(str(ruta))
    corte = AREA.x0 + AREA.width * 0.3
    fondo = pymupdf.Rect(0, 0, corte + 8, PAGINA.height)
    story_principal = historia(principal)
    dispositivo = escritor.begin_page(PAGINA)
    colocar(dispositivo, historia(lateral), pymupdf.Rect(AREA.x0 - 20, AREA.y0, corte - 6, AREA.y1))
    hay_mas, _ = colocar(dispositivo, story_principal, pymupdf.Rect(corte + 18, AREA.y0, AREA.x1, AREA.y1))
    escritor.end_page()
    while hay_mas:  # si la columna principal no cabe, sigue en otra página
        dispositivo = escritor.begin_page(PAGINA)
        hay_mas, _ = colocar(dispositivo, story_principal, AREA)
        escritor.end_page()
    escritor.close()
    # fondo de la barra lateral (se dibuja debajo del texto)
    doc = pymupdf.open(ruta)
    doc[0].draw_rect(fondo, color=None, fill=(0.91, 0.93, 0.96), overlay=False)
    datos = doc.tobytes()
    doc.close()
    Path(ruta).write_bytes(datos)


def escribir_pdf_tabla(cabecera, filas, ruta):
    """Etiquetas de sección a la izquierda y contenido a la derecha, fila por fila."""
    escritor = pymupdf.DocumentWriter(str(ruta))
    corte = AREA.x0 + AREA.width * 0.26
    dispositivo = escritor.begin_page(PAGINA)
    _, usado = colocar(dispositivo, historia(cabecera), AREA)
    y = usado.y1 + 10
    for etiqueta, contenido in filas:
        story = historia(contenido)
        _, usado_etiqueta = colocar(dispositivo, historia(f"<p class='etiqueta'>{e(etiqueta)}</p>"),
                                    pymupdf.Rect(AREA.x0, y, corte - 10, AREA.y1))
        hay_mas, usado = colocar(dispositivo, story, pymupdf.Rect(corte, y, AREA.x1, AREA.y1))
        while hay_mas:  # fila demasiado larga: sigue en otra página
            escritor.end_page()
            dispositivo = escritor.begin_page(PAGINA)
            hay_mas, usado = colocar(dispositivo, story, pymupdf.Rect(corte, AREA.y0, AREA.x1, AREA.y1))
        y = max(usado.y1, usado_etiqueta.y1) + 10
    escritor.end_page()
    escritor.close()


def comprimir(ruta):
    """Incrusta solo los caracteres usados de cada fuente (cada PDF pasa de ~95 KB a ~30 KB)."""
    doc = pymupdf.open(ruta)
    doc.subset_fonts()
    datos = doc.tobytes(garbage=3, deflate=True)
    doc.close()
    Path(ruta).write_bytes(datos)


def escanear(ruta, rng):
    """Convierte un PDF en imágenes ligeramente giradas y con ruido, como un escaneo."""
    original = pymupdf.open(ruta)
    escaneado = pymupdf.open()
    for pagina in original:
        pix = pagina.get_pixmap(dpi=150, colorspace=pymupdf.csGRAY)
        img = Image.frombytes('L', (pix.width, pix.height), pix.samples)
        img = img.rotate(rng.uniform(-0.8, 0.8), fillcolor=255, resample=Image.BICUBIC)
        img = img.filter(ImageFilter.GaussianBlur(rng.uniform(0.2, 0.6)))
        ruido = Image.effect_noise(img.size, 12)
        img = Image.blend(img, ruido, 0.06)
        buffer = io.BytesIO()
        img.save(buffer, format='JPEG', quality=70)
        nueva = escaneado.new_page(width=pagina.rect.width, height=pagina.rect.height)
        nueva.insert_image(nueva.rect, stream=buffer.getvalue())
    original.close()
    escaneado.save(ruta)


# ---------- Word ----------

def docx_titulo(doc, texto, tamano=12, color=(28, 61, 90)):
    run = doc.add_paragraph().add_run(texto)
    run.bold = True
    run.font.size = Pt(tamano)
    run.font.color.rgb = RGBColor(*color)


def docx_lista(doc, valores, separador):
    if separador is None:
        for v in valores:
            doc.add_paragraph(v, style='List Bullet')
    else:
        doc.add_paragraph(separador.join(valores))


def escribir_docx(rng, p, formato, ruta):
    doc = docx.Document()
    estilo = doc.styles['Normal']
    estilo.font.name = 'Calibri'
    estilo.font.size = Pt(10.5)

    if formato == 'word_tablas':
        tabla = doc.add_table(rows=1, cols=2)
        izquierda, derecha = tabla.rows[0].cells
        izquierda.text = nombre_visible(p) + '\n' + p['titulo_perfil']
        derecha.text = '\n'.join(x for x in [p['telefono'], p['email'], p['ciudad']] if x)
    else:
        docx_titulo(doc, nombre_visible(p), 18, (20, 20, 20))
        doc.add_paragraph(p['titulo_perfil'])
        doc.add_paragraph(contacto(p, rng.choice([' | ', ' / ', ' · '])))

    prosa = formato == 'word_prosa'
    for seccion in orden_secciones(p):
        if seccion == 'perfil' and prosa and rng.random() < 0.5:
            doc.add_paragraph(perfil(p))  # perfil sin encabezado
            continue
        titulo = encabezado(rng, seccion)
        docx_titulo(doc, titulo.upper() if formato == 'word_tablas' else titulo)
        if seccion == 'perfil':
            doc.add_paragraph(perfil(p))
        elif seccion == 'experiencia':
            if prosa:
                for t in p['trabajos']:
                    doc.add_paragraph(f"{t['empresa']} ({periodo(p, t)}). Cargo: {t['puesto']}. "
                                      f"Funciones: {t['tareas'][0].lower()}; {t['tareas'][1].lower()}.")
            elif formato == 'word_tablas':
                tabla = doc.add_table(rows=0, cols=2)
                for t in p['trabajos']:
                    izquierda, derecha = tabla.add_row().cells
                    izquierda.text = periodo(p, t)
                    derecha.text = f"{t['puesto']}\n{t['empresa']}, {t['ciudad']}\n" + '\n'.join(t['tareas'])
            else:
                for t in p['trabajos']:
                    doc.add_paragraph().add_run(f"{t['puesto']}{p['guion']}{t['empresa']}").bold = True
                    doc.add_paragraph(periodo(p, t))
                    docx_lista(doc, t['tareas'], None)
        elif seccion == 'educacion':
            for x in p['educacion']:
                if prosa:
                    doc.add_paragraph(f"{x['institucion']}{p['guion']}{x['titulo']}, promoción {x['fin']}.")
                else:
                    doc.add_paragraph(f"{x['inicio']}{p['guion']}{x['fin']}   {x['titulo']}, {x['institucion']}")
        elif seccion == 'habilidades':
            docx_lista(doc, p['habilidades'], p['separador_habilidades'])
        elif seccion == 'idiomas':
            docx_lista(doc, p['idiomas'], rng.choice([', ', ' | ', None]))
    doc.save(ruta)


# ---------- Principal ----------

def generar(n_entrenamiento, n_prueba, semilla, salida):
    rng = random.Random(semilla)
    grupos = construir_grupos()
    (salida / 'pdf').mkdir(parents=True, exist_ok=True)
    (salida / 'word').mkdir(parents=True, exist_ok=True)
    formatos, pesos = list(FORMATOS), [v[0] for v in FORMATOS.values()]

    filas = []
    conjuntos = ['entrenamiento'] * n_entrenamiento + ['prueba'] * n_prueba
    for i, conjunto in enumerate(conjuntos, start=1):
        p = crear_persona(rng, conjunto, grupos)
        formato = rng.choices(formatos, pesos)[0]
        tipo = FORMATOS[formato][1]
        carpeta = 'pdf' if tipo == 'pdf' else 'word'
        archivo = f"{carpeta}/cv_s{i:03d}_{formato}.{tipo}"
        ruta = salida / archivo

        if tipo == 'docx':
            escribir_docx(rng, p, formato, ruta)
        else:
            base = rng.choice(['clasico', 'tabla']) if formato == 'escaneado' else formato
            if base in ('clasico', 'varias_paginas'):
                escribir_pdf(html_clasico(rng, p, extra=base == 'varias_paginas'), ruta)
            elif base == 'creativo':
                escribir_pdf(html_creativo(rng, p), ruta)
            elif base == 'dos_columnas':
                escribir_pdf_columnas(*html_dos_columnas(rng, p), ruta)
            else:
                escribir_pdf_tabla(*html_tabla(rng, p), ruta)
            if formato == 'escaneado':
                escanear(ruta, rng)
            else:
                comprimir(ruta)

        casos = []
        if not p['email']:
            casos.append('Sin correo electrónico.')
        if p['habilidades_en_perfil']:
            casos.append('Sin sección de habilidades; aparecen en el perfil.')
        if p['educacion_primero']:
            casos.append('Educación antes que experiencia.')
        filas.append({
            'archivo': archivo, 'conjunto': conjunto, 'formato': formato, 'tipo': 'PDF' if tipo == 'pdf' else 'Word',
            'tiene_foto': 'no', 'texto_seleccionable': 'no' if formato == 'escaneado' else 'si',
            'nombre': p['nombre'], 'email': p['email'], 'telefono': p['telefono'], 'ciudad': p['ciudad'],
            'puesto_actual': p['trabajos'][0]['puesto'],
            'empresas': '; '.join(t['empresa'] for t in p['trabajos']),
            'titulos_educacion': '; '.join(x['titulo'] for x in p['educacion']),
            'instituciones': '; '.join(dict.fromkeys(x['institucion'] for x in p['educacion'])),
            'habilidades': '; '.join(p['habilidades']), 'idiomas': '; '.join(p['idiomas']),
            'anios_experiencia': p['anios_experiencia'], 'formato_fechas': p['formato_fechas'],
            'casos_especiales': ' '.join(casos),
        })

    with open(salida / 'etiquetas_ground_truth.csv', 'w', newline='', encoding='utf-8-sig') as f:
        escritor = csv.DictWriter(f, fieldnames=list(filas[0]))
        escritor.writeheader()
        escritor.writerows(filas)
    return filas


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--entrenamiento', type=int, default=160)
    parser.add_argument('--prueba', type=int, default=40)
    parser.add_argument('--semilla', type=int, default=2026)
    parser.add_argument('--salida', type=Path, default=RAIZ / 'CVs_sinteticos')
    args = parser.parse_args()
    filas = generar(args.entrenamiento, args.prueba, args.semilla, args.salida)
    print(f'{len(filas)} CVs generados en {args.salida}')
