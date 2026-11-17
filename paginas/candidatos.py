"""Página Candidatos: subir CVs, ver la información extraída y su clasificación por puesto."""
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st
from spacy import displacy

from comun import (AZUL, COLORES_NER, MINIMO_COMPATIBLE, VERDE, calcular_compatibilidad, cargar_modelos,
                   encabezado, etiqueta, leer_puestos, procesar)

encabezado('Extracción inteligente de información de CVs para agilizar la preselección de candidatos.')

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

if archivos:
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
    st.session_state['resultados'] = resultados  # se conservan al cambiar de página
elif st.session_state.get('resultados'):
    st.caption(f"Mostrando los {len(st.session_state['resultados'])} CVs que subiste. "
               'Para cambiarlos, sube otros arriba.')

resultados = st.session_state.get('resultados', [])
if not resultados:
    c1, c2, c3 = st.columns(3)
    c1.html('<div class="paso"><b>1 · Define los puestos</b><br>En la página <b>Puestos</b> pega la oferta de '
            'cada puesto que tienes abierto.</div>')
    c2.html('<div class="paso"><b>2 · Sube los CVs</b><br>Archivos sueltos o una carpeta completa en PDF o Word. '
            'Los escaneados se leen con OCR.</div>')
    c3.html('<div class="paso"><b>3 · Revisa la clasificación</b><br>Cada candidato aparece con su % de '
            'compatibilidad con cada puesto y su mejor puesto.</div>')
    st.stop()

candidatos = pd.DataFrame(resultados)
candidatos['nombre'] = candidatos['nombre'].fillna(candidatos['archivo'])
candidatos[['email', 'telefono']] = candidatos[['email', 'telefono']].fillna('')  # CVs sin correo o teléfono

# misma habilidad con distinta escritura ("Power BI" / "power bi") cuenta como una
escrituras = {}
for habilidades in candidatos['habilidades']:
    for h in habilidades:
        escrituras.setdefault(h.lower(), h)
st.session_state['habilidades_cvs'] = sorted(escrituras.values(), key=str.lower)

# ---------- Compatibilidad con los puestos guardados ----------
puestos, pesos = leer_puestos()
porcentajes, detalle = calcular_compatibilidad(candidatos, puestos, pesos)
candidatos['mejor_puesto'] = porcentajes['mejor_puesto']
candidatos['mejor_pct'] = porcentajes['mejor_pct']
por_nombre = {p['nombre']: p for p in puestos}

# ---------- Filtros ----------
with st.sidebar:
    st.header('Filtrar candidatos')
    if puestos:
        eleccion = st.selectbox('Puesto', ['Todos los puestos'] + list(por_nombre),
                                help='Muestra a los candidatos ordenados por su compatibilidad con este puesto.')
        minimo_pct = st.slider('Compatibilidad mínima', 0, 100, 0, 5, format='%d%%',
                               help='Oculta a los candidatos con menor compatibilidad.')
    else:
        eleccion, minimo_pct = 'Todos los puestos', 0
        st.caption('Define puestos en la página **Puestos** para filtrar por compatibilidad.')

    with st.expander('Más filtros'):
        requeridas = st.multiselect('Tiene alguna de estas habilidades', sorted(escrituras.values(), key=str.lower),
                                    placeholder='Elige una o varias')
        maximo = float(candidatos['anios_experiencia'].max())
        minimo_anios = st.slider('Años de experiencia mínimos', 0.0, max(maximo, 1.0), 0.0, 0.5)
        busqueda = st.text_input('Buscar', placeholder='Nombre, empresa, título...')

puesto_elegido = por_nombre.get(eleccion)
if puesto_elegido:
    candidatos['pct'] = porcentajes[puesto_elegido['id']]
else:
    candidatos['pct'] = candidatos['mejor_pct']

requeridas_min = {r.lower() for r in requeridas}


def cumple(fila):
    if requeridas_min and not requeridas_min & {h.lower() for h in fila['habilidades']}:
        return False
    if busqueda:
        campos = [fila['nombre'], fila['email'], *fila['empresas'], *fila['titulos'], *fila['instituciones']]
        if busqueda.lower() not in ' '.join(campos).lower():
            return False
    return fila['anios_experiencia'] >= minimo_anios and fila['pct'] >= minimo_pct


filtrados = candidatos[candidatos.apply(cumple, axis=1)]
filtrados = filtrados.sort_values(['pct', 'anios_experiencia'], ascending=False)

# ---------- Resumen ----------
m1, m2, m3, m4 = st.columns(4)
m1.metric('CVs', len(candidatos), border=True)
m2.metric('Cumplen filtros', len(filtrados), border=True)
m3.metric('Puestos', len(puestos), border=True, help='Puestos definidos en la página Puestos.')
compatibles = (candidatos['mejor_pct'] >= MINIMO_COMPATIBLE).sum() if puestos else 0
m4.metric('Compatibles con algún puesto', compatibles, border=True,
          help=f'Candidatos con {MINIMO_COMPATIBLE}% o más de compatibilidad con al menos un puesto.')

if filtrados.empty:
    st.info('Ningún candidato cumple los filtros. Prueba quitando alguna condición.')
    st.stop()

tab_clasificacion, tab_tarjetas, tab_tabla, tab_resumen, tab_detalle = st.tabs(
    ['Clasificación por puesto', 'Candidatos', 'Tabla comparativa', 'Resumen', 'Detalle NER'])

with tab_clasificacion:
    if not puestos:
        st.info('Todavía no hay puestos definidos. Agrégalos para clasificar a los candidatos.')
        st.page_link('paginas/puestos.py', label='Ir a Puestos', icon='💼')
    else:
        # cuántos candidatos encajan mejor en cada puesto
        columnas = st.columns(len(puestos) + 1)
        for columna, puesto in zip(columnas, puestos):
            cantidad = (filtrados['mejor_puesto'] == puesto['nombre']).sum()
            columna.metric(puesto['nombre'], cantidad, border=True,
                           help=f'Candidatos cuyo puesto más compatible es este ({MINIMO_COMPATIBLE}% o más).')
        columnas[-1].metric('Sin puesto', (filtrados['mejor_puesto'] == 'Ninguno').sum(), border=True,
                            help=f'Candidatos con menos de {MINIMO_COMPATIBLE}% en todos los puestos.')

        st.markdown('##### ¿Para qué puesto encaja cada candidato?')
        matriz = pd.DataFrame({'Candidato': filtrados['nombre'],
                               'Puesto más compatible': filtrados['mejor_puesto'],
                               'Mejor %': filtrados['mejor_pct']})
        for puesto in puestos:
            matriz[puesto['nombre']] = porcentajes.loc[filtrados.index, puesto['id']]
        matriz = matriz.loc[:, ~matriz.columns.duplicated()]  # por si dos puestos se llaman igual
        porcentuales = [c for c in matriz.columns if c not in ('Candidato', 'Puesto más compatible')]
        st.dataframe(matriz, hide_index=True, width='stretch', column_config={
            c: st.column_config.ProgressColumn(c, format='%.0f%%', min_value=0, max_value=100) for c in porcentuales})
        st.download_button('Descargar clasificación (CSV)', matriz.to_csv(index=False).encode('utf-8-sig'),
                           file_name='clasificacion_talentlens.csv', mime='text/csv')

        st.markdown('##### Ranking por puesto')
        orden = [puesto_elegido] + [p for p in puestos if p is not puesto_elegido] if puesto_elegido else puestos
        for tab_puesto, puesto in zip(st.tabs([p['nombre'] for p in orden]), orden):
            with tab_puesto:
                st.caption(f"Pide {len(puesto['habilidades'])} habilidades y {puesto['anios']} años de experiencia.")
                ranking = sorted(filtrados.index, key=lambda i: -detalle[puesto['id']][i]['porcentaje'])
                for i in ranking:
                    resultado = detalle[puesto['id']][i]
                    fila = filtrados.loc[i]
                    with st.container(border=True):
                        izquierda, derecha = st.columns([4, 1])
                        izquierda.markdown(f"**{fila['nombre']}** · {fila['anios_experiencia']:.1f} años de experiencia")
                        derecha.markdown(f"### {resultado['porcentaje']:.0f}%")
                        st.progress(resultado['porcentaje'] / 100)
                        partes = resultado['partes']
                        st.caption(f"Habilidades {partes['habilidades']:.0%} · Experiencia {partes['experiencia']:.0%}"
                                   f" · Similitud con la oferta {partes['similitud']:.0%}")
                        etiquetas = ' '.join([f':green-badge[✓ {etiqueta(h)}]' for h in resultado['tiene']] +
                                             [f':red-badge[✗ {etiqueta(h)}]' for h in resultado['faltan']])
                        if etiquetas:
                            st.markdown(etiquetas)

with tab_tarjetas:
    columnas = st.columns(2)
    for i, (_, fila) in enumerate(filtrados.iterrows()):
        with columnas[i % 2].container(border=True):
            st.markdown(f"#### {fila['nombre']}")
            etiquetas = f":blue-badge[{fila['anios_experiencia']:.1f} años de experiencia]"
            if puestos:
                if fila['mejor_puesto'] == 'Ninguno':
                    etiquetas += f" :gray-badge[Sin puesto compatible]"
                else:
                    etiquetas += f" :green-badge[{etiqueta(fila['mejor_puesto'])} · {fila['mejor_pct']:.0f}%]"
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
                st.markdown(' '.join(f":{'green' if h.lower() in requeridas_min else 'gray'}-badge[{etiqueta(h)}]"
                                     for h in fila['habilidades']))
            st.caption(f"📄 {fila['archivo']}")

with tab_tabla:
    tabla = filtrados.copy()
    for columna in ['empresas', 'titulos', 'instituciones', 'habilidades']:
        tabla[columna] = tabla[columna].map('; '.join)
    tabla = tabla.rename(columns={
        'archivo': 'Archivo', 'nombre': 'Nombre', 'email': 'Correo', 'telefono': 'Teléfono',
        'anios_experiencia': 'Años de experiencia', 'empresas': 'Empresas', 'titulos': 'Títulos',
        'instituciones': 'Instituciones', 'habilidades': 'Habilidades',
        'mejor_puesto': 'Puesto más compatible', 'mejor_pct': 'Compatibilidad'})
    orden = ['Nombre', 'Años de experiencia', 'Habilidades', 'Títulos', 'Instituciones',
             'Empresas', 'Correo', 'Teléfono', 'Archivo']
    if puestos:
        orden[1:1] = ['Puesto más compatible', 'Compatibilidad']
    tabla = tabla[orden]

    st.dataframe(tabla, hide_index=True, width='stretch', column_config={
        'Años de experiencia': st.column_config.ProgressColumn(
            format='%.1f', min_value=0, max_value=max(maximo, 1.0)),
        'Compatibilidad': st.column_config.ProgressColumn(format='%.0f%%', min_value=0, max_value=100),
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
