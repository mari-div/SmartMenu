from datetime import datetime, timedelta

from app.funcional.cocina import (PedidoCocina, estimar_minutos_entrega, minutos_espera,
                                  ordenar_cola, prioridad, tiempo_preparacion_pedido)

AHORA = datetime(2026, 11, 13, 13, 0, 0)


def pedido(id, hace_min, prep=10, comensales=1):
    return PedidoCocina(id, AHORA - timedelta(minutes=hace_min), prep, 1, comensales)


def test_tiempo_preparacion_un_plato_y_varios():
    assert tiempo_preparacion_pedido([]) == 0
    assert tiempo_preparacion_pedido([12]) == 12
    assert tiempo_preparacion_pedido([16, 8, 4]) == 19.0   # 16 + 25% de 12


def test_minutos_espera_nunca_es_negativo():
    futuro = PedidoCocina(1, AHORA + timedelta(minutes=5), 10, 1)
    assert minutos_espera(futuro, AHORA) == 0


def test_el_que_lleva_mas_esperando_va_primero():
    cola = ordenar_cola([pedido(1, 2), pedido(2, 20), pedido(3, 8)], AHORA)
    assert [p.id for p in cola] == [2, 3, 1]


def test_bono_de_rapidez_a_igual_espera():
    cola = ordenar_cola([pedido(1, 5, prep=20), pedido(2, 5, prep=3)], AHORA)
    assert cola[0].id == 2


def test_mesas_grandes_pesan_un_poco_mas():
    assert prioridad(pedido(1, 5, comensales=6), AHORA) > prioridad(pedido(2, 5, comensales=1), AHORA)


def test_ordenar_no_modifica_la_entrada_y_es_estable():
    original = [pedido(1, 5), pedido(2, 5)]
    resultado = ordenar_cola(original, AHORA)
    assert [p.id for p in original] == [1, 2]
    assert [p.id for p in resultado] == [1, 2]


def test_estimar_entrega():
    assert estimar_minutos_entrega([], 12) == 12
    assert estimar_minutos_entrega([15, 15, 15], 10, estaciones=3) == 25
    assert estimar_minutos_entrega([30], 10, estaciones=0) == 40   # estaciones invalidas -> 1
