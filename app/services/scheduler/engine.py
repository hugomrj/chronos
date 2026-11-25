"""Motor de generación de horarios.

Modelo MILP resuelto con PuLP + HiGHS:

* x[seccion_materia, bloque] = 1 si esa materia se dicta en ese bloque.
* y[seccion_materia, bloque, aula] = 1 si además usa esa aula.
* q[seccion_materia, par] = 1 para materias con bloque doble.

El profesor de cada sección-materia se decide antes del modelo con una
heurística determinista (respeta profesores fijados, materias habilitadas,
disponibilidad y carga máxima). El modelo garantiza que no haya choques.
"""
from __future__ import annotations

import time as _time
from collections import defaultdict
from dataclasses import dataclass, field

from pulp import HiGHS, LpMinimize, LpProblem, lpSum, value as lp_value

from app.services.scheduler.constraints import (
    aulas_elegibles, bloques_clase, bloques_por_dia, bloques_solapados,
    pares_consecutivos, profesor_disponible, reglas_que_aplican,
    ultimo_bloque_por_dia, primer_receso,
)


@dataclass
class Asignacion:
    seccion_materia_id: int
    bloque_id: int
    aula_id: int | None
    profesor_id: int | None
    fijado: bool = False


@dataclass
class ResultadoGeneracion:
    ok: bool
    estado: str
    mensaje: str
    asignaciones: list[Asignacion] = field(default_factory=list)
    estadisticas: dict = field(default_factory=dict)
    advertencias: list[str] = field(default_factory=list)
    detalle: list[str] = field(default_factory=list)


class _Item:
    def __init__(self, sm, seccion, bloques, aulas):
        self.sm = sm
        self.seccion = seccion
        self.profesor = None
        self.bloques = bloques
        self.bloques_ids = {b.id for b in bloques}
        self.aulas = aulas
        self.horas = sm.horas_semanales


def _sanitizar(texto):
    return ''.join(c if c.isalnum() else '_' for c in str(texto))



def _profesor_habilitado(profesor, seccion, materia):
    """Materia habilitada y, si es técnica, especialidad compatible."""
    if materia not in profesor.materias:
        return False
    if not materia.especialidades:
        return True
    if not seccion.especialidad:
        return False
    if seccion.especialidad not in materia.especialidades:
        return False
    return seccion.especialidad in profesor.especialidades

def generar_horario(secciones, profesores, aulas, reglas, limite_segundos=30, fijados=None):
    """Genera un horario para las secciones recibidas (de un mismo turno)."""
    inicio = _time.perf_counter()
    advertencias = []
    detalle = []

    fijados = fijados or []

    if not secciones:
        return ResultadoGeneracion(
            False, 'sin_datos',
            'No hay secciones para generar en el turno seleccionado.',
            detalle=['Cargá al menos una sección con su plan de estudios.'],
        )

    items = []
    for seccion in secciones:
        bloques = bloques_clase(seccion.plantilla)
        if not bloques:
            detalle.append(
                f'La plantilla de {seccion.grado.nombre} {seccion.nombre} no tiene bloques de clase.'
            )
            continue
        if not seccion.materias:
            detalle.append(
                f'{seccion.grado.nombre} {seccion.nombre} no tiene materias en su plan.'
            )
            continue
        for sm in seccion.materias:
            items.append(_Item(sm, seccion, bloques,
                               aulas_elegibles(sm, seccion, aulas)))

    if detalle:
        return ResultadoGeneracion(
            False, 'validacion', 'Faltan datos para generar el horario.', detalle=detalle,
        )

    # ------------------------------------------------------------------
    # Celdas fijadas: se fuerzan en el modelo
    # ------------------------------------------------------------------
    items_por_sm = {item.sm.id: item for item in items}
    fijos_por_sm = defaultdict(list)
    profesor_forzado = {}
    for fijo in fijados:
        sm_id = fijo['seccion_materia_id']
        item = items_por_sm.get(sm_id)
        if item is None:
            detalle.append('Una celda fijada pertenece a una sección que ya no está en el turno.')
            continue
        if fijo['bloque_id'] not in item.bloques_ids:
            detalle.append(
                f'Una celda fijada de {item.sm.materia.nombre} usa un bloque '
                f'que no pertenece a su plantilla.'
            )
            continue
        aula_id = fijo.get('aula_id')
        if aula_id and aula_id not in {a.id for a in item.aulas}:
            detalle.append(
                f'Una celda fijada de {item.sm.materia.nombre} usa un aula '
                f'que ya no está disponible para esa materia.'
            )
            continue
        profesor_id = fijo.get('profesor_id')
        if profesor_id:
            prof = next((p for p in profesores if p.id == profesor_id), None)
            if not prof or not prof.activo:
                detalle.append(
                    f'Una celda fijada de {item.sm.materia.nombre} tiene un profesor inactivo.'
                )
                continue
            profesor_forzado[sm_id] = prof
        fijos_por_sm[sm_id].append(fijo)

    if detalle:
        return ResultadoGeneracion(
            False, 'validacion', 'Las celdas fijadas no son compatibles con los datos actuales.',
            detalle=detalle,
        )

    # ------------------------------------------------------------------
    # Profesores: fijados o asignados por heurística
    # ------------------------------------------------------------------
    profesores_activos = [p for p in profesores if p.activo]
    carga = defaultdict(int)
    sin_profesor = []
    habitaciones_faltantes = []

    for item in items:
        sm = item.sm
        if not item.aulas:
            habitaciones_faltantes.append(
                f'{sm.materia.nombre} en {item.seccion.grado.nombre} {item.seccion.nombre}'
                f' no tiene aulas disponibles del tipo requerido.'
            )
            continue

        if sm.id in profesor_forzado:
            prof = profesor_forzado[sm.id]
            if not _profesor_habilitado(prof, item.seccion, sm.materia):
                sin_profesor.append(
                    f'{prof.nombre} no está habilitado para {sm.materia.nombre} '
                    f'en {item.seccion.grado.nombre} {item.seccion.nombre}.'
                )
                continue
            item.profesor = prof
            disponibles = sum(1 for b in item.bloques if profesor_disponible(prof, b))
            if disponibles == 0:
                sin_profesor.append(
                    f'{prof.nombre} no tiene disponibilidad para '
                    f'{sm.materia.nombre} en {item.seccion.grado.nombre} {item.seccion.nombre}.'
                )
        elif sm.profesor_id:
            prof = next((p for p in profesores if p.id == sm.profesor_id), None)
            if prof is None or not prof.activo:
                sin_profesor.append(
                    f'{sm.materia.nombre} en {item.seccion.grado.nombre} {item.seccion.nombre}:'
                    f' el profesor asignado no está activo.'
                )
                continue
            if not _profesor_habilitado(prof, item.seccion, sm.materia):
                sin_profesor.append(
                    f'{prof.nombre} no está habilitado para {sm.materia.nombre} '
                    f'en {item.seccion.grado.nombre} {item.seccion.nombre}.'
                )
                continue
            item.profesor = prof
            disponibles = sum(1 for b in item.bloques if profesor_disponible(prof, b))
            if disponibles == 0:
                sin_profesor.append(
                    f'{prof.nombre} no tiene disponibilidad para '
                    f'{sm.materia.nombre} en {item.seccion.grado.nombre} {item.seccion.nombre}.'
                )
                continue
        else:
            candidatos = [
                p for p in profesores_activos
                if _profesor_habilitado(p, item.seccion, sm.materia)
            ]
            candidatos = [p for p in candidatos
                          if any(profesor_disponible(p, b) for b in item.bloques)]
            if not candidatos:
                sin_profesor.append(
                    f'No hay profesor habilitado y disponible para '
                    f'{sm.materia.nombre} en {item.seccion.grado.nombre} {item.seccion.nombre}.'
                )
                continue

            con_capacidad = [
                p for p in candidatos
                if not p.horas_max_semana or carga[p.id] + item.horas <= p.horas_max_semana
            ]
            if not con_capacidad:
                advertencias.append(
                    f'La carga de los profesores habilitados para {sm.materia.nombre} '
                    f'supera su máximo semanal; el modelo puede resultar infactible.'
                )
            pool = con_capacidad or candidatos

            def _score(p):
                disponibles = sum(1 for b in item.bloques if profesor_disponible(p, b))
                return (-disponibles, carga[p.id], p.id)

            item.profesor = min(pool, key=_score)

        carga[item.profesor.id] += item.horas

    detalle.extend(sin_profesor)
    detalle.extend(habitaciones_faltantes)
    if detalle:
        return ResultadoGeneracion(
            False, 'validacion', 'No se puede armar el horario con los datos actuales.',
            detalle=detalle, advertencias=advertencias,
        )

    # ------------------------------------------------------------------
    # Validaciones de factibilidad evidentes
    # ------------------------------------------------------------------
    for seccion in secciones:
        plan = sum(sm.horas_semanales for sm in seccion.materias)
        disponibles = len(bloques_clase(seccion.plantilla))
        if plan > disponibles:
            detalle.append(
                f'{seccion.grado.nombre} {seccion.nombre}: el plan suma {plan} horas '
                f'pero la plantilla tiene {disponibles} bloques de clase.'
            )

    for item in items:
        if item.horas > len(item.bloques):
            detalle.append(
                f'{item.sm.materia.nombre} pide {item.horas} horas y solo hay '
                f'{len(item.bloques)} bloques disponibles.'
            )
        if item.sm.requiere_bloque_doble:
            if item.horas % 2 != 0:
                detalle.append(
                    f'{item.sm.materia.nombre} requiere bloque doble pero tiene '
                    f'{item.horas} horas (debe ser par).'
                )
            pares = [
                (b1, b2) for b1, b2 in pares_consecutivos(item.bloques)
                if profesor_disponible(item.profesor, b1)
                and profesor_disponible(item.profesor, b2)
            ]
            if not pares:
                detalle.append(
                    f'{item.sm.materia.nombre} requiere bloque doble pero la plantilla '
                    f'no tiene pares consecutivos disponibles.'
                )
            if item.sm.max_bloques_por_dia < 2:
                detalle.append(
                    f'{item.sm.materia.nombre} requiere bloque doble y su máximo por día es 1.'
                )

    for prof in profesores:
        if prof.horas_max_semana and carga[prof.id] > prof.horas_max_semana:
            detalle.append(
                f'{prof.nombre}: carga asignada {carga[prof.id]} h '
                f'supera su máximo semanal de {prof.horas_max_semana} h.'
            )

    if detalle:
        return ResultadoGeneracion(
            False, 'validacion', 'El horario no es factible con la configuración actual.',
            detalle=detalle, advertencias=advertencias,
        )

    # ------------------------------------------------------------------
    # Modelo
    # ------------------------------------------------------------------
    prob = LpProblem('chronos_horario', LpMinimize)
    x = {}
    for item in items:
        for b in item.bloques:
            x[(item.sm.id, b.id)] = prob.add_variable(
                f"x_{item.sm.id}_{b.id}", cat='Binary')

    # Disponibilidad del profesor: bloque no permitido => x = 0
    for item in items:
        for b in item.bloques:
            if not profesor_disponible(item.profesor, b):
                prob.addConstraint(
                    x[(item.sm.id, b.id)] == 0,
                    name=f"nodisp_{item.sm.id}_{b.id}",
                )

    # Horas exactas + bloques dobles
    for item in items:
        sm = item.sm
        if sm.requiere_bloque_doble:
            pares = [
                (b1, b2) for b1, b2 in pares_consecutivos(item.bloques)
                if profesor_disponible(item.profesor, b1)
                and profesor_disponible(item.profesor, b2)
            ]
            q = {}
            for idx, (b1, b2) in enumerate(pares):
                q[(b1.id, b2.id)] = prob.add_variable(
                    f"q_{sm.id}_{idx}", cat='Binary')

            prob.addConstraint(
                lpSum(q.values()) == sm.horas_semanales // 2,
                name=f"horas_dobles_{sm.id}",
            )
            for b in item.bloques:
                involucradas = [
                    var for (id1, id2), var in q.items()
                    if b.id in (id1, id2)
                ]
                prob.addConstraint(
                    x[(sm.id, b.id)] == lpSum(involucradas) if involucradas else x[(sm.id, b.id)] == 0,
                    name=f"doble_{sm.id}_{b.id}",
                )
        else:
            prob.addConstraint(
                lpSum(x[(sm.id, b.id)] for b in item.bloques) == sm.horas_semanales,
                name=f"horas_{sm.id}",
            )

        # Máximo por día
        for dia, del_dia in bloques_por_dia(item.bloques).items():
            prob.addConstraint(
                lpSum(x[(sm.id, b.id)] for b in del_dia) <= sm.max_bloques_por_dia,
                name=f"maxdia_{sm.id}_{dia}",
            )

    # Una sola clase por sección y bloque
    for seccion in secciones:
        bloques = bloques_clase(seccion.plantilla)
        for b in bloques:
            terminos = [
                x[(item.sm.id, b.id)] for item in items
                if item.seccion.id == seccion.id and b.id in item.bloques_ids
            ]
            if terminos:
                prob.addConstraint(
                    lpSum(terminos) <= 1,
                    name=f"seccion_{seccion.id}_{b.id}",
                )

    # Choques de profesor (bloques que se superponen en el tiempo)
    bloques_globales = {b.id: b for item in items for b in item.bloques}
    pares_solapados = bloques_solapados(list(bloques_globales.values()))

    por_profesor = defaultdict(list)
    for item in items:
        por_profesor[item.profesor.id].append(item)

    for prof_id, sus_items in por_profesor.items():
        # Dos clases en el mismo bloque para el mismo profesor
        for b in bloques_globales.values():
            terminos = [
                x[(item.sm.id, b.id)] for item in sus_items
                if b.id in item.bloques_ids
            ]
            if terminos:
                prob.addConstraint(
                    lpSum(terminos) <= 1,
                    name=f"prof_bloque_{prof_id}_{b.id}",
                )

        for b1, b2 in pares_solapados:
            terminos = []
            for item in sus_items:
                if b1.id in item.bloques_ids:
                    terminos.append(x[(item.sm.id, b1.id)])
                if b2.id in item.bloques_ids:
                    terminos.append(x[(item.sm.id, b2.id)])
            if terminos:
                prob.addConstraint(
                    lpSum(terminos) <= 1,
                    name=f"prof_{prof_id}_{b1.id}_{b2.id}",
                )

    # Aulas: y[sm, bloque, aula]
    y = {}
    for item in items:
        for b in item.bloques:
            aula_vars = []
            for aula in item.aulas:
                var = prob.add_variable(
                    f"y_{item.sm.id}_{b.id}_{aula.id}", cat='Binary')
                y[(item.sm.id, b.id, aula.id)] = var
                aula_vars.append(var)
            prob.addConstraint(
                lpSum(aula_vars) == x[(item.sm.id, b.id)],
                name=f"aula_{item.sm.id}_{b.id}",
            )

    # Celdas fijadas: x = 1 y, si tiene aula, y = 1
    for sm_id, fijos in fijos_por_sm.items():
        for fijo in fijos:
            b_id = fijo['bloque_id']
            prob.addConstraint(
                x[(sm_id, b_id)] == 1,
                name=f"fijo_x_{sm_id}_{b_id}",
            )
            aula_id = fijo.get('aula_id')
            if aula_id:
                prob.addConstraint(
                    y[(sm_id, b_id, aula_id)] == 1,
                    name=f"fijo_y_{sm_id}_{b_id}_{aula_id}",
                )

    # Choques de aula
    aulas_usadas = {a.id: a for item in items for a in item.aulas}
    for aula_id in aulas_usadas:
        # Dos clases en el mismo bloque para la misma aula
        for b in bloques_globales.values():
            terminos = [
                y[(item.sm.id, b.id, aula_id)] for item in items
                if b.id in item.bloques_ids and any(a.id == aula_id for a in item.aulas)
            ]
            if terminos:
                prob.addConstraint(
                    lpSum(terminos) <= 1,
                    name=f"aula_bloque_{aula_id}_{b.id}",
                )

        for b1, b2 in pares_solapados:
            terminos = []
            for item in items:
                if aula_id not in {a.id for a in item.aulas}:
                    continue
                if b1.id in item.bloques_ids:
                    terminos.append(y[(item.sm.id, b1.id, aula_id)])
                if b2.id in item.bloques_ids:
                    terminos.append(y[(item.sm.id, b2.id, aula_id)])
            if terminos:
                prob.addConstraint(
                    lpSum(terminos) <= 1,
                    name=f"aula_choque_{aula_id}_{b1.id}_{b2.id}",
                )

    # Carga máxima de profesores (semana y día)
    for prof in profesores:
        sus_items = por_profesor.get(prof.id, [])
        if not sus_items:
            continue
        total = lpSum(
            x[(item.sm.id, b.id)]
            for item in sus_items for b in item.bloques
        )
        if prof.horas_max_semana:
            prob.addConstraint(total <= prof.horas_max_semana,
                               name=f"maxsem_{prof.id}")

        limite_dia = None
        for regla in reglas:
            if (regla.activa and regla.codigo == 'MAX_HORAS_DIA_PROFESOR'
                    and (regla.profesor_id in (None, prof.id))):
                horas_param = regla.parametros.get('horas') if regla.parametros else None
                if isinstance(horas_param, int) and horas_param > 0:
                    limite_dia = min(limite_dia or horas_param, horas_param)

        if limite_dia:
            for dia in range(1, 8):
                terminos = [
                    x[(item.sm.id, b.id)] for item in sus_items
                    for b in item.bloques if b.dia_semana == dia
                ]
                if terminos:
                    prob.addConstraint(
                        lpSum(terminos) <= limite_dia,
                        name=f"maxdia_prof_{prof.id}_{dia}",
                    )

    # ------------------------------------------------------------------
    # Reglas blandas
    # ------------------------------------------------------------------
    costo = []
    reglas_no_aplicadas = set()

    for item in items:
        aplicables = reglas_que_aplican(
            reglas, item.sm, item.seccion, item.profesor)
        ultimos = ultimo_bloque_por_dia(item.bloques)
        receso = primer_receso(item.seccion.plantilla)

        for regla in aplicables:
            peso = max(0, regla.peso or 0)
            if regla.codigo == 'NO_ULTIMA_HORA':
                for dia, ultimo in ultimos.items():
                    if regla.obligatoria:
                        prob.addConstraint(x[(item.sm.id, ultimo.id)] == 0,
                                           name=f"regla_ult_{item.sm.id}_{dia}")
                    elif peso:
                        costo.append(peso * x[(item.sm.id, ultimo.id)])

            elif regla.codigo == 'ANTES_DE_RECESO':
                if receso:
                    despues = [b for b in item.bloques if b.hora_inicio >= receso]
                    for b in despues:
                        if regla.obligatoria:
                            prob.addConstraint(
                                x[(item.sm.id, b.id)] == 0,
                                name=f"regla_rec_{item.sm.id}_{b.id}")
                        elif peso:
                            costo.append(peso * x[(item.sm.id, b.id)])

            elif regla.codigo == 'DISTRIBUIR_SEMANA':
                if peso:
                    dias = []
                    for dia, del_dia in bloques_por_dia(item.bloques).items():
                        dv = prob.add_variable(
                            f"dia_{item.sm.id}_{dia}", cat='Binary')
                        for b in del_dia:
                            prob.addConstraint(x[(item.sm.id, b.id)] <= dv)
                        prob.addConstraint(
                            dv <= lpSum(x[(item.sm.id, b.id)] for b in del_dia),
                            name=f"dia_uso_{item.sm.id}_{dia}",
                        )
                        dias.append(dv)
                    # Cuantos más días distintos, menor el costo.
                    costo.append(-peso * lpSum(dias))

            elif regla.codigo == 'EVITAR_HUECOS_PROFESOR':
                # Aproximación lineal: penaliza retomar clases después de un hueco.
                pass  # se agrega abajo, una vez por profesor

            elif regla.codigo == 'MAX_HORAS_DIA_PROFESOR':
                pass  # ya se aplicó como restricción dura

            else:
                reglas_no_aplicadas.add(regla.codigo)

    # Penalización de huecos por profesor (aproximación)
    reglas_huecos = [
        r for r in reglas
        if r.activa and r.codigo == 'EVITAR_HUECOS_PROFESOR' and (r.peso or 0) > 0
    ]
    if reglas_huecos:
        peso_huecos = max(r.peso for r in reglas_huecos)
        advertencias.append(
            'EVITAR_HUECOS_PROFESOR se aplica como penalización de reanudación '
            'después de un hueco (aproximación lineal).'
        )
        for prof in profesores:
            sus_items = por_profesor.get(prof.id, [])
            if not sus_items:
                continue
            bloques_prof = {}
            for item in sus_items:
                for b in item.bloques:
                    bloques_prof[b.id] = b
            for dia, del_dia in bloques_por_dia(list(bloques_prof.values())).items():
                for prev, curr in zip(del_dia, del_dia[1:]):
                    if prev.hora_fin >= curr.hora_inicio:
                        continue
                    usados_prev = []
                    usados_curr = []
                    for item in sus_items:
                        if prev.id in item.bloques_ids:
                            usados_prev.append(x[(item.sm.id, prev.id)])
                        if curr.id in item.bloques_ids:
                            usados_curr.append(x[(item.sm.id, curr.id)])
                    if not usados_prev or not usados_curr:
                        continue
                    arranque = prob.add_variable(
                        f"hueco_{prof.id}_{dia}_{curr.id}", 0, 1,
                        cat='Continuous')
                    prob.addConstraint(
                        arranque >= lpSum(usados_curr) - lpSum(usados_prev),
                        name=f"hueco_c_{prof.id}_{dia}_{curr.id}",
                    )
                    costo.append(peso_huecos * arranque)

    if reglas_no_aplicadas:
        advertencias.append(
            'Reglas activas no aplicadas en esta versión: '
            + ', '.join(sorted(reglas_no_aplicadas))
        )

    prob += lpSum(costo) if costo else 0

    # ------------------------------------------------------------------
    # Resolver
    # ------------------------------------------------------------------
    stats = prob.solve(HiGHS(msg=False, timeLimit=limite_segundos))
    segundos = round(_time.perf_counter() - inicio, 2)
    estado = getattr(stats, 'status_str', str(getattr(stats, 'status', '')))

    estadisticas = {
        'estado_solver': estado,
        'segundos': segundos,
        'variables': prob.numVariables(),
        'restricciones': prob.numConstraints(),
        'items': len(items),
        'bloques': len(bloques_globales),
        'profesores': len({item.profesor.id for item in items}),
    }

    if str(estado).lower() != 'optimal':
        mensaje = {
            'infeasible': 'No existe un horario que cumpla todas las restricciones duras.',
            'time limit': f'El solver alcanzó el límite de {limite_segundos} segundos sin demostrar optimalidad.',
        }.get(str(estado).lower(), f'El solver terminó con estado: {estado}.')
        detalle = [
            'Revisá la disponibilidad de los profesores y sus horas máximas.',
            'Verificá que cada materia tenga aulas del tipo requerido.',
            'Comprobá que el plan no supere los bloques de clase de la plantilla.',
            'Si hay bloques dobles, asegurate de que existan pares consecutivos.',
        ]
        return ResultadoGeneracion(
            False, 'solver', mensaje,
            estadisticas=estadisticas, advertencias=advertencias, detalle=detalle,
        )

    # ------------------------------------------------------------------
    # Extraer solución
    # ------------------------------------------------------------------
    asignaciones = []
    for item in items:
        elegidos = [b for b in item.bloques
                    if (x[(item.sm.id, b.id)].value() or 0) > 0.5]
        if len(elegidos) != item.horas:
            return ResultadoGeneracion(
                False, 'extraccion',
                f'El solver devolvió {len(elegidos)} bloques para '
                f'{item.sm.materia.nombre} en {item.seccion.nombre} '
                f'(se esperaban {item.horas}).',
                estadisticas=estadisticas, advertencias=advertencias,
            )
        for b in elegidos:
            aula = None
            mejor = -1.0
            for a in item.aulas:
                valor = y[(item.sm.id, b.id, a.id)].value() or 0
                if valor > mejor:
                    mejor = valor
                    aula = a
            asignaciones.append(Asignacion(
                seccion_materia_id=item.sm.id,
                bloque_id=b.id,
                aula_id=aula.id if aula else None,
                profesor_id=item.profesor.id,
                fijado=(b.id in {(f['bloque_id']) for f in fijos_por_sm.get(item.sm.id, [])}),
            ))

    estadisticas['celdas'] = len(asignaciones)
    try:
        valor_objetivo = lp_value(prob.objective)
    except Exception:
        valor_objetivo = None
    estadisticas['objetivo'] = round(valor_objetivo, 2) if valor_objetivo is not None else None
    return ResultadoGeneracion(
        True, 'ok', f'Horario generado: {len(asignaciones)} bloques asignados.',
        asignaciones=asignaciones, estadisticas=estadisticas,
        advertencias=advertencias,
    )
