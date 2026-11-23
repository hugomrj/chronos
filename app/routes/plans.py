from flask import abort, flash, redirect, render_template, request, url_for
from flask_login import login_required
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import (
    AreaConocimiento, Grado, GradoMateriaArea, Nivel, PlanEstudio, Seccion,
)
from app.utils.helpers import colegio_actual, parse_int


def register_plan_routes(app):
    """Áreas de conocimiento y planes de estudio."""

    def _colegio():
        colegio = colegio_actual()
        if not colegio:
            flash('Primero creá un colegio para continuar.', 'warning')
        return colegio

    def _areas_ctx(colegio, edit=None, form=None, errors=None):
        return dict(
            crumb='Áreas de conocimiento',
            items=AreaConocimiento.query.filter_by(colegio_id=colegio.id)
                                        .order_by(AreaConocimiento.orden,
                                                  AreaConocimiento.nombre).all(),
            edit=edit,
            form=form or {},
            errors=errors or [],
        )

    def _planes_ctx(colegio, edit=None, form=None, errors=None):
        niveles = Nivel.query.filter_by(colegio_id=colegio.id) \
                              .order_by(Nivel.nombre).all()
        grados = Grado.query.join(Nivel).filter(Nivel.colegio_id == colegio.id) \
                            .order_by(Nivel.nombre, Grado.orden, Grado.nombre).all()
        return dict(
            crumb='Planes de estudio',
            items=PlanEstudio.query.filter_by(colegio_id=colegio.id)
                                    .order_by(PlanEstudio.orden,
                                              PlanEstudio.nombre).all(),
            niveles=niveles,
            grados=grados,
            edit=edit,
            form=form or {},
            errors=errors or [],
        )

    # ------------------------------------------------------------------
    # ÁREAS DE CONOCIMIENTO
    # ------------------------------------------------------------------
    @app.route('/areas')
    @login_required
    def areas():
        colegio = _colegio()
        if not colegio:
            return redirect(url_for('colegios'))
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
            return redirect(url_for('colegios'))

        item_id = request.form.get('id', type=int)
        item = db.session.get(AreaConocimiento, item_id) if item_id else None
        if item and item.colegio_id != colegio.id:
            abort(404)

        nombre = (request.form.get('nombre') or '').strip()
        orden = parse_int(request.form.get('orden'), 0) or 0
        activa = request.form.get('activa') == 'on'

        errors = []
        if not nombre:
            errors.append('El nombre del área es obligatorio.')
        if orden < 0:
            errors.append('El orden no puede ser negativo.')
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
        item.orden = orden
        item.activa = activa

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
            return redirect(url_for('colegios'))
        item = db.get_or_404(AreaConocimiento, item_id)
        if item.colegio_id != colegio.id:
            abort(404)
        if GradoMateriaArea.query.filter_by(area_id=item.id).first():
            flash('No se puede eliminar: el área está asignada a materias de un plan.', 'error')
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
    # PLANES DE ESTUDIO
    # ------------------------------------------------------------------
    @app.route('/planes')
    @login_required
    def planes():
        colegio = _colegio()
        if not colegio:
            return redirect(url_for('colegios'))
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
            return redirect(url_for('colegios'))

        item_id = request.form.get('id', type=int)
        item = db.session.get(PlanEstudio, item_id) if item_id else None
        if item and item.colegio_id != colegio.id:
            abort(404)

        nombre = (request.form.get('nombre') or '').strip()
        nivel_id = parse_int(request.form.get('nivel_id'))
        nivel = db.session.get(Nivel, nivel_id) if nivel_id else None
        if nivel and nivel.colegio_id != colegio.id:
            nivel = None
        orden = parse_int(request.form.get('orden'), 0) or 0
        activo = request.form.get('activo') == 'on'
        grado_ids = [int(x) for x in request.form.getlist('grado_ids') if x.isdigit()]

        errors = []
        if not nombre:
            errors.append('El nombre del plan es obligatorio.')
        if not nivel:
            errors.append('Seleccioná un ciclo/nivel válido.')
        if orden < 0:
            errors.append('El orden no puede ser negativo.')
        existente = PlanEstudio.query.filter_by(
            colegio_id=colegio.id, nombre=nombre
        ).first()
        if existente and (item is None or existente.id != item.id):
            errors.append('Ya existe un plan con ese nombre en el colegio.')

        grados = []
        if nivel:
            grados = Grado.query.filter(Grado.id.in_(grado_ids),
                                        Grado.nivel_id == nivel.id).all() \
                                if grado_ids else []
            if grado_ids and len(grados) != len(set(grado_ids)):
                errors.append('Algún grado seleccionado no pertenece al ciclo elegido.')

        if errors:
            return render_template('academic/planes.html',
                                   **_planes_ctx(colegio, edit=item,
                                                 form=request.form, errors=errors))

        if item is None:
            item = PlanEstudio(colegio_id=colegio.id)
            db.session.add(item)
        item.nombre = nombre
        item.nivel_id = nivel.id
        item.orden = orden
        item.activo = activo
        db.session.flush()

        seleccionados = {g.id for g in grados}
        for grado in Grado.query.filter_by(plan_id=item.id).all():
            if grado.id not in seleccionados:
                grado.plan_id = None
        for grado in grados:
            grado.plan_id = item.id

        try:
            db.session.commit()
            flash('Plan de estudios guardado.', 'success')
        except IntegrityError:
            db.session.rollback()
            flash('No se pudo guardar el plan.', 'error')
        return redirect(url_for('planes'))

    @app.route('/planes/<int:item_id>/eliminar', methods=['POST'])
    @login_required
    def plan_eliminar(item_id):
        colegio = _colegio()
        if not colegio:
            return redirect(url_for('colegios'))
        item = db.get_or_404(PlanEstudio, item_id)
        if item.colegio_id != colegio.id:
            abort(404)
        secciones = Seccion.query.join(Grado).filter(Grado.plan_id == item.id).count()
        if secciones:
            flash('No se puede eliminar: hay secciones asociadas a este plan.', 'error')
            return redirect(url_for('planes'))
        Grado.query.filter_by(plan_id=item.id).update(
            {'plan_id': None}, synchronize_session=False
        )
        try:
            db.session.delete(item)
            db.session.commit()
            flash('Plan eliminado.', 'success')
        except IntegrityError:
            db.session.rollback()
            flash('No se puede eliminar el plan.', 'error')
        return redirect(url_for('planes'))
