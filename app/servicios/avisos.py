"""Avisos del cliente (llamar al mozo / pedir la cuenta) y su calificacion del servicio."""
from datetime import datetime

from app.models import TIPOS_AVISO, Aviso, Pedido, Usuario


class ErrorAviso(ValueError):
    """Datos invalidos en un aviso o una calificacion (error 400 para el cliente)."""


def crear_aviso(pedido: Pedido, tipo: str, ahora: datetime | None = None) -> tuple[Aviso, bool]:
    """Crea el aviso. Devuelve (aviso, es_nuevo): si ya habia uno pendiente del mismo tipo no se duplica."""
    if tipo not in TIPOS_AVISO:
        raise ErrorAviso("Tipo de aviso no válido")
    if pedido.estado == "cancelado":
        raise ErrorAviso("Este pedido fue cancelado")
    if pedido.pagado:
        raise ErrorAviso("Este pedido ya fue pagado")
    if tipo == "cuenta" and pedido.estado != "entregado":
        raise ErrorAviso("Podrás pedir la cuenta cuando te entreguen tu pedido")
    pendiente = next((a for a in pedido.avisos if a.pendiente and a.tipo == tipo), None)
    if pendiente:
        return pendiente, False
    aviso = Aviso(pedido=pedido, tipo=tipo, creado_en=ahora or datetime.now())
    pedido.avisos.append(aviso)
    return aviso, True


def avisos_pendientes(usuario: Usuario, ahora: datetime | None = None) -> list[dict]:
    """Avisos sin atender: del mozo dueño del pedido (el admin ve todos)."""
    ahora = ahora or datetime.now()
    consulta = Aviso.query.join(Pedido).filter(Aviso.atendido_en.is_(None)).order_by(Aviso.creado_en)
    if usuario.rol != "admin":
        consulta = consulta.filter(Pedido.mozo_id == usuario.id)
    return [{"id": a.id, "tipo": a.tipo, "etiqueta": TIPOS_AVISO[a.tipo], "mesa": a.pedido.mesa.numero,
             "pedido": a.pedido_id, "hace_min": round((ahora - a.creado_en).total_seconds() / 60, 1)}
            for a in consulta.all()]


def calificar(pedido: Pedido, estrellas, comentario: str = "", ahora: datetime | None = None) -> Pedido:
    """El cliente califica su pedido una sola vez, cuando ya lo recibio."""
    if pedido.estado != "entregado":
        raise ErrorAviso("Podrás calificar cuando recibas tu pedido")
    if pedido.calificacion is not None:
        raise ErrorAviso("Ya calificaste este pedido. ¡Gracias!")
    try:
        estrellas = int(estrellas)
    except (TypeError, ValueError):
        raise ErrorAviso("Elige de 1 a 5 estrellas")
    if not 1 <= estrellas <= 5:
        raise ErrorAviso("Elige de 1 a 5 estrellas")
    pedido.calificacion = estrellas
    pedido.comentario_cliente = " ".join(str(comentario or "").split())[:255] or None
    pedido.calificado_en = ahora or datetime.now()
    return pedido
