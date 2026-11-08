"""Metricas de negocio calculadas con pandas y numpy.

Todas reciben el DataFrame ya limpio (salida de `limpieza.limpiar_ventas`).
"""
import numpy as np
import pandas as pd


def pedidos_unicos(df: pd.DataFrame) -> pd.DataFrame:
    """Una fila por pedido (las columnas *_pedido y los tiempos ya son del pedido)."""
    return df.drop_duplicates("pedido_id")


def kpis(df: pd.DataFrame) -> dict:
    """Indicadores generales. Ingresos = lo realmente cobrado (con descuentos);
    el margen es bruto, calculado a precio de carta."""
    ped = pedidos_unicos(df)
    if ped.empty:
        return {}
    return {
        "ingresos": round(float(ped["total_pedido"].sum()), 2),
        "pedidos": int(len(ped)),
        "ticket_promedio": round(float(ped["total_pedido"].mean()), 2),
        "platos_vendidos": int(df["cantidad"].sum()),
        "margen_bruto": round(float(df["margen_linea"].sum()), 2),
        "descuentos": round(float(ped["descuento_pedido"].sum()), 2),
        "espera_cocina_prom_min": round(float(ped["espera_cocina_min"].mean()), 1),
        "prep_prom_min": round(float(ped["prep_real_min"].mean()), 1),
    }


def ventas_por_hora(df: pd.DataFrame) -> pd.DataFrame:
    ped = pedidos_unicos(df)
    por_hora = ped.groupby("hora").agg(pedidos=("pedido_id", "count"),
                                       ingresos=("total_pedido", "sum"))
    horas = range(int(df["hora"].min()), int(df["hora"].max()) + 1)
    return por_hora.reindex(horas, fill_value=0).rename_axis("hora").reset_index()


def ventas_por_dia_semana(df: pd.DataFrame) -> pd.DataFrame:
    ped = pedidos_unicos(df)
    por_dia = ped.groupby("dia_semana").agg(pedidos=("pedido_id", "count"),
                                            ingresos=("total_pedido", "sum"))
    por_dia = por_dia.reindex(range(7), fill_value=0)
    # Promedio por dia calendario (no por pedido) para comparar dias justamente
    n_dias = ped.groupby("dia_semana")["fecha"].nunique().reindex(range(7)).replace(0, np.nan)
    por_dia["ingreso_prom_dia"] = (por_dia["ingresos"] / n_dias).fillna(0)
    por_dia["nombre_dia"] = [d for d in ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]]
    return por_dia.reset_index()


def ventas_diarias(df: pd.DataFrame, ventana: int = 7) -> pd.DataFrame:
    """Ingresos por dia y su media movil (suaviza la tendencia)."""
    ped = pedidos_unicos(df)
    diario = ped.groupby("fecha").agg(pedidos=("pedido_id", "count"),
                                      ingresos=("total_pedido", "sum")).reset_index()
    # El dia en curso esta incompleto: incluirlo haria caer la tendencia sin motivo real
    diario = diario[diario["fecha"] != pd.Timestamp.now().normalize()].reset_index(drop=True)
    diario["media_movil"] = diario["ingresos"].rolling(ventana, min_periods=1).mean()
    return diario


def top_platos(df: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    return (df.groupby(["plato", "categoria"])
              .agg(unidades=("cantidad", "sum"), ingresos=("ingreso_linea", "sum"),
                   margen=("margen_linea", "sum"))
              .sort_values("unidades", ascending=False)
              .head(n).reset_index())


def pareto_platos(df: pd.DataFrame) -> pd.DataFrame:
    """Analisis ABC: clase A = platos que generan el primer 80% de los ingresos,
    B = hasta el 95%, C = el resto."""
    ing = (df.groupby("plato")["ingreso_linea"].sum()
             .sort_values(ascending=False).reset_index())
    ing["pct"] = 100 * ing["ingreso_linea"] / ing["ingreso_linea"].sum()
    ing["pct_acumulado"] = np.cumsum(ing["pct"])
    previo = ing["pct_acumulado"] - ing["pct"]          # acumulado ANTES de este plato
    ing["clase"] = np.select([previo < 80, previo < 95], ["A", "B"], default="C")
    return ing


def tiempos_por_hora(df: pd.DataFrame) -> pd.DataFrame:
    """Espera y preparacion promedio segun la hora (muestra la saturacion de cocina)."""
    ped = pedidos_unicos(df)
    return (ped.groupby("hora")
               .agg(espera_cocina=("espera_cocina_min", "mean"),
                    preparacion=("prep_real_min", "mean"),
                    pedidos=("pedido_id", "count"))
               .reset_index())
