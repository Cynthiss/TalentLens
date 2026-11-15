"""Vocabulario para generar CVs sintéticos.

Cada lista está separada en dos grupos:
- ENTRENAMIENTO: valores que pueden aparecer en los CVs de entrenamiento.
- PRUEBA: valores que solo aparecen en los CVs de prueba, para medir si el NER
  generaliza a empresas, instituciones, títulos y habilidades que nunca vio.

Ningún valor repite las empresas ni instituciones de los 20 CVs originales,
así esos CVs siguen siendo una prueba independiente.
"""

NOMBRES_MUJER = [
    'Alejandra', 'Ana Gabriela', 'Andrea', 'Beatriz', 'Carmen', 'Claudia', 'Cristina', 'Diana', 'Elena',
    'Estefanía', 'Fernanda', 'Gloria', 'Helen', 'Isabel', 'Jimena', 'Julia', 'Karen', 'Laura', 'Lourdes',
    'Marcela', 'María Fernanda', 'María Renée', 'Mariana', 'Melissa', 'Natalia', 'Paola', 'Patricia',
    'Rebeca', 'Rocío', 'Silvia', 'Susana', 'Tatiana', 'Vanessa', 'Ximena', 'Yesenia', 'Zulma',
    'Ana Belén', 'Dulce María', 'Evelyn', 'Flor de María', 'Ingrid', 'Josefina', 'Lilian', 'Nidia',
]
NOMBRES_HOMBRE = [
    'Alberto', 'Alejandro', 'Álvaro', 'Andrés', 'Antonio', 'Bryan', 'César', 'Cristian', 'Daniel', 'David',
    'Eduardo', 'Emilio', 'Erick', 'Esteban', 'Felipe', 'Francisco', 'Gerardo', 'Gustavo', 'Héctor', 'Hugo',
    'Iván', 'Jorge', 'José Manuel', 'Julio César', 'Leonel', 'Manuel', 'Mario', 'Miguel Ángel', 'Nelson',
    'Óscar', 'Pablo', 'Rafael', 'Ricardo', 'Rodrigo', 'Rubén', 'Samuel', 'Sergio', 'Walter', 'Wilson',
    'Byron', 'Edgar', 'Elmer', 'Fredy', 'Juan Carlos', 'Luis Alberto', 'Otto', 'Ronald',
]
APELLIDOS = {
    'entrenamiento': [
        'Aguilar', 'Alvarado', 'Arévalo', 'Barrios', 'Calderón', 'Cano', 'Castañeda', 'Castillo', 'Cojtí',
        'Contreras', 'Cruz', 'Chávez', 'Escobar', 'Estrada', 'Flores', 'Fuentes', 'Gálvez', 'García',
        'Girón', 'Godoy', 'Gómez', 'González', 'Guerra', 'Gutiérrez', 'Herrera', 'Hernández', 'Juárez',
        'Lemus', 'López', 'Marroquín', 'Martínez', 'Mejía', 'Méndez', 'Monroy', 'Morales', 'Muñoz',
        'Orellana', 'Ortiz', 'Pérez', 'Pineda', 'Quiñónez', 'Ramírez', 'Ramos', 'Reyes', 'Rivera',
        'Rodas', 'Rodríguez', 'Ruiz', 'Sagastume', 'Samayoa', 'Sandoval', 'Sosa', 'Tzoc', 'Velásquez',
        'Villatoro', 'Xicay', 'Yax', 'Zelada', 'Zepeda', 'Batz', 'Coc', 'Tum', 'Ajú',
    ],
    'prueba': [
        'Ambrosio', 'Bocel', 'Cifuentes', 'Culajay', 'De la Roca', 'Figueroa', 'Gramajo', 'Ixcot', 'Jerez',
        'Lima', 'Mazariegos', 'Nájera', 'Noriega', 'Obregón', 'Pac', 'Quemé', 'Recinos', 'Saquic', 'Tobar',
        'Urízar', 'Valdizón', 'Wellmann', 'Xitumul', 'Yat',
    ],
}

CIUDADES = ['Ciudad de Guatemala', 'Mixco', 'Villa Nueva', 'Quetzaltenango', 'Antigua Guatemala',
            'Escuintla', 'Cobán', 'Huehuetenango', 'Chimaltenango', 'Retalhuleu', 'Mazatenango',
            'San Marcos', 'Jalapa', 'Zacapa', 'Puerto Barrios', 'Sololá', 'Totonicapán', 'Santa Catarina Pinula',
            'Fraijanes', 'San José Pinula']

DOMINIOS_CORREO = ['gmail.com', 'yahoo.com', 'outlook.com', 'hotmail.com']

# Empresas: un tipo de negocio + un nombre propio. Los nombres propios no se comparten
# entre entrenamiento y prueba, así las empresas de prueba son nuevas para el modelo.
TIPOS_EMPRESA = ['Grupo', 'Corporación', 'Distribuidora', 'Servicios', 'Inversiones', 'Comercial',
                 'Industrias', 'Consultores', 'Agroindustrias', 'Transportes', 'Laboratorios', 'Tecnologías',
                 'Constructora', 'Hotel', 'Financiera', 'Clínicas', 'Farmacias', 'Textiles', 'Alimentos',
                 'Importadora', 'Cooperativa', 'Exportadora', 'Editorial', 'Aseguradora']
NOMBRES_EMPRESA = {
    'entrenamiento': [
        'Los Altos', 'Cuchumatanes', 'Río Dulce', 'Petén', 'Tikal', 'Izabal', 'Pacaya', 'Fuego', 'Amatitlán',
        'Mixco Viejo', 'Iximché', 'Kaminal', 'La Aurora', 'El Mirador', 'Santa Rosa', 'Lago Azul',
        'Sierra Madre', 'Monte Verde', 'Valle Central', 'Nuevo Horizonte', 'Ruta Maya', 'Cinco Volcanes',
        'Agua Clara', 'Montebello', 'Tierra Fértil', 'Sol de Oriente', 'Brisas del Mar', 'San Cristóbal',
        'La Esperanza', 'Las Américas', 'Quiriguá', 'Copán', 'Yaxhá', 'Semuc', 'Chichicastenango',
        'Rabinal', 'Zunil', 'Tecpán', 'Almolonga', 'Sacatepéquez', 'Cerro Alto', 'Plaza Mayor',
        'Punto Norte', 'Unión Central', 'Sur Andino', 'Vía Láctea', 'Bosque Nuevo', 'Cosecha Dorada',
    ],
    'prueba': [
        'Polochic', 'Motagua', 'Samalá', 'Acatenango', 'Tajumulco', 'Lachuá', 'Ixil', 'Uaxactún',
        'Barranquilla Verde', 'Puerta del Sol', 'Tres Ríos', 'Alto Pinar', 'Cielo Abierto', 'Raíces',
        'Vértice', 'Monteazul',
    ],
}
SUFIJOS_EMPRESA = ['', '', '', ' S.A.', ' GT', ' de Guatemala']

UNIVERSIDADES = {
    'entrenamiento': [
        'Universidad Panamericana', 'Universidad Mesoamericana', 'Universidad Rural de Guatemala',
        'Universidad InterNaciones', 'Universidad da Vinci de Guatemala', 'Universidad Regional de Guatemala',
        'Universidad San Pablo de Guatemala', 'Universidad de Costa Rica', 'Universidad Nacional Autónoma de Honduras',
        'Universidad Centroamericana José Simeón Cañas', 'Universidad Nacional Autónoma de México',
        'Instituto Tecnológico de Monterrey', 'Universidad de Buenos Aires', 'Universidad de Chile',
    ],
    'prueba': [
        'Universidad de los Andes', 'Pontificia Universidad Javeriana', 'Universidad de Salamanca',
        'Universidad Nacional de Colombia', 'Universidad Católica de Honduras', 'Universidad Tecnológica de Panamá',
    ],
}
COLEGIOS = {
    'entrenamiento': [
        'Colegio Monte María', 'Liceo Javier', 'Colegio Belga Guatemalteco', 'Liceo Guatemala',
        'Colegio El Prado', 'Colegio Bilingüe Vista Hermosa', 'Instituto Normal Central para Señoritas Belén',
        'Colegio Evangélico La Patria', 'Colegio Capouilliez', 'Liceo Canadiense', 'Instituto Experimental de Mixco',
        'Colegio La Salle', 'Instituto Adolfo V. Hall', 'Colegio Austriaco Guatemalteco',
    ],
    'prueba': [
        'Liceo Francés', 'Colegio Santa Teresita', 'Instituto Rafael Aqueche', 'Colegio Alemán de Guatemala',
        'Instituto Mixto de Educación Básica', 'Colegio Interamericano',
    ],
}
TITULOS_COLEGIO = ['Bachillerato en Ciencias y Letras', 'Perito Contador', 'Bachillerato en Computación',
                   'Magisterio de Educación Primaria', 'Secretariado Bilingüe', 'Perito en Administración de Empresas']

IDIOMAS = ["Inglés", "Francés", "Portugués", "Alemán", "Italiano", "K'iche'", "Kaqchikel", "Mam", "Q'eqchi'"]
NIVELES = ['básico', 'intermedio', 'avanzado']

# Profesiones: puestos (de junior a senior), títulos universitarios y habilidades.
# Los títulos y habilidades de "prueba" no aparecen en entrenamiento.
PROFESIONES = {
    'datos': {
        'puestos': ['Analista Junior de Datos', 'Analista de Datos', 'Analista de BI', 'Científico de Datos',
                    'Jefe de Analítica'],
        'perfil': 'Analista de Datos',
        'titulos': {'entrenamiento': ['Licenciatura en Estadística', 'Ingeniería en Ciencias y Sistemas',
                                      'Licenciatura en Matemática Aplicada'],
                    'prueba': ['Licenciatura en Ciencia de Datos', 'Ingeniería en Informática']},
        'posgrados': ['Maestría en Analítica de Datos', 'Maestría en Inteligencia de Negocios'],
        'habilidades': {'entrenamiento': ['Python', 'SQL', 'Power BI', 'Tableau', 'Pandas', 'Excel', 'R',
                                          'Estadística', 'Machine Learning', 'Looker Studio', 'Scikit-learn'],
                        'prueba': ['Apache Spark', 'Databricks', 'Qlik Sense', 'SPSS', 'Snowflake']},
        'tareas': ['Construcción de tableros de indicadores para gerencia',
                   'Limpieza y análisis de bases de datos de clientes',
                   'Modelos de pronóstico de ventas mensuales',
                   'Automatización de reportes semanales'],
    },
    'desarrollo': {
        'puestos': ['Desarrollador Junior', 'Desarrollador Backend', 'Desarrollador Full Stack',
                    'Desarrollador Senior', 'Líder Técnico'],
        'perfil': 'Desarrollador de Software',
        'titulos': {'entrenamiento': ['Ingeniería en Ciencias y Sistemas', 'Ingeniería en Sistemas de Información'],
                    'prueba': ['Ingeniería de Software', 'Licenciatura en Desarrollo de Software']},
        'posgrados': ['Maestría en Ingeniería de Software', 'Maestría en Ciberseguridad'],
        'habilidades': {'entrenamiento': ['Java', 'JavaScript', 'React', 'Node.js', 'Docker', 'Git', 'AWS',
                                          'PostgreSQL', 'Django', 'REST APIs', 'Linux', 'TypeScript'],
                        'prueba': ['Kubernetes', 'Go', 'Angular', 'MongoDB', 'Terraform', 'Flutter']},
        'tareas': ['Desarrollo de APIs para el sistema de pagos', 'Migración de servicios a la nube',
                   'Revisión de código y mentoría a desarrolladores junior',
                   'Optimización de consultas que redujo tiempos de respuesta'],
    },
    'contabilidad': {
        'puestos': ['Auxiliar Contable', 'Contador General', 'Auditor Interno', 'Jefe de Contabilidad',
                    'Gerente Financiero'],
        'perfil': 'Contador Público',
        'titulos': {'entrenamiento': ['Licenciatura en Contaduría Pública y Auditoría', 'Licenciatura en Finanzas'],
                    'prueba': ['Licenciatura en Economía', 'Licenciatura en Banca y Finanzas']},
        'posgrados': ['Maestría en Finanzas', 'Maestría en Administración Financiera'],
        'habilidades': {'entrenamiento': ['NIIF', 'QuickBooks', 'SAP', 'Excel', 'Auditoría', 'Contabilidad de costos',
                                          'Presupuestos', 'Conciliaciones bancarias', 'SAT Guatemala'],
                        'prueba': ['Oracle NetSuite', 'Odoo', 'Análisis financiero', 'Microsoft Dynamics']},
        'tareas': ['Elaboración de estados financieros mensuales', 'Conciliaciones bancarias y cuentas por pagar',
                   'Apoyo en auditorías externas anuales', 'Control de presupuesto por centro de costo'],
    },
    'marketing': {
        'puestos': ['Asistente de Marketing', 'Especialista en Marketing Digital', 'Community Manager',
                    'Coordinador de Marketing', 'Gerente de Marca'],
        'perfil': 'Especialista en Marketing',
        'titulos': {'entrenamiento': ['Licenciatura en Mercadeo', 'Licenciatura en Comunicación'],
                    'prueba': ['Licenciatura en Publicidad', 'Licenciatura en Relaciones Públicas']},
        'posgrados': ['Maestría en Mercadeo Digital', 'Maestría en Dirección Comercial'],
        'habilidades': {'entrenamiento': ['SEO', 'Google Ads', 'Meta Ads', 'Google Analytics', 'Canva', 'HubSpot',
                                          'Copywriting', 'Email marketing', 'Hootsuite'],
                        'prueba': ['Semrush', 'Mailchimp', 'TikTok Ads', 'Salesforce Marketing Cloud']},
        'tareas': ['Gestión de campañas pagadas en redes sociales', 'Estrategia de contenido para redes sociales',
                   'Posicionamiento del sitio web en buscadores', 'Medición de resultados de campañas'],
    },
    'rrhh': {
        'puestos': ['Asistente de Recursos Humanos', 'Analista de Reclutamiento', 'Analista de Recursos Humanos',
                    'Coordinador de Talento', 'Gerente de Recursos Humanos'],
        'perfil': 'Profesional de Recursos Humanos',
        'titulos': {'entrenamiento': ['Licenciatura en Psicología Industrial', 'Licenciatura en Administración de Recursos Humanos'],
                    'prueba': ['Licenciatura en Psicología Organizacional', 'Licenciatura en Gestión del Talento Humano']},
        'posgrados': ['Maestría en Gestión del Talento', 'Maestría en Desarrollo Organizacional'],
        'habilidades': {'entrenamiento': ['Reclutamiento y selección', 'Entrevistas por competencias', 'Nómina',
                                          'Clima laboral', 'Pruebas psicométricas', 'Excel', 'Inducción de personal'],
                        'prueba': ['Evaluación del desempeño', 'Workday', 'Legislación laboral', 'BambooHR']},
        'tareas': ['Reclutamiento de personal operativo y administrativo', 'Programas de inducción y capacitación',
                   'Gestión de planilla y prestaciones', 'Medición anual de clima laboral'],
    },
    'logistica': {
        'puestos': ['Auxiliar de Bodega', 'Analista de Logística', 'Supervisor de Logística',
                    'Coordinador de Logística', 'Gerente de Operaciones'],
        'perfil': 'Profesional de Logística',
        'titulos': {'entrenamiento': ['Licenciatura en Administración de Empresas', 'Ingeniería Industrial'],
                    'prueba': ['Licenciatura en Comercio Internacional', 'Ingeniería en Logística']},
        'posgrados': ['Maestría en Cadena de Suministro', 'Maestría en Administración de Empresas (MBA)'],
        'habilidades': {'entrenamiento': ['SAP', 'WMS', 'Gestión de inventarios', 'Cadena de suministro', 'Excel',
                                          'Importaciones', 'Compras', 'Planificación de rutas'],
                        'prueba': ['Incoterms', 'Odoo Inventario', 'Gestión aduanera', 'Lean Logistics']},
        'tareas': ['Negociación con transportistas', 'Planificación de rutas de entrega',
                   'Gestión de importaciones y trámites aduanales', 'Control de inventarios en bodega central'],
    },
    'enfermeria': {
        'puestos': ['Auxiliar de Enfermería', 'Enfermera de Emergencias', 'Enfermera Profesional',
                    'Supervisora de Enfermería', 'Jefa de Servicio'],
        'perfil': 'Enfermera Profesional',
        'titulos': {'entrenamiento': ['Licenciatura en Enfermería', 'Técnico en Enfermería'],
                    'prueba': ['Licenciatura en Nutrición', 'Licenciatura en Fisioterapia']},
        'posgrados': ['Maestría en Salud Pública', 'Especialización en Cuidados Intensivos'],
        'habilidades': {'entrenamiento': ['Primeros auxilios', 'Soporte vital básico', 'Manejo de expedientes',
                                          'Atención de emergencias', 'Farmacología', 'Toma de signos vitales'],
                        'prueba': ['Cuidados paliativos', 'Soporte vital avanzado', 'Control de infecciones']},
        'tareas': ['Atención directa a pacientes hospitalizados', 'Registro de historiales clínicos',
                   'Capacitación a personal auxiliar', 'Administración de medicamentos'],
    },
    'diseno': {
        'puestos': ['Diseñador Junior', 'Diseñador Gráfico', 'Diseñador UX/UI', 'Director de Arte',
                    'Director Creativo'],
        'perfil': 'Diseñador Gráfico',
        'titulos': {'entrenamiento': ['Licenciatura en Diseño Gráfico', 'Licenciatura en Diseño Industrial'],
                    'prueba': ['Licenciatura en Diseño Digital', 'Licenciatura en Artes Visuales']},
        'posgrados': ['Maestría en Diseño de Experiencia de Usuario', 'Maestría en Dirección de Arte'],
        'habilidades': {'entrenamiento': ['Adobe Illustrator', 'Photoshop', 'InDesign', 'Figma', 'After Effects',
                                          'Branding', 'Canva', 'Tipografía'],
                        'prueba': ['Blender', 'Procreate', 'Cinema 4D', 'Sketch']},
        'tareas': ['Diseño de identidad visual para marcas', 'Coordinación con imprentas y proveedores',
                   'Diseño de interfaces para aplicaciones móviles', 'Producción de piezas para campañas'],
    },
    'industrial': {
        'puestos': ['Asistente de Producción', 'Ingeniero de Procesos', 'Supervisor de Producción',
                    'Jefe de Mejora Continua', 'Gerente de Planta'],
        'perfil': 'Ingeniero Industrial',
        'titulos': {'entrenamiento': ['Ingeniería Industrial', 'Ingeniería Mecánica Industrial'],
                    'prueba': ['Ingeniería Química', 'Ingeniería en Producción']},
        'posgrados': ['Maestría en Gestión de Proyectos', 'Maestría en Ingeniería de la Calidad'],
        'habilidades': {'entrenamiento': ['Six Sigma', 'Lean Manufacturing', 'Minitab', 'AutoCAD',
                                          'Gestión de proyectos', 'Metodología 5S', 'Control de calidad'],
                        'prueba': ['ISO 9001', 'SolidWorks', 'Kaizen', 'MS Project']},
        'tareas': ['Reducción de desperdicios en línea de empaque', 'Supervisión de un equipo de operarios',
                   'Implementación de metodología 5S en planta', 'Control estadístico de procesos'],
    },
    'ventas': {
        'puestos': ['Asesor de Ventas', 'Ejecutivo de Cuentas', 'Supervisor de Ventas', 'Jefe de Ventas',
                    'Gerente Comercial'],
        'perfil': 'Ejecutivo Comercial',
        'titulos': {'entrenamiento': ['Licenciatura en Administración de Empresas', 'Licenciatura en Mercadeo'],
                    'prueba': ['Licenciatura en Negocios Internacionales', 'Licenciatura en Gestión Comercial']},
        'posgrados': ['Maestría en Administración de Empresas (MBA)', 'Maestría en Dirección Comercial'],
        'habilidades': {'entrenamiento': ['Negociación', 'Salesforce', 'Atención al cliente', 'Prospección',
                                          'Excel', 'Ventas consultivas', 'CRM'],
                        'prueba': ['Pipedrive', 'Zoho CRM', 'Key Account Management', 'Licitaciones']},
        'tareas': ['Cumplimiento de metas trimestrales de ventas', 'Apertura de nuevos clientes corporativos',
                   'Seguimiento de cartera de clientes', 'Elaboración de cotizaciones y propuestas'],
    },
    'legal': {
        'puestos': ['Asistente Legal', 'Abogado Junior', 'Abogado Corporativo', 'Asesor Legal',
                    'Gerente Legal'],
        'perfil': 'Abogado y Notario',
        'titulos': {'entrenamiento': ['Licenciatura en Ciencias Jurídicas y Sociales'],
                    'prueba': ['Licenciatura en Derecho Corporativo', 'Licenciatura en Relaciones Internacionales']},
        'posgrados': ['Maestría en Derecho Mercantil', 'Maestría en Derecho Tributario'],
        'habilidades': {'entrenamiento': ['Derecho mercantil', 'Contratos', 'Litigio', 'Derecho laboral',
                                          'Redacción jurídica', 'Cumplimiento normativo'],
                        'prueba': ['Propiedad intelectual', 'Arbitraje', 'Derecho tributario']},
        'tareas': ['Redacción y revisión de contratos comerciales', 'Representación en audiencias laborales',
                   'Asesoría en cumplimiento regulatorio', 'Trámites ante el Registro Mercantil'],
    },
    'educacion': {
        'puestos': ['Maestro de Primaria', 'Docente de Matemática', 'Coordinador Académico', 'Subdirector',
                    'Director de Colegio'],
        'perfil': 'Docente',
        'titulos': {'entrenamiento': ['Licenciatura en Pedagogía', 'Profesorado en Enseñanza Media'],
                    'prueba': ['Licenciatura en Educación Bilingüe', 'Licenciatura en Psicopedagogía']},
        'posgrados': ['Maestría en Docencia Universitaria', 'Maestría en Gestión Educativa'],
        'habilidades': {'entrenamiento': ['Planificación curricular', 'Google Classroom', 'Evaluación educativa',
                                          'Moodle', 'Aprendizaje basado en proyectos'],
                        'prueba': ['Educación inclusiva', 'Canvas LMS', 'Metodología Montessori']},
        'tareas': ['Planificación de clases por competencias', 'Coordinación de reuniones con padres de familia',
                   'Diseño de evaluaciones trimestrales', 'Capacitación docente en herramientas digitales'],
    },
}

TAREAS_EXTRA = ['Logro destacado: participación en el proyecto de mejora de procesos del área, coordinando con '
                'equipos de otras gerencias y presentando resultados trimestrales a la dirección.']

CURSOS = ['Curso de Excel avanzado - INTECAP', 'Diplomado en liderazgo de equipos', 'Certificación en gestión de '
          'proyectos ágiles', 'Taller de comunicación efectiva - Cámara de Comercio', 'Curso de inglés de negocios',
          'Diplomado en servicio al cliente', 'Certificación en primeros auxilios - Cruz Roja']

CARGOS_REFERENCIA = ['Gerente de Operaciones', 'Jefa de Proyectos', 'Director Administrativo', 'Gerente General',
                     'Coordinadora de Área', 'Supervisor de Turno']
TRATAMIENTOS = ['Lic.', 'Licda.', 'Ing.', 'Inga.', 'Dr.', 'Dra.']

# Encabezados de sección (todos los reconoce el separador de secciones del notebook)
ENCABEZADOS = {
    'perfil': ['Perfil', 'Perfil profesional', 'Sobre mí', 'Resumen', 'Objetivo'],
    'experiencia': ['Experiencia', 'Experiencia laboral', 'Experiencia profesional', 'Trayectoria profesional',
                    'Historial laboral'],
    'educacion': ['Educación', 'Formación', 'Formación académica', 'Preparación académica', 'Estudios'],
    'habilidades': ['Habilidades', 'Competencias', 'Aptitudes', 'Conocimientos técnicos',
                    'Herramientas y conocimientos'],
    'idiomas': ['Idiomas', 'Lenguas'],
}
ENCABEZADOS_INGLES = {'perfil': 'Profile', 'experiencia': 'Experience', 'educacion': 'Education',
                      'habilidades': 'Skills', 'idiomas': 'Languages'}
