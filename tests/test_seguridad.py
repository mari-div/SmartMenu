"""Proteccion CSRF y cambio de contraseña propia."""
import re

import pytest

from app.models import Auditoria, Usuario


def _token_de(html: str) -> str:
    return re.search(r'name="csrf-token" content="([0-9a-f]+)"', html).group(1)


# ---------------------------------------------------------------- CSRF
def test_el_servidor_rechaza_un_post_sin_token(app):
    c = app.test_client()
    c.sin_csrf = True
    r = c.post("/login", data={"username": "admin", "password": "admin123"})
    assert r.status_code == 403
    assert c.get("/admin/").status_code == 302                       # y no inicio sesion


def test_un_token_falso_tambien_se_rechaza(app):
    c = app.test_client()
    c.get("/login")                                                   # crea la sesion con su token real
    c.sin_csrf = True
    r = c.post("/login", data={"username": "admin", "password": "admin123", "csrf_token": "falso"})
    assert r.status_code == 403


def test_el_formulario_de_login_incluye_el_token_y_funciona(app):
    c = app.test_client()
    c.sin_csrf = True
    token = _token_de(c.get("/login").get_data(as_text=True))
    r = c.post("/login", data={"username": "admin", "password": "admin123", "csrf_token": token})
    assert r.status_code == 302


def test_la_api_rechaza_un_post_sin_token_con_json(entrar):
    c = entrar("mozo1")
    c.sin_csrf = True
    r = c.post("/api/cotizar", json={"items": []})
    assert r.status_code == 403 and "error" in r.json


def test_la_api_acepta_el_token_en_la_cabecera(entrar):
    c = entrar("mozo1")
    c.sin_csrf = True
    token = _token_de(c.get("/mozo/").get_data(as_text=True))
    r = c.post("/api/cotizar", json={"items": []}, headers={"X-CSRF-Token": token})
    assert r.status_code == 200


def test_los_get_no_necesitan_token(entrar):
    c = entrar("admin")
    c.sin_csrf = True
    assert c.get("/admin/api/vivo").status_code == 200


def test_las_paginas_publicas_del_cliente_tambien_llevan_token(app):
    # el cliente (sin cuenta) tambien hace POST (avisos, calificacion): necesita su token
    from app.extensions import db
    from app.models import Mesa, Pedido
    pedido = Pedido(mesa=Mesa.query.first(), total=10, subtotal=10)
    db.session.add(pedido)
    db.session.commit()
    c = app.test_client()
    assert re.search(r'name="csrf-token" content="[0-9a-f]+"', c.get(f"/seguimiento/{pedido.token}").get_data(as_text=True))


# ---------------------------------------------------------------- cambio de contraseña
def test_pagina_mi_cuenta_requiere_sesion(client):
    assert client.get("/cuenta").status_code == 302


def test_cambiar_la_propia_clave(entrar, app):
    c = entrar("mozo1")
    r = c.post("/api/cuenta/clave", json={"actual": "mozo123", "nueva": "NuevaClave9"})
    assert r.status_code == 200
    assert Usuario.query.filter_by(username="mozo1").one().check_password("NuevaClave9")
    assert Auditoria.query.filter_by(accion="CLAVE_CAMBIADA", username="mozo1").count() == 1
    # la clave vieja ya no sirve y la nueva si
    otro = app.test_client()
    assert otro.post("/login", data={"username": "mozo1", "password": "mozo123"}).status_code == 401
    assert otro.post("/login", data={"username": "mozo1", "password": "NuevaClave9"}).status_code == 302


@pytest.mark.parametrize("cuerpo,fragmento", [
    ({"actual": "mala", "nueva": "NuevaClave9"}, "actual no es correcta"),
    ({"actual": "mozo123", "nueva": "corta"}, "al menos 8"),
])
def test_cambio_de_clave_valida(entrar, cuerpo, fragmento):
    r = entrar("mozo1").post("/api/cuenta/clave", json=cuerpo)
    assert r.status_code == 400 and fragmento in r.json["error"]


def test_un_visitante_no_puede_cambiar_claves(client):
    assert client.post("/api/cuenta/clave", json={"actual": "x", "nueva": "yyyyyyyy"}).status_code == 401


def test_la_nueva_clave_debe_ser_distinta_a_la_actual(entrar):
    c = entrar("mozo1")
    assert c.post("/api/cuenta/clave", json={"actual": "mozo123", "nueva": "ClaveLarga123"}).status_code == 200
    r = c.post("/api/cuenta/clave", json={"actual": "ClaveLarga123", "nueva": "ClaveLarga123"})
    assert r.status_code == 400 and "distinta" in r.json["error"]
