from datetime import date, time

from flask import current_app

from app.extensions import db
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
    """Colegio que sirve esta instancia (COLEGIO_ID del .env).

    Si la instancia no tiene COLEGIO_ID, en desarrollo se usa el primer
    colegio de la base para no bloquear el trabajo local.
    """
    colegio_id = current_app.config.get('COLEGIO_ID') or 0
    if colegio_id:
        return db.session.get(Colegio, colegio_id)

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


def parse_time(value):
    """Acepta 'HH:MM' (input time) y devuelve datetime.time."""
    if not value:
        return None
    try:
        return time.fromisoformat(value)
    except (TypeError, ValueError):
        return None


def hhmm(value):
    return value.strftime('%H:%M') if value else ''


def rango_horario(desde, hasta):
    return f'{hhmm(desde)} – {hhmm(hasta)}'


def is_safe_url(target):
    """Solo permite redirecciones internas (evita open redirect)."""
    from urllib.parse import urljoin, urlparse
    from flask import request

    if not target:
        return False
    ref = urlparse(request.host_url)
    test = urlparse(urljoin(request.host_url, target))
    return test.scheme in ('http', 'https') and ref.netloc == test.netloc
