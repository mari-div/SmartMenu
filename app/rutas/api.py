"""API JSON usada por las paginas (carrito, cocina y seguimiento)."""
from flask import Blueprint, jsonify, request

from app.extensions import db
from app.models import EstadoPedido, Mesa, Pedido, TransicionInvalida
from app.servicios import pedidos as servicio

bp = Blueprint("api", __name__, url_prefix="/api")


@bp.errorhandler(servicio.ErrorPedido)
def _error_pedido(e):
    return jsonify(error=str(e)), 400


@bp.errorhandler(TransicionInvalida)
def _error_transicion(e):
    return jsonify(error=str(e)), 409


@bp.post("/cotizar")
def cotizar():
    datos = request.get_json(silent=True) or {}
    items = datos.get("items", [])
    if not items:  # carrito vacio: todo en cero
        return jsonify(subtotal=0, descuento=0, total=0, regla_aplicada="")
    return jsonify(servicio.cotizar(items, datos.get("comensales", 1)))


@bp.post("/pedidos")
def crear_pedido():
    datos = request.get_json(silent=True) or {}
    mesa = Mesa.query.filter_by(token=str(datos.get("mesa_token", ""))).first()
    if mesa is None:
        return jsonify(error="Mesa no válida"), 404
    pedido = servicio.crear_pedido(mesa, datos.get("items", []),
                                   datos.get("comensales", 1), datos.get("notas", ""))
    return jsonify(servicio.pedido_a_dict(pedido)), 201


@bp.get("/pedidos/<int:pedido_id>")
def ver_pedido(pedido_id: int):
    return jsonify(servicio.pedido_a_dict(db.get_or_404(Pedido, pedido_id)))


@bp.post("/pedidos/<int:pedido_id>/avanzar")
def avanzar(pedido_id: int):
    pedido = db.get_or_404(Pedido, pedido_id)
    pedido.avanzar()
    db.session.commit()
    return jsonify(servicio.pedido_a_dict(pedido))


@bp.post("/pedidos/<int:pedido_id>/cancelar")
def cancelar(pedido_id: int):
    pedido = db.get_or_404(Pedido, pedido_id)
    pedido.cambiar_estado(EstadoPedido.CANCELADO)
    db.session.commit()
    return jsonify(servicio.pedido_a_dict(pedido))


@bp.get("/cocina/cola")
def cola():
    return jsonify(servicio.cola_cocina())
