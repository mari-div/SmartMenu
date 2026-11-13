"""Metricas del panel de administracion (pandas + numpy sobre los datos reales)."""
import json
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

from analisis import metricas
from analisis.datos import cargar_ventas
from analisis.limpieza import limpiar_ventas
from app.extensions import db
from app.models import Ingrediente, Pedido, Plato

MINUTOS_DEMORA = 20            # un pedido pendiente/en preparacion mas de esto se marca "demorado"


def _registros(df: pd.DataFrame) -> list[dict]:
    """DataFrame -> lista de dicts JSON-seguros (sin tipos de numpy ni NaN)."""
    return json.loads(df.to_json(orient="records", date_format="iso"))


def _variacion(actual: float, previo: float) -> float | None:
    return None if not previo else round(100 * (actual - previo) / previo, 1)


def _periodo(df: pd.DataFrame, desde: datetime, hasta: datetime) -> pd.DataFrame:
    return df[(df["creado_en"] >= desde) & (df["creado_en"] < hasta)]


def cargar_limpio() -> tuple[pd.DataFrame | None, dict]:
    bruto = cargar_ventas(db.engine)
    if bruto.empty:
        return None, {}
    return limpiar_ventas(bruto)


# ---------------------------------------------------------------- en vivo
def estado_en_vivo(ahora: datetime | None = None) -> dict:
    """Foto del momento: pedidos activos, demorados y alertas de inventario."""
    ahora = ahora or datetime.now()
    activos = Pedido.query.filter(Pedido.estado.in_(["pendiente", "en_preparacion", "listo"])).all()
    demorados = [p for p in activos if p.estado in ("pendiente", "en_preparacion")
                 and (ahora - p.creado_en).total_seconds() / 60 > MINUTOS_DEMORA]
    stock_bajo = Ingrediente.query.filter(Ingrediente.stock <= Ingrediente.stock_minimo).all()
    no_disp = Plato.query.filter_by(disponible=False).all()
    return {
        "activos": len(activos),
        "pendientes": sum(p.estado == "pendiente" for p in activos),
        "en_preparacion": sum(p.estado == "en_preparacion" for p in activos),
        "listos": sum(p.estado == "listo" for p in activos),
        "demorados": [{"id": p.id, "mesa": p.mesa.numero, "estado": p.estado,
                       "minutos": round((ahora - p.creado_en).total_seconds() / 60)}
                      for p in demorados],
        "stock_bajo": [{"nombre": i.nombre, "stock": round(i.stock, 2), "minimo": i.stock_minimo,
                        "unidad": i.unidad} for i in stock_bajo],
        "platos_no_disponibles": [p.nombre for p in no_disp],
    }


# ---------------------------------------------------------------- resumen por periodo
def resumen(dias: int = 30, ahora: datetime | None = None) -> dict:
    """KPIs, comparativa con el periodo anterior y las series de los graficos."""
    ahora = ahora or datetime.now()
    limpio, informe = cargar_limpio()
    vivo = estado_en_vivo(ahora)
    if limpio is None:
        return {"vacio": True, "vivo": vivo}

    dias = max(1, int(dias))
    # dias=0 se interpreta como "todo el historial" desde la vista; aqui siempre hay un rango
    inicio = ahora - timedelta(days=dias)
    actual = _periodo(limpio, inicio, ahora + timedelta(days=1))
    previo = _periodo(limpio, inicio - timedelta(days=dias), inicio)
    if actual.empty:
        return {"vacio": True, "vivo": vivo, "dias": dias}

    k, kp = metricas.kpis(actual), (metricas.kpis(previo) if not previo.empty else {})
    ped = metricas.pedidos_unicos(actual)

    # cancelados del periodo (el dataset limpio ya los excluye): se cuentan aparte
    total_ped = Pedido.query.filter(Pedido.creado_en >= inicio).count()
    cancelados = Pedido.query.filter(Pedido.creado_en >= inicio, Pedido.estado == "cancelado").count()

    ingresos = k["ingresos"]
    kpis = {
        "ingresos": ingresos,
        "pedidos": k["pedidos"],
        "ticket_promedio": k["ticket_promedio"],
        "platos_vendidos": k["platos_vendidos"],
        "margen_bruto": k["margen_bruto"],
        "margen_pct": round(100 * k["margen_bruto"] / max(1e-9, ingresos + k["descuentos"]), 1),
        "descuentos": k["descuentos"],
        "cancelados": cancelados,
        "cancelados_pct": round(100 * cancelados / total_ped, 1) if total_ped else 0.0,
        "espera_cocina_min": k["espera_cocina_prom_min"],
        "prep_min": k["prep_prom_min"],
        "comensales_prom": round(float(ped["comensales"].mean()), 1),
        "var_ingresos": _variacion(ingresos, kp.get("ingresos", 0)),
        "var_pedidos": _variacion(k["pedidos"], kp.get("pedidos", 0)),
        "var_ticket": _variacion(k["ticket_promedio"], kp.get("ticket_promedio", 0)),
    }

    diarias = metricas.ventas_diarias(actual)
    diarias["fecha"] = pd.to_datetime(diarias["fecha"]).dt.strftime("%Y-%m-%d")
    por_cat = (actual.groupby("categoria")["ingreso_linea"].sum().sort_values(ascending=False)
               .rename("ingresos").reset_index())
    por_mozo = (ped.groupby("mozo").agg(pedidos=("pedido_id", "count"), ingresos=("total_pedido", "sum"),
                                        ticket=("total_pedido", "mean"))
                .sort_values("ingresos", ascending=False).round(2).reset_index())
    # Mapa de calor: pedidos por dia de la semana y hora (numpy: matriz 7 x horas)
    horas = list(range(int(actual["hora"].min()), int(actual["hora"].max()) + 1))
    matriz = np.zeros((7, len(horas)), dtype=int)
    for dia, hora in zip(ped["dia_semana"], ped["hora"]):
        matriz[int(dia), horas.index(int(hora))] += 1

    top = metricas.top_platos(actual, 8)
    top["margen_pct"] = (100 * top["margen"] / top["ingresos"]).round(1)
    return {
        "vacio": False, "dias": dias, "kpis": kpis, "vivo": vivo, "limpieza": informe,
        "series": {
            "diarias": _registros(diarias.round(2)),
            "horas": _registros(metricas.ventas_por_hora(actual).round(2)),
            "dias_semana": _registros(metricas.ventas_por_dia_semana(actual).round(2)),
            "top_platos": _registros(top.round(2)),
            "categorias": _registros(por_cat.round(2)),
            "mozos": _registros(por_mozo),
            "tiempos": _registros(metricas.tiempos_por_hora(actual).round(2)),
            "calor": {"horas": horas, "dias": ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"],
                      "valores": matriz.tolist()},
        },
    }
