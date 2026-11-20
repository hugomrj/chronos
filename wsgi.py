"""Punto de entrada para gunicorn / producción.

Uso:
    gunicorn -w 2 -b 127.0.0.1:8000 wsgi:app
Cada instancia lee su propio .env y sirve un único colegio (COLEGIO_ID).
"""
from app.factory import create_app

app = create_app()
