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

def prediccion_demanda(df: pd.DataFrame, dias: int = 7) -> pd.DataFrame:
    """Predice las unidades que se venderán de cada plato durante los próximos días."""
    columnas = ["plato", "fecha", "unidades_predichas"]

    if df.empty or dias <= 0:
        return pd.DataFrame(columns=columnas)

    # Rango completo de fechas del historial
    fechas = pd.date_range(
        df["fecha"].min().normalize(),
        df["fecha"].max().normalize(),
        freq="D"
    )

    resultados = []

    # Analizamos cada plato por separado
    for plato, grupo in df.groupby("plato"):
        ventas = (
            grupo.groupby("fecha")["cantidad"]
            .sum()
            .reindex(fechas, fill_value=0)
        )

        # Convertimos los días en números: 0, 1, 2, 3...
        x = np.arange(len(ventas))
        y = ventas.to_numpy()

                # 1. Tendencia: una recta que dice si las ventas suben o bajan
        if len(y) >= 2:
            pendiente, intercepto = np.polyfit(x, y, 1)
        else:
            pendiente, intercepto = 0, float(y[0])
        tendencia = pendiente * x + intercepto

        # 2. Efecto del día de la semana: cuánto se aleja cada día de la recta,
        #    en promedio (ej.: los sábados se vende más que la tendencia)
        desviacion = y - tendencia
        efecto_dia = pd.Series(desviacion).groupby(fechas.day_of_week.to_numpy()).mean()

        # 3. Fechas futuras y su día de la semana
        fechas_futuras = pd.date_range(
            fechas[-1] + pd.Timedelta(days=1), periods=dias, freq="D"
        )
        x_futuro = np.arange(len(y), len(y) + dias)
        ajuste = (efecto_dia.reindex(fechas_futuras.day_of_week.to_numpy())
                  .fillna(0).to_numpy())

        # 4. Predicción = tendencia + efecto del día; sin valores negativos
        predicciones = np.maximum(0, np.rint(pendiente * x_futuro + intercepto + ajuste))

        

        for fecha, unidades in zip(fechas_futuras, predicciones):
            resultados.append({
                "plato": plato,
                "fecha": fecha,
                "unidades_predichas": int(unidades)
            })

    return pd.DataFrame(resultados, columns=columnas)



def matriz_ingenieria_menu(df: pd.DataFrame) -> pd.DataFrame:
    """Clasifica los platos según su popularidad y margen."""

    # 1. Si no hay datos, devolvemos una tabla vacía
    if df.empty:
        return pd.DataFrame()

    # 2. Obtenemos todos los platos y sus resultados
    platos = top_platos(df, n=df["plato"].nunique())

    # 3. Calculamos las medianas
    mediana_unidades = platos["unidades"].median()
    mediana_margen = platos["margen"].median()

    # 4. Identificamos popularidad y margen altos
    popularidad_alta = platos["unidades"] >= mediana_unidades
    margen_alto = platos["margen"] >= mediana_margen

    # 5. Clasificamos cada plato
    platos["clasificacion"] = np.select(
        [
            popularidad_alta & margen_alto,
            popularidad_alta & ~margen_alto,
            ~popularidad_alta & margen_alto
        ],
        [
            "Estrella",
            "Vaca",
            "Puzzle"
        ],
        default="Perro"
    )

    # 6. Guardamos las medianas para utilizarlas en el gráfico
    platos["mediana_unidades"] = mediana_unidades
    platos["mediana_margen"] = mediana_margen

    return platos


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
