from collections import defaultdict

from flask import abort, flash, redirect, render_template, request, url_for
from flask_login import login_required

from app.extensions import db
from app.models import (
    Grado, HorarioCelda, HorarioVersion, Profesor, Seccion, Turno,
)
from app.utils.helpers import (
    DIAS_SEMANA, anio_activo, colegio_actual, etiqueta_bloque,
    etiqueta_seccion,
)


def register_report_routes(app):
    """Reportes imprimibles: horario general y horario individual docente."""

    def _colegio():
        colegio = colegio_actual()
        if not colegio:
            flash('Primero creá un colegio para continuar.', 'warning')
        return colegio

    def _version(version_id, colegio):
        version = db.get_or_404(HorarioVersion, version_id)
        if version.anio_lectivo.colegio_id != colegio.id:
            abort(404)
        return version

    def _secciones(version):
        return Seccion.query.join(Grado).filter(
            Seccion.anio_lectivo_id == version.anio_lectivo_id,
            Seccion.turno_id == version.turno_id,
        ).order_by(Grado.orden, Grado.nombre, Seccion.nombre).all()

    def _versiones_vigentes(colegio, anio):
        """La versión vigente de cada turno: publicada o, si no, el último borrador."""
        if not anio:
            return []

        vigentes = []
        for turno in Turno.query.filter_by(colegio_id=colegio.id).all():
            version = HorarioVersion.query.filter_by(
                anio_lectivo_id=anio.id,
                turno_id=turno.id,
                estado='publicado',
            ).first()
            if version is None:
                version = HorarioVersion.query.filter_by(
                    anio_lectivo_id=anio.id, turno_id=turno.id
                ).order_by(HorarioVersion.creado_en.desc()).first()
            if version:
                vigentes.append(version)
        return vigentes

    # ------------------------------------------------------------------
    # HORARIO GENERAL (todas las secciones de un turno)
    # ------------------------------------------------------------------
    @app.route('/horarios/<int:version_id>/general')
    @login_required
    def horario_general(version_id):
        colegio = _colegio()
        if not colegio:
            return redirect(url_for('colegios'))
        version = _version(version_id, colegio)
        secciones = _secciones(version)

        if not secciones:
            flash('La versión no tiene secciones.', 'warning')
            return redirect(url_for('horario_detalle', version_id=version.id))

        celdas = HorarioCelda.query.filter_by(version_id=version.id).all()
        celdas_map = {(c.seccion_id, c.bloque_id): c for c in celdas}

        # Días con bloques en las plantillas de las secciones
        dias = sorted({
            b.dia_semana
            for s in secciones for b in s.plantilla.bloques
        })
        dia = request.args.get('dia', type=int) or (dias[0] if dias else 1)
        if dia not in dias:
            dia = dias[0] if dias else 1

        # Unión de bloques del día, por rango horario
        filas = {}
        for s in secciones:
            for b in s.plantilla.bloques:
                if b.dia_semana != dia:
                    continue
                clave = (b.hora_inicio, b.hora_fin, b.tipo)
                if clave not in filas:
                    filas[clave] = {
                        'inicio': b.hora_inicio,
                        'fin': b.hora_fin,
                        'tipo': b.tipo,
                        'bloques': {},
                    }
                filas[clave]['bloques'][s.id] = b

        filas_data = []
        salida = None
        for clave, fila in sorted(filas.items(), key=lambda kv: (kv[0][0], kv[0][1])):
            por_seccion = {}
            for s in secciones:
                bloque = fila['bloques'].get(s.id)
                celda = celdas_map.get((s.id, bloque.id)) if bloque else None
                por_seccion[s.id] = {
                    'bloque': bloque,
                    'celda': celda,
                    'etiqueta': etiqueta_bloque(bloque)
                    if bloque and bloque.tipo != 'clase' else '',
                }
            uniforme = (
                len(fila['bloques']) == len(secciones)
                and len({b.id for b in fila['bloques'].values()}) == 1
            )
            filas_data.append({
                'inicio': fila['inicio'],
                'fin': fila['fin'],
                'tipo': fila['tipo'],
                'por_seccion': por_seccion,
                'uniforme': uniforme,
                'etiqueta': etiqueta_bloque(next(iter(fila['bloques'].values())))
                if fila['bloques'] else '',
            })
            if salida is None or fila['fin'] > salida:
                salida = fila['fin']

        return render_template(
            'horarios/general.html',
            crumb='Horario general',
            version=version,
            secciones=secciones,
            dias=dias,
            dias_nombres=DIAS_SEMANA,
            dia=dia,
            filas=filas_data,
            salida=salida,
        )

    # ------------------------------------------------------------------
    # HORARIOS DOCENTES
    # ------------------------------------------------------------------
    @app.route('/horarios/docentes')
    @login_required
    def horarios_docentes():
        colegio = _colegio()
        if not colegio:
            return redirect(url_for('colegios'))

        anio = anio_activo(colegio.id)
        versiones = _versiones_vigentes(colegio, anio)
        ids = [v.id for v in versiones]

        horas = defaultdict(int)
        if ids:
            for profesor_id, total in (
                db.session.query(HorarioCelda.profesor_id,
                                 db.func.count(HorarioCelda.id))
                .filter(HorarioCelda.version_id.in_(ids))
                .group_by(HorarioCelda.profesor_id).all()
            ):
                horas[profesor_id] = total

        profesores = Profesor.query.filter_by(
            colegio_id=colegio.id, activo=True).order_by(Profesor.nombre).all()

        return render_template(
            'horarios/docentes.html',
            crumb='Horarios docentes',
            anio=anio,
            versiones=versiones,
            profesores=profesores,
            horas=horas,
        )

    @app.route('/horarios/docentes/<int:profesor_id>')
    @login_required
    def horario_docente(profesor_id):
        colegio = _colegio()
        if not colegio:
            return redirect(url_for('colegios'))

        profesor = db.get_or_404(Profesor, profesor_id)
        if profesor.colegio_id != colegio.id:
            abort(404)

        anio = anio_activo(colegio.id)
        versiones = _versiones_vigentes(colegio, anio)
        ids = [v.id for v in versiones]

        celdas = []
        if ids:
            celdas = HorarioCelda.query.filter(
                HorarioCelda.version_id.in_(ids),
                HorarioCelda.profesor_id == profesor.id,
            ).all()

        # Agrupar por nivel y turno: cada combinación es una hoja distinta.
        por_grupo = {}
        for celda in celdas:
            seccion = celda.seccion_materia.seccion
            nivel = seccion.grado.nivel
            turno = seccion.turno
            clave = (nivel.id, turno.id)
            grupo = por_grupo.setdefault(clave, {
                'nivel': nivel,
                'turno': turno,
                'celdas': [],
            })
            grupo['celdas'].append(celda)

        bloques_nivel = []
        for grupo in por_grupo.values():
            del_grupo = grupo['celdas']
            dias = sorted({c.dia_semana for c in del_grupo})
            tiempos = sorted({(c.bloque.hora_inicio, c.bloque.hora_fin)
                              for c in del_grupo})
            mapa = {(c.dia_semana, c.bloque.hora_inicio, c.bloque.hora_fin): c
                    for c in del_grupo}
            filas = []
            for inicio, fin in tiempos:
                filas.append({
                    'inicio': inicio,
                    'fin': fin,
                    'por_dia': {d: mapa.get((d, inicio, fin)) for d in dias},
                })
            bloques_nivel.append({
                'nivel': grupo['nivel'],
                'turno': grupo['turno'],
                'dias': dias,
                'filas': filas,
                'total': len(del_grupo),
            })

        bloques_nivel.sort(key=lambda g: (g['nivel'].nombre, g['turno'].nombre))

        materias = sorted({
            c.seccion_materia.materia.nombre for c in celdas
        })
        areas = sorted({
            c.seccion_materia.seccion.grado.nivel.nombre for c in celdas
        })

        return render_template(
            'horarios/docente.html',
            crumb='Horario docente',
            profesor=profesor,
            anio=anio,
            versiones=versiones,
            total_horas=len(celdas),
            materias=materias,
            areas=areas,
            bloques_nivel=bloques_nivel,
            dias_nombres=DIAS_SEMANA,
        )
