# Ejecución: python scripts/backup_db.py
# Genera un archivo .sql con toda la estructura y datos de la base de datos
import os
import subprocess
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime

# Cargar .env desde la raíz del proyecto
env_path = Path(__file__).resolve().parent.parent / '.env'
load_dotenv(dotenv_path=env_path, override=True)

DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASS = os.getenv('DB_PASS', '')
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME', 'chronos_db')

def backup_database():
    # Crear carpeta de backups si no existe
    backup_dir = Path(__file__).resolve().parent.parent / 'backups'
    backup_dir.mkdir(exist_ok=True)
    
    # Generar nombre de archivo con timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_file = backup_dir / f'backup_{DB_NAME}_{timestamp}.sql'
    
    print(f"📦 Generando backup de '{DB_NAME}'...")
    print(f"   Archivo: {backup_file}")
    
    try:
        # Configurar contraseña en variable de entorno para pg_dump
        env = os.environ.copy()
        env['PGPASSWORD'] = DB_PASS
        
        # Ejecutar pg_dump
        cmd = [
            'pg_dump',
            '-h', DB_HOST,
            '-p', DB_PORT,
            '-U', DB_USER,
            '-d', DB_NAME,
            '-F', 'p',  # Formato plain SQL
            '-v',       # Verbose
            '-f', str(backup_file)
        ]
        
        result = subprocess.run(cmd, env=env, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"✅ Backup generado exitosamente: {backup_file.name}")
            print(f"   Tamaño: {backup_file.stat().st_size / 1024:.2f} KB")
        else:
            print(f"❌ Error al generar backup:")
            print(result.stderr)
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == '__main__':
    backup_database()