from app.extensions import db
from app.models.base import BaseModel
from flask_login import UserMixin


class Rol(db.Model):
    __tablename__ = 'rol'

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.Text, unique=True, nullable=False)
    es_master = db.Column(db.Boolean, nullable=False, default=False,
                          server_default='false')
    # Un rol bloqueado no puede entrar a la instancia.
    bloqueado = db.Column(db.Boolean, nullable=False, default=False,
                          server_default='false')

    # Claves de menú habilitadas. El rol master ve todo y no usa esta tabla.
    menu_items = db.relationship(
        'RolMenu', back_populates='rol', cascade='all, delete-orphan',
        lazy='selectin',
    )

    @property
    def items_menu(self):
        return {m.item for m in self.menu_items}

    def tiene_menu(self, clave):
        if self.es_master:
            return True
        return clave in self.items_menu

    @property
    def menu_configurable(self):
        return not self.es_master

    def __repr__(self):
        return f'<Rol {self.nombre}>'


class RolMenu(db.Model):
    __tablename__ = 'rol_menu'

    rol_id = db.Column(db.Integer,
                       db.ForeignKey('rol.id', ondelete='CASCADE'),
                       primary_key=True)
    item = db.Column(db.Text, primary_key=True)

    rol = db.relationship('Rol', back_populates='menu_items')


class Colegio(BaseModel):
    __tablename__ = 'colegio'

    nombre = db.Column(db.Text, nullable=False)
    minutos_hora_catedra = db.Column(
        db.Integer, nullable=False, default=40, server_default='40')
    # Si es false, el horario se genera solo con profesor y sección.
    usa_aulas = db.Column(db.Boolean, nullable=False, default=True,
                          server_default='true')
    aulas_cambiado_en = db.Column(db.DateTime(timezone=True))

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
        return bool(self.rol and self.rol.nombre in ('admin', 'master')
                    and not self.rol.bloqueado)

    @property
    def es_master(self):
        return bool(self.rol and self.rol.es_master)

    def puede_ver(self, clave_menu):
        if not self.rol or self.rol.bloqueado:
            return False
        return self.rol.tiene_menu(clave_menu)
