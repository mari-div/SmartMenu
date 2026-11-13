# SmartMenu

Sistema web de **pedidos inteligentes para restaurantes** (Python, Flask, PostgreSQL, pandas, numpy, matplotlib).
Precios en **soles (S/)**.

## Cómo funciona (flujo por roles)

```
 MOZO ──toma el pedido──▶ COCINA ──lo prepara──▶ "LISTO" ──ALERTA──▶ MOZO ──entrega──▶ CLIENTE
   │                                                                                       ▲
   └──── genera un QR con un código secreto ───────────────────────────────────────────────┘
                                          (el cliente sigue su pedido en tiempo real)
```

| Rol | Entra a | Qué hace |
|---|---|---|
| **Mozo** | `/mozo/` | Elige la mesa, toma el pedido con la carta (fotos, filtros de dieta y alérgenos), obtiene el **QR** para el cliente, recibe la **alerta con sonido** cuando un pedido está listo y lo entrega. |
| **Cocina** | `/cocina` | Ve los pedidos entrantes priorizados, los marca *en preparación* y *listo* (esto avisa al mozo). No entrega. |
| **Administrador** | `/admin/` | KPIs y gráficos de ventas, pedidos, menú y fotos, inventario, usuarios, **bitácora (logs)** y análisis avanzado. Puede ver todo. |
| **Cliente** | `/seguimiento/<código>` | Sin cuenta: escanea el QR y ve el avance, el tiempo estimado y el detalle en vivo. |

## Usuarios de demostración

| Usuario | Contraseña | Rol |
|---|---|---|
| `admin` | `admin123` | Administrador |
| `mozo1` / `mozo2` | `mozo123` | Mozo |
| `cocina1` | `cocina123` | Cocina |

> Son claves de **desarrollo**. Las contraseñas se guardan con hash; el administrador puede cambiarlas en *Admin → Usuarios*.

## Arquitectura

```
HTML + CSS + JS  →  Flask (app/rutas)  →  Servicios (app/servicios)  →  PostgreSQL
                                                 ↓
                              Pandas + NumPy + Matplotlib (analisis/)
```

| Carpeta | Contenido | Paradigma |
|---|---|---|
| `app/models/` | `Usuario`, `Auditoria`, `Plato`, `Ingrediente`, `Mesa`, `Pedido`… y la máquina de estados del pedido | **POO** |
| `app/funcional/` | Precios y descuentos, prioridad de cocina, filtros dietéticos, **permisos por rol**, recomendador | **Funcional** |
| `app/auth.py` | Sesión, decoradores por rol, bitácora, bloqueo por intentos fallidos | |
| `app/servicios/` | Pedidos, inventario y métricas del panel admin | Integración |
| `app/rutas/` | `auth`, `mozo`, `cocina`, `cliente`, `admin`, `api` | |
| `analisis/` | Carga, limpieza, métricas, gráficos y generador de datos sintéticos | pandas / numpy |
| `tests/` | Pruebas con pytest (`python -m pytest`) | |

## Puesta en marcha

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
copy .env.example .env          # y poner tu contraseña de PostgreSQL en DATABASE_URL
createdb -U postgres smartmenu
```

```bash
flask --app run sembrar                  # menú (con fotos), mesas y usuarios de prueba
flask --app run generar-datos --dias 45  # historial simulado para el análisis
python run.py                            # http://127.0.0.1:5000
```

> **Si ya tenías la base de datos de antes**, el esquema cambió (usuarios, auditoría, fotos, QR).
> Reinícala una vez (**borra los datos**): `flask --app run reset-db --yes` y luego los comandos de `sembrar` y `generar-datos`.

Sin PostgreSQL se puede probar con SQLite: `DATABASE_URL=sqlite:///smartmenu_dev.db` en el `.env`.

### QR para el celular del cliente

El QR contiene la dirección del servidor. Para que un celular pueda abrirla, la PC y el celular deben estar en la **misma red Wi-Fi**:

1. Averigua la IP de la PC (`ipconfig`), por ejemplo `192.168.1.20`.
2. En el `.env`: `BASE_URL=http://192.168.1.20:5000`
3. Arranca con `flask --app run run --host 0.0.0.0` (y permite el puerto 5000 en el firewall si lo pide).

### Variables del `.env`

| Variable | Para qué |
|---|---|
| `DATABASE_URL` | Conexión a PostgreSQL (o SQLite) |
| `SECRET_KEY` | Firma las sesiones de login. **Cámbiala** (`python -c "import secrets; print(secrets.token_hex(32))"`) |
| `BASE_URL` | Dirección pública para los QR (ver arriba) |
| `ESTACIONES_COCINA` | Platos que la cocina prepara en paralelo (estimación de tiempos) |

## Seguridad

- Contraseñas con hash (Werkzeug) y sesión firmada con cookie `HttpOnly` + `SameSite=Lax`
- Control de acceso por rol en cada ruta y en la API; los intentos no autorizados quedan en la bitácora
- Bloqueo temporal tras 5 intentos de login fallidos
- El cliente solo accede con un **código secreto** no adivinable y ve únicamente su pedido (sin datos del personal)
- Los cambios de estado respetan el rol: la cocina prepara, el mozo entrega, el admin puede todo

## Funcionalidades destacadas

- Carta con **fotos**, filtros vegano / sin gluten / sin lácteos y avisos de alérgenos
- Descuentos automáticos (happy hour, volumen, grupos) calculados en el servidor
- Cola de cocina priorizada y tiempo de entrega estimado según la carga
- **Alertas con sonido** al mozo (pedido listo) y a la cocina (pedido nuevo)
- Inventario que se descuenta solo, con alertas de stock bajo
- Panel admin: ingresos, ticket promedio, margen, cancelaciones, tiempos de cocina, ventas por hora / categoría / mozo,
  mapa de calor de afluencia, comparativa con el periodo anterior, ingeniería de menú, Pareto ABC y predicción de demanda

Ver [TAREAS.md](TAREAS.md) para el reparto del equipo.
