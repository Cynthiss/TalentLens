# TalentLens

Extracción inteligente de información de CVs para agilizar la preselección de candidatos.

El reclutador sube uno o varios CVs en PDF o Word y obtiene una **tabla comparativa** con la información clave de cada candidato, extraída automáticamente con PLN: nombre, contacto, años de experiencia, empresas, educación y habilidades.

> TalentLens no reemplaza al reclutador: ordena la información para acelerar la revisión inicial.

Proyecto final del curso de Procesamiento de Lenguaje Natural — Cynthia Santos (20230493).

## El problema

Una oferta de empleo recibe en promedio unos 250 CVs y el primer vistazo de un reclutador dura unos 7 segundos. Cada CV tiene un formato distinto (una o dos columnas, tablas, escaneados, encabezados diferentes), lo que hace lento compararlos. Como un CV es texto libre sin estructura fija, las reglas fijas fallan con cada formato; el PLN permite identificar la información por su contexto.

## Cómo funciona

```
CV (PDF / Word) → Captura de texto → Limpieza → Secciones → Extracción → Tabla comparativa
```

1. **Captura.** Texto de PDF con `pymupdf` y de Word con `python-docx` (incluyendo tablas). Si una página no tiene texto (CV escaneado) se lee con OCR (`pytesseract`, español).
2. **Limpieza.** Normalización unicode y de espacios, eliminación de viñetas, unión de correos partidos en dos líneas y reparación de la `@` mal leída por el OCR.
3. **Secciones.** Un diccionario de sinónimos agrupa los encabezados de cada CV (Experiencia / Trayectoria / Historial laboral, Habilidades / Skills / Aptitudes...).
4. **Extracción.**
   - **Correo y teléfono:** expresiones regulares.
   - **Nombre:** NER preentrenado de spaCy (`es_core_news_sm`) + reglas, ignorando las secciones donde aparecen otras personas (referencias).
   - **Años de experiencia:** lectura de rangos de fechas en cuatro formatos (`mar 2021`, `03/2021`, `Marzo de 2021`, `2021`), sin contar dos veces los periodos que se traslapan.
   - **Empresas, títulos, instituciones y habilidades:** NER de spaCy **entrenado con etiquetas propias** (`EMPRESA`, `TITULO`, `INSTITUCION`, `HABILIDAD`).
5. **Producto.** App de Streamlit con tabla comparativa, filtros y descarga en CSV.

## Datos

20 CVs **ficticios** en español con contexto guatemalteco (`CVs_ficticios_prueba/`): 14 en PDF y 6 en Word, con formatos variados a propósito (clásico, dos columnas con foto, creativo, tablas, escaneados, varias páginas con referencias, encabezados poco comunes). Las personas, correos, teléfonos y empresas son inventados.

`etiquetas_ground_truth.csv` tiene la respuesta correcta de cada CV. Se usa para:
- **Generar las anotaciones del NER:** cada valor del CSV se busca en el texto del CV y se marca su posición (no se etiquetó a mano).
- **Evaluar** el sistema campo por campo.

El NER se entrena con 14 CVs y se evalúa con 6 (uno de cada tipo de formato).

## Resultados

**Campos con reglas (20 CVs)**

| Campo | Resultado |
|---|---|
| Nombre | 100% correctos |
| Correo | 100% correctos |
| Teléfono | 100% correctos |
| Años de experiencia | 80% exactos, error promedio de 0.09 años |

**NER ajustado (6 CVs de prueba)**

| Campo | Precisión | Recall | F1 |
|---|---|---|---|
| Empresas | 0.92 | 0.92 | 0.92 |
| Títulos | 0.93 | 1.00 | 0.96 |
| Instituciones | 1.00 | 1.00 | 1.00 |
| Habilidades | 0.88 | 0.94 | 0.91 |

**Comparación con el NER preentrenado sin ajustar** (`ORG` como empresa, `MISC` como habilidad)

| Campo | F1 preentrenado | F1 ajustado |
|---|---|---|
| Empresas | 0.06 | 0.92 |
| Habilidades | 0.23 | 0.91 |

## Limitaciones

- **El NER memoriza más de lo que generaliza.** Los CVs ficticios repiten las mismas empresas y habilidades: 69 de las 73 entidades de prueba ya aparecían en entrenamiento. Con esas el recall es 0.97, pero con valores nuevos solo encontró 1 de 4. Con CVs reales y más variados el desempeño sería menor.
- **Pocos datos y ficticios.** 20 CVs alcanzan para demostrar el flujo completo, no para un modelo de producción.
- **Fechas solo con año.** Si el CV dice "2022 - 2026" sin mes, se asume julio; ese error no se puede eliminar.
- **Errores visibles del NER.** A veces confunde un puesto con una empresa o habilidad (por ejemplo "Auditora Interna") o marca un apellido como habilidad. La app muestra las entidades resaltadas para que el reclutador pueda revisarlas.
- **Teléfonos.** La expresión regular está pensada para números de Guatemala (`+502 XXXX-XXXX`).

## Instalación

Requisitos: Python 3.13 y [Homebrew](https://brew.sh) (macOS) para Tesseract.

1. Clonar el repo:

```bash
git clone https://github.com/Cynthiss/TalentLens.git
```

```bash
cd TalentLens
```

2. Instalar Tesseract con el idioma español (para los CVs escaneados):

```bash
brew install tesseract tesseract-lang
```

3. Crear el entorno virtual e instalar las dependencias:

```bash
python3 -m venv .venv
```

```bash
.venv/bin/pip install -r requirements.txt
```

```bash
.venv/bin/python -m spacy download es_core_news_sm
```

4. (Opcional) Registrar el kernel para el notebook:

```bash
.venv/bin/python -m ipykernel install --user --name talentlens --display-name "Python (TalentLens)"
```

> Las versiones de `cymem`, `murmurhash`, `preshed` y `srsly` están fijas en `requirements.txt` porque versiones más nuevas no cargan modelos de spaCy guardados.

## Uso

**App**

```bash
.venv/bin/streamlit run app.py
```

Se abre en http://localhost:8501. Sube uno o varios CVs (puedes probar con los de `CVs_ficticios_prueba/`):

- La tabla muestra a los candidatos ordenados por años de experiencia.
- En la barra lateral se filtra por habilidades requeridas y años mínimos.
- **Descargar tabla (CSV)** exporta el resultado.
- **Detalle por candidato** muestra el texto del CV con las entidades que encontró el NER.

En la app, "actualidad" se calcula con la fecha de hoy; en el notebook se usa septiembre 2026 para coincidir con el CSV de respuestas.

**Notebook**

`TalentLens.ipynb` recorre todo el proceso con el kernel **Python (TalentLens)**: captura, limpieza, extracción, entrenamiento del NER y evaluación. Al final guarda el modelo en `modelo_ner/`, que es el que usa la app.

## Estructura

```
TalentLens/
├── TalentLens.ipynb         # proceso completo: captura, limpieza, NER y evaluación
├── extractor.py             # pipeline usado por la app
├── app.py                   # app de Streamlit
├── modelo_ner/              # NER entrenado (EMPRESA, TITULO, INSTITUCION, HABILIDAD)
├── requirements.txt
└── CVs_ficticios_prueba/    # 20 CVs de prueba y respuestas correctas
```

## Próximas versiones

- Comparar cada CV con la oferta laboral y calcular un porcentaje de compatibilidad.
- Entrenar con CVs reales (anonimizados) y más variados para que el NER generalice a empresas y habilidades nuevas.
