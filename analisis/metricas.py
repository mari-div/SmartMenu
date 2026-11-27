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


def _nombres(serie: pd.Series, maximo: int = 3) -> str:
    """'A, B y C' (y '+N más' si hay más de `maximo`)."""
    lista = serie.tolist()
    texto = ", ".join(lista[:maximo])
    return texto + (f" y {len(lista) - maximo} más" if len(lista) > maximo else "")


def conclusiones(df: pd.DataFrame) -> list[str]:
    """Hallazgos principales en frases, calculados con los mismos datos de los gráficos.

    Sirven para que el administrador no tenga que interpretar cada gráfico:
    el sistema le dice qué mantener, qué promocionar y qué revisar.
    """
    if df.empty:
        return []
    frases = []

    # 1. Ingeniería de menú: qué hacer con cada grupo de platos
    matriz = matriz_ingenieria_menu(df)
    for clase, texto in [("Estrella", "Mantener y destacar en la carta (Estrellas)"),
                         ("Puzzle", "Promocionar: dejan buen margen pero se piden poco (Puzzles)"),
                         ("Vaca", "Mejorar precio o costo: se venden mucho pero ganan poco (Vacas)"),
                         ("Perro", "Revisar o retirar: ni se venden ni ganan (Perros)")]:
        grupo = matriz.loc[matriz["clasificacion"] == clase, "plato"]
        if not grupo.empty:
            frases.append(f"{texto}: {_nombres(grupo)}.")

    # 2. Pareto: pocos platos generan casi todo el ingreso
    pareto = pareto_platos(df)
    n_a = int((pareto["clase"] == "A").sum())
    frases.append(f"{n_a} de {len(pareto)} platos generan el 80% de los ingresos (clase A del Pareto).")

    # 3. Dia y hora de mayor movimiento
    dias = ventas_por_dia_semana(df)
    mejor_dia = dias.loc[dias["ingreso_prom_dia"].idxmax()]
    frases.append(f"El día con más ingreso promedio es {mejor_dia['nombre_dia']} "
                  f"(S/ {mejor_dia['ingreso_prom_dia']:,.0f}).")
    horas = ventas_por_hora(df)
    pico = horas.loc[horas["pedidos"].idxmax()]
    frases.append(f"La hora pico es a las {int(pico['hora'])}:00, con {int(pico['pedidos'])} pedidos en el periodo.")

    # 4. Que plato se espera mas en los proximos 7 dias
    pred = prediccion_demanda(df, dias=7)
    if not pred.empty:
        total = pred.groupby("plato")["unidades_predichas"].sum().sort_values(ascending=False)
        frases.append(f"Próximos 7 días: se espera más demanda de {total.index[0]} "
                      f"(unas {int(total.iloc[0])} unidades).")
    return frases


# ------------------------------------------------------------------ datos para el panel interactivo
def filtrar_periodo(df: pd.DataFrame, dias: int | None = None,
                    categoria: str | None = None) -> pd.DataFrame:
    """Recorta los datos a los últimos `dias` (contados desde la última venta) y/o a una categoría."""
    if df.empty:
        return df
    if dias:
        limite = df["creado_en"].max() - pd.Timedelta(days=dias)
        df = df[df["creado_en"] > limite]
    if categoria:
        df = df[df["categoria"] == categoria]
    return df


def matriz_para_json(df: pd.DataFrame) -> dict:
    """La matriz de ingeniería de menú lista para enviarse al navegador."""
    vacio = {"platos": [], "mediana_unidades": 0, "mediana_margen": 0}
    if df.empty:
        return vacio
    matriz = matriz_ingenieria_menu(df)
    if matriz.empty:
        return vacio
    return {
        "mediana_unidades": float(matriz["mediana_unidades"].iloc[0]),
        "mediana_margen": round(float(matriz["mediana_margen"].iloc[0]), 2),
        "platos": [{"plato": f.plato, "categoria": f.categoria, "unidades": int(f.unidades),
                    "ingresos": round(float(f.ingresos), 2), "margen": round(float(f.margen), 2),
                    "clasificacion": f.clasificacion}
                   for f in matriz.itertuples()],
    }


def prediccion_para_json(df: pd.DataFrame, plato: str | None = None, dias: int = 7) -> dict:
    """Historial y proyección de un plato (por defecto el más vendido), listos para el navegador."""
    vacio = {"platos": [], "plato": None, "historial": [], "prediccion": []}
    if df.empty:
        return vacio
    pred = prediccion_demanda(df, dias=dias)
    platos = top_platos(df, n=df["plato"].nunique())["plato"].tolist()    # del más al menos vendido
    if pred.empty or not platos:
        return vacio
    if plato not in platos:
        plato = platos[0]
    historial = df[df["plato"] == plato].groupby("fecha")["cantidad"].sum().sort_index()
    futuro = pred[pred["plato"] == plato]
    return {
        "platos": platos,
        "plato": plato,
        "historial": [{"fecha": f.strftime("%Y-%m-%d"), "unidades": int(u)}
                      for f, u in historial.items()],
        "prediccion": [{"fecha": f.strftime("%Y-%m-%d"), "unidades": int(u)}
                       for f, u in zip(futuro["fecha"], futuro["unidades_predichas"])],
    }
