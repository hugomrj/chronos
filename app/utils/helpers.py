from datetime import date, time

from flask import has_request_context, session

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
    """Colegio activo de la sesión; si no hay, el primero disponible."""
    if has_request_context():
        colegio_id = session.get('colegio_id')
        if colegio_id:
            colegio = db.session.get(Colegio, colegio_id)
            if colegio:
                return colegio

    colegio = Colegio.query.order_by(Colegio.id).first()
    if colegio and has_request_context():
        session['colegio_id'] = colegio.id
    return colegio


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
