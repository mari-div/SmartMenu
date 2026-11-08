# SmartMenu

Sistema web de **pedidos inteligentes para restaurantes** desarrollado con Python, Flask y PostgreSQL.
El cliente escanea el QR de su mesa, ve la carta (con filtros de dieta y alérgenos), arma su pedido y
sigue su estado; la cocina recibe una cola priorizada; el dueño ve analítica con pandas, numpy y matplotlib.

## Arquitectura

```
HTML + CSS + JS  →  Flask (app/rutas)  →  Servicios (app/servicios)  →  PostgreSQL
                                                 ↓
                              Pandas + NumPy + Matplotlib (analisis/)
```

| Carpeta | Contenido | Paradigma |
|---|---|---|
| `app/models/` | `Categoria`, `Plato`, `Ingrediente`, `Mesa`, `Pedido`, `ItemPedido` y la máquina de estados del pedido | **POO** |
| `app/funcional/` | Precios y descuentos, prioridad de cocina, filtros dietéticos: funciones puras | **Funcional** |
| `app/servicios/` | Une modelos y funciones puras (crear pedido, cola de cocina, estimaciones) | Integración |
| `app/rutas/` | Páginas y API JSON | |
| `analisis/` | Carga, limpieza, métricas y gráficos; generador de datos sintéticos | pandas / numpy |
| `tests/` | Pruebas con pytest | |

## Puesta en marcha

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
copy .env.example .env          # y poner tu contraseña de PostgreSQL en DATABASE_URL
createdb -U postgres smartmenu
```

```bash
flask --app run sembrar                  # menú de ejemplo + 10 mesas
flask --app run generar-datos --dias 45  # historial simulado para el análisis
flask --app run reporte                  # tablas por consola + gráficos en docs/graficos
python run.py                            # http://127.0.0.1:5000
```

Páginas: `/` (mesas), `/mesa/<token>` (carta), `/pedido/<id>` (seguimiento), `/cocina`, `/dashboard/`.

Sin PostgreSQL se puede probar con SQLite: `DATABASE_URL=sqlite:///smartmenu_dev.db` en el `.env`.

Pruebas: `python -m pytest`

## Funcionalidades

- Carta digital por mesa con filtros: vegano, vegetariano, sin gluten, sin lácteos, sin frutos secos, y avisos de alérgenos
- Carrito con total calculado en el servidor (descuentos: happy hour, volumen, grupos; se aplica el mayor)
- Flujo de estados: pendiente → en preparación → listo → entregado (o cancelado)
- Cola de cocina priorizada por espera, rapidez y tamaño de mesa
- Tiempo estimado de entrega según la carga de la cocina
- Analítica: KPIs, pedidos por hora, día de semana, tendencia, Pareto ABC, tiempos de cocina

Ver [TAREAS.md](TAREAS.md) para el reparto del equipo.
