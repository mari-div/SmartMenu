"""Panel de administracion: KPIs, menu, inventario, usuarios y bitacora."""
from datetime import datetime

import pytest

from analisis.generador import generar_historial
from app.extensions import db
from app.models import Auditoria, Ingrediente, Plato, Usuario


@pytest.fixture
def admin(entrar):
    return entrar("admin")


@pytest.fixture
def con_datos(app):
    generar_historial(dias=20, pedidos_base=30, semilla=11, hasta=datetime.now())


def test_resumen_sin_ventas_no_falla(admin):
    d = admin.get("/admin/api/resumen?dias=30").json
    assert d["vacio"] is True and "vivo" in d


def test_resumen_con_kpis_y_series(admin, con_datos):
    d = admin.get("/admin/api/resumen?dias=30").json
    assert d["vacio"] is False
    k = d["kpis"]
    assert k["ingresos"] > 0 and k["pedidos"] > 0
    assert k["ticket_promedio"] == pytest.approx(k["ingresos"] / k["pedidos"], abs=0.02)
    assert 0 <= k["margen_pct"] <= 100 and 0 <= k["cancelados_pct"] <= 100
    s = d["series"]
    assert {"diarias", "horas", "dias_semana", "top_platos", "categorias", "mozos", "tiempos", "calor"} <= set(s)
    assert {m["mozo"] for m in s["mozos"]} == {"Carlos Quispe", "Lucía Ramos"}      # ventas por mozo
    assert sum(sum(f) for f in s["calor"]["valores"]) == k["pedidos"]               # el mapa de calor cuadra
    assert sum(c["ingresos"] for c in s["categorias"]) == pytest.approx(
        k["ingresos"] + k["descuentos"], rel=0.01)                                   # ventas por categoria (precio de carta)


def test_resumen_rechaza_dias_invalidos(admin):
    assert admin.get("/admin/api/resumen?dias=abc").status_code == 400


def test_todas_las_secciones_del_admin_cargan(admin, con_datos):
    for ruta in ["/admin/", "/admin/pedidos", "/admin/pedidos?estado=entregado", "/admin/menu",
                 "/admin/usuarios", "/admin/logs", "/admin/analisis", "/admin/api/vivo"]:
        assert admin.get(ruta).status_code == 200, ruta
    assert admin.get("/admin/grafico/pareto.png?tema=oscuro").mimetype == "image/png"
    assert admin.get("/admin/grafico/nada.png").status_code == 404


def test_editar_plato_precio_disponibilidad_y_foto(admin):
    p = Plato.query.filter_by(nombre="Gaseosa").one()
    r = admin.patch(f"/admin/api/platos/{p.id}", json={"precio": "7.50", "disponible": False,
                                                       "imagen_url": "https://ejemplo.com/foto.jpg"})
    assert r.status_code == 200
    db.session.refresh(p)
    assert (p.precio, p.disponible, p.imagen_url) == (7.5, False, "https://ejemplo.com/foto.jpg")
    assert Auditoria.query.filter_by(accion="PLATO_EDITADO").count() == 1


@pytest.mark.parametrize("cuerpo", [{"precio": -1}, {"precio": "abc"}, {"imagen_url": "javascript:alert(1)"}])
def test_editar_plato_valida_los_datos(admin, cuerpo):
    assert admin.patch(f"/admin/api/platos/{Plato.query.first().id}", json=cuerpo).status_code == 400


def test_reponer_stock(admin):
    ing = Ingrediente.query.filter_by(nombre="Albahaca").one()
    antes = ing.stock
    r = admin.post(f"/admin/api/ingredientes/{ing.id}/reponer", json={"cantidad": 5})
    assert r.status_code == 200 and r.json["stock"] == antes + 5
    assert admin.post(f"/admin/api/ingredientes/{ing.id}/reponer", json={"cantidad": -2}).status_code == 400


def test_crear_y_gestionar_usuarios(admin, client):
    r = admin.post("/admin/api/usuarios", json={"username": "mozo3", "nombre": "Ana Paz", "rol": "mozo", "password": "secreto1"})
    assert r.status_code == 201
    uid = r.json["id"]
    assert client.post("/login", data={"username": "mozo3", "password": "secreto1"}).status_code == 302
    assert admin.post("/admin/api/usuarios", json={"username": "mozo3", "nombre": "X", "rol": "mozo", "password": "secreto1"}).status_code == 409
    assert admin.patch(f"/admin/api/usuarios/{uid}", json={"activo": False}).status_code == 200
    assert client.post("/login", data={"username": "mozo3", "password": "secreto1"}).status_code == 401
    assert admin.patch(f"/admin/api/usuarios/{uid}", json={"password": "nueva123"}).status_code == 200


@pytest.mark.parametrize("cuerpo", [
    {"username": "A", "nombre": "X", "rol": "mozo", "password": "secreto1"},         # usuario invalido
    {"username": "valido", "nombre": "X", "rol": "dios", "password": "secreto1"},    # rol invalido
    {"username": "valido", "nombre": "X", "rol": "mozo", "password": "123"},          # clave corta
])
def test_crear_usuario_valida(admin, cuerpo):
    assert admin.post("/admin/api/usuarios", json=cuerpo).status_code == 400


def test_el_admin_no_puede_desactivarse_a_si_mismo(admin):
    yo = Usuario.query.filter_by(username="admin").one()
    assert admin.patch(f"/admin/api/usuarios/{yo.id}", json={"activo": False}).status_code == 400


def test_logs_con_filtros(admin, entrar):
    entrar("mozo1").get("/admin/")                                   # genera un ACCESO_DENEGADO
    html = admin.get("/admin/logs?accion=ACCESO_DENEGADO").get_data(as_text=True)
    assert "ACCESO_DENEGADO" in html and "mozo1" in html
    assert "mozo1" in admin.get("/admin/logs?q=mozo1").get_data(as_text=True)


def test_estado_en_vivo_detecta_stock_bajo_y_platos_no_disponibles(admin):
    ing = Ingrediente.query.filter_by(nombre="Albahaca").one()
    ing.stock = 0.1
    Plato.query.filter_by(nombre="Café").one().disponible = False
    db.session.commit()
    v = admin.get("/admin/api/vivo").json
    assert "Albahaca" in [i["nombre"] for i in v["stock_bajo"]]
    assert v["platos_no_disponibles"] == ["Café"]
