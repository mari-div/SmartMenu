"""Panel del mozo: toma pedidos en la mesa, recibe el aviso de cocina y entrega."""
from flask import Blueprint, abort, render_template, request

from app.auth import rol_requerido, usuario_actual
from app.extensions import db
from app.funcional.filtros import (ETIQUETAS_FILTRO, alergenos, etiquetas_dieteticas,
                                   filtrar_platos)
from app.models import Categoria, Mesa, Pedido
from app.rutas.cliente import url_seguimiento

bp = Blueprint("mozo", __name__, url_prefix="/mozo")


@bp.get("/")
@rol_requerido("mozo", "admin")
def panel():
    return render_template("mozo.html", usuario=usuario_actual())


@bp.get("/mesa/<int:mesa_id>")
@rol_requerido("mozo", "admin")
def tomar_pedido(mesa_id: int):
    """Carta con carrito: el mozo arma el pedido de la mesa."""
    mesa = db.get_or_404(Mesa, mesa_id)
    dietas = [d for d in request.args.getlist("dieta") if d in ETIQUETAS_FILTRO]

    secciones = []
    for categoria in Categoria.query.order_by(Categoria.orden).all():
        platos = [p.a_dict() for p in categoria.platos if p.disponible]
        platos = filtrar_platos(platos, dietas)
        for p in platos:
            p["alergenos"] = alergenos(p)
            p["etiquetas"] = etiquetas_dieteticas(p)
        if platos:
            secciones.append({"nombre": categoria.nombre, "platos": platos})

    # ?parcial=1 devuelve solo la lista de platos (el JS filtra sin recargar la pagina)
    plantilla = "_secciones.html" if request.args.get("parcial") else "carta.html"
    return render_template(plantilla, mesa=mesa, secciones=secciones,
                           filtros=ETIQUETAS_FILTRO, dietas_activas=dietas)


@bp.get("/pedido/<int:pedido_id>")
@rol_requerido("mozo", "admin")
def pedido_enviado(pedido_id: int):
    """Confirmacion con el QR que se le entrega al cliente."""
    pedido = db.get_or_404(Pedido, pedido_id)
    return render_template("pedido_enviado.html", pedido=pedido, url=url_seguimiento(pedido))
