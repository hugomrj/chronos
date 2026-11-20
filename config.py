# Configuración de la aplicación
import os
from pathlib import Path
from urllib.parse import quote_plus
from dotenv import load_dotenv

# Cargar variables de entorno desde la raíz (el .env manda sobre el entorno del sistema)
env_path = Path(__file__).resolve().parent / '.env'
load_dotenv(dotenv_path=env_path, override=True)


class Config:
    """Configuración base."""
    SECRET_KEY = os.getenv('SECRET_KEY', 'clave-secreta-por-defecto-cambiar-en-produccion')
    
    # Base de datos
    DB_USER = os.getenv('DB_USER', 'postgres')
    DB_PASS = os.getenv('DB_PASS', '')
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_PORT = os.getenv('DB_PORT', '5432')
    DB_NAME = os.getenv('DB_NAME', 'chronos_db')
    
    SQLALCHEMY_DATABASE_URI = (
        f'postgresql+psycopg2://{quote_plus(DB_USER)}:{quote_plus(DB_PASS)}'
        f'@{DB_HOST}:{DB_PORT}/{DB_NAME}'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Servidor
    HOST = os.getenv('HOST', '0.0.0.0')
    PORT = int(os.getenv('PORT', 5000))
    DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'


class DevelopmentConfig(Config):
    """Configuración para desarrollo."""
    DEBUG = True


class ProductionConfig(Config):
    """Configuración para producción."""
    DEBUG = False


# Diccionario para seleccionar configuración
config_by_name = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}