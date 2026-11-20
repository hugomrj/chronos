# Instancias de extensiones de Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_bcrypt import Bcrypt

# Inicializar extensiones (se configuran en create_app)
db = SQLAlchemy()
login_manager = LoginManager()
bcrypt = Bcrypt()

# Configurar LoginManager
login_manager.login_view = 'login'  # Sin blueprints, el endpoint es 'login'
login_manager.login_message = 'Por favor, inicia sesión para acceder a esta página.'
login_manager.login_message_category = 'warning'