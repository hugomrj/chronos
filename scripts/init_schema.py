# Ejecución: python scripts/init_schema.py
import psycopg2
from dotenv import load_dotenv
import os
from pathlib import Path

env_path = Path(__file__).resolve().parent.parent / '.env'
load_dotenv(dotenv_path=env_path, override=True)

DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASS = os.getenv('DB_PASS', 'tu_contraseña_root')
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME', 'chronos_db')

def init_schema():
    root_dir = Path(__file__).resolve().parent.parent
    schema_path = root_dir / 'scripts/schema.sql'

    if not schema_path.exists():
        print(f"❌ Error: No se encontró el archivo schema.sql en {schema_path}")
        return

    try:
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASS,
            host=DB_HOST,
            port=DB_PORT
        )
        cursor = conn.cursor()
        
        with open(schema_path, 'r') as f:
            sql_script = f.read()
            
        cursor.execute(sql_script)
        conn.commit()
        print("✅ Esquema de base de datos (schema.sql) aplicado exitosamente.")
        
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"❌ Error al aplicar el esquema: {e}")
        if 'conn' in locals():
            conn.rollback()

if __name__ == '__main__':
    init_schema()