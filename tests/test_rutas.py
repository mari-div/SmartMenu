from app.models import Mesa, Plato


def _id(nombre):
    return Plato.query.filter_by(nombre=nombre).one().id


def test_paginas_principales(client):
    assert client.get("/").status_code == 200
    assert client.get("/cocina").status_code == 200
    assert client.get("/dashboard/").status_code == 200       # sin datos muestra un aviso
    assert client.get("/dashboard/grafico/pareto.png").status_code == 404
    assert client.get("/dashboard/grafico/otra_cosa.png").status_code == 404


def test_carta_y_filtros(client):
    mesa = Mesa.query.first()
    html = client.get(f"/mesa/{mesa.token}").get_data(as_text=True)
    assert "Hamburguesa clásica" in html and "Ensalada fresca" in html
    vegano = client.get(f"/mesa/{mesa.token}?dieta=vegano").get_data(as_text=True)
    assert "Ensalada fresca" in vegano and "Hamburguesa clásica" not in vegano
    assert client.get("/mesa/token-falso").status_code == 404


def test_carta_parcial_para_filtrar_sin_recargar(client):
    mesa = Mesa.query.first()
    parcial = client.get(f"/mesa/{mesa.token}?dieta=vegano&dieta=sin_gluten&parcial=1").get_data(as_text=True)
    assert "<html" not in parcial and "catnav" in parcial          # solo el fragmento
    assert "Papas fritas" in parcial and "Hamburguesa vegana" not in parcial   # el pan lleva gluten
    assert client.get(f"/mesa/{mesa.token}?dieta=inventada&parcial=1").status_code == 200   # filtro desconocido se ignora


def test_flujo_completo_por_api(client):
    mesa = Mesa.query.first()
    r = client.post("/api/cotizar", json={"items": [{"plato_id": _id("Gaseosa"), "cantidad": 2}]})
    assert r.status_code == 200 and r.json["subtotal"] == 4.0

    r = client.post("/api/pedidos", json={"mesa_token": mesa.token, "comensales": 2, "notas": "sin hielo",
                                          "items": [{"plato_id": _id("Pizza margarita"), "cantidad": 1}]})
    assert r.status_code == 201
    pid = r.json["id"]
    assert r.json["estado"] == "pendiente" and r.json["minutos_estimados"] > 0

    cola = client.get("/api/cocina/cola").json
    assert [p["id"] for p in cola["pendientes"]] == [pid]

    assert client.post(f"/api/pedidos/{pid}/avanzar").json["estado"] == "en_preparacion"
    assert client.post(f"/api/pedidos/{pid}/avanzar").json["estado"] == "listo"
    assert client.get(f"/api/pedidos/{pid}").json["estado"] == "listo"
    assert client.post(f"/api/pedidos/{pid}/avanzar").json["estado"] == "entregado"
    assert client.post(f"/api/pedidos/{pid}/avanzar").status_code == 409
    assert client.post(f"/api/pedidos/{pid}/cancelar").status_code == 409
    assert client.get(f"/pedido/{pid}").status_code == 200


def test_errores_de_la_api(client):
    mesa = Mesa.query.first()
    assert client.post("/api/pedidos", json={"mesa_token": "no", "items": []}).status_code == 404
    r = client.post("/api/pedidos", json={"mesa_token": mesa.token, "items": []})
    assert r.status_code == 400 and "error" in r.json
    assert client.get("/api/pedidos/999").status_code == 404
    assert client.post("/api/pedidos", data="no es json").status_code == 404
