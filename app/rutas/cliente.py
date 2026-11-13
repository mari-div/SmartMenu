"""Lo que ve el cliente: portada y seguimiento de su pedido (se entra con el QR)."""
import io

import qrcode
import qrcode.image.svg
from flask import Blueprint, Response, abort, current_app, render_template, request, url_for

from app.models import Pedido

bp = Blueprint("cliente", __name__)


@bp.get("/")
def inicio():
    return render_template("index.html")


@bp.get("/seguimiento/<token>")
def seguimiento(token: str):
    """Pagina publica: solo conoce el pedido quien tenga el codigo secreto del QR."""
    pedido = Pedido.query.filter_by(token=token).first_or_404()
    return render_template("pedido.html", pedido=pedido)


def url_seguimiento(pedido: Pedido) -> str:
    base = current_app.config.get("BASE_URL") or request.url_root.rstrip("/")
    return base + url_for("cliente.seguimiento", token=pedido.token)


@bp.get("/qr/<token>.svg")
def qr(token: str):
    pedido = Pedido.query.filter_by(token=token).first()
    if pedido is None:
        abort(404)
    imagen = qrcode.make(url_seguimiento(pedido), image_factory=qrcode.image.svg.SvgPathImage,
                         box_size=10, border=2)
    buffer = io.BytesIO()
    imagen.save(buffer)
    return Response(buffer.getvalue(), mimetype="image/svg+xml",
                    headers={"Cache-Control": "private, max-age=3600"})
