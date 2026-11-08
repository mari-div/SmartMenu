from datetime import datetime

import numpy as np
import pandas as pd
import pytest

from analisis import graficos, metricas
from analisis.datos import cargar_ventas
from analisis.generador import generar_historial
from analisis.limpieza import limpiar_ventas
from analisis.reporte import generar_reporte
from app.extensions import db
from app.models import Pedido

HASTA = datetime(2026, 11, 13)


@pytest.fixture
def limpio(app):
    generar_historial(dias=21, pedidos_base=30, semilla=7, hasta=HASTA)
    return limpiar_ventas(cargar_ventas(db.engine))


def test_generador_es_reproducible(app):
    n1 = generar_historial(dias=5, pedidos_base=20, semilla=1, hasta=HASTA)
    db.session.query(Pedido).delete()
    db.session.commit()
    n2 = generar_historial(dias=5, pedidos_base=20, semilla=1, hasta=HASTA)
    assert n1 == n2 > 0


def test_limpieza_excluye_cancelados_y_marca_datos_sucios(limpio):
    df, informe = limpio
    assert (df["estado"] != "cancelado").all()
    assert informe["pedidos_cancelados"] > 0
    assert informe["pedidos_validos"] == informe["pedidos_iniciales"] - informe["pedidos_cancelados"]
    assert informe["pedidos_sin_tiempos"] >= 0 and informe["pedidos_con_tiempo_atipico"] >= 0
    # los atipicos quedan anulados (NaN), no eliminados
    assert df.loc[df["tiempo_atipico"], "prep_real_min"].isna().all()


def test_columnas_derivadas(limpio):
    df, _ = limpio
    assert np.allclose(df["ingreso_linea"], df["cantidad"] * df["precio_unitario"])
    assert df["hora"].between(11, 22).all()
    assert df["prep_estimada_min"].gt(0).all()


def test_kpis_son_consistentes(limpio):
    df, _ = limpio
    k = metricas.kpis(df)
    ped = metricas.pedidos_unicos(df)
    assert k["pedidos"] == len(ped)
    assert k["ingresos"] == pytest.approx(ped["total_pedido"].sum(), abs=0.01)
    assert k["ticket_promedio"] == pytest.approx(k["ingresos"] / k["pedidos"], abs=0.01)


def test_horas_pico_se_detectan(limpio):
    df, _ = limpio
    por_hora = metricas.ventas_por_hora(df).set_index("hora")["pedidos"]
    assert por_hora.idxmax() in (13, 20)                 # almuerzo o cena (los picos simulados)
    assert por_hora.loc[16] < por_hora.loc[13]


def test_pareto_clases_abc(limpio):
    df, _ = limpio
    p = metricas.pareto_platos(df)
    assert p["pct_acumulado"].iloc[-1] == pytest.approx(100)
    assert p["pct_acumulado"].is_monotonic_increasing
    assert p["clase"].iloc[0] == "A" and set(p["clase"]) <= {"A", "B", "C"}


def test_la_cocina_se_satura_en_hora_pico(limpio):
    df, _ = limpio
    t = metricas.tiempos_por_hora(df).set_index("hora")
    assert t.loc[20, "espera_cocina"] > t.loc[16, "espera_cocina"]


def test_los_graficos_se_generan(limpio):
    df, _ = limpio
    for nombre, funcion in graficos.GRAFICOS.items():
        png = graficos.a_png(funcion(df))
        assert png[:8] == b"\x89PNG\r\n\x1a\n", nombre


def test_reporte_completo_y_dashboard(app, client, tmp_path):
    generar_historial(dias=10, pedidos_base=25, semilla=3, hasta=HASTA)
    r = generar_reporte(db.engine, carpeta=tmp_path, imprimir=False)
    assert len(list(tmp_path.glob("*.png"))) == len(graficos.GRAFICOS)
    assert r["kpis"]["pedidos"] > 0
    assert b"Ingresos" in client.get("/dashboard/").data
    assert client.get("/dashboard/grafico/top_platos.png").mimetype == "image/png"


def test_reporte_sin_datos_da_error_claro(app, tmp_path):
    with pytest.raises(ValueError, match="No hay ventas"):
        generar_reporte(db.engine, carpeta=tmp_path, imprimir=False)


def test_limpieza_con_dataframe_minimo():
    bruto = pd.DataFrame({
        "pedido_id": [1, 1, 2], "plato_id": [1, 1, 1], "estado": ["entregado"] * 3,
        "cantidad": [1, 1, 1], "precio_unitario": [10.0] * 3, "costo": [4.0] * 3,
        "tiempo_prep_min": [10.0] * 3, "total_pedido": [10.0] * 3,
        "creado_en": pd.to_datetime(["2026-11-13 12:00"] * 3),
        "inicio_prep_en": pd.to_datetime(["2026-11-13 12:01"] * 3),
        "listo_en": pd.to_datetime(["2026-11-13 12:11"] * 3),
        "entregado_en": pd.to_datetime(["2026-11-13 12:13"] * 3),
    })
    df, informe = limpiar_ventas(bruto)
    assert informe["duplicados_eliminados"] == 1 and len(df) == 2
    assert df["prep_real_min"].eq(10).all() and df["espera_cocina_min"].eq(1).all()


def test_grafico_en_modo_oscuro(app, client):
    generar_historial(dias=7, pedidos_base=20, semilla=5, hasta=HASTA)
    claro = client.get("/dashboard/grafico/pareto.png?tema=claro")
    oscuro = client.get("/dashboard/grafico/pareto.png?tema=oscuro")
    assert claro.mimetype == oscuro.mimetype == "image/png"
    assert claro.data != oscuro.data                      # cambian los colores de fondo y texto


def test_ventas_diarias_excluye_el_dia_en_curso():
    hoy = pd.Timestamp.now().normalize()
    df = pd.DataFrame({"pedido_id": [1, 2, 3], "total_pedido": [10.0, 20.0, 5.0],
                       "fecha": [hoy - pd.Timedelta(days=1), hoy - pd.Timedelta(days=1), hoy]})
    diario = metricas.ventas_diarias(df)
    assert len(diario) == 1 and diario["ingresos"].iloc[0] == 30.0     # hoy (incompleto) no cuenta
