"""Pantalla de cocina."""
from flask import Blueprint, render_template

bp = Blueprint("cocina", __name__)


@bp.get("/cocina")
def panel():
    return render_template("cocina.html")
