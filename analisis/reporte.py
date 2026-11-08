"""Genera el reporte de analisis: tablas por consola + graficos PNG en docs/graficos."""
from pathlib import Path

import pandas as pd

from analisis import graficos, metricas
from analisis.datos import cargar_ventas
from analisis.limpieza import limpiar_ventas

CARPETA_POR_DEFECTO = Path(__file__).resolve().parent.parent / "docs" / "graficos"


def generar_reporte(engine, carpeta: Path = CARPETA_POR_DEFECTO, imprimir: bool = True) -> dict:
    bruto = cargar_ventas(engine)
    if bruto.empty:
        raise ValueError("No hay ventas en la base de datos. Ejecuta: flask generar-datos")
    limpio, informe = limpiar_ventas(bruto)

    carpeta = Path(carpeta)
    carpeta.mkdir(parents=True, exist_ok=True)
    archivos = []
    for nombre, funcion in graficos.GRAFICOS.items():
        ruta = carpeta / f"{nombre}.png"
        ruta.write_bytes(graficos.a_png(funcion(limpio)))
        archivos.append(ruta)

    resultado = {"informe_limpieza": informe, "kpis": metricas.kpis(limpio),
                 "top_platos": metricas.top_platos(limpio), "archivos": archivos}
    if imprimir:
        pd.set_option("display.width", 120)
        print("\n== LIMPIEZA DE DATOS ==")
        for clave, valor in informe.items():
            print(f"  {clave}: {valor}")
        print("\n== INDICADORES ==")
        for clave, valor in resultado["kpis"].items():
            print(f"  {clave}: {valor}")
        print("\n== TOP 10 PLATOS ==")
        print(resultado["top_platos"].round(2).to_string(index=False))
        print(f"\nGraficos guardados en: {carpeta}")
    return resultado
