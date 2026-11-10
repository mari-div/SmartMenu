"""Capa de servicios: une los modelos (POO) con las funciones puras (funcional)."""
from datetime import datetime

from flask import current_app

from app.extensions import db
from app.funcional.cocina import (PedidoCocina, estimar_minutos_entrega, minutos_espera,
                                  ordenar_cola, prioridad)
from app.funcional.precios import Linea, calcular_total
from app.models import ESTADOS_ACTIVOS, EstadoPedido, ItemPedido, Mesa, Pedido, Plato

# ---------------------------------------------------------------- inventario
from app.servicios.inventario import (
    ErrorInventario,
    descontar_stock,
    validar_stock,
)


MAX_CANTIDAD_POR_PLATO = 20


class ErrorPedido(ValueError):
    """Datos invalidos al crear un pedido (se devuelve al cliente como error 400)."""


# ---------------------------------------------------------------- utilidades
def _estaciones() -> int:
    return current_app.config["ESTACIONES_COCINA"]


def _lineas_validadas(items: list[dict]) -> list[tuple[Plato, int, str]]:
    """Valida el carrito y junta los platos repetidos. Devuelve (plato, cantidad, nota)."""
    if not items:
        raise ErrorPedido("El pedido no tiene platos")
    acumulado: dict[int, list] = {}
    for item in items:
        try:
            plato_id, cantidad = int(item["plato_id"]), int(item["cantidad"])
        except (KeyError, TypeError, ValueError):
            raise ErrorPedido("Cada plato necesita 'plato_id' y 'cantidad' numericos")
        if not 1 <= cantidad <= MAX_CANTIDAD_POR_PLATO:
            raise ErrorPedido(f"La cantidad debe estar entre 1 y {MAX_CANTIDAD_POR_PLATO}")
        plato = db.session.get(Plato, plato_id)
        if plato is None:
            raise ErrorPedido(f"El plato {plato_id} no existe")
        if not plato.disponible:
            raise ErrorPedido(f"'{plato.nombre}' no está disponible")
        nota = str(item.get("notas", ""))[:255]
        if plato_id in acumulado:
            acumulado[plato_id][1] += cantidad
        else:
            acumulado[plato_id] = [plato, cantidad, nota]
    return [tuple(v) for v in acumulado.values()]


def cotizar(items: list[dict], comensales: int = 1, ahora: datetime | None = None) -> dict:
    """Calcula subtotal, descuento y total sin crear nada (usa funciones puras)."""
    ahora = ahora or datetime.now()
    lineas = [Linea(p.precio, c) for p, c, _ in _lineas_validadas(items)]
    d = calcular_total(lineas, hora=ahora.hour, comensales=comensales)
    return {"subtotal": d.subtotal, "descuento": d.descuento, "total": d.total,
            "regla_aplicada": d.regla_aplicada}


# ---------------------------------------------------------------- cola de cocina
def _a_pedido_cocina(p: Pedido) -> PedidoCocina:
    return PedidoCocina(id=p.id, creado_en=p.creado_en, tiempo_prep_min=p.tiempo_prep_min,
                        unidades=p.unidades, comensales=p.comensales)


def _pedidos_activos(estados=ESTADOS_ACTIVOS) -> list[Pedido]:
    return Pedido.query.filter(Pedido.estado.in_(estados)).order_by(Pedido.creado_en).all()


def estimar_pedido(pedido: Pedido, ahora: datetime | None = None) -> float:
    """Minutos que faltan para que el pedido este listo."""
    ahora = ahora or datetime.now()
    estado = pedido.estado_enum
    if estado in (EstadoPedido.LISTO, EstadoPedido.ENTREGADO, EstadoPedido.CANCELADO):
        return 0.0
    propio = pedido.tiempo_prep_min
    if estado is EstadoPedido.EN_PREPARACION:
        transcurrido = (ahora - pedido.inicio_prep_en).total_seconds() / 60
        return round(max(0.0, propio - transcurrido), 1)
    # Pendiente: se suma la carga de lo que esta en preparacion y de los pedidos mas antiguos
    por_delante = [
        p.tiempo_prep_min
        for p in _pedidos_activos((EstadoPedido.PENDIENTE.value, EstadoPedido.EN_PREPARACION.value))
        if p.id != pedido.id and (p.estado == EstadoPedido.EN_PREPARACION.value
                                  or p.creado_en <= pedido.creado_en)
    ]
    return estimar_minutos_entrega(por_delante, propio, _estaciones())


# ---------------------------------------------------------------- crear pedido

def crear_pedido(mesa: Mesa, items: list[dict], comensales: int = 1, notas: str = "",
                 ahora: datetime | None = None) -> Pedido:
    ahora = ahora or datetime.now()
    try:
        comensales = max(1, min(int(comensales), 30))
    except (TypeError, ValueError):
        raise ErrorPedido("'comensales' debe ser un numero")

    lineas = _lineas_validadas(items)
    desglose = calcular_total(
        [Linea(p.precio, c) for p, c, _ in lineas],
        hora=ahora.hour,
        comensales=comensales
    )

    try:
        # Validar el stock de todos los platos antes de descontar.
        for plato, cantidad, _ in lineas:
            validar_stock(plato, cantidad)

        pedido = Pedido(
            mesa=mesa,
            comensales=comensales,
            notas=str(notas)[:255],
            creado_en=ahora,
            subtotal=desglose.subtotal,
            descuento=desglose.descuento,
            total=desglose.total
        )

        pedido.items = [
            ItemPedido(plato=p, cantidad=c, precio_unitario=p.precio, notas=n)
            for p, c, n in lineas
        ]

        # Descontar los ingredientes utilizados.
        for plato, cantidad, _ in lineas:
            descontar_stock(plato, cantidad)

        db.session.add(pedido)
        db.session.commit()
        return pedido

    except ErrorInventario as error:
        db.session.rollback()
        raise ErrorPedido(str(error))
    except Exception:
        db.session.rollback()
        raise


# ---------------------------------------------------------------- serializacion (JSON)
def pedido_a_dict(p: Pedido, ahora: datetime | None = None) -> dict:
    ahora = ahora or datetime.now()
    return {
        "id": p.id,
        "mesa": p.mesa.numero,
        "estado": p.estado,
        "comensales": p.comensales,
        "notas": p.notas,
        "subtotal": p.subtotal,
        "descuento": p.descuento,
        "total": p.total,
        "creado_en": p.creado_en.isoformat(timespec="seconds"),
        "espera_min": round(minutos_espera(_a_pedido_cocina(p), ahora), 1),
        "minutos_estimados": estimar_pedido(p, ahora),
        "items": [{"plato": i.plato.nombre, "cantidad": i.cantidad, "notas": i.notas}
                  for i in p.items],
    }


def cola_cocina(ahora: datetime | None = None) -> dict:
    """Pedidos activos agrupados por estado; los pendientes van ordenados por prioridad."""
    ahora = ahora or datetime.now()
    activos = _pedidos_activos()
    por_id = {p.id: p for p in activos}

    pendientes = [p for p in activos if p.estado == EstadoPedido.PENDIENTE.value]
    ordenados = ordenar_cola(map(_a_pedido_cocina, pendientes), ahora)

    def con_prioridad(pc: PedidoCocina) -> dict:
        d = pedido_a_dict(por_id[pc.id], ahora)
        d["prioridad"] = prioridad(pc, ahora)
        return d

    return {
        "pendientes": [con_prioridad(pc) for pc in ordenados],
        "en_preparacion": [pedido_a_dict(p, ahora) for p in activos
                           if p.estado == EstadoPedido.EN_PREPARACION.value],
        "listos": [pedido_a_dict(p, ahora) for p in activos
                   if p.estado == EstadoPedido.LISTO.value],
    }
