"""Servicios para gestionar el inventario de ingredientes."""

from app.extensions import db
from app.models import Plato


class ErrorInventario(ValueError):
    """Error cuando no hay suficiente stock para preparar un plato."""


def validar_stock(plato: Plato, cantidad: int = 1) -> None:
    """Comprueba que existan ingredientes suficientes para preparar un plato."""

    for relacion in plato.ingredientes:
        ingrediente = relacion.ingrediente
        necesario = relacion.cantidad * cantidad

        if ingrediente.stock < necesario:
            raise ErrorInventario(
                f"Stock insuficiente de '{ingrediente.nombre}'. "
                f"Disponible: {ingrediente.stock} {ingrediente.unidad}; "
                f"necesario: {necesario} {ingrediente.unidad}."
            )


def descontar_stock(plato: Plato, cantidad: int = 1) -> None:
    """Descuenta del inventario los ingredientes utilizados."""

    validar_stock(plato, cantidad)

    for relacion in plato.ingredientes:
        ingrediente = relacion.ingrediente
        necesario = relacion.cantidad * cantidad
        ingrediente.stock -= necesario


def guardar_cambios_inventario() -> None:
    """Guarda los cambios de stock en la base de datos."""
    db.session.flush()
