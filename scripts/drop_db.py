# Ejecución: python scripts/drop_db.py
import psycopg2
from dotenv import load_dotenv
import os
from pathlib import Path

env_path = Path(__file__).resolve().parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASS = os.getenv('DB_PASS', 'tu_contraseña_root')
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME', 'chronos_db')

def drop_database():
    confirm = input(f"¿Estás seguro de que quieres BORRAR la base de datos '{DB_NAME}'? (s/n): ")
    if confirm.lower() != 's':
        print("Operación cancelada.")
        return

    try:
        conn = psycopg2.connect(
            dbname="postgres",
            user=DB_USER,
            password=DB_PASS,
            host=DB_HOST,
            port=DB_PORT
        )
        conn.autocommit = True
        cursor = conn.cursor()
        
        # Terminar conexiones activas para poder borrar
        cursor.execute(f"""
            SELECT pg_terminate_backend(pg_stat_activity.pid) 
            FROM pg_stat_activity 
            WHERE pg_stat_activity.datname = '{DB_NAME}' 
            AND pid <> pg_backend_pid();
        """)
        
        cursor.execute(f'DROP DATABASE IF EXISTS {DB_NAME}')
        print(f"🗑️ Base de datos '{DB_NAME}' eliminada exitosamente.")
        
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"❌ Error al eliminar la base de datos: {e}")

if __name__ == '__main__':
    drop_database()