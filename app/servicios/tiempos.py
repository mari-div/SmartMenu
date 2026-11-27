"""Tiempos de cocina aprendidos del historial real.

La estimacion base (`tiempo_prep_min` de cada plato) es una promesa teorica; aqui se
mide cuanto tarda de verdad la cocina a cada hora del dia y se ajusta la estimacion.
"""
import time
from datetime import datetime, timedelta

from sqlalchemy.orm import selectinload

from app.funcional.cocina import factor_ajuste
from app.models import ItemPedido, Pedido

VENTANA_DIAS = 30
TTL_SEGUNDOS = 600                  # el calculo es pesado: se reutiliza 10 minutos
_cache: dict = {"hasta": 0.0, "factores": {}}


def reiniciar_cache() -> None:
    _cache.update(hasta=0.0, factores={})


def calcular_factores(ahora: datetime | None = None) -> dict[int, float]:
    """{hora del dia: factor}.  1.15 = la cocina tarda un 15% mas de lo estimado a esa hora."""
    ahora = ahora or datetime.now()
    desde = ahora - timedelta(days=VENTANA_DIAS)
    pedidos = (Pedido.query
               .options(selectinload(Pedido.items).joinedload(ItemPedido.plato))
               .filter(Pedido.estado == "entregado", Pedido.creado_en >= desde,
                       Pedido.inicio_prep_en.isnot(None), Pedido.listo_en.isnot(None)).all())
    por_hora: dict[int, list[float]] = {}
    for p in pedidos:
        estimado = p.tiempo_prep_min
        real = (p.listo_en - p.inicio_prep_en).total_seconds() / 60
        if estimado > 0 and 0.2 < real / estimado < 5:          # descarta registros absurdos
            por_hora.setdefault(p.creado_en.hour, []).append(real / estimado)
    return {hora: factor_ajuste(razones) for hora, razones in por_hora.items()}


def factor_para(hora: int, ahora: datetime | None = None) -> float:
    if time.monotonic() > _cache["hasta"]:
        _cache.update(factores=calcular_factores(ahora), hasta=time.monotonic() + TTL_SEGUNDOS)
    return _cache["factores"].get(hora, 1.0)
