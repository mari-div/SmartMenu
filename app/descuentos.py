"""Paradigma POO: reglas de descuento como jerarquia de clases (herencia y polimorfismo).

`ReglaDescuento` es la clase base abstracta: define QUE debe saber hacer toda regla
(`porcentaje`) y reutiliza el resto (`aplicar`, `__call__`).  Cada subclase decide
COMO calcula su porcentaje.  Gracias al polimorfismo, el codigo que usa las reglas
(`calcular_total`, `mejor_descuento`) no necesita saber de que tipo es cada una:
solo las recorre y las llama.

Como las reglas son *invocables* (`__call__`), se integran con la parte funcional
del proyecto: `mejor_descuento(reglas, ctx)` las trata como funciones.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # solo para anotaciones; evita un import circular con precios.py
    from app.funcional.precios import Contexto


class ReglaDescuento(ABC):
    """Base de todas las reglas: devuelve (porcentaje, nombre) segun el contexto."""

    nombre: str = "Descuento"

    @abstractmethod
    def porcentaje(self, ctx: "Contexto") -> float:
        """Porcentaje (0.0 a 1.0) que esta regla ofrece para este pedido."""

    def etiqueta(self, ctx: "Contexto") -> str:
        """Texto que se muestra al cliente cuando la regla se aplica."""
        return self.nombre

    def aplicar(self, ctx: "Contexto") -> tuple[float, str]:
        pct = self.porcentaje(ctx)
        return (pct, self.etiqueta(ctx)) if pct > 0 else (0.0, "")

    def __call__(self, ctx: "Contexto") -> tuple[float, str]:
        return self.aplicar(ctx)

    def __repr__(self) -> str:
        return f"<{type(self).__name__}>"


class HappyHour(ReglaDescuento):
    """15% (por defecto) entre las 17:00 y las 18:59."""
    nombre = "Happy hour"

    def __init__(self, desde: int = 17, hasta: int = 19, pct: float = 0.15):
        self.desde, self.hasta, self.pct = desde, hasta, pct

    def porcentaje(self, ctx: "Contexto") -> float:
        return self.pct if self.desde <= ctx.hora < self.hasta else 0.0


class DescuentoVolumen(ReglaDescuento):
    """Descuento escalonado segun el subtotal: S/ 180 -> 8%, S/ 100 -> 5%."""
    nombre = "Consumo mayor"

    def __init__(self, escalones: tuple[tuple[float, float], ...] = ((180, 0.08), (100, 0.05))):
        self.escalones = tuple(sorted(escalones, reverse=True))      # del mayor umbral al menor

    def _escalon(self, ctx: "Contexto"):
        return next(((umbral, pct) for umbral, pct in self.escalones if ctx.subtotal >= umbral), None)

    def porcentaje(self, ctx: "Contexto") -> float:
        escalon = self._escalon(ctx)
        return escalon[1] if escalon else 0.0

    def etiqueta(self, ctx: "Contexto") -> str:
        escalon = self._escalon(ctx)
        return f"Consumo mayor a S/ {escalon[0]:g}" if escalon else self.nombre


class DescuentoGrupo(ReglaDescuento):
    """10% para grupos de 6 o mas comensales."""
    nombre = "Descuento de grupo"

    def __init__(self, minimo: int = 6, pct: float = 0.10):
        self.minimo, self.pct = minimo, pct

    def porcentaje(self, ctx: "Contexto") -> float:
        return self.pct if ctx.comensales >= self.minimo else 0.0


def reglas_por_defecto() -> tuple[ReglaDescuento, ...]:
    """Las reglas que usa el restaurante. Para agregar otra basta una subclase nueva."""
    return (HappyHour(), DescuentoVolumen(), DescuentoGrupo())
