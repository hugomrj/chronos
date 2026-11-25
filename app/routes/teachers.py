from flask import flash, redirect, render_template, request, url_for
from flask_login import login_required
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import (
    Especialidad, Materia, Profesor, ProfesorDisponibilidad, ProfesorHorasAnio,
    Seccion,
    SeccionMateria,
)
from app.utils.helpers import (
    DIAS_SEMANA, anio_activo, colegio_actual, parse_int, parse_time,
)


def register_teachers_routes(app):
    """CRUD de profesores y su disponibilidad horaria."""

    def _ctx_profesores(colegio, edit=None, form=None, errors=None, seleccionadas=None):
        materias = Materia.query.filter_by(colegio_id=colegio.id) \
                                 .join(Materia.nivel) \
                                 .order_by(Materia.nivel_id, Materia.nombre).all()
        por_nivel = {}
        for materia in materias:
            por_nivel.setdefault(materia.nivel, []).append(materia)
        return dict(
            crumb='Profesores',
            items=Profesor.query.filter_by(colegio_id=colegio.id)
                                .order_by(Profesor.nombre).all(),
            materias=materias,
            materias_por_nivel=por_nivel,
            especialidades=Especialidad.query.filter_by(
                colegio_id=colegio.id, activa=True
            ).order_by(Especialidad.nombre).all(),
            especialidades_sel=(set(edit.especialidades) if edit else set()),
            edit=edit,
            form=form or {},
            errors=errors or [],
            seleccionadas=seleccionadas if seleccionadas is not None else set(),
        )

    def _ctx_disponibilidad(colegio, profesor_id=None, form=None, errors=None):
        profesores = Profesor.query.filter_by(colegio_id=colegio.id) \
                                   .order_by(Profesor.nombre).all()
        selected = None
        if profesor_id:
            selected = db.session.get(Profesor, profesor_id)
            if selected and selected.colegio_id != colegio.id:
                selected = None
        if selected is None and profesores:
            selected = profesores[0]

        por_dia = {dia: [] for dia in DIAS_SEMANA}
        if selected:
            for b in sorted(selected.disponibilidad,
                            key=lambda b: (b.dia_semana, b.hora_desde)):
                por_dia.setdefault(b.dia_semana, []).append(b)

        return dict(
            crumb='Disponibilidad',
            profesores=profesores,
            selected=selected,
            por_dia=por_dia,
            dias=DIAS_SEMANA,
            form=form or {},
            errors=errors or [],
        )

    def _carga_anual(colegio_id, profesor_id, excluir_sm=None):
        anio = anio_activo(colegio_id)
        if not anio:
            return 0
        consulta = SeccionMateria.query.join(Seccion).filter(
            Seccion.anio_lectivo_id == anio.id,
            SeccionMateria.profesor_id == profesor_id,
        )
        if excluir_sm:
            consulta = consulta.filter(SeccionMateria.id != excluir_sm)
        return sum(sm.horas_semanales for sm in consulta.all())

    # ------------------------------------------------------------------
    # PROFESORES
    # ------------------------------------------------------------------
    @app.route('/profesores')
    @login_required
    def profesores():
        colegio = colegio_actual()
        if not colegio:
            flash('Primero creá un colegio para continuar.', 'warning')
            return redirect(url_for('colegios'))

        edit = None
        edit_id = request.args.get('editar', type=int)
        if edit_id:
            edit = db.session.get(Profesor, edit_id)
            if edit and edit.colegio_id != colegio.id:
                edit = None

        seleccionadas = {str(m.id) for m in edit.materias} if edit else set()
        return render_template('teachers/profesores.html',
                               **_ctx_profesores(colegio, edit=edit,
                                                 seleccionadas=seleccionadas))

    @app.route('/profesores/guardar', methods=['POST'])
    @login_required
    def profesor_guardar():
        colegio = colegio_actual()
        if not colegio:
            flash('Primero creá un colegio para continuar.', 'warning')
            return redirect(url_for('colegios'))

        item_id = request.form.get('id', type=int)
        item = db.session.get(Profesor, item_id) if item_id else None
        if item and item.colegio_id != colegio.id:
            item = None

        nombre = (request.form.get('nombre') or '').strip()
        documento = (request.form.get('documento') or '').strip() or None
        contacto = (request.form.get('contacto') or '').strip() or None
        h_max = parse_int(request.form.get('horas_max_semana')) if request.form.get('horas_max_semana') else None
        activo = request.form.get('activo') == 'on'

        especialidades_ids = request.form.getlist('especialidades')
        especialidades = []
        if especialidades_ids:
            especialidades = Especialidad.query.filter(
                Especialidad.id.in_([int(x) for x in especialidades_ids if x.isdigit()]),
                Especialidad.colegio_id == colegio.id,
            ).all()

        materias_ids = request.form.getlist('materias')
        materias = []
        if materias_ids:
            materias = Materia.query.filter(
                Materia.id.in_([int(x) for x in materias_ids if x.isdigit()]),
                Materia.colegio_id == colegio.id,
            ).all()

        errors = []
        if not nombre:
            errors.append('El nombre del profesor es obligatorio.')
        if h_max is not None and h_max < 0:
            errors.append('Las horas semanales no pueden ser negativas.')
        if item is not None and h_max is not None:
            carga_actual = _carga_anual(colegio.id, item.id)
            if carga_actual > h_max:
                errors.append(
                    f'La carga actual del profesor es de {carga_actual} h y '
                    f'no puede bajar su máximo semanal a {h_max} h.'
                )

        if errors:
            return render_template(
                'teachers/profesores.html',
                **_ctx_profesores(colegio, edit=item, form=request.form,
                                  errors=errors,
                                  seleccionadas=set(request.form.getlist('materias'))),
            )

        if item is None:
            item = Profesor(colegio_id=colegio.id)
            db.session.add(item)

        item.nombre = nombre
        item.documento = documento
        item.contacto = contacto
        item.horas_max_semana = h_max
        item.activo = activo
        item.materias = materias
        item.especialidades = especialidades

        anio = anio_activo(colegio.id)
        if anio and h_max is not None:
            registro = next(
                (h for h in item.horas_anio if h.anio_lectivo_id == anio.id),
                None,
            )
            if registro is None:
                item.horas_anio.append(ProfesorHorasAnio(
                    anio_lectivo_id=anio.id, horas_max_semana=h_max,
                ))
            else:
                registro.horas_max_semana = h_max

        try:
            db.session.commit()
            flash('Profesor guardado correctamente.', 'success')
        except IntegrityError:
            db.session.rollback()
            flash('No se pudo guardar. Revisá el documento duplicado.', 'error')

        return redirect(url_for('profesores'))

    @app.route('/profesores/<int:item_id>/eliminar', methods=['POST'])
    @login_required
    def profesor_eliminar(item_id):
        item = db.get_or_404(Profesor, item_id)
        try:
            db.session.delete(item)
            db.session.commit()
            flash('Profesor eliminado.', 'success')
        except IntegrityError:
            db.session.rollback()
            flash('No se puede eliminar: el profesor tiene asignaciones en horarios.', 'error')
        return redirect(url_for('profesores'))

    # ------------------------------------------------------------------
    # DISPONIBILIDAD
    # ------------------------------------------------------------------
    @app.route('/disponibilidad')
    @login_required
    def disponibilidad():
        colegio = colegio_actual()
        if not colegio:
            flash('Primero creá un colegio para continuar.', 'warning')
            return redirect(url_for('colegios'))

        profesor_id = request.args.get('profesor_id', type=int)
        return render_template('teachers/disponibilidad.html',
                               **_ctx_disponibilidad(colegio, profesor_id=profesor_id))

    @app.route('/disponibilidad/guardar', methods=['POST'])
    @login_required
    def disponibilidad_guardar():
        colegio = colegio_actual()
        if not colegio:
            flash('Primero creá un colegio para continuar.', 'warning')
            return redirect(url_for('colegios'))

        profesor_id = request.form.get('profesor_id', type=int)
        profesor = db.session.get(Profesor, profesor_id) if profesor_id else None
        if not profesor or profesor.colegio_id != colegio.id:
            flash('Seleccioná un profesor válido.', 'error')
            return redirect(url_for('disponibilidad'))

        dia = parse_int(request.form.get('dia_semana'))
        desde = parse_time(request.form.get('hora_desde'))
        hasta = parse_time(request.form.get('hora_hasta'))
        tipo = request.form.get('tipo') or 'disponible'
        motivo = (request.form.get('motivo') or '').strip() or None

        errors = []
        if dia not in DIAS_SEMANA:
            errors.append('Seleccioná un día válido.')
        if not desde or not hasta:
            errors.append('Completá la hora de inicio y de fin.')
        elif hasta <= desde:
            errors.append('La hora de fin debe ser posterior a la de inicio.')
        if tipo not in ('disponible', 'no_disponible'):
            errors.append('El tipo de franja no es válido.')

        if not errors:
            conflicto = ProfesorDisponibilidad.query.filter(
                ProfesorDisponibilidad.profesor_id == profesor.id,
                ProfesorDisponibilidad.dia_semana == dia,
                ProfesorDisponibilidad.hora_desde < hasta,
                ProfesorDisponibilidad.hora_hasta > desde,
            ).first()
            if conflicto:
                errors.append(
                    f'La franja se solapa con otra existente '
                    f'({conflicto.hora_desde.strftime("%H:%M")}–'
                    f'{conflicto.hora_hasta.strftime("%H:%M")}).'
                )

        if errors:
            return render_template(
                'teachers/disponibilidad.html',
                **_ctx_disponibilidad(colegio, profesor_id=profesor.id,
                                      form=request.form, errors=errors),
            )

        bloque = ProfesorDisponibilidad(
            profesor_id=profesor.id,
            dia_semana=dia,
            hora_desde=desde,
            hora_hasta=hasta,
            tipo=tipo,
            motivo=motivo,
        )
        db.session.add(bloque)
        db.session.commit()
        flash('Franja de disponibilidad agregada.', 'success')
        return redirect(url_for('disponibilidad', profesor_id=profesor.id))

    @app.route('/disponibilidad/<int:item_id>/eliminar', methods=['POST'])
    @login_required
    def disponibilidad_eliminar(item_id):
        bloque = db.get_or_404(ProfesorDisponibilidad, item_id)
        profesor_id = bloque.profesor_id
        try:
            db.session.delete(bloque)
            db.session.commit()
            flash('Franja eliminada.', 'success')
        except IntegrityError:
            db.session.rollback()
            flash('No se pudo eliminar la franja.', 'error')
        return redirect(url_for('disponibilidad', profesor_id=profesor_id))
