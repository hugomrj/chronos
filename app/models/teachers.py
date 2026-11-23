from app.extensions import db
from app.models.base import BaseModel


class Profesor(BaseModel):
    __tablename__ = 'profesor'
    __table_args__ = (
        db.UniqueConstraint('colegio_id', 'documento', name='uq_profesor_colegio_documento'),
    )

    colegio_id = db.Column(db.Integer, db.ForeignKey('colegio.id'), nullable=False)
    nombre = db.Column(db.Text, nullable=False)
    documento = db.Column(db.Text)
    contacto = db.Column(db.Text)
    horas_max_semana = db.Column(db.Integer)
    activo = db.Column(db.Boolean, nullable=False, default=True, server_default='true')

    colegio = db.relationship('Colegio', back_populates='profesores')
    materias = db.relationship(
        'Materia', secondary='profesor_materia', backref='profesores'
    )
    disponibilidad = db.relationship(
        'ProfesorDisponibilidad', back_populates='profesor',
        cascade='all, delete-orphan'
    )
    horas_anio = db.relationship(
        'ProfesorHorasAnio', back_populates='profesor',
        cascade='all, delete-orphan'
    )

    def __repr__(self):
        return f'<Profesor {self.nombre}>'


class ProfesorHorasAnio(db.Model):
    __tablename__ = 'profesor_horas_anio'

    profesor_id = db.Column(db.Integer,
                            db.ForeignKey('profesor.id', ondelete='CASCADE'),
                            primary_key=True)
    anio_lectivo_id = db.Column(db.Integer,
                                db.ForeignKey('anio_lectivo.id', ondelete='CASCADE'),
                                primary_key=True)
    horas_max_semana = db.Column(db.Integer, nullable=False)

    profesor = db.relationship('Profesor', back_populates='horas_anio')
    anio_lectivo = db.relationship('AnioLectivo')

    def __repr__(self):
        return f'<ProfesorHorasAnio {self.profesor_id} {self.anio_lectivo_id}>'


class ProfesorMateria(db.Model):
    __tablename__ = 'profesor_materia'

    profesor_id = db.Column(db.Integer, db.ForeignKey('profesor.id', ondelete='CASCADE'),
                            primary_key=True)
    materia_id = db.Column(db.Integer, db.ForeignKey('materia.id'), primary_key=True)


class ProfesorDisponibilidad(BaseModel):
    __tablename__ = 'profesor_disponibilidad'
    __table_args__ = (
        db.CheckConstraint('dia_semana BETWEEN 1 AND 7', name='ck_disponibilidad_dia'),
        db.CheckConstraint("tipo IN ('disponible','no_disponible')",
                           name='ck_disponibilidad_tipo'),
        db.CheckConstraint('hora_hasta > hora_desde', name='ck_disponibilidad_horas'),
    )

    profesor_id = db.Column(db.Integer, db.ForeignKey('profesor.id', ondelete='CASCADE'),
                            nullable=False)
    dia_semana = db.Column(db.SmallInteger, nullable=False)
    hora_desde = db.Column(db.Time, nullable=False)
    hora_hasta = db.Column(db.Time, nullable=False)
    tipo = db.Column(db.Text, nullable=False)
    motivo = db.Column(db.Text)

    profesor = db.relationship('Profesor', back_populates='disponibilidad')
