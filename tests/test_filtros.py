from app.funcional.filtros import (alergenos, es_vegano, es_vegetariano, etiquetas_dieteticas,
                                   filtrar_platos, sin_gluten)
from app.models import Plato


def _plato(app, nombre):
    return Plato.query.filter_by(nombre=nombre).one().a_dict()


def test_clasificacion_de_platos(app):
    assert es_vegano(_plato(app, "Ensalada fresca"))
    assert not es_vegano(_plato(app, "Pasta alfredo"))           # lleva crema y queso
    assert es_vegetariano(_plato(app, "Pasta alfredo"))
    assert not es_vegetariano(_plato(app, "Hamburguesa clásica"))
    assert sin_gluten(_plato(app, "Papas fritas"))
    assert not sin_gluten(_plato(app, "Pizza margarita"))


def test_alergenos(app):
    assert alergenos(_plato(app, "Brownie con helado")) == ["Gluten", "Lácteos", "Huevo", "Frutos secos"]
    assert alergenos(_plato(app, "Ensalada fresca")) == []


def test_etiquetas(app):
    assert etiquetas_dieteticas(_plato(app, "Ensalada fresca")) == ["Vegano", "Sin gluten"]
    assert etiquetas_dieteticas(_plato(app, "Pizza vegetariana")) == ["Vegetariano"]


def test_filtrar_combinando_dietas(app):
    platos = [p.a_dict() for p in Plato.query.all()]
    veganos_sin_gluten = {p["nombre"] for p in filtrar_platos(platos, ["vegano", "sin_gluten"])}
    assert "Ensalada fresca" in veganos_sin_gluten
    assert "Papas fritas" in veganos_sin_gluten
    assert "Hamburguesa vegana" not in veganos_sin_gluten        # el pan tiene gluten
    assert len(filtrar_platos(platos, [])) == len(platos)         # sin filtros: todo
    assert len(filtrar_platos(platos, ["dieta_inexistente"])) == len(platos)
