"""Paradigma FUNCIONAL: que puede hacer cada rol con un pedido (funciones puras).

La cocina prepara, el mozo entrega y el administrador puede todo.  Al ser datos
y funciones puras, las reglas se prueban sin base de datos ni servidor.
"""

# (estado_actual, estado_nuevo) permitidos por rol
TRANSICIONES_POR_ROL: dict[str, frozenset[tuple[str, str]]] = {
    "cocina": frozenset({
        ("pendiente", "en_preparacion"),
        ("en_preparacion", "listo"),
        ("pendiente", "cancelado"),
        ("en_preparacion", "cancelado"),
    }),
    "mozo": frozenset({
        ("listo", "entregado"),
        ("pendiente", "cancelado"),
    }),
    "admin": frozenset({
        ("pendiente", "en_preparacion"),
        ("en_preparacion", "listo"),
        ("listo", "entregado"),
        ("pendiente", "cancelado"),
        ("en_preparacion", "cancelado"),
    }),
}


def puede_cambiar_estado(rol: str, desde: str, hasta: str) -> bool:
    return (desde, hasta) in TRANSICIONES_POR_ROL.get(rol, frozenset())


# Pagina de inicio de cada rol (nombre de la ruta de Flask)
INICIO_POR_ROL = {"admin": "admin.resumen", "mozo": "mozo.panel", "cocina": "cocina.panel"}


def ruta_inicio(rol: str) -> str:
    return INICIO_POR_ROL.get(rol, "cliente.inicio")
