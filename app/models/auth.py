from app.extensions import db
from flask_login import UserMixin

class Rol(db.Model):
    __tablename__ = 'rol'
    
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.Text, unique=True, nullable=False)


class Usuario(db.Model, UserMixin):
    __tablename__ = 'usuario'
    
    id = db.Column(db.Integer, primary_key=True)
    colegio_id = db.Column(db.Integer, db.ForeignKey('colegio.id'), nullable=False)
    email = db.Column(db.Text, unique=True, nullable=False)
    password_hash = db.Column(db.Text, nullable=False)
    rol_id = db.Column(db.Integer, db.ForeignKey('rol.id'), nullable=False)
    profesor_id = db.Column(db.Integer, db.ForeignKey('profesor.id'), nullable=True)
    activo = db.Column(db.Boolean, default=True, nullable=False)

    # Relaciones básicas (se pueden expandir luego)
    rol = db.relationship('Rol', backref='usuarios')

    def get_id(self):
        return str(self.id)