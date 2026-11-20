from sqlalchemy import text
from sqlalchemy.dialects.postgresql import JSONB

from app.extensions import db
from app.models.base import BaseModel


class Regla(BaseModel):
    __tablename__ = 'regla'

    colegio_id = db.Column(db.Integer, db.ForeignKey('colegio.id'), nullable=False)
    codigo = db.Column(db.Text, nullable=False)
    descripcion = db.Column(db.Text)
    obligatoria = db.Column(db.Boolean, nullable=False, default=False,
                            server_default='false')
    peso = db.Column(db.Integer, nullable=False, default=10, server_default='10')
    activa = db.Column(db.Boolean, nullable=False, default=True, server_default='true')
    materia_id = db.Column(db.Integer, db.ForeignKey('materia.id'))
    nivel_id = db.Column(db.Integer, db.ForeignKey('nivel.id'))
    profesor_id = db.Column(db.Integer, db.ForeignKey('profesor.id'))
    parametros = db.Column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))

    colegio = db.relationship('Colegio', backref='reglas')
    materia = db.relationship('Materia', backref='reglas')
    nivel = db.relationship('Nivel', backref='reglas')
    profesor = db.relationship('Profesor', backref='reglas')

    def __repr__(self):
        return f'<Regla {self.codigo}>'
