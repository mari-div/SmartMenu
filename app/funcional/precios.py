"""Paradigma FUNCIONAL: calculo de precios, descuentos y cuentas.

Todas las funciones son *puras*: no leen la base de datos, no modifican sus
argumentos y devuelven siempre el mismo resultado para los mismos datos.
Eso las hace faciles de probar y de combinar (composicion).
"""
from dataclasses import dataclass
from functools import reduce
from typing import Callable, Iterable


# ---------------------------------------------------------------- datos inmutables
@dataclass(frozen=True)
class Linea:
    """Una linea de pedido: precio unitario y cantidad."""
    precio_unitario: float
    cantidad: int


@dataclass(frozen=True)
class Contexto:
    """Informacion que las reglas de descuento pueden consultar."""
    subtotal: float
    unidades: int
    hora: int          # 0-23
    comensales: int = 1


@dataclass(frozen=True)
class Desglose:
    subtotal: float
    descuento: float
    total: float
    regla_aplicada: str = ""


# ---------------------------------------------------------------- utilidades
def componer(*funciones: Callable) -> Callable:
    """componer(f, g, h)(x) == h(g(f(x)))  (de izquierda a derecha)."""
    return lambda x: reduce(lambda acc, f: f(acc), funciones, x)


def redondear(valor: float) -> float:
    return round(valor + 1e-9, 2)


# ---------------------------------------------------------------- subtotales
def importe_linea(linea: Linea) -> float:
    return linea.precio_unitario * linea.cantidad


def subtotal(lineas: Iterable[Linea]) -> float:
    """Suma de todas las lineas usando map + reduce."""
    return redondear(reduce(lambda a, b: a + b, map(importe_linea, lineas), 0.0))


def unidades(lineas: Iterable[Linea]) -> int:
    return sum(map(lambda l: l.cantidad, lineas))


# ---------------------------------------------------------------- reglas de descuento
# Cada regla es una funcion  Contexto -> (porcentaje, nombre).  Es facil agregar mas.
def happy_hour(ctx: Contexto) -> tuple[float, str]:
    """15% de descuento entre las 17:00 y las 18:59."""
    return (0.15, "Happy hour") if 17 <= ctx.hora < 19 else (0.0, "")


def descuento_volumen(ctx: Contexto) -> tuple[float, str]:
    """8% si el subtotal llega a $50, 5% si llega a $30."""
    if ctx.subtotal >= 50:
        return 0.08, "Consumo mayor a $50"
    if ctx.subtotal >= 30:
        return 0.05, "Consumo mayor a $30"
    return 0.0, ""


def descuento_grupo(ctx: Contexto) -> tuple[float, str]:
    """10% para grupos de 6 o mas comensales."""
    return (0.10, "Descuento de grupo") if ctx.comensales >= 6 else (0.0, "")


REGLAS_POR_DEFECTO = (happy_hour, descuento_volumen, descuento_grupo)


def mejor_descuento(reglas: Iterable[Callable], ctx: Contexto) -> tuple[float, str]:
    """Aplica solo el mayor descuento (los descuentos no se acumulan)."""
    return max(map(lambda regla: regla(ctx), reglas), default=(0.0, ""),
               key=lambda resultado: resultado[0])


# ---------------------------------------------------------------- total del pedido
def calcular_total(lineas: Iterable[Linea], hora: int, comensales: int = 1,
                   reglas: Iterable[Callable] = REGLAS_POR_DEFECTO) -> Desglose:
    lineas = tuple(lineas)
    sub = subtotal(lineas)
    ctx = Contexto(subtotal=sub, unidades=unidades(lineas), hora=hora, comensales=comensales)
    porcentaje, nombre = mejor_descuento(reglas, ctx)
    descuento = redondear(sub * porcentaje)
    return Desglose(subtotal=sub, descuento=descuento,
                    total=redondear(sub - descuento), regla_aplicada=nombre)


# ---------------------------------------------------------------- propina y division de cuenta
def propina_sugerida(total: float, porcentaje: float = 0.10) -> float:
    return redondear(total * porcentaje)


def dividir_cuenta(total: float, personas: int) -> list[float]:
    """Reparte el total en partes iguales sin perder ni inventar centavos.

    Trabaja en centavos enteros: los centavos sobrantes se reparten de a uno
    entre las primeras personas.  Ej.: $10.00 entre 3 -> [3.34, 3.33, 3.33]
    """
    if personas < 1:
        raise ValueError("Debe haber al menos 1 persona")
    centavos = round(total * 100)
    base, resto = divmod(centavos, personas)
    return [(base + (1 if i < resto else 0)) / 100 for i in range(personas)]
