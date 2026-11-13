from app.models import Mesa, Pedido, Plato


def _id(nombre):
    return Plato.query.filter_by(nombre=nombre).one().id


def _crear(mozo, nombre="Pizza margarita", cantidad=1, mesa=None):
    mesa = mesa or Mesa.query.first()
    return mozo.post("/api/pedidos", json={"mesa_id": mesa.id, "comensales": 2, "notas": "sin hielo",
                                           "items": [{"plato_id": _id(nombre), "cantidad": cantidad}]})


def test_paginas_publicas(client):
    assert client.get("/").status_code == 200
    assert client.get("/login").status_code == 200
    assert client.get("/seguimiento/codigo-falso").status_code == 404
    assert client.get("/qr/codigo-falso.svg").status_code == 404


def test_la_carta_ya_no_es_publica(client):
    # El cliente no pide por su cuenta: el pedido lo toma el mozo
    assert client.get("/mesa/loquesea").status_code == 404


def test_el_mozo_ve_la_carta_con_fotos_y_soles(entrar):
    mozo = entrar("mozo1")
    mesa = Mesa.query.first()
    html = mozo.get(f"/mozo/mesa/{mesa.id}").get_data(as_text=True)
    assert "Hamburguesa clásica" in html and "S/ 28.00" in html
    assert "images.unsplash.com" in html                       # fotos de internet
    vegano = mozo.get(f"/mozo/mesa/{mesa.id}?dieta=vegano").get_data(as_text=True)
    assert "Ensalada fresca" in vegano and "Hamburguesa clásica" not in vegano


def test_carta_parcial_para_filtrar_sin_recargar(entrar):
    mozo = entrar("mozo1")
    mesa = Mesa.query.first()
    parcial = mozo.get(f"/mozo/mesa/{mesa.id}?dieta=vegano&dieta=sin_gluten&parcial=1").get_data(as_text=True)
    assert "<html" not in parcial and "catnav" in parcial
    assert "Papas fritas" in parcial and "Hamburguesa vegana" not in parcial
    assert mozo.get(f"/mozo/mesa/{mesa.id}?dieta=inventada&parcial=1").status_code == 200


def test_cotizar_en_soles(entrar):
    mozo = entrar("mozo1")
    r = mozo.post("/api/cotizar", json={"items": [{"plato_id": _id("Gaseosa"), "cantidad": 2}]})
    assert r.status_code == 200 and r.json["subtotal"] == 12.0


def test_flujo_completo_mozo_cocina_mozo_cliente(entrar, client):
    mozo, cocina = entrar("mozo1"), entrar("cocina1")

    # 1) el mozo toma el pedido
    r = _crear(mozo)
    assert r.status_code == 201
    pid, token = r.json["id"], r.json["token"]
    assert r.json["mozo"] == "Carlos Quispe" and r.json["estado"] == "pendiente"

    # 2) el cliente (sin sesion) lo sigue con el codigo del QR
    seg = client.get(f"/api/seguimiento/{token}")
    assert seg.status_code == 200 and seg.json["estado"] == "pendiente"
    assert "id" not in seg.json and "token" not in seg.json     # no se filtran datos internos

    # 3) la cocina lo ve y lo prepara
    assert [p["id"] for p in cocina.get("/api/cocina/cola").json["pendientes"]] == [pid]
    assert cocina.post(f"/api/pedidos/{pid}/avanzar").json["estado"] == "en_preparacion"
    assert cocina.post(f"/api/pedidos/{pid}/avanzar").json["estado"] == "listo"

    # 4) el mozo recibe el aviso (pedido listo) y lo entrega; la cocina NO puede entregar
    panel = mozo.get("/api/mozo/panel").json
    assert [p["id"] for p in panel["pedidos"] if p["estado"] == "listo"] == [pid]
    assert cocina.post(f"/api/pedidos/{pid}/avanzar").status_code == 403
    assert mozo.post(f"/api/pedidos/{pid}/avanzar").json["estado"] == "entregado"

    # 5) el cliente ve el estado final
    assert client.get(f"/api/seguimiento/{token}").json["estado"] == "entregado"
    assert client.get(f"/seguimiento/{token}").status_code == 200


def test_el_qr_es_un_svg_con_la_direccion_del_pedido(entrar, client):
    token = _crear(entrar("mozo1")).json["token"]
    r = client.get(f"/qr/{token}.svg")
    assert r.status_code == 200 and r.mimetype == "image/svg+xml" and b"<svg" in r.data
    enviado = entrar("mozo1").get(f"/mozo/pedido/{Pedido.query.one().id}").get_data(as_text=True)
    assert f"/qr/{token}.svg" in enviado and f"/seguimiento/{token}" in enviado


def test_errores_de_la_api(entrar):
    mozo = entrar("mozo1")
    assert mozo.post("/api/pedidos", json={"mesa_id": 9999, "items": []}).status_code == 404
    r = mozo.post("/api/pedidos", json={"mesa_id": Mesa.query.first().id, "items": []})
    assert r.status_code == 400 and "error" in r.json
    assert mozo.get("/api/pedidos/999").status_code == 404
    assert mozo.get("/api/seguimiento/x").status_code == 404
