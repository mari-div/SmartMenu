"""SmartMenu: fabrica de la aplicacion Flask."""
from flask import Flask, jsonify, render_template, request

from .config import Config
from .extensions import db


def create_app(config_class=Config) -> Flask:
    app = Flask(__name__)
    app.config.from_object(config_class)
    db.init_app(app)

    from . import models  # noqa: F401  (registra las tablas)
    from .auth import usuario_actual
    from .cli import registrar_comandos
    from .models import ETIQUETA_ROL
    from .rutas import admin, api, auth, cliente, cocina, mozo

    for modulo in (cliente, auth, mozo, cocina, api, admin):
        app.register_blueprint(modulo.bp)
    registrar_comandos(app)

    @app.context_processor
    def datos_comunes():
        """Disponible en todas las plantillas: usuario actual y moneda."""
        usuario = usuario_actual()
        return {"usuario": usuario, "etiqueta_rol": ETIQUETA_ROL.get(usuario.rol) if usuario else "",
                "MONEDA": "S/"}

    @app.errorhandler(404)
    def no_encontrado(e):
        if request.path.startswith("/api/"):
            return jsonify(error="No encontrado"), 404
        return render_template("404.html"), 404

    @app.after_request
    def cabeceras_seguridad(resp):
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        resp.headers.setdefault("X-Frame-Options", "DENY")
        resp.headers.setdefault("Referrer-Policy", "same-origin")
        return resp

    return app
