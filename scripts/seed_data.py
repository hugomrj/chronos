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


def create_rol_admin(cursor):
    """Crea el rol 'admin' si no existe."""
    cursor.execute("SELECT id FROM rol WHERE nombre = 'admin'")
    rol = cursor.fetchone()
    
    if not rol:
        cursor.execute("INSERT INTO rol (nombre) VALUES ('admin') RETURNING id")
        rol_id = cursor.fetchone()[0]
        print("✅ Rol 'admin' creado.")
        return rol_id
    else:
        print("⚠️ Rol 'admin' ya existe.")
        return rol[0]


def create_colegio_demo(cursor):
    """Crea un colegio base si no existe."""
    cursor.execute("SELECT id FROM colegio WHERE nombre = %s", (COLEGIO_NOMBRE,))
    colegio = cursor.fetchone()
    
    if not colegio:
        cursor.execute("INSERT INTO colegio (nombre) VALUES (%s) RETURNING id", (COLEGIO_NOMBRE,))
        colegio_id = cursor.fetchone()[0]
        print(f"✅ Colegio '{COLEGIO_NOMBRE}' creado.")
        return colegio_id
    else:
        print(f"⚠️ Colegio '{COLEGIO_NOMBRE}' ya existe.")
        return colegio[0]


def create_admin_user(cursor, colegio_id, rol_id):
    """Crea el usuario administrador."""
    cursor.execute("SELECT id FROM usuario WHERE email = %s", (ADMIN_EMAIL,))
    user = cursor.fetchone()
    
    if not user:
        password_hash = hash_password(ADMIN_PASSWORD)
        cursor.execute("""
            INSERT INTO usuario (colegio_id, email, password_hash, rol_id, activo)
            VALUES (%s, %s, %s, %s, true)
            RETURNING id
        """, (colegio_id, ADMIN_EMAIL, password_hash, rol_id))
        user_id = cursor.fetchone()[0]
        print(f"✅ Usuario admin creado: {ADMIN_EMAIL} / {ADMIN_PASSWORD}")
        return user_id
    else:
        print(f"⚠️ Usuario '{ADMIN_EMAIL}' ya existe.")
        return user[0]


# =====================================================================
# FUNCIONES ADICIONALES (para el futuro)
# =====================================================================
# def create_niveles_demo(cursor, colegio_id):
#     pass
#
# def create_profesores_demo(cursor, colegio_id):
#     pass
#
# def create_materias_demo(cursor, colegio_id):
#     pass


def seed_database():
    """Función principal que orquesta la carga de datos."""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # 1. Crear rol admin
        rol_id = create_rol_admin(cursor)
        
        # 2. Crear colegio demo
        colegio_id = create_colegio_demo(cursor)
        
        # 3. Crear usuario admin
        create_admin_user(cursor, colegio_id, rol_id)
        
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
    print(f"Email: {ADMIN_EMAIL}")
    print(f"Password: {ADMIN_PASSWORD}")
    print(f"Colegio: {COLEGIO_NOMBRE}")
    print("=" * 60)
    
    confirm = input("\n¿Deseas continuar? (s/n): ")
    if confirm.lower() == 's':
        seed_database()
    else:
        print("Operación cancelada.")



        