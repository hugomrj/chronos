from flask import redirect, render_template, url_for
from flask_login import login_required
from sqlalchemy import text

from app.extensions import db
from app.models import HorarioVersion, Seccion, Turno
from app.utils.helpers import anio_activo, colegio_actual


def _scalar(sql, params=None, default=0):
    """Ejecuta un COUNT/SUM simple y devuelve un valor seguro."""
    try:
        value = db.session.execute(text(sql), params or {}).scalar()
        return value if value is not None else default
    except Exception:
        db.session.rollback()
        return default


def register_dashboard_routes(app):
    """Registra el dashboard principal."""

    @app.route('/dashboard')
    @login_required
    def dashboard():
        colegio = colegio_actual()
        if not colegio:
            return redirect(url_for('colegios'))

        params = {'cid': colegio.id}
        stats = {
            'profesores': _scalar(
                "SELECT count(*) FROM profesor WHERE activo AND colegio_id = :cid",
                params),
            'secciones': _scalar(
                "SELECT count(*) FROM seccion s "
                "JOIN anio_lectivo a ON a.id = s.anio_lectivo_id "
                "WHERE a.colegio_id = :cid", params),
            'aulas': _scalar(
                "SELECT count(*) FROM aula WHERE activa AND colegio_id = :cid",
                params),
            'materias': _scalar(
                "SELECT count(*) FROM materia WHERE colegio_id = :cid", params),
            'horas_plan': _scalar(
                "SELECT coalesce(sum(sm.horas_semanales), 0) "
                "FROM seccion_materia sm "
                "JOIN seccion s ON s.id = sm.seccion_id "
                "JOIN anio_lectivo a ON a.id = s.anio_lectivo_id "
                "WHERE a.colegio_id = :cid", params),
            'bloques_asignados': _scalar(
                "SELECT count(*) FROM horario_celda c "
                "JOIN horario_version v ON v.id = c.version_id "
                "JOIN anio_lectivo a ON a.id = v.anio_lectivo_id "
                "WHERE a.colegio_id = :cid", params),
            'publicados': _scalar(
                "SELECT count(*) FROM horario_version v "
                "JOIN anio_lectivo a ON a.id = v.anio_lectivo_id "
                "WHERE a.colegio_id = :cid AND v.estado = 'publicado'", params),
        }

        anio = anio_activo(colegio.id)
        publicaciones = []
        versiones = []

        if anio:
            turnos = Turno.query.filter_by(colegio_id=colegio.id) \
                                 .order_by(Turno.nombre).all()
            for turno in turnos:
                version = HorarioVersion.query.filter_by(
                    anio_lectivo_id=anio.id,
                    turno_id=turno.id,
                    estado='publicado',
                ).first()
                if version:
                    celdas = len(version.celdas)
                else:
                    celdas = 0
                publicaciones.append({
                    'turno': turno,
                    'version': version,
                    'celdas': celdas,
                })

            versiones = HorarioVersion.query.filter_by(anio_lectivo_id=anio.id) \
                                            .order_by(HorarioVersion.creado_en.desc()) \
                                            .limit(8).all()

        return render_template(
            'dashboard.html',
            crumb='Dashboard',
            stats=stats,
            colegio=colegio.nombre,
            anio=anio.nombre if anio else None,
            versiones=versiones,
            publicaciones=publicaciones,
        )
