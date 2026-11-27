"""Herencia y polimorfismo: las reglas de descuento son una jerarquia de clases."""
import pytest

from app.descuentos import (DescuentoGrupo, DescuentoVolumen, HappyHour, ReglaDescuento,
                            reglas_por_defecto)
from app.funcional.precios import Contexto, Linea, calcular_total, mejor_descuento


def ctx(subtotal=50.0, hora=12, comensales=2):
    return Contexto(subtotal=subtotal, unidades=2, hora=hora, comensales=comensales)


def test_las_reglas_heredan_de_la_clase_base():
    for regla in reglas_por_defecto():
        assert isinstance(regla, ReglaDescuento)


def test_la_clase_base_es_abstracta():
    with pytest.raises(TypeError):
        ReglaDescuento()                      # no se puede instanciar: falta `porcentaje`


def test_polimorfismo_misma_llamada_distinto_comportamiento():
    # Se recorren como si fueran lo mismo; cada una responde a su manera
    pedido = ctx(subtotal=200, hora=18, comensales=7)
    resultados = {type(r).__name__: r.aplicar(pedido) for r in reglas_por_defecto()}
    assert resultados["HappyHour"] == (0.15, "Happy hour")
    assert resultados["DescuentoVolumen"] == (0.08, "Consumo mayor a S/ 180")
    assert resultados["DescuentoGrupo"] == (0.10, "Descuento de grupo")


def test_una_regla_que_no_aplica_devuelve_cero_y_nombre_vacio():
    assert HappyHour().aplicar(ctx(hora=12)) == (0.0, "")
    assert DescuentoVolumen().aplicar(ctx(subtotal=10)) == (0.0, "")
    assert DescuentoGrupo().aplicar(ctx(comensales=2)) == (0.0, "")


def test_parametros_propios_de_cada_subclase():
    madrugada = HappyHour(desde=0, hasta=6, pct=0.5)
    assert madrugada.porcentaje(ctx(hora=3)) == 0.5 and madrugada.porcentaje(ctx(hora=7)) == 0
    assert DescuentoVolumen(escalones=((50, 0.2),)).porcentaje(ctx(subtotal=60)) == 0.2
    assert DescuentoGrupo(minimo=2, pct=0.05).porcentaje(ctx(comensales=2)) == 0.05


def test_agregar_una_regla_nueva_no_requiere_tocar_el_resto():
    class DescuentoCumpleanos(ReglaDescuento):
        nombre = "Cumpleaños"

        def porcentaje(self, ctx):
            return 0.20

    d = calcular_total([Linea(10, 2)], hora=12, reglas=[*reglas_por_defecto(), DescuentoCumpleanos()])
    assert d.regla_aplicada == "Cumpleaños" and d.descuento == 4.0


def test_las_reglas_son_invocables_y_se_integran_con_la_parte_funcional():
    pedido = ctx(subtotal=200, hora=18, comensales=2)
    # `mejor_descuento` (funcional) trata a los objetos como funciones
    assert mejor_descuento(reglas_por_defecto(), pedido) == (0.15, "Happy hour")
    assert HappyHour()(pedido) == HappyHour().aplicar(pedido)


def test_repr_legible():
    assert repr(HappyHour()) == "<HappyHour>"
