# Ejecución: python scripts/create_db.py
import psycopg2
from dotenv import load_dotenv
import os
from pathlib import Path

# Cargar .env desde la raíz del proyecto
env_path = Path(__file__).resolve().parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASS = os.getenv('DB_PASS', 'tu_contraseña_root')
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME', 'chronos_db')

def create_database():
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
        
        cursor.execute(f"SELECT 1 FROM pg_catalog.pg_database WHERE datname = '{DB_NAME}'")
        exists = cursor.fetchone()
        
        if not exists:
            cursor.execute(f'CREATE DATABASE {DB_NAME}')
            print(f"✅ Base de datos '{DB_NAME}' creada exitosamente.")
        else:
            print(f"⚠️ La base de datos '{DB_NAME}' ya existe.")
            
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"❌ Error al crear la base de datos: {e}")

if __name__ == '__main__':
    create_database()