"""Paradigma FUNCIONAL: filtros dieteticos y alergenos.

Un "plato" aqui es un diccionario simple (ver `Plato.a_dict()`), asi las
funciones no dependen de la base de datos.  Cada filtro es un *predicado*
(plato -> bool) y se combinan con `filter` / `all`.
"""
from typing import Callable, Iterable

TIPOS_ANIMAL = frozenset({"carne", "pescado", "lacteo", "huevo"})
TIPOS_CARNE = frozenset({"carne", "pescado"})

Plato = dict
Predicado = Callable[[Plato], bool]


def _tipos(plato: Plato) -> set[str]:
    return {i["tipo"] for i in plato["ingredientes"]}


def es_vegano(plato: Plato) -> bool:
    return not (_tipos(plato) & TIPOS_ANIMAL)


def es_vegetariano(plato: Plato) -> bool:
    return not (_tipos(plato) & TIPOS_CARNE)


def sin_gluten(plato: Plato) -> bool:
    return not any(i["tiene_gluten"] for i in plato["ingredientes"])


def sin_lacteos(plato: Plato) -> bool:
    return "lacteo" not in _tipos(plato)


def sin_frutos_secos(plato: Plato) -> bool:
    return not any(i["tiene_frutos_secos"] for i in plato["ingredientes"])


FILTROS: dict[str, Predicado] = {
    "vegano": es_vegano,
    "vegetariano": es_vegetariano,
    "sin_gluten": sin_gluten,
    "sin_lacteos": sin_lacteos,
    "sin_frutos_secos": sin_frutos_secos,
}

ETIQUETAS_FILTRO = {
    "vegano": "Vegano",
    "vegetariano": "Vegetariano",
    "sin_gluten": "Sin gluten",
    "sin_lacteos": "Sin lácteos",
    "sin_frutos_secos": "Sin frutos secos",
}


def filtrar_platos(platos: Iterable[Plato], dietas: Iterable[str]) -> list[Plato]:
    """Deja solo los platos que cumplen TODAS las dietas pedidas."""
    predicados = [FILTROS[d] for d in dietas if d in FILTROS]
    return list(filter(lambda p: all(f(p) for f in predicados), platos))


def alergenos(plato: Plato) -> list[str]:
    """Alergenos presentes en el plato (para mostrar advertencias al cliente)."""
    reglas = (
        ("Gluten", lambda i: i["tiene_gluten"]),
        ("Lácteos", lambda i: i["tipo"] == "lacteo"),
        ("Huevo", lambda i: i["tipo"] == "huevo"),
        ("Pescado/mariscos", lambda i: i["tipo"] == "pescado"),
        ("Frutos secos", lambda i: i["tiene_frutos_secos"]),
    )
    return [nombre for nombre, regla in reglas if any(map(regla, plato["ingredientes"]))]


def etiquetas_dieteticas(plato: Plato) -> list[str]:
    """Etiquetas positivas: 'Vegano', 'Sin gluten', etc."""
    return [
        ETIQUETAS_FILTRO[nombre]
        for nombre in ("vegano", "vegetariano", "sin_gluten")
        if FILTROS[nombre](plato) and not (nombre == "vegetariano" and es_vegano(plato))
    ]
