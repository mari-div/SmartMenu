import pytest

from app.funcional.precios import (Contexto, Linea, calcular_total, componer, descuento_grupo,
                                   descuento_volumen, dividir_cuenta, happy_hour,
                                   mejor_descuento, propina_sugerida, subtotal)


def test_subtotal():
    assert subtotal([Linea(2.5, 2), Linea(10, 1)]) == 15.0
    assert subtotal([]) == 0.0


def test_sin_descuento():
    d = calcular_total([Linea(10, 1)], hora=15)
    assert (d.subtotal, d.descuento, d.total, d.regla_aplicada) == (10.0, 0.0, 10.0, "")


def test_happy_hour():
    d = calcular_total([Linea(10, 2)], hora=17)
    assert d.descuento == 3.0 and d.total == 17.0 and d.regla_aplicada == "Happy hour"
    assert happy_hour(Contexto(20, 2, hora=19))[0] == 0  # a las 19:00 ya termino


def test_descuento_por_volumen():
    assert descuento_volumen(Contexto(29.99, 3, 15))[0] == 0
    assert descuento_volumen(Contexto(30, 3, 15))[0] == 0.05
    assert descuento_volumen(Contexto(50, 3, 15))[0] == 0.08


def test_descuento_grupo():
    assert descuento_grupo(Contexto(10, 1, 15, comensales=6))[0] == 0.10
    assert descuento_grupo(Contexto(10, 1, 15, comensales=5))[0] == 0


def test_los_descuentos_no_se_acumulan_gana_el_mayor():
    # hora feliz (15%) + volumen (8%) + grupo (10%) -> solo 15%
    d = calcular_total([Linea(20, 3)], hora=18, comensales=6)
    assert d.descuento == 9.0 and d.regla_aplicada == "Happy hour"
    assert mejor_descuento([], Contexto(1, 1, 1)) == (0.0, "")


def test_propina():
    assert propina_sugerida(33.33) == 3.33
    assert propina_sugerida(100, 0.15) == 15.0


@pytest.mark.parametrize("total,personas", [(10, 3), (100, 7), (0.05, 2), (33.33, 4)])
def test_dividir_cuenta_no_pierde_centavos(total, personas):
    partes = dividir_cuenta(total, personas)
    assert len(partes) == personas
    assert round(sum(partes), 2) == total
    assert max(partes) - min(partes) <= 0.01


def test_dividir_cuenta_invalida():
    with pytest.raises(ValueError):
        dividir_cuenta(10, 0)


def test_componer_va_de_izquierda_a_derecha():
    f = componer(lambda x: x + 1, lambda x: x * 10)
    assert f(2) == 30


def test_funciones_puras_no_modifican_sus_datos():
    lineas = [Linea(5, 2)]
    calcular_total(lineas, 12)
    assert lineas == [Linea(5, 2)]
