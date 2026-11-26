import re

from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy.exc import IntegrityError

from app.extensions import bcrypt, db
from app.models import Profesor, Rol, Usuario
from app.utils.helpers import POR_PAGINA, parse_int
from app.utils.colegio import colegio_actual

EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')


def register_users_routes(app):
    """Usuarios, perfil, preferencias y configuración."""

    def _pagina_usuarios(colegio, texto):
        consulta = Usuario.query.filter_by(colegio_id=colegio.id)
        if texto:
            patron = f'%{texto.strip()}%'
            consulta = consulta.join(Usuario.rol).filter(db.or_(
                Usuario.email.ilike(patron),
                Rol.nombre.ilike(patron),
            ))
        return consulta.order_by(Usuario.email).paginate(
            page=request.args.get('pagina', 1, type=int),
            per_page=POR_PAGINA, error_out=False)

    def _ctx_usuarios(colegio, edit=None, form=None, errors=None):
        return dict(
            crumb='Usuarios',
            colegio=colegio,
            items=None,
            pagina=_pagina_usuarios(colegio, request.args.get('q')),
            filtro=request.args.get('q') or '',
            roles=Rol.query.order_by(Rol.es_master.desc(), Rol.nombre).all(),
            profesores=Profesor.query.filter_by(colegio_id=colegio.id)
                                     .order_by(Profesor.nombre).all(),
            edit=edit,
            form=form or {},
            errors=errors or [],
        )

    # ------------------------------------------------------------------
    # USUARIOS
    # ------------------------------------------------------------------
    @app.route('/usuarios')
    @login_required
    def usuarios():
        colegio = colegio_actual()
        if not colegio:
            return redirect(url_for('dashboard'))

        edit = None
        edit_id = request.args.get('editar', type=int)
        if edit_id:
            edit = db.session.get(Usuario, edit_id)
            if edit and edit.colegio_id != colegio.id:
                edit = None

        return render_template('users/usuarios.html',
                               **_ctx_usuarios(colegio, edit=edit))

    @app.route('/usuarios/guardar', methods=['POST'])
    @login_required
    def usuario_guardar():
        colegio = colegio_actual()
        if not colegio:
            return redirect(url_for('dashboard'))

        item_id = request.form.get('id', type=int)
        item = db.session.get(Usuario, item_id) if item_id else None
        if item and item.colegio_id != colegio.id:
            item = None

        email = (request.form.get('email') or '').strip().lower()
        password = request.form.get('password') or ''
        rol_id = parse_int(request.form.get('rol_id'))
        profesor_id = parse_int(request.form.get('profesor_id'))
        activo = request.form.get('activo') == 'on'

        rol = db.session.get(Rol, rol_id) if rol_id else None
        profesor = db.session.get(Profesor, profesor_id) if profesor_id else None
        if profesor and profesor.colegio_id != colegio.id:
            profesor = None

        errors = []
        if not email or not EMAIL_RE.match(email):
            errors.append('Ingresá un correo electrónico válido.')
        if not rol:
            errors.append('Seleccioná un rol válido.')
        if item is None and len(password) < 6:
            errors.append('La contraseña debe tener al menos 6 caracteres.')
        if password and len(password) < 6:
            errors.append('La contraseña debe tener al menos 6 caracteres.')
        if item is not None and item.id == current_user.id and not activo:
            errors.append('No podés desactivar tu propio usuario.')

        existente = Usuario.query.filter_by(email=email).first()
        if existente and (item is None or existente.id != item.id):
            errors.append('Ya existe un usuario con ese correo.')

        if item is not None and item.es_admin and item.activo and not activo:
            otros_admins = Usuario.query.filter(
                Usuario.colegio_id == colegio.id,
                Usuario.rol_id == rol.id,
                Usuario.activo.is_(True),
                Usuario.id != item.id,
            ).count()
            if otros_admins == 0:
                errors.append('No podés desactivar el último administrador activo.')

        if errors:
            return render_template('users/usuarios.html',
                                   **_ctx_usuarios(colegio, edit=item,
                                                   form=request.form,
                                                   errors=errors))

        if item is None:
            item = Usuario(colegio_id=colegio.id)
            db.session.add(item)

        item.email = email
        item.rol_id = rol.id
        item.profesor_id = profesor.id if profesor else None
        item.activo = activo
        if password:
            item.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

        try:
            db.session.commit()
            flash('Usuario guardado correctamente.', 'success')
        except IntegrityError:
            db.session.rollback()
            flash('No se pudo guardar el usuario. Revisá el correo.', 'error')

        return redirect(url_for('usuarios'))

    @app.route('/usuarios/<int:item_id>/eliminar', methods=['POST'])
    @login_required
    def usuario_eliminar(item_id):
        colegio = colegio_actual()
        if not colegio:
            return redirect(url_for('dashboard'))

        item = db.get_or_404(Usuario, item_id)
        if item.colegio_id != colegio.id:
            flash('El usuario no pertenece al colegio activo.', 'error')
            return redirect(url_for('usuarios'))
        if item.id == current_user.id:
            flash('No podés eliminar tu propio usuario.', 'error')
            return redirect(url_for('usuarios'))

        if item.es_admin and item.activo:
            admins = Usuario.query.filter_by(
                colegio_id=colegio.id, rol_id=item.rol_id, activo=True
            ).count()
            if admins <= 1:
                flash('No podés eliminar el último administrador activo.', 'error')
                return redirect(url_for('usuarios'))

        db.session.delete(item)
        db.session.commit()
        flash('Usuario eliminado.', 'success')
        return redirect(url_for('usuarios'))

    # ------------------------------------------------------------------
    # PERFIL
    # ------------------------------------------------------------------
    @app.route('/perfil', methods=['GET', 'POST'])
    @login_required
    def perfil():
        errors = []
        if request.method == 'POST':
            email = (request.form.get('email') or '').strip().lower()
            actual = request.form.get('password_actual') or ''
            nueva = request.form.get('password_nueva') or ''
            confirmar = request.form.get('password_confirmar') or ''

            if not email or not EMAIL_RE.match(email):
                errors.append('Ingresá un correo electrónico válido.')
            if not bcrypt.check_password_hash(current_user.password_hash, actual):
                errors.append('La contraseña actual no es correcta.')
            if nueva and len(nueva) < 6:
                errors.append('La nueva contraseña debe tener al menos 6 caracteres.')
            if nueva != confirmar:
                errors.append('La confirmación de la nueva contraseña no coincide.')

            existente = Usuario.query.filter_by(email=email).first()
            if existente and existente.id != current_user.id:
                errors.append('Ese correo ya está en uso por otro usuario.')

            if not errors:
                current_user.email = email
                if nueva:
                    current_user.password_hash = bcrypt.generate_password_hash(nueva) \
                                                       .decode('utf-8')
                db.session.commit()
                flash('Perfil actualizado correctamente.', 'success')
                return redirect(url_for('perfil'))

        return render_template('users/perfil.html',
                               crumb='Mi perfil',
                               errors=errors,
                               form=request.form if request.method == 'POST' else {})

    # ------------------------------------------------------------------
    # PREFERENCIAS
    # ------------------------------------------------------------------
    @app.route('/preferencias')
    @login_required
    def preferencias():
        return render_template('users/preferencias.html', crumb='Preferencias')

    # ------------------------------------------------------------------
    # CONFIGURACIÓN
    # ------------------------------------------------------------------
    @app.route('/configuracion')
    @login_required
    def configuracion():
        colegio = colegio_actual()
        if not colegio:
            return redirect(url_for('dashboard'))

        return render_template(
            'users/configuracion.html',
            crumb='Configuración',
            colegio=colegio,
            total_usuarios=Usuario.query.filter_by(colegio_id=colegio.id).count(),
            total_profesores=Profesor.query.filter_by(colegio_id=colegio.id).count(),
        )

    @app.route('/configuracion/guardar', methods=['POST'])
    @login_required
    def configuracion_guardar():
        colegio = colegio_actual()
        if not colegio:
            return redirect(url_for('dashboard'))

        nombre = (request.form.get('nombre') or '').strip()
        minutos = parse_int(request.form.get('minutos_hora_catedra'), 40)

        errors = []
        if not nombre:
            errors.append('El nombre del colegio es obligatorio.')
        if minutos is None or minutos < 20 or minutos > 120:
            errors.append('La hora cátedra debe estar entre 20 y 120 minutos.')
        if errors:
            for error in errors:
                flash(error, 'error')
            return redirect(url_for('configuracion'))

        colegio.nombre = nombre
        colegio.minutos_hora_catedra = minutos
        db.session.commit()
        flash('Configuración del colegio actualizada.', 'success')
        return redirect(url_for('configuracion'))
