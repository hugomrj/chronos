"""Reinicia los datos académicos y carga una demo completa.

- BORRA todos los datos académicos (colegios, años, niveles, grados, secciones,
  profesores, materias, aulas, reglas y horarios).
- NO borra usuarios ni roles: el login sigue funcionando.
- Carga un colegio demo con E.E.B. y Nivel Medio, incluyendo BATAN.
- Genera y publica un horario de doble escolaridad para ambos ciclos.

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
    AnioLectivo, AreaConocimiento, Aula, Bloque, Colegio, Grado,
    Especialidad, HorarioCelda, HorarioVersion, Materia, MateriaEspecialidad,
    PlanGrado, PlanMateria, ProfesorEspecialidad, ProfesorHorasAnio,
    Nivel, PlanEstudio, PlantillaHorario, Profesor, ProfesorDisponibilidad,
    ProfesorMateria, Regla, Seccion, SeccionMateria, Turno, Usuario,
)
from app.services.scheduler.engine import generar_horario
from app.utils.helpers import DIAS_SEMANA

COLEGIO_DEMO = 'Colegio Demo'

# ---------------------------------------------------------------------
# Catálogos
# ---------------------------------------------------------------------
MATERIAS = [
    # (nombre, área, nivel, horas por defecto, tipo de aula)
    ('Matemática', 'Matemática y sus Tecnologías', 'E.E.B.', 6, None),
    ('Lengua y Literatura', 'Lengua y Literatura', 'E.E.B.', 6, None),
    ('Ciencias Naturales', 'Ciencias Básicas', 'E.E.B.', 5, None),
    ('Ciencias Sociales', 'Ciencias Sociales', 'E.E.B.', 5, None),
    ('Inglés', 'Lengua y Literatura', 'E.E.B.', 4, None),
    ('Educación Física', 'Educación Física', 'E.E.B.', 3, 'gimnasio'),
    ('Informática', 'Técnicas y Tecnológicas', 'E.E.B.', 4, 'informatica'),
    ('Orientación', 'Desarrollo Personal y Social', 'E.E.B.', 2, None),
    ('Expresión Artística', 'Expresión Artística', 'E.E.B.', 4, None),
    ('Formación Ética', 'Ciencias Sociales', 'E.E.B.', 3, None),
    ('Historia y Geografía', 'Ciencias Sociales', 'E.E.B.', 2, None),
    ('Guaraní', 'Lengua y Literatura', 'E.E.B.', 3, None),

    ('Matemática', 'Matemática y sus Tecnologías', 'Nivel Medio', 5, None),
    ('Lengua y Literatura', 'Lengua y Literatura', 'Nivel Medio', 4, None),
    ('Ciencias Naturales', 'Ciencias Básicas', 'Nivel Medio', 4, None),
    ('Ciencias Sociales', 'Ciencias Sociales', 'Nivel Medio', 4, None),
    ('Inglés', 'Lengua y Literatura', 'Nivel Medio', 3, None),
    ('Educación Física', 'Educación Física', 'Nivel Medio', 2, 'gimnasio'),
    ('Informática', 'Técnicas y Tecnológicas', 'Nivel Medio', 5, 'informatica'),
    ('Orientación', 'Desarrollo Personal y Social', 'Nivel Medio', 1, None),
    ('Contabilidad', 'Técnicas y Tecnológicas', 'Nivel Medio', 5, None),
    ('Administración', 'Técnicas y Tecnológicas', 'Nivel Medio', 4, None),
]

AULAS = [
    ('Aula 1', 'regular', 35),
    ('Aula 2', 'regular', 35),
    ('Aula 3', 'regular', 35),
    ('Aula 4', 'regular', 30),
    ('Aula 5', 'regular', 30),
    ('Aula 6', 'regular', 30),
    ('Aula 7', 'regular', 30),
    ('Laboratorio 1', 'laboratorio', 30),
    ('Sala Informática', 'informatica', 30),
    ('Gimnasio', 'gimnasio', 80),
]

PLAN_TERCER_CICLO = [
    ('Matemática', 6),
    ('Lengua y Literatura', 6),
    ('Ciencias Naturales', 5),
    ('Ciencias Sociales', 5),
    ('Inglés', 4),
    ('Educación Física', 3),
    ('Informática', 4),
    ('Orientación', 2),
    ('Expresión Artística', 4),
    ('Formación Ética', 3),
    ('Historia y Geografía', 2),
    ('Guaraní', 3),
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

PLAN_COMUN = [
    ('Matemática', 5),
    ('Lengua y Literatura', 4),
    ('Ciencias Naturales', 4),
    ('Ciencias Sociales', 4),
    ('Inglés', 3),
    ('Educación Física', 2),
    ('Orientación', 2),
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

# (nombre, documento, materias, max semanal, max diario, referencia)
PROFESORES = [
    # Tercer Ciclo
    ('Cynthia Rojas', '4002001', ['Matemática'], 25, 6, 'E.E.B.'),
    ('Rossana Villalba', '4002002', ['Lengua y Literatura'], 25, 6, 'E.E.B.'),
    ('Soledad Insfrán', '4002003', ['Ciencias Naturales'], 25, 6, 'E.E.B.'),
    ('Alejandra Benítez', '4002004', ['Ciencias Sociales', 'Formación Ética', 'Historia y Geografía'], 35, 6, 'E.E.B.'),
    ('Fernando Acosta', '4002005', ['Inglés'], 25, 6, 'E.E.B.'),
    ('José Giménez', '4002006', ['Educación Física'], 25, 6, 'E.E.B.'),
    ('Marcos Duarte', '4002007', ['Informática'], 25, 6, 'E.E.B.'),
    ('Marta Ayala', '4002008', ['Guaraní'], 25, 6, 'E.E.B.'),
    ('Rocío Benítez', '4002009', ['Orientación'], 25, 6, 'E.E.B.'),
    ('Hugo Villalba', '4002010', ['Expresión Artística'], 25, 6, 'E.E.B.'),

    # Nivel Medio
    ('Diego Ramírez', '4002011', ['Matemática'], 30, 7, 'Nivel Medio'),
    ('Laura Gómez', '4002012', ['Lengua y Literatura'], 30, 7, 'Nivel Medio'),
    ('Patricia Cáceres', '4002013', ['Ciencias Naturales'], 30, 7, 'Nivel Medio'),
    ('Nora Aquino', '4002014', ['Ciencias Sociales'], 30, 7, 'Nivel Medio'),
    ('Alma Benítez', '4002015', ['Inglés'], 30, 7, 'Nivel Medio'),
    ('Freddy López', '4002016', ['Educación Física'], 30, 7, 'Nivel Medio'),
    ('Emilio Rojas', '4002017', ['Informática'], 30, 7, 'Nivel Medio'),
    ('Lourdes Cáceres', '4002018', ['Contabilidad'], 30, 7, 'Nivel Medio'),
    ('Mabel Villalba', '4002019', ['Administración'], 30, 7, 'Nivel Medio'),
    ('Priscila Ayala', '4002020', ['Orientación'], 30, 7, 'Nivel Medio'),
]

BLOQUES_TERCER_CICLO = [
    ('clase', '08:00', '08:40'),
    ('clase', '08:40', '09:20'),
    ('receso', '09:20', '09:35'),
    ('clase', '09:35', '10:15'),
    ('clase', '10:15', '10:55'),
    ('receso', '10:55', '11:10'),
    ('clase', '11:10', '11:50'),
    ('clase', '11:50', '12:30'),
    ('receso', '12:30', '13:00'),
    ('clase', '13:00', '13:40'),
    ('clase', '13:40', '14:20'),
    ('receso', '14:20', '14:30'),
    ('clase', '14:30', '15:00'),
]

BLOQUES_NIVEL_MEDIO = [
    ('clase', '08:00', '08:40'),
    ('clase', '08:40', '09:20'),
    ('clase', '09:20', '10:00'),
    ('receso', '10:00', '10:20'),
    ('clase', '10:20', '11:00'),
    ('clase', '11:00', '11:40'),
    ('receso', '11:40', '11:50'),
    ('clase', '11:50', '12:30'),
    ('clase', '12:30', '13:10'),
    ('receso', '13:10', '13:50'),
    ('clase', '13:50', '14:25'),
    ('clase', '14:25', '15:00'),
    ('receso', '15:00', '15:10'),
    ('clase', '15:10', '15:45'),
    ('clase', '15:45', '16:20'),
    ('clase', '16:20', '17:00'),
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
        PlanMateria, PlanGrado,
        Grado,
        PlanEstudio,
        Especialidad,
        Regla,
        ProfesorEspecialidad, ProfesorDisponibilidad, ProfesorMateria,
        Bloque, PlantillaHorario,
        Profesor,
        Aula,
        MateriaEspecialidad,
        Materia,
        AreaConocimiento,
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

    anio_anterior = AnioLectivo(
        colegio_id=colegio.id,
        nombre='2025',
        fecha_inicio=date(2025, 2, 1),
        fecha_fin=date(2025, 11, 30),
        activo=False,
    )
    db.session.add(anio_anterior)
    db.session.flush()

    nivel_tercero = Nivel(colegio_id=colegio.id, nombre='E.E.B.')
    nivel_medio = Nivel(colegio_id=colegio.id, nombre='Nivel Medio')
    db.session.add_all([nivel_tercero, nivel_medio])
    db.session.flush()

    especialidades = {}
    for nombre, codigo in [('BATIN', 'BATIN'), ('BATAN', 'BATAN')]:
        esp = Especialidad(
            colegio_id=colegio.id, nivel_id=nivel_medio.id,
            nombre=nombre, codigo=codigo, activa=True,
        )
        db.session.add(esp)
        especialidades[nombre] = esp
    db.session.flush()

    planes = {}
    for nivel, nombre, orden, esp_nombre in [
        (nivel_tercero, 'E.E.B. 7°-9°', 1, None),
        (nivel_medio, 'Nivel Medio Común', 1, None),
        (nivel_medio, 'BATIN', 2, 'BATIN'),
        (nivel_medio, 'BATAN', 3, 'BATAN'),
    ]:
        plan = PlanEstudio(
            colegio_id=colegio.id,
            nivel_id=nivel.id,
            especialidad_id=(especialidades[esp_nombre].id if esp_nombre else None),
            nombre=nombre,
            orden=orden,
            activo=True,
        )
        db.session.add(plan)
        planes[nombre] = plan
    db.session.flush()

    grados = {}
    for orden, nombre in enumerate(['7°', '8°', '9°'], start=1):
        grado = Grado(nivel_id=nivel_tercero.id, nombre=nombre, orden=orden)
        db.session.add(grado)
        grados[nombre] = grado
    for orden, nombre in enumerate(['1°', '2°', '3°'], start=1):
        grado = Grado(nivel_id=nivel_medio.id, nombre=nombre, orden=orden)
        db.session.add(grado)
        grados[nombre] = grado
    db.session.flush()

    for plan_nombre, plan in planes.items():
        if plan_nombre == 'E.E.B. 7°-9°':
            cursos = ['7°', '8°', '9°']
        else:
            cursos = ['1°', '2°', '3°']
        for curso in cursos:
            db.session.add(PlanGrado(plan_id=plan.id, grado_id=grados[curso].id))
    db.session.flush()

    turnos = {}
    turno = Turno(colegio_id=colegio.id, nombre='Doble escolaridad')
    db.session.add(turno)
    turnos['Doble escolaridad'] = turno
    db.session.flush()

    aulas = {}
    for nombre, tipo, capacidad in AULAS:
        aula = Aula(colegio_id=colegio.id, nombre=nombre, tipo=tipo,
                    capacidad=capacidad, activa=True)
        db.session.add(aula)
        aulas[nombre] = aula
    db.session.flush()

    areas = {}
    for orden, nombre in enumerate([
        'Lengua y Literatura',
        'Expresión Artística',
        'Ciencias Básicas',
        'Matemática y sus Tecnologías',
        'Ciencias Sociales',
        'Educación Física',
        'Desarrollo Personal y Social',
        'Técnicas y Tecnológicas',
        'S.I.L.',
        'Plan Optativo',
    ], start=1):
        horas = {
            'Lengua y Literatura': 20,
            'Expresión Artística': 10,
            'Ciencias Básicas': 10,
            'Matemática y sus Tecnologías': 10,
            'Ciencias Sociales': 15,
            'Educación Física': 6,
            'Desarrollo Personal y Social': 5,
            'Técnicas y Tecnológicas': 15,
            'S.I.L.': 15,
            'Plan Optativo': 10,
        }.get(nombre)
        area = AreaConocimiento(
            colegio_id=colegio.id, nombre=nombre, orden=orden, activa=True,
            horas_max_semana=horas)
        db.session.add(area)
        areas[nombre] = area
    db.session.flush()

    materias = {}
    for nombre, area_nombre, nivel_nombre, horas, tipo in MATERIAS:
        nivel = nivel_tercero if nivel_nombre == 'E.E.B.' else nivel_medio
        materia = Materia(
            colegio_id=colegio.id,
            nivel_id=nivel.id,
            nombre=nombre,
            area_id=areas[area_nombre].id,
            horas_semanales=horas,
            tipo_aula_requerida=tipo,
        )
        db.session.add(materia)
        materias[(nombre, nivel_nombre)] = materia
    db.session.flush()

    materias[('Informática', 'Nivel Medio')].especialidades = [especialidades['BATIN']]
    materias[('Contabilidad', 'Nivel Medio')].especialidades = [especialidades['BATAN']]
    materias[('Administración', 'Nivel Medio')].especialidades = [especialidades['BATAN']]

    return (anio, anio_anterior, grados, turnos, aulas, materias, planes,
            areas, especialidades)


def crear_plantillas(colegio, turnos):
    plantillas = {}

    for nombre, turno_nombre, bloques in [
        ('Tercer Ciclo', 'Doble escolaridad', BLOQUES_TERCER_CICLO),
        ('Nivel Medio', 'Doble escolaridad', BLOQUES_NIVEL_MEDIO),
    ]:
        plantilla = PlantillaHorario(
            colegio_id=colegio.id,
            turno_id=turnos[turno_nombre].id,
            nombre=nombre,
        )
        db.session.add(plantilla)
        db.session.flush()
        for dia in range(1, 6):
            bloques_dia = list(bloques)
            # El esqueleto de Tercer Ciclo suma 47 bloques semanales:
            # 9 bloques de lunes a viernes y un décimo bloque martes y jueves.
            if nombre == 'Tercer Ciclo' and dia in (2, 4, 5):
                bloques_dia.append(('clase', '15:00', '15:40'))
            for numero, (tipo, desde, hasta) in enumerate(bloques_dia, start=1):
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
    for nombre, documento, nombres_materias, max_sem, _max_dia, nivel_nombre in PROFESORES:
        profe = Profesor(
            colegio_id=colegio.id,
            nombre=nombre,
            documento=documento,
            contacto='0981 000 000',
            horas_max_semana=max_sem,
            activo=True,
        )
        db.session.add(profe)
        db.session.flush()
        profe.materias = [
            materias[(m, nivel_nombre)] for m in nombres_materias
            if (m, nivel_nombre) in materias
        ]
        especialidad = {
            'Lourdes Cáceres': 'BATAN',
            'Mabel Villalba': 'BATAN',
            'Emilio Rojas': 'BATIN',
            'Marcos Duarte': 'BATIN',
        }.get(nombre)
        if especialidad:
            plan = PlanEstudio.query.filter_by(nombre=especialidad).first()
            if plan and plan.especialidad:
                profe.especialidades = [plan.especialidad]
        desde, hasta = time(7, 30), time(18, 0)
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
        'E.E.B. 7°-9°': PLAN_TERCER_CICLO,
        'Nivel Medio Común': PLAN_COMUN,
        'BATIN': PLAN_INFO,
        'BATAN': PLAN_CONTA,
    }
    for plan_nombre, plan in planes.items():
        plan_db = PlanEstudio.query.filter_by(nombre=plan_nombre).first()
        if not plan_db:
            continue
        for grado in plan_db.grados:
            for materia_nombre, horas in plan:
                materia = materias[(materia_nombre, grado.nivel.nombre)]
                tipo = 'especifico' if materia_nombre in (
                    'Informática', 'Contabilidad', 'Administración') else 'comun'
                db.session.add(PlanMateria(
                    plan_id=plan_db.id,
                    grado_id=grado.id,
                    materia_id=materia.id,
                    horas_semanales=horas,
                    max_bloques_por_dia=(2 if horas > 5 else 1),
                    requiere_bloque_doble=False,
                    tipo_plan=tipo,
                ))
    db.session.flush()


def crear_secciones(anio, grados, turnos, aulas, plantillas):
    datos = [
        ('7°', 'A', 'Doble escolaridad', 'Tercer Ciclo', 'Aula 1', 'E.E.B. 7°-9°'),
        ('8°', 'A', 'Doble escolaridad', 'Tercer Ciclo', 'Aula 2', 'E.E.B. 7°-9°'),
        ('1°', 'A', 'Doble escolaridad', 'Nivel Medio', 'Aula 1', 'BATIN'),
        ('1°', 'B', 'Doble escolaridad', 'Nivel Medio', 'Aula 2', 'BATIN'),
        ('1°', 'A', 'Doble escolaridad', 'Nivel Medio', 'Aula 4', 'BATAN'),
    ]

    for grado_nombre, nombre, turno_nombre, plantilla_nombre, aula_nombre, plan_nombre in datos:
        grado = grados[grado_nombre]
        plan = PlanEstudio.query.filter_by(nombre=plan_nombre).first()
        seccion = Seccion(
            anio_lectivo_id=anio.id,
            grado_id=grado.id,
            plan_id=plan.id,
            especialidad_id=plan.especialidad_id,
            turno_id=turnos[turno_nombre].id,
            nombre=nombre,
            aula_base_id=aulas[aula_nombre].id,
            plantilla_id=plantillas[plantilla_nombre].id,
        )
        db.session.add(seccion)
        db.session.flush()

        for gm in PlanMateria.query.filter_by(
                plan_id=plan.id, grado_id=grado.id).all():
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
         materias[('Educación Física', 'E.E.B.')], {}),
        ('NO_ULTIMA_HORA', 'Matemática no en la última hora', False, 40,
         materias[('Matemática', 'E.E.B.')], {}),
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
                                    limite_segundos=180)
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

        anio, anio_anterior, grados, turnos, aulas, materias, planes, areas, especialidades = crear_estructura(colegio)
        plantillas = crear_plantillas(colegio, turnos)
        profesores = crear_profesores(colegio, materias)
        for profe in profesores.values():
            profe.horas_anio = [
                ProfesorHorasAnio(
                    anio_lectivo_id=anio.id,
                    horas_max_semana=profe.horas_max_semana,
                ),
                ProfesorHorasAnio(
                    anio_lectivo_id=anio_anterior.id,
                    horas_max_semana=20,
                ),
            ]
        db.session.flush()
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
        print('  Cursos y grados:', Grado.query.count())
        print('  Secciones:', Seccion.query.count())
        print('  Profesores:', Profesor.query.count())
        print('  Materias:', Materia.query.count())
        print('  Aulas:', Aula.query.count())
        print('  Especialidades:', Especialidad.query.filter_by(colegio_id=colegio.id).count())
        print('  Planes:', PlanEstudio.query.filter_by(colegio_id=colegio.id).count())
        print('  Áreas:', AreaConocimiento.query.filter_by(colegio_id=colegio.id).count())
        print('  Usuarios preservados:', total_usuarios)
        print('  Login: los usuarios existentes siguen funcionando.')


if __name__ == '__main__':
    main()
