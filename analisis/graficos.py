
"""Graficos con Matplotlib (se usa `Figure` directamente, sin pyplot, para que sea
seguro dentro de Flask). Cada funcion recibe el DataFrame limpio y devuelve una Figure."""

import io

import numpy as np
from matplotlib.figure import Figure

from analisis import metricas


# ============================================================
# COLORES
# ============================================================

COLOR = "#DC2626"        # color principal (rojo SmartMenu)
COLOR_2 = "#1F9D6B"      # verde
COLOR_3 = "#6b7280"      # gris
COLOR_B = "#E5A00D"      # dorado (clase B del Pareto)


# ============================================================
# TEMAS
# ============================================================

# Colores de fondo/texto para que el grafico combine con el modo claro u oscuro de la web

TEMAS = {
    False: {
        "fondo": "#ffffff",
        "texto": "#3b1d14",
        "suave": "#6b5249",
        "rejilla": "#f1dfd3"
    },
    True: {
        "fondo": "#241814",
        "texto": "#fbede6",
        "suave": "#b9a298",
        "rejilla": "#3b2a23"
    },
}


# ============================================================
# FUNCIONES AUXILIARES
# ============================================================

def _aplicar_tema(fig: Figure, oscuro: bool) -> None:
    t = TEMAS[oscuro]

    fig.set_facecolor(t["fondo"])

    for ax in fig.axes:
        ax.set_facecolor(t["fondo"])
        ax.title.set_color(t["texto"])
        ax.xaxis.label.set_color(t["suave"])
        ax.yaxis.label.set_color(t["suave"])
        ax.tick_params(colors=t["suave"])

        for borde in ax.spines.values():
            borde.set_color(t["rejilla"])

        for linea in ax.get_xgridlines() + ax.get_ygridlines():
            linea.set_color(t["rejilla"])

        for texto in ax.texts:                  # etiquetas de platos, "Proyección →", etc.
            texto.set_color(t["texto"])
        leyenda = ax.get_legend()
        
        if leyenda:
            leyenda.get_title().set_color(t["texto"])
            for texto in leyenda.get_texts():
                texto.set_color(t["texto"])


def _base(titulo: str, ancho: float = 8, alto: float = 4.4):
    fig = Figure(figsize=(ancho, alto), layout="constrained")
    ax = fig.subplots()

    ax.set_title(titulo, loc="left", fontsize=13, fontweight="bold")
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", alpha=0.25)
    ax.set_axisbelow(True)

    return fig, ax


# ============================================================
# GRAFICOS DE VENTAS
# ============================================================

def ventas_por_hora(df) -> Figure:
    datos = metricas.ventas_por_hora(df)

    fig, ax = _base("Pedidos por hora del día")

    ax.bar(datos["hora"], datos["pedidos"], color=COLOR)
    ax.set_xlabel("Hora")
    ax.set_ylabel("Pedidos")
    ax.set_xticks(datos["hora"])

    return fig


def ventas_por_dia_semana(df) -> Figure:
    datos = metricas.ventas_por_dia_semana(df)

    fig, ax = _base("Ingreso promedio por día de la semana")

    ax.bar(datos["nombre_dia"], datos["ingreso_prom_dia"], color=COLOR_2)
    ax.set_ylabel("Ingreso promedio ($)")

    return fig


def ventas_diarias(df) -> Figure:
    datos = metricas.ventas_diarias(df)

    fig, ax = _base("Ingresos diarios y tendencia (media móvil 7 días)")

    ax.plot(
        datos["fecha"],
        datos["ingresos"],
        color=COLOR_3,
        alpha=0.5,
        label="Diario"
    )

    ax.plot(
        datos["fecha"],
        datos["media_movil"],
        color=COLOR,
        linewidth=2.5,
        label="Media móvil"
    )

    # Recta de tendencia con minimos cuadrados (numpy)

    x = np.arange(len(datos))
    pendiente, intercepto = np.polyfit(x, datos["ingresos"], 1)

    ax.plot(
        datos["fecha"],
        pendiente * x + intercepto,
        color=COLOR_2,
        linestyle="--",
        label=f"Tendencia ({pendiente:+.1f} $/día)"
    )

    ax.set_ylabel("Ingresos ($)")
    ax.legend(frameon=False)

    fig.autofmt_xdate()

    return fig


# ============================================================
# GRAFICOS DE PLATOS
# ============================================================

def top_platos(df, n: int = 10) -> Figure:
    datos = metricas.top_platos(df, n).iloc[::-1]  # el mas vendido arriba

    fig, ax = _base(f"Los {n} platos más vendidos", alto=4.8)

    ax.barh(datos["plato"], datos["unidades"], color=COLOR)
    ax.set_xlabel("Unidades vendidas")
    ax.grid(axis="y", visible=False)
    ax.grid(axis="x", alpha=0.25)

    return fig


def pareto(df) -> Figure:
    datos = metricas.pareto_platos(df)

    fig, ax = _base(
        "Pareto de ingresos por plato (análisis ABC)",
        ancho=9
    )

    colores = datos["clase"].map({
        "A": COLOR,
        "B": COLOR_B,
        "C": COLOR_3
    })

    ax.bar(datos["plato"], datos["ingreso_linea"], color=colores)
    ax.set_ylabel("Ingresos ($)")
    ax.tick_params(axis="x", rotation=70)

    for etiqueta in ax.get_xticklabels():
        etiqueta.set_ha("right")

    ax2 = ax.twinx()

    ax2.plot(
        datos["plato"],
        datos["pct_acumulado"],
        color=COLOR_3,
        marker="o",
        markersize=3
    )

    ax2.axhline(80, color=COLOR_3, linestyle=":", linewidth=1)
    ax2.set_ylim(0, 105)
    ax2.set_ylabel("% acumulado")
    ax2.spines[["top"]].set_visible(False)

    return fig


# ============================================================
# GRAFICO DE TIEMPOS DE COCINA
# ============================================================

def tiempos_por_hora(df) -> Figure:
    datos = metricas.tiempos_por_hora(df)

    fig, ax = _base("Tiempos de cocina según la hora")

    ax.plot(
        datos["hora"],
        datos["espera_cocina"],
        color=COLOR,
        marker="o",
        label="Espera antes de empezar"
    )

    ax.plot(
        datos["hora"],
        datos["preparacion"],
        color=COLOR_2,
        marker="o",
        label="Preparación"
    )

    ax.set_xlabel("Hora")
    ax.set_ylabel("Minutos")
    ax.legend(frameon=False)

    return fig


# ============================================================
# MATRIZ DE INGENIERIA DE MENU
# ============================================================

def matriz_ingenieria_menu(df) -> Figure:
    """Grafico de dispersion de la ingenieria de menu."""

    # Obtenemos la clasificacion de los platos

    datos = metricas.matriz_ingenieria_menu(df)

    fig, ax = _base(
        "Matriz de ingenieria de menu",
        ancho=8.8,
        alto=4.84
    )

    # Si no hay datos, mostramos un mensaje

    if datos.empty:
        ax.text(
            0.5,
            0.5,
            "No hay datos disponibles",
            ha="center",
            va="center",
            transform=ax.transAxes
        )

        return fig

    # Asignamos un color a cada clasificacion

    colores = {
        "Estrella": COLOR_B,
        "Vaca": COLOR_2,
        "Puzzle": COLOR,
        "Perro": COLOR_3
    }

    # Dibujamos los platos

    for categoria, grupo in datos.groupby("clasificacion"):
        ax.scatter(
            grupo["unidades"],
            grupo["margen"],
            label=categoria,
            color=colores[categoria],
            s=90,
            alpha=0.85
        )

        # Colocamos el nombre de cada plato

        for _, fila in grupo.iterrows():
            ax.annotate(
                fila["plato"],
                (fila["unidades"], fila["margen"]),
                fontsize=8,
                xytext=(5, 5),
                textcoords="offset points"
            )

    # Dibujamos las medianas

    ax.axvline(
        datos["mediana_unidades"].iloc[0],
        color=COLOR_3,
        linestyle="--",
        label="Mediana popularidad"
    )

    ax.axhline(
        datos["mediana_margen"].iloc[0],
        color=COLOR_3,
        linestyle=":",
        label="Mediana margen"
    )

    ax.set_xlabel("Unidades vendidas")
    ax.set_ylabel("Margen de ganancia")
    ax.legend(frameon=False)

    return fig


# ============================================================
# PREDICCION DE DEMANDA
# ============================================================

def prediccion_demanda(df) -> Figure:
    """Compara las ventas reales con la demanda proyectada para 7 días."""

    predicciones = metricas.prediccion_demanda(df, dias=7)

    fig, ax = _base(
        "Predicción de demanda: próximos 7 días",
        ancho=10,
        alto=5
    )

    if df.empty or predicciones.empty:
        ax.text(
            0.5,
            0.5,
            "No hay datos disponibles",
            ha="center",
            va="center",
            transform=ax.transAxes
        )

        return fig

    # Seleccionamos los 5 platos más vendidos para evitar saturar el gráfico

    platos = metricas.top_platos(df, n=5)["plato"].tolist()

    for plato in platos:
        historial = (
            df[df["plato"] == plato]
            .groupby("fecha")["cantidad"]
            .sum()
            .sort_index()
        )

        # El nombre del plato aparece una sola vez en la leyenda

        linea, = ax.plot(
            historial.index,
            historial.values,
            marker="o",
            markersize=3,
            label=plato
        )

        # La proyección usa el mismo color, pero con línea discontinua y sin etiqueta

        futuro = predicciones[predicciones["plato"] == plato]

        ax.plot(
            futuro["fecha"],
            futuro["unidades_predichas"],
            marker="o",
            markersize=3,
            linestyle="--",
            color=linea.get_color()
        )

    # Línea vertical que separa el historial de la proyección

    inicio = predicciones["fecha"].min()

    ax.axvline(
        inicio,
        color=COLOR_3,
        linestyle=":",
        linewidth=1
    )

    ax.text(
        inicio,
        ax.get_ylim()[1],
        " Proyección →",
        va="top",
        fontsize=8,
        color=COLOR_3
    )

    ax.set_xlabel("Fecha")
    ax.set_ylabel("Unidades vendidas")

    # Leyenda fuera del área del gráfico para que no tape las líneas

    ax.legend(
        frameon=False,
        fontsize=8,
        loc="center left",
        bbox_to_anchor=(1.01, 0.5),
        title="Plato (continuo = real,\ndiscontinuo = proyección)",
        title_fontsize=8
    )

    fig.autofmt_xdate()

    return fig


# ============================================================
# DICCIONARIO DE GRAFICOS
# ============================================================

GRAFICOS = {
    "ventas_por_hora": ventas_por_hora,
    "ventas_por_dia_semana": ventas_por_dia_semana,
    "top_platos": top_platos,
    "ventas_diarias": ventas_diarias,
    "pareto": pareto,
    "tiempos_por_hora": tiempos_por_hora,
    "matriz_ingenieria_menu": matriz_ingenieria_menu,
    "prediccion_demanda": prediccion_demanda,
}


# ============================================================
# EXPORTACION A PNG
# ============================================================

def a_png(
    fig: Figure,
    dpi: int = 110,
    oscuro: bool = False,
    sin_titulo: bool = False
) -> bytes:
    """PNG del grafico. En la web el titulo lo pone la pagina (sin_titulo=True)."""

    _aplicar_tema(fig, oscuro)

    if sin_titulo:
        for ax in fig.axes:
            ax.set_title("", loc="left")      # el título se creó con loc="left"

    buffer = io.BytesIO()

    fig.savefig(
        buffer,
        format="png",
        dpi=dpi
    )

    return buffer.getvalue()
