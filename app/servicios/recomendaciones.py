"""Recomendador de platos (usa la logica de NumPy de app/funcional/recomendador.py).

La matriz de co-ocurrencia se calcula con todos los pedidos entregados y se guarda
unos minutos: asi la carta puede pedir sugerencias en cada toque sin recalcular todo.
"""
import time

from sqlalchemy import text

from app.extensions import db
from app.funcional.recomendador import construir_matriz_coocurrencia, recomendar_con_ids
from app.models import Plato

TTL_SEGUNDOS = 300
_cache: dict = {"hasta": 0.0, "matriz": None, "ids": []}


def reiniciar_cache() -> None:
    _cache.update(hasta=0.0, matriz=None, ids=[])


def _matriz():
    if _cache["matriz"] is None or time.monotonic() > _cache["hasta"]:
        ids = [i for (i,) in db.session.execute(text("SELECT id FROM platos ORDER BY id"))]
        filas = db.session.execute(text(
            "SELECT i.pedido_id, i.plato_id FROM items_pedido i "
            "JOIN pedidos p ON p.id = i.pedido_id WHERE p.estado = 'entregado'"))
        por_pedido: dict[int, list[int]] = {}
        for pedido_id, plato_id in filas:
            por_pedido.setdefault(pedido_id, []).append(plato_id)
        _cache.update(matriz=construir_matriz_coocurrencia(list(por_pedido.values()), ids),
                      ids=ids, hasta=time.monotonic() + TTL_SEGUNDOS)
    return _cache["matriz"], _cache["ids"]


def sugerencias(plato_id: int, n: int = 3, excluir=()) -> list[Plato]:
    """Los platos que mas se piden junto con `plato_id` (sin repetir ni los ya elegidos)."""
    matriz, ids = _matriz()
    if plato_id not in ids:
        return []
    pedidos_ids = recomendar_con_ids(plato_id, matriz, ids, n + len(excluir) + 2)
    resultado = []
    for pid in pedidos_ids:
        plato = db.session.get(Plato, pid)
        if plato and plato.disponible and pid not in excluir:
            resultado.append(plato)
        if len(resultado) == n:
            break
    return resultado
