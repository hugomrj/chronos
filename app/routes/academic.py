from flask import abort, flash, redirect, render_template, request, url_for
from flask_login import login_required
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import (
    AnioLectivo, AreaConocimiento, Aula, Colegio, Especialidad, Grado, Materia,
    Nivel, Turno,
)
from app.utils.helpers import (
    TIPOS_AULA, TIPOS_AULA_LABEL, parse_date, parse_int,
)
from app.utils.colegio import colegio_actual



def register_academic_routes(app):
    """CRUD de la estructura académica."""

    def _colegio_o_none():
        colegio = colegio_actual()
        if not colegio:
            flash('Primero creá un colegio para continuar.', 'warning')
        return colegio

    def _get(model, key='editar'):
        item_id = request.args.get(key, type=int)
        return db.session.get(model, item_id) if item_id else None

    # ------------------------------------------------------------------
    # AÑOS LECTIVOS
    # ------------------------------------------------------------------
    @app.route('/anios')
    @login_required
    def anios():
        colegio = _colegio_o_none()
        if not colegio:
            return redirect(url_for('dashboard'))
        return render_template(
            'academic/anios.html',
            crumb='Años lectivos',
            items=AnioLectivo.query.filter_by(colegio_id=colegio.id)
                                   .order_by(AnioLectivo.nombre.desc()).all(),
            edit=_get(AnioLectivo),
            form={},
            errors=[],
        )

    @app.route('/anios/guardar', methods=['POST'])
    @login_required
    def anio_guardar():
        colegio = _colegio_o_none()
        if not colegio:
            return redirect(url_for('dashboard'))

        item_id = request.form.get('id', type=int)
        item = db.session.get(AnioLectivo, item_id) if item_id else None

        nombre = (request.form.get('nombre') or '').strip()
        fecha_inicio = parse_date(request.form.get('fecha_inicio'))
        fecha_fin = parse_date(request.form.get('fecha_fin'))
        activo = request.form.get('activo') == 'on'

        errors = []
        if not nombre:
            errors.append('El nombre del año lectivo es obligatorio.')
        if not fecha_inicio or not fecha_fin:
            errors.append('Las fechas de inicio y fin son obligatorias.')
        elif fecha_fin <= fecha_inicio:
            errors.append('La fecha de fin debe ser posterior a la de inicio.')

        if errors:
            return render_template(
                'academic/anios.html', crumb='Años lectivos',
                items=AnioLectivo.query.filter_by(colegio_id=colegio.id)
                                       .order_by(AnioLectivo.nombre.desc()).all(),
                edit=item, form=request.form, errors=errors,
            )

        if item is None:
            item = AnioLectivo(colegio_id=colegio.id)
            db.session.add(item)

        item.nombre = nombre
        item.fecha_inicio = fecha_inicio
        item.fecha_fin = fecha_fin

        if activo:
            AnioLectivo.query.filter(
                AnioLectivo.colegio_id == colegio.id,
                AnioLectivo.activo.is_(True),
                AnioLectivo.id != (item.id or -1),
            ).update({'activo': False}, synchronize_session=False)
            item.activo = True
        else:
            item.activo = False

        try:
            db.session.commit()
            flash('Año lectivo guardado correctamente.', 'success')
        except IntegrityError:
            db.session.rollback()
            flash('No se pudo guardar el año lectivo. Verificá el nombre y las fechas.', 'error')

        return redirect(url_for('anios'))

    @app.route('/anios/<int:item_id>/activar', methods=['POST'])
    @login_required
    def anio_activar(item_id):
        item = db.get_or_404(AnioLectivo, item_id)
        AnioLectivo.query.filter(
            AnioLectivo.colegio_id == item.colegio_id,
            AnioLectivo.activo.is_(True),
            AnioLectivo.id != item.id,
        ).update({'activo': False}, synchronize_session=False)
        item.activo = True
        try:
            db.session.commit()
            flash(f'Año {item.nombre} activado.', 'success')
        except IntegrityError:
            db.session.rollback()
            flash('No se pudo activar el año lectivo.', 'error')
        return redirect(url_for('anios'))

    @app.route('/anios/<int:item_id>/eliminar', methods=['POST'])
    @login_required
    def anio_eliminar(item_id):
        item = db.get_or_404(AnioLectivo, item_id)
        try:
            db.session.delete(item)
            db.session.commit()
            flash('Año lectivo eliminado.', 'success')
        except IntegrityError:
            db.session.rollback()
            flash('No se puede eliminar: tiene secciones u horarios asociados.', 'error')
        return redirect(url_for('anios'))

    # ------------------------------------------------------------------
    # NIVELES
    # ------------------------------------------------------------------
    @app.route('/niveles')
    @login_required
    def niveles():
        colegio = _colegio_o_none()
        if not colegio:
            return redirect(url_for('dashboard'))
        return render_template(
            'academic/niveles.html', crumb='Niveles',
            items=Nivel.query.filter_by(colegio_id=colegio.id)
                              .order_by(Nivel.nombre).all(),
            edit=_get(Nivel), form={}, errors=[],
        )

    @app.route('/niveles/guardar', methods=['POST'])
    @login_required
    def nivel_guardar():
        colegio = _colegio_o_none()
        if not colegio:
            return redirect(url_for('dashboard'))

        item_id = request.form.get('id', type=int)
        item = db.session.get(Nivel, item_id) if item_id else None
        nombre = (request.form.get('nombre') or '').strip()

        errors = []
        if not nombre:
            errors.append('El nombre del nivel es obligatorio.')
        if errors:
            return render_template(
                'academic/niveles.html', crumb='Niveles',
                items=Nivel.query.filter_by(colegio_id=colegio.id)
                                  .order_by(Nivel.nombre).all(),
                edit=item, form=request.form, errors=errors,
            )

        if item:
            item.nombre = nombre
        else:
            item = Nivel(colegio_id=colegio.id, nombre=nombre)
            db.session.add(item)

        try:
            db.session.commit()
            flash('Nivel guardado correctamente.', 'success')
        except IntegrityError:
            db.session.rollback()
            flash('Ya existe un nivel con ese nombre en el colegio.', 'error')
        return redirect(url_for('niveles'))

    @app.route('/niveles/<int:item_id>/eliminar', methods=['POST'])
    @login_required
    def nivel_eliminar(item_id):
        item = db.get_or_404(Nivel, item_id)
        try:
            db.session.delete(item)
            db.session.commit()
            flash('Nivel eliminado.', 'success')
        except IntegrityError:
            db.session.rollback()
            flash('No se puede eliminar: el nivel tiene grados asociados.', 'error')
        return redirect(url_for('niveles'))

    # ------------------------------------------------------------------
    # GRADOS
    # ------------------------------------------------------------------
    @app.route('/grados')
    @login_required
    def grados():
        colegio = _colegio_o_none()
        if not colegio:
            return redirect(url_for('dashboard'))

        nivel = None
        nivel_id = request.args.get('nivel_id', type=int)
        if nivel_id:
            nivel = db.session.get(Nivel, nivel_id)
            if nivel and nivel.colegio_id != colegio.id:
                nivel = None

        consulta = Grado.query.join(Nivel).filter(Nivel.colegio_id == colegio.id)
        if nivel:
            consulta = consulta.filter(Grado.nivel_id == nivel.id)

        return render_template(
            'academic/grados.html', crumb='Grados / Cursos',
            items=consulta.order_by(Nivel.nombre, Grado.nombre).all(),
            niveles=Nivel.query.filter_by(colegio_id=colegio.id)
                               .order_by(Nivel.nombre).all(),
            especialidades=Especialidad.query.filter_by(
                colegio_id=colegio.id, activa=True).order_by(Especialidad.nombre).all(),
            nivel=nivel,
            edit=_get(Grado), form={}, errors=[],
        )

    @app.route('/grados/guardar', methods=['POST'])
    @login_required
    def grado_guardar():
        colegio = _colegio_o_none()
        if not colegio:
            return redirect(url_for('dashboard'))

        item_id = request.form.get('id', type=int)
        item = db.session.get(Grado, item_id) if item_id else None

        nombre = (request.form.get('nombre') or '').strip()
        nivel_id = parse_int(request.form.get('nivel_id'))
        especialidad_id = parse_int(request.form.get('especialidad_id'))

        nivel = db.session.get(Nivel, nivel_id) if nivel_id else None
        if nivel and nivel.colegio_id != colegio.id:
            nivel = None
        especialidad = db.session.get(Especialidad, especialidad_id) \
            if especialidad_id else None
        if especialidad and especialidad.colegio_id != colegio.id:
            especialidad = None

        errors = []
        if not nombre:
            errors.append('El nombre del grado es obligatorio.')
        if not nivel:
            errors.append('Seleccioná un nivel válido.')
        if especialidad and (not nivel or especialidad.nivel_id != nivel.id):
            errors.append('La especialidad no pertenece al nivel elegido.')

        if errors:
            return render_template(
                'academic/grados.html', crumb='Grados / Cursos',
                items=Grado.query.join(Nivel).filter(Nivel.colegio_id == colegio.id)
                                 .order_by(Nivel.nombre, Grado.nombre).all(),
                niveles=Nivel.query.filter_by(colegio_id=colegio.id)
                                   .order_by(Nivel.nombre).all(),
                especialidades=Especialidad.query.filter_by(
                    colegio_id=colegio.id, activa=True
                ).order_by(Especialidad.nombre).all(),
                edit=item, form=request.form, errors=errors,
            )

        if item:
            item.nombre = nombre
            item.nivel_id = nivel.id
            item.especialidad_id = especialidad.id if especialidad else None
        else:
            item = Grado(nivel_id=nivel.id, nombre=nombre,
                         especialidad_id=especialidad.id if especialidad else None)
            db.session.add(item)

        try:
            db.session.commit()
            flash('Grado guardado correctamente.', 'success')
        except IntegrityError:
            db.session.rollback()
            flash('Ya existe un grado con ese nombre en el nivel.', 'error')
        return redirect(url_for('grados'))

    @app.route('/grados/<int:item_id>/eliminar', methods=['POST'])
    @login_required
    def grado_eliminar(item_id):
        item = db.get_or_404(Grado, item_id)
        try:
            db.session.delete(item)
            db.session.commit()
            flash('Grado eliminado.', 'success')
        except IntegrityError:
            db.session.rollback()
            flash('No se puede eliminar: el grado tiene materias o secciones asociadas.', 'error')
        return redirect(url_for('grados'))

    # ------------------------------------------------------------------
    # TURNOS
    # ------------------------------------------------------------------
    @app.route('/turnos')
    @login_required
    def turnos():
        colegio = _colegio_o_none()
        if not colegio:
            return redirect(url_for('dashboard'))
        return render_template(
            'academic/turnos.html', crumb='Turnos',
            items=Turno.query.filter_by(colegio_id=colegio.id)
                              .order_by(Turno.nombre).all(),
            edit=_get(Turno), form={}, errors=[],
        )

    @app.route('/turnos/guardar', methods=['POST'])
    @login_required
    def turno_guardar():
        colegio = _colegio_o_none()
        if not colegio:
            return redirect(url_for('dashboard'))

        item_id = request.form.get('id', type=int)
        item = db.session.get(Turno, item_id) if item_id else None
        nombre = (request.form.get('nombre') or '').strip()

        errors = []
        if not nombre:
            errors.append('El nombre del turno es obligatorio.')
        if errors:
            return render_template(
                'academic/turnos.html', crumb='Turnos',
                items=Turno.query.filter_by(colegio_id=colegio.id)
                                  .order_by(Turno.nombre).all(),
                edit=item, form=request.form, errors=errors,
            )

        if item:
            item.nombre = nombre
        else:
            item = Turno(colegio_id=colegio.id, nombre=nombre)
            db.session.add(item)

        try:
            db.session.commit()
            flash('Turno guardado correctamente.', 'success')
        except IntegrityError:
            db.session.rollback()
            flash('Ya existe un turno con ese nombre.', 'error')
        return redirect(url_for('turnos'))

    @app.route('/turnos/<int:item_id>/eliminar', methods=['POST'])
    @login_required
    def turno_eliminar(item_id):
        item = db.get_or_404(Turno, item_id)
        try:
            db.session.delete(item)
            db.session.commit()
            flash('Turno eliminado.', 'success')
        except IntegrityError:
            db.session.rollback()
            flash('No se puede eliminar: el turno tiene plantillas o secciones.', 'error')
        return redirect(url_for('turnos'))

    # ------------------------------------------------------------------
    # AULAS
    # ------------------------------------------------------------------
    @app.route('/aulas')
    @login_required
    def aulas():
        colegio = _colegio_o_none()
        if not colegio:
            return redirect(url_for('dashboard'))
        return render_template(
            'academic/aulas.html', crumb='Aulas',
            items=Aula.query.filter_by(colegio_id=colegio.id)
                             .order_by(Aula.nombre).all(),
            tipos=TIPOS_AULA, tipos_label=TIPOS_AULA_LABEL,
            edit=_get(Aula), form={}, errors=[],
        )

    @app.route('/aulas/guardar', methods=['POST'])
    @login_required
    def aula_guardar():
        colegio = _colegio_o_none()
        if not colegio:
            return redirect(url_for('dashboard'))

        item_id = request.form.get('id', type=int)
        item = db.session.get(Aula, item_id) if item_id else None

        nombre = (request.form.get('nombre') or '').strip()
        tipo = request.form.get('tipo') or 'regular'
        capacidad = parse_int(request.form.get('capacidad')) if request.form.get('capacidad') else None
        activa = request.form.get('activa') == 'on'

        errors = []
        if not nombre:
            errors.append('El nombre del aula es obligatorio.')
        if tipo not in TIPOS_AULA:
            errors.append('El tipo de aula no es válido.')
        if capacidad is not None and capacidad < 0:
            errors.append('La capacidad no puede ser negativa.')

        if errors:
            return render_template(
                'academic/aulas.html', crumb='Aulas',
                items=Aula.query.filter_by(colegio_id=colegio.id)
                                 .order_by(Aula.nombre).all(),
                tipos=TIPOS_AULA, tipos_label=TIPOS_AULA_LABEL,
                edit=item, form=request.form, errors=errors,
            )

        if item:
            item.nombre = nombre
            item.tipo = tipo
            item.capacidad = capacidad
            item.activa = activa
        else:
            item = Aula(colegio_id=colegio.id, nombre=nombre, tipo=tipo,
                        capacidad=capacidad, activa=activa)
            db.session.add(item)

        try:
            db.session.commit()
            flash('Aula guardada correctamente.', 'success')
        except IntegrityError:
            db.session.rollback()
            flash('Ya existe un aula con ese nombre en el colegio.', 'error')
        return redirect(url_for('aulas'))

    @app.route('/aulas/<int:item_id>/eliminar', methods=['POST'])
    @login_required
    def aula_eliminar(item_id):
        item = db.get_or_404(Aula, item_id)
        try:
            db.session.delete(item)
            db.session.commit()
            flash('Aula eliminada.', 'success')
        except IntegrityError:
            db.session.rollback()
            flash('No se puede eliminar: el aula está siendo usada en secciones u horarios.', 'error')
        return redirect(url_for('aulas'))

    # ------------------------------------------------------------------
    # MATERIAS
    # ------------------------------------------------------------------
    @app.route('/materias')
    @login_required
    def materias():
        colegio = _colegio_o_none()
        if not colegio:
            return redirect(url_for('dashboard'))

        area = None
        area_id = request.args.get('area_id', type=int)
        if area_id:
            area = db.session.get(AreaConocimiento, area_id)
            if area and area.colegio_id != colegio.id:
                area = None

        consulta = Materia.query.filter_by(colegio_id=colegio.id)
        if area:
            consulta = consulta.filter(Materia.area_id == area.id)

        edit = _get(Materia)
        areas = AreaConocimiento.query.filter_by(
            colegio_id=colegio.id
        ).order_by(AreaConocimiento.nombre).all()
        niveles = Nivel.query.filter_by(colegio_id=colegio.id) \
                             .order_by(Nivel.nombre).all()
        return render_template(
            'academic/materias.html', crumb='Materias',
            items=consulta.order_by(Materia.nombre).all(),
            area=area,
            areas=areas,
            niveles=niveles,
            especialidades=Especialidad.query.filter_by(
                colegio_id=colegio.id, activa=True).order_by(Especialidad.nombre).all(),
            tipos=TIPOS_AULA, tipos_label=TIPOS_AULA_LABEL,
            edit=edit, form={}, errors=[],
        )

    @app.route('/materias/guardar', methods=['POST'])
    @login_required
    def materia_guardar():
        colegio = _colegio_o_none()
        if not colegio:
            return redirect(url_for('dashboard'))

        item_id = request.form.get('id', type=int)
        item = db.session.get(Materia, item_id) if item_id else None

        nombre = (request.form.get('nombre') or '').strip()
        tipo_aula = request.form.get('tipo_aula_requerida') or None
        area_id = parse_int(request.form.get('area_id'))
        area = db.session.get(AreaConocimiento, area_id) if area_id else None
        if area and area.colegio_id != colegio.id:
            area = None
        nivel_id = parse_int(request.form.get('nivel_id'))
        nivel = db.session.get(Nivel, nivel_id) if nivel_id else None
        if nivel and nivel.colegio_id != colegio.id:
            nivel = None
        horas = parse_int(request.form.get('horas_semanales'))
        especialidad_ids = [int(x) for x in request.form.getlist('especialidades')
                            if x.isdigit()]
        especialidades = Especialidad.query.filter(
            Especialidad.id.in_(especialidad_ids),
            Especialidad.colegio_id == colegio.id,
        ).all() if especialidad_ids else []

        errors = []
        if not nombre:
            errors.append('El nombre de la materia es obligatorio.')
        if not area:
            errors.append('Seleccioná un área válida.')
        if not nivel:
            errors.append('Seleccioná un nivel válido.')
        if horas is None or horas < 0:
            errors.append('Las horas semanales deben ser iguales o mayores a cero.')
        if nivel and any(e.nivel_id != nivel.id for e in especialidades):
            errors.append('Alguna especialidad no pertenece al nivel de la materia.')
        if tipo_aula and tipo_aula not in TIPOS_AULA:
            errors.append('El tipo de aula requerida no es válido.')
        if area and nivel and nombre:
            duplicada = Materia.query.filter_by(
                colegio_id=colegio.id, nivel_id=nivel.id,
                nombre=nombre, area_id=area.id
            ).first()
            if duplicada and (item is None or duplicada.id != item.id):
                errors.append('Ya existe una materia con ese nombre en esa área.')

        if errors:
            return render_template(
                'academic/materias.html', crumb='Materias',
                items=Materia.query.filter_by(colegio_id=colegio.id)
                                   .order_by(Materia.nombre).all(),
                areas=AreaConocimiento.query.filter_by(
                    colegio_id=colegio.id
                ).order_by(AreaConocimiento.nombre).all(),
                niveles=Nivel.query.filter_by(colegio_id=colegio.id)
                                   .order_by(Nivel.nombre).all(),
                especialidades=Especialidad.query.filter_by(
                    colegio_id=colegio.id, activa=True).order_by(Especialidad.nombre).all(),
                tipos=TIPOS_AULA, tipos_label=TIPOS_AULA_LABEL,
                edit=item, form=request.form, errors=errors,
            )

        if item:
            item.nombre = nombre
            item.tipo_aula_requerida = tipo_aula
            item.area_id = area.id
            item.nivel_id = nivel.id
            item.horas_semanales = horas
        else:
            item = Materia(colegio_id=colegio.id, nombre=nombre,
                           area_id=area.id, nivel_id=nivel.id,
                           horas_semanales=horas,
                           tipo_aula_requerida=tipo_aula)
            db.session.add(item)
        item.especialidades = especialidades

        try:
            db.session.commit()
            flash('Materia guardada correctamente.', 'success')
        except IntegrityError:
            db.session.rollback()
            flash('Ya existe una materia con ese nombre en el colegio.', 'error')
        return redirect(url_for('materias'))

    @app.route('/materias/<int:item_id>/eliminar', methods=['POST'])
    @login_required
    def materia_eliminar(item_id):
        item = db.get_or_404(Materia, item_id)
        try:
            db.session.delete(item)
            db.session.commit()
            flash('Materia eliminada.', 'success')
        except IntegrityError:
            db.session.rollback()
            flash('No se puede eliminar: la materia está asignada a profesores o planes.', 'error')
        return redirect(url_for('materias'))
