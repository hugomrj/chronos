from app.extensions import db
from app.models.base import BaseModel


class Seccion(BaseModel):
    __tablename__ = 'seccion'
    __table_args__ = (
        db.UniqueConstraint('anio_lectivo_id', 'grado_id', 'turno_id', 'nombre',
                            name='uq_seccion_anio_grado_turno_nombre'),
    )

    anio_lectivo_id = db.Column(db.Integer, db.ForeignKey('anio_lectivo.id'), nullable=False)
    grado_id = db.Column(db.Integer, db.ForeignKey('grado.id'), nullable=False)
    turno_id = db.Column(db.Integer, db.ForeignKey('turno.id'), nullable=False)
    nombre = db.Column(db.Text, nullable=False)
    aula_base_id = db.Column(db.Integer, db.ForeignKey('aula.id'))
    plantilla_id = db.Column(db.Integer, db.ForeignKey('plantilla_horario.id'), nullable=False)

    anio_lectivo = db.relationship('AnioLectivo', back_populates='secciones')
    grado = db.relationship('Grado', backref='secciones')
    turno = db.relationship('Turno', backref='secciones')
    aula_base = db.relationship('Aula', foreign_keys=[aula_base_id], backref='secciones_base')
    plantilla = db.relationship('PlantillaHorario', backref='secciones')
    materias = db.relationship(
        'SeccionMateria', back_populates='seccion',
        cascade='all, delete-orphan'
    )

    def __repr__(self):
        return f'<Seccion {self.nombre}>'


class GradoMateria(db.Model):
    __tablename__ = 'grado_materia'

    grado_id = db.Column(db.Integer, db.ForeignKey('grado.id'), primary_key=True)
    materia_id = db.Column(db.Integer, db.ForeignKey('materia.id'), primary_key=True)
    horas_semanales = db.Column(db.Integer, nullable=False)
    max_bloques_por_dia = db.Column(db.Integer, nullable=False, default=1,
                                    server_default='1')
    requiere_bloque_doble = db.Column(db.Boolean, nullable=False, default=False,
                                      server_default='false')

    grado = db.relationship('Grado', back_populates='grado_materias')
    materia = db.relationship('Materia', back_populates='grado_materias')


class SeccionMateria(BaseModel):
    __tablename__ = 'seccion_materia'
    __table_args__ = (
        db.UniqueConstraint('seccion_id', 'materia_id', name='uq_seccion_materia'),
        db.CheckConstraint('horas_semanales > 0', name='ck_seccion_materia_horas'),
        db.CheckConstraint('max_bloques_por_dia > 0',
                           name='ck_seccion_materia_max_dia'),
        db.CheckConstraint('NOT profesor_fijado OR profesor_id IS NOT NULL',
                           name='ck_seccion_materia_profesor_fijado'),
    )

    seccion_id = db.Column(db.Integer, db.ForeignKey('seccion.id', ondelete='CASCADE'),
                           nullable=False)
    materia_id = db.Column(db.Integer, db.ForeignKey('materia.id'), nullable=False)
    horas_semanales = db.Column(db.Integer, nullable=False)
    max_bloques_por_dia = db.Column(db.Integer, nullable=False, default=1,
                                    server_default='1')
    requiere_bloque_doble = db.Column(db.Boolean, nullable=False, default=False,
                                      server_default='false')
    profesor_id = db.Column(db.Integer, db.ForeignKey('profesor.id'))
    profesor_fijado = db.Column(db.Boolean, nullable=False, default=False,
                                server_default='false')
    aula_requerida_id = db.Column(db.Integer, db.ForeignKey('aula.id'))

    seccion = db.relationship('Seccion', back_populates='materias')
    materia = db.relationship('Materia', backref='seccion_materias')
    profesor = db.relationship('Profesor', foreign_keys=[profesor_id],
                               backref='seccion_materias')
    aula_requerida = db.relationship('Aula', foreign_keys=[aula_requerida_id])
