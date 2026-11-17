"""Página Puestos: los puestos disponibles con los que se clasifica a los candidatos."""
import streamlit as st

from comun import analizar_oferta, encabezado, etiqueta, guardar_puestos, leer_puestos, nuevo_id

encabezado('Puestos disponibles: define los puestos que tienes abiertos para clasificar a los candidatos.')

puestos, pesos = leer_puestos()


def avisar(mensaje):
    st.session_state['aviso'] = mensaje  # se muestra después de st.rerun()


if 'aviso' in st.session_state:
    st.toast(st.session_state.pop('aviso'))
# habilidades de los CVs que ya se subieron, para reconocerlas también en las ofertas
habilidades_cvs = st.session_state.get('habilidades_cvs', [])

st.write('Cada puesto se define con su **oferta de empleo**. TalentLens lee la oferta, detecta las '
         '**habilidades** y los **años de experiencia** que pide, y con eso calcula qué tan compatible es '
         'cada candidato en la página **Candidatos**. Los puestos se guardan y siguen aquí la próxima vez.')

# ---------- Agregar un puesto ----------
with st.container(border=True):
    st.subheader('Agregar un puesto')
    borrador = st.session_state.get('borrador')

    if borrador is None:
        st.caption('Paso 1 de 2 · Escribe el nombre y pega la oferta.')
        nombre = st.text_input('Nombre del puesto', placeholder='Ej. Contador General')
        oferta = st.text_area('Oferta de empleo', height=140,
                              placeholder='Pega aquí el anuncio completo: funciones, requisitos, '
                                          'conocimientos y años de experiencia...')
        if st.button('Analizar oferta', type='primary'):
            if nombre.strip() and oferta.strip():
                habilidades, anios = analizar_oferta(oferta, habilidades_cvs)
                st.session_state['borrador'] = {'nombre': nombre.strip(), 'oferta': oferta.strip(),
                                                'habilidades': habilidades, 'anios': anios}
                st.rerun()
            else:
                st.warning('Escribe el nombre del puesto y pega la oferta.')
    else:
        st.caption('Paso 2 de 2 · Revisa lo que se detectó en la oferta y guarda el puesto.')
        st.markdown(f"**{borrador['nombre']}**")
        with st.expander('Ver oferta'):
            st.write(borrador['oferta'])
        if not borrador['habilidades']:
            st.info('No se detectaron habilidades en la oferta. Escríbelas abajo.')
        habilidades = st.multiselect(
            'Habilidades requeridas', sorted(set(borrador['habilidades']) | set(habilidades_cvs), key=str.lower),
            default=borrador['habilidades'], accept_new_options=True,
            help='Detectadas en la oferta. Puedes quitar alguna o escribir otras y presionar Enter.')
        anios = st.number_input('Años mínimos de experiencia', 0, 40, borrador['anios'],
                                help='Detectados en la oferta (por ejemplo "al menos 3 años de experiencia").')
        c1 = c2 = st.container(horizontal=True)
        if c1.button('Guardar puesto', type='primary'):
            puestos.append({'id': nuevo_id(puestos), 'nombre': borrador['nombre'], 'oferta': borrador['oferta'],
                            'habilidades': habilidades, 'anios': int(anios)})
            guardar_puestos(puestos, pesos)
            del st.session_state['borrador']
            avisar(f"Puesto «{borrador['nombre']}» guardado.")
            st.rerun()
        if c2.button('Cancelar'):
            del st.session_state['borrador']
            st.rerun()

# ---------- Puestos guardados ----------
st.subheader(f'Puestos guardados ({len(puestos)})')
if not puestos:
    st.info('Todavía no hay puestos. Agrega el primero arriba.')

for puesto in list(puestos):
    clave = puesto['id']
    with st.container(border=True):
        st.markdown(f"#### {puesto['nombre']}")
        if puesto['habilidades']:
            st.markdown(f":blue-badge[{puesto['anios']} años de experiencia] " +
                        ' '.join(f":green-badge[{etiqueta(h)}]" for h in puesto['habilidades']))
        else:
            st.markdown(f":blue-badge[{puesto['anios']} años de experiencia] :gray-badge[Sin habilidades requeridas]")

        with st.expander('Ver oferta'):
            st.write(puesto['oferta'])
        with st.expander('Editar'):
            nombre = st.text_input('Nombre del puesto', puesto['nombre'], key=f'nombre_{clave}')
            oferta = st.text_area('Oferta de empleo', puesto['oferta'], height=120, key=f'oferta_{clave}')
            habilidades = st.multiselect(
                'Habilidades requeridas', sorted(set(puesto['habilidades']) | set(habilidades_cvs), key=str.lower),
                default=puesto['habilidades'], accept_new_options=True, key=f'habilidades_{clave}')
            anios = st.number_input('Años mínimos de experiencia', 0, 40, puesto['anios'], key=f'anios_{clave}')
            c1 = c2 = st.container(horizontal=True)
            if c1.button('Guardar cambios', key=f'guardar_{clave}', type='primary'):
                puesto.update(nombre=nombre.strip() or puesto['nombre'], oferta=oferta.strip() or puesto['oferta'],
                              habilidades=habilidades, anios=int(anios))
                guardar_puestos(puestos, pesos)
                avisar('Cambios guardados.')
                st.rerun()
            if c2.button('Eliminar puesto', key=f'eliminar_{clave}'):
                puestos.remove(puesto)
                guardar_puestos(puestos, pesos)
                avisar(f"Puesto «{puesto['nombre']}» eliminado.")
                st.rerun()

# ---------- Cálculo ----------
with st.expander('¿Cómo se calcula el % de compatibilidad?'):
    st.markdown("""
El % de un candidato con un puesto combina tres partes:

- **Habilidades:** cuántas de las habilidades requeridas tiene el candidato.
- **Experiencia:** sus años frente a los años mínimos del puesto (100% si los cumple o supera).
- **Similitud con la oferta:** qué tanto se parece el texto del CV al de la oferta, con **TF-IDF y similitud coseno**.
  Capta palabras que no son habilidades, como funciones o sector.

Puedes cambiar cuánto pesa cada parte:
""")
    nuevos = {
        'habilidades': st.slider('Habilidades', 0, 100, pesos['habilidades'], 5, format='%d%%'),
        'experiencia': st.slider('Experiencia', 0, 100, pesos['experiencia'], 5, format='%d%%'),
        'similitud': st.slider('Similitud con la oferta', 0, 100, pesos['similitud'], 5, format='%d%%'),
    }
    total = sum(nuevos.values())
    st.caption(f'Los pesos se reparten en proporción (suman {total}%).' if total else
               'Al menos un peso debe ser mayor que 0.')
    if st.button('Guardar pesos', disabled=total == 0 or nuevos == pesos):
        guardar_puestos(puestos, nuevos)
        avisar('Pesos guardados.')
        st.rerun()
