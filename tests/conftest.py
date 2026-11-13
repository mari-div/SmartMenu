import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import create_app  # noqa: E402
from app.config import TestConfig  # noqa: E402
from app.extensions import db  # noqa: E402
from app.seed import sembrar_menu, sembrar_mesas, sembrar_usuarios  # noqa: E402

CLAVES = {"admin": "admin123", "mozo1": "mozo123", "mozo2": "mozo123", "cocina1": "cocina123"}


@pytest.fixture
def app():
    app = create_app(TestConfig)
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
