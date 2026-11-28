"""Carga los datos básicos de un colegio nuevo (estructura mínima).

Reemplaza el borrado total de ``cargar_demo.py`` por una carga mínima,
idempotente y repetible: si los datos ya existen, no los duplica.

Carga:
    - Año lectivo 2026 (activo)
    - Niveles: E.E.B. y Educación Media
    - Especialidades de Educación Media: BATIN y BATAN
    - Cursos: 7° (E.E.B.) y 1° (Educación Media)

NO carga materias, planes, profesores, turnos, aulas, secciones ni horarios.

Uso:
    python scripts/cargar_basico.py
    python scripts/cargar_basico.py --force   # borra lo académico primero

Los datos se agregan por partes a medida que se definan.
"""
import argparse
import sys
from datetime import date, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import delete

from app.extensions import db
from app.factory import create_app
from app.models import (
    AnioLectivo, Bloque, Colegio, Especialidad, Grado, HorarioCelda,
    HorarioVersion, Materia, MateriaEspecialidad, Nivel, PlanEstudio,
    PlanGrado, PlanMateria, PlantillaHorario, Profesor, ProfesorDisponibilidad,
    ProfesorEspecialidad, ProfesorMateria, Regla, Seccion, SeccionMateria,
    Turno, Usuario, Aula, AreaConocimiento,
)

# ---------------------------------------------------------------------
# Datos básicos
# ---------------------------------------------------------------------
ANIO = {
    'nombre': '2026',
    'fecha_inicio': date(2026, 2, 1),
    'fecha_fin': date(2026, 11, 30),
    'activo': True,
}

NIVELES = ['E.E.B.', 'Educación Media']

# (nombre, codigo, nivel)
ESPECIALIDADES = [
    ('BATIN', 'BATIN', 'Educación Media'),
    ('BATAN', 'BATAN', 'Educación Media'),
]

# Turnos: franjas generales de funcionamiento.
TURNOS = [
    'Jornada completa',
]

# (curso, nivel)
CURSOS = [
    ('7°', 'E.E.B.'),
    ('1°', 'Educación Media'),
]

# Plan de Educación Media: materias y horas por curso.
PLANES = [
    {
        'nombre': 'Plan Educación Media',
        'nivel': 'Educación Media',
        'especialidad': None,
        'cursos': ['1°'],
        'materias': [
            ('Lengua y Literatura', 4),
            ('Matemática', 5),
            ('Informática', 4),
        ],
    },
]

# Estructura de horario: bloques de clase y recesos de cada día.
# (tipo, desde, hasta)
ESTRUCTURA = {
    'nombre': 'Jornada completa',
    'turno': 'Jornada completa',
    'bloques': [
        ('clase', '07:30', '08:10'),
        ('clase', '08:10', '08:50'),
        ('clase', '08:50', '09:30'),
        ('receso', '09:30', '09:50'),
        ('clase', '09:50', '10:30'),
        ('clase', '10:30', '11:10'),
        ('clase', '11:10', '11:50'),
        ('receso', '11:50', '13:00'),
        ('clase', '13:00', '13:40'),
        ('clase', '13:40', '14:20'),
        ('clase', '14:20', '15:00'),
    ],
    'dias': [1, 2, 3, 4, 5],
}

# Áreas de conocimiento: agrupan materias por campo del saber.
AREAS = [
    'Lengua y Literatura',
    'Matemática y sus Tecnologías',
    'Ciencias Básicas',
    'Ciencias Sociales',
    'Técnicas y Tecnológicas',
]

# (materia, área, nivel, horas semanales por defecto)
MATERIAS = [
    ('Lengua y Literatura', 'Lengua y Literatura', 'E.E.B.', 6),
    ('Matemática', 'Matemática y sus Tecnologías', 'E.E.B.', 6),
    ('Ciencias Naturales', 'Ciencias Básicas', 'E.E.B.', 5),
    ('Ciencias Sociales', 'Ciencias Sociales', 'E.E.B.', 4),

    ('Lengua y Literatura', 'Lengua y Literatura', 'Educación Media', 4),
    ('Matemática', 'Matemática y sus Tecnologías', 'Educación Media', 5),
    ('Informática', 'Técnicas y Tecnológicas', 'Educación Media', 4),
]


def limpiar_datos():
    """Borra los datos académicos sin tocar usuarios, roles ni colegios."""
    db.session.execute(Usuario.__table__.update().values(profesor_id=None))
    orden = [
        HorarioCelda, HorarioVersion,
        SeccionMateria, Seccion,
        PlanMateria, PlanGrado,
        Grado, PlanEstudio, Especialidad,
        Regla,
        ProfesorEspecialidad, ProfesorDisponibilidad, ProfesorMateria,
        Bloque, PlantillaHorario, Profesor, Aula,
        MateriaEspecialidad, Materia, AreaConocimiento,
        Nivel, Turno, AnioLectivo,
    ]
    for modelo in orden:
        db.session.execute(delete(modelo))
    db.session.commit()


def obtener_colegio():
    """Colegio de la instancia (o el primero de la base)."""
    usuario = Usuario.query.order_by(Usuario.id).first()
    colegio = usuario.colegio if usuario and usuario.colegio else None
    if colegio is None:
        colegio = Colegio.query.order_by(Colegio.id).first()
    if colegio is None:
        colegio = Colegio(nombre='Colegio Demo')
        db.session.add(colegio)
        db.session.flush()
    return colegio


def crear_anio(colegio):
    anio = AnioLectivo.query.filter_by(
        colegio_id=colegio.id, nombre=ANIO['nombre']).first()
    if anio is None:
        anio = AnioLectivo(
            colegio_id=colegio.id,
            nombre=ANIO['nombre'],
            fecha_inicio=ANIO['fecha_inicio'],
            fecha_fin=ANIO['fecha_fin'],
            activo=False,
        )
        db.session.add(anio)
        db.session.flush()
        print(f"  + Año {anio.nombre}")
    else:
        print(f"  · Año {anio.nombre} ya existe")

    if ANIO['activo'] and not anio.activo:
        AnioLectivo.query.filter_by(colegio_id=colegio.id).update(
            {'activo': False}, synchronize_session=False)
        anio.activo = True
        print("    (activado)")
    db.session.flush()
    return anio


def crear_niveles(colegio):
    niveles = {}
    for nombre in NIVELES:
        nivel = Nivel.query.filter_by(colegio_id=colegio.id, nombre=nombre).first()
        if nivel is None:
            nivel = Nivel(colegio_id=colegio.id, nombre=nombre)
            db.session.add(nivel)
            db.session.flush()
            print(f"  + Nivel {nombre}")
        else:
            print(f"  · Nivel {nombre} ya existe")
        niveles[nombre] = nivel
    return niveles


def crear_especialidades(colegio, niveles):
    especialidades = {}
    for nombre, codigo, nivel_nombre in ESPECIALIDADES:
        nivel = niveles[nivel_nombre]
        esp = Especialidad.query.filter_by(
            colegio_id=colegio.id, nombre=nombre).first()
        if esp is None:
            esp = Especialidad(
                colegio_id=colegio.id, nivel_id=nivel.id,
                nombre=nombre, codigo=codigo, activa=True,
            )
            db.session.add(esp)
            db.session.flush()
            print(f"  + Especialidad {nombre} ({nivel_nombre})")
        else:
            print(f"  · Especialidad {nombre} ya existe")
        especialidades[nombre] = esp
    return especialidades


def crear_turnos(colegio):
    turnos = {}
    for nombre in TURNOS:
        turno = Turno.query.filter_by(
            colegio_id=colegio.id, nombre=nombre).first()
        if turno is None:
            turno = Turno(colegio_id=colegio.id, nombre=nombre)
            db.session.add(turno)
            db.session.flush()
            print(f"  + Turno {nombre}")
        else:
            print(f"  · Turno {nombre} ya existe")
        turnos[nombre] = turno
    return turnos


def crear_cursos(colegio, niveles):
    grados = {}
    for nombre, nivel_nombre in CURSOS:
        nivel = niveles[nivel_nombre]
        grado = Grado.query.filter_by(nivel_id=nivel.id, nombre=nombre).first()
        if grado is None:
            grado = Grado(nivel_id=nivel.id, nombre=nombre)
            db.session.add(grado)
            db.session.flush()
            print(f"  + Curso {nombre} ({nivel_nombre})")
        else:
            print(f"  · Curso {nombre} ({nivel_nombre}) ya existe")
        grados[nombre] = grado
    return grados


def crear_areas(colegio):
    areas = {}
    for nombre in AREAS:
        area = AreaConocimiento.query.filter_by(
            colegio_id=colegio.id, nombre=nombre).first()
        if area is None:
            area = AreaConocimiento(colegio_id=colegio.id, nombre=nombre,
                                    activa=True)
            db.session.add(area)
            db.session.flush()
            print(f"  + Área {nombre}")
        else:
            print(f"  · Área {nombre} ya existe")
        areas[nombre] = area
    return areas


def crear_materias(colegio, areas, niveles):
    materias = {}
    for nombre, area_nombre, nivel_nombre, horas in MATERIAS:
        area = areas[area_nombre]
        nivel = niveles[nivel_nombre]
        materia = Materia.query.filter_by(
            colegio_id=colegio.id, nivel_id=nivel.id,
            nombre=nombre, area_id=area.id).first()
        if materia is None:
            materia = Materia(
                colegio_id=colegio.id, nivel_id=nivel.id,
                area_id=area.id, nombre=nombre, horas_semanales=horas,
            )
            db.session.add(materia)
            db.session.flush()
            print(f"  + Materia {nombre} ({nivel_nombre} · {area_nombre})")
        else:
            print(f"  · Materia {nombre} ({nivel_nombre}) ya existe")
        materias[(nombre, nivel_nombre)] = materia
    return materias


def crear_planes(colegio, niveles, materias):
    planes = {}
    for datos in PLANES:
        nivel = niveles[datos['nivel']]
        plan = PlanEstudio.query.filter_by(
            colegio_id=colegio.id, nivel_id=nivel.id, nombre=datos['nombre']).first()
        if plan is None:
            plan = PlanEstudio(
                colegio_id=colegio.id, nivel_id=nivel.id,
                nombre=datos['nombre'], activo=True,
            )
            db.session.add(plan)
            db.session.flush()
            print(f"  + Plan {plan.nombre} ({nivel.nombre})")
        else:
            print(f"  · Plan {plan.nombre} ya existe")

        for curso in datos['cursos']:
            grado = Grado.query.filter_by(nivel_id=nivel.id, nombre=curso).first()
            if grado is None:
                continue
            if not PlanGrado.query.filter_by(
                    plan_id=plan.id, grado_id=grado.id).first():
                db.session.add(PlanGrado(plan_id=plan.id, grado_id=grado.id))
                print(f"    · curso {curso}")

            for materia_nombre, horas in datos['materias']:
                materia = materias.get((materia_nombre, nivel.nombre))
                if materia is None:
                    continue
                if not PlanMateria.query.filter_by(
                        plan_id=plan.id, grado_id=grado.id,
                        materia_id=materia.id).first():
                    db.session.add(PlanMateria(
                        plan_id=plan.id, grado_id=grado.id,
                        materia_id=materia.id, horas_semanales=horas,
                        max_bloques_por_dia=1, requiere_bloque_doble=False,
                        tipo_plan='comun',
                    ))
                    print(f"    · {materia_nombre} {horas} h")
        db.session.flush()
        planes[plan.nombre] = plan
    return planes


def crear_estructura_horario(colegio, turnos):
    turno = turnos[ESTRUCTURA['turno']]
    plantilla = PlantillaHorario.query.filter_by(
        colegio_id=colegio.id, nombre=ESTRUCTURA['nombre']).first()
    if plantilla is None:
        plantilla = PlantillaHorario(
            colegio_id=colegio.id, turno_id=turno.id,
            nombre=ESTRUCTURA['nombre'],
        )
        db.session.add(plantilla)
        db.session.flush()
        print(f"  + Estructura {plantilla.nombre} ({turno.nombre})")
    else:
        print(f"  · Estructura {plantilla.nombre} ya existe")

    if not plantilla.bloques:
        for dia in ESTRUCTURA['dias']:
            for numero, (tipo, desde, hasta) in enumerate(ESTRUCTURA['bloques'], start=1):
                plantilla.bloques.append(Bloque(
                    dia_semana=dia, numero=numero,
                    hora_inicio=time.fromisoformat(desde),
                    hora_fin=time.fromisoformat(hasta),
                    tipo=tipo,
                ))
        clases = sum(1 for b in ESTRUCTURA['bloques'] if b[0] == 'clase')
        recesos = sum(1 for b in ESTRUCTURA['bloques'] if b[0] == 'receso')
        print(f"    · {len(ESTRUCTURA['dias'])} días · {clases} clase(s) y "
              f"{recesos} receso(s) por día")
        db.session.flush()
    return plantilla


def resumen(colegio):
    print()
    print('Datos básicos cargados en:', colegio.nombre)
    print('  Años:', AnioLectivo.query.filter_by(colegio_id=colegio.id).count())
    print('  Niveles:', [n.nombre for n in
                          Nivel.query.filter_by(colegio_id=colegio.id).all()])
    print('  Especialidades:', [e.nombre for e in
                                Especialidad.query.filter_by(
                                    colegio_id=colegio.id).all()])
    print('  Cursos:', [f'{g.nombre} ({g.nivel.nombre})' for g in
                        Grado.query.all()])
    print('  Turnos:', [t.nombre for t in
                        Turno.query.filter_by(colegio_id=colegio.id).all()])
    print('  Áreas:', [a.nombre for a in
                       AreaConocimiento.query.filter_by(
                           colegio_id=colegio.id).all()])
    print('  Planes:', [p.nombre for p in
                       PlanEstudio.query.filter_by(colegio_id=colegio.id).all()])
    print('  Estructura de horario:', [f'{p.nombre} ({len(p.bloques)} bloques)'
                                       for p in PlantillaHorario.query.filter_by(
                                           colegio_id=colegio.id).all()])
    print('  Materias:', [f'{m.nombre} · {m.nivel.nombre}'
                          for m in Materia.query.filter_by(
                              colegio_id=colegio.id).all()])
    print()
    print('  Usuarios preservados:', Usuario.query.count())


def main():
    parser = argparse.ArgumentParser(
        description='Carga los datos básicos de un colegio.')
    parser.add_argument('--force', action='store_true',
                        help='Borra los datos académicos antes de cargar')
    args = parser.parse_args()

    if args.force:
        print('⚠ Se borrarán los datos académicos (no los usuarios).')
        if input('Escribí SI para continuar: ').strip().upper() != 'SI':
            print('Cancelado.')
            return

    app = create_app()
    with app.app_context():
        colegio = obtener_colegio()
        if args.force:
            print(f'Limpiando datos académicos de {colegio.nombre}...')
            limpiar_datos()

        print('Cargando datos básicos...')
        crear_anio(colegio)
        niveles = crear_niveles(colegio)
        crear_especialidades(colegio, niveles)
        crear_cursos(colegio, niveles)
        turnos = crear_turnos(colegio)
        areas = crear_areas(colegio)
        materias = crear_materias(colegio, areas, niveles)
        crear_planes(colegio, niveles, materias)
        crear_estructura_horario(colegio, turnos)
        db.session.commit()
        resumen(colegio)


if __name__ == '__main__':
    main()
