"""Carga de datos desde la base de datos hacia pandas."""
import pandas as pd
from sqlalchemy import text

# Una fila por plato vendido dentro de un pedido (tabla "larga" lista para analizar)
CONSULTA_VENTAS = text("""
    SELECT p.id              AS pedido_id,
           p.mesa_id,
           p.estado,
           p.comensales,
           p.subtotal        AS subtotal_pedido,
           p.descuento       AS descuento_pedido,
           p.total           AS total_pedido,
           p.creado_en,
           p.inicio_prep_en,
           p.listo_en,
           p.entregado_en,
           i.plato_id,
           i.cantidad,
           i.precio_unitario,
           pl.nombre         AS plato,
           pl.costo,
           pl.tiempo_prep_min,
           c.nombre          AS categoria
    FROM pedidos p
    JOIN items_pedido i ON i.pedido_id = p.id
    JOIN platos pl      ON pl.id = i.plato_id
    JOIN categorias c   ON c.id = pl.categoria_id
""")

COLUMNAS_FECHA = ["creado_en", "inicio_prep_en", "listo_en", "entregado_en"]


def cargar_ventas(engine) -> pd.DataFrame:
    """Lee todas las ventas de la base de datos (PostgreSQL o SQLite)."""
    return pd.read_sql(CONSULTA_VENTAS, engine, parse_dates=COLUMNAS_FECHA)
