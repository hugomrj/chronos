from datetime import datetime

from flask import abort, flash, redirect, render_template, request, url_for
from flask_login import login_required
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import (
    AnioLectivo, Aula, HorarioCelda, HorarioVersion, Profesor, Regla, Seccion,
    Turno,
)
from app.services.scheduler.engine import generar_horario
from app.utils.helpers import (
    DIAS_SEMANA, anio_activo, colegio_actual, parse_int,
)


def register_horarios_routes(app):
    """Generación y consulta de versiones de horario."""

    def _ctx_lista(colegio, resultado=None, turno_sel=None):
        anio = anio_activo(colegio.id)
        turnos = Turno.query.filter_by(colegio_id=colegio.id) \
                             .order_by(Turno.nombre).all()
        secciones_por_turno = {}
        if anio:
            for turno in turnos:
                secciones_por_turno[turno.id] = Seccion.query.filter_by(
                    anio_lectivo_id=anio.id, turno_id=turno.id
                ).count()
        versiones = []
        if anio:
            versiones = HorarioVersion.query.filter_by(anio_lectivo_id=anio.id) \
                                            .order_by(HorarioVersion.creado_en.desc()).all()
        return dict(
            crumb='Horarios',
            anio=anio,
            turnos=turnos,
            secciones_por_turno=secciones_por_turno,
            versiones=versiones,
            resultado=resultado,
            turno_sel=turno_sel,
        )

    @app.route('/horarios')
    @login_required
    def horarios():
        colegio = colegio_actual()
        if not colegio:
            flash('Primero creá un colegio para continuar.', 'warning')
            return redirect(url_for('colegios'))
        return render_template('horarios/horarios.html', **_ctx_lista(colegio))

    @app.route('/horarios/generar', methods=['POST'])
    @login_required
    def horario_generar():
        colegio = colegio_actual()
        if not colegio:
            flash('Primero creá un colegio para continuar.', 'warning')
            return redirect(url_for('colegios'))

        anio = anio_activo(colegio.id)
        if not anio:
            flash('Activá un año lectivo antes de generar horarios.', 'warning')
            return redirect(url_for('anios'))

        turno_id = parse_int(request.form.get('turno_id'))
        turno = db.session.get(Turno, turno_id) if turno_id else None
        if not turno or turno.colegio_id != colegio.id:
            flash('Seleccioná un turno válido.', 'error')
            return redirect(url_for('horarios'))

        secciones = Seccion.query.filter_by(
            anio_lectivo_id=anio.id, turno_id=turno.id
        ).all()
        if not secciones:
            flash(f'El turno {turno.nombre} no tiene secciones cargadas.', 'warning')
            return redirect(url_for('horarios'))

        profesores = Profesor.query.filter_by(colegio_id=colegio.id, activo=True).all()
        aulas = Aula.query.filter_by(colegio_id=colegio.id, activa=True).all()
        reglas = Regla.query.filter_by(colegio_id=colegio.id, activa=True).all()

        resultado = generar_horario(secciones, profesores, aulas, reglas,
                                    limite_segundos=30)

        if not resultado.ok:
            return render_template('horarios/horarios.html',
                                   **_ctx_lista(colegio, resultado=resultado,
                                                turno_sel=turno.id))

        nombre = (request.form.get('nombre') or '').strip()
        if not nombre:
            nombre = f'Generación {datetime.now().strftime("%d/%m/%Y %H:%M")}'

        stats = resultado.estadisticas
        version = HorarioVersion(
            anio_lectivo_id=anio.id,
            turno_id=turno.id,
            nombre=nombre,
            estado='borrador',
            notas=(f"Generado automáticamente en {stats.get('segundos', '?')} s · "
                   f"{stats.get('celdas', 0)} celdas · "
                   f"{stats.get('profesores', 0)} profesores · "
                   f"objetivo {stats.get('objetivo')}"),
        )
        db.session.add(version)
        db.session.flush()

        for a in resultado.asignaciones:
            db.session.add(HorarioCelda(
                version_id=version.id,
                seccion_materia_id=a.seccion_materia_id,
                bloque_id=a.bloque_id,
                aula_id=a.aula_id,
                profesor_id=a.profesor_id,
                fijado=False,
                origen='auto',
            ))

        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash('El horario generado tenía conflictos y no se guardó. '
                  'Revisá los datos y volvé a intentar.', 'error')
            return redirect(url_for('horarios'))

        flash(f'Horario generado y guardado como borrador: {len(resultado.asignaciones)} bloques.',
              'success')
        for advertencia in resultado.advertencias:
            flash(advertencia, 'warning')

        return redirect(url_for('horario_detalle', version_id=version.id))

    @app.route('/horarios/<int:version_id>')
    @login_required
    def horario_detalle(version_id):
        colegio = colegio_actual()
        if not colegio:
            flash('Primero creá un colegio para continuar.', 'warning')
            return redirect(url_for('colegios'))

        version = db.get_or_404(HorarioVersion, version_id)
        if version.anio_lectivo.colegio_id != colegio.id:
            abort(404)

        celdas = HorarioCelda.query.filter_by(version_id=version.id) \
            .order_by(HorarioCelda.seccion_id, HorarioCelda.dia_semana,
                      HorarioCelda.inicio_min).all()

        secciones = Seccion.query.filter_by(
            anio_lectivo_id=version.anio_lectivo_id,
            turno_id=version.turno_id,
        ).order_by(Seccion.id).all()

        por_seccion = {s.id: [] for s in secciones}
        for celda in celdas:
            por_seccion.setdefault(celda.seccion_id, []).append(celda)

        resumen = []
        for seccion in secciones:
            plan = sum(sm.horas_semanales for sm in seccion.materias)
            asignadas = len(por_seccion.get(seccion.id, []))
            resumen.append({
                'seccion': seccion,
                'plan': plan,
                'asignadas': asignadas,
                'completo': asignadas == plan,
            })

        return render_template(
            'horarios/detalle.html',
            crumb='Horario',
            version=version,
            celdas=celdas,
            resumen=resumen,
            por_seccion=por_seccion,
            dias=DIAS_SEMANA,
            total_plan=sum(r['plan'] for r in resumen),
            total_asignadas=len(celdas),
        )

    @app.route('/horarios/<int:version_id>/eliminar', methods=['POST'])
    @login_required
    def horario_eliminar(version_id):
        colegio = colegio_actual()
        if not colegio:
            flash('Primero creá un colegio para continuar.', 'warning')
            return redirect(url_for('colegios'))
        version = db.get_or_404(HorarioVersion, version_id)
        if version.anio_lectivo.colegio_id != colegio.id:
            abort(404)

        db.session.delete(version)
        db.session.commit()
        flash('Versión de horario eliminada.', 'success')
        return redirect(url_for('horarios'))
