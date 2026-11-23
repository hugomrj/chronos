"""Carga datos mínimos de estructura para poder probar Chronos.

Uso: python scripts/seed_estructura.py
Es idempotente: no duplica registros existentes.
"""
from datetime import date, time
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.extensions import db
from app.factory import create_app
from app.models import (
    AnioLectivo, AreaConocimiento, Aula, Bloque, Colegio, Grado, GradoMateria, Materia, Nivel,
    PlantillaHorario, Profesor, ProfesorDisponibilidad, Regla, Seccion,
    SeccionMateria, Turno,
)

COLEGIO_NOMBRE = 'Colegio Demo'
ANIO_NOMBRE = '2026'

NIVELES = {
    'Primaria': ['1er grado', '2do grado', '3er grado'],
    'Secundaria': ['1er curso', '2do curso'],
}

TURNOS = ['Mañana', 'Tarde']

AULAS = [
    ('Aula 1', 'regular', 35),
    ('Aula 2', 'regular', 35),
    ('Aula 3', 'regular', 30),
    ('Laboratorio 1', 'laboratorio', 30),
    ('Sala Informática', 'informatica', 30),
    ('Gimnasio', 'gimnasio', 80),
]

MATERIAS = [
    ('Matemática', None),
    ('Lengua y Literatura', None),
    ('Ciencias Naturales', None),
    ('Ciencias Sociales', None),
    ('Inglés', None),
    ('Educación Física', 'gimnasio'),
    ('Informática', 'informatica'),
]

BLOQUES_MANANA = [
    ('clase', '07:00', '07:45'),
    ('clase', '07:45', '08:30'),
    ('clase', '08:30', '09:15'),
    ('receso', '09:15', '09:45'),
    ('clase', '09:45', '10:30'),
    ('clase', '10:30', '11:15'),
]

BLOQUES_TARDE = [
    ('clase', '13:00', '13:45'),
    ('clase', '13:45', '14:30'),
    ('clase', '14:30', '15:15'),
    ('receso', '15:15', '15:45'),
    ('clase', '15:45', '16:30'),
    ('clase', '16:30', '17:15'),
]

PLANTILLAS = [
    ('Mañana Primaria', 'Mañana', BLOQUES_MANANA),
    ('Tarde Secundaria', 'Tarde', BLOQUES_TARDE),
]

PLANES_GRADO = {
    '1er grado': [
        ('Matemática', 5), ('Lengua y Literatura', 5), ('Ciencias Naturales', 4),
        ('Ciencias Sociales', 3), ('Inglés', 3), ('Educación Física', 2),
        ('Informática', 2),
    ],
    '2do grado': [
        ('Matemática', 5), ('Lengua y Literatura', 5), ('Ciencias Naturales', 4),
        ('Ciencias Sociales', 3), ('Inglés', 3), ('Educación Física', 2),
        ('Informática', 2),
    ],
    '1er curso': [
        ('Matemática', 5), ('Lengua y Literatura', 4), ('Ciencias Naturales', 4),
        ('Ciencias Sociales', 4), ('Inglés', 3), ('Educación Física', 2),
        ('Informática', 2),
    ],
    '2do curso': [
        ('Matemática', 5), ('Lengua y Literatura', 4), ('Ciencias Naturales', 4),
        ('Ciencias Sociales', 4), ('Inglés', 3), ('Educación Física', 2),
        ('Informática', 2),
    ],
}

SECCIONES = [
    ('1er grado', 'A', 'Mañana', 'Mañana Primaria', 'Aula 1'),
    ('2do grado', 'A', 'Mañana', 'Mañana Primaria', 'Aula 3'),
    ('1er curso', 'A', 'Tarde', 'Tarde Secundaria', 'Aula 2'),
    ('2do curso', 'A', 'Tarde', 'Tarde Secundaria', 'Aula 3'),
]

REGLAS_DEMO = [
    {'codigo': 'ANTES_DE_RECESO', 'descripcion': 'Educación Física antes del receso',
     'obligatoria': False, 'peso': 50, 'materia': 'Educación Física'},
    {'codigo': 'NO_ULTIMA_HORA', 'descripcion': 'Matemática no en la última hora',
     'obligatoria': False, 'peso': 40, 'materia': 'Matemática'},
    {'codigo': 'DISTRIBUIR_SEMANA', 'descripcion': 'Repartir las horas en la semana',
     'obligatoria': True, 'peso': 10, 'parametros': {'max_por_dia': 1}},
    {'codigo': 'EVITAR_HUECOS_PROFESOR', 'descripcion': 'Evitar huecos de los profesores',
     'obligatoria': False, 'peso': 30, 'parametros': {'max_huecos': 1}},
]

PROFESORES = [
    {
        'nombre': 'Ana Benítez',
        'documento': '4001001',
        'contacto': '0981 111 222',
        'horas_max_semana': 25,
        'materias': ['Matemática', 'Ciencias Naturales'],
        'disponibilidad': [
            (1, '07:00', '12:00'), (2, '07:00', '12:00'), (3, '07:00', '12:00'),
            (4, '07:00', '12:00'), (5, '07:00', '12:00'),
        ],
    },
    {
        'nombre': 'Carlos Méndez',
        'documento': '4001002',
        'contacto': '0982 333 444',
        'horas_max_semana': 20,
        'materias': ['Educación Física', 'Informática'],
        'disponibilidad': [
            (1, '07:00', '12:00'), (2, '07:00', '12:00'), (3, '07:00', '12:00'),
            (4, '07:00', '12:00'), (5, '07:00', '12:00'),
            (1, '13:00', '18:00'), (2, '13:00', '18:00'), (3, '13:00', '18:00'),
            (4, '13:00', '18:00'), (5, '13:00', '18:00'),
        ],
    },
    {
        'nombre': 'Diego Ramírez',
        'documento': '4001004',
        'contacto': '0984 777 888',
        'horas_max_semana': 25,
        'materias': ['Matemática', 'Ciencias Naturales'],
        'disponibilidad': [
            (1, '13:00', '18:00'), (2, '13:00', '18:00'), (3, '13:00', '18:00'),
            (4, '13:00', '18:00'), (5, '13:00', '18:00'),
        ],
    },
    {
        'nombre': 'Lucía Fernández',
        'documento': '4001003',
        'contacto': '0983 555 666',
        'horas_max_semana': 22,
        'materias': ['Lengua y Literatura', 'Inglés', 'Ciencias Sociales'],
        'disponibilidad': [],
    },
]


def get_or_create(model, defaults=None, **kwargs):
    obj = model.query.filter_by(**kwargs).first()
    if obj:
        return obj, False
    obj = model(**kwargs, **(defaults or {}))
    db.session.add(obj)
    db.session.flush()
    return obj, True


def seed():
    colegio, _ = get_or_create(Colegio, nombre=COLEGIO_NOMBRE)

    anio = AnioLectivo.query.filter_by(colegio_id=colegio.id, nombre=ANIO_NOMBRE).first()
    if not anio:
        AnioLectivo.query.filter_by(colegio_id=colegio.id, activo=True).update(
            {'activo': False}, synchronize_session=False
        )
        anio = AnioLectivo(
            colegio_id=colegio.id,
            nombre=ANIO_NOMBRE,
            fecha_inicio=date(2026, 2, 1),
            fecha_fin=date(2026, 11, 30),
            activo=True,
        )
        db.session.add(anio)

    for nivel_nombre, grados in NIVELES.items():
        nivel, _ = get_or_create(Nivel, colegio_id=colegio.id, nombre=nivel_nombre)
        for orden, grado_nombre in enumerate(grados, start=1):
            get_or_create(Grado, nivel_id=nivel.id, nombre=grado_nombre,
                          defaults={'orden': orden})

    for turno_nombre in TURNOS:
        get_or_create(Turno, colegio_id=colegio.id, nombre=turno_nombre)

    for nombre, tipo, capacidad in AULAS:
        get_or_create(
            Aula, colegio_id=colegio.id, nombre=nombre,
            defaults={'tipo': tipo, 'capacidad': capacidad, 'activa': True},
        )

    area_general, _ = get_or_create(
        AreaConocimiento, colegio_id=colegio.id, nombre='General',
        defaults={'orden': 0, 'activa': True},
    )
    for nombre, tipo_aula in MATERIAS:
        get_or_create(
            Materia, colegio_id=colegio.id, nombre=nombre,
            defaults={'tipo_aula_requerida': tipo_aula,
                      'area_id': area_general.id},
        )

    materias_por_nombre = {
        m.nombre: m for m in Materia.query.filter_by(colegio_id=colegio.id).all()
    }
    for datos in PROFESORES:
        profe, _ = get_or_create(
            Profesor, colegio_id=colegio.id, nombre=datos['nombre'],
            defaults={
                'documento': datos['documento'],
                'contacto': datos['contacto'],
                'horas_max_semana': datos['horas_max_semana'],
                'activo': True,
            },
        )
        profe.materias = [
            materias_por_nombre[m] for m in datos['materias']
            if m in materias_por_nombre
        ]
        for dia, desde, hasta in datos['disponibilidad']:
            hd = time.fromisoformat(desde)
            hh = time.fromisoformat(hasta)
            cubierta = False
            for d in list(profe.disponibilidad):
                if d.dia_semana != dia or d.tipo != 'disponible':
                    continue
                if d.hora_desde <= hd and d.hora_hasta >= hh:
                    cubierta = True
                    break
                if d.hora_desde <= hd and d.hora_hasta < hh:
                    d.hora_hasta = hh
                    cubierta = True
                    break
            if not cubierta:
                profe.disponibilidad.append(ProfesorDisponibilidad(
                    dia_semana=dia,
                    hora_desde=hd,
                    hora_hasta=hh,
                    tipo='disponible',
                ))

    turnos_por_nombre = {
        t.nombre: t for t in Turno.query.filter_by(colegio_id=colegio.id).all()
    }
    for nombre, turno_nombre, bloques in PLANTILLAS:
        plantilla, _ = get_or_create(
            PlantillaHorario, colegio_id=colegio.id, nombre=nombre,
            defaults={'turno_id': turnos_por_nombre[turno_nombre].id},
        )
        if not plantilla.bloques:
            for dia in range(1, 6):
                for numero, (tipo, desde, hasta) in enumerate(bloques, start=1):
                    plantilla.bloques.append(Bloque(
                        dia_semana=dia,
                        numero=numero,
                        hora_inicio=time.fromisoformat(desde),
                        hora_fin=time.fromisoformat(hasta),
                        tipo=tipo,
                    ))

    for grado_nombre, plan in PLANES_GRADO.items():
        grado = Grado.query.filter_by(nombre=grado_nombre).first()
        if not grado:
            continue
        for materia_nombre, horas in plan:
            materia = materias_por_nombre.get(materia_nombre)
            if not materia:
                continue
            get_or_create(
                GradoMateria, grado_id=grado.id, materia_id=materia.id,
                defaults={'horas_semanales': horas, 'max_bloques_por_dia': 1,
                          'requiere_bloque_doble': False},
            )

    plantillas_por_nombre = {
        p.nombre: p for p in PlantillaHorario.query.filter_by(colegio_id=colegio.id).all()
    }
    aulas_por_nombre = {
        a.nombre: a for a in Aula.query.filter_by(colegio_id=colegio.id).all()
    }
    for grado_nombre, seccion_nombre, turno_nombre, plantilla_nombre, aula_nombre in SECCIONES:
        grado = Grado.query.filter_by(nombre=grado_nombre).first()
        turno = turnos_por_nombre.get(turno_nombre)
        plantilla = plantillas_por_nombre.get(plantilla_nombre)
        aula = aulas_por_nombre.get(aula_nombre)
        if not (grado and turno and plantilla):
            continue

        seccion = Seccion.query.filter_by(
            anio_lectivo_id=anio.id, grado_id=grado.id,
            turno_id=turno.id, nombre=seccion_nombre,
        ).first()
        if not seccion:
            seccion = Seccion(
                anio_lectivo_id=anio.id, grado_id=grado.id, turno_id=turno.id,
                nombre=seccion_nombre, aula_base_id=aula.id if aula else None,
                plantilla_id=plantilla.id,
            )
            db.session.add(seccion)
            db.session.flush()

        for gm in grado.grado_materias:
            existe = SeccionMateria.query.filter_by(
                seccion_id=seccion.id, materia_id=gm.materia_id
            ).first()
            if not existe:
                db.session.add(SeccionMateria(
                    seccion_id=seccion.id,
                    materia_id=gm.materia_id,
                    horas_semanales=gm.horas_semanales,
                    max_bloques_por_dia=gm.max_bloques_por_dia,
                    requiere_bloque_doble=gm.requiere_bloque_doble,
                ))

    for datos in REGLAS_DEMO:
        materia = materias_por_nombre.get(datos.get('materia'))
        existe = Regla.query.filter_by(
            colegio_id=colegio.id,
            codigo=datos['codigo'],
            materia_id=materia.id if materia else None,
            nivel_id=None,
            profesor_id=None,
        ).first()
        if not existe:
            db.session.add(Regla(
                colegio_id=colegio.id,
                codigo=datos['codigo'],
                descripcion=datos['descripcion'],
                obligatoria=datos['obligatoria'],
                peso=datos['peso'],
                activa=True,
                materia_id=materia.id if materia else None,
                parametros=datos.get('parametros', {}),
            ))

    db.session.commit()

    print('Estructura lista:')
    print(f'  Colegio: {colegio.nombre}')
    print(f'  Año activo: {anio.nombre}')
    print(f'  Niveles: {Nivel.query.filter_by(colegio_id=colegio.id).count()}')
    print(f'  Grados: {Grado.query.count()}')
    print(f'  Turnos: {Turno.query.filter_by(colegio_id=colegio.id).count()}')
    print(f'  Aulas: {Aula.query.filter_by(colegio_id=colegio.id).count()}')
    print(f'  Materias: {Materia.query.filter_by(colegio_id=colegio.id).count()}')
    print(f'  Profesores: {Profesor.query.filter_by(colegio_id=colegio.id).count()}')
    print(f'  Plantillas: {PlantillaHorario.query.filter_by(colegio_id=colegio.id).count()}')
    print(f'  Bloques: {Bloque.query.count()}')
    print(f'  Secciones: {Seccion.query.filter_by(anio_lectivo_id=anio.id).count()}')
    print(f'  Reglas: {Regla.query.filter_by(colegio_id=colegio.id).count()}')


if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        seed()
