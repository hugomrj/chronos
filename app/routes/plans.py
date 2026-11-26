from flask import abort, flash, redirect, render_template, request, url_for
from flask_login import login_required
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import (
    AreaConocimiento, Especialidad, Grado, Nivel, PlanEstudio, PlanGrado,
    PlanMateria, Seccion,
)
from app.utils.helpers import parse_int
from app.utils.colegio import colegio_actual


def register_plan_routes(app):
    def _colegio():
        colegio = colegio_actual()
        if not colegio:
            flash('Primero creá un colegio para continuar.', 'warning')
        return colegio

    def _areas_ctx(colegio, edit=None, form=None, errors=None):
        return dict(
            crumb='Áreas de conocimiento',
            items=AreaConocimiento.query.filter_by(colegio_id=colegio.id)
                                        .order_by(AreaConocimiento.nombre).all(),
            edit=edit, form=form or {}, errors=errors or [],
        )

    def _especialidades_ctx(colegio, edit=None, form=None, errors=None):
        return dict(
            crumb='Especialidades',
            items=Especialidad.query.filter_by(colegio_id=colegio.id)
                                    .order_by(Especialidad.nombre).all(),
            niveles=Nivel.query.filter_by(colegio_id=colegio.id)
                               .order_by(Nivel.nombre).all(),
            edit=edit, form=form or {}, errors=errors or [],
        )

    def _planes_ctx(colegio, edit=None, form=None, errors=None):
        return dict(
            crumb='Planes de estudio',
            items=PlanEstudio.query.filter_by(colegio_id=colegio.id)
                                   .order_by(PlanEstudio.nombre).all(),
            niveles=Nivel.query.filter_by(colegio_id=colegio.id)
                               .order_by(Nivel.nombre).all(),
            especialidades=Especialidad.query.filter_by(
                colegio_id=colegio.id, activa=True
            ).order_by(Especialidad.nombre).all(),
            grados=Grado.query.join(Nivel).filter(
                Nivel.colegio_id == colegio.id
            ).order_by(Nivel.nombre, Grado.nombre).all(),
            edit=edit, form=form or {}, errors=errors or [],
        )

    # ------------------------------------------------------------------
    # ÁREAS
    # ------------------------------------------------------------------
    @app.route('/areas')
    @login_required
    def areas():
        colegio = _colegio()
        if not colegio:
            return redirect(url_for('dashboard'))
        edit_id = request.args.get('editar', type=int)
        return render_template(
            'academic/areas.html',
            **_areas_ctx(colegio, edit=db.session.get(AreaConocimiento, edit_id)
                         if edit_id else None),
        )

    @app.route('/areas/guardar', methods=['POST'])
    @login_required
    def area_guardar():
        colegio = _colegio()
        if not colegio:
            return redirect(url_for('dashboard'))
        item_id = request.form.get('id', type=int)
        item = db.session.get(AreaConocimiento, item_id) if item_id else None
        if item and item.colegio_id != colegio.id:
            abort(404)

        nombre = (request.form.get('nombre') or '').strip()
        activa = request.form.get('activa') == 'on'
        raw_horas = (request.form.get('horas_max_semana') or '').strip()
        horas_max = parse_int(raw_horas) if raw_horas else None

        errors = []
        if not nombre:
            errors.append('El nombre del área es obligatorio.')
        if horas_max is not None and horas_max < 1:
            errors.append('El máximo de horas debe ser mayor a cero.')
        if item is not None and horas_max is not None and item.materias:
            totales = {}
            for pm in PlanMateria.query.filter(
                    PlanMateria.materia_id.in_([m.id for m in item.materias])).all():
                totales[(pm.plan_id, pm.grado_id)] = (
                    totales.get((pm.plan_id, pm.grado_id), 0) + pm.horas_semanales
                )
            if any(total > horas_max for total in totales.values()):
                errors.append(
                    'El máximo no puede ser menor a las horas ya asignadas '
                    'en algún plan/curso.'
                )
        existente = AreaConocimiento.query.filter_by(
            colegio_id=colegio.id, nombre=nombre
        ).first()
        if existente and (item is None or existente.id != item.id):
            errors.append('Ya existe un área con ese nombre en el colegio.')

        if errors:
            return render_template('academic/areas.html',
                                   **_areas_ctx(colegio, edit=item,
                                               form=request.form, errors=errors))

        if item is None:
            item = AreaConocimiento(colegio_id=colegio.id)
            db.session.add(item)
        item.nombre = nombre
        item.activa = activa
        item.horas_max_semana = horas_max
        try:
            db.session.commit()
            flash('Área de conocimiento guardada.', 'success')
        except IntegrityError:
            db.session.rollback()
            flash('No se pudo guardar el área.', 'error')
        return redirect(url_for('areas'))

    @app.route('/areas/<int:item_id>/eliminar', methods=['POST'])
    @login_required
    def area_eliminar(item_id):
        colegio = _colegio()
        if not colegio:
            return redirect(url_for('dashboard'))
        item = db.get_or_404(AreaConocimiento, item_id)
        if item.colegio_id != colegio.id:
            abort(404)
        if item.materias:
            flash('No se puede eliminar: el área está asignada a materias.', 'error')
            return redirect(url_for('areas'))
        try:
            db.session.delete(item)
            db.session.commit()
            flash('Área eliminada.', 'success')
        except IntegrityError:
            db.session.rollback()
            flash('No se puede eliminar el área.', 'error')
        return redirect(url_for('areas'))

    # ------------------------------------------------------------------
    # ESPECIALIDADES
    # ------------------------------------------------------------------
    @app.route('/especialidades')
    @login_required
    def especialidades():
        colegio = _colegio()
        if not colegio:
            return redirect(url_for('dashboard'))
        edit_id = request.args.get('editar', type=int)
        return render_template(
            'academic/especialidades.html',
            **_especialidades_ctx(colegio,
                                  edit=db.session.get(Especialidad, edit_id)
                                  if edit_id else None),
        )

    @app.route('/especialidades/guardar', methods=['POST'])
    @login_required
    def especialidad_guardar():
        colegio = _colegio()
        if not colegio:
            return redirect(url_for('dashboard'))
        item_id = request.form.get('id', type=int)
        item = db.session.get(Especialidad, item_id) if item_id else None
        if item and item.colegio_id != colegio.id:
            abort(404)

        nombre = (request.form.get('nombre') or '').strip()
        nivel_id = parse_int(request.form.get('nivel_id'))
        nivel = db.session.get(Nivel, nivel_id) if nivel_id else None
        if nivel and nivel.colegio_id != colegio.id:
            nivel = None
        codigo = (request.form.get('codigo') or '').strip() or None
        activa = request.form.get('activa') == 'on'

        errors = []
        if not nombre:
            errors.append('El nombre es obligatorio.')
        if not nivel:
            errors.append('Seleccioná un nivel.')
        existente = Especialidad.query.filter_by(
            colegio_id=colegio.id, nombre=nombre).first()
        if existente and (item is None or existente.id != item.id):
            errors.append('Ya existe una especialidad con ese nombre.')

        if errors:
            return render_template('academic/especialidades.html',
                                   **_especialidades_ctx(colegio, edit=item,
                                                         form=request.form,
                                                         errors=errors))
        if item is None:
            item = Especialidad(colegio_id=colegio.id)
            db.session.add(item)
        item.nombre = nombre
        item.nivel_id = nivel.id
        item.codigo = codigo
        item.activa = activa
        try:
            db.session.commit()
            flash('Especialidad guardada.', 'success')
        except IntegrityError:
            db.session.rollback()
            flash('No se pudo guardar la especialidad.', 'error')
        return redirect(url_for('especialidades'))

    @app.route('/especialidades/<int:item_id>/eliminar', methods=['POST'])
    @login_required
    def especialidad_eliminar(item_id):
        colegio = _colegio()
        if not colegio:
            return redirect(url_for('dashboard'))
        item = db.get_or_404(Especialidad, item_id)
        if item.colegio_id != colegio.id:
            abort(404)
        if item.planes or item.secciones:
            flash('No se puede eliminar: está asignada a planes o secciones.', 'error')
            return redirect(url_for('especialidades'))
        try:
            db.session.delete(item)
            db.session.commit()
            flash('Especialidad eliminada.', 'success')
        except IntegrityError:
            db.session.rollback()
            flash('No se puede eliminar la especialidad.', 'error')
        return redirect(url_for('especialidades'))

    # ------------------------------------------------------------------
    # PLANES
    # ------------------------------------------------------------------
    @app.route('/planes')
    @login_required
    def planes():
        colegio = _colegio()
        if not colegio:
            return redirect(url_for('dashboard'))
        edit_id = request.args.get('editar', type=int)
        return render_template(
            'academic/planes.html',
            **_planes_ctx(colegio, edit=db.session.get(PlanEstudio, edit_id)
                         if edit_id else None),
        )

    @app.route('/planes/guardar', methods=['POST'])
    @login_required
    def plan_guardar():
        colegio = _colegio()
        if not colegio:
            return redirect(url_for('dashboard'))
        item_id = request.form.get('id', type=int)
        item = db.session.get(PlanEstudio, item_id) if item_id else None
        if item and item.colegio_id != colegio.id:
            abort(404)

        nombre = (request.form.get('nombre') or '').strip()
        nivel_id = parse_int(request.form.get('nivel_id'))
        nivel = db.session.get(Nivel, nivel_id) if nivel_id else None
        if nivel and nivel.colegio_id != colegio.id:
            nivel = None
        especialidad_id = parse_int(request.form.get('especialidad_id'))
        especialidad = db.session.get(Especialidad, especialidad_id) \
            if especialidad_id else None
        if especialidad and especialidad.colegio_id != colegio.id:
            especialidad = None
        activo = request.form.get('activo') == 'on'
        grado_ids = [int(x) for x in request.form.getlist('grado_ids') if x.isdigit()]

        errors = []
        if not nombre:
            errors.append('El nombre del plan es obligatorio.')
        if not nivel:
            errors.append('Seleccioná un nivel válido.')
        if especialidad and (not nivel or especialidad.nivel_id != nivel.id):
            errors.append('La especialidad no pertenece al nivel elegido.')
        # El nombre se repite por especialidad: la clave es nombre + nivel + especialidad.
        existente = PlanEstudio.query.filter(
            PlanEstudio.colegio_id == colegio.id,
            PlanEstudio.nombre == nombre,
            PlanEstudio.nivel_id == (nivel.id if nivel else None),
            PlanEstudio.especialidad_id == (especialidad.id if especialidad else None),
        ).first()
        if existente and (item is None or existente.id != item.id):
            detalle = f'en {especialidad.nombre}' if especialidad else 'sin especialidad'
            errors.append(
                f'Ya existe un plan «{nombre}» {detalle} en ese nivel.'
            )

        grados = []
        if nivel and grado_ids:
            grados = Grado.query.filter(
                Grado.id.in_(grado_ids), Grado.nivel_id == nivel.id).all()
            if len(grados) != len(set(grado_ids)):
                errors.append('Algún curso no pertenece al nivel elegido.')

        if errors:
            return render_template('academic/planes.html',
                                   **_planes_ctx(colegio, edit=item,
                                                 form=request.form, errors=errors))
        if item is None:
            item = PlanEstudio(colegio_id=colegio.id)
            db.session.add(item)
        item.nombre = nombre
        item.nivel_id = nivel.id
        item.especialidad_id = especialidad.id if especialidad else None
        item.activo = activo
        db.session.flush()

        PlanGrado.query.filter_by(plan_id=item.id).delete(
            synchronize_session=False)
        for grado in grados:
            db.session.add(PlanGrado(plan_id=item.id, grado_id=grado.id))
        try:
            db.session.commit()
            flash('Plan de estudios guardado.', 'success')
        except IntegrityError:
            db.session.rollback()
            flash('No se pudo guardar el plan.', 'error')
        return redirect(url_for('planes'))

    @app.route('/planes/<int:item_id>')
    @login_required
    def plan_detalle(item_id):
        colegio = _colegio()
        plan = db.get_or_404(PlanEstudio, item_id)
        if plan.colegio_id != colegio.id:
            abort(404)
        grados = sorted(plan.grados, key=lambda g: g.nombre)
        datos = []
        for grado in grados:
            datos.append({
                'grado': grado,
                'materias': PlanMateria.query.filter_by(
                    plan_id=plan.id, grado_id=grado.id).count(),
            })
        return render_template('academic/plan_detalle.html',
                               crumb=plan.nombre, plan=plan, grados=datos)

    @app.route('/planes/<int:item_id>/eliminar', methods=['POST'])
    @login_required
    def plan_eliminar(item_id):
        colegio = _colegio()
        if not colegio:
            return redirect(url_for('dashboard'))
        item = db.get_or_404(PlanEstudio, item_id)
        if item.colegio_id != colegio.id:
            abort(404)
        if Seccion.query.filter_by(plan_id=item.id).first():
            flash('No se puede eliminar: hay secciones asociadas a este plan.', 'error')
            return redirect(url_for('planes'))
        try:
            db.session.delete(item)
            db.session.commit()
            flash('Plan eliminado.', 'success')
        except IntegrityError:
            db.session.rollback()
            flash('No se puede eliminar el plan.', 'error')
        return redirect(url_for('planes'))
