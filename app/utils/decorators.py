from functools import wraps

from flask import abort, flash, jsonify, redirect, request, url_for
from flask_login import current_user, logout_user

from app.utils.menu import item_de_ruta

# Rutas que no se controlan por menú.
RUTAS_LIBRES = (
    '/static', '/login', '/logout', '/dashboard', '/perfil', '/preferencias',
    '/guia', '/guia-usuario', '/presentacion', '/doc', '/avisos',
)


# Las instancias sirven un solo colegio: no hay administración de colegios.
RUTAS_BLOQUEADAS = ('/colegios',)

# Solo el rol master.
RUTAS_MASTER = ('/ajustes', '/roles')


def master_required(view):
    """Permite el acceso solo al rol master."""
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('login'))
        if not getattr(current_user, 'es_master', False):
            flash('Solo el administrador master puede acceder a esa sección.',
                  'error')
            return redirect(url_for('dashboard'))
        return view(*args, **kwargs)
    return wrapped


def admin_required(view):
    """Permite el acceso a usuarios con rol admin o master."""
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('login'))
        if not getattr(current_user, 'es_admin', False):
            flash('No tenés permisos para acceder a esa sección.', 'error')
            return redirect(url_for('dashboard'))
        return view(*args, **kwargs)
    return wrapped


def registrar_control_menu(app):
    """Bloquea el acceso a las rutas que el rol del usuario no tiene habilitadas."""

    @app.before_request
    def _control_menu():
        if not current_user.is_authenticated:
            return None
        if request.method == 'OPTIONS':
            return None
        if current_user.rol and current_user.rol.bloqueado:
            logout_user()
            flash('Tu rol fue bloqueado.', 'error')
            return redirect(url_for('login'))

        path = request.path or '/'
        if any(path.startswith(libre) for libre in RUTAS_LIBRES):
            return None

        if any(path == r or path.startswith(r + '/') for r in RUTAS_MASTER):
            if not current_user.es_master:
                flash('Solo el administrador master puede acceder.', 'error')
                return redirect(url_for('dashboard'))
            return None

        if any(path == r or path.startswith(r + '/') for r in RUTAS_BLOQUEADAS):
            flash('Cada instalación administra un único colegio.', 'error')
            return redirect(url_for('dashboard'))

        clave = item_de_ruta(path)
        if clave is None:
            return None
        if current_user.puede_ver(clave):
            return None

        if request.endpoint and request.endpoint.startswith('static'):
            return None
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'ok': False, 'error': 'sin_permiso'}), 403
        flash('Tu rol no tiene acceso a esa sección.', 'error')
        return redirect(url_for('dashboard'))
