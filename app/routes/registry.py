# Registro centralizado de rutas
from flask import redirect, url_for


def register_routes(app):
    """Registra todas las rutas de la aplicación."""

    # Autenticación
    from app.routes.auth import register_auth_routes
    register_auth_routes(app)

    # Dashboard
    from app.routes.dashboard import register_dashboard_routes
    register_dashboard_routes(app)

    # Estructura académica
    from app.routes.academic import register_academic_routes
    register_academic_routes(app)

    # Profesores y disponibilidad
    from app.routes.teachers import register_teachers_routes
    register_teachers_routes(app)

    # Plantillas, secciones y planes
    from app.routes.schedule import register_schedule_routes
    register_schedule_routes(app)

    # Reglas
    from app.routes.rules import register_rules_routes
    register_rules_routes(app)

    # Generación de horarios
    from app.routes.horarios import register_horarios_routes
    register_horarios_routes(app)

    # Usuarios, perfil y configuración
    from app.routes.users import register_users_routes
    register_users_routes(app)

    # Guía de usuario
    from app.routes.docs import register_docs_routes
    register_docs_routes(app)

    @app.route('/')
    def index():
        return redirect(url_for('dashboard'))

    # Futuro: importar y registrar más rutas aquí
    # from app.routes.academic import register_academic_routes
    # register_academic_routes(app)
