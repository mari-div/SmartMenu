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
from app.servicios import avisos as servicio_avisos
from app.servicios import cobros
from app.servicios import pedidos as servicio
from app.servicios import recomendaciones as servicio_recs
from app.servicios.avisos import ErrorAviso
from app.servicios.cobros import ErrorCobro

bp = Blueprint("api", __name__, url_prefix="/api")


@bp.errorhandler(servicio.ErrorPedido)
def _error_pedido(e):
    return jsonify(error=str(e)), 400


@bp.errorhandler(ErrorCobro)
@bp.errorhandler(ErrorAviso)
def _error_negocio(e):
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
    if nuevo is EstadoPedido.CANCELADO:
        servicio.reponer_inventario(pedido)            # los ingredientes vuelven al inventario
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


@bp.post("/pedidos/<int:pedido_id>/items")
@rol_requerido("mozo", "admin")
def agregar_items(pedido_id: int):
    """El mozo suma platos a un pedido que la cocina aun no termino."""
    pedido = db.get_or_404(Pedido, pedido_id)
    datos = request.get_json(silent=True) or {}
    servicio.agregar_items(pedido, datos.get("items", []))
    registrar("PEDIDO_ITEMS", f"#{pedido.id} mesa {pedido.mesa.numero}: se agregaron platos, "
                              f"nuevo total S/ {pedido.total:.2f}")
    return jsonify(servicio.pedido_a_dict(pedido))


@bp.post("/pedidos/<int:pedido_id>/cobrar")
@rol_requerido("mozo", "admin")
def cobrar(pedido_id: int):
    """Registra el pago (metodo y propina) de un pedido entregado y libera la mesa."""
    pedido = db.get_or_404(Pedido, pedido_id)
    datos = request.get_json(silent=True) or {}
    cobros.cobrar(pedido, str(datos.get("metodo", "")), datos.get("propina", 0))
    db.session.commit()
    registrar("PEDIDO_COBRADO", f"#{pedido.id} mesa {pedido.mesa.numero}: S/ {pedido.total:.2f} "
                                f"+ propina S/ {pedido.propina:.2f} ({pedido.metodo_pago})")
    return jsonify(servicio.pedido_a_dict(pedido))


@bp.post("/avisos/<int:aviso_id>/atender")
@rol_requerido("mozo", "admin")
def atender_aviso(aviso_id: int):
    from app.models import Aviso
    aviso = db.get_or_404(Aviso, aviso_id)
    usuario = usuario_actual()
    if usuario.rol == "mozo" and aviso.pedido.mozo_id != usuario.id:
        return jsonify(error="Ese aviso es de otro mozo"), 403
    aviso.atender()
    db.session.commit()
    registrar("AVISO_ATENDIDO", f"mesa {aviso.pedido.mesa.numero}: {aviso.tipo}")
    return jsonify(ok=True)


# ---------------------------------------------------------------- cliente (publico, con el codigo del QR)
def _pedido_por_token(token: str):
    return Pedido.query.filter_by(token=token).first()


@bp.post("/seguimiento/<token>/avisar")
def avisar(token: str):
    """PUBLICO: el cliente llama al mozo o pide la cuenta desde su QR."""
    pedido = _pedido_por_token(token)
    if pedido is None:
        return jsonify(error="Pedido no encontrado"), 404
    tipo = str((request.get_json(silent=True) or {}).get("tipo", ""))
    aviso, nuevo = servicio_avisos.crear_aviso(pedido, tipo)
    db.session.commit()
    if nuevo:
        registrar("AVISO_CLIENTE", f"mesa {pedido.mesa.numero}: {tipo} (pedido #{pedido.id})", username="cliente")
    return jsonify(servicio.pedido_publico_dict(pedido)), (201 if nuevo else 200)


@bp.post("/seguimiento/<token>/calificar")
def calificar(token: str):
    """PUBLICO: el cliente califica su pedido (1 a 5 estrellas) una sola vez."""
    pedido = _pedido_por_token(token)
    if pedido is None:
        return jsonify(error="Pedido no encontrado"), 404
    datos = request.get_json(silent=True) or {}
    servicio_avisos.calificar(pedido, datos.get("estrellas"), datos.get("comentario", ""))
    db.session.commit()
    registrar("CALIFICACION", f"pedido #{pedido.id}: {pedido.calificacion} estrellas", username="cliente")
    return jsonify(servicio.pedido_publico_dict(pedido))


@bp.get("/seguimiento/<token>/cuenta")
def cuenta(token: str):
    """PUBLICO: simula como se divide la cuenta entre varias personas (con propina opcional)."""
    pedido = _pedido_por_token(token)
    if pedido is None:
        return jsonify(error="Pedido no encontrado"), 404
    return jsonify(cobros.cuenta_dividida(pedido.total, request.args.get("personas", 1),
                                          request.args.get("propina", 0)))


@bp.get("/sugerencias/<int:plato_id>")
@rol_requerido("mozo", "admin")
def sugerencias(plato_id: int):
    """Platos que suelen pedirse junto con este (para la carta del mozo)."""
    excluir = {int(x) for x in request.args.get("excluir", "").split(",") if x.isdigit()}
    if request.args.get("pedido", "").isdigit():             # modo "agregar": tampoco repetir lo ya pedido
        existente = db.session.get(Pedido, int(request.args["pedido"]))
        if existente:
            excluir |= {i.plato_id for i in existente.items}
    platos = servicio_recs.sugerencias(plato_id, n=3, excluir=excluir | {plato_id})
    return jsonify([{"id": p.id, "nombre": p.nombre, "precio": float(p.precio),
                     "imagen_url": p.imagen_url or ""} for p in platos])


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
    matriz, plato_ids = servicio_recs._matriz()      # matriz en cache (se recalcula cada 5 min)

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

