# Estado del proyecto

Entrega final: **semana 17**. Avance entregado: viernes 13 de noviembre.

## Hecho

| Área | Qué hay | Quién |
|---|---|---|
| Base y arquitectura | Modelos POO, funciones puras, servicios, API Flask, interfaz | Leopoldo |
| Roles y seguridad | Login por rol, permisos, bitácora, bloqueo de intentos, **CSRF**, cambio de contraseña | Leopoldo |
| Flujo completo | Mozo → cocina → alerta → entrega → cobro; QR y seguimiento del cliente | Leopoldo |
| POO | Reglas de descuento como jerarquía de clases (herencia y polimorfismo) | Leopoldo |
| Cliente | Llamar al mozo, pedir la cuenta, dividir la cuenta con propina, calificar | Leopoldo |
| Mozo | Agregar platos a un pedido abierto, cobrar con método y propina, sugerencias | Leopoldo |
| Inventario | Descuento automático, reposición al cancelar, alertas de stock bajo | Mari / Leopoldo |
| Recomendador | Co-ocurrencia con NumPy, endpoint y sugerencias en la carta | Mari |
| Análisis | Limpieza, métricas, matriz de menú, predicción de demanda, Pareto | Leslie |
| Panel admin | KPIs, gráficos, usuarios, menú, bitácora, exportación CSV | Leopoldo |
| Tiempos | Estimación que aprende del historial real por hora | Leopoldo |
| Pruebas | **182 pruebas** automáticas (137 funciones) | todos |
| Documentación | README, capturas documentadas, borrador del informe | todos |

## Pendiente para la entrega final

1. **Informe final**: completar y revisar `docs/INFORME.md` (portada, nombres, docente, fuentes). Cada integrante redacta su sección.
2. **Probar con PostgreSQL real** (hasta ahora se probó con SQLite) y el QR en un celular en la red local.
3. **Ensayar la exposición**: cada integrante explica sus módulos y se ensaya la demo (`flask --app run preparar-demo`).
4. Validar el análisis con **datos reales** de un restaurante (hoy son simulados).

## Ideas si sobra tiempo

- Actualizaciones en vivo con SSE o WebSockets en lugar de consultar cada 3 s.
- Gestión de mesas y categorías desde el admin.
- Impresión de comandas para la cocina.

## Reglas del equipo

- Toda función nueva de lógica va con prueba en `tests/` (`python -m pytest` debe pasar antes del PR).
- Funciones puras en `app/funcional/` (sin base de datos); clases en `app/models/` y `app/descuentos.py`.
- Comentar el código en español y explicar el *por qué*.
- Cada quien debe poder explicar en la exposición lo que hizo.
