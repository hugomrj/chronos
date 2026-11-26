from datetime import datetime, timezone

from flask import abort, flash, redirect, render_template, request, url_for
from flask_login import login_required
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import Rol, RolMenu, Usuario
from app.utils.colegio import colegio_actual
from app.utils.decorators import master_required
from app.utils.menu import ITEMS_POR_DEFECTO, MENU_KEYS, items_por_grupo


def register_roles_routes(app):
    """Roles y menú. Los define el master; admin es un rol más."""

    def _roles():
        return Rol.query.order_by(Rol.es_master.desc(), Rol.nombre).all()

    def _ctx(edit=None, form=None, errors=None, nuevo=False):
        return dict(
            crumb='Roles y menú',
            items=_roles(),
            grupos=items_por_grupo(),
            edit=edit,
            form=form or {},
            errors=errors or [],
            nuevo=nuevo,
        )

    # ------------------------------------------------------------------
    # AJUSTES DE INSTANCIA (solo master)
    # ------------------------------------------------------------------
    @app.route('/ajustes')
    @login_required
    @master_required
    def ajustes():
        colegio = colegio_actual()
        if not colegio:
            flash('Esta instalación no tiene un colegio asociado.', 'error')
            return redirect(url_for('dashboard'))
        return render_template('users/ajustes.html', crumb='Ajustes de instancia',
                               colegio=colegio, errors=[])

    @app.route('/ajustes/guardar', methods=['POST'])
    @login_required
    @master_required
    def ajustes_guardar():
        colegio = colegio_actual()
        if not colegio:
            flash('Esta instalación no tiene un colegio asociado.', 'error')
            return redirect(url_for('dashboard'))

        nuevo_valor = request.form.get('usa_aulas') == 'on'
        if nuevo_valor != colegio.usa_aulas:
            colegio.usa_aulas = nuevo_valor
            colegio.aulas_cambiado_en = datetime.now(timezone.utc)
            db.session.commit()
            if nuevo_valor:
                flash('El colegio ahora usa aulas. Regenerá los horarios para '
                      'que tengan aula asignada.', 'warning')
            else:
                flash('El colegio ya no usa aulas. Regenerá los horarios para '
                      'quitarlas.', 'warning')
        else:
            flash('Sin cambios.', 'success')
        return redirect(url_for('ajustes'))

    @app.route('/roles')
    @login_required
    @master_required
    def roles():
        edit = None
        edit_id = request.args.get('editar', type=int)
        if edit_id:
            edit = db.session.get(Rol, edit_id)
        nuevo = request.args.get('nuevo') == '1' or 'nuevo' in request.args
        return render_template('users/roles.html', **_ctx(edit=edit, nuevo=nuevo))

    @app.route('/roles/<int:rol_id>/menu')
    @login_required
    @master_required
    def rol_menu(rol_id):
        rol = db.get_or_404(Rol, rol_id)
        return render_template('users/rol_menu.html', crumb='Roles y menú',
                               rol=rol, grupos=items_por_grupo(),
                               seleccionados=rol.items_menu, errors=[])

    @app.route('/roles/<int:rol_id>/menu/guardar', methods=['POST'])
    @login_required
    @master_required
    def rol_menu_guardar(rol_id):
        rol = db.get_or_404(Rol, rol_id)
        if rol.es_master:
            flash('El rol master siempre ve todas las pantallas.', 'warning')
            return redirect(url_for('roles'))

        elegidos = [i for i in request.form.getlist('items') if i in MENU_KEYS]
        rol.menu_items = [RolMenu(item=item) for item in elegidos]
        db.session.commit()
        flash(f'Menú actualizado para el rol {rol.nombre}.', 'success')
        return redirect(url_for('roles'))

    @app.route('/roles/guardar', methods=['POST'])
    @login_required
    @master_required
    def rol_guardar():
        item_id = request.form.get('id', type=int)
        item = db.session.get(Rol, item_id) if item_id else None
        nombre = (request.form.get('nombre') or '').strip().lower()

        errors = []
        if not nombre:
            errors.append('El nombre del rol es obligatorio.')
        if ' ' in nombre:
            errors.append('El nombre del rol no puede tener espacios.')
        existente = Rol.query.filter_by(nombre=nombre).first()
        if existente and (item is None or existente.id != item.id):
            errors.append('Ya existe un rol con ese nombre.')
        if item is not None and item.es_master and nombre != item.nombre:
            errors.append('El rol master no se puede renombrar.')

        if errors:
            return render_template('users/roles.html',
                                   **_ctx(edit=item, form=request.form,
                                         errors=errors, nuevo=item is None))

        creado = item is None
        if creado:
            item = Rol(nombre=nombre, es_master=False)
            db.session.add(item)
            db.session.flush()
            for clave in ITEMS_POR_DEFECTO:
                db.session.add(RolMenu(rol_id=item.id, item=clave))
        else:
            item.nombre = nombre

        try:
            db.session.commit()
            flash('Rol guardado.', 'success')
        except IntegrityError:
            db.session.rollback()
            flash('No se pudo guardar el rol.', 'error')
        return redirect(url_for('roles'))

    @app.route('/roles/<int:rol_id>/bloqueo', methods=['POST'])
    @login_required
    @master_required
    def rol_bloqueo(rol_id):
        rol = db.get_or_404(Rol, rol_id)
        if rol.es_master:
            flash('El rol master no se puede bloquear.', 'error')
            return redirect(url_for('roles'))
        rol.bloqueado = not rol.bloqueado
        db.session.commit()
        estado = 'bloqueado' if rol.bloqueado else 'habilitado'
        flash(f'Rol {rol.nombre} {estado}.', 'success')
        return redirect(url_for('roles'))

    @app.route('/roles/<int:rol_id>/eliminar', methods=['POST'])
    @login_required
    @master_required
    def rol_eliminar(rol_id):
        rol = db.get_or_404(Rol, rol_id)
        if rol.es_master:
            flash('El rol master no se puede eliminar.', 'error')
            return redirect(url_for('roles'))
        if Usuario.query.filter_by(rol_id=rol.id).first():
            flash('No se puede eliminar: hay usuarios con ese rol.', 'error')
            return redirect(url_for('roles'))
        try:
            db.session.delete(rol)
            db.session.commit()
            flash('Rol eliminado.', 'success')
        except IntegrityError:
            db.session.rollback()
            abort(400)
        return redirect(url_for('roles'))
