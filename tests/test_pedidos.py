from datetime import datetime, timedelta

import pytest

from app.extensions import db
from app.models import EstadoPedido, Mesa, Plato, TransicionInvalida
from app.servicios import pedidos as servicio


def _items(*pares):
    return [{"plato_id": Plato.query.filter_by(nombre=n).one().id, "cantidad": c} for n, c in pares]


def _pedido(ahora=None, *pares):
    mesa = Mesa.query.first()
    return servicio.crear_pedido(mesa, _items(*(pares or [("Hamburguesa clásica", 2)])),
                                 comensales=2, ahora=ahora or datetime(2026, 11, 13, 13, 0))


def test_crear_pedido_calcula_total_y_guarda_precio(app):
    p = _pedido(None, ("Hamburguesa clásica", 2), ("Gaseosa", 1))
    assert p.subtotal == 62.00 and p.total == 62.00 and p.descuento == 0
    assert p.estado == "pendiente"
    assert {i.precio_unitario for i in p.items} == {28.00, 6.00}


def test_happy_hour_se_aplica_por_la_hora_del_pedido(app):
    p = _pedido(datetime(2026, 11, 13, 17, 30), ("Pizza pepperoni", 2))
    assert p.subtotal == 72.0 and p.descuento == 10.80 and p.total == 61.20


def test_platos_repetidos_se_juntan(app):
    p = _pedido(None, ("Gaseosa", 1), ("Gaseosa", 2))
    assert len(p.items) == 1 and p.items[0].cantidad == 3


@pytest.mark.parametrize("items", [
    [], [{"plato_id": 9999, "cantidad": 1}], [{"plato_id": 1, "cantidad": 0}],
    [{"plato_id": 1, "cantidad": 21}], [{"plato_id": "x", "cantidad": 1}], [{"cantidad": 1}],
])
def test_pedidos_invalidos(app, items):
    with pytest.raises(servicio.ErrorPedido):
        servicio.crear_pedido(Mesa.query.first(), items)


def test_plato_no_disponible(app):
    plato = Plato.query.first()
    plato.disponible = False
    db.session.commit()
    with pytest.raises(servicio.ErrorPedido):
        servicio.crear_pedido(Mesa.query.first(), [{"plato_id": plato.id, "cantidad": 1}])


def test_flujo_de_estados_completo_registra_tiempos(app):
    p = _pedido()
    t0 = datetime(2026, 11, 13, 13, 0)
    p.avanzar(t0 + timedelta(minutes=2))
    p.avanzar(t0 + timedelta(minutes=15))
    p.avanzar(t0 + timedelta(minutes=17))
    assert p.estado == "entregado"
    assert (p.inicio_prep_en, p.listo_en, p.entregado_en) == (
        t0 + timedelta(minutes=2), t0 + timedelta(minutes=15), t0 + timedelta(minutes=17))


def test_transiciones_invalidas(app):
    p = _pedido()
    with pytest.raises(TransicionInvalida):
        p.cambiar_estado(EstadoPedido.LISTO)          # no se puede saltar la preparacion
    p.cambiar_estado(EstadoPedido.CANCELADO)
    with pytest.raises(TransicionInvalida):
        p.avanzar()                                    # un cancelado no avanza
    assert not p.puede_pasar_a(EstadoPedido.EN_PREPARACION)


def test_cola_cocina_ordena_pendientes_por_prioridad(app):
    ahora = datetime(2026, 11, 13, 13, 0)
    viejo = _pedido(ahora - timedelta(minutes=20), ("Pollo a la parrilla", 1))
    nuevo = _pedido(ahora - timedelta(minutes=1), ("Gaseosa", 1))
    en_prep = _pedido(ahora - timedelta(minutes=5), ("Papas fritas", 1))
    en_prep.avanzar(ahora)
    db.session.commit()

    cola = servicio.cola_cocina(ahora)
    assert [p["id"] for p in cola["pendientes"]] == [viejo.id, nuevo.id]
    assert [p["id"] for p in cola["en_preparacion"]] == [en_prep.id]
    assert cola["listos"] == []


def test_estimacion_crece_con_la_carga(app):
    ahora = datetime(2026, 11, 13, 13, 0)
    primero = _pedido(ahora, ("Hamburguesa clásica", 1))
    solo = servicio.estimar_pedido(primero, ahora)
    segundo = _pedido(ahora + timedelta(seconds=30), ("Hamburguesa clásica", 1))
    assert servicio.estimar_pedido(segundo, ahora + timedelta(seconds=30)) > solo
    assert servicio.estimar_pedido(primero, ahora) == solo       # no se afecta por los que llegan despues
