# Configuración de la aplicación
import os
from pathlib import Path
from urllib.parse import quote_plus

from dotenv import load_dotenv


def _env_flag(nombre, por_defecto=False):
    valor = os.getenv(nombre)
    if valor is None:
        return por_defecto
    return valor.strip().lower() in ('1', 'true', 'yes', 'on', 'si', 'sí')


# El .env de la instancia manda sobre el entorno del sistema.
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(dotenv_path=BASE_DIR / '.env', override=True)


class Config:
    """Configuración base."""

    # Instancia: cada proceso sirve UN colegio
    COLEGIO_ID = int(os.getenv('COLEGIO_ID', '0') or 0)

    SECRET_KEY = os.getenv('SECRET_KEY', 'clave-secreta-por-defecto-cambiar-en-produccion')

    # Base de datos (compartida entre instancias)
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
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 1800,
    }

    # Seguridad
    CSRF_ENABLED = _env_flag('CSRF_ENABLED', True)
    SESSION_COOKIE_SECURE = _env_flag('SESSION_COOKIE_SECURE', False)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = os.getenv('SESSION_COOKIE_SAMESITE', 'Lax')
    PERMANENT_SESSION_LIFETIME = int(os.getenv('SESSION_LIFETIME', '28800'))

    # Portal maestro (solo la instancia que administra colegios)
    SUPERADMIN = _env_flag('SUPERADMIN', False)

    # Detrás de nginx / proxy inverso
    USE_PROXY_FIX = _env_flag('USE_PROXY_FIX', False)

    # Documentación (guía de usuario)
    DOCS_DIRECTORY = str(BASE_DIR / 'docs')

    # Etiquetas para bloques que no son clase (recesos, almuerzo, etc.).
    # Se identifican por rango horario: "HH:MM-HH:MM".
    # No requiere cambios en la base de datos.
    ETIQUETAS_BLOQUES = {
        '07:45-08:00': 'Actividades Formativas',
        # '13:10-13:50': 'Almuerzo',
    }

    # Servidor
    HOST = os.getenv('HOST', '0.0.0.0')
    PORT = int(os.getenv('PORT', 5000))
    DEBUG = _env_flag('DEBUG', False)


class DevelopmentConfig(Config):
    """Configuración para desarrollo."""
    DEBUG = True
    SESSION_COOKIE_SECURE = False


class ProductionConfig(Config):
    """Configuración para producción."""
    DEBUG = False
    SESSION_COOKIE_SECURE = _env_flag('SESSION_COOKIE_SECURE', True)


# Diccionario para seleccionar configuración
config_by_name = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': DevelopmentConfig,
    'default': DevelopmentConfig,
}
