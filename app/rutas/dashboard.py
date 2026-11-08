"""Panel de analitica para el dueño (usa el paquete `analisis`: pandas + numpy + matplotlib)."""
from flask import Blueprint, Response, abort, render_template, request

from analisis import graficos, metricas
from analisis.datos import cargar_ventas
from analisis.limpieza import limpiar_ventas
from app.extensions import db

bp = Blueprint("dashboard", __name__, url_prefix="/dashboard")


def _datos_limpios():
    bruto = cargar_ventas(db.engine)
    if bruto.empty:
        return None, {}
    return limpiar_ventas(bruto)


@bp.get("/")
def panel():
    limpio, informe = _datos_limpios()
    if limpio is None:
        return render_template("dashboard.html", kpis=None, informe={}, top=[], graficos=[])
    return render_template(
        "dashboard.html", kpis=metricas.kpis(limpio), informe=informe,
        top=metricas.top_platos(limpio, 5).round(2).to_dict("records"),
        graficos=list(graficos.GRAFICOS))


@bp.get("/grafico/<nombre>.png")
def grafico(nombre: str):
    funcion = graficos.GRAFICOS.get(nombre)
    if funcion is None:
        abort(404)
    limpio, _ = _datos_limpios()
    if limpio is None:
        abort(404)
    oscuro = request.args.get("tema") == "oscuro"       # ?tema=oscuro para el modo oscuro
    return Response(graficos.a_png(funcion(limpio), oscuro=oscuro, sin_titulo=True),
                    mimetype="image/png")
