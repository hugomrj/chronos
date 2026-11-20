from datetime import date

from app.models import AnioLectivo, Colegio

TIPOS_AULA = ('regular', 'laboratorio', 'informatica', 'gimnasio', 'otro')

TIPOS_AULA_LABEL = {
    'regular': 'Aula regular',
    'laboratorio': 'Laboratorio',
    'informatica': 'Sala de informática',
    'gimnasio': 'Gimnasio',
    'otro': 'Otro',
}

DIAS_SEMANA = {
    1: 'Lunes',
    2: 'Martes',
    3: 'Miércoles',
    4: 'Jueves',
    5: 'Viernes',
    6: 'Sábado',
    7: 'Domingo',
}


def colegio_actual():
    """El colegio con el que trabaja la app (hoy, el primero)."""
    return Colegio.query.order_by(Colegio.id).first()


def anio_activo(colegio_id):
    return AnioLectivo.query.filter_by(colegio_id=colegio_id, activo=True).first()


def parse_int(value, default=None):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def parse_date(value):
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        return None
