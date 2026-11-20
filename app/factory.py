# Application Factory
from flask import Flask
from config import config_by_name
from app.extensions import db, login_manager, bcrypt
import os


def create_app(config_name=None):
    """Crea y configura la aplicación Flask."""
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'development')
    
    app = Flask(__name__)
    app.config.from_object(config_by_name[config_name])
    
    # Inicializar extensiones
    db.init_app(app)
    login_manager.init_app(app)
    bcrypt.init_app(app)

    # Cargar el usuario desde la sesión (Flask-Login)
    @login_manager.user_loader
    def load_user(user_id):
        from app.models.auth import Usuario
        return db.session.get(Usuario, int(user_id))

    # Registrar rutas
    from app.routes.registry import register_routes
    register_routes(app)
    
    return app