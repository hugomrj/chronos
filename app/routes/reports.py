from collections import defaultdict

from flask import abort, flash, redirect, render_template, request, url_for
from flask_login import login_required

from app.extensions import db
from app.models import (
    AnioLectivo, AreaConocimiento, Grado, GradoMateria, HorarioCelda,
    HorarioVersion, Materia, PlanEstudio, Profesor, Seccion, SeccionMateria,
    Turno,
)
from app.utils.helpers import (
    DIAS_SEMANA, TIPOS_PLAN_LABEL, anio_activo, colegio_actual,
    etiqueta_bloque, etiqueta_seccion, parse_int,
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
    # DISTRIBUCIÓN DE MATERIAS POR PLAN / GRADO
    # ------------------------------------------------------------------
    @app.route('/reportes/distribucion')
    @login_required
    def distribucion_materias():
        colegio = _colegio()
        if not colegio:
            return redirect(url_for('colegios'))

        anios = AnioLectivo.query.filter_by(colegio_id=colegio.id) \
                                  .order_by(AnioLectivo.nombre.desc()).all()
        anio = None
        anio_id = request.args.get('anio_id', type=int)
        if anio_id:
            anio = db.session.get(AnioLectivo, anio_id)
            if anio and anio.colegio_id != colegio.id:
                anio = None
        if anio is None:
            anio = anio_activo(colegio.id) or (anios[0] if anios else None)

        planes = PlanEstudio.query.filter_by(colegio_id=colegio.id) \
                                   .order_by(PlanEstudio.orden, PlanEstudio.nombre).all()
        plan = None
        plan_id = request.args.get('plan_id', type=int)
        if plan_id:
            plan = db.session.get(PlanEstudio, plan_id)
            if plan and plan.colegio_id != colegio.id:
                plan = None
        if plan is None:
            plan = planes[0] if planes else None

        grados = []
        if plan:
            grados = Grado.query.filter_by(plan_id=plan.id) \
                                 .order_by(Grado.orden, Grado.nombre).all()
        grado = None
        grado_id = request.args.get('grado_id', type=int)
        if grado_id:
            grado = db.session.get(Grado, grado_id)
            if grado and (not plan or grado.plan_id != plan.id):
                grado = None
        if grado is None and grados:
            grado = grados[0]

        secciones = []
        items = []
        grupos = []
        total_general = 0
        totales_seccion = {}
        if anio and grado:
            secciones = Seccion.query.filter_by(
                anio_lectivo_id=anio.id, grado_id=grado.id
            ).order_by(Seccion.nombre).all()
            seccion_ids = [s.id for s in secciones]
            sms = SeccionMateria.query.filter(
                SeccionMateria.seccion_id.in_(seccion_ids)
            ).all() if seccion_ids else []
            sm_map = {(sm.seccion_id, sm.materia_id): sm for sm in sms}
            totales_seccion = {s.id: 0 for s in secciones}

            # Docente real: primero el fijado en el plan de la sección;
            # si no, el que quedó asignado en la versión vigente del turno.
            versiones = HorarioVersion.query.filter_by(
                anio_lectivo_id=anio.id
            ).all()
            vigentes = {}
            for v in versiones:
                actual = vigentes.get(v.turno_id)
                if actual is None:
                    vigentes[v.turno_id] = v
                elif v.estado == 'publicado' and actual.estado != 'publicado':
                    vigentes[v.turno_id] = v
                elif (v.estado == actual.estado and
                      v.creado_en and actual.creado_en and
                      v.creado_en > actual.creado_en):
                    vigentes[v.turno_id] = v
            version_ids = [v.id for v in vigentes.values()]
            prof_map = {}
            if version_ids:
                for celda in HorarioCelda.query.filter(
                        HorarioCelda.version_id.in_(version_ids)).all():
                    sm = celda.seccion_materia
                    if sm and celda.profesor:
                        prof_map[(sm.seccion_id, sm.materia_id)] = celda.profesor
            for sm in sms:
                totales_seccion[sm.seccion_id] = totales_seccion.get(sm.seccion_id, 0) + sm.horas_semanales

            items = GradoMateria.query.filter_by(grado_id=grado.id) \
                                       .join(Materia).order_by(Materia.nombre).all()

            orden_tipo = {'comun': 1, 'especifico': 2, 'optativo': 3}
            filas = []
            for gm in items:
                area_principal = gm.materia.area
                filas.append({
                    'gm': gm,
                    'tipo_plan': gm.tipo_plan,
                    'tipo_label': TIPOS_PLAN_LABEL.get(gm.tipo_plan, gm.tipo_plan),
                    'area': area_principal,
                    'horas': gm.horas_semanales,
                    'docentes': [
                        {
                            'sm': sm_map.get((s.id, gm.materia_id)),
                            'profesor': (
                                sm_map[(s.id, gm.materia_id)].profesor
                                if sm_map.get((s.id, gm.materia_id)) and
                                sm_map[(s.id, gm.materia_id)].profesor
                                else prof_map.get((s.id, gm.materia_id))
                            ),
                        }
                        for s in secciones
                    ],
                })

            filas.sort(key=lambda f: (
                orden_tipo.get(f['tipo_plan'], 9),
                f['area'].orden if f['area'] else 999,
                f['area'].nombre if f['area'] else 'Sin área',
                f['gm'].materia.nombre,
            ))

            grupos_map = {}
            for fila in filas:
                clave = (fila['tipo_plan'],
                         fila['area'].id if fila['area'] else 0)
                if clave not in grupos_map:
                    grupos_map[clave] = {
                        'tipo_label': fila['tipo_label'],
                        'area_nombre': fila['area'].nombre if fila['area'] else 'Sin área',
                        'filas': [],
                        'total': 0,
                    }
                    grupos.append(grupos_map[clave])
                grupos_map[clave]['filas'].append(fila)
                grupos_map[clave]['total'] += fila['horas']
                total_general += fila['horas']

        return render_template(
            'reportes/distribucion.html',
            crumb='Distribución de materias',
            colegio=colegio,
            anios=anios,
            anio=anio,
            planes=planes,
            plan=plan,
            grados=grados,
            grado=grado,
            secciones=secciones,
            grupos=grupos,
            total_general=total_general,
            totales_seccion=totales_seccion,
            tipos_plan_label=TIPOS_PLAN_LABEL,
        )

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
