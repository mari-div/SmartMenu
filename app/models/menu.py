"""Paradigma POO: modelos del menu (categorias, ingredientes y platos)."""
from enum import Enum

from app.extensions import db


class TipoIngrediente(str, Enum):
    CARNE = "carne"
    PESCADO = "pescado"
    LACTEO = "lacteo"
    HUEVO = "huevo"
    VEGETAL = "vegetal"
    CEREAL = "cereal"
    OTRO = "otro"


class Categoria(db.Model):
    __tablename__ = "categorias"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(60), unique=True, nullable=False)
    orden = db.Column(db.Integer, default=0)

    platos = db.relationship("Plato", back_populates="categoria", order_by="Plato.id")

    def __repr__(self):
        return f"<Categoria {self.nombre}>"


class Ingrediente(db.Model):
    __tablename__ = "ingredientes"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(80), unique=True, nullable=False)
    tipo = db.Column(db.String(20), nullable=False, default=TipoIngrediente.OTRO.value)
    tiene_gluten = db.Column(db.Boolean, nullable=False, default=False)
    tiene_frutos_secos = db.Column(db.Boolean, nullable=False, default=False)
    stock = db.Column(db.Float, nullable=False, default=0)
    stock_minimo = db.Column(db.Float, nullable=False, default=5)   # debajo de esto: alerta
    unidad = db.Column(db.String(10), nullable=False, default="kg")

    @property
    def stock_bajo(self) -> bool:
        return self.stock <= self.stock_minimo

    def __repr__(self):
        return f"<Ingrediente {self.nombre}>"


class PlatoIngrediente(db.Model):
    """Tabla intermedia: cuanto de cada ingrediente lleva un plato."""
    __tablename__ = "plato_ingredientes"

    plato_id = db.Column(db.Integer, db.ForeignKey("platos.id"), primary_key=True)
    ingrediente_id = db.Column(db.Integer, db.ForeignKey("ingredientes.id"), primary_key=True)
    cantidad = db.Column(db.Float, nullable=False, default=0.1)

    plato = db.relationship("Plato", back_populates="ingredientes")
    ingrediente = db.relationship("Ingrediente")


class Plato(db.Model):
    __tablename__ = "platos"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), unique=True, nullable=False)
    descripcion = db.Column(db.String(255), default="")
    precio = db.Column(db.Numeric(10, 2, asdecimal=False), nullable=False)
    costo = db.Column(db.Numeric(10, 2, asdecimal=False), nullable=False, default=0)
    tiempo_prep_min = db.Column(db.Float, nullable=False, default=10)
    disponible = db.Column(db.Boolean, nullable=False, default=True)
    imagen_url = db.Column(db.String(500))            # foto (enlace de internet)
    categoria_id = db.Column(db.Integer, db.ForeignKey("categorias.id"), nullable=False)

    categoria = db.relationship("Categoria", back_populates="platos")
    ingredientes = db.relationship("PlatoIngrediente", back_populates="plato",
                                   cascade="all, delete-orphan")

    @property
    def margen(self) -> float:
        return round(self.precio - self.costo, 2)

    @property
    def margen_pct(self) -> float:
        return round(100 * self.margen / self.precio, 1) if self.precio else 0.0

    def a_dict(self) -> dict:
        """Version simple (diccionario) del plato.

        Es el puente entre POO y funcional: los modulos de `app.funcional`
        reciben estos diccionarios y no necesitan conocer la base de datos.
        """
        return {
            "id": self.id,
            "nombre": self.nombre,
            "descripcion": self.descripcion,
            "precio": float(self.precio),
            "imagen_url": self.imagen_url or "",
            "categoria": self.categoria.nombre,
            "tiempo_prep_min": self.tiempo_prep_min,
            "disponible": self.disponible,
            "ingredientes": [
                {
                    "nombre": pi.ingrediente.nombre,
                    "tipo": pi.ingrediente.tipo,
                    "tiene_gluten": pi.ingrediente.tiene_gluten,
                    "tiene_frutos_secos": pi.ingrediente.tiene_frutos_secos,
                }
                for pi in self.ingredientes
            ],
        }

    def __repr__(self):
        return f"<Plato {self.nombre} ${self.precio}>"
