from collections import defaultdict

from flask import redirect, render_template, url_for
from flask_login import login_required
from sqlalchemy import text

from app.extensions import db
from app.models import (
    HorarioCelda, HorarioVersion, Profesor, Seccion, SeccionMateria, Turno,
)
from app.services.notifications import obtener_avisos
from app.utils.helpers import DIAS_SEMANA, anio_activo, colegio_actual

DIAS_ESCOLARES = [d for d in DIAS_SEMANA if d <= 5]


def _metricas(colegio, anio):
    """Recorre el borrador/publicado más reciente de cada turno y calcula KPIs."""
    datos = {
        'horas_plan': 0,
        'horas_asignadas': 0,
        'carga_profesor': [],
        'ocupacion_aula': [],
        'carga_materia': [],
        'carga_por_dia': [],
        'sin_plan': 0,
        'secciones_total': 0,
        'profesores_sin_disponibilidad': 0,
        'profesores_total': 0,
        'alerta': None,
    }

    if not anio:
        return datos

    secciones = Seccion.query.filter_by(anio_lectivo_id=anio.id).all()
    datos['secciones_total'] = len(secciones)

    plan_por_seccion = {}
    for sm in SeccionMateria.query.filter(
            SeccionMateria.seccion_id.in_([s.id for s in secciones])).all():
        plan_por_seccion[sm.seccion_id] = plan_por_seccion.get(sm.seccion_id, 0) + sm.horas_semanales

    datos['horas_plan'] = sum(plan_por_seccion.values())
    datos['sin_plan'] = sum(1 for s in secciones
                            if plan_por_seccion.get(s.id, 0) == 0)

    versiones = HorarioVersion.query.filter_by(
        anio_lectivo_id=anio.id
    ).order_by(HorarioVersion.creado_en.desc()).all()

    # Una versión representativa por turno: la publicada, o el último borrador.
    elegidas = {}
    for v in versiones:
        actual = elegidas.get(v.turno_id)
        if actual is None:
            elegidas[v.turno_id] = {
                'turno_id': v.turno_id,
                'version': v,
                'publicado': v.estado == 'publicado',
            }
        elif v.estado == 'publicado' and not actual['publicado']:
            elegidas[v.turno_id] = {
                'turno_id': v.turno_id,
                'version': v,
                'publicado': True,
            }

    ids_version = [e['version'].id for e in elegidas.values() if e['version']]
    if not ids_version:
        datos['carga_profesor'] = [
            {'nombre': p.nombre, 'horas': 0, 'maximo': p.horas_max_semana}
            for p in Profesor.query.filter_by(colegio_id=colegio.id, activo=True)
                                   .order_by(Profesor.nombre).limit(8)
        ]
        datos['alerta'] = ('Sin horarios generados',
                           'Generá un horario para ver la carga docente y la ocupación de aulas.')
        return datos

    # Cada bloque del día solo puede ocuparse una vez por sección/turno, así que
    # contar las celdas de la versión vigente de cada turno es correcto.
    celdas = HorarioCelda.query.filter(
        HorarioCelda.version_id.in_(ids_version)).all()

    datos['horas_asignadas'] = len(celdas)
    if not celdas:
        datos['alerta'] = ('Sin bloques asignados',
                           'Las versiones existentes todavía no tienen celdas asignadas.')

    por_profesor = defaultdict(int)
    por_aula = defaultdict(int)
    por_materia = defaultdict(int)
    por_dia = defaultdict(int)
    aulas_nombres = {}
    materias_nombres = {}

    for c in celdas:
        if c.profesor_id:
            por_profesor[c.profesor_id] += 1
        if c.aula_id:
            por_aula[c.aula_id] += 1
            if c.aula:
                aulas_nombres[c.aula_id] = c.aula.nombre
        sm = c.seccion_materia
        if sm:
            por_materia[sm.materia_id] += 1
            if sm.materia:
                materias_nombres[sm.materia_id] = sm.materia.nombre
        por_dia[c.dia_semana] += 1

    profesores = {p.id: p for p in Profesor.query.filter_by(
        colegio_id=colegio.id, activo=True).all()}
    datos['profesores_total'] = len(profesores)
    datos['profesores_sin_disponibilidad'] = sum(
        1 for p in profesores.values() if not p.disponibilidad)

    datos['carga_profesor'] = sorted(
        [{'nombre': p.nombre, 'horas': por_profesor.get(pid, 0),
          'maximo': p.horas_max_semana}
         for pid, p in profesores.items()],
        key=lambda x: -x['horas'],
    )[:8]

    datos['ocupacion_aula'] = sorted(
        [{'nombre': aulas_nombres.get(aid, f'Aula {aid}'), 'horas': h}
         for aid, h in por_aula.items()],
        key=lambda x: -x['horas'],
    )[:8]

    total_materias = sum(por_materia.values()) or 1
    datos['carga_materia'] = sorted(
        [{'nombre': materias_nombres.get(mid, f'Materia {mid}'), 'horas': h,
          'pct': round(h * 100 / total_materias)}
         for mid, h in por_materia.items()],
        key=lambda x: -x['horas'],
    )[:8]

    datos['carga_por_dia'] = [
        {'dia': DIAS_SEMANA[d], 'horas': por_dia.get(d, 0)}
        for d in DIAS_ESCOLARES
    ]

    return datos


def register_dashboard_routes(app):
    """Registra el dashboard principal."""

    @app.route('/dashboard')
    @login_required
    def dashboard():
        colegio = colegio_actual()
        if not colegio:
            return redirect(url_for('colegios'))

        anio = anio_activo(colegio.id)
        params = {'cid': colegio.id}

        def count(sql):
            return db.session.execute(text(sql), params).scalar() or 0

        stats = {
            'profesores': count(
                "SELECT count(*) FROM profesor WHERE activo AND colegio_id = :cid"),
            'secciones': count(
                "SELECT count(*) FROM seccion s "
                "JOIN anio_lectivo a ON a.id = s.anio_lectivo_id "
                "WHERE a.colegio_id = :cid"),
            'aulas': count(
                "SELECT count(*) FROM aula WHERE activa AND colegio_id = :cid"),
            'materias': count(
                "SELECT count(*) FROM materia WHERE colegio_id = :cid"),
            'reglas': count(
                "SELECT count(*) FROM regla WHERE activa AND colegio_id = :cid"),
        }

        metricas = _metricas(colegio, anio)

        publicaciones = []
        if anio:
            turnos = Turno.query.filter_by(colegio_id=colegio.id) \
                                 .order_by(Turno.nombre).all()
            for turno in turnos:
                version = HorarioVersion.query.filter_by(
                    anio_lectivo_id=anio.id, turno_id=turno.id,
                    estado='publicado').first()
                publicaciones.append({
                    'turno': turno,
                    'version': version,
                    'celdas': len(version.celdas) if version else 0,
                })

        versiones = []
        if anio:
            versiones = HorarioVersion.query.filter_by(anio_lectivo_id=anio.id) \
                                            .order_by(HorarioVersion.creado_en.desc()) \
                                            .limit(5).all()

        avisos = obtener_avisos(colegio)

        return render_template(
            'dashboard.html',
            crumb='Dashboard',
            stats=stats,
            metricas=metricas,
            colegio=colegio.nombre,
            anio=anio.nombre if anio else None,
            versiones=versiones,
            publicaciones=publicaciones,
            avisos=avisos,
        )
