from app.extensions import db
from app.models.base import BaseModel


class Nivel(BaseModel):
    __tablename__ = 'nivel'
    __table_args__ = (
        db.UniqueConstraint('colegio_id', 'nombre', name='uq_nivel_colegio_nombre'),
    )

    colegio_id = db.Column(db.Integer, db.ForeignKey('colegio.id'), nullable=False)
    nombre = db.Column(db.Text, nullable=False)

    colegio = db.relationship('Colegio', back_populates='niveles')
    grados = db.relationship(
        'Grado', back_populates='nivel', order_by='Grado.orden, Grado.nombre'
    )

    def __repr__(self):
        return f'<Nivel {self.nombre}>'


class Grado(BaseModel):
    __tablename__ = 'grado'
    __table_args__ = (
        db.UniqueConstraint('nivel_id', 'nombre', name='uq_grado_nivel_nombre'),
    )

    nivel_id = db.Column(db.Integer, db.ForeignKey('nivel.id'), nullable=False)
    nombre = db.Column(db.Text, nullable=False)
    orden = db.Column(db.Integer, nullable=False, default=0, server_default='0')

    nivel = db.relationship('Nivel', back_populates='grados')
    grado_materias = db.relationship(
        'GradoMateria', back_populates='grado', cascade='all, delete-orphan'
    )

    def __repr__(self):
        return f'<Grado {self.nombre}>'


class Turno(BaseModel):
    __tablename__ = 'turno'
    __table_args__ = (
        db.UniqueConstraint('colegio_id', 'nombre', name='uq_turno_colegio_nombre'),
    )

    colegio_id = db.Column(db.Integer, db.ForeignKey('colegio.id'), nullable=False)
    nombre = db.Column(db.Text, nullable=False)

    colegio = db.relationship('Colegio', back_populates='turnos')
    plantillas = db.relationship('PlantillaHorario', back_populates='turno')

    def __repr__(self):
        return f'<Turno {self.nombre}>'


class Aula(BaseModel):
    __tablename__ = 'aula'
    __table_args__ = (
        db.UniqueConstraint('colegio_id', 'nombre', name='uq_aula_colegio_nombre'),
        db.CheckConstraint(
            "tipo IN ('regular','laboratorio','informatica','gimnasio','otro')",
            name='ck_aula_tipo',
        ),
    )

    colegio_id = db.Column(db.Integer, db.ForeignKey('colegio.id'), nullable=False)
    nombre = db.Column(db.Text, nullable=False)
    tipo = db.Column(db.Text, nullable=False, default='regular', server_default='regular')
    capacidad = db.Column(db.Integer)
    activa = db.Column(db.Boolean, nullable=False, default=True, server_default='true')

    colegio = db.relationship('Colegio', back_populates='aulas')

    def __repr__(self):
        return f'<Aula {self.nombre}>'


class Materia(BaseModel):
    __tablename__ = 'materia'
    __table_args__ = (
        db.UniqueConstraint('colegio_id', 'nombre', name='uq_materia_colegio_nombre'),
        db.CheckConstraint(
            "tipo_aula_requerida IS NULL OR tipo_aula_requerida IN "
            "('regular','laboratorio','informatica','gimnasio','otro')",
            name='ck_materia_tipo_aula',
        ),
    )

    colegio_id = db.Column(db.Integer, db.ForeignKey('colegio.id'), nullable=False)
    nombre = db.Column(db.Text, nullable=False)
    tipo_aula_requerida = db.Column(db.Text)

    colegio = db.relationship('Colegio', back_populates='materias')
    grado_materias = db.relationship(
        'GradoMateria', back_populates='materia', cascade='all, delete-orphan'
    )

    def __repr__(self):
        return f'<Materia {self.nombre}>'


class PlantillaHorario(BaseModel):
    __tablename__ = 'plantilla_horario'
    __table_args__ = (
        db.UniqueConstraint('colegio_id', 'nombre', name='uq_plantilla_colegio_nombre'),
    )

    colegio_id = db.Column(db.Integer, db.ForeignKey('colegio.id'), nullable=False)
    turno_id = db.Column(db.Integer, db.ForeignKey('turno.id'), nullable=False)
    nombre = db.Column(db.Text, nullable=False)

    turno = db.relationship('Turno', back_populates='plantillas')
    bloques = db.relationship(
        'Bloque', back_populates='plantilla',
        cascade='all, delete-orphan', order_by='Bloque.dia_semana, Bloque.numero'
    )

    def __repr__(self):
        return f'<PlantillaHorario {self.nombre}>'


class Bloque(BaseModel):
    __tablename__ = 'bloque'
    __table_args__ = (
        db.UniqueConstraint('plantilla_id', 'dia_semana', 'numero',
                            name='uq_bloque_plantilla_dia_numero'),
        db.CheckConstraint('dia_semana BETWEEN 1 AND 7', name='ck_bloque_dia'),
        db.CheckConstraint('hora_fin > hora_inicio', name='ck_bloque_horas'),
        db.CheckConstraint("tipo IN ('clase','receso')", name='ck_bloque_tipo'),
    )

    plantilla_id = db.Column(db.Integer, db.ForeignKey('plantilla_horario.id', ondelete='CASCADE'),
                             nullable=False)
    dia_semana = db.Column(db.SmallInteger, nullable=False)
    numero = db.Column(db.SmallInteger, nullable=False)
    hora_inicio = db.Column(db.Time, nullable=False)
    hora_fin = db.Column(db.Time, nullable=False)
    tipo = db.Column(db.Text, nullable=False, default='clase', server_default='clase')

    plantilla = db.relationship('PlantillaHorario', back_populates='bloques')

    def __repr__(self):
        return f'<Bloque dia={self.dia_semana} n={self.numero}>'
