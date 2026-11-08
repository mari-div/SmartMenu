"""SmartMenu: fabrica de la aplicacion Flask."""
from flask import Flask

from .config import Config
from .extensions import db


def create_app(config_class=Config) -> Flask:
    app = Flask(__name__)
    app.config.from_object(config_class)
    db.init_app(app)

    from . import models  # noqa: F401  (registra las tablas)
    from .cli import registrar_comandos
    from .rutas import api, cliente, cocina, dashboard

    for modulo in (cliente, cocina, api, dashboard):
        app.register_blueprint(modulo.bp)
    registrar_comandos(app)
    return app
