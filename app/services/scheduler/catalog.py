"""Catálogo de reglas que entiende el motor de generación.

Cada código define el texto que ve el usuario y los parámetros esperados.
El motor (Sprint 5) leerá estos códigos para construir las restricciones.
"""

REGLAS_CATALOGO = {
    'ANTES_DE_RECESO': {
        'nombre': 'Antes del receso',
        'descripcion': 'Ubicar la materia antes del primer receso del día.',
        'obligatoria_sugerida': False,
        'peso_sugerido': 50,
        'parametros': {},
        'ayuda': 'Sin parámetros.',
    },
    'NO_ULTIMA_HORA': {
        'nombre': 'Evitar última hora',
        'descripcion': 'Evitar que la materia quede en el último bloque del día.',
        'obligatoria_sugerida': False,
        'peso_sugerido': 40,
        'parametros': {},
        'ayuda': 'Sin parámetros.',
    },
    'DISTRIBUIR_SEMANA': {
        'nombre': 'Distribuir en la semana',
        'descripcion': 'Repartir las horas de la materia a lo largo de la semana.',
        'obligatoria_sugerida': True,
        'peso_sugerido': 10,
        'parametros': {'max_por_dia': 1},
        'ayuda': 'Opcional: {"max_por_dia": 1}.',
    },
    'EVITAR_HUECOS_PROFESOR': {
        'nombre': 'Evitar huecos del profesor',
        'descripcion': 'Evitar horas libres entre las clases de un profesor.',
        'obligatoria_sugerida': False,
        'peso_sugerido': 30,
        'parametros': {'max_huecos': 1},
        'ayuda': 'Opcional: {"max_huecos": 1}.',
    },
    'MAX_HORAS_DIA_PROFESOR': {
        'nombre': 'Máximo de horas diarias',
        'descripcion': 'Limitar la cantidad de horas que un profesor dicta por día.',
        'obligatoria_sugerida': False,
        'peso_sugerido': 20,
        'parametros': {'horas': 6},
        'ayuda': 'Opcional: {"horas": 6}.',
    },
}

REGLAS_POR_CODIGO = REGLAS_CATALOGO
