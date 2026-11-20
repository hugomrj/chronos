import json

from flask import flash, redirect, render_template, request, url_for
from flask_login import login_required

from app.extensions import db
from app.models import Materia, Nivel, Profesor, Regla
from app.services.scheduler.catalog import REGLAS_CATALOGO
from app.utils.helpers import colegio_actual, parse_int


def register_rules_routes(app):
    """CRUD de reglas obligatorias y deseables."""

    def _ctx(colegio, edit=None, form=None, errors=None):
        return dict(
            crumb='Reglas',
            items=Regla.query.filter_by(colegio_id=colegio.id)
                              .order_by(Regla.codigo, Regla.id).all(),
            catalogo=REGLAS_CATALOGO,
            materias=Materia.query.filter_by(colegio_id=colegio.id)
                                  .order_by(Materia.nombre).all(),
            niveles=Nivel.query.filter_by(colegio_id=colegio.id)
                               .order_by(Nivel.nombre).all(),
            profesores=Profesor.query.filter_by(colegio_id=colegio.id)
                                     .order_by(Profesor.nombre).all(),
            edit=edit,
            form=form or {},
            errors=errors or [],
        )

    @app.route('/reglas')
    @login_required
    def reglas():
        colegio = colegio_actual()
        if not colegio:
            flash('Primero creá un colegio para continuar.', 'warning')
            return redirect(url_for('colegios'))

        edit = None
        edit_id = request.args.get('editar', type=int)
        if edit_id:
            edit = db.session.get(Regla, edit_id)
            if edit and edit.colegio_id != colegio.id:
                edit = None

        return render_template('rules/reglas.html', **_ctx(colegio, edit=edit))

    @app.route('/reglas/guardar', methods=['POST'])
    @login_required
    def regla_guardar():
        colegio = colegio_actual()
        if not colegio:
            flash('Primero creá un colegio para continuar.', 'warning')
            return redirect(url_for('colegios'))

        item_id = request.form.get('id', type=int)
        item = db.session.get(Regla, item_id) if item_id else None
        if item and item.colegio_id != colegio.id:
            item = None

        codigo = (request.form.get('codigo') or '').strip()
        descripcion = (request.form.get('descripcion') or '').strip() or None
        obligatoria = request.form.get('obligatoria') == 'on'
        activa = request.form.get('activa') == 'on'
        peso = parse_int(request.form.get('peso'), 10)
        materia_id = parse_int(request.form.get('materia_id'))
        nivel_id = parse_int(request.form.get('nivel_id'))
        profesor_id = parse_int(request.form.get('profesor_id'))
        parametros_raw = (request.form.get('parametros') or '').strip() or '{}'

        materia = db.session.get(Materia, materia_id) if materia_id else None
        if materia and materia.colegio_id != colegio.id:
            materia = None
        nivel = db.session.get(Nivel, nivel_id) if nivel_id else None
        if nivel and nivel.colegio_id != colegio.id:
            nivel = None
        profesor = db.session.get(Profesor, profesor_id) if profesor_id else None
        if profesor and profesor.colegio_id != colegio.id:
            profesor = None

        errors = []
        codigo_valido = codigo in REGLAS_CATALOGO
        if item and item.codigo == codigo:
            codigo_valido = True
        if not codigo:
            errors.append('Seleccioná un código de regla.')
        elif not codigo_valido:
            errors.append('Ese código no está soportado por el motor.')
        if peso is None:
            peso = 10
        if peso < 0 or peso > 100:
            errors.append('El peso debe estar entre 0 y 100.')
        if materia_id and not materia:
            errors.append('La materia seleccionada no es válida.')
        if nivel_id and not nivel:
            errors.append('El nivel seleccionado no es válido.')
        if profesor_id and not profesor:
            errors.append('El profesor seleccionado no es válido.')

        parametros = {}
        try:
            parametros = json.loads(parametros_raw)
            if not isinstance(parametros, dict):
                errors.append('Los parámetros deben ser un objeto JSON, por ejemplo {"horas": 6}.')
                parametros = {}
        except ValueError:
            errors.append('Los parámetros no son un JSON válido.')
            parametros = {}

        if not errors:
            duplicada = Regla.query.filter_by(
                colegio_id=colegio.id,
                codigo=codigo,
                materia_id=materia.id if materia else None,
                nivel_id=nivel.id if nivel else None,
                profesor_id=profesor.id if profesor else None,
            )
            if item:
                duplicada = duplicada.filter(Regla.id != item.id)
            if duplicada.first():
                errors.append('Ya existe una regla con ese código y el mismo alcance.')

        if errors:
            return render_template('rules/reglas.html',
                                   **_ctx(colegio, edit=item, form=request.form,
                                         errors=errors))

        if item is None:
            item = Regla(colegio_id=colegio.id)
            db.session.add(item)

        item.codigo = codigo
        item.descripcion = descripcion
        item.obligatoria = obligatoria
        item.activa = activa
        item.peso = peso
        item.materia_id = materia.id if materia else None
        item.nivel_id = nivel.id if nivel else None
        item.profesor_id = profesor.id if profesor else None
        item.parametros = parametros

        db.session.commit()
        flash('Regla guardada correctamente.', 'success')
        return redirect(url_for('reglas'))

    @app.route('/reglas/<int:item_id>/eliminar', methods=['POST'])
    @login_required
    def regla_eliminar(item_id):
        item = db.get_or_404(Regla, item_id)
        db.session.delete(item)
        db.session.commit()
        flash('Regla eliminada.', 'success')
        return redirect(url_for('reglas'))
