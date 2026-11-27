"""Cobro, avisos del cliente, calificacion, agregar platos, stock al cancelar, tiempos y exportacion."""
from datetime import datetime

import pytest

from analisis.generador import generar_historial
from app.extensions import db
from app.funcional.cocina import factor_ajuste
from app.models import Auditoria, Ingrediente, Mesa, Pedido, Plato
from app.servicios import pedidos as servicio
from app.servicios import tiempos


def _plato(nombre):
    return Plato.query.filter_by(nombre=nombre).one()


def _items(*pares):
    return [{"plato_id": _plato(n).id, "cantidad": c} for n, c in pares]


def _crear(mozo, *pares, mesa=None):
    mesa = mesa or Mesa.query.first()
    r = mozo.post("/api/pedidos", json={"mesa_id": mesa.id, "comensales": 2,
                                        "items": _items(*(pares or [("Pizza margarita", 1)]))})
    assert r.status_code == 201, r.json
    return r.json


def _entregar(cocina, mozo, pid):
    cocina.post(f"/api/pedidos/{pid}/avanzar")
    cocina.post(f"/api/pedidos/{pid}/avanzar")
    assert mozo.post(f"/api/pedidos/{pid}/avanzar").json["estado"] == "entregado"


def _stock(nombre):
    return Ingrediente.query.filter_by(nombre=nombre).one().stock


# ---------------------------------------------------------------- stock al cancelar
def test_cancelar_devuelve_los_ingredientes_al_inventario(entrar):
    mozo = entrar("mozo1")
    antes = _stock("Jarabe de gaseosa")
    pid = _crear(mozo, ("Gaseosa", 2))["id"]
    db.session.expire_all()
    assert _stock("Jarabe de gaseosa") == pytest.approx(antes - 0.3)       # se descuenta al pedir
    assert mozo.post(f"/api/pedidos/{pid}/cancelar").json["estado"] == "cancelado"
    db.session.expire_all()
    assert _stock("Jarabe de gaseosa") == pytest.approx(antes)             # y se repone al cancelar


# ---------------------------------------------------------------- agregar platos a un pedido
def test_agregar_platos_recalcula_total_e_inventario(entrar):
    mozo = entrar("mozo1")
    pedido = _crear(mozo, ("Gaseosa", 1))
    assert pedido["total"] == 6.0
    antes = _stock("Harina de trigo")
    r = mozo.post(f"/api/pedidos/{pedido['id']}/items", json={"items": _items(("Pizza margarita", 1), ("Gaseosa", 1))})
    assert r.status_code == 200
    assert r.json["subtotal"] == 44.0                                      # 2 gaseosas (12) + pizza (32)
    assert sorted(i["cantidad"] for i in r.json["items"]) == [1, 2]
    db.session.expire_all()
    assert _stock("Harina de trigo") < antes                               # la pizza descuenta ingredientes
    assert Auditoria.query.filter_by(accion="PEDIDO_ITEMS").count() == 1


def test_no_se_puede_agregar_cuando_ya_esta_listo(entrar):
    mozo, cocina = entrar("mozo1"), entrar("cocina1")
    pid = _crear(mozo)["id"]
    cocina.post(f"/api/pedidos/{pid}/avanzar")
    cocina.post(f"/api/pedidos/{pid}/avanzar")                             # listo
    r = mozo.post(f"/api/pedidos/{pid}/items", json={"items": _items(("Gaseosa", 1))})
    assert r.status_code == 400 and "no esté listo" in r.json["error"]


def test_agregar_valida_los_platos(entrar):
    mozo = entrar("mozo1")
    pid = _crear(mozo)["id"]
    assert mozo.post(f"/api/pedidos/{pid}/items", json={"items": []}).status_code == 400
    assert mozo.post(f"/api/pedidos/{pid}/items", json={"items": [{"plato_id": 9999, "cantidad": 1}]}).status_code == 400
    assert entrar("cocina1").post(f"/api/pedidos/{pid}/items", json={"items": _items(("Gaseosa", 1))}).status_code == 403


def test_la_carta_en_modo_agregar_solo_vale_para_pedidos_abiertos(entrar):
    mozo = entrar("mozo1")
    pedido = _crear(mozo)
    mesa_id = Mesa.query.first().id
    html = mozo.get(f"/mozo/mesa/{mesa_id}?pedido={pedido['id']}").get_data(as_text=True)
    assert f"Agregando al pedido #{pedido['id']}" in html and f'data-pedido-id="{pedido["id"]}"' in html
    assert "Agregando al pedido" not in mozo.get(f"/mozo/mesa/{mesa_id}?pedido=9999").get_data(as_text=True)


# ---------------------------------------------------------------- cobro y cierre de mesa
def test_cobrar_libera_la_mesa(entrar):
    mozo, cocina = entrar("mozo1"), entrar("cocina1")
    pedido = _crear(mozo, ("Pizza margarita", 1))
    mesa_id = Mesa.query.first().id
    _entregar(cocina, mozo, pedido["id"])

    panel = mozo.get("/api/mozo/panel").json                               # entregado pero sin cobrar
    assert [p["id"] for p in panel["por_cobrar"]] == [pedido["id"]]
    assert next(m for m in panel["mesas"] if m["id"] == mesa_id)["estado"] == "por_cobrar"

    r = mozo.post(f"/api/pedidos/{pedido['id']}/cobrar", json={"metodo": "yape", "propina": 0.1})
    assert r.status_code == 200 and r.json["pagado"] and r.json["propina"] == 3.2
    panel = mozo.get("/api/mozo/panel").json
    assert panel["por_cobrar"] == []
    assert next(m for m in panel["mesas"] if m["id"] == mesa_id)["estado"] == "libre"
    assert Auditoria.query.filter_by(accion="PEDIDO_COBRADO").count() == 1


@pytest.mark.parametrize("cuerpo", [{"metodo": "bitcoin"}, {"metodo": "efectivo", "propina": 0.9},
                                    {"metodo": "efectivo", "propina": "mucha"}, {}])
def test_cobrar_valida_metodo_y_propina(entrar, cuerpo):
    mozo, cocina = entrar("mozo1"), entrar("cocina1")
    pid = _crear(mozo)["id"]
    _entregar(cocina, mozo, pid)
    assert mozo.post(f"/api/pedidos/{pid}/cobrar", json=cuerpo).status_code == 400


def test_solo_se_cobra_lo_entregado_y_una_sola_vez(entrar):
    mozo, cocina = entrar("mozo1"), entrar("cocina1")
    pid = _crear(mozo)["id"]
    assert mozo.post(f"/api/pedidos/{pid}/cobrar", json={"metodo": "efectivo"}).status_code == 400   # aun en cocina
    _entregar(cocina, mozo, pid)
    assert mozo.post(f"/api/pedidos/{pid}/cobrar", json={"metodo": "efectivo"}).status_code == 200
    assert mozo.post(f"/api/pedidos/{pid}/cobrar", json={"metodo": "efectivo"}).status_code == 400   # ya cobrado
    assert entrar("cocina1").post(f"/api/pedidos/{pid}/cobrar", json={"metodo": "efectivo"}).status_code == 403


# ---------------------------------------------------------------- avisos del cliente
def test_el_cliente_llama_al_mozo_y_el_mozo_lo_atiende(entrar, client):
    mozo = entrar("mozo1")
    pedido = _crear(mozo)
    url = f"/api/seguimiento/{pedido['token']}/avisar"

    r = client.post(url, json={"tipo": "mozo"})                            # el cliente NO tiene sesion
    assert r.status_code == 201 and r.json["avisos_pendientes"] == ["mozo"]
    assert client.post(url, json={"tipo": "mozo"}).status_code == 200       # no se duplica

    avisos = mozo.get("/api/mozo/panel").json["avisos"]
    assert len(avisos) == 1 and avisos[0]["tipo"] == "mozo" and avisos[0]["mesa"] == 1
    assert entrar("mozo2").post(f"/api/avisos/{avisos[0]['id']}/atender").status_code == 403   # es de otro mozo
    assert mozo.post(f"/api/avisos/{avisos[0]['id']}/atender").status_code == 200
    assert mozo.get("/api/mozo/panel").json["avisos"] == []
    assert client.get(f"/api/seguimiento/{pedido['token']}").json["avisos_pendientes"] == []


def test_pedir_la_cuenta_solo_despues_de_recibir_el_pedido(entrar, client):
    mozo, cocina = entrar("mozo1"), entrar("cocina1")
    pedido = _crear(mozo)
    url = f"/api/seguimiento/{pedido['token']}/avisar"
    assert client.post(url, json={"tipo": "cuenta"}).status_code == 400
    _entregar(cocina, mozo, pedido["id"])
    assert client.post(url, json={"tipo": "cuenta"}).status_code == 201
    assert client.get(f"/api/seguimiento/{pedido['token']}").json["puede_pedir_cuenta"] is True
    # al cobrar, el aviso de la cuenta se cierra solo
    mozo.post(f"/api/pedidos/{pedido['id']}/cobrar", json={"metodo": "tarjeta"})
    assert mozo.get("/api/mozo/panel").json["avisos"] == []
    assert client.post(url, json={"tipo": "mozo"}).status_code == 400       # ya pagado


@pytest.mark.parametrize("cuerpo", [{"tipo": "otro"}, {}])
def test_aviso_invalido(entrar, client, cuerpo):
    pedido = _crear(entrar("mozo1"))
    assert client.post(f"/api/seguimiento/{pedido['token']}/avisar", json=cuerpo).status_code == 400


def test_avisos_con_codigo_inexistente(client):
    assert client.post("/api/seguimiento/falso/avisar", json={"tipo": "mozo"}).status_code == 404
    assert client.post("/api/seguimiento/falso/calificar", json={"estrellas": 5}).status_code == 404
    assert client.get("/api/seguimiento/falso/cuenta").status_code == 404


def test_el_admin_ve_todos_los_avisos_y_el_mozo_solo_los_suyos(entrar, client):
    pedido = _crear(entrar("mozo1"))
    client.post(f"/api/seguimiento/{pedido['token']}/avisar", json={"tipo": "mozo"})
    assert len(entrar("admin").get("/api/mozo/panel").json["avisos"]) == 1
    assert entrar("mozo2").get("/api/mozo/panel").json["avisos"] == []


# ---------------------------------------------------------------- calificacion
def test_el_cliente_califica_una_sola_vez_y_solo_al_recibir(entrar, client):
    mozo, cocina = entrar("mozo1"), entrar("cocina1")
    pedido = _crear(mozo)
    url = f"/api/seguimiento/{pedido['token']}/calificar"
    assert client.post(url, json={"estrellas": 5}).status_code == 400       # aun no lo recibe
    _entregar(cocina, mozo, pedido["id"])
    assert client.get(f"/api/seguimiento/{pedido['token']}").json["puede_calificar"] is True
    assert client.post(url, json={"estrellas": 7}).status_code == 400
    assert client.post(url, json={"estrellas": "x"}).status_code == 400
    r = client.post(url, json={"estrellas": 4, "comentario": "  Muy   rico\n\n  todo  "})
    assert r.status_code == 200 and r.json["calificacion"] == 4 and r.json["puede_calificar"] is False
    assert db.session.get(Pedido, pedido["id"]).comentario_cliente == "Muy rico todo"      # se limpian espacios
    assert client.post(url, json={"estrellas": 5}).status_code == 400       # ya califico


def test_el_comentario_se_guarda_como_texto_no_como_html(entrar, client):
    mozo, cocina = entrar("mozo1"), entrar("cocina1")
    pedido = _crear(mozo)
    _entregar(cocina, mozo, pedido["id"])
    client.post(f"/api/seguimiento/{pedido['token']}/calificar",
                json={"estrellas": 5, "comentario": "<script>alert(1)</script>"})
    html = entrar("admin").get("/admin/pedidos").get_data(as_text=True)
    assert "<script>alert(1)</script>" not in html


# ---------------------------------------------------------------- dividir la cuenta
def test_dividir_la_cuenta_no_pierde_centavos(entrar, client):
    pedido = _crear(entrar("mozo1"), ("Pizza margarita", 1), ("Gaseosa", 1))            # S/ 38.00
    d = client.get(f"/api/seguimiento/{pedido['token']}/cuenta?personas=3&propina=0.1").json
    assert d["total"] == 38.0 and d["propina"] == 3.8 and d["total_con_propina"] == 41.8
    assert round(sum(d["partes"]), 2) == 41.8 and len(d["partes"]) == 3
    assert max(d["partes"]) - min(d["partes"]) <= 0.01


@pytest.mark.parametrize("consulta", ["personas=0", "personas=99", "personas=abc", "personas=2&propina=0.9"])
def test_dividir_la_cuenta_valida(entrar, client, consulta):
    pedido = _crear(entrar("mozo1"))
    assert client.get(f"/api/seguimiento/{pedido['token']}/cuenta?{consulta}").status_code == 400


# ---------------------------------------------------------------- recomendador en la carta
def test_sugerencias_segun_lo_que_se_pide_junto(entrar):
    generar_historial(dias=25, pedidos_base=30, semilla=3, hasta=datetime.now())
    mozo = entrar("mozo1")
    hamburguesa = _plato("Hamburguesa clásica").id
    r = mozo.get(f"/api/sugerencias/{hamburguesa}")
    assert r.status_code == 200 and 1 <= len(r.json) <= 3
    assert hamburguesa not in [p["id"] for p in r.json]                      # nunca se sugiere a si mismo
    primero = r.json[0]["id"]
    sin_el = mozo.get(f"/api/sugerencias/{hamburguesa}?excluir={primero}").json
    assert primero not in [p["id"] for p in sin_el]                           # respeta lo que ya esta en el pedido
    assert mozo.get("/api/sugerencias/99999").json == []
    assert entrar("cocina1").get(f"/api/sugerencias/{hamburguesa}").status_code == 403


def test_el_endpoint_de_recomendaciones_sigue_funcionando_con_cache(entrar):
    generar_historial(dias=10, pedidos_base=25, semilla=5, hasta=datetime.now())
    r = entrar("mozo1").get(f"/api/recomendaciones/{_plato('Pizza pepperoni').id}?n=3")
    assert r.status_code == 200 and len(r.json["recomendaciones"]) <= 3


# ---------------------------------------------------------------- tiempo estimado dinamico (historial)
def test_factor_ajuste_es_una_funcion_pura_robusta():
    assert factor_ajuste([1.2] * 5) == 1.0                                    # pocas muestras: sin ajuste
    assert factor_ajuste([1.3] * 20) == 1.3
    assert factor_ajuste([1.3] * 19 + [50.0]) == 1.3                          # un valor raro no cambia la mediana
    assert factor_ajuste([5.0] * 20) == 2.0 and factor_ajuste([0.1] * 20) == 0.6   # limites
    assert factor_ajuste([]) == 1.0


def test_los_factores_se_aprenden_del_historial(app):
    generar_historial(dias=30, pedidos_base=40, semilla=2, hasta=datetime.now())
    factores = tiempos.calcular_factores()
    assert factores and all(0.6 <= f <= 2.0 for f in factores.values())
    assert set(factores) <= set(range(11, 23))                                # solo horas de atencion


def test_la_estimacion_usa_el_factor_del_historial(entrar, monkeypatch):
    mozo = entrar("mozo1")
    pedido = db.session.get(Pedido, _crear(mozo, ("Pizza margarita", 1))["id"])
    ahora = datetime(2026, 11, 13, 13, 0)
    pedido.creado_en = ahora
    monkeypatch.setattr(tiempos, "factor_para", lambda hora, ahora=None: 1.0)
    base = servicio.estimar_pedido(pedido, ahora)
    monkeypatch.setattr(tiempos, "factor_para", lambda hora, ahora=None: 1.5)
    assert servicio.estimar_pedido(pedido, ahora) == pytest.approx(base * 1.5, abs=0.2)


# ---------------------------------------------------------------- generador: cobros y calificaciones simulados
def test_el_historial_simulado_incluye_pagos_propinas_y_calificaciones(app):
    generar_historial(dias=15, pedidos_base=30, semilla=9, hasta=datetime.now())
    entregados = Pedido.query.filter_by(estado="entregado").all()
    assert entregados and all(p.pagado_en and p.metodo_pago for p in entregados)
    assert any(p.propina > 0 for p in entregados)
    calificados = [p for p in entregados if p.calificacion]
    assert calificados and all(1 <= p.calificacion <= 5 for p in calificados)
    assert not any(p.pagado_en for p in Pedido.query.filter_by(estado="cancelado"))


# ---------------------------------------------------------------- admin: metricas nuevas y exportacion
@pytest.fixture
def con_datos(app):
    generar_historial(dias=20, pedidos_base=30, semilla=11, hasta=datetime.now())


def test_el_resumen_incluye_propinas_satisfaccion_y_pagos(entrar, con_datos):
    d = entrar("admin").get("/admin/api/resumen?dias=30").json
    k = d["kpis"]
    assert k["propinas"] > 0 and 1 <= k["satisfaccion"] <= 5 and k["calificaciones_n"] > 0
    assert {p["metodo_pago"] for p in d["series"]["pagos"]} <= {"efectivo", "tarjeta", "yape", "plin"}
    assert [c["estrellas"] for c in d["series"]["calificaciones"]] == [1, 2, 3, 4, 5]
    assert sum(c["cantidad"] for c in d["series"]["calificaciones"]) == k["calificaciones_n"]
    assert all(c["comentario_cliente"] for c in d["series"]["comentarios"])
    assert {"por_cobrar", "avisos_pendientes"} <= set(d["vivo"])


def test_exportar_csv_de_ventas_y_pedidos(entrar, con_datos):
    admin = entrar("admin")
    ventas = admin.get("/admin/export/ventas.csv?dias=30")
    assert ventas.status_code == 200 and ventas.mimetype == "text/csv"
    assert "attachment" in ventas.headers["Content-Disposition"]
    cuerpo = ventas.get_data(as_text=True)
    assert cuerpo.startswith("﻿") and "plato" in cuerpo.splitlines()[0] and len(cuerpo.splitlines()) > 100
    pedidos = admin.get("/admin/export/pedidos.csv?dias=7").get_data(as_text=True)
    assert "total_s" in pedidos.splitlines()[0] and "propina_s" in pedidos.splitlines()[0]
    assert Auditoria.query.filter_by(accion="EXPORTACION").count() == 2


def test_exportar_valida_y_protege(entrar, con_datos):
    assert entrar("admin").get("/admin/export/otra.csv").status_code == 404
    assert entrar("admin").get("/admin/export/ventas.csv?dias=abc").status_code == 400
    assert entrar("mozo1").get("/admin/export/ventas.csv").status_code == 403


def test_exportar_sin_datos_no_falla(entrar):
    r = entrar("admin").get("/admin/export/ventas.csv")
    assert r.status_code == 200


def test_en_modo_agregar_no_se_sugiere_lo_que_ya_esta_en_el_pedido(entrar):
    generar_historial(dias=25, pedidos_base=30, semilla=3, hasta=datetime.now())
    mozo = entrar("mozo1")
    pedido = _crear(mozo, ("Hamburguesa clásica", 1), ("Papas fritas", 1))
    gaseosa = _plato("Gaseosa").id
    sin_filtro = [p["id"] for p in mozo.get(f"/api/sugerencias/{gaseosa}").json]
    con_pedido = [p["id"] for p in mozo.get(f"/api/sugerencias/{gaseosa}?pedido={pedido['id']}").json]
    assert not {_plato("Hamburguesa clásica").id, _plato("Papas fritas").id} & set(con_pedido)
    assert sin_filtro                                                           # sin el pedido si hay sugerencias
