
"""Servicios para gestionar el inventario de ingredientes."""

from math import isfinite

from app.extensions import db
from app.models import Plato


class ErrorInventario(ValueError):
    """Error cuando no hay suficiente stock o existen datos inválidos."""


def validar_cantidad(cantidad: int) -> None:
    """Comprueba que la cantidad solicitada sea válida."""

    if isinstance(cantidad, bool) or not isinstance(cantidad, int):
        raise ErrorInventario("La cantidad debe ser un número entero.")

    if cantidad <= 0:
        raise ErrorInventario("La cantidad debe ser mayor que cero.")


def validar_stock(plato: Plato, cantidad: int = 1) -> None:
    """Comprueba que existan ingredientes suficientes."""

    validar_cantidad(cantidad)

    for relacion in plato.ingredientes:
        ingrediente = relacion.ingrediente
        stock = ingrediente.stock
        necesario = relacion.cantidad * cantidad

        if (
            stock is None
            or not isfinite(stock)
            or stock < 0
        ):
            raise ErrorInventario(
                f"El stock de '{ingrediente.nombre}' no es válido."
            )

        if (
            not isfinite(relacion.cantidad)
            or relacion.cantidad <= 0
        ):
            raise ErrorInventario(
                f"La cantidad configurada para '{ingrediente.nombre}' no es válida."
            )

        if stock < necesario:
            raise ErrorInventario(
                f"Stock insuficiente de '{ingrediente.nombre}'. "
                f"Disponible: {stock} {ingrediente.unidad}; "
                f"necesario: {necesario} {ingrediente.unidad}."
            )


def descontar_stock(plato: Plato, cantidad: int = 1) -> None:
    """Descuenta los ingredientes después de validar todo el stock."""

    validar_stock(plato, cantidad)

    for relacion in plato.ingredientes:
        ingrediente = relacion.ingrediente
        necesario = relacion.cantidad * cantidad
        ingrediente.stock -= necesario


def guardar_cambios_inventario() -> None:
    """Sincroniza los cambios de inventario con la sesión."""

    db.session.flush()
