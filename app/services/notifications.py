from flask import url_for

from app.models import (
    HorarioVersion, Profesor, Seccion, SeccionMateria, Turno,
)
from app.utils.helpers import anio_activo


def obtener_avisos(colegio):
    """Avisos actuales del colegio para el dashboard y la campana."""
    avisos = []
    if not colegio:
        return avisos

    anio = anio_activo(colegio.id)
    if not anio:
        avisos.append({
            'tipo': 'warn',
            'titulo': 'Sin año lectivo activo',
            'texto': 'Activá un año lectivo para empezar a planificar.',
            'url': url_for('anios'),
        })
        return avisos

    secciones = Seccion.query.filter_by(anio_lectivo_id=anio.id).all()
    seccion_ids = [s.id for s in secciones]
    con_plan = set()
    if seccion_ids:
        con_plan = {
            row[0] for row in (
                SeccionMateria.query
                .with_entities(SeccionMateria.seccion_id)
                .filter(SeccionMateria.seccion_id.in_(seccion_ids))
                .distinct()
                .all()
            )
        }
    sin_plan = len([s for s in secciones if s.id not in con_plan])
    if sin_plan:
        avisos.append({
            'tipo': 'warn',
            'titulo': 'Secciones sin plan',
            'texto': f'{sin_plan} sección(es) no tienen materias cargadas.',
            'url': url_for('secciones'),
        })

    sin_disponibilidad = Profesor.query.filter_by(
        colegio_id=colegio.id, activo=True
    ).filter(~Profesor.disponibilidad.any()).count()
    if sin_disponibilidad:
        avisos.append({
            'tipo': 'info',
            'titulo': 'Profesores sin disponibilidad',
            'texto': f'{sin_disponibilidad} profesor(es) no tienen franjas cargadas.',
            'url': url_for('disponibilidad'),
        })

    turnos_con_secciones = {
        s.turno_id for s in secciones
    }
    turnos_sin_publicar = []
    if turnos_con_secciones:
        publicados = {
            v.turno_id for v in HorarioVersion.query.filter_by(
                anio_lectivo_id=anio.id, estado='publicado'
            ).all()
        }
        turnos_sin_publicar = [
            t for t in Turno.query.filter(
                Turno.id.in_(turnos_con_secciones)
            ).order_by(Turno.nombre).all()
            if t.id not in publicados
        ]
    if turnos_sin_publicar:
        avisos.append({
            'tipo': 'info',
            'titulo': 'Horarios sin publicar',
            'texto': 'Turnos pendientes: ' + ', '.join(
                t.nombre for t in turnos_sin_publicar),
            'url': url_for('horarios'),
        })

    return avisos


def contar_avisos(colegio):
    return len(obtener_avisos(colegio))
