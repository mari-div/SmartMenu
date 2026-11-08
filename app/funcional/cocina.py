"""Paradigma FUNCIONAL: priorizacion de la cola de cocina y tiempos estimados.

Trabaja con datos inmutables (`PedidoCocina`) y funciones puras: se pasa
`ahora` como argumento para que los resultados sean reproducibles en pruebas.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, Sequence


@dataclass(frozen=True)
class PedidoCocina:
    id: int
    creado_en: datetime
    tiempo_prep_min: float   # tiempo estimado de preparacion del pedido
    unidades: int            # cantidad de platos
    comensales: int = 1


# ---------------------------------------------------------------- tiempo de preparacion
def tiempo_preparacion_pedido(tiempos_platos: Sequence[float]) -> float:
    """Tiempo estimado de un pedido con varios platos.

    La cocina prepara los platos casi en paralelo: el plato mas lento marca el
    tiempo y cada plato adicional suma un 25% de su duracion.
    """
    if not tiempos_platos:
        return 0.0
    mayor = max(tiempos_platos)
    return round(mayor + 0.25 * (sum(tiempos_platos) - mayor), 2)


# ---------------------------------------------------------------- prioridad
def minutos_espera(pedido: PedidoCocina, ahora: datetime) -> float:
    return max(0.0, (ahora - pedido.creado_en).total_seconds() / 60)


def prioridad(pedido: PedidoCocina, ahora: datetime) -> float:
    """Puntaje de prioridad: mientras mas alto, mas urgente.

    - 1.0 punto por cada minuto que lleva esperando (evita que alguien se quede olvidado)
    - bono de rapidez: los pedidos cortos (<15 min) suben un poco; atender primero
      lo rapido reduce el tiempo de espera promedio de toda la sala
    - 0.5 puntos por comensal: las mesas grandes pesan mas
    """
    bono_rapidez = 0.4 * max(0.0, 15 - pedido.tiempo_prep_min)
    return round(minutos_espera(pedido, ahora) + bono_rapidez + 0.5 * pedido.comensales, 2)


def ordenar_cola(pedidos: Iterable[PedidoCocina], ahora: datetime) -> list[PedidoCocina]:
    """Devuelve los pedidos del mas urgente al menos urgente."""
    return sorted(pedidos, key=lambda p: (-prioridad(p, ahora), p.creado_en, p.id))


# ---------------------------------------------------------------- estimacion de entrega
def estimar_minutos_entrega(tiempos_por_delante: Iterable[float], tiempo_propio: float,
                            estaciones: int = 3) -> float:
    """Minutos hasta que el pedido este listo.

    La carga que hay por delante se reparte entre las estaciones de la cocina y
    luego se suma el tiempo del propio pedido.
    """
    carga = sum(tiempos_por_delante)
    return round(carga / max(1, estaciones) + tiempo_propio, 1)
