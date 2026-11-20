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
    AnioLectivo, Aula, Colegio, Grado, Materia, Nivel, Profesor,
    ProfesorDisponibilidad, Turno,
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

PROFESORES = [
    {
        'nombre': 'Ana Benítez',
        'documento': '4001001',
        'contacto': '0981 111 222',
        'horas_min_semana': 12,
        'horas_max_semana': 25,
        'horas_max_dia': 5,
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
        'horas_min_semana': 8,
        'horas_max_semana': 20,
        'horas_max_dia': 4,
        'materias': ['Educación Física', 'Informática'],
        'disponibilidad': [
            (1, '13:00', '17:00'), (2, '13:00', '17:00'), (3, '13:00', '17:00'),
            (4, '13:00', '17:00'), (5, '13:00', '17:00'),
        ],
    },
    {
        'nombre': 'Lucía Fernández',
        'documento': '4001003',
        'contacto': '0983 555 666',
        'horas_min_semana': 10,
        'horas_max_semana': 22,
        'horas_max_dia': 5,
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

    for nombre, tipo_aula in MATERIAS:
        get_or_create(
            Materia, colegio_id=colegio.id, nombre=nombre,
            defaults={'tipo_aula_requerida': tipo_aula},
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
                'horas_min_semana': datos['horas_min_semana'],
                'horas_max_semana': datos['horas_max_semana'],
                'horas_max_dia': datos['horas_max_dia'],
                'activo': True,
            },
        )
        profe.materias = [
            materias_por_nombre[m] for m in datos['materias']
            if m in materias_por_nombre
        ]
        if not profe.disponibilidad:
            for dia, desde, hasta in datos['disponibilidad']:
                profe.disponibilidad.append(ProfesorDisponibilidad(
                    dia_semana=dia,
                    hora_desde=time.fromisoformat(desde),
                    hora_hasta=time.fromisoformat(hasta),
                    tipo='disponible',
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


if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        seed()
