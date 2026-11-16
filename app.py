from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st
from spacy import displacy

import compatibilidad
import extractor

st.set_page_config(page_title='TalentLens', page_icon='🔎', layout='wide')

AZUL = '#121F38'
VERDE = '#1C7A6B'
COLORES_NER = {'EMPRESA': '#e4dcf7', 'TITULO': '#dbe7f7', 'INSTITUCION': '#d8efe6', 'HABILIDAD': '#f7dede'}
MINIMO_COMPATIBLE = 40  # por debajo de este %, ningún puesto se considera compatible
PUESTOS_EJEMPLO = [
    {'nombre': 'Analista de Datos',
     'oferta': 'Buscamos Analista de Datos con al menos 3 años de experiencia. Requisitos: Python, SQL, '
               'Power BI y Estadística. Construirás tableros de indicadores, modelos de pronóstico de ventas '
               'y automatización de reportes para gerencia. Licenciatura en Estadística, Ingeniería en '
               'Sistemas o carrera afín.'},
    {'nombre': 'Desarrollador Backend',
     'oferta': 'Empresa de tecnología busca Desarrollador Backend con mínimo 2 años de experiencia. '
               'Conocimientos en Python o Java, Docker, AWS, PostgreSQL y REST APIs. Desarrollo de '
               'servicios en la nube, migración de sistemas y revisión de código.'},
]

st.html(f"""
<style>
  .hero {{ background: {AZUL}; color: #F7F5F0; padding: 28px 32px; border-radius: 14px; margin-bottom: 8px; }}
  .hero h1 {{ color: #F7F5F0; font-size: 2.4rem; letter-spacing: 0.04em; margin: 0; padding: 0; }}
  .hero p {{ color: #C9CFDB; margin: 6px 0 0; font-size: 1.05rem; }}
  .paso {{ background: #fff; border: 1px solid #DDD6CA; border-radius: 12px; padding: 18px; height: 100%; }}
  .paso b {{ color: {VERDE}; }}
  mark {{ color: #1E2433; }}
</style>
""")


@st.cache_resource(show_spinner='Cargando modelos de PLN...')
def cargar_modelos():
    return extractor.cargar_modelos()


@st.cache_data(show_spinner=False)
def procesar(datos, nombre_archivo):
    nlp, ner_cv = cargar_modelos()
    return extractor.procesar_cv(datos, nombre_archivo, nlp, ner_cv)


def badges(valores, resaltar=()):
    """Habilidades como etiquetas; en verde las que coinciden con el filtro."""
    resaltar = {r.lower() for r in resaltar}
    partes = []
    for v in valores:
        texto = v.replace('[', '(').replace(']', ')')
        color = 'green' if v.lower() in resaltar else 'gray'
        partes.append(f':{color}-badge[{texto}]')
    return ' '.join(partes)


st.html("""
<div class="hero">
  <h1>TALENTLENS</h1>
  <p>Extracción inteligente de información de CVs para agilizar la preselección de candidatos.</p>
</div>
""")

# ---------- Carga de CVs ----------
modo = st.segmented_control('Cómo quieres subir los CVs', ['Archivos', 'Carpeta completa'],
                            default='Archivos', label_visibility='collapsed')
if modo == 'Carpeta completa':
    archivos = st.file_uploader('Selecciona una carpeta: se leen todos los PDF y Word que contenga, '
                                'incluyendo subcarpetas.', type=['pdf', 'docx'],
                                accept_multiple_files='directory', key='carpeta')
else:
    archivos = st.file_uploader('Selecciona uno o varios CVs en PDF o Word.', type=['pdf', 'docx'],
                                accept_multiple_files=True, key='archivos')

if not archivos:
    c1, c2, c3 = st.columns(3)
    c1.html('<div class="paso"><b>1 · Sube</b><br>Archivos sueltos o una carpeta completa de CVs en PDF o Word. '
            'Los escaneados se leen con OCR.</div>')
    c2.html('<div class="paso"><b>2 · Extraemos</b><br>Un modelo NER identifica nombre, educación, empresas, '
            'habilidades y años de experiencia.</div>')
    c3.html('<div class="paso"><b>3 · Compara</b><br>Filtra por habilidades y experiencia, revisa a cada candidato '
            'y descarga la tabla.</div>')
    st.stop()

# ---------- Procesamiento ----------
unicos = {}
for archivo in archivos:
    unicos.setdefault((Path(archivo.name).name, archivo.size), archivo)  # sin repetidos

resultados, fallidos = [], []
barra = st.progress(0.0, text='Procesando CVs...')
for i, archivo in enumerate(unicos.values(), start=1):
    nombre = Path(archivo.name).name
    try:
        resultados.append(procesar(archivo.getvalue(), nombre))
    except Exception as error:
        fallidos.append((nombre, error))
    barra.progress(i / len(unicos), text=f'Procesando CVs... {i}/{len(unicos)}')
barra.empty()

for nombre, error in fallidos:
    st.warning(f'No se pudo leer **{nombre}**: {error}')
if not resultados:
    st.stop()

candidatos = pd.DataFrame(resultados)
candidatos['nombre'] = candidatos['nombre'].fillna(candidatos['archivo'])
candidatos[['email', 'telefono']] = candidatos[['email', 'telefono']].fillna('')  # CVs sin correo o teléfono

# misma habilidad con distinta escritura ("Power BI" / "power bi") cuenta como una
escrituras = {}
for habilidades in candidatos['habilidades']:
    for h in habilidades:
        escrituras.setdefault(h.lower(), h)

# ---------- Filtros ----------
with st.sidebar:
    st.header('Filtros')
    requeridas = st.multiselect('Habilidades', sorted(escrituras.values(), key=str.lower),
                                placeholder='Elige una o varias',
                                help='Se muestran los candidatos que tienen al menos una.')
    todas = st.toggle('Exigir todas las habilidades', value=False)
    maximo = float(candidatos['anios_experiencia'].max())
    minimo_anios = st.slider('Años de experiencia mínimos', 0.0, max(maximo, 1.0), 0.0, 0.5)
    busqueda = st.text_input('Buscar', placeholder='Nombre, empresa, título...')

    st.header('Compatibilidad')
    st.caption('Cuánto pesa cada parte en el % de compatibilidad con un puesto.')
    pesos = {
        'habilidades': st.slider('Habilidades requeridas', 0, 100, 50, 5, format='%d%%'),
        'experiencia': st.slider('Años de experiencia', 0, 100, 20, 5, format='%d%%'),
        'similitud': st.slider('Similitud con la oferta (TF-IDF)', 0, 100, 30, 5, format='%d%%'),
    }
    if sum(pesos.values()) == 0:
        pesos = dict(compatibilidad.PESOS)

requeridas_min = [r.lower() for r in requeridas]


def coincidencias(habilidades):
    tiene = {h.lower() for h in habilidades}
    return sum(r in tiene for r in requeridas_min)


def contiene_busqueda(fila):
    if not busqueda:
        return True
    campos = [fila['nombre'], fila['email'] or '', *fila['empresas'], *fila['titulos'], *fila['instituciones']]
    return busqueda.lower() in ' '.join(campos).lower()


candidatos['coincidencias'] = candidatos['habilidades'].map(coincidencias)
necesarias = len(requeridas_min) if todas else min(1, len(requeridas_min))
filtrados = candidatos[(candidatos['coincidencias'] >= necesarias)
                       & (candidatos['anios_experiencia'] >= minimo_anios)
                       & candidatos.apply(contiene_busqueda, axis=1)]
filtrados = filtrados.sort_values(['coincidencias', 'anios_experiencia'], ascending=False)

# ---------- Resumen ----------
m1, m2, m3, m4 = st.columns(4)
m1.metric('CVs', len(candidatos), border=True)
m2.metric('Cumplen filtros', len(filtrados), border=True)
m3.metric('Años promedio', f"{filtrados['anios_experiencia'].mean():.1f}" if len(filtrados) else '-',
          border=True, help='Años de experiencia promedio de los candidatos que cumplen los filtros.')
m4.metric('Habilidades', len(escrituras), border=True, help='Habilidades distintas encontradas en los CVs.')

if filtrados.empty:
    st.info('Ningún candidato cumple los filtros. Prueba quitando alguna condición.')
    st.stop()

tab_tarjetas, tab_compatibilidad, tab_tabla, tab_resumen, tab_detalle = st.tabs(
    ['Candidatos', 'Compatibilidad con puestos', 'Tabla comparativa', 'Resumen', 'Detalle NER'])

with tab_tarjetas:
    columnas = st.columns(2)
    for i, (_, fila) in enumerate(filtrados.iterrows()):
        with columnas[i % 2].container(border=True):
            st.markdown(f"#### {fila['nombre']}")
            etiquetas = f":blue-badge[{fila['anios_experiencia']:.1f} años de experiencia]"
            if requeridas_min:
                etiquetas += f" :green-badge[{fila['coincidencias']} de {len(requeridas_min)} habilidades buscadas]"
            st.markdown(etiquetas)
            if fila['titulos']:
                institucion = f" · {fila['instituciones'][0]}" if fila['instituciones'] else ''
                st.markdown(f"🎓 {fila['titulos'][0]}{institucion}")
            if fila['empresas']:
                st.markdown(f"💼 {', '.join(fila['empresas'])}")
            contacto = ' · '.join(c for c in [fila['email'], fila['telefono']] if c)
            if contacto:
                st.markdown(f"✉️ {contacto}")
            if fila['habilidades']:
                st.markdown(badges(fila['habilidades'], requeridas))
            st.caption(f"📄 {fila['archivo']}")

with tab_compatibilidad:
    st.session_state.setdefault('puestos', [])
    st.session_state.setdefault('siguiente_id', 0)
    puestos = st.session_state['puestos']

    def agregar_puesto(nombre, oferta):
        puestos.append({'id': st.session_state['siguiente_id'], 'nombre': nombre.strip(), 'oferta': oferta.strip()})
        st.session_state['siguiente_id'] += 1

    st.write('Agrega los puestos que necesitas cubrir pegando la descripción de la oferta. '
             'TalentLens saca las habilidades y los años que pide, y calcula qué tan compatible es cada CV.')
    with st.form('nuevo_puesto', clear_on_submit=True, border=True):
        c1, c2 = st.columns([1, 2])
        nombre_puesto = c1.text_input('Nombre del puesto', placeholder='Ej. Analista de Datos')
        oferta_puesto = c2.text_area('Descripción de la oferta', height=110,
                                     placeholder='Pega aquí el anuncio: requisitos, funciones, años de experiencia...')
        if st.form_submit_button('Agregar puesto', type='primary'):
            if nombre_puesto.strip() and oferta_puesto.strip():
                agregar_puesto(nombre_puesto, oferta_puesto)
            else:
                st.warning('Escribe el nombre del puesto y la descripción de la oferta.')

    if not puestos:
        st.info('Todavía no hay puestos. Agrega uno arriba o prueba con dos puestos de ejemplo.')
        if st.button('Cargar puestos de ejemplo'):
            for ejemplo in PUESTOS_EJEMPLO:
                agregar_puesto(ejemplo['nombre'], ejemplo['oferta'])
            st.rerun()
    else:
        _, ner_cv = cargar_modelos()
        conocidas = list(escrituras.values())

        # Requisitos de cada puesto (sacados de la oferta y editables)
        st.markdown('##### Requisitos de cada puesto')
        for puesto in list(puestos):
            clave = puesto['id']
            sugeridas, anios_sugeridos = compatibilidad.requisitos_de_oferta(puesto['oferta'], ner_cv, conocidas)
            with st.expander(f"{puesto['nombre']}", expanded=False):
                st.caption(puesto['oferta'])
                puesto['requeridas'] = st.multiselect(
                    'Habilidades requeridas', sorted(set(conocidas) | set(sugeridas), key=str.lower),
                    default=sugeridas, key=f'requeridas_{clave}', accept_new_options=True,
                    help='Se sacaron de la oferta. Puedes quitar o agregar habilidades.')
                c1, c2 = st.columns([1, 1])
                puesto['anios'] = c1.number_input('Años mínimos de experiencia', 0, 40, anios_sugeridos,
                                                  key=f'anios_{clave}')
                if c2.button('Quitar puesto', key=f'quitar_{clave}'):
                    puestos.remove(puesto)
                    st.rerun()

        # Porcentaje de cada candidato con cada puesto
        similitud = compatibilidad.similitudes([p['oferta'] for p in puestos], filtrados['texto'])
        resultados_puestos = {}
        for i, puesto in enumerate(puestos):
            resultados_puestos[puesto['id']] = [
                compatibilidad.compatibilidad(fila, puesto['requeridas'], puesto['anios'], similitud[i][j], pesos)
                for j, (_, fila) in enumerate(filtrados.iterrows())]

        nombres_columna = {}
        for puesto in puestos:  # nombres de columna únicos aunque dos puestos se llamen igual
            nombre = puesto['nombre']
            while nombre in nombres_columna.values():
                nombre += ' (2)'
            nombres_columna[puesto['id']] = nombre

        matriz = pd.DataFrame({'Candidato': filtrados['nombre'].values})
        for puesto in puestos:
            matriz[nombres_columna[puesto['id']]] = [r['porcentaje'] for r in resultados_puestos[puesto['id']]]
        columnas_puestos = list(nombres_columna.values())
        matriz['Mejor %'] = matriz[columnas_puestos].max(axis=1)
        matriz['Puesto más compatible'] = matriz[columnas_puestos].idxmax(axis=1).where(
            matriz['Mejor %'] >= MINIMO_COMPATIBLE, f'Ninguno (menos de {MINIMO_COMPATIBLE}%)')
        matriz = matriz[['Candidato', 'Puesto más compatible', 'Mejor %'] + columnas_puestos]
        matriz = matriz.sort_values('Mejor %', ascending=False)

        st.markdown('##### ¿Para qué puesto encaja cada candidato?')
        configuracion = {c: st.column_config.ProgressColumn(c, format='%.0f%%', min_value=0, max_value=100)
                         for c in columnas_puestos + ['Mejor %']}
        st.dataframe(matriz, hide_index=True, width='stretch', column_config=configuracion)
        st.download_button('Descargar compatibilidad (CSV)', matriz.to_csv(index=False).encode('utf-8-sig'),
                           file_name='compatibilidad_talentlens.csv', mime='text/csv')

        # Ranking por puesto
        st.markdown('##### Ranking por puesto')
        for tab_puesto, puesto in zip(st.tabs([nombres_columna[p['id']] for p in puestos]), puestos):
            with tab_puesto:
                ranking = sorted(zip(resultados_puestos[puesto['id']], filtrados.itertuples()),
                                 key=lambda par: -par[0]['porcentaje'])
                requisito = f"{len(puesto['requeridas'])} habilidades requeridas · {puesto['anios']} años mínimos"
                st.caption(requisito)
                for resultado, fila in ranking:
                    with st.container(border=True):
                        izquierda, derecha = st.columns([4, 1])
                        izquierda.markdown(f"**{fila.nombre}** · {fila.anios_experiencia:.1f} años de experiencia")
                        derecha.markdown(f"### {resultado['porcentaje']:.0f}%")
                        st.progress(resultado['porcentaje'] / 100)
                        partes = resultado['partes']
                        st.caption(f"Habilidades {partes['habilidades']:.0%} · Experiencia {partes['experiencia']:.0%}"
                                   f" · Similitud con la oferta {partes['similitud']:.0%}")
                        etiquetas = ' '.join([f':green-badge[✓ {h}]' for h in resultado['tiene']] +
                                             [f':red-badge[✗ {h}]' for h in resultado['faltan']])
                        if etiquetas:
                            st.markdown(etiquetas)

with tab_tabla:
    tabla = filtrados.drop(columns=['texto']).copy()
    for columna in ['empresas', 'titulos', 'instituciones', 'habilidades']:
        tabla[columna] = tabla[columna].map('; '.join)
    tabla['coincidencias'] = tabla['coincidencias'].map(lambda n: f'{n} de {len(requeridas_min)}')
    tabla = tabla.rename(columns={
        'archivo': 'Archivo', 'nombre': 'Nombre', 'email': 'Correo', 'telefono': 'Teléfono',
        'anios_experiencia': 'Años de experiencia', 'empresas': 'Empresas', 'titulos': 'Títulos',
        'instituciones': 'Instituciones', 'habilidades': 'Habilidades',
        'coincidencias': 'Habilidades buscadas'})
    orden = ['Nombre', 'Años de experiencia', 'Habilidades', 'Títulos', 'Instituciones',
             'Empresas', 'Correo', 'Teléfono', 'Archivo']
    if requeridas_min:
        orden.insert(1, 'Habilidades buscadas')
    tabla = tabla[orden]

    st.dataframe(tabla, hide_index=True, width='stretch', column_config={
        'Años de experiencia': st.column_config.ProgressColumn(
            format='%.1f', min_value=0, max_value=max(maximo, 1.0)),
        'Habilidades buscadas': st.column_config.TextColumn(
            help='Cuántas de las habilidades elegidas en el filtro tiene el candidato.'),
    })
    st.download_button('Descargar tabla (CSV)', tabla.to_csv(index=False).encode('utf-8-sig'),
                       file_name='candidatos_talentlens.csv', mime='text/csv', type='primary')

with tab_resumen:
    g1, g2 = st.columns(2)

    conteo = pd.Series([escrituras[h.lower()] for hs in filtrados['habilidades'] for h in hs]).value_counts()
    top = conteo.head(12).rename_axis('Habilidad').reset_index(name='Candidatos')
    g1.markdown('**Habilidades más frecuentes**')
    g1.altair_chart(
        alt.Chart(top).mark_bar(color=VERDE, cornerRadiusEnd=4, size=14).encode(
            x=alt.X('Candidatos:Q', axis=alt.Axis(tickMinStep=1, grid=True, gridOpacity=0.4)),
            y=alt.Y('Habilidad:N', sort='-x', title=None, axis=alt.Axis(labelLimit=200)),
            tooltip=['Habilidad', 'Candidatos']),
        width='stretch')

    experiencia = filtrados[['nombre', 'anios_experiencia']].rename(
        columns={'nombre': 'Candidato', 'anios_experiencia': 'Años'})
    g2.markdown('**Años de experiencia por candidato**')
    g2.altair_chart(
        alt.Chart(experiencia).mark_bar(color=AZUL, cornerRadiusEnd=4, size=14).encode(
            x=alt.X('Años:Q', axis=alt.Axis(grid=True, gridOpacity=0.4)),
            y=alt.Y('Candidato:N', sort='-x', title=None, axis=alt.Axis(labelLimit=260)),
            tooltip=['Candidato', alt.Tooltip('Años:Q', format='.1f')]),
        width='stretch')

with tab_detalle:
    st.write('Texto de cada CV con las entidades que encontró el modelo NER. '
             'Sirve para revisar si la extracción es correcta.')
    _, ner_cv = cargar_modelos()
    for _, fila in filtrados.iterrows():
        with st.expander(f"{fila['nombre']} · {fila['anios_experiencia']:.1f} años"):
            st.html(displacy.render(ner_cv(fila['texto']), style='ent', options={'colors': COLORES_NER}))

st.caption('TalentLens no reemplaza al reclutador: ordena la información para acelerar la revisión inicial. '
           'Revisa siempre el CV original antes de descartar a alguien.')
