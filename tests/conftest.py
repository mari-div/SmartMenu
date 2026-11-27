import secrets
import sys
from pathlib import Path

import pytest
from flask.testing import FlaskClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import create_app  # noqa: E402
from app.config import TestConfig  # noqa: E402
from app.extensions import db  # noqa: E402
from app.seed import sembrar_menu, sembrar_mesas, sembrar_usuarios  # noqa: E402
from app.servicios import recomendaciones, tiempos  # noqa: E402

CLAVES = {"admin": "admin123", "mozo1": "mozo123", "mozo2": "mozo123", "cocina1": "cocina123"}


class ClienteConCsrf(FlaskClient):
    """Cliente de pruebas que, como el navegador, manda el token CSRF en cada POST/PATCH/DELETE.

    Poner `cliente.sin_csrf = True` lo desactiva (para probar que el servidor rechaza peticiones sin token).
    """
    sin_csrf = False

    def open(self, *args, **kwargs):
        metodo = str(kwargs.get("method", "GET")).upper()
        if not self.sin_csrf and metodo not in ("GET", "HEAD", "OPTIONS"):
            with self.session_transaction() as sesion:
                token = sesion.setdefault("csrf", secrets.token_hex(16))
            cabeceras = dict(kwargs.get("headers") or {})
            cabeceras.setdefault("X-CSRF-Token", token)
            kwargs["headers"] = cabeceras
        return super().open(*args, **kwargs)


@pytest.fixture(autouse=True)
def _sin_cache():
    """Las caches de tiempos y recomendaciones viven en memoria: se limpian entre pruebas."""
    tiempos.reiniciar_cache()
    recomendaciones.reiniciar_cache()
    yield


@pytest.fixture
def app():
    app = create_app(TestConfig)
    app.test_client_class = ClienteConCsrf
    with app.app_context():
        db.create_all()
        sembrar_menu()
        sembrar_mesas(3)
        sembrar_usuarios()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Cliente SIN sesion (como un visitante o un cliente del restaurante)."""
    return app.test_client()


@pytest.fixture
def entrar(app):
    """Devuelve una funcion que crea un cliente con la sesion de ese usuario iniciada."""
    def _entrar(username: str):
        c = app.test_client()
        r = c.post("/login", data={"username": username, "password": CLAVES[username]})
        assert r.status_code == 302, f"No se pudo iniciar sesion como {username}"
        return c
    return _entrar
