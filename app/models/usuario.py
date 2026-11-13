"""Paradigma POO: usuarios del sistema (con roles) y registro de auditoria."""
from datetime import datetime
from enum import Enum

from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db


class Rol(str, Enum):
    ADMIN = "admin"
    MOZO = "mozo"
    COCINA = "cocina"


ETIQUETA_ROL = {Rol.ADMIN.value: "Administrador", Rol.MOZO.value: "Mozo", Rol.COCINA.value: "Cocina"}


class Usuario(db.Model):
    __tablename__ = "usuarios"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(40), unique=True, nullable=False, index=True)
    nombre = db.Column(db.String(80), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    rol = db.Column(db.String(20), nullable=False, default=Rol.MOZO.value)
    activo = db.Column(db.Boolean, nullable=False, default=True)
    creado_en = db.Column(db.DateTime, nullable=False, default=datetime.now)
    ultimo_acceso = db.Column(db.DateTime)

    # --- contraseñas: nunca se guarda el texto, solo su hash ---------------------
    def set_password(self, clave: str) -> None:
        self.password_hash = generate_password_hash(clave)

    def check_password(self, clave: str) -> bool:
        return check_password_hash(self.password_hash, clave)

    @property
    def etiqueta_rol(self) -> str:
        return ETIQUETA_ROL.get(self.rol, self.rol)

    def a_dict(self) -> dict:
        return {"id": self.id, "username": self.username, "nombre": self.nombre,
                "rol": self.rol, "activo": self.activo,
                "ultimo_acceso": self.ultimo_acceso.isoformat(timespec="seconds")
                if self.ultimo_acceso else None}

    def __repr__(self):
        return f"<Usuario {self.username} ({self.rol})>"


class Auditoria(db.Model):
    """Bitacora de acciones importantes (quien hizo que y cuando)."""
    __tablename__ = "auditoria"

    id = db.Column(db.Integer, primary_key=True)
    fecha = db.Column(db.DateTime, nullable=False, default=datetime.now, index=True)
    username = db.Column(db.String(40), index=True)      # texto (se conserva aunque se borre el usuario)
    rol = db.Column(db.String(20))
    accion = db.Column(db.String(40), nullable=False, index=True)
    detalle = db.Column(db.String(500), default="")
    ip = db.Column(db.String(45))

    def a_dict(self) -> dict:
        return {"id": self.id, "fecha": self.fecha.isoformat(timespec="seconds"),
                "username": self.username or "—", "rol": self.rol or "—",
                "accion": self.accion, "detalle": self.detalle, "ip": self.ip or ""}
