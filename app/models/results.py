from sqlalchemy import Computed
from sqlalchemy.dialects.postgresql import INT4RANGE

from app.extensions import db
from app.models.base import BaseModel


class HorarioVersion(BaseModel):
    __tablename__ = 'horario_version'
    __table_args__ = (
        db.CheckConstraint("estado IN ('borrador','publicado','archivado')",
                           name='ck_version_estado'),
    )

    anio_lectivo_id = db.Column(db.Integer, db.ForeignKey('anio_lectivo.id'), nullable=False)
    turno_id = db.Column(db.Integer, db.ForeignKey('turno.id'), nullable=False)
    nombre = db.Column(db.Text)
    estado = db.Column(db.Text, nullable=False, default='borrador',
                       server_default='borrador')
    notas = db.Column(db.Text)
    creado_en = db.Column(db.DateTime(timezone=True), nullable=False,
                          server_default=db.func.now())

    anio_lectivo = db.relationship('AnioLectivo', backref='horario_versiones')
    turno = db.relationship('Turno', backref='horario_versiones')
    celdas = db.relationship(
        'HorarioCelda', back_populates='version',
        cascade='all, delete-orphan'
    )

    def __repr__(self):
        return f'<HorarioVersion {self.nombre or self.id} ({self.estado})>'


class HorarioCelda(BaseModel):
    __tablename__ = 'horario_celda'
    __table_args__ = (
        db.CheckConstraint("origen IN ('manual','auto')", name='ck_celda_origen'),
    )

    version_id = db.Column(db.Integer,
                           db.ForeignKey('horario_version.id', ondelete='CASCADE'),
                           nullable=False)
    seccion_materia_id = db.Column(db.Integer, db.ForeignKey('seccion_materia.id'),
                                   nullable=False)
    bloque_id = db.Column(db.Integer, db.ForeignKey('bloque.id'), nullable=False)
    aula_id = db.Column(db.Integer, db.ForeignKey('aula.id'))
    profesor_id = db.Column(db.Integer, db.ForeignKey('profesor.id'))
    fijado = db.Column(db.Boolean, nullable=False, default=False, server_default='false')
    origen = db.Column(db.Text, nullable=False, default='auto', server_default='auto')

    # Copiados por trigger desde bloque/seccion_materia; no se escriben desde Python.
    seccion_id = db.Column(db.Integer, nullable=False)
    dia_semana = db.Column(db.SmallInteger, nullable=False)
    inicio_min = db.Column(db.Integer, nullable=False)
    fin_min = db.Column(db.Integer, nullable=False)
    franja = db.Column(INT4RANGE,
                       Computed('int4range(inicio_min, fin_min)', persisted=True))

    version = db.relationship('HorarioVersion', back_populates='celdas')
    seccion_materia = db.relationship('SeccionMateria', backref='celdas')
    bloque = db.relationship('Bloque', backref='celdas')
    aula = db.relationship('Aula', foreign_keys=[aula_id], backref='celdas')
    profesor = db.relationship('Profesor', foreign_keys=[profesor_id], backref='celdas')

    def __repr__(self):
        return f'<HorarioCelda v{self.version_id} sm{self.seccion_materia_id}>'
