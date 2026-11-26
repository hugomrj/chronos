# Ejecución: python scripts/seed_data.py
import psycopg2
from dotenv import load_dotenv
import os
from pathlib import Path
import bcrypt

# Cargar .env desde la raíz del proyecto
env_path = Path(__file__).resolve().parent.parent / '.env'
load_dotenv(dotenv_path=env_path, override=True)

DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASS = os.getenv('DB_PASS', 'tu_contraseña_root')
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME', 'chronos_db')

# =====================================================================
# CONFIGURACIÓN DE DATOS INICIALES
# =====================================================================
# Rol master: administra la plataforma (colegios, roles y usuarios).
MASTER_EMAIL = "master@chronos.com"
MASTER_PASSWORD = "admin123"

# Rol admin: administra su colegio (menú configurable).
ADMIN_EMAIL = "admin@chronos.com"
ADMIN_PASSWORD = "admin123"
COLEGIO_NOMBRE = "Colegio Demo"


def get_connection():
    """Retorna una conexión a la base de datos."""
    return psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASS,
        host=DB_HOST,
        port=DB_PORT
    )


def hash_password(password):
    """Hashea una contraseña usando bcrypt."""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


ITEMS_MENU_ADMIN = [
    'anios', 'niveles', 'especialidades', 'grados', 'areas', 'materias',
    'planes', 'turnos', 'aulas', 'profesores', 'disponibilidad', 'plantillas',
    'secciones', 'reglas', 'horarios', 'reportes', 'usuarios',
    'configuracion', 'roles',
]


def create_roles(cursor):
    """Crea los roles master y admin, y el menú del admin."""
    cursor.execute(
        "INSERT INTO rol (nombre, es_master) VALUES ('master', true) "
        "ON CONFLICT (nombre) DO UPDATE SET es_master = true"
    )
    cursor.execute(
        "INSERT INTO rol (nombre, es_master) VALUES ('admin', false) "
        "ON CONFLICT (nombre) DO NOTHING"
    )
    cursor.execute("SELECT id FROM rol WHERE nombre = 'admin'")
    admin_id = cursor.fetchone()[0]
    for item in ITEMS_MENU_ADMIN:
        cursor.execute(
            "INSERT INTO rol_menu (rol_id, item) VALUES (%s, %s) "
            "ON CONFLICT DO NOTHING",
            (admin_id, item),
        )
    print("✅ Roles master y admin listos.")


def create_colegio_demo(cursor):
    """Crea un colegio base si no existe."""
    cursor.execute("SELECT id FROM colegio WHERE nombre = %s", (COLEGIO_NOMBRE,))
    colegio = cursor.fetchone()

    if not colegio:
        cursor.execute(
            "INSERT INTO colegio (nombre) VALUES (%s) RETURNING id",
            (COLEGIO_NOMBRE,),
        )
        colegio_id = cursor.fetchone()[0]
        print(f"✅ Colegio '{COLEGIO_NOMBRE}' creado.")
        return colegio_id

    print(f"⚠️ Colegio '{COLEGIO_NOMBRE}' ya existe.")
    return colegio[0]


def _crear_usuario(cursor, colegio_id, rol_nombre, email, password, etiqueta):
    cursor.execute("SELECT id FROM rol WHERE nombre = %s", (rol_nombre,))
    fila = cursor.fetchone()
    if not fila:
        return None
    cursor.execute("SELECT id FROM usuario WHERE email = %s", (email,))
    existente = cursor.fetchone()
    if existente:
        print(f"⚠️ Usuario '{email}' ya existe.")
        return existente[0]
    cursor.execute("""
        INSERT INTO usuario (colegio_id, email, password_hash, rol_id, activo)
        VALUES (%s, %s, %s, %s, true)
        RETURNING id
    """, (colegio_id, email, hash_password(password), fila[0]))
    print(f"✅ Usuario {etiqueta}: {email} / {password}")
    return cursor.fetchone()[0]


def create_master_user(cursor, colegio_id):
    """Crea el usuario master (administra la plataforma)."""
    return _crear_usuario(cursor, colegio_id, 'master', MASTER_EMAIL,
                          MASTER_PASSWORD, 'master')


def create_admin_user(cursor, colegio_id):
    """Crea el usuario admin de colegio (menú configurable)."""
    return _crear_usuario(cursor, colegio_id, 'admin', ADMIN_EMAIL,
                          ADMIN_PASSWORD, 'admin de colegio')


def seed_database():
    """Función principal que orquesta la carga de datos."""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # 1. Crear roles master y admin
        create_roles(cursor)
        
        # 2. Crear colegio demo
        colegio_id = create_colegio_demo(cursor)
        
        # 3. Crear usuarios: master y admin de colegio
        create_master_user(cursor, colegio_id)
        create_admin_user(cursor, colegio_id)
        
        # Futuro: añadir más datos aquí
        # create_niveles_demo(cursor, colegio_id)
        # create_profesores_demo(cursor, colegio_id)
        
        conn.commit()
        print("\n✅ Datos iniciales cargados exitosamente.")
        
        cursor.close()
    except Exception as e:
        print(f"❌ Error al cargar datos: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()


if __name__ == '__main__':
    print("=" * 60)
    print("CARGA DE DATOS INICIALES - CHRONOS")
    print("=" * 60)
    print(f"Master: {MASTER_EMAIL} / {MASTER_PASSWORD}")
    print(f"Admin:  {ADMIN_EMAIL} / {ADMIN_PASSWORD}")
    print(f"Colegio: {COLEGIO_NOMBRE}")
    print("=" * 60)
    
    confirm = input("\n¿Deseas continuar? (s/n): ")
    if confirm.lower() == 's':
        seed_database()
    else:
        print("Operación cancelada.")



        