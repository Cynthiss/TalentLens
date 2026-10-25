import pandas as pd
import streamlit as st
from spacy import displacy

import extractor

st.set_page_config(page_title='TalentLens', page_icon='🔎', layout='wide')

COLORES = {'EMPRESA': '#d9ccf5', 'TITULO': '#cfe0f7', 'INSTITUCION': '#d3efe4', 'HABILIDAD': '#f7d3d3'}


@st.cache_resource
def cargar_modelos():
    return extractor.cargar_modelos()


@st.cache_data(show_spinner=False)
def procesar(datos, nombre_archivo):
    nlp, ner_cv = cargar_modelos()
    return extractor.procesar_cv(datos, nombre_archivo, nlp, ner_cv)


st.title('🔎 TalentLens')
st.write('Sube CVs en PDF o Word y obtén una tabla comparativa de los candidatos, '
         'extraída automáticamente con PLN.')

archivos = st.file_uploader('CVs', type=['pdf', 'docx'], accept_multiple_files=True,
                            label_visibility='collapsed')

if not archivos:
    st.info('Sube uno o varios CVs para empezar. Los PDF escaneados se leen con OCR.')
    st.stop()

resultados, fallidos = [], []
barra = st.progress(0.0, text='Procesando CVs...')
for i, archivo in enumerate(archivos, start=1):
    try:
        resultados.append(procesar(archivo.getvalue(), archivo.name))
    except Exception as error:
        fallidos.append((archivo.name, error))
    barra.progress(i / len(archivos), text=f'Procesando CVs... {i}/{len(archivos)}')
barra.empty()

for nombre, error in fallidos:
    st.warning(f'No se pudo leer **{nombre}**: {error}')
if not resultados:
    st.stop()

candidatos = pd.DataFrame(resultados)

# ---------- Filtros ----------
with st.sidebar:
    st.header('Filtros')
    todas = sorted({h for hs in candidatos['habilidades'] for h in hs}, key=str.lower)
    requeridas = st.multiselect('Habilidades requeridas', todas)
    maximo = float(candidatos['anios_experiencia'].max())
    minimo_anios = st.slider('Años de experiencia mínimos', 0.0, max(maximo, 1.0), 0.0, 0.5)

def cumple(fila):
    tiene = {h.lower() for h in fila['habilidades']}
    return fila['anios_experiencia'] >= minimo_anios and all(r.lower() in tiene for r in requeridas)

filtrados = candidatos[candidatos.apply(cumple, axis=1)]

# ---------- Tabla comparativa ----------
c1, c2, c3 = st.columns(3)
c1.metric('CVs procesados', len(candidatos))
c2.metric('Cumplen los filtros', len(filtrados))
c3.metric('Experiencia promedio', f"{filtrados['anios_experiencia'].mean():.1f} años" if len(filtrados) else '-')

tabla = filtrados.drop(columns=['texto']).copy()
for columna in ['empresas', 'titulos', 'instituciones', 'habilidades']:
    tabla[columna] = tabla[columna].map('; '.join)
tabla = tabla.rename(columns={
    'archivo': 'Archivo', 'nombre': 'Nombre', 'email': 'Correo', 'telefono': 'Teléfono',
    'anios_experiencia': 'Años de experiencia', 'empresas': 'Empresas', 'titulos': 'Títulos',
    'instituciones': 'Instituciones', 'habilidades': 'Habilidades'})
tabla = tabla[['Nombre', 'Años de experiencia', 'Habilidades', 'Títulos', 'Instituciones',
               'Empresas', 'Correo', 'Teléfono', 'Archivo']].sort_values('Años de experiencia', ascending=False)

st.dataframe(tabla, hide_index=True, use_container_width=True,
             column_config={'Años de experiencia': st.column_config.NumberColumn(format='%.1f')})

st.download_button('Descargar tabla (CSV)', tabla.to_csv(index=False).encode('utf-8-sig'),
                   file_name='candidatos_talentlens.csv', mime='text/csv')

st.caption('TalentLens no reemplaza al reclutador: ordena la información para acelerar la revisión inicial. '
           'Revisa siempre el CV original antes de descartar a alguien.')

# ---------- Detalle por candidato ----------
st.subheader('Detalle por candidato')
st.write('Entidades que encontró el modelo NER en el texto de cada CV.')
_, ner_cv = cargar_modelos()
for _, fila in filtrados.iterrows():
    with st.expander(f"{fila['nombre'] or fila['archivo']} · {fila['anios_experiencia']:.1f} años"):
        html = displacy.render(ner_cv(fila['texto']), style='ent', options={'colors': COLORES})
        st.html(f'<style>mark {{ color: #1f2430; }}</style>{html}')
