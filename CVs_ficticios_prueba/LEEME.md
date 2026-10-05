# CVs ficticios en español para pruebas — Smart Recruiter AI

20 currículums **ficticios** (personas, correos, teléfonos y empresas inventados; las fotos son ilustraciones generadas, no personas reales). Contexto guatemalteco. Libres para usar en el proyecto.

## Contenido
- `pdf/` — 14 CVs en PDF
- `word/` — 6 CVs en Word (.docx)
- `fotos/` — las fotos ilustradas usadas en los CVs
- `etiquetas_ground_truth.csv` — la respuesta correcta de cada CV (nombre, correo, teléfono, empresas, educación, habilidades, idiomas, años de experiencia). Sirve para medir precisión y recall del sistema.

## Formatos incluidos
| Formato | CVs | Qué pone a prueba |
|---|---|---|
| Clásico, solo texto | cv_01, cv_06, cv_20 | Caso base. cv_20 pone Educación antes que Experiencia |
| Moderno con barra lateral y foto (estilo Canva) | cv_02, cv_09, cv_15 | Dos columnas: el texto extraído puede salir mezclado |
| Creativo con banner, foto y barras de habilidad | cv_05, cv_11, cv_18 | Encabezados en inglés ("Skills"), dos columnas |
| Tabla con etiquetas a la izquierda | cv_03, cv_13 | Secciones dentro de una tabla |
| Escaneado (imagen, sin texto) | cv_07, cv_16 | Requiere OCR (p. ej., pytesseract) |
| Varias páginas (3) con cursos y referencias | cv_10 | Nombres de referencias que NO son el candidato |
| Word sencillo | cv_04, cv_14 | cv_14 no tiene sección de habilidades (están en el texto) |
| Word con foto y tablas | cv_08, cv_17 | Tablas en .docx; cv_17 no tiene perfil |
| Word con encabezados poco comunes | cv_12, cv_19 | "Trayectoria profesional", experiencia en prosa |

## Otras variaciones deliberadas
- Cuatro formatos de fecha distintos: `mar 2021`, `03/2021`, `Marzo de 2021`, `2021`; y "actualidad", "a la fecha", "presente", "actual" para el trabajo vigente.
- Nombres de sección distintos según el formato (Experiencia / Trayectoria / Historial laboral…).
- cv_07 no tiene correo electrónico.
- Años de experiencia calculados con fecha de referencia septiembre 2026.
