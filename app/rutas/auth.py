"""Inicio y cierre de sesion; cada rol aterriza en su propio panel."""
from urllib.parse import urlparse

from flask import Blueprint, jsonify, redirect, render_template, request, url_for

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


@bp.get("/cuenta")
@auth.login_requerido
def cuenta():
    return render_template("cuenta.html")


@bp.post("/api/cuenta/clave")
@auth.login_requerido
def cambiar_clave():
    """Cada usuario cambia su propia contraseña (debe conocer la actual)."""
    datos = request.get_json(silent=True) or {}
    usuario = auth.usuario_actual()
    actual, nueva = str(datos.get("actual", "")), str(datos.get("nueva", ""))
    if not usuario.check_password(actual):
        auth.registrar("CLAVE_RECHAZADA", "Contraseña actual incorrecta")
        return jsonify(error="La contraseña actual no es correcta"), 400
    if len(nueva) < 8:
        return jsonify(error="La nueva contraseña debe tener al menos 8 caracteres"), 400
    if nueva == actual:
        return jsonify(error="La nueva contraseña debe ser distinta a la actual"), 400
    usuario.set_password(nueva)
    from app.extensions import db
    db.session.commit()
    auth.registrar("CLAVE_CAMBIADA", "El usuario cambió su propia contraseña")
    return jsonify(ok=True)
