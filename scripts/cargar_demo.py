"""Reinicia los datos académicos y carga una demo completa.

- BORRA todos los datos académicos (colegios, años, niveles, grados, secciones,
  profesores, materias, aulas, reglas y horarios).
- NO borra usuarios ni roles: el login sigue funcionando.
- Carga un colegio demo con Tercer Ciclo y Nivel Medio, incluyendo BATAN.
- Genera y publica un horario para Mañana y otro para Tarde.

Uso:
    python scripts/cargar_demo.py
    python scripts/cargar_demo.py --force
    python scripts/cargar_demo.py --force --sin-horarios

Solo para desarrollo/demostración. Hacé backup antes de usarlo en una base real.
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
    AnioLectivo, AreaConocimiento, Aula, Bloque, Colegio, Grado, GradoMateria,
    GradoMateriaArea, HorarioCelda, HorarioVersion, Materia, Nivel,
    PlanEstudio, PlantillaHorario, Profesor, ProfesorDisponibilidad,
    ProfesorMateria, Regla, Seccion, SeccionMateria, Turno, Usuario,
)
from app.services.scheduler.engine import generar_horario
from app.utils.helpers import DIAS_SEMANA

COLEGIO_DEMO = 'Colegio Demo'

# ---------------------------------------------------------------------
# Catálogos
# ---------------------------------------------------------------------
MATERIAS = [
    ('Matemática', None),
    ('Lengua y Literatura', None),
    ('Ciencias Naturales', None),
    ('Ciencias Sociales', None),
    ('Inglés', None),
    ('Educación Física', 'gimnasio'),
    ('Informática', 'informatica'),
    ('Contabilidad', None),
    ('Administración', None),
    ('Orientación', None),
]

AULAS = [
    ('Aula 1', 'regular', 35),
    ('Aula 2', 'regular', 35),
    ('Aula 3', 'regular', 35),
    ('Aula 4', 'regular', 30),
    ('Laboratorio 1', 'laboratorio', 30),
    ('Sala Informática', 'informatica', 30),
    ('Gimnasio', 'gimnasio', 80),
]

PLAN_TERCER_CICLO = [
    ('Matemática', 5),
    ('Lengua y Literatura', 5),
    ('Ciencias Naturales', 4),
    ('Ciencias Sociales', 4),
    ('Inglés', 3),
    ('Educación Física', 2),
    ('Informática', 2),
]

PLAN_INFO = [
    ('Matemática', 5),
    ('Lengua y Literatura', 4),
    ('Ciencias Naturales', 4),
    ('Ciencias Sociales', 3),
    ('Inglés', 3),
    ('Educación Física', 2),
    ('Informática', 5),
    ('Orientación', 1),
]

PLAN_CONTA = [
    ('Matemática', 5),
    ('Lengua y Literatura', 4),
    ('Ciencias Sociales', 4),
    ('Inglés', 3),
    ('Educación Física', 2),
    ('Contabilidad', 5),
    ('Administración', 4),
]

AREAS_POR_MATERIA = {
    'Matemática': ['Matemática y sus Tecnologías'],
    'Lengua y Literatura': ['Lengua y Literatura'],
    'Ciencias Naturales': ['Ciencias Básicas'],
    'Ciencias Sociales': ['Ciencias Sociales'],
    'Inglés': ['Lengua y Literatura', 'S.I.L.'],
    'Educación Física': ['Educación Física'],
    'Informática': ['Técnicas y Tecnológicas', 'S.I.L.'],
    'Contabilidad': ['Técnicas y Tecnológicas'],
    'Administración': ['Técnicas y Tecnológicas'],
    'Orientación': ['Desarrollo Personal y Social'],
}

# (nombre, documento, materias, max semanal, max diario, turno de disponibilidad)
PROFESORES = [
    # Tercer Ciclo · Mañana
    ('Cynthia Rojas', '4002001', ['Matemática'], 25, 6, 'Mañana'),
    ('Rossana Villalba', '4002002', ['Lengua y Literatura'], 25, 6, 'Mañana'),
    ('Soledad Insfrán', '4002003', ['Ciencias Naturales'], 25, 6, 'Mañana'),
    ('Alejandra Benítez', '4002004', ['Ciencias Sociales'], 25, 6, 'Mañana'),
    ('Fernando Acosta', '4002005', ['Inglés'], 25, 6, 'Mañana'),
    ('José Giménez', '4002006', ['Educación Física'], 25, 6, 'Mañana'),
    ('Marcos Duarte', '4002007', ['Informática'], 25, 6, 'Mañana'),

    # Nivel Medio · Tarde
    ('Diego Ramírez', '4002011', ['Matemática'], 30, 7, 'Tarde'),
    ('Laura Gómez', '4002012', ['Lengua y Literatura'], 30, 7, 'Tarde'),
    ('Patricia Cáceres', '4002013', ['Ciencias Naturales'], 30, 7, 'Tarde'),
    ('Nora Aquino', '4002014', ['Ciencias Sociales'], 30, 7, 'Tarde'),
    ('Alma Benítez', '4002015', ['Inglés'], 30, 7, 'Tarde'),
    ('Freddy López', '4002016', ['Educación Física'], 30, 7, 'Tarde'),
    ('Emilio Rojas', '4002017', ['Informática'], 30, 7, 'Tarde'),
    ('Lourdes Cáceres', '4002018', ['Contabilidad'], 30, 7, 'Tarde'),
    ('Mabel Villalba', '4002019', ['Administración'], 30, 7, 'Tarde'),
    ('Priscila Ayala', '4002020', ['Orientación'], 30, 7, 'Tarde'),
]

BLOQUES_MANANA = [
    ('receso', '07:45', '08:00'),
    ('clase', '08:00', '08:40'),
    ('clase', '08:40', '09:20'),
    ('clase', '09:20', '10:00'),
    ('receso', '10:00', '10:20'),
    ('clase', '10:20', '11:00'),
    ('clase', '11:00', '11:40'),
    ('receso', '11:40', '11:50'),
    ('clase', '11:50', '12:30'),
    ('clase', '12:30', '13:10'),
]

BLOQUES_TARDE = [
    ('clase', '13:00', '13:40'),
    ('clase', '13:40', '14:20'),
    ('clase', '14:20', '15:00'),
    ('receso', '15:00', '15:20'),
    ('clase', '15:20', '16:00'),
    ('clase', '16:00', '16:40'),
    ('clase', '16:40', '17:20'),
]


def _hhmm(texto):
    return time.fromisoformat(texto)


def limpiar_datos():
    """Borra datos académicos sin tocar usuarios, roles ni colegios."""
    # Los usuarios pueden apuntar a un profesor: se desvinculan antes de borrar.
    db.session.execute(Usuario.__table__.update().values(profesor_id=None))

    orden = [
        HorarioCelda, HorarioVersion,
        SeccionMateria, Seccion,
        GradoMateriaArea, GradoMateria, Grado,
        PlanEstudio, AreaConocimiento,
        Regla,
        ProfesorDisponibilidad, ProfesorMateria,
        Bloque, PlantillaHorario,
        Profesor,
        Aula,
        Materia,
        Nivel,
        Turno,
        AnioLectivo,
    ]
    for modelo in orden:
        db.session.execute(delete(modelo))

    db.session.commit()


def crear_colegio(usuario, colegio_id=None):
    """Devuelve el colegio donde cargar la demo, sin borrar usuarios."""
    colegio = db.session.get(Colegio, colegio_id) if colegio_id else None
    if colegio is None and usuario and usuario.colegio:
        colegio = usuario.colegio
    if colegio is None:
        colegio = Colegio.query.order_by(Colegio.id).first()
    if colegio is None:
        colegio = Colegio(nombre=COLEGIO_DEMO)
        db.session.add(colegio)
        db.session.flush()

    if not colegio.minutos_hora_catedra:
        colegio.minutos_hora_catedra = 40
        db.session.flush()
    return colegio


def crear_estructura(colegio):
    anio = AnioLectivo(
        colegio_id=colegio.id,
        nombre='2026',
        fecha_inicio=date(2026, 2, 1),
        fecha_fin=date(2026, 11, 30),
        activo=True,
    )
    db.session.add(anio)
    db.session.flush()

    nivel_tercero = Nivel(colegio_id=colegio.id, nombre='Tercer Ciclo')
    nivel_medio = Nivel(colegio_id=colegio.id, nombre='Nivel Medio')
    db.session.add_all([nivel_tercero, nivel_medio])
    db.session.flush()

    planes = {}
    for nivel, nombre, orden in [
        (nivel_tercero, 'E.E.B. 7°-9°', 1),
        (nivel_medio, 'BATIN', 1),
        (nivel_medio, 'BATAN', 2),
    ]:
        plan = PlanEstudio(
            colegio_id=colegio.id,
            nivel_id=nivel.id,
            nombre=nombre,
            orden=orden,
            activo=True,
        )
        db.session.add(plan)
        planes[nombre] = plan
    db.session.flush()

    grados = {}
    for orden, nombre in enumerate(['7°', '8°', '9°'], start=1):
        grado = Grado(nivel_id=nivel_tercero.id,
                      plan_id=planes['E.E.B. 7°-9°'].id,
                      nombre=nombre, orden=orden)
        db.session.add(grado)
        grados[nombre] = grado
    for orden, (nombre, plan_nombre) in enumerate([
            ('1° BATIN Informática', 'BATIN'),
            ('2° BATIN Informática', 'BATIN'),
            ('1° BATAN Contabilidad', 'BATAN')], start=1):
        grado = Grado(nivel_id=nivel_medio.id,
                      plan_id=planes[plan_nombre].id,
                      nombre=nombre, orden=orden)
        db.session.add(grado)
        grados[nombre] = grado
    db.session.flush()

    turnos = {}
    for nombre in ['Mañana', 'Tarde']:
        turno = Turno(colegio_id=colegio.id, nombre=nombre)
        db.session.add(turno)
        turnos[nombre] = turno
    db.session.flush()

    aulas = {}
    for nombre, tipo, capacidad in AULAS:
        aula = Aula(colegio_id=colegio.id, nombre=nombre, tipo=tipo,
                    capacidad=capacidad, activa=True)
        db.session.add(aula)
        aulas[nombre] = aula
    db.session.flush()

    materias = {}
    for nombre, tipo in MATERIAS:
        materia = Materia(colegio_id=colegio.id, nombre=nombre,
                          tipo_aula_requerida=tipo)
        db.session.add(materia)
        materias[nombre] = materia
    db.session.flush()

    areas = {}
    for orden, nombre in enumerate([
        'Lengua y Literatura',
        'Ciencias Básicas',
        'Matemática y sus Tecnologías',
        'Ciencias Sociales',
        'Educación Física',
        'Desarrollo Personal y Social',
        'Técnicas y Tecnológicas',
        'S.I.L.',
        'Plan Optativo',
    ], start=1):
        area = AreaConocimiento(
            colegio_id=colegio.id, nombre=nombre, orden=orden, activa=True)
        db.session.add(area)
        areas[nombre] = area
    db.session.flush()

    return anio, grados, turnos, aulas, materias, planes, areas


def crear_plantillas(colegio, turnos):
    plantillas = {}

    for nombre, turno_nombre, bloques in [
        ('Mañana Tercer Ciclo', 'Mañana', BLOQUES_MANANA),
        ('Tarde Nivel Medio', 'Tarde', BLOQUES_TARDE),
    ]:
        plantilla = PlantillaHorario(
            colegio_id=colegio.id,
            turno_id=turnos[turno_nombre].id,
            nombre=nombre,
        )
        db.session.add(plantilla)
        db.session.flush()
        for dia in range(1, 6):
            for numero, (tipo, desde, hasta) in enumerate(bloques, start=1):
                db.session.add(Bloque(
                    plantilla_id=plantilla.id,
                    dia_semana=dia,
                    numero=numero,
                    hora_inicio=_hhmm(desde),
                    hora_fin=_hhmm(hasta),
                    tipo=tipo,
                ))
        plantillas[nombre] = plantilla
    db.session.flush()
    return plantillas


def crear_profesores(colegio, materias):
    profesores = {}
    for nombre, documento, nombres_materias, max_sem, max_dia, turno in PROFESORES:
        profe = Profesor(
            colegio_id=colegio.id,
            nombre=nombre,
            documento=documento,
            contacto='0981 000 000',
            horas_min_semana=5,
            horas_max_semana=max_sem,
            horas_max_dia=max_dia,
            activo=True,
        )
        profe.materias = [materias[m] for m in nombres_materias]
        db.session.add(profe)
        db.session.flush()

        if turno == 'Mañana':
            desde, hasta = time(7, 30), time(13, 30)
        else:
            desde, hasta = time(12, 30), time(18, 0)

        for dia in range(1, 6):
            db.session.add(ProfesorDisponibilidad(
                profesor_id=profe.id,
                dia_semana=dia,
                hora_desde=desde,
                hora_hasta=hasta,
                tipo='disponible',
            ))
        profesores[nombre] = profe
    db.session.flush()
    return profesores


def crear_planes(grados, materias, areas):
    planes = {
        '7°': PLAN_TERCER_CICLO,
        '8°': PLAN_TERCER_CICLO,
        '9°': PLAN_TERCER_CICLO,
        '1° BATIN Informática': PLAN_INFO,
        '2° BATIN Informática': PLAN_INFO,
        '1° BATAN Contabilidad': PLAN_CONTA,
    }
    for grado_nombre, plan in planes.items():
        grado = grados[grado_nombre]
        for materia_nombre, horas in plan:
            materia = materias[materia_nombre]
            tipo = 'especifico' if materia_nombre in (
                'Informática', 'Contabilidad', 'Administración') else 'comun'
            gm = GradoMateria(
                grado_id=grado.id,
                materia_id=materia.id,
                horas_semanales=horas,
                max_bloques_por_dia=1,
                requiere_bloque_doble=False,
                tipo_plan=tipo,
            )
            db.session.add(gm)
            db.session.flush()

            for area_nombre in AREAS_POR_MATERIA.get(materia_nombre, []):
                db.session.add(GradoMateriaArea(
                    grado_id=grado.id,
                    materia_id=materia.id,
                    area_id=areas[area_nombre].id,
                ))
    db.session.flush()


def crear_secciones(anio, grados, turnos, aulas, plantillas):
    datos = [
        ('7°', 'A', 'Mañana', 'Mañana Tercer Ciclo', 'Aula 1'),
        ('8°', 'A', 'Mañana', 'Mañana Tercer Ciclo', 'Aula 2'),
        ('9°', 'A', 'Mañana', 'Mañana Tercer Ciclo', 'Aula 3'),
        ('1° BATIN Informática', 'A', 'Tarde', 'Tarde Nivel Medio', 'Aula 1'),
        ('1° BATIN Informática', 'B', 'Tarde', 'Tarde Nivel Medio', 'Aula 2'),
        ('2° BATIN Informática', 'A', 'Tarde', 'Tarde Nivel Medio', 'Aula 3'),
        ('1° BATAN Contabilidad', 'A', 'Tarde', 'Tarde Nivel Medio', 'Aula 4'),
    ]

    for grado_nombre, nombre, turno_nombre, plantilla_nombre, aula_nombre in datos:
        grado = grados[grado_nombre]
        seccion = Seccion(
            anio_lectivo_id=anio.id,
            grado_id=grado.id,
            turno_id=turnos[turno_nombre].id,
            nombre=nombre,
            aula_base_id=aulas[aula_nombre].id,
            plantilla_id=plantillas[plantilla_nombre].id,
        )
        db.session.add(seccion)
        db.session.flush()

        for gm in grado.grado_materias:
            db.session.add(SeccionMateria(
                seccion_id=seccion.id,
                materia_id=gm.materia_id,
                horas_semanales=gm.horas_semanales,
                max_bloques_por_dia=gm.max_bloques_por_dia,
                requiere_bloque_doble=gm.requiere_bloque_doble,
            ))
    db.session.commit()


def crear_reglas(colegio, materias):
    reglas = [
        ('ANTES_DE_RECESO', 'Educación Física antes del receso', False, 50,
         materias['Educación Física'], {}),
        ('NO_ULTIMA_HORA', 'Matemática no en la última hora', False, 40,
         materias['Matemática'], {}),
        ('DISTRIBUIR_SEMANA', 'Repartir las horas en la semana', True, 10,
         None, {'max_por_dia': 1}),
        ('EVITAR_HUECOS_PROFESOR', 'Evitar huecos de los profesores', False, 30,
         None, {'max_huecos': 1}),
    ]
    for codigo, descripcion, obligatoria, peso, materia, parametros in reglas:
        db.session.add(Regla(
            colegio_id=colegio.id,
            codigo=codigo,
            descripcion=descripcion,
            obligatoria=obligatoria,
            peso=peso,
            activa=True,
            materia_id=materia.id if materia else None,
            parametros=parametros,
        ))
    db.session.commit()


def generar_horarios(colegio, anio):
    profesores = Profesor.query.filter_by(colegio_id=colegio.id, activo=True).all()
    aulas = Aula.query.filter_by(colegio_id=colegio.id, activa=True).all()
    reglas = Regla.query.filter_by(colegio_id=colegio.id, activa=True).all()

    for turno in Turno.query.filter_by(colegio_id=colegio.id).order_by(Turno.nombre).all():
        secciones = Seccion.query.filter_by(
            anio_lectivo_id=anio.id, turno_id=turno.id
        ).all()
        if not secciones:
            continue

        print(f'Generando horario de {turno.nombre}...')
        resultado = generar_horario(secciones, profesores, aulas, reglas,
                                    limite_segundos=60)
        if not resultado.ok:
            print(f'  ⚠ No se pudo generar: {resultado.mensaje}')
            for linea in resultado.detalle:
                print(f'    - {linea}')
            continue

        version = HorarioVersion(
            anio_lectivo_id=anio.id,
            turno_id=turno.id,
            nombre=f'Demo {turno.nombre}',
            estado='publicado',
            notas=f'Generada automáticamente con {len(resultado.asignaciones)} bloques.',
        )
        db.session.add(version)
        db.session.flush()
        for a in resultado.asignaciones:
            db.session.add(HorarioCelda(
                version_id=version.id,
                seccion_materia_id=a.seccion_materia_id,
                bloque_id=a.bloque_id,
                aula_id=a.aula_id,
                profesor_id=a.profesor_id,
                fijado=False,
                origen='auto',
            ))
        db.session.commit()
        print(f'  ✓ {version.nombre}: {len(resultado.asignaciones)} bloques, {resultado.estadisticas.get("segundos")} s')


def main():
    parser = argparse.ArgumentParser(description='Carga una demo completa de Chronos.')
    parser.add_argument('--force', action='store_true', help='No pedir confirmación')
    parser.add_argument('--sin-horarios', action='store_true',
                        help='No generar horarios automáticamente')
    args = parser.parse_args()

    if not args.force:
        print('⚠ Esto BORRA todos los datos académicos (no los usuarios).')
        if input('Escribí SI para continuar: ').strip().upper() != 'SI':
            print('Cancelado.')
            return

    app = create_app()
    with app.app_context():
        usuario = Usuario.query.order_by(Usuario.id).first()
        colegio = crear_colegio(usuario, app.config.get('COLEGIO_ID') or None)

        print(f'Limpiando datos académicos de {colegio.nombre}...')
        limpiar_datos()

        anio, grados, turnos, aulas, materias, planes, areas = crear_estructura(colegio)
        plantillas = crear_plantillas(colegio, turnos)
        profesores = crear_profesores(colegio, materias)
        crear_planes(grados, materias, areas)
        crear_secciones(anio, grados, turnos, aulas, plantillas)
        crear_reglas(colegio, materias)

        if not args.sin_horarios:
            generar_horarios(colegio, anio)

        total_usuarios = Usuario.query.count()
        print()
        print('Demo cargada en:', colegio.nombre)
        print('  Año:', anio.nombre)
        print('  Niveles:', Nivel.query.filter_by(colegio_id=colegio.id).count())
        print('  Grados:', Grado.query.count())
        print('  Secciones:', Seccion.query.count())
        print('  Profesores:', Profesor.query.count())
        print('  Materias:', Materia.query.count())
        print('  Aulas:', Aula.query.count())
        print('  Planes:', PlanEstudio.query.filter_by(colegio_id=colegio.id).count())
        print('  Áreas:', AreaConocimiento.query.filter_by(colegio_id=colegio.id).count())
        print('  Usuarios preservados:', total_usuarios)
        print('  Login: los usuarios existentes siguen funcionando.')


if __name__ == '__main__':
    main()
