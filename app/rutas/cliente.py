"""Vistas del cliente: carta digital (a la que se llega con el QR) y seguimiento."""
from flask import Blueprint, abort, render_template, request

from app.extensions import db
from app.funcional.filtros import (ETIQUETAS_FILTRO, alergenos, etiquetas_dieteticas,
                                   filtrar_platos)
from app.models import Categoria, Mesa, Pedido

bp = Blueprint("cliente", __name__)


@bp.get("/")
def inicio():
    """Pagina de demostracion: lista las mesas con su enlace (el que ira en el QR)."""
    mesas = Mesa.query.order_by(Mesa.numero).all()
    return render_template("index.html", mesas=mesas)


@bp.get("/mesa/<token>")
def carta(token: str):
    mesa = Mesa.query.filter_by(token=token).first_or_404()
    dietas = [d for d in request.args.getlist("dieta") if d in ETIQUETAS_FILTRO]

    secciones = []
    for categoria in Categoria.query.order_by(Categoria.orden).all():
        platos = [p.a_dict() for p in categoria.platos if p.disponible]
        platos = filtrar_platos(platos, dietas)
        for p in platos:  # datos extra solo para mostrar en pantalla
            p["alergenos"] = alergenos(p)
            p["etiquetas"] = etiquetas_dieteticas(p)
        if platos:
            secciones.append({"nombre": categoria.nombre, "platos": platos})

    # ?parcial=1 devuelve solo la lista de platos (el JS la intercambia sin recargar la pagina)
    plantilla = "_secciones.html" if request.args.get("parcial") else "carta.html"
    return render_template(plantilla, mesa=mesa, secciones=secciones,
                           filtros=ETIQUETAS_FILTRO, dietas_activas=dietas)


@bp.get("/pedido/<int:pedido_id>")
def seguimiento(pedido_id: int):
    pedido = db.get_or_404(Pedido, pedido_id)
    return render_template("pedido.html", pedido=pedido)
