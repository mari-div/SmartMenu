"""Limpieza y transformacion de datos con pandas y numpy.

Pasos (cada uno es una funcion DataFrame -> DataFrame, encadenables con `.pipe`):
  1. quitar duplicados
  2. excluir pedidos cancelados (no son ventas)
  3. agregar columnas derivadas (ingresos, margen, hora, dia, tiempos)
  4. marcar como atipicos los tiempos de preparacion fuera de rango (regla IQR)
"""
import numpy as np
import pandas as pd

from app.funcional.cocina import tiempo_preparacion_pedido

NOMBRES_DIA = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
UN_MINUTO = pd.Timedelta(minutes=1)


def quitar_duplicados(df: pd.DataFrame) -> pd.DataFrame:
    return df.drop_duplicates(subset=["pedido_id", "plato_id"])


def excluir_cancelados(df: pd.DataFrame) -> pd.DataFrame:
    return df.loc[df["estado"] != "cancelado"]


def agregar_columnas(df: pd.DataFrame) -> pd.DataFrame:
    """Columnas derivadas: dinero, calendario y tiempos (en minutos)."""
    df = df.copy()
    df["ingreso_linea"] = df["cantidad"] * df["precio_unitario"]
    df["margen_linea"] = df["cantidad"] * (df["precio_unitario"] - df["costo"])
    df["fecha"] = df["creado_en"].dt.normalize()
    df["hora"] = df["creado_en"].dt.hour
    df["dia_semana"] = df["creado_en"].dt.day_of_week
    df["nombre_dia"] = df["dia_semana"].map(dict(enumerate(NOMBRES_DIA)))
    # Tiempos reales: si falta alguna marca de tiempo el resultado es NaN (dato faltante)
    df["espera_cocina_min"] = (df["inicio_prep_en"] - df["creado_en"]) / UN_MINUTO
    df["prep_real_min"] = (df["listo_en"] - df["inicio_prep_en"]) / UN_MINUTO
    df["total_min"] = (df["entregado_en"] - df["creado_en"]) / UN_MINUTO
    # Tiempo estimado por pedido (usa la funcion pura del modulo funcional)
    estimado = df.groupby("pedido_id")["tiempo_prep_min"].apply(
        lambda s: tiempo_preparacion_pedido(list(s)))
    df["prep_estimada_min"] = df["pedido_id"].map(estimado)
    return df


def marcar_atipicos(df: pd.DataFrame, k: float = 1.5) -> pd.DataFrame:
    """Anula (NaN) los tiempos reales anormales.

    Se compara tiempo real / tiempo estimado y se descartan las razones fuera de
    [Q1 - k*IQR, Q3 + k*IQR].  Asi un pedido de 18 min estimados que tardo 2 horas
    (error de registro) no distorsiona los promedios.
    """
    df = df.copy()
    razon = df["prep_real_min"] / df["prep_estimada_min"]
    q1, q3 = np.nanpercentile(razon, [25, 75]) if razon.notna().any() else (np.nan, np.nan)
    iqr = q3 - q1
    atipico = (razon < q1 - k * iqr) | (razon > q3 + k * iqr)
    df["tiempo_atipico"] = atipico.fillna(False)
    df["prep_real_min"] = np.where(df["tiempo_atipico"], np.nan, df["prep_real_min"])
    return df


def limpiar_ventas(bruto: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Aplica todo el proceso y devuelve (datos limpios, informe de lo que se hizo)."""
    informe = {"lineas_iniciales": len(bruto), "pedidos_iniciales": bruto["pedido_id"].nunique()}

    sin_dup = quitar_duplicados(bruto)
    informe["duplicados_eliminados"] = len(bruto) - len(sin_dup)

    sin_canc = excluir_cancelados(sin_dup)
    informe["pedidos_cancelados"] = (sin_dup.loc[sin_dup["estado"] == "cancelado", "pedido_id"]
                                     .nunique())

    limpio = sin_canc.pipe(agregar_columnas).pipe(marcar_atipicos)

    pedidos = limpio.drop_duplicates("pedido_id")
    informe["pedidos_validos"] = len(pedidos)
    informe["pedidos_sin_tiempos"] = int(pedidos["listo_en"].isna().sum())
    informe["pedidos_con_tiempo_atipico"] = int(pedidos["tiempo_atipico"].sum())
    return limpio.reset_index(drop=True), informe
