"""Piezas compartidas por las páginas de la app: estilos, modelos, puestos guardados y cálculo de compatibilidad."""
import csv
import json
from pathlib import Path

import pandas as pd
import streamlit as st

import compatibilidad
import extractor

CARPETA = Path(__file__).parent
ARCHIVO_PUESTOS = CARPETA / 'puestos.json'

AZUL = '#121F38'
VERDE = '#1C7A6B'
COLORES_NER = {'EMPRESA': '#e4dcf7', 'TITULO': '#dbe7f7', 'INSTITUCION': '#d8efe6', 'HABILIDAD': '#f7dede'}
# por debajo de este %, ningún puesto se considera compatible. Umbral y pesos se eligieron con la
# función de valor (horas ahorradas al reclutador menos candidatos calificados perdidos) en 1,860 pares
# CV-puesto: con el % igual a la similitud TF-IDF y 19%, no se pierde ninguno de los 144 calificados y
# solo pasan 2 de 1,716 no calificados. Mezclar habilidades bajaba el valor: la oferta y el CV suelen
# nombrar distinto la misma habilidad (SQL / Snowflake). Habilidades y experiencia se muestran como explicación.
MINIMO_COMPATIBLE = 19
PESOS_INICIALES = {'habilidades': 0, 'experiencia': 0, 'similitud': 100}

ESTILOS = f"""
<style>
  .hero {{ background: {AZUL}; color: #F7F5F0; padding: 28px 32px; border-radius: 14px; margin-bottom: 8px; }}
  .hero h1 {{ color: #F7F5F0; font-size: 2.4rem; letter-spacing: 0.04em; margin: 0; padding: 0; }}
  .hero p {{ color: #C9CFDB; margin: 6px 0 0; font-size: 1.05rem; }}
  .paso {{ background: #fff; border: 1px solid #DDD6CA; border-radius: 12px; padding: 18px; height: 100%; }}
  .paso b {{ color: {VERDE}; }}
  mark {{ color: #1E2433; }}
  .detalle-ner .entities {{ line-height: 1.75 !important; font-size: 0.92rem; }}
  .detalle-ner mark {{ padding: 0.1em 0.35em !important; margin: 0 0.1em !important; line-height: 1.4 !important;
                       border-radius: 0.3em !important; }}
  .detalle-ner mark span {{ font-size: 0.65em !important; margin-left: 0.35em !important; }}
</style>
"""


def encabezado(subtitulo):
    st.html(f'<div class="hero"><h1>TALENTLENS</h1><p>{subtitulo}</p></div>')


@st.cache_resource(show_spinner='Cargando modelos de PLN...')
def cargar_modelos():
    return extractor.cargar_modelos()


@st.cache_data(show_spinner=False)
def procesar(datos, nombre_archivo):
    nlp, ner_cv = cargar_modelos()
    return extractor.procesar_cv(datos, nombre_archivo, nlp, ner_cv)


def etiqueta(texto):
    """Texto seguro dentro de una etiqueta :color-badge[...] de Streamlit."""
    return texto.replace('[', '(').replace(']', ')')


# ---------- Puestos guardados ----------

def leer_puestos():
    """Puestos disponibles y pesos del cálculo, guardados en puestos.json."""
    if ARCHIVO_PUESTOS.exists():
        datos = json.loads(ARCHIVO_PUESTOS.read_text(encoding='utf-8'))
    else:
        datos = {}
    return datos.get('puestos', []), {**PESOS_INICIALES, **datos.get('pesos', {})}


def guardar_puestos(puestos, pesos):
    datos = {'pesos': pesos, 'puestos': puestos}
    ARCHIVO_PUESTOS.write_text(json.dumps(datos, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def nuevo_id(puestos):
    return max((p['id'] for p in puestos), default=0) + 1


@st.cache_data(show_spinner=False)
def catalogo_habilidades():
    """Habilidades conocidas (de los CSV de respuestas) para reconocerlas dentro de una oferta."""
    habilidades = {}
    for archivo in CARPETA.glob('CVs_*/etiquetas_ground_truth.csv'):
        with open(archivo, encoding='utf-8-sig') as f:
            for fila in csv.DictReader(f):
                for h in fila['habilidades'].split('; '):
                    if h:
                        habilidades.setdefault(h.lower(), h)
    return sorted(habilidades.values(), key=str.lower)


def analizar_oferta(oferta, extra=()):
    """Habilidades y años mínimos que pide una oferta."""
    _, ner_cv = cargar_modelos()
    conocidas = list(dict.fromkeys([*catalogo_habilidades(), *extra]))
    return compatibilidad.requisitos_de_oferta(oferta, ner_cv, conocidas)


# ---------- Compatibilidad ----------

def calcular_compatibilidad(candidatos, puestos, pesos):
    """Para cada candidato: % con cada puesto, su mejor puesto y el detalle de cada cálculo.

    Devuelve (tabla de porcentajes con una columna por puesto, detalle[id_puesto] = lista por candidato).
    """
    tabla = pd.DataFrame(index=candidatos.index)
    detalle = {}
    if not puestos or candidatos.empty:
        tabla['mejor_puesto'] = None
        tabla['mejor_pct'] = 0.0
        return tabla, detalle

    similitud = compatibilidad.similitudes([p['oferta'] for p in puestos], candidatos['texto'])
    for i, puesto in enumerate(puestos):
        resultados = [compatibilidad.compatibilidad(fila, puesto['habilidades'], puesto['anios'],
                                                    similitud[i][j], pesos)
                      for j, (_, fila) in enumerate(candidatos.iterrows())]
        detalle[puesto['id']] = dict(zip(candidatos.index, resultados))
        tabla[puesto['id']] = [r['porcentaje'] for r in resultados]

    ids = [p['id'] for p in puestos]
    tabla['mejor_pct'] = tabla[ids].max(axis=1)
    nombres = {p['id']: p['nombre'] for p in puestos}
    tabla['mejor_puesto'] = tabla[ids].idxmax(axis=1).map(nombres).where(
        tabla['mejor_pct'] >= MINIMO_COMPATIBLE, 'Ninguno')
    return tabla, detalle
