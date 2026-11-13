"""Inicio y cierre de sesion; cada rol aterriza en su propio panel."""
from urllib.parse import urlparse

from flask import Blueprint, redirect, render_template, request, url_for

from app import auth
from app.funcional.permisos import ruta_inicio
from app.models import Usuario

bp = Blueprint("auth", __name__)


def _destino_seguro(destino: str | None) -> str | None:
    """Solo se acepta volver a rutas internas (evita redirecciones a sitios externos)."""
    if destino and destino.startswith("/") and not destino.startswith("//") \
            and not urlparse(destino).netloc:
        return destino
    return None


@bp.route("/login", methods=["GET", "POST"])
def login():
    actual = auth.usuario_actual()
    if actual and request.method == "GET":
        return redirect(url_for(ruta_inicio(actual.rol)))

    error = ""
    username = ""
    if request.method == "POST":
        username = request.form.get("username", "").strip().lower()
        clave = request.form.get("password", "")
        if auth.intentos_recientes(username) >= auth.MAX_INTENTOS:
            error = "Demasiados intentos. Espera unos minutos e inténtalo de nuevo."
            auth.registrar("LOGIN_BLOQUEADO", "Demasiados intentos", username=username)
        else:
            usuario = Usuario.query.filter_by(username=username).first()
            if usuario and usuario.activo and usuario.check_password(clave):
                auth.iniciar_sesion(usuario)
                auth.registrar("LOGIN", f"Ingresó como {usuario.rol}", usuario=usuario)
                destino = _destino_seguro(request.args.get("next"))
                return redirect(destino or url_for(ruta_inicio(usuario.rol)))
            error = "Usuario o contraseña incorrectos."
            auth.registrar("LOGIN_FALLIDO", "Credenciales inválidas", username=username)
    return render_template("login.html", error=error, username=username), (401 if error else 200)


@bp.post("/logout")
def logout():
    usuario = auth.usuario_actual()
    if usuario:
        auth.registrar("LOGOUT", "", usuario=usuario)
    auth.cerrar_sesion()
    return redirect(url_for("cliente.inicio"))
