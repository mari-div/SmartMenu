"""API JSON usada por las paginas (carrito, cocina y seguimiento)."""

from flask import Blueprint, jsonify, request

from app.extensions import db
from app.auth import registrar, rol_requerido, usuario_actual
from app.funcional.permisos import puede_cambiar_estado
from app.models import EstadoPedido, Mesa, Pedido, Plato, TransicionInvalida
from app.models.pedido import SIGUIENTE
from app.funcional.recomendador import (
    construir_matriz_coocurrencia,
    recomendar_con_ids,
)
from app.servicios import pedidos as servicio

bp = Blueprint("api", __name__, url_prefix="/api")


@bp.errorhandler(servicio.ErrorPedido)
def _error_pedido(e):
    return jsonify(error=str(e)), 400


@bp.errorhandler(TransicionInvalida)
def _error_transicion(e):
    return jsonify(error=str(e)), 409


@bp.post("/cotizar")
@rol_requerido("mozo", "admin")
def cotizar():
    datos = request.get_json(silent=True) or {}
    items = datos.get("items", [])
    if not items:
        return jsonify(subtotal=0, descuento=0, total=0, regla_aplicada="")
    return jsonify(servicio.cotizar(items, datos.get("comensales", 1)))


@bp.post("/pedidos")
@rol_requerido("mozo", "admin")
def crear_pedido():
    """El mozo envia a cocina el pedido de una mesa."""
    datos = request.get_json(silent=True) or {}
    mesa = db.session.get(Mesa, datos.get("mesa_id")) if str(datos.get("mesa_id", "")).isdigit() else None
    if mesa is None:
        return jsonify(error="Mesa no válida"), 404
    pedido = servicio.crear_pedido(
        mesa, datos.get("items", []),
        datos.get("comensales", 1), datos.get("notas", ""),
        mozo=usuario_actual(),
    )
    registrar("PEDIDO_CREADO", f"#{pedido.id} mesa {mesa.numero} total S/ {pedido.total:.2f}")
    return jsonify(servicio.pedido_a_dict(pedido)), 201


@bp.get("/pedidos/<int:pedido_id>")
@rol_requerido("mozo", "cocina", "admin")
def ver_pedido(pedido_id: int):
    return jsonify(servicio.pedido_a_dict(db.get_or_404(Pedido, pedido_id)))


def _cambiar_estado(pedido_id: int, nuevo: EstadoPedido):
    """Aplica un cambio de estado solo si el rol del usuario puede hacerlo."""
    pedido = db.get_or_404(Pedido, pedido_id)
    usuario = usuario_actual()
    if not puede_cambiar_estado(usuario.rol, pedido.estado, nuevo.value):
        registrar("ACCESO_DENEGADO", f"#{pedido.id}: {pedido.estado} -> {nuevo.value}")
        return jsonify(error=f"Tu rol ({usuario.rol}) no puede pasar el pedido de "
                             f"'{pedido.estado}' a '{nuevo.value}'"), 403
    anterior = pedido.estado
    pedido.cambiar_estado(nuevo)
    db.session.commit()
    registrar("PEDIDO_ESTADO", f"#{pedido.id} mesa {pedido.mesa.numero}: {anterior} -> {nuevo.value}")
    return jsonify(servicio.pedido_a_dict(pedido))


@bp.post("/pedidos/<int:pedido_id>/avanzar")
@rol_requerido("mozo", "cocina", "admin")
def avanzar(pedido_id: int):
    pedido = db.get_or_404(Pedido, pedido_id)
    siguiente = SIGUIENTE.get(pedido.estado_enum)
    if siguiente is None:
        raise TransicionInvalida(f"El pedido en '{pedido.estado}' ya no puede avanzar")
    return _cambiar_estado(pedido_id, siguiente)


@bp.post("/pedidos/<int:pedido_id>/cancelar")
@rol_requerido("mozo", "cocina", "admin")
def cancelar(pedido_id: int):
    return _cambiar_estado(pedido_id, EstadoPedido.CANCELADO)


@bp.get("/cocina/cola")
@rol_requerido("cocina", "admin")
def cola():
    return jsonify(servicio.cola_cocina())


@bp.get("/mozo/panel")
@rol_requerido("mozo", "admin")
def panel_mozo():
    return jsonify(servicio.panel_mozo(usuario_actual()))


@bp.get("/seguimiento/<token>")
def seguimiento(token: str):
    """PUBLICO: el cliente consulta su pedido con el codigo del QR."""
    pedido = Pedido.query.filter_by(token=token).first()
    if pedido is None:
        return jsonify(error="Pedido no encontrado"), 404
    return jsonify(servicio.pedido_publico_dict(pedido))


# ---------------------------------------------------------------- recomendaciones
@bp.get("/recomendaciones/<int:plato_id>")
@rol_requerido("mozo", "admin")
def recomendaciones(plato_id: int):
    """Recomienda platos que suelen pedirse junto con el plato indicado."""

    plato = db.session.get(Plato, plato_id)
    if plato is None:
        return jsonify(error="Plato no encontrado"), 404

    try:
        n = int(request.args.get("n", 5))
        if n < 0:
            return jsonify(error="n debe ser mayor o igual a cero"), 400
    except (TypeError, ValueError):
        return jsonify(error="n debe ser un número entero"), 400

    platos = Plato.query.order_by(Plato.id).all()
    plato_ids = [p.id for p in platos]

    pedidos_entregados = Pedido.query.filter_by(
        estado=EstadoPedido.ENTREGADO.value
    ).all()

    pedidos = [
        [item.plato_id for item in pedido.items]
        for pedido in pedidos_entregados
    ]

    matriz = construir_matriz_coocurrencia(pedidos, plato_ids)

    ids_recomendados = recomendar_con_ids(
        plato_id, matriz, plato_ids, n
    )

    platos_por_id = {p.id: p for p in platos}

    return jsonify({
        "plato_id": plato_id,
        "recomendaciones": [
            platos_por_id[id_recomendado].a_dict()
            for id_recomendado in ids_recomendados
        ]
    })

