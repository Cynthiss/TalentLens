# TalentLens

Extracción inteligente de información de CVs para agilizar la preselección de candidatos.

El reclutador define los **puestos** que tiene abiertos, sube uno o varios CVs en PDF o Word y obtiene una **tabla comparativa** con la información clave de cada candidato, extraída automáticamente con PLN (nombre, contacto, años de experiencia, empresas, educación y habilidades), junto con su **% de compatibilidad con cada puesto**.

> TalentLens no reemplaza al reclutador: ordena la información para acelerar la revisión inicial.

Proyecto final del curso de Procesamiento de Lenguaje Natural — Cynthia Santos (20230493).

## El problema

Una oferta de empleo recibe en promedio unos 250 CVs y el primer vistazo de un reclutador dura unos 7 segundos. Cada CV tiene un formato distinto (una o dos columnas, tablas, escaneados, encabezados diferentes), lo que hace lento compararlos. Como un CV es texto libre sin estructura fija, las reglas fijas fallan con cada formato; el PLN permite identificar la información por su contexto.

## Cómo funciona

```
CV (PDF / Word) → Captura de texto → Limpieza → Secciones → Extracción → Compatibilidad con los puestos → Tabla comparativa
```

1. **Captura.** Texto de PDF con `pymupdf` y de Word con `python-docx` (incluyendo tablas). Si una página no tiene texto (CV escaneado) se lee con OCR (`pytesseract`, español).
2. **Limpieza.** Normalización unicode (NFKC, que también separa ligaduras tipográficas como `ﬁ`) y de espacios, eliminación de viñetas, unión de correos partidos en dos líneas y reparación de la `@` mal leída por el OCR.
3. **Secciones.** Un diccionario de sinónimos agrupa los encabezados de cada CV (Experiencia / Trayectoria / Historial laboral, Habilidades / Skills / Aptitudes...), incluso cuando el encabezado está partido en dos líneas.
4. **Extracción.**
   - **Correo y teléfono:** expresiones regulares.
   - **Nombre:** NER preentrenado de spaCy (`es_core_news_sm`) + reglas, ignorando las secciones donde aparecen otras personas (referencias).
   - **Años de experiencia:** lectura de rangos de fechas en cuatro formatos (`mar 2021`, `03/2021`, `Marzo de 2021`, `2021`), sin contar dos veces los periodos que se traslapan.
   - **Empresas, títulos, instituciones y habilidades:** NER de spaCy **entrenado con etiquetas propias** (`EMPRESA`, `TITULO`, `INSTITUCION`, `HABILIDAD`).
5. **Compatibilidad con los puestos.** De la oferta de cada puesto se sacan las habilidades requeridas (NER + habilidades conocidas escritas en la oferta) y los años mínimos ("al menos 3 años de experiencia"). El % de cada candidato combina tres partes, con pesos ajustables:
   - **Habilidades (50%):** cuántas de las requeridas tiene; cuenta si el NER la encontró o si aparece escrita en el CV.
   - **Experiencia (20%):** sus años frente a los mínimos (100% si los cumple), multiplicado por qué tan relacionado está el perfil (el mayor entre habilidades y similitud). Así, muchos años en otra área no hacen compatible a alguien.
   - **Similitud con la oferta (30%):** TF-IDF + similitud coseno entre el texto del CV y la oferta; capta funciones y sector aunque no sean habilidades. Una similitud de 0.35 cuenta como 100%.

   Cada candidato se asigna al puesto con el que tiene mayor %, solo si llega al **21%**; si no, queda **sin puesto**.
6. **Producto.** App de Streamlit con dos páginas (Puestos y Candidatos), clasificación por puesto, filtros y descarga en CSV.

## Datos

Todos los CVs son **ficticios** y en español, con contexto guatemalteco: personas, correos, teléfonos y empresas inventados.

- **`CVs_ficticios_prueba/` — 20 CVs originales** (14 PDF y 6 Word) con formatos variados a propósito: clásico, dos columnas con foto, creativo, tablas, escaneados, varias páginas con referencias y encabezados poco comunes.
- **`CVs_sinteticos/` — 200 CVs del dataset ampliado**, creados con `generador/generar_cvs.py` en los mismos 9 formatos, con fechas, encabezados y separadores variados:
  - **160 de entrenamiento.**
  - **40 de prueba** que usan empresas, instituciones, títulos y habilidades que **no aparecen** en entrenamiento (92 empresas, 12 instituciones y 42 habilidades nuevas), para medir si el NER generaliza.
  - No repiten empresas ni instituciones de los 20 originales.

Cada carpeta tiene un `etiquetas_ground_truth.csv` con la respuesta correcta de cada CV. Se usa para:
- **Generar las anotaciones del NER:** cada valor del CSV se busca en el texto del CV y se marca su posición (no se etiquetó a mano).
- **Evaluar** el sistema campo por campo.

El primer NER se entrenó con 14 CVs originales y se evaluó con 6 (uno de cada formato). Como los originales repiten las mismas empresas y habilidades, el modelo memorizaba; por eso se amplió el dataset y se reentrenó con los 160 sintéticos más los 14 originales.

## Resultados

**Campos con reglas (20 CVs originales)**

| Campo | Resultado |
|---|---|
| Nombre | 100% correctos |
| Correo | 100% correctos |
| Teléfono | 100% correctos |
| Años de experiencia | 80% exactos, error promedio de 0.09 años |

En los 200 CVs sintéticos: nombre 99.5%, correo 98.5%, teléfono 100% y error promedio de 0.17 años. Los errores restantes vienen sobre todo del OCR de los escaneados y de fechas que solo traen el año.

**NER reentrenado con el dataset ampliado**

| Conjunto de prueba | Modelo inicial (14 CVs) | Reentrenado (174 CVs) |
|---|---|---|
| 40 CVs sintéticos con valores nuevos | F1 0.61 | **F1 0.89** |
| 6 CVs originales de prueba | F1 0.92 | **F1 0.95** |

Con valores que nunca vio en entrenamiento, el modelo reentrenado encuentra el **79%** (285 de 359); el modelo inicial encontraba 1 de 4.

**Clasificación por puesto (40 CVs sintéticos de prueba)**

Con tres puestos de ejemplo (Analista de Datos, Desarrollador Backend y Contador General), 10 de los 40 CVs son de profesiones relacionadas (2 de datos, 5 de desarrollo y 3 de contabilidad). Con el umbral de 21%, la app asignó los 10 **al puesto de su profesión**. Los 30 CVs de otras profesiones (marketing, enfermería, docencia...) sacaron 17% o menos y quedaron **sin puesto**.

El umbral se eligió con una función de valor por vacante: horas del reclutador ahorradas menos el costo de perder candidatos calificados. En 660 pares CV-puesto, 21% es el punto de mayor valor: no se pierde ningún calificado y solo pasa el 1.3% de los demás.

Con los CVs reales: la estudiante de Ingeniería en Computer Science quedó como Analista de Datos (52%) y la de Contaduría y Auditoría como Contador General (31%); las otras dos, de marketing y operaciones, quedaron sin puesto.

| Campo (40 sintéticos de prueba) | Precisión | Recall | F1 |
|---|---|---|---|
| Empresas | 1.00 | 1.00 | 1.00 |
| Títulos | 1.00 | 0.99 | 0.99 |
| Instituciones | 0.82 | 0.82 | 0.82 |
| Habilidades | 0.93 | 0.68 | 0.79 |

**NER inicial (6 CVs originales de prueba)**

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

- **Datos sintéticos.** El dataset ampliado redujo la memorización (recall con valores nuevos de 0.25 a 0.79), pero los CVs siguen siendo generados con plantillas. Los CVs reales tienen más variedad de redacción y formato, así que el desempeño con ellos probablemente sería menor. El siguiente paso es evaluar con CVs reales anonimizados.
- **Habilidades nuevas.** Es la entidad más difícil: el modelo reentrenado encuentra el 68% de las habilidades de prueba. Las empresas son más fáciles porque casi siempre empiezan con un tipo de negocio conocido ("Grupo", "Distribuidora"...).
- **Fechas solo con año.** Si el CV dice "2022 - 2026" sin mes, se asume julio; ese error no se puede eliminar.
- **Errores visibles del NER.** A veces confunde un puesto con una empresa o habilidad (por ejemplo "Auditora Interna") o marca un apellido como habilidad. La app muestra las entidades resaltadas para que el reclutador pueda revisarlas.
- **Compatibilidad.** La escala de similitud (0.35 = 100%) y el umbral de 21% se calibraron con los CVs sintéticos; con CVs reales habría que revisarlos. El % no mide la calidad de la experiencia, solo qué tanto coincide el CV con la oferta.
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

Se abre en http://localhost:8501 con dos páginas en el menú lateral.

**1. Puestos:** los puestos que tienes abiertos.
- **Agregar un puesto:** escribe el nombre, pega la oferta de empleo y presiona **Analizar oferta**. TalentLens detecta las habilidades y los años mínimos; puedes quitar o escribir habilidades antes de **Guardar puesto**.
- **Puestos guardados:** cada puesto muestra sus requisitos y se puede ver la oferta, editar o eliminar.
- **¿Cómo se calcula el % de compatibilidad?:** explica el cálculo y permite cambiar el peso de cada parte.
- Los puestos y los pesos se guardan en `puestos.json`, así que siguen ahí al volver a abrir la app. El repo incluye tres puestos de ejemplo.

**2. Candidatos:** sube CVs sueltos o **una carpeta completa** (se leen todos los PDF y Word, también de subcarpetas). Puedes probar con `CVs_ficticios_prueba/` o `CVs_sinteticos/`. Los CVs subidos se conservan al cambiar de página.
- **Filtros** en la barra lateral: puesto, compatibilidad mínima y, en **Más filtros**, habilidades (basta con tener **al menos una**), años mínimos de experiencia y búsqueda por nombre, empresa o título.
- **Clasificación por puesto:** cuántos candidatos encajan en cada puesto, una tabla con el % de cada candidato para cada puesto (descargable en CSV) y el ranking de cada puesto con las habilidades que tiene ✓ y las que le faltan ✗.
- **Candidatos:** tarjetas con educación, empresas, contacto, habilidades y su puesto más compatible.
- **Tabla comparativa:** toda la información extraída más el puesto más compatible y su %; **Descargar tabla (CSV)** exporta el resultado.
- **Resumen:** habilidades más frecuentes y años de experiencia por candidato.
- **Detalle NER:** el texto de cada CV con las entidades que encontró el modelo, para revisar la extracción.

En la app, "actualidad" se calcula con la fecha de hoy; en el notebook se usa septiembre 2026 para coincidir con el CSV de respuestas.

**Notebook**

`TalentLens.ipynb` recorre todo el proceso con el kernel **Python (TalentLens)**: captura, limpieza, extracción, entrenamiento del NER, evaluación y, en la sección 5, el reentrenamiento con el dataset ampliado (unos 4 minutos en total). Al final guarda el modelo reentrenado en `modelo_ner/`, que es el que usa la app.

**Generar el dataset ampliado**

```bash
.venv/bin/python generador/generar_cvs.py --entrenamiento 160 --prueba 40
```

Usa una semilla fija (`--semilla 2026`), así que vuelve a crear los mismos CVs y respuestas en `CVs_sinteticos/` (solo el ruido de los escaneados cambia un poco).

## Estructura

```
TalentLens/
├── TalentLens.ipynb         # proceso completo: captura, limpieza, NER, evaluación y reentrenamiento
├── extractor.py             # pipeline usado por la app
├── app.py                   # app de Streamlit (menú con las dos páginas)
├── paginas/                 # candidatos.py y puestos.py
├── comun.py                 # piezas compartidas: modelos, puestos guardados y cálculo de compatibilidad
├── compatibilidad.py        # requisitos de una oferta y % de compatibilidad CV-puesto
├── puestos.json             # puestos disponibles y pesos del cálculo
├── modelo_ner/              # NER reentrenado (EMPRESA, TITULO, INSTITUCION, HABILIDAD)
├── generador/               # generador de CVs sintéticos y su vocabulario
├── requirements.txt
├── CVs_ficticios_prueba/    # 20 CVs originales y respuestas correctas
└── CVs_sinteticos/          # 200 CVs del dataset ampliado y respuestas correctas
```

## Próximas versiones

- Evaluar con CVs reales anonimizados.
- Calibrar la escala de similitud y el umbral de 21% con más CVs y ofertas reales.
