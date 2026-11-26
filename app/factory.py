# Application Factory
import os
import secrets
from hmac import compare_digest

from flask import Flask, abort, render_template, request, session
from config import config_by_name
from app.extensions import db, login_manager, bcrypt


def create_app(config_name=None):
    """Crea y configura la aplicación Flask."""
    if config_name is None:
        config_name = (os.getenv('FLASK_CONFIG')
                       or os.getenv('FLASK_ENV')
                       or 'development')
    if config_name not in config_by_name:
        config_name = 'default'

    app = Flask(__name__)
    app.config.from_object(config_by_name[config_name])

    if app.config.get('USE_PROXY_FIX'):
        from werkzeug.middleware.proxy_fix import ProxyFix
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1)

    # Inicializar extensiones
    db.init_app(app)
    login_manager.init_app(app)
    bcrypt.init_app(app)

    # Cargar el usuario desde la sesión (Flask-Login)
    @login_manager.user_loader
    def load_user(user_id):
        from app.models.auth import Usuario
        return db.session.get(Usuario, int(user_id))

    # ------------------------------------------------------------------
    # CSRF (token en sesión, sin dependencias externas)
    # ------------------------------------------------------------------
    def csrf_token():
        token = session.get('_csrf_token')
        if not token:
            token = secrets.token_urlsafe(32)
            session['_csrf_token'] = token
        return token

    @app.before_request
    def csrf_protect():
        if request.method == 'POST' and app.config.get('CSRF_ENABLED', True):
            enviado = request.form.get('_csrf_token') or request.headers.get('X-CSRF-Token')
            esperado = session.get('_csrf_token')
            if not esperado or not enviado or not compare_digest(enviado, esperado):
                abort(400, description='Token CSRF inválido o ausente. Recargá la página e intentá de nuevo.')

    @app.context_processor
    def inject_globals():
        from flask_login import current_user
        from app.models import Colegio
        from app.services.notifications import obtener_avisos
        from app.utils.colegio import colegio_actual
        from app.utils.menu import MENU_POR_CLAVE

        actual, colegios, avisos = None, [], []
        try:
            actual = colegio_actual()
            colegios = [actual] if actual else []
            if actual and current_user.is_authenticated:
                avisos = obtener_avisos(actual)
        except Exception:
            actual, colegios, avisos = None, [], []

        return {
            'csrf_token': csrf_token,
            'colegio_actual': actual,
            'colegios_disponibles': colegios,
            'colegio_multiple': len(colegios) > 1,
            'notificaciones': avisos,
            'notificaciones_count': len(avisos),
            'menu_items': MENU_POR_CLAVE,
        }

    @app.errorhandler(400)
    def bad_request(error):
        return render_template('errors/400.html',
                               mensaje=getattr(error, 'description', 'Solicitud inválida.')), 400

    # Registrar rutas
    from app.routes.registry import register_routes
    register_routes(app)

    # Control de acceso al menú según el rol
    from app.utils.decorators import registrar_control_menu
    registrar_control_menu(app)

    return app
