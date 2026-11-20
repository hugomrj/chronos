from datetime import datetime

from flask import abort, flash, redirect, render_template, request, url_for
from flask_login import login_required
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import (
    Aula, Bloque, HorarioCelda, HorarioVersion, Profesor, Regla, Seccion,
    SeccionMateria, Turno,
)
from app.services.scheduler.constraints import profesor_disponible
from app.services.scheduler.engine import generar_horario
from app.utils.helpers import (
    DIAS_SEMANA, anio_activo, colegio_actual, parse_int,
)


def register_horarios_routes(app):
    """Generación, revisión, ajustes y publicación de horarios."""

    def _version_de_colegio(version_id, colegio):
        version = db.get_or_404(HorarioVersion, version_id)
        if version.anio_lectivo.colegio_id != colegio.id:
            abort(404)
        return version

    def _secciones_de_version(version):
        return Seccion.query.filter_by(
            anio_lectivo_id=version.anio_lectivo_id,
            turno_id=version.turno_id,
        ).order_by(Seccion.id).all()

    def _resumen(version, celdas=None):
        secciones = _secciones_de_version(version)
        if celdas is None:
            celdas = HorarioCelda.query.filter_by(version_id=version.id).all()
        conteo = {}
        for celda in celdas:
            conteo[celda.seccion_id] = conteo.get(celda.seccion_id, 0) + 1
        resumen = []
        for seccion in secciones:
            plan = sum(sm.horas_semanales for sm in seccion.materias)
            asignadas = conteo.get(seccion.id, 0)
            resumen.append({
                'seccion': seccion,
                'plan': plan,
                'asignadas': asignadas,
                'completo': asignadas == plan and plan > 0,
            })
        total_plan = sum(r['plan'] for r in resumen)
        total_asignadas = sum(r['asignadas'] for r in resumen)
        return resumen, total_plan, total_asignadas

    def _completa(version):
        resumen, total_plan, total_asignadas = _resumen(version)
        return bool(resumen) and total_asignadas == total_plan and total_plan > 0

    def _conflicto(version_id, seccion_id, profesor_id, aula_id, dia, inicio, fin,
                   excluir_id=None):
        base = HorarioCelda.query.filter(
            HorarioCelda.version_id == version_id,
            HorarioCelda.dia_semana == dia,
            HorarioCelda.inicio_min < fin,
            HorarioCelda.fin_min > inicio,
        )
        if excluir_id:
            base = base.filter(HorarioCelda.id != excluir_id)

        if base.filter(HorarioCelda.seccion_id == seccion_id).first():
            return 'La sección ya tiene una clase en ese bloque.'
        if profesor_id and base.filter(HorarioCelda.profesor_id == profesor_id).first():
            return 'El profesor ya tiene una clase en ese horario.'
        if aula_id and base.filter(HorarioCelda.aula_id == aula_id).first():
            return 'El aula ya está ocupada en ese horario.'
        return None

    # ------------------------------------------------------------------
    # LISTADO Y GENERACIÓN
    # ------------------------------------------------------------------
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

        resultado = generar_horario(
            secciones,
            Profesor.query.filter_by(colegio_id=colegio.id, activo=True).all(),
            Aula.query.filter_by(colegio_id=colegio.id, activa=True).all(),
            Regla.query.filter_by(colegio_id=colegio.id, activa=True).all(),
            limite_segundos=30,
        )

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
                   f"{stats.get('profesores', 0)} profesores"),
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
                fijado=a.fijado,
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

    # ------------------------------------------------------------------
    # DETALLE / GRILLA
    # ------------------------------------------------------------------
    def _ctx_detalle(version, colegio, seccion_id=None, profesor_id=None,
                     vista='seccion', celda_id=None, nuevo=False, bloque_id=None,
                     form=None, errors=None, resultado=None):
        secciones = _secciones_de_version(version)
        seleccionada = None
        if secciones:
            seleccionada = next((s for s in secciones if s.id == seccion_id), secciones[0])

        celdas = HorarioCelda.query.filter_by(version_id=version.id) \
            .order_by(HorarioCelda.seccion_id, HorarioCelda.dia_semana,
                      HorarioCelda.inicio_min).all()

        resumen, total_plan, total_asignadas = _resumen(version, celdas)

        por_seccion = {}
        for celda in celdas:
            por_seccion.setdefault(celda.seccion_id, []).append(celda)

        # Grilla de la sección elegida
        dias = []
        filas = []
        celdas_bloque = {}
        bloques_form = []
        if seleccionada:
            bloques = sorted(seleccionada.plantilla.bloques,
                             key=lambda b: (b.dia_semana, b.hora_inicio))
            dias = sorted({b.dia_semana for b in bloques})
            filas_dict = {}
            for b in bloques:
                clave = (b.hora_inicio, b.hora_fin, b.tipo)
                filas_dict.setdefault(clave, {})[b.dia_semana] = b
                if b.tipo == 'clase':
                    bloques_form.append(b)
            filas = [
                {'inicio': k[0], 'fin': k[1], 'tipo': k[2], 'por_dia': v}
                for k, v in sorted(filas_dict.items())
            ]
            celdas_bloque = {
                c.bloque_id: c for c in por_seccion.get(seleccionada.id, [])
            }

        # Formulario de celda
        edit_celda = None
        if celda_id:
            edit_celda = db.session.get(HorarioCelda, celda_id)
            if edit_celda and edit_celda.version_id != version.id:
                edit_celda = None

        aulas = Aula.query.filter_by(
            colegio_id=colegio.id, activa=True).order_by(Aula.nombre).all()
        profesores = Profesor.query.filter_by(
            colegio_id=colegio.id, activo=True).order_by(Profesor.nombre).all()

        # Vista por profesor
        profesor_sel = None
        celdas_profesor = []
        if vista == 'profesor' and profesores:
            profesor_sel = next((p for p in profesores if p.id == profesor_id),
                                profesores[0])
            celdas_profesor = sorted(
                [c for c in celdas if c.profesor_id == profesor_sel.id],
                key=lambda c: (c.dia_semana, c.inicio_min),
            )

        return dict(
            crumb='Horario',
            version=version,
            secciones=secciones,
            seleccionada=seleccionada,
            celdas=celdas,
            por_seccion=por_seccion,
            resumen=resumen,
            total_plan=total_plan,
            total_asignadas=total_asignadas,
            completa=bool(resumen) and total_asignadas == total_plan and total_plan > 0,
            dias=dias,
            dias_nombres=DIAS_SEMANA,
            filas=filas,
            celdas_bloque=celdas_bloque,
            bloques_form=bloques_form,
            aulas=aulas,
            profesores=profesores,
            edit_celda=edit_celda,
            nuevo=nuevo,
            bloque_id=bloque_id,
            form=form or {},
            errors=errors or [],
            vista=vista,
            profesor_sel=profesor_sel,
            celdas_profesor=celdas_profesor,
            resultado=resultado,
        )

    @app.route('/horarios/<int:version_id>')
    @login_required
    def horario_detalle(version_id):
        colegio = colegio_actual()
        if not colegio:
            flash('Primero creá un colegio para continuar.', 'warning')
            return redirect(url_for('colegios'))
        version = _version_de_colegio(version_id, colegio)

        seccion_id = request.args.get('seccion_id', type=int)
        celda_id = request.args.get('celda', type=int)
        if celda_id:
            celda = db.session.get(HorarioCelda, celda_id)
            if celda and celda.version_id == version.id:
                seccion_id = celda.seccion_id

        return render_template(
            'horarios/detalle.html',
            **_ctx_detalle(
                version, colegio,
                seccion_id=seccion_id,
                profesor_id=request.args.get('profesor_id', type=int),
                vista=request.args.get('vista') or 'seccion',
                celda_id=celda_id,
                nuevo=request.args.get('nuevo') == '1',
                bloque_id=request.args.get('bloque_id', type=int),
            ),
        )

    # ------------------------------------------------------------------
    # AJUSTES MANUALES
    # ------------------------------------------------------------------
    @app.route('/horarios/<int:version_id>/celdas/guardar', methods=['POST'])
    @login_required
    def celda_guardar(version_id):
        colegio = colegio_actual()
        if not colegio:
            flash('Primero creá un colegio para continuar.', 'warning')
            return redirect(url_for('colegios'))
        version = _version_de_colegio(version_id, colegio)

        celda_id = request.form.get('celda_id', type=int)
        celda = db.session.get(HorarioCelda, celda_id) if celda_id else None
        if celda and celda.version_id != version.id:
            celda = None

        sm_id = parse_int(request.form.get('seccion_materia_id'))
        bloque_id = parse_int(request.form.get('bloque_id'))
        aula_id = parse_int(request.form.get('aula_id'))
        profesor_id = parse_int(request.form.get('profesor_id'))
        fijado = request.form.get('fijado') == 'on'

        sm = db.session.get(SeccionMateria, sm_id) if sm_id else None
        bloque = db.session.get(Bloque, bloque_id) if bloque_id else None
        aula = db.session.get(Aula, aula_id) if aula_id else None
        profesor = db.session.get(Profesor, profesor_id) if profesor_id else None

        seccion = sm.seccion if sm else None
        errors = []

        if not sm or seccion.anio_lectivo_id != version.anio_lectivo_id \
                or seccion.turno_id != version.turno_id:
            errors.append('Seleccioná una materia válida de las secciones de esta versión.')
        if not bloque or not seccion or bloque.plantilla_id != seccion.plantilla_id:
            errors.append('Seleccioná un bloque de la plantilla de la sección.')
        elif bloque.tipo != 'clase':
            errors.append('Solo se pueden asignar clases a bloques de tipo clase.')
        if aula and (aula.colegio_id != colegio.id or not aula.activa):
            errors.append('El aula seleccionada no está disponible.')
        if profesor and (profesor.colegio_id != colegio.id or not profesor.activo):
            errors.append('El profesor seleccionado no está disponible.')

        if sm and aula:
            if sm.aula_requerida_id and aula.id != sm.aula_requerida_id:
                errors.append('La materia exige otra aula específica.')
            elif sm.materia.tipo_aula_requerida and aula.tipo != sm.materia.tipo_aula_requerida:
                errors.append(
                    f'La materia requiere un aula de tipo '
                    f'{sm.materia.tipo_aula_requerida}.'
                )

        if sm and profesor and sm.materia not in profesor.materias:
            errors.append('El profesor no tiene habilitada esa materia.')

        if sm and profesor and bloque and not profesor_disponible(profesor, bloque):
            errors.append('El profesor no está disponible en ese bloque.')

        if sm:
            existentes = HorarioCelda.query.filter_by(
                version_id=version.id, seccion_materia_id=sm.id)
            if celda:
                existentes = existentes.filter(HorarioCelda.id != celda.id)
            if existentes.count() >= sm.horas_semanales:
                errors.append(
                    f'{sm.materia.nombre} ya tiene todas sus horas asignadas '
                    f'en esta versión.'
                )

        if not errors:
            inicio = bloque.hora_inicio.hour * 60 + bloque.hora_inicio.minute
            fin = bloque.hora_fin.hour * 60 + bloque.hora_fin.minute
            conflicto = _conflicto(
                version.id, seccion.id,
                profesor.id if profesor else None,
                aula.id if aula else None,
                bloque.dia_semana, inicio, fin,
                excluir_id=celda.id if celda else None,
            )
            if conflicto:
                errors.append(conflicto)

        if errors:
            return render_template(
                'horarios/detalle.html',
                **_ctx_detalle(
                    version, colegio,
                    seccion_id=seccion.id if seccion else None,
                    celda_id=celda.id if celda else None,
                    nuevo=celda is None,
                    bloque_id=bloque.id if bloque else None,
                    form=request.form, errors=errors,
                ),
            )

        if celda is None:
            celda = HorarioCelda(version_id=version.id, origen='manual')
            db.session.add(celda)

        celda.seccion_materia_id = sm.id
        celda.bloque_id = bloque.id
        celda.aula_id = aula.id if aula else None
        celda.profesor_id = profesor.id if profesor else None
        celda.fijado = fijado
        celda.origen = 'manual'

        try:
            db.session.commit()
            flash('Celda guardada correctamente.', 'success')
        except IntegrityError:
            db.session.rollback()
            flash('La celda se superpone con otra clase. Revisá el horario.', 'error')
            return redirect(url_for('horario_detalle', version_id=version.id,
                                    seccion_id=seccion.id))

        return redirect(url_for('horario_detalle', version_id=version.id,
                                seccion_id=seccion.id))

    @app.route('/horarios/<int:version_id>/celdas/<int:celda_id>/eliminar',
               methods=['POST'])
    @login_required
    def celda_eliminar(version_id, celda_id):
        colegio = colegio_actual()
        if not colegio:
            return redirect(url_for('colegios'))
        version = _version_de_colegio(version_id, colegio)
        celda = db.get_or_404(HorarioCelda, celda_id)
        if celda.version_id != version.id:
            abort(404)

        seccion_id = celda.seccion_id
        db.session.delete(celda)
        db.session.commit()
        flash('Celda eliminada.', 'success')
        return redirect(url_for('horario_detalle', version_id=version.id,
                                seccion_id=seccion_id))

    # ------------------------------------------------------------------
    # ESTADO DE LA VERSIÓN
    # ------------------------------------------------------------------
    @app.route('/horarios/<int:version_id>/publicar', methods=['POST'])
    @login_required
    def horario_publicar(version_id):
        colegio = colegio_actual()
        if not colegio:
            return redirect(url_for('colegios'))
        version = _version_de_colegio(version_id, colegio)

        if not _completa(version):
            flash('No se puede publicar: el horario está incompleto.', 'error')
            return redirect(url_for('horario_detalle', version_id=version.id))

        HorarioVersion.query.filter(
            HorarioVersion.anio_lectivo_id == version.anio_lectivo_id,
            HorarioVersion.turno_id == version.turno_id,
            HorarioVersion.estado == 'publicado',
            HorarioVersion.id != version.id,
        ).update({'estado': 'archivado'}, synchronize_session=False)

        version.estado = 'publicado'
        db.session.commit()
        flash('Horario publicado. La versión anterior quedó archivada.', 'success')
        return redirect(url_for('horario_detalle', version_id=version.id))

    @app.route('/horarios/<int:version_id>/archivar', methods=['POST'])
    @login_required
    def horario_archivar(version_id):
        colegio = colegio_actual()
        if not colegio:
            return redirect(url_for('colegios'))
        version = _version_de_colegio(version_id, colegio)
        version.estado = 'archivado'
        db.session.commit()
        flash('Versión archivada.', 'success')
        return redirect(url_for('horario_detalle', version_id=version.id))

    @app.route('/horarios/<int:version_id>/duplicar', methods=['POST'])
    @login_required
    def horario_duplicar(version_id):
        colegio = colegio_actual()
        if not colegio:
            return redirect(url_for('colegios'))
        original = _version_de_colegio(version_id, colegio)

        copia = HorarioVersion(
            anio_lectivo_id=original.anio_lectivo_id,
            turno_id=original.turno_id,
            nombre=f'Copia de {original.nombre or ("Versión " + str(original.id))}',
            estado='borrador',
            notas='Copia de una versión existente.',
        )
        db.session.add(copia)
        db.session.flush()

        for celda in original.celdas:
            db.session.add(HorarioCelda(
                version_id=copia.id,
                seccion_materia_id=celda.seccion_materia_id,
                bloque_id=celda.bloque_id,
                aula_id=celda.aula_id,
                profesor_id=celda.profesor_id,
                fijado=celda.fijado,
                origen=celda.origen,
            ))
        db.session.commit()
        flash('Versión duplicada como borrador.', 'success')
        return redirect(url_for('horario_detalle', version_id=copia.id))

    @app.route('/horarios/<int:version_id>/regenerar', methods=['POST'])
    @login_required
    def horario_regenerar(version_id):
        colegio = colegio_actual()
        if not colegio:
            return redirect(url_for('colegios'))
        original = _version_de_colegio(version_id, colegio)

        secciones = _secciones_de_version(original)
        fijados = [
            {
                'seccion_materia_id': c.seccion_materia_id,
                'bloque_id': c.bloque_id,
                'aula_id': c.aula_id,
                'profesor_id': c.profesor_id,
            }
            for c in original.celdas if c.fijado
        ]

        resultado = generar_horario(
            secciones,
            Profesor.query.filter_by(colegio_id=colegio.id, activo=True).all(),
            Aula.query.filter_by(colegio_id=colegio.id, activa=True).all(),
            Regla.query.filter_by(colegio_id=colegio.id, activa=True).all(),
            limite_segundos=30,
            fijados=fijados,
        )

        if not resultado.ok:
            return render_template(
                'horarios/detalle.html',
                **_ctx_detalle(original, colegio, resultado=resultado),
            )

        nueva = HorarioVersion(
            anio_lectivo_id=original.anio_lectivo_id,
            turno_id=original.turno_id,
            nombre=f'Regeneración de {original.nombre or ("Versión " + str(original.id))}',
            estado='borrador',
            notas=(f"Regenerada automáticamente; se conservaron {len(fijados)} "
                   f"celda(s) fijada(s)."),
        )
        db.session.add(nueva)
        db.session.flush()

        for a in resultado.asignaciones:
            db.session.add(HorarioCelda(
                version_id=nueva.id,
                seccion_materia_id=a.seccion_materia_id,
                bloque_id=a.bloque_id,
                aula_id=a.aula_id,
                profesor_id=a.profesor_id,
                fijado=a.fijado,
                origen='manual' if a.fijado else 'auto',
            ))

        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash('La regeneración produjo conflictos y no se guardó.', 'error')
            return redirect(url_for('horario_detalle', version_id=original.id))

        flash(f'Horario regenerado con {len(fijados)} celda(s) fijada(s) conservada(s).',
              'success')
        for advertencia in resultado.advertencias:
            flash(advertencia, 'warning')
        return redirect(url_for('horario_detalle', version_id=nueva.id))

    @app.route('/horarios/<int:version_id>/eliminar', methods=['POST'])
    @login_required
    def horario_eliminar(version_id):
        colegio = colegio_actual()
        if not colegio:
            flash('Primero creá un colegio para continuar.', 'warning')
            return redirect(url_for('colegios'))
        version = _version_de_colegio(version_id, colegio)
        if version.estado == 'publicado':
            flash('No se puede eliminar una versión publicada. Archivála primero.', 'error')
            return redirect(url_for('horario_detalle', version_id=version.id))

        db.session.delete(version)
        db.session.commit()
        flash('Versión de horario eliminada.', 'success')
        return redirect(url_for('horarios'))
