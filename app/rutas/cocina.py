"""Pantalla de cocina: recibe los pedidos de los mozos y los va preparando."""
from flask import Blueprint, render_template

from app.auth import rol_requerido, usuario_actual

bp = Blueprint("cocina", __name__)


@bp.get("/cocina")
@rol_requerido("cocina", "admin")
def panel():
    return render_template("cocina.html", rol=usuario_actual().rol)
