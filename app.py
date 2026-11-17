"""TalentLens: app de Streamlit con dos páginas, Candidatos y Puestos."""
import streamlit as st

from comun import ESTILOS

st.set_page_config(page_title='TalentLens', page_icon='🔎', layout='wide')
st.html(ESTILOS)

pagina = st.navigation([
    st.Page('paginas/candidatos.py', title='Candidatos', icon='👥', default=True),
    st.Page('paginas/puestos.py', title='Puestos', icon='💼'),
])
pagina.run()
