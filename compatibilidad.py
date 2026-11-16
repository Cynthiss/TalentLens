"""Compatibilidad entre un CV y una oferta de empleo.

El porcentaje combina tres partes:
- Habilidades: cuántas de las habilidades requeridas tiene el candidato.
- Experiencia: sus años frente a los años mínimos del puesto.
- Similitud del texto: TF-IDF + similitud coseno entre la oferta y el CV completo.
"""
import re

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from spacy.lang.es.stop_words import STOP_WORDS

from extractor import sin_acentos

PESOS = {'habilidades': 0.5, 'experiencia': 0.2, 'similitud': 0.3}
# Con los CVs sintéticos, un CV de la misma profesión que la oferta tiene similitud coseno
# de 0.15 a 0.38 y uno de otra profesión menos de 0.08; 0.35 se toma como 100%.
SIMILITUD_MAXIMA = 0.35
PALABRAS_VACIAS = sorted({sin_acentos(p) for p in STOP_WORDS})

RE_ANIOS = re.compile(r'(\d{1,2})\s*\+?\s*años?\s+(?:o más\s+)?de\s+experiencia', re.I)
RE_ANIOS_MINIMO = re.compile(r'(?:mínimo|minimo|al menos)\s+(?:de\s+)?(\d{1,2})\s*años?', re.I)


def contiene(texto, valor):
    """¿Aparece `valor` como palabra completa en el texto? (sin importar mayúsculas ni saltos de línea)"""
    patron = r'\s+'.join(map(re.escape, valor.split()))
    return re.search(rf'(?<!\w){patron}(?!\w)', texto, flags=re.I) is not None


def requisitos_de_oferta(oferta, ner_cv, habilidades_conocidas):
    """Habilidades requeridas y años mínimos que se mencionan en el texto de la oferta.

    Las habilidades salen del NER y de las habilidades ya encontradas en los CVs que
    aparecen escritas en la oferta.
    """
    habilidades = {}
    for e in ner_cv(oferta).ents:
        if e.label_ == 'HABILIDAD':
            valor = ' '.join(e.text.split())
            habilidades.setdefault(valor.lower(), valor)
    for valor in habilidades_conocidas:
        if contiene(oferta, valor):
            habilidades.setdefault(valor.lower(), valor)

    anios = [int(m) for m in RE_ANIOS.findall(oferta) + RE_ANIOS_MINIMO.findall(oferta)]
    return list(habilidades.values()), (min(anios) if anios else 0)


def similitudes(ofertas, textos_cv):
    """Matriz [oferta x CV] de similitud TF-IDF, convertida a una escala de 0 a 1."""
    vectorizador = TfidfVectorizer(strip_accents='unicode', lowercase=True,
                                   stop_words=PALABRAS_VACIAS, sublinear_tf=True)
    matriz = vectorizador.fit_transform(list(textos_cv) + list(ofertas))
    coseno = cosine_similarity(matriz[len(textos_cv):], matriz[:len(textos_cv)])
    return (coseno / SIMILITUD_MAXIMA).clip(0, 1)


def compatibilidad(candidato, requeridas, anios_minimos, similitud, pesos=PESOS):
    """Porcentaje de compatibilidad de un candidato con un puesto y el detalle de cada parte.

    `candidato` necesita 'habilidades', 'texto' y 'anios_experiencia'. Una habilidad cuenta
    si el NER la encontró o si aparece escrita en el CV.
    """
    propias = {h.lower() for h in candidato['habilidades']}
    tiene = [h for h in requeridas if h.lower() in propias or contiene(candidato['texto'], h)]
    faltan = [h for h in requeridas if h not in tiene]

    partes = {
        'habilidades': len(tiene) / len(requeridas) if requeridas else 1.0,
        'experiencia': min(candidato['anios_experiencia'] / anios_minimos, 1.0) if anios_minimos else 1.0,
        'similitud': float(similitud),
    }
    total = sum(pesos.values()) or 1
    porcentaje = 100 * sum(pesos[k] * partes[k] for k in partes) / total
    return {'porcentaje': round(porcentaje, 1), 'partes': partes, 'tiene': tiene, 'faltan': faltan}
