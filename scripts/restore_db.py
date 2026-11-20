# Ejecución: python scripts/restore_db.py [archivo_backup.sql]
# Si no se especifica archivo, lista los backups disponibles
import os
import sys
import subprocess
from pathlib import Path
from dotenv import load_dotenv

# Cargar .env desde la raíz del proyecto
env_path = Path(__file__).resolve().parent.parent / '.env'
load_dotenv(dotenv_path=env_path, override=True)

DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASS = os.getenv('DB_PASS', '')
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME', 'chronos_db')

def list_backups():
    """Lista todos los backups disponibles."""
    backup_dir = Path(__file__).resolve().parent.parent / 'backups'
    
    if not backup_dir.exists():
        print("❌ No existe la carpeta de backups.")
        return []
    
    backups = sorted(backup_dir.glob('backup_*.sql'), reverse=True)
    
    if not backups:
        print("⚠️ No hay backups disponibles.")
        return []
    
    print("\n📋 Backups disponibles:")
    for i, backup in enumerate(backups, 1):
        size = backup.stat().st_size / 1024
        print(f"   {i}. {backup.name} ({size:.2f} KB)")
    
    return backups

def restore_database(backup_file):
    """Restaura la base de datos desde un archivo de backup."""
    if not Path(backup_file).exists():
        print(f"❌ El archivo {backup_file} no existe.")
        return
    
    print(f"🔄 Restaurando base de datos '{DB_NAME}' desde {Path(backup_file).name}...")
    print("⚠️  Esto REEMPLAZARÁ todos los datos actuales.")
    
    confirm = input("¿Continuar? (s/n): ")
    if confirm.lower() != 's':
        print("Operación cancelada.")
        return
    
    try:
        # Configurar contraseña en variable de entorno para psql
        env = os.environ.copy()
        env['PGPASSWORD'] = DB_PASS
        
        # Ejecutar psql para restaurar
        cmd = [
            'psql',
            '-h', DB_HOST,
            '-p', DB_PORT,
            '-U', DB_USER,
            '-d', DB_NAME,
            '-f', str(backup_file),
            '-v', 'ON_ERROR_STOP=1'  # Detenerse en el primer error
        ]
        
        result = subprocess.run(cmd, env=env, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"✅ Base de datos restaurada exitosamente desde {Path(backup_file).name}")
        else:
            print(f"❌ Error al restaurar:")
            print(result.stderr)
            
    except Exception as e:
        print(f"❌ Error: {e}")

def main():
    if len(sys.argv) > 1:
        # Se especificó un archivo de backup
        restore_database(sys.argv[1])
    else:
        # Listar backups disponibles
        backups = list_backups()
        
        if backups:
            print("\n💡 Uso: python scripts/restore_db.py <archivo_backup.sql>")
            print("   Ejemplo: python scripts/restore_db.py backups/backup_chronos_db_20240115_143022.sql")

if __name__ == '__main__':
    main()