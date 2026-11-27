# Capturas documentadas de SmartMenu

Capturas reales de la aplicación corriendo con **datos de demostración** (generados con `flask --app run generar-datos`),
tomadas el 13 de noviembre de 2026 con Chrome (escritorio 1440×900 y móvil 390×844). Sirven como evidencia para el informe
y la presentación. Cada fila indica qué muestra y qué criterio de la rúbrica respalda.

| Archivo | Qué muestra | Rol / usuario | Criterio |
|---|---|---|---|
| `landing.png` | Portada pública con el flujo del sistema | público | Resultados |
| `login.png` | Inicio de sesión con usuarios de demostración | público | Diseño / seguridad |
| `m_mozo_panel.png` | Panel del mozo: mesas con estado y alerta «Listos para entregar» | mozo1 (móvil) | Resultados |
| `m_carta.png` | Carta con fotos de internet, precios en soles y barra del pedido | mozo1 (móvil) | Resultados |
| `m_carrito.png` | Resumen del pedido con descuento Happy hour y total en soles | mozo1 (móvil) | Paradigmas (reglas funcionales) |
| `m_qr.png` | Pedido enviado y código QR para el cliente | mozo1 (móvil) | Resultados |
| `m_cliente.png` | Seguimiento del cliente: «Estamos cocinando», minutos restantes | cliente (móvil) | Resultados |
| `m_cliente_listo.png` | Seguimiento del cliente: pedido listo | cliente (móvil) | Resultados |
| `carta_vegano.png` | Filtro de dieta «Vegano» aplicado sin recargar la página | mozo1 | Paradigmas (filtros funcionales) |
| `cocina.png` | Cocina: pendientes por prioridad, en preparación y listos | cocina1 | Resultados |
| `admin_resumen.png` | KPIs del negocio y estado en vivo | admin | Análisis de datos |
| `admin_diarias.png` | Ingresos diarios y media móvil de 7 días | admin | Análisis de datos |
| `admin_calor.png` | Mapa de calor de afluencia por día y hora (matriz de numpy) | admin | Análisis de datos |
| `admin_top.png` | Platos más vendidos | admin | Análisis de datos |
| `admin_mozos.png` | Ingresos por mozo | admin | Análisis de datos |
| `admin_categorias.png` | Ventas por categoría | admin | Análisis de datos |
| `admin_horas.png` | Pedidos por hora del día | admin | Análisis de datos |
| `admin_menu.png` | Edición de platos: precio, disponibilidad y enlace de la foto | admin | Resultados |
| `admin_stock.png` | Inventario con ingredientes en «Stock bajo» | admin | Resultados |
| `admin_usuarios.png` | Gestión de usuarios y roles | admin | Diseño / seguridad |
| `admin_logs.png` | Bitácora: logins, pedidos, cambios de estado, accesos denegados | admin | Diseño / seguridad |
| `an_matriz.png` | Matriz de ingeniería de menú (estrella, vaca, puzzle, perro) | admin | Análisis de datos |
| `an_prediccion.png` | Predicción de demanda de 7 días | admin | Análisis de datos |
| `an_pareto.png` | Análisis ABC (Pareto) de ingresos por plato | admin | Análisis de datos |
| `terminal_pytest.png` | Salida real de `python -m pytest -q`: 126 passed | desarrollo | Pruebas |
| `code_funcional.png` | `precios.py`: `componer`, `subtotal` (map y reduce), `mejor_descuento` | código | Paradigmas |
| `code_poo.png` | `pedido.py`: `cambiar_estado` y `avanzar` (máquina de estados) | código | Paradigmas |
| `code_permisos.png` | `permisos.py`: permisos por rol como datos y función pura | código | Paradigmas |
| `code_limpieza.png` | `limpieza.py`: atípicos con IQR (`np.nanpercentile`, `np.where`) | código | Análisis de datos |
| `code_pareto.png` | `metricas.py`: Pareto ABC con `np.cumsum` y `np.select` | código | Análisis de datos |
| `code_prioridad.png` | `cocina.py`: prioridad de la cola de cocina | código | Paradigmas |
| `code_auth.png` | `auth.py`: decorador `rol_requerido` | código | Diseño |

## Funciones nuevas (versión final)

| Archivo | Qué muestra | Criterio |
|---|---|---|
| `nuevas_m_sug_flotante.png` | Carta del mozo con la tira «Te puede gustar» (recomendador) | Análisis / Resultados |
| `nuevas_m_agregar.png` | Agregar platos a un pedido abierto, con sugerencias | Resultados |
| `nuevas_m_alerta_listo.png` | Alerta «Listos para entregar» en el panel del mozo | Resultados |
| `nuevas_m_cliente_final.png` | Cliente: llamar al mozo, pedir la cuenta, dividirla con propina y calificar | Resultados |
| `nuevas_m_avisos_cobro.png` | Mozo: «Clientes te llaman» y «Por cobrar» (método y propina) | Resultados |
| `nuevas_admin_nuevo.png` | Admin: KPIs con propinas y satisfacción, exportar CSV | Análisis de datos |
| `nuevas_admin_pagos.png` | Admin: métodos de pago y calificaciones | Análisis de datos |
| `nuevas_admin_comentarios.png` | Admin: comentarios de clientes | Análisis de datos |
| `nuevas_cuenta.png` | Mi cuenta: cambio de contraseña | Seguridad |

## Cifras de la depuración de datos (captura `admin_resumen.png`, 30 días)

3,114 pedidos leídos → 147 cancelados excluidos, 49 sin marca de tiempo y 51 con tiempo atípico descartado → **2,967 pedidos válidos**.
Los datos son **sintéticos** (reproducibles con semilla) y contienen errores intencionales para demostrar la limpieza.
