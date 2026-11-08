# Reparto de tareas

Entrega final: **semana 17**. Avance: **viernes 13**.
Cada quien trabaja en su rama (`mari/...`, `leslie/...`, `leopoldo/...`) y abre Pull Request a `main`.

## Hecho (base del avance)
- Modelos POO, máquina de estados del pedido, esquema de base de datos
- Funciones puras: precios/descuentos, prioridad de cocina, filtros dietéticos
- Carta con carrito, seguimiento del pedido, panel de cocina
- Generador de datos, limpieza con pandas, métricas, 6 gráficos, dashboard
- 54 pruebas automáticas

## Leslie: análisis de datos (pandas / numpy)
Archivos: `analisis/metricas.py`, `analisis/graficos.py`, `tests/test_analisis.py`
1. **Matriz de ingeniería de menú**: clasificar cada plato en estrella / vaca / puzzle / perro según popularidad y margen (usa `top_platos` como base).
2. **Predicción de demanda**: media móvil o regresión con `np.polyfit` para proyectar ventas de los próximos 7 días por plato.
3. Gráficos nuevos para 1 y 2, y agregarlos a `GRAFICOS` en `graficos.py` (aparecen solos en el dashboard).

## Mari: lógica inteligente (funcional)
Archivos nuevos en `app/funcional/` y `app/servicios/`
1. **Recomendador**: matriz de co-ocurrencia de platos con numpy ("quien pidió X también pidió Y"); función pura `recomendar(plato_id, matriz, n)` y mostrarlo en la carta al agregar un plato. El generador ya simula afinidades (hamburguesa + papas + gaseosa), así que hay señal real.
2. **Tiempo estimado dinámico**: mejorar `estimar_minutos_entrega` usando los tiempos reales históricos por plato y hora.
3. **Inventario**: descontar ingredientes (`PlatoIngrediente.cantidad`) al hacer pedidos y marcar platos no disponibles cuando falte stock.

## Leopoldo: integración, cliente y entrega
1. Código **QR** por mesa y seguimiento en tiempo real para el cliente
2. **Dividir cuenta** y propina en la pantalla del pedido (la lógica ya está en `precios.py`)
3. Conexión con PostgreSQL, revisión de PRs, pruebas de integración
4. Informe, presentación y ensayo de la exposición (todos participan)

## Reglas del equipo
- Toda función nueva de lógica va con prueba en `tests/` (`python -m pytest` debe pasar antes del PR)
- Funciones puras en `app/funcional/` (sin base de datos); clases en `app/models/`
- Comentar el código en español y explicar el *por qué*
- Cada quien debe poder explicar en la exposición lo que hizo
