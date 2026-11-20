from functools import wraps

from flask import flash, redirect, url_for
from flask_login import current_user


def admin_required(view):
    """Permite el acceso solo a usuarios con rol admin."""
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('login'))
        if not getattr(current_user, 'es_admin', False):
            flash('No tenés permisos para acceder a esa sección.', 'error')
            return redirect(url_for('dashboard'))
        return view(*args, **kwargs)
    return wrapped
