from flask import redirect, url_for
from app.routes.auth import register_auth_routes

def register_routes(app):
    """Registra todas las rutas de la aplicación."""
    
    @app.route('/')
    def index():
        # Redirigir la raíz al login o al dashboard si ya está autenticado
        return redirect(url_for('login'))

    # 1. Registrar rutas de autenticación
    register_auth_routes(app)
    
    # 2. Futuro: Registrar rutas del dashboard
    # from app.routes.dashboard import register_dashboard_routes
    # register_dashboard_routes(app)