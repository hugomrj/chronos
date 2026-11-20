"""Funciones puras de apoyo para el motor de horarios."""
from collections import defaultdict


def bloques_clase(plantilla):
    return [b for b in plantilla.bloques if b.tipo == 'clase']


def bloques_por_dia(bloques):
    agrupados = defaultdict(list)
    for b in bloques:
        agrupados[b.dia_semana].append(b)
    for dia in agrupados:
        agrupados[dia].sort(key=lambda b: (b.hora_inicio, b.hora_fin))
    return agrupados


def bloques_solapados(bloques):
    """Pares de bloques del mismo día cuyos rangos horarios se superponen."""
    pares = []
    for i, b1 in enumerate(bloques):
        for b2 in bloques[i + 1:]:
            if (b1.dia_semana == b2.dia_semana
                    and b1.hora_inicio < b2.hora_fin
                    and b1.hora_fin > b2.hora_inicio):
                pares.append((b1, b2))
    return pares


def pares_consecutivos(bloques):
    """Pares de bloques de clase contiguos (sin recreo ni hueco en el medio)."""
    pares = []
    for dia, del_dia in bloques_por_dia(bloques).items():
        for b1, b2 in zip(del_dia, del_dia[1:]):
            if b1.hora_fin == b2.hora_inicio:
                pares.append((b1, b2))
    return pares


def profesor_disponible(profesor, bloque):
    """Aplica la semántica del esquema para disponibilidad/no disponibilidad."""
    filas = [d for d in profesor.disponibilidad if d.dia_semana == bloque.dia_semana]
    if not filas:
        return True

    disponibles = [f for f in filas if f.tipo == 'disponible']
    if disponibles:
        dentro = any(
            f.hora_desde <= bloque.hora_inicio and f.hora_hasta >= bloque.hora_fin
            for f in disponibles
        )
        if not dentro:
            return False

    for f in filas:
        if f.tipo != 'no_disponible':
            continue
        if bloque.hora_inicio < f.hora_hasta and bloque.hora_fin > f.hora_desde:
            return False
    return True


def aulas_elegibles(seccion_materia, seccion, aulas):
    """Aulas activas que puede usar una materia de una sección."""
    if seccion_materia.aula_requerida_id:
        return [a for a in aulas
                if a.activa and a.id == seccion_materia.aula_requerida_id]

    tipo = seccion_materia.materia.tipo_aula_requerida
    if tipo:
        return [a for a in aulas if a.activa and a.tipo == tipo]

    return [a for a in aulas if a.activa and a.tipo == 'regular']


def reglas_que_aplican(reglas, seccion_materia, seccion, profesor):
    """Reglas activas que alcanzan a esta materia/sección/profesor."""
    aplicables = []
    for regla in reglas:
        if not regla.activa:
            continue
        if regla.materia_id and regla.materia_id != seccion_materia.materia_id:
            continue
        if regla.nivel_id and regla.nivel_id != seccion.grado.nivel_id:
            continue
        if regla.profesor_id and regla.profesor_id != profesor.id:
            continue
        aplicables.append(regla)
    return aplicables


def primer_receso(plantilla):
    recesos = sorted(
        (b for b in plantilla.bloques if b.tipo == 'receso'),
        key=lambda b: b.hora_inicio,
    )
    return recesos[0].hora_inicio if recesos else None


def ultimo_bloque_por_dia(bloques):
    resultado = {}
    for dia, del_dia in bloques_por_dia(bloques).items():
        resultado[dia] = max(del_dia, key=lambda b: b.hora_fin)
    return resultado
