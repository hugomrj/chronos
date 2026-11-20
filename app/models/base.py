from app.extensions import db


class BaseModel(db.Model):
    """Modelo abstracto con PK entera para las tablas de Chronos."""
    __abstract__ = True

    id = db.Column(db.Integer, primary_key=True)
