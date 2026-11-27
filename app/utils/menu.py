"""Menú del sistema por rol.

Cada ítem tiene una clave estable, una etiqueta y las rutas que protege.
El rol `master` ve todo y no se puede limitar.
Los demás roles ven los ítems cargados en `rol_menu`.
"""

MENU_ITEMS = [
    # (clave, etiqueta, grupo, prefijos de ruta)
    ('anios', 'Años lectivos', 'Estructura', ('/anios',)),
    ('niveles', 'Niveles', 'Estructura', ('/niveles',)),
    ('especialidades', 'Especialidades', 'Estructura', ('/especialidades',)),
    ('grados', 'Grado / Curso', 'Estructura', ('/grados',)),
    ('areas', 'Áreas', 'Estructura', ('/areas',)),
    ('materias', 'Materias', 'Estructura', ('/materias',)),
    ('planes', 'Planes', 'Estructura', ('/planes',)),
    ('turnos', 'Turnos', 'Estructura', ('/turnos',)),
    ('aulas', 'Aulas', 'Estructura', ('/aulas',)),
    ('profesores', 'Profesores', 'Profesores', ('/profesores',)),
    ('disponibilidad', 'Disponibilidad', 'Profesores', ('/disponibilidad',)),
    ('plantillas', 'Estructura de horarios', 'Planificación', ('/plantillas',)),
    ('secciones', 'Secciones y plan', 'Planificación', ('/secciones',)),
    ('reglas', 'Reglas', 'Planificación', ('/reglas',)),
    ('horarios', 'Horarios', 'Planificación', ('/horarios',)),
    ('reportes', 'Reportes', 'Planificación',
     ('/reportes', '/reportes/distribucion')),
    ('usuarios', 'Usuarios', 'Sistema', ('/usuarios',)),
    ('configuracion', 'Configuración', 'Sistema', ('/configuracion',)),
    ('roles', 'Roles y menú', 'Sistema', ('/roles',)),
]

MENU_KEYS = [item[0] for item in MENU_ITEMS]
MENU_POR_CLAVE = {item[0]: item for item in MENU_ITEMS}

# Ningún ítem es obligatorio: todos se pueden habilitar o quitar por rol.

# Ítems habilitados por defecto para un rol nuevo.
ITEMS_POR_DEFECTO = [
    'anios', 'niveles', 'especialidades', 'grados', 'areas', 'materias',
    'planes', 'profesores', 'disponibilidad', 'plantillas', 'secciones',
    'reglas', 'horarios', 'reportes',
]


def item_de_ruta(path):
    """Devuelve la clave de menú que corresponde a una ruta."""
    candidato = None
    for clave, _etiqueta, _grupo, prefijos in MENU_ITEMS:
        for prefijo in prefijos:
            if path == prefijo or path.startswith(prefijo + '/'):
                if candidato is None or len(prefijo) > len(candidato[1]):
                    candidato = (clave, prefijo)
    return candidato[0] if candidato else None


def items_por_grupo():
    """Agrupa los ítems para dibujar el formulario de configuración."""
    grupos = {}
    for clave, etiqueta, grupo, _prefijos in MENU_ITEMS:
        grupos.setdefault(grupo, []).append((clave, etiqueta))
    return grupos
