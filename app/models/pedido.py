"""Paradigma POO: mesas, pedidos y su maquina de estados."""
import uuid
from datetime import datetime
from enum import Enum

from app.extensions import db
from app.funcional.cocina import tiempo_preparacion_pedido


class EstadoPedido(str, Enum):
    PENDIENTE = "pendiente"
    EN_PREPARACION = "en_preparacion"
    LISTO = "listo"
    ENTREGADO = "entregado"
    CANCELADO = "cancelado"


# Que cambios de estado estan permitidos
TRANSICIONES = {
    EstadoPedido.PENDIENTE: (EstadoPedido.EN_PREPARACION, EstadoPedido.CANCELADO),
    EstadoPedido.EN_PREPARACION: (EstadoPedido.LISTO, EstadoPedido.CANCELADO),
    EstadoPedido.LISTO: (EstadoPedido.ENTREGADO,),
    EstadoPedido.ENTREGADO: (),
    EstadoPedido.CANCELADO: (),
}

# Siguiente paso "normal" del flujo (boton "avanzar" de la cocina)
SIGUIENTE = {
    EstadoPedido.PENDIENTE: EstadoPedido.EN_PREPARACION,
    EstadoPedido.EN_PREPARACION: EstadoPedido.LISTO,
    EstadoPedido.LISTO: EstadoPedido.ENTREGADO,
}

ESTADOS_ACTIVOS = (EstadoPedido.PENDIENTE.value, EstadoPedido.EN_PREPARACION.value,
                   EstadoPedido.LISTO.value)


class TransicionInvalida(ValueError):
    """Se intento un cambio de estado que no esta permitido."""


def _nuevo_token() -> str:
    return uuid.uuid4().hex[:12]


class Mesa(db.Model):
    __tablename__ = "mesas"

    id = db.Column(db.Integer, primary_key=True)
    numero = db.Column(db.Integer, unique=True, nullable=False)
    capacidad = db.Column(db.Integer, nullable=False, default=4)
    # Identificador unico que ira dentro del codigo QR de la mesa
    token = db.Column(db.String(32), unique=True, nullable=False, default=_nuevo_token)

    pedidos = db.relationship("Pedido", back_populates="mesa")

    def __repr__(self):
        return f"<Mesa {self.numero}>"


class Pedido(db.Model):
    __tablename__ = "pedidos"

    id = db.Column(db.Integer, primary_key=True)
    mesa_id = db.Column(db.Integer, db.ForeignKey("mesas.id"), nullable=False)
    mozo_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), index=True)   # quien tomo el pedido
    # Codigo secreto del pedido: va dentro del QR que se entrega al cliente
    token = db.Column(db.String(32), unique=True, nullable=False, default=_nuevo_token)
    estado = db.Column(db.String(20), nullable=False, default=EstadoPedido.PENDIENTE.value,
                       index=True)
    comensales = db.Column(db.Integer, nullable=False, default=1)
    notas = db.Column(db.String(255), default="")

    subtotal = db.Column(db.Numeric(10, 2, asdecimal=False), nullable=False, default=0)
    descuento = db.Column(db.Numeric(10, 2, asdecimal=False), nullable=False, default=0)
    total = db.Column(db.Numeric(10, 2, asdecimal=False), nullable=False, default=0)

    # Marcas de tiempo de cada etapa (base del analisis de tiempos)
    creado_en = db.Column(db.DateTime, nullable=False, default=datetime.now, index=True)
    inicio_prep_en = db.Column(db.DateTime)
    listo_en = db.Column(db.DateTime)
    entregado_en = db.Column(db.DateTime)

    mesa = db.relationship("Mesa", back_populates="pedidos")
    mozo = db.relationship("Usuario", foreign_keys=[mozo_id])
    items = db.relationship("ItemPedido", back_populates="pedido",
                            cascade="all, delete-orphan")

    # ------------------------------------------------------------ comportamiento
    @property
    def estado_enum(self) -> EstadoPedido:
        return EstadoPedido(self.estado)

    @property
    def unidades(self) -> int:
        return sum(i.cantidad for i in self.items)

    @property
    def tiempo_prep_min(self) -> float:
        """Tiempo estimado de preparacion (usa la funcion pura del modulo funcional)."""
        return tiempo_preparacion_pedido([i.plato.tiempo_prep_min for i in self.items])

    def puede_pasar_a(self, nuevo: EstadoPedido) -> bool:
        return EstadoPedido(nuevo) in TRANSICIONES[self.estado_enum]

    def cambiar_estado(self, nuevo, ahora: datetime | None = None) -> None:
        nuevo = EstadoPedido(nuevo)
        if not self.puede_pasar_a(nuevo):
            raise TransicionInvalida(
                f"No se puede pasar de '{self.estado}' a '{nuevo.value}'")
        ahora = ahora or datetime.now()
        self.estado = nuevo.value
        if nuevo is EstadoPedido.EN_PREPARACION:
            self.inicio_prep_en = ahora
        elif nuevo is EstadoPedido.LISTO:
            self.listo_en = ahora
        elif nuevo is EstadoPedido.ENTREGADO:
            self.entregado_en = ahora

    def avanzar(self, ahora: datetime | None = None) -> EstadoPedido:
        """Pasa al siguiente estado del flujo normal y lo devuelve."""
        siguiente = SIGUIENTE.get(self.estado_enum)
        if siguiente is None:
            raise TransicionInvalida(f"El pedido en '{self.estado}' ya no puede avanzar")
        self.cambiar_estado(siguiente, ahora)
        return siguiente

    def __repr__(self):
        return f"<Pedido #{self.id} {self.estado}>"


class ItemPedido(db.Model):
    __tablename__ = "items_pedido"

    id = db.Column(db.Integer, primary_key=True)
    pedido_id = db.Column(db.Integer, db.ForeignKey("pedidos.id"), nullable=False, index=True)
    plato_id = db.Column(db.Integer, db.ForeignKey("platos.id"), nullable=False, index=True)
    cantidad = db.Column(db.Integer, nullable=False, default=1)
    # Se guarda el precio al momento de pedir (el menu puede cambiar despues)
    precio_unitario = db.Column(db.Numeric(10, 2, asdecimal=False), nullable=False)
    notas = db.Column(db.String(255), default="")

    pedido = db.relationship("Pedido", back_populates="items")
    plato = db.relationship("Plato")

    @property
    def importe(self) -> float:
        return round(self.precio_unitario * self.cantidad, 2)
