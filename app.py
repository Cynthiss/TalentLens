from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st
from spacy import displacy

import extractor

st.set_page_config(page_title='TalentLens', page_icon='🔎', layout='wide')

AZUL = '#121F38'
VERDE = '#1C7A6B'
COLORES_NER = {'EMPRESA': '#e4dcf7', 'TITULO': '#dbe7f7', 'INSTITUCION': '#d8efe6', 'HABILIDAD': '#f7dede'}

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

tab_tarjetas, tab_tabla, tab_resumen, tab_detalle = st.tabs(
    ['Candidatos', 'Tabla comparativa', 'Resumen', 'Detalle NER'])

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

with tab_tabla:
    tabla = filtrados.drop(columns=['texto']).copy()
    for columna in ['empresas', 'titulos', 'instituciones', 'habilidades']:
        tabla[columna] = tabla[columna].map('; '.join)
    tabla = tabla.rename(columns={
        'archivo': 'Archivo', 'nombre': 'Nombre', 'email': 'Correo', 'telefono': 'Teléfono',
        'anios_experiencia': 'Años de experiencia', 'empresas': 'Empresas', 'titulos': 'Títulos',
        'instituciones': 'Instituciones', 'habilidades': 'Habilidades', 'coincidencias': 'Coincidencias'})
    orden = ['Nombre', 'Años de experiencia', 'Habilidades', 'Títulos', 'Instituciones',
             'Empresas', 'Correo', 'Teléfono', 'Archivo']
    if requeridas_min:
        orden.insert(1, 'Coincidencias')
    tabla = tabla[orden]

    st.dataframe(tabla, hide_index=True, use_container_width=True,
                 column_config={'Años de experiencia': st.column_config.ProgressColumn(
                     format='%.1f', min_value=0, max_value=max(maximo, 1.0))})
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
        use_container_width=True)

    experiencia = filtrados[['nombre', 'anios_experiencia']].rename(
        columns={'nombre': 'Candidato', 'anios_experiencia': 'Años'})
    g2.markdown('**Años de experiencia por candidato**')
    g2.altair_chart(
        alt.Chart(experiencia).mark_bar(color=AZUL, cornerRadiusEnd=4, size=14).encode(
            x=alt.X('Años:Q', axis=alt.Axis(grid=True, gridOpacity=0.4)),
            y=alt.Y('Candidato:N', sort='-x', title=None, axis=alt.Axis(labelLimit=260)),
            tooltip=['Candidato', alt.Tooltip('Años:Q', format='.1f')]),
        use_container_width=True)

with tab_detalle:
    st.write('Texto de cada CV con las entidades que encontró el modelo NER. '
             'Sirve para revisar si la extracción es correcta.')
    _, ner_cv = cargar_modelos()
    for _, fila in filtrados.iterrows():
        with st.expander(f"{fila['nombre']} · {fila['anios_experiencia']:.1f} años"):
            st.html(displacy.render(ner_cv(fila['texto']), style='ent', options={'colors': COLORES_NER}))

st.caption('TalentLens no reemplaza al reclutador: ordena la información para acelerar la revisión inicial. '
           'Revisa siempre el CV original antes de descartar a alguien.')
