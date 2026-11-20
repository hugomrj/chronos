"""Crea el archivo .env de una nueva instancia (un colegio por instancia).

Uso:
    python scripts/nuevo_colegio.py <COLEGIO_ID> <nombre_instancia> [--force]

Genera `.env.<nombre_instancia>` a partir de `.env.example`, con:
  * COLEGIO_ID del colegio,
  * SECRET_KEY aleatoria,
  * BASE_COLEGIO vacío (la instancia toma el nombre desde la base).

Ejemplo de despliegue:

    python scripts/nuevo_colegio.py 2 sanjose
    ln -sf .env.sanjose .env      # en la carpeta de la instancia 2
    gunicorn -w 2 -b 127.0.0.1:8001 wsgi:app
"""
import argparse
import secrets
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
PLANTILLA = BASE_DIR / '.env.example'


def leer_plantilla():
    if not PLANTILLA.exists():
        sys.exit(f'No se encontró la plantilla {PLANTILLA}')
    return PLANTILLA.read_text(encoding='utf-8')


def reemplazar(texto, clave, valor):
    lineas = []
    encontrado = False
    for linea in texto.splitlines():
        if linea.startswith(f'{clave}='):
            lineas.append(f'{clave}={valor}')
            encontrado = True
        else:
            lineas.append(linea)
    if not encontrado:
        lineas.append(f'{clave}={valor}')
    return '\n'.join(lineas) + '\n'


def main():
    parser = argparse.ArgumentParser(description='Genera el .env de una instancia por colegio.')
    parser.add_argument('colegio_id', type=int, help='ID del colegio en la tabla colegio')
    parser.add_argument('instancia', help='Nombre corto de la instancia (ej. sanjose)')
    parser.add_argument('--force', action='store_true', help='Sobrescribir si ya existe')
    args = parser.parse_args()

    destino = BASE_DIR / f'.env.{args.instancia}'
    if destino.exists() and not args.force:
        sys.exit(f'El archivo {destino.name} ya existe. Usá --force para sobrescribirlo.')

    texto = leer_plantilla()
    texto = reemplazar(texto, 'COLEGIO_ID', args.colegio_id)
    texto = reemplazar(texto, 'SECRET_KEY', secrets.token_hex(32))
    texto = reemplazar(texto, 'SUPERADMIN', 'False')

    destino.write_text(texto, encoding='utf-8')
    destino.chmod(0o600)

    print(f'Instancia creada: {destino.name}')
    print(f'  COLEGIO_ID = {args.colegio_id}')
    print('  Review: DB_*, HOST, PORT y USE_PROXY_FIX antes de arrancar.')


if __name__ == '__main__':
    main()
