from app.extensions import db
from app.models.base import BaseModel
from flask_login import UserMixin


class Rol(db.Model):
    __tablename__ = 'rol'

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.Text, unique=True, nullable=False)


class Colegio(BaseModel):
    __tablename__ = 'colegio'

    nombre = db.Column(db.Text, nullable=False)

    anios = db.relationship(
        'AnioLectivo', back_populates='colegio',
        cascade='all, delete-orphan', order_by='AnioLectivo.nombre'
    )
    niveles = db.relationship('Nivel', back_populates='colegio', order_by='Nivel.nombre')
    turnos = db.relationship('Turno', back_populates='colegio', order_by='Turno.nombre')
    aulas = db.relationship('Aula', back_populates='colegio', order_by='Aula.nombre')
    materias = db.relationship('Materia', back_populates='colegio', order_by='Materia.nombre')
    profesores = db.relationship('Profesor', back_populates='colegio', order_by='Profesor.nombre')

    def __repr__(self):
        return f'<Colegio {self.nombre}>'


class AnioLectivo(BaseModel):
    __tablename__ = 'anio_lectivo'
    __table_args__ = (
        db.UniqueConstraint('colegio_id', 'nombre', name='uq_anio_colegio_nombre'),
        db.CheckConstraint('fecha_fin > fecha_inicio', name='ck_anio_fechas'),
    )

    colegio_id = db.Column(db.Integer, db.ForeignKey('colegio.id'), nullable=False)
    nombre = db.Column(db.Text, nullable=False)
    fecha_inicio = db.Column(db.Date, nullable=False)
    fecha_fin = db.Column(db.Date, nullable=False)
    activo = db.Column(db.Boolean, nullable=False, default=False, server_default='false')

    colegio = db.relationship('Colegio', back_populates='anios')
    secciones = db.relationship('Seccion', back_populates='anio_lectivo')

    def __repr__(self):
        return f'<AnioLectivo {self.nombre}>'


class Usuario(db.Model, UserMixin):
    __tablename__ = 'usuario'

    id = db.Column(db.Integer, primary_key=True)
    colegio_id = db.Column(db.Integer, db.ForeignKey('colegio.id'), nullable=False)
    email = db.Column(db.Text, unique=True, nullable=False)
    password_hash = db.Column(db.Text, nullable=False)
    rol_id = db.Column(db.Integer, db.ForeignKey('rol.id'), nullable=False)
    profesor_id = db.Column(db.Integer, db.ForeignKey('profesor.id'), nullable=True)
    activo = db.Column(db.Boolean, default=True, nullable=False)

    colegio = db.relationship('Colegio', backref='usuarios')
    rol = db.relationship('Rol', backref='usuarios')
    profesor = db.relationship('Profesor', backref='usuarios')

    def get_id(self):
        return str(self.id)

    @property
    def es_admin(self):
        return bool(self.rol and self.rol.nombre == 'admin')
