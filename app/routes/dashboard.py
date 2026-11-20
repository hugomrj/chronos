from flask import render_template
from flask_login import login_required
from sqlalchemy import text
from app.extensions import db


def _scalar(sql, default=0):
    """Ejecuta un COUNT/SUM simple y devuelve un valor seguro."""
    try:
        value = db.session.execute(text(sql)).scalar()
        return value if value is not None else default
    except Exception:
        db.session.rollback()
        return default


def register_dashboard_routes(app):
    """Registra el dashboard principal."""

    @app.route('/dashboard')
    @login_required
    def dashboard():
        stats = {
            'profesores': _scalar("SELECT count(*) FROM profesor WHERE activo"),
            'secciones': _scalar("SELECT count(*) FROM seccion"),
            'aulas': _scalar("SELECT count(*) FROM aula WHERE activa"),
            'materias': _scalar("SELECT count(*) FROM materia"),
            'horas_plan': _scalar("SELECT coalesce(sum(horas_semanales), 0) FROM seccion_materia"),
            'bloques_asignados': _scalar("SELECT count(*) FROM horario_celda"),
            'publicados': _scalar("SELECT count(*) FROM horario_version WHERE estado = 'publicado'"),
        }

        colegio = _scalar("SELECT nombre FROM colegio ORDER BY id LIMIT 1", None)
        anio = _scalar("SELECT nombre FROM anio_lectivo WHERE activo ORDER BY id LIMIT 1", None)

        versiones = []
        try:
            versiones = db.session.execute(text("""
                SELECT coalesce(nombre, 'Versión ' || id) AS nombre,
                       estado,
                       creado_en
                FROM horario_version
                ORDER BY creado_en DESC
                LIMIT 6
            """)).fetchall()
        except Exception:
            db.session.rollback()

        return render_template(
            'dashboard.html',
            crumb='Dashboard',
            stats=stats,
            colegio=colegio,
            anio=anio,
            versiones=versiones,
        )
