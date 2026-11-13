"""Login, roles, permisos y bitacora."""
import pytest

from app.funcional.permisos import puede_cambiar_estado, ruta_inicio
from app.models import Auditoria, Mesa, Pedido, Plato, Usuario


# ---------------------------------------------------------------- funciones puras
@pytest.mark.parametrize("rol,desde,hasta,esperado", [
    ("cocina", "pendiente", "en_preparacion", True),
    ("cocina", "en_preparacion", "listo", True),
    ("cocina", "listo", "entregado", False),        # entregar es del mozo
    ("mozo", "listo", "entregado", True),
    ("mozo", "pendiente", "en_preparacion", False),  # cocinar es de la cocina
    ("mozo", "en_preparacion", "cancelado", False),
    ("admin", "pendiente", "en_preparacion", True),
    ("admin", "listo", "entregado", True),
    ("cliente", "pendiente", "cancelado", False),
    ("cocina", "entregado", "listo", False),
])
def test_permisos_por_rol(rol, desde, hasta, esperado):
    assert puede_cambiar_estado(rol, desde, hasta) is esperado


def test_cada_rol_aterriza_en_su_panel():
    assert ruta_inicio("admin") == "admin.resumen"
    assert ruta_inicio("mozo") == "mozo.panel"
    assert ruta_inicio("cocina") == "cocina.panel"
    assert ruta_inicio("otro") == "cliente.inicio"


# ---------------------------------------------------------------- login
@pytest.mark.parametrize("usuario,clave,destino", [
    ("admin", "admin123", "/admin/"),
    ("mozo1", "mozo123", "/mozo/"),
    ("cocina1", "cocina123", "/cocina"),
])
def test_login_deriva_cada_usuario_a_su_panel(client, usuario, clave, destino):
    r = client.post("/login", data={"username": usuario, "password": clave})
    assert r.status_code == 302 and r.headers["Location"].endswith(destino)


def test_login_incorrecto(client):
    r = client.post("/login", data={"username": "admin", "password": "mala"})
    assert r.status_code == 401 and "incorrectos" in r.get_data(as_text=True)
    assert client.get("/admin/").status_code == 302          # sigue sin sesion


def test_las_claves_se_guardan_con_hash(app):
    u = Usuario.query.filter_by(username="admin").one()
    assert u.password_hash != "admin123" and u.password_hash.startswith(("scrypt:", "pbkdf2:"))
    assert u.check_password("admin123") and not u.check_password("otra")


def test_usuario_desactivado_no_entra(app, client):
    Usuario.query.filter_by(username="mozo2").one().activo = False
    from app.extensions import db
    db.session.commit()
    assert client.post("/login", data={"username": "mozo2", "password": "mozo123"}).status_code == 401


def test_bloqueo_tras_varios_intentos_fallidos(client):
    for _ in range(5):
        client.post("/login", data={"username": "mozo1", "password": "x"})
    r = client.post("/login", data={"username": "mozo1", "password": "mozo123"})   # ni con la clave buena
    assert r.status_code == 401 and "Demasiados intentos" in r.get_data(as_text=True)


def test_logout_cierra_la_sesion(entrar):
    c = entrar("mozo1")
    assert c.get("/mozo/").status_code == 200
    assert c.post("/logout").status_code == 302
    assert c.get("/mozo/").status_code == 302


def test_next_solo_acepta_rutas_internas(client):
    r = client.post("/login?next=https://malo.com", data={"username": "mozo1", "password": "mozo123"})
    assert r.headers["Location"].endswith("/mozo/")
    r = client.post("/login?next=//malo.com", data={"username": "mozo1", "password": "mozo123"})
    assert r.headers["Location"].endswith("/mozo/")


# ---------------------------------------------------------------- acceso por rol
@pytest.mark.parametrize("ruta", ["/mozo/", "/cocina", "/admin/", "/admin/usuarios", "/admin/logs"])
def test_sin_sesion_se_pide_login(client, ruta):
    r = client.get(ruta)
    assert r.status_code == 302 and "/login" in r.headers["Location"]


@pytest.mark.parametrize("ruta", ["/api/cocina/cola", "/api/mozo/panel", "/admin/api/resumen"])
def test_api_sin_sesion_da_401(client, ruta):
    assert client.get(ruta).status_code == 401


@pytest.mark.parametrize("usuario,ruta,codigo", [
    ("mozo1", "/cocina", 403), ("mozo1", "/admin/", 403), ("mozo1", "/mozo/", 200),
    ("cocina1", "/mozo/", 403), ("cocina1", "/admin/", 403), ("cocina1", "/cocina", 200),
    ("admin", "/mozo/", 200), ("admin", "/cocina", 200), ("admin", "/admin/", 200),
])
def test_matriz_de_acceso(entrar, usuario, ruta, codigo):
    assert entrar(usuario).get(ruta).status_code == codigo


def test_la_cocina_no_puede_crear_pedidos_ni_el_mozo_ver_la_cola(entrar):
    mesa = Mesa.query.first()
    cuerpo = {"mesa_id": mesa.id, "items": [{"plato_id": Plato.query.first().id, "cantidad": 1}]}
    assert entrar("cocina1").post("/api/pedidos", json=cuerpo).status_code == 403
    assert entrar("mozo1").get("/api/cocina/cola").status_code == 403


def test_el_acceso_denegado_queda_en_la_bitacora(entrar):
    entrar("mozo1").get("/admin/")
    assert Auditoria.query.filter_by(accion="ACCESO_DENEGADO", username="mozo1").count() == 1


def test_la_bitacora_registra_login_pedido_y_cambios(entrar):
    mozo, cocina = entrar("mozo1"), entrar("cocina1")
    mesa = Mesa.query.first()
    pid = mozo.post("/api/pedidos", json={"mesa_id": mesa.id, "items": [
        {"plato_id": Plato.query.first().id, "cantidad": 1}]}).json["id"]
    cocina.post(f"/api/pedidos/{pid}/avanzar")
    acciones = [a.accion for a in Auditoria.query.order_by(Auditoria.id)]
    assert acciones.count("LOGIN") == 2 and "PEDIDO_CREADO" in acciones and "PEDIDO_ESTADO" in acciones
    assert Pedido.query.get(pid).mozo.username == "mozo1"          # el pedido guarda quien lo tomo


def test_mozo_puede_cancelar_solo_pendientes(entrar):
    mozo, cocina = entrar("mozo1"), entrar("cocina1")
    mesa = Mesa.query.first()
    items = [{"plato_id": Plato.query.first().id, "cantidad": 1}]
    a = mozo.post("/api/pedidos", json={"mesa_id": mesa.id, "items": items}).json["id"]
    b = mozo.post("/api/pedidos", json={"mesa_id": mesa.id, "items": items}).json["id"]
    assert mozo.post(f"/api/pedidos/{a}/cancelar").json["estado"] == "cancelado"
    cocina.post(f"/api/pedidos/{b}/avanzar")
    assert mozo.post(f"/api/pedidos/{b}/cancelar").status_code == 403   # ya esta cocinandose
