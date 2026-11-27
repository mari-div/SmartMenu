"""Datos JSON del análisis interactivo (matriz y predicción)."""
from datetime import datetime

import pandas as pd
import pytest

from analisis import metricas
from analisis.generador import generar_historial


@pytest.fixture
def admin(entrar):
    return entrar("admin")


@pytest.fixture
def con_datos(app):
    generar_historial(dias=20, pedidos_base=30, semilla=11, hasta=datetime.now())


def test_filtrar_periodo_por_dias_y_categoria():
    df = pd.DataFrame({
        "plato": ["Pizza", "Pizza", "Gaseosa"],
        "categoria": ["Comida", "Comida", "Bebida"],
        "creado_en": pd.to_datetime(["2026-11-01 13:00", "2026-11-10 13:00", "2026-11-10 14:00"]),
    })
    assert len(metricas.filtrar_periodo(df)) == 3
    assert len(metricas.filtrar_periodo(df, dias=3)) == 2          # solo el 10 de noviembre
    assert metricas.filtrar_periodo(df, categoria="Bebida")["plato"].tolist() == ["Gaseosa"]


def test_api_matriz_devuelve_clasificaciones(admin, con_datos):
    d = admin.get("/admin/api/analisis/matriz").json
    assert d["platos"] and d["categorias"]
    assert {p["clasificacion"] for p in d["platos"]} <= {"Estrella", "Vaca", "Puzzle", "Perro"}
    assert d["mediana_unidades"] > 0


def test_api_matriz_filtra_por_categoria(admin, con_datos):
    categoria = admin.get("/admin/api/analisis/matriz").json["categorias"][0]
    d = admin.get(f"/admin/api/analisis/matriz?categoria={categoria}").json
    assert d["platos"] and {p["categoria"] for p in d["platos"]} == {categoria}


def test_api_prediccion_trae_historial_y_siete_dias(admin, con_datos):
    d = admin.get("/admin/api/analisis/prediccion").json
    assert d["plato"] == d["platos"][0]            # por defecto, el más vendido
    assert len(d["prediccion"]) == 7 and d["historial"]
    otro = d["platos"][1]
    assert admin.get(f"/admin/api/analisis/prediccion?plato={otro}").json["plato"] == otro


def test_api_analisis_sin_datos_no_falla(admin):
    assert admin.get("/admin/api/analisis/matriz").json["platos"] == []
    assert admin.get("/admin/api/analisis/prediccion").json["plato"] is None


def test_api_analisis_exige_ser_admin(entrar):
    assert entrar("mozo1").get("/admin/api/analisis/matriz").status_code == 403


def test_la_pagina_de_analisis_trae_los_graficos_interactivos(admin, con_datos):
    html = admin.get("/admin/analisis").get_data(as_text=True)
    assert 'id="c-matriz"' in html and 'id="c-pred"' in html
    assert "admin_interactivo.js" in html
