from flask import abort, flash, redirect, render_template, request, url_for
from flask_login import login_required
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import (
    AnioLectivo, AreaConocimiento, Aula, Bloque, Grado, Materia, PlanEstudio,
    PlanMateria, PlantillaHorario, Profesor, Seccion, SeccionMateria, Turno,
)
from app.utils.helpers import (
    DIAS_SEMANA, TIPOS_PLAN, TIPOS_PLAN_LABEL, parse_int, parse_time,
)
from app.utils.colegio import anio_activo, colegio_actual



def register_schedule_routes(app):
    """Plantillas de horario, secciones y planes de estudio."""

    def _colegio():
        colegio = colegio_actual()
        if not colegio:
            flash('Primero creá un colegio para continuar.', 'warning')
        return colegio

    def _plantilla(plantilla_id, colegio):
        item = db.session.get(PlantillaHorario, plantilla_id)
        if not item or item.colegio_id != colegio.id:
            abort(404)
        return item

    def _seccion(seccion_id, colegio):
        item = db.session.get(Seccion, seccion_id)
        if not item:
            abort(404)
        if item.anio_lectivo.colegio_id != colegio.id:
            abort(404)
        return item

    def _grado(grado_id, colegio):
        item = db.session.get(Grado, grado_id)
        if not item or item.nivel.colegio_id != colegio.id:
            abort(404)
        return item

    def _clase_count(plantilla):
        if not plantilla:
            return 0
        return Bloque.query.filter_by(plantilla_id=plantilla.id, tipo='clase').count()

    def _plantillas_ctx(colegio, edit=None, form=None, errors=None):
        return dict(
            crumb='Plantillas',
            items=PlantillaHorario.query.filter_by(colegio_id=colegio.id)
                                        .order_by(PlantillaHorario.nombre).all(),
            turnos=Turno.query.filter_by(colegio_id=colegio.id)
                               .order_by(Turno.nombre).all(),
            edit=edit,
            form=form or {},
            errors=errors or [],
        )

    def _detalle_ctx(plantilla, edit_bloque=None, form=None, errors=None, dia=None):
        bloques = sorted(plantilla.bloques, key=lambda b: (b.dia_semana, b.hora_inicio))
        por_dia = {d: [] for d in DIAS_SEMANA}
        for b in bloques:
            por_dia.setdefault(b.dia_semana, []).append(b)
        return dict(
            crumb='Bloques',
            plantilla=plantilla,
            por_dia=por_dia,
            dias=DIAS_SEMANA,
            edit_bloque=edit_bloque,
            form=form or {},
            errors=errors or [],
            dia_sel=dia or 1,
            clases=_clase_count(plantilla),
            recesos=sum(1 for b in bloques if b.tipo == 'receso'),
        )

    def _secciones_ctx(colegio, edit=None, form=None, errors=None):
        anio = anio_activo(colegio.id)
        items = []
        if anio:
            items = Seccion.query.filter_by(anio_lectivo_id=anio.id) \
                                  .join(Grado) \
                                  .order_by(Grado.nombre, Seccion.nombre).all()
        return dict(
            crumb='Secciones',
            anio=anio,
            items=items,
            grados=Grado.query.join(Grado.nivel)
                              .filter_by(colegio_id=colegio.id)
                              .order_by(Grado.nombre).all(),
            planes=PlanEstudio.query.filter_by(
                colegio_id=colegio.id, activo=True
            ).order_by(PlanEstudio.nombre).all(),
            turnos=Turno.query.filter_by(colegio_id=colegio.id)
                               .order_by(Turno.nombre).all(),
            aulas=Aula.query.filter_by(colegio_id=colegio.id, activa=True)
                             .order_by(Aula.nombre).all(),
            plantillas=PlantillaHorario.query.filter_by(colegio_id=colegio.id)
                                             .order_by(PlantillaHorario.nombre).all(),
            edit=edit,
            form=form or {},
            errors=errors or [],
        )

    def _grado_plan_ctx(grado, plan, edit=None, form=None, errors=None):
        items = PlanMateria.query.filter_by(
            plan_id=plan.id, grado_id=grado.id
        ).join(Materia).order_by(Materia.nombre).all()
        return dict(
            crumb=f'Plan · {plan.nombre} · {grado.nombre}',
            grado=grado,
            plan=plan,
            items=items,
            materias=[
                m for m in Materia.query.filter_by(
                    colegio_id=grado.nivel.colegio_id, nivel_id=grado.nivel_id
                ).order_by(Materia.nombre).all()
                if (plan.especialidad and (
                        not m.especialidades or plan.especialidad in m.especialidades))
                or (not plan.especialidad and not m.especialidades)
            ],
            tipos_plan=TIPOS_PLAN,
            tipos_plan_label=TIPOS_PLAN_LABEL,
            edit=edit,
            form=form or {},
            errors=errors or [],
        )

    def _seccion_plan_ctx(seccion, edit=None, form=None, errors=None):
        items = SeccionMateria.query.filter_by(seccion_id=seccion.id) \
                                    .join(Materia).order_by(Materia.nombre).all()
        total = sum(sm.horas_semanales for sm in items)
        disponible = _clase_count(seccion.plantilla)
        gm_map = {gm.materia_id: gm for gm in PlanMateria.query.filter_by(
            plan_id=seccion.plan_id, grado_id=seccion.grado_id).all()}
        return dict(
            crumb=f'Plan · {seccion.grado.nombre} {seccion.nombre}',
            seccion=seccion,
            items=items,
            gm_map=gm_map,
            total_horas=total,
            disponible=disponible,
            materias=[
                m for m in Materia.query.filter_by(
                    colegio_id=seccion.anio_lectivo.colegio_id,
                    nivel_id=seccion.grado.nivel_id,
                ).order_by(Materia.nombre).all()
                if not m.especialidades or (
                    seccion.especialidad and seccion.especialidad in m.especialidades)
            ],
            profesores=Profesor.query.filter_by(
                colegio_id=seccion.anio_lectivo.colegio_id, activo=True
            ).order_by(Profesor.nombre).all(),
            aulas=Aula.query.filter_by(
                colegio_id=seccion.anio_lectivo.colegio_id, activa=True
            ).order_by(Aula.nombre).all(),
            edit=edit,
            form=form or {},
            errors=errors or [],
        )

    # ------------------------------------------------------------------
    # PLANTILLAS
    # ------------------------------------------------------------------
    @app.route('/plantillas')
    @login_required
    def plantillas():
        colegio = _colegio()
        if not colegio:
            return redirect(url_for('dashboard'))

        edit = None
        edit_id = request.args.get('editar', type=int)
        if edit_id:
            edit = db.session.get(PlantillaHorario, edit_id)
            if edit and edit.colegio_id != colegio.id:
                edit = None

        return render_template('schedule/plantillas.html',
                               **_plantillas_ctx(colegio, edit=edit))

    @app.route('/plantillas/guardar', methods=['POST'])
    @login_required
    def plantilla_guardar():
        colegio = _colegio()
        if not colegio:
            return redirect(url_for('dashboard'))

        item_id = request.form.get('id', type=int)
        item = db.session.get(PlantillaHorario, item_id) if item_id else None
        if item and item.colegio_id != colegio.id:
            item = None

        nombre = (request.form.get('nombre') or '').strip()
        turno_id = parse_int(request.form.get('turno_id'))
        plan = db.session.get(PlanEstudio, plan_id) if plan_id else None
        if plan and plan.colegio_id != colegio.id:
            plan = None
        turno = db.session.get(Turno, turno_id) if turno_id else None
        if turno and turno.colegio_id != colegio.id:
            turno = None

        errors = []
        if not nombre:
            errors.append('El nombre de la plantilla es obligatorio.')
        if not turno:
            errors.append('Seleccioná un turno válido.')

        if errors:
            return render_template('schedule/plantillas.html',
                                   **_plantillas_ctx(colegio, edit=item,
                                                     form=request.form,
                                                     errors=errors))

        if item:
            item.nombre = nombre
            item.turno_id = turno.id
        else:
            item = PlantillaHorario(colegio_id=colegio.id, nombre=nombre,
                                    turno_id=turno.id)
            db.session.add(item)

        try:
            db.session.commit()
            flash('Plantilla guardada correctamente.', 'success')
        except IntegrityError:
            db.session.rollback()
            flash('Ya existe una plantilla con ese nombre.', 'error')

        return redirect(url_for('plantillas'))

    @app.route('/plantillas/<int:plantilla_id>/eliminar', methods=['POST'])
    @login_required
    def plantilla_eliminar(plantilla_id):
        colegio = _colegio()
        if not colegio:
            return redirect(url_for('dashboard'))
        item = _plantilla(plantilla_id, colegio)

        try:
            db.session.delete(item)
            db.session.commit()
            flash('Plantilla eliminada.', 'success')
        except IntegrityError:
            db.session.rollback()
            flash('No se puede eliminar: hay secciones que usan esta plantilla.', 'error')
        return redirect(url_for('plantillas'))

    @app.route('/plantillas/<int:plantilla_id>')
    @login_required
    def plantilla_detalle(plantilla_id):
        colegio = _colegio()
        if not colegio:
            return redirect(url_for('dashboard'))
        item = _plantilla(plantilla_id, colegio)

        edit_bloque = None
        edit_id = request.args.get('editar', type=int)
        if edit_id:
            edit_bloque = db.session.get(Bloque, edit_id)
            if edit_bloque and edit_bloque.plantilla_id != item.id:
                edit_bloque = None

        dia = request.args.get('dia', type=int) or (edit_bloque.dia_semana if edit_bloque else 1)
        return render_template('schedule/plantilla_detalle.html',
                               **_detalle_ctx(item, edit_bloque=edit_bloque, dia=dia))

    @app.route('/plantillas/<int:plantilla_id>/bloques/guardar', methods=['POST'])
    @login_required
    def bloque_guardar(plantilla_id):
        colegio = _colegio()
        if not colegio:
            return redirect(url_for('dashboard'))
        plantilla = _plantilla(plantilla_id, colegio)

        bloque_id = request.form.get('id', type=int)
        bloque = db.session.get(Bloque, bloque_id) if bloque_id else None
        if bloque and bloque.plantilla_id != plantilla.id:
            bloque = None

        dia = parse_int(request.form.get('dia_semana'))
        numero = parse_int(request.form.get('numero'))
        inicio = parse_time(request.form.get('hora_inicio'))
        fin = parse_time(request.form.get('hora_fin'))
        tipo = request.form.get('tipo') or 'clase'

        errors = []
        if dia not in DIAS_SEMANA:
            errors.append('Seleccioná un día válido.')
        if not numero or numero < 1:
            errors.append('El número de bloque debe ser mayor a cero.')
        if not inicio or not fin:
            errors.append('Completá la hora de inicio y de fin.')
        elif fin <= inicio:
            errors.append('La hora de fin debe ser posterior a la de inicio.')
        if tipo not in ('clase', 'receso'):
            errors.append('El tipo de bloque no es válido.')

        if not errors:
            duplicado = Bloque.query.filter(
                Bloque.plantilla_id == plantilla.id,
                Bloque.dia_semana == dia,
                Bloque.numero == numero,
                Bloque.id != (bloque.id if bloque else -1),
            ).first()
            if duplicado:
                errors.append(f'Ya existe el bloque N° {numero} para ese día.')

            solape = Bloque.query.filter(
                Bloque.plantilla_id == plantilla.id,
                Bloque.dia_semana == dia,
                Bloque.hora_inicio < fin,
                Bloque.hora_fin > inicio,
                Bloque.id != (bloque.id if bloque else -1),
            ).first()
            if solape:
                errors.append(
                    f'El horario se solapa con el bloque '
                    f'{solape.hora_inicio.strftime("%H:%M")}–'
                    f'{solape.hora_fin.strftime("%H:%M")}.'
                )

        if errors:
            return render_template(
                'schedule/plantilla_detalle.html',
                **_detalle_ctx(plantilla, edit_bloque=bloque, form=request.form,
                               errors=errors, dia=dia),
            )

        if bloque is None:
            bloque = Bloque(plantilla_id=plantilla.id)
            db.session.add(bloque)

        bloque.dia_semana = dia
        bloque.numero = numero
        bloque.hora_inicio = inicio
        bloque.hora_fin = fin
        bloque.tipo = tipo

        try:
            db.session.commit()
            flash('Bloque guardado correctamente.', 'success')
        except IntegrityError:
            db.session.rollback()
            flash('No se pudo guardar el bloque. Revisá el número y el horario.', 'error')

        return redirect(url_for('plantilla_detalle', plantilla_id=plantilla.id, dia=dia))

    @app.route('/plantillas/<int:plantilla_id>/bloques/<int:bloque_id>/eliminar',
               methods=['POST'])
    @login_required
    def bloque_eliminar(plantilla_id, bloque_id):
        colegio = _colegio()
        if not colegio:
            return redirect(url_for('dashboard'))
        plantilla = _plantilla(plantilla_id, colegio)
        bloque = db.get_or_404(Bloque, bloque_id)
        if bloque.plantilla_id != plantilla.id:
            abort(404)

        dia = bloque.dia_semana
        try:
            db.session.delete(bloque)
            db.session.commit()
            flash('Bloque eliminado.', 'success')
        except IntegrityError:
            db.session.rollback()
            flash('No se puede eliminar: el bloque está usado en un horario.', 'error')
        return redirect(url_for('plantilla_detalle', plantilla_id=plantilla.id, dia=dia))

    # ------------------------------------------------------------------
    # PLAN BASE POR GRADO
    # ------------------------------------------------------------------
    @app.route('/grados/<int:grado_id>/plan')
    @login_required
    def grado_plan(grado_id):
        colegio = _colegio()
        if not colegio:
            return redirect(url_for('dashboard'))
        grado = _grado(grado_id, colegio)

        plan_id = request.args.get('plan_id', type=int)
        plan = db.session.get(PlanEstudio, plan_id) if plan_id else None
        if plan is None or plan.colegio_id != colegio.id or grado not in plan.grados:
            plan = next((p for p in grado.planes
                         if p.colegio_id == colegio.id), None)
        if plan is None:
            flash('El curso no tiene un plan asignado.', 'warning')
            return redirect(url_for('planes'))

        edit = None
        materia_id = request.args.get('editar', type=int)
        if materia_id:
            edit = db.session.get(PlanMateria, (plan.id, grado.id, materia_id))

        return render_template('schedule/grado_plan.html',
                               **_grado_plan_ctx(grado, plan, edit=edit))

    @app.route('/grados/<int:grado_id>/plan/guardar', methods=['POST'])
    @login_required
    def grado_plan_guardar(grado_id):
        colegio = _colegio()
        if not colegio:
            return redirect(url_for('dashboard'))
        grado = _grado(grado_id, colegio)

        plan_id = parse_int(request.form.get('plan_id'))
        plan = db.session.get(PlanEstudio, plan_id) if plan_id else None
        if not plan or plan.colegio_id != colegio.id or grado not in plan.grados:
            abort(404)

        materia_id = parse_int(request.form.get('materia_id'))
        original_id = parse_int(request.form.get('materia_original'))
        horas = parse_int(request.form.get('horas_semanales'))
        max_dia = parse_int(request.form.get('max_bloques_por_dia'), 1) or 1
        doble = request.form.get('requiere_bloque_doble') == 'on'
        tipo_plan = request.form.get('tipo_plan') or 'comun'

        materia = db.session.get(Materia, materia_id) if materia_id else None
        if materia and materia.colegio_id != colegio.id:
            materia = None

        edit = db.session.get(PlanMateria, (plan.id, grado.id, original_id)) if original_id else None
        if edit is not None:
            materia = edit.materia

        errors = []
        if not materia:
            errors.append('Seleccioná una materia válida.')
        elif materia.nivel_id != grado.nivel_id:
            errors.append('La materia pertenece a otro nivel.')
        elif materia.especialidades and (
                not plan.especialidad or plan.especialidad not in materia.especialidades):
            errors.append('La materia no pertenece a la especialidad del plan.')
        if horas is None or horas < 1:
            errors.append('Las horas semanales deben ser mayores a cero.')
        if max_dia < 1:
            errors.append('El máximo por día debe ser mayor a cero.')
        if tipo_plan not in TIPOS_PLAN:
            errors.append('El tipo de plan seleccionado no es válido.')

        # Validar el máximo de horas del área de la materia.
        if materia and materia.area and horas is not None and horas >= 1:
            area = materia.area
            limite = area.horas_max_semana
            if limite:
                total = 0
                for gm in PlanMateria.query.filter_by(plan_id=plan.id, grado_id=grado.id).all():
                    if edit is not None and gm.materia_id == edit.materia_id:
                        continue
                    if gm.materia.area_id == area.id:
                        total += gm.horas_semanales
                total += horas
                if total > limite:
                    errors.append(
                        f'El área {area.nombre} quedaría con {total} h y su máximo es {limite} h.'
                    )

        if materia and not original_id:
            if db.session.get(PlanMateria, (plan.id, grado.id, materia.id)):
                errors.append('Esa materia ya está en el plan del grado.')

        if errors:
            return render_template('schedule/grado_plan.html',
                                   **_grado_plan_ctx(grado, plan, edit=edit,
                                                     form=request.form,
                                                     errors=errors))

        if edit is None:
            edit = PlanMateria(plan_id=plan.id, grado_id=grado.id, materia_id=materia.id)
            db.session.add(edit)

        edit.horas_semanales = horas
        edit.max_bloques_por_dia = max_dia
        edit.requiere_bloque_doble = doble
        edit.tipo_plan = tipo_plan

        try:
            db.session.commit()
            flash('Plan del grado actualizado.', 'success')
        except IntegrityError:
            db.session.rollback()
            flash('No se pudo guardar el plan. Revisá la materia y las horas.', 'error')
        return redirect(url_for('grado_plan', grado_id=grado.id, plan_id=plan.id))

    @app.route('/grados/<int:grado_id>/plan/<int:materia_id>/eliminar', methods=['POST'])
    @login_required
    def grado_plan_eliminar(grado_id, materia_id):
        colegio = _colegio()
        if not colegio:
            return redirect(url_for('dashboard'))
        grado = _grado(grado_id, colegio)
        plan_id = request.args.get('plan_id', type=int) or request.form.get('plan_id', type=int)
        plan = db.session.get(PlanEstudio, plan_id) if plan_id else None
        if not plan or plan.colegio_id != colegio.id:
            abort(404)
        item = db.session.get(PlanMateria, (plan.id, grado.id, materia_id))
        if not item:
            abort(404)

        db.session.delete(item)
        db.session.commit()
        flash('Materia quitada del plan del grado.', 'success')
        return redirect(url_for('grado_plan', grado_id=grado.id, plan_id=plan.id))

    # ------------------------------------------------------------------
    # SECCIONES
    # ------------------------------------------------------------------
    @app.route('/secciones')
    @login_required
    def secciones():
        colegio = _colegio()
        if not colegio:
            return redirect(url_for('dashboard'))

        edit = None
        edit_id = request.args.get('editar', type=int)
        if edit_id:
            edit = db.session.get(Seccion, edit_id)
            if edit and edit.anio_lectivo.colegio_id != colegio.id:
                edit = None

        return render_template('schedule/secciones.html',
                               **_secciones_ctx(colegio, edit=edit))

    @app.route('/secciones/guardar', methods=['POST'])
    @login_required
    def seccion_guardar():
        colegio = _colegio()
        if not colegio:
            return redirect(url_for('dashboard'))

        anio = anio_activo(colegio.id)
        if not anio:
            flash('Activá un año lectivo antes de crear secciones.', 'warning')
            return redirect(url_for('anios'))

        item_id = request.form.get('id', type=int)
        item = db.session.get(Seccion, item_id) if item_id else None
        if item and item.anio_lectivo.colegio_id != colegio.id:
            item = None

        nombre = (request.form.get('nombre') or '').strip()
        grado_id = parse_int(request.form.get('grado_id'))
        plan_id = parse_int(request.form.get('plan_id'))
        turno_id = parse_int(request.form.get('turno_id'))
        plantilla_id = parse_int(request.form.get('plantilla_id'))
        aula_id = parse_int(request.form.get('aula_base_id'))

        grado = db.session.get(Grado, grado_id) if grado_id else None
        if grado and grado.nivel.colegio_id != colegio.id:
            grado = None
        plan = db.session.get(PlanEstudio, plan_id) if plan_id else None
        if plan and plan.colegio_id != colegio.id:
            plan = None
        turno = db.session.get(Turno, turno_id) if turno_id else None
        if turno and turno.colegio_id != colegio.id:
            turno = None
        plantilla = db.session.get(PlantillaHorario, plantilla_id) if plantilla_id else None
        if plantilla and plantilla.colegio_id != colegio.id:
            plantilla = None
        aula = db.session.get(Aula, aula_id) if aula_id else None
        if aula and aula.colegio_id != colegio.id:
            aula = None

        errors = []
        if not nombre:
            errors.append('El nombre de la sección es obligatorio (por ejemplo A).')
        if not grado:
            errors.append('Seleccioná un grado o curso válido.')
        if not plan:
            errors.append('Seleccioná un plan válido.')
        elif grado and plan not in grado.planes:
            errors.append('El plan no pertenece al curso elegido.')
        if not turno:
            errors.append('Seleccioná un turno válido.')
        if not plantilla:
            errors.append('Seleccioná una plantilla de horario.')
        elif turno and plantilla.turno_id != turno.id:
            errors.append('La plantilla debe pertenecer al turno elegido.')

        if errors:
            return render_template('schedule/secciones.html',
                                   **_secciones_ctx(colegio, edit=item,
                                                     form=request.form,
                                                     errors=errors))

        creada = item is None
        if item is None:
            item = Seccion(anio_lectivo_id=anio.id, grado_id=grado.id,
                           plan_id=plan.id,
                           especialidad_id=plan.especialidad_id,
                           turno_id=turno.id, nombre=nombre,
                           aula_base_id=aula.id if aula else None,
                           plantilla_id=plantilla.id)
            db.session.add(item)
        else:
            item.grado_id = grado.id
            item.plan_id = plan.id
            item.especialidad_id = plan.especialidad_id
            item.turno_id = turno.id
            item.nombre = nombre
            item.aula_base_id = aula.id if aula else None
            item.plantilla_id = plantilla.id

        db.session.flush()

        if creada:
            for gm in PlanMateria.query.filter_by(
                    plan_id=plan.id, grado_id=grado.id).all():
                db.session.add(SeccionMateria(
                    seccion_id=item.id,
                    materia_id=gm.materia_id,
                    horas_semanales=gm.horas_semanales,
                    max_bloques_por_dia=gm.max_bloques_por_dia,
                    requiere_bloque_doble=gm.requiere_bloque_doble,
                ))

        try:
            db.session.commit()
            flash('Sección guardada correctamente.', 'success')
        except IntegrityError:
            db.session.rollback()
            flash('Ya existe una sección con ese nombre para el grado y turno.', 'error')
            return redirect(url_for('secciones'))

        total = sum(sm.horas_semanales for sm in item.materias)
        if total > _clase_count(item.plantilla):
            flash(
                f'Atención: el plan suma {total} horas y la plantilla solo tiene '
                f'{_clase_count(item.plantilla)} bloques de clase.',
                'warning',
            )

        return redirect(url_for('secciones'))

    @app.route('/secciones/<int:seccion_id>/eliminar', methods=['POST'])
    @login_required
    def seccion_eliminar(seccion_id):
        colegio = _colegio()
        if not colegio:
            return redirect(url_for('dashboard'))
        item = _seccion(seccion_id, colegio)
        try:
            db.session.delete(item)
            db.session.commit()
            flash('Sección eliminada.', 'success')
        except IntegrityError:
            db.session.rollback()
            flash('No se puede eliminar: la sección tiene horarios generados.', 'error')
        return redirect(url_for('secciones'))

    # ------------------------------------------------------------------
    # PLAN POR SECCIÓN
    # ------------------------------------------------------------------
    @app.route('/secciones/<int:seccion_id>/plan')
    @login_required
    def seccion_plan(seccion_id):
        colegio = _colegio()
        if not colegio:
            return redirect(url_for('dashboard'))
        seccion = _seccion(seccion_id, colegio)

        edit = None
        sm_id = request.args.get('editar', type=int)
        if sm_id:
            edit = db.session.get(SeccionMateria, sm_id)
            if edit and edit.seccion_id != seccion.id:
                edit = None

        return render_template('schedule/seccion_plan.html',
                               **_seccion_plan_ctx(seccion, edit=edit))

    @app.route('/secciones/<int:seccion_id>/plan/guardar', methods=['POST'])
    @login_required
    def seccion_plan_guardar(seccion_id):
        colegio = _colegio()
        if not colegio:
            return redirect(url_for('dashboard'))
        seccion = _seccion(seccion_id, colegio)

        sm_id = request.form.get('sm_id', type=int)
        edit = db.session.get(SeccionMateria, sm_id) if sm_id else None
        if edit and edit.seccion_id != seccion.id:
            edit = None

        materia_id = parse_int(request.form.get('materia_id'))
        materia = db.session.get(Materia, materia_id) if materia_id else None
        if materia and materia.colegio_id != colegio.id:
            materia = None
        if edit is not None:
            materia = edit.materia

        horas = parse_int(request.form.get('horas_semanales'))
        max_dia = parse_int(request.form.get('max_bloques_por_dia'), 1) or 1
        doble = request.form.get('requiere_bloque_doble') == 'on'
        profesor_id = parse_int(request.form.get('profesor_id'))
        profesor = db.session.get(Profesor, profesor_id) if profesor_id else None
        if profesor and profesor.colegio_id != colegio.id:
            profesor = None
        fijado = request.form.get('profesor_fijado') == 'on'
        aula_id = parse_int(request.form.get('aula_requerida_id'))
        aula = db.session.get(Aula, aula_id) if aula_id else None
        if aula and aula.colegio_id != colegio.id:
            aula = None

        errors = []
        if not materia:
            errors.append('Seleccioná una materia válida.')
        elif materia.nivel_id != seccion.grado.nivel_id:
            errors.append('La materia pertenece a otro nivel.')
        elif materia.especialidades and (
                not seccion.especialidad or
                seccion.especialidad not in materia.especialidades):
            errors.append('La materia no pertenece a la especialidad de la sección.')
        if horas is None or horas < 1:
            errors.append('Las horas semanales deben ser mayores a cero.')
        if max_dia < 1:
            errors.append('El máximo por día debe ser mayor a cero.')
        if fijado and not profesor:
            errors.append('Para fijar un profesor tenés que seleccionarlo.')
        if profesor and materia and materia not in profesor.materias:
            errors.append('El profesor seleccionado no tiene habilitada esa materia.')
        if (profesor and materia and materia.especialidades and
                seccion.especialidad and
                seccion.especialidad not in profesor.especialidades):
            errors.append(
                'El profesor seleccionado no tiene la especialidad de la materia.'
            )
        if (materia and materia.area and materia.area.horas_max_semana
                and horas is not None and horas >= 1):
            area = materia.area
            total_area = 0
            for sm in SeccionMateria.query.filter_by(seccion_id=seccion.id).all():
                if edit is not None and sm.id == edit.id:
                    continue
                if sm.materia.area_id == area.id:
                    total_area += sm.horas_semanales
            if total_area + horas > area.horas_max_semana:
                errors.append(
                    f'El área {area.nombre} quedaría con '
                    f'{total_area + horas} h y su máximo es '
                    f'{area.horas_max_semana} h.'
                )
        if edit is None and materia and SeccionMateria.query.filter_by(
                seccion_id=seccion.id, materia_id=materia.id).first():
            errors.append('Esa materia ya está en el plan de la sección.')

        if errors:
            return render_template('schedule/seccion_plan.html',
                                   **_seccion_plan_ctx(seccion, edit=edit,
                                                       form=request.form,
                                                       errors=errors))

        es_nuevo = edit is None
        if es_nuevo:
            edit = SeccionMateria(seccion_id=seccion.id, materia_id=materia.id)
            db.session.add(edit)

        edit.horas_semanales = horas
        edit.max_bloques_por_dia = max_dia
        edit.requiere_bloque_doble = doble
        edit.profesor_id = profesor.id if profesor else None
        edit.profesor_fijado = bool(fijado and profesor)
        edit.aula_requerida_id = aula.id if aula else None

        try:
            db.session.commit()
            flash('Plan de la sección actualizado.', 'success')
        except IntegrityError:
            db.session.rollback()
            flash('No se pudo guardar la materia en el plan.', 'error')
            return redirect(url_for('seccion_plan', seccion_id=seccion.id))

        ctx = _seccion_plan_ctx(seccion)
        if ctx['total_horas'] > ctx['disponible']:
            flash(
                f'Atención: el plan suma {ctx["total_horas"]} horas y la plantilla '
                f'tiene {ctx["disponible"]} bloques de clase.',
                'warning',
            )

        return redirect(url_for('seccion_plan', seccion_id=seccion.id))

    @app.route('/secciones/<int:seccion_id>/plan/<int:sm_id>/eliminar',
               methods=['POST'])
    @login_required
    def seccion_plan_eliminar(seccion_id, sm_id):
        colegio = _colegio()
        if not colegio:
            return redirect(url_for('dashboard'))
        seccion = _seccion(seccion_id, colegio)
        item = db.session.get(SeccionMateria, sm_id)
        if not item or item.seccion_id != seccion.id:
            abort(404)

        try:
            db.session.delete(item)
            db.session.commit()
            flash('Materia quitada del plan.', 'success')
        except IntegrityError:
            db.session.rollback()
            flash('No se puede quitar: la materia tiene clases asignadas.', 'error')
        return redirect(url_for('seccion_plan', seccion_id=seccion.id))

    @app.route('/secciones/<int:seccion_id>/plan/sincronizar', methods=['POST'])
    @login_required
    def seccion_plan_sincronizar(seccion_id):
        colegio = _colegio()
        if not colegio:
            return redirect(url_for('dashboard'))
        seccion = _seccion(seccion_id, colegio)

        creados = actualizados = 0
        for gm in PlanMateria.query.filter_by(
                plan_id=seccion.plan_id, grado_id=seccion.grado_id).all():
            sm = SeccionMateria.query.filter_by(
                seccion_id=seccion.id, materia_id=gm.materia_id
            ).first()
            if sm:
                sm.horas_semanales = gm.horas_semanales
                sm.max_bloques_por_dia = gm.max_bloques_por_dia
                sm.requiere_bloque_doble = gm.requiere_bloque_doble
                actualizados += 1
            else:
                db.session.add(SeccionMateria(
                    seccion_id=seccion.id,
                    materia_id=gm.materia_id,
                    horas_semanales=gm.horas_semanales,
                    max_bloques_por_dia=gm.max_bloques_por_dia,
                    requiere_bloque_doble=gm.requiere_bloque_doble,
                ))
                creados += 1

        db.session.commit()
        flash(f'Plan sincronizado: {creados} nueva(s), {actualizados} actualizada(s).',
              'success')

        ctx = _seccion_plan_ctx(seccion)
        if ctx['total_horas'] > ctx['disponible']:
            flash(
                f'Atención: el plan suma {ctx["total_horas"]} horas y la plantilla '
                f'tiene {ctx["disponible"]} bloques de clase.',
                'warning',
            )

        return redirect(url_for('seccion_plan', seccion_id=seccion.id))
