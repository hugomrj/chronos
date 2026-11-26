"""Colegio activo de la instancia.

Cada instancia sirve un colegio (COLEGIO_ID del .env).
"""
from flask import current_app

from app.extensions import db
from app.models import AnioLectivo, Colegio


def colegio_actual():
    """Colegio que se está administrando en esta petición."""
    colegio_id = current_app.config.get('COLEGIO_ID') or 0
    if colegio_id:
        return db.session.get(Colegio, colegio_id)

    return Colegio.query.order_by(Colegio.id).first()


def colegios_visibles():
    """La instancia sirve un único colegio."""
    actual = colegio_actual()
    return [actual] if actual else []


def anio_activo(colegio_id):
    return AnioLectivo.query.filter_by(colegio_id=colegio_id, activo=True).first()
