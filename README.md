# SmartMenu

Sistema web de **pedidos inteligentes para restaurantes** (Python, Flask, PostgreSQL, pandas, numpy, matplotlib).
Precios en **soles (S/)**.

## Cómo funciona (flujo por roles)

```
 MOZO ──toma el pedido──▶ COCINA ──lo prepara──▶ "LISTO" ──ALERTA──▶ MOZO ──entrega──▶ CLIENTE ──paga──▶ MESA LIBRE
   │                                                                                       ▲
   └──── genera un QR con un código secreto ───────────────────────────────────────────────┘
        (el cliente sigue su pedido en tiempo real, llama al mozo, pide la cuenta, la divide y califica)
```

| Rol | Entra a | Qué hace |
|---|---|---|
| **Mozo** | `/mozo/` | Elige la mesa, toma el pedido (carta con fotos, filtros de dieta y alérgenos, sugerencias «Te puede gustar»), agrega platos a un pedido abierto, entrega, **cobra** (método y propina) y libera la mesa. Recibe **alertas con sonido** cuando un pedido está listo o un cliente lo llama. |
| **Cocina** | `/cocina` | Ve los pedidos entrantes priorizados, los marca *en preparación* y *listo* (esto avisa al mozo). Si el mozo agrega platos, la tarjeta se actualiza. No entrega. |
| **Administrador** | `/admin/` | KPIs y gráficos de ventas, pedidos, menú y fotos, inventario, usuarios, **bitácora (logs)**, análisis avanzado y **exportación a CSV**. Puede ver todo. |
| **Cliente** | `/seguimiento/<código>` | Sin cuenta: escanea el QR y ve el avance y los minutos restantes; puede **llamar al mozo**, **pedir la cuenta**, **dividirla** entre varias personas con propina y **calificar** el servicio. |

## Usuarios de demostración

| Usuario | Contraseña | Rol |
|---|---|---|
| `admin` | `admin123` | Administrador |
| `mozo1` / `mozo2` | `mozo123` | Mozo |
| `cocina1` | `cocina123` | Cocina |

> Son claves de **desarrollo**. Cada usuario puede cambiar la suya en **Mi cuenta** (clic en su nombre) y el administrador puede restablecerlas en *Admin → Usuarios*.

## Arquitectura

```
HTML + CSS + JS  →  Flask (app/rutas)  →  Servicios (app/servicios)  →  PostgreSQL
                                                 ↓
                              Pandas + NumPy + Matplotlib (analisis/)
```

| Carpeta | Contenido | Paradigma |
|---|---|---|
| `app/models/` | `Usuario`, `Auditoria`, `Plato`, `Ingrediente`, `Mesa`, `Pedido`, `Aviso`… y la máquina de estados del pedido | **POO** |
| `app/descuentos.py` | Reglas de descuento: clase base abstracta `ReglaDescuento` y subclases (`HappyHour`, `DescuentoVolumen`, `DescuentoGrupo`) | **POO** (herencia y polimorfismo) |
| `app/funcional/` | Precios, prioridad de cocina, filtros dietéticos, **permisos por rol**, recomendador, ajuste de tiempos | **Funcional** |
| `app/auth.py` | Sesión, decoradores por rol, **protección CSRF**, bitácora, bloqueo por intentos fallidos | |
| `app/servicios/` | Pedidos, inventario, cobros, avisos y calificación, tiempos aprendidos, recomendaciones y métricas del panel | Integración |
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

**Las tablas y los usuarios NO se crean al arrancar la app**: se inicializan con comandos.

```bash
flask --app run preparar-demo      # TODO en uno: reinicia la base, siembra menú/mesas/usuarios y simula 45 días de ventas
python run.py                      # http://127.0.0.1:5000
```

O por pasos:

```bash
flask --app run sembrar                  # crea tablas + menú (con fotos) + 10 mesas + usuarios de prueba (no duplica)
flask --app run generar-datos --dias 45  # historial simulado con pagos, propinas y calificaciones
flask --app run reset-db --yes           # BORRA todo y recrea las tablas (necesario si cambió el esquema)
flask --app run reporte                  # tablas por consola + gráficos en docs/graficos
```

> **Si ya tenías la base de datos de una versión anterior**, el esquema cambió (cobros, avisos, calificación…): ejecuta `flask --app run preparar-demo` (**borra los datos**).

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
- **Protección CSRF**: toda petición que modifica datos exige un token que el navegador envía solo
- Control de acceso por rol en cada ruta y en la API; los intentos no autorizados quedan en la bitácora
- Bloqueo temporal tras 5 intentos de login fallidos; cada usuario puede cambiar su clave (mínimo 8 caracteres)
- El cliente solo accede con un **código secreto** no adivinable y ve únicamente su pedido (sin datos del personal)
- Los cambios de estado respetan el rol: la cocina prepara, el mozo entrega y cobra, el admin puede todo
- Cabeceras de seguridad (`X-Frame-Options`, `X-Content-Type-Options`, `Referrer-Policy`); los comentarios de clientes se muestran siempre como texto

## Funcionalidades destacadas

- Carta con **fotos**, filtros vegano / sin gluten / sin lácteos y avisos de alérgenos
- Descuentos automáticos (happy hour, volumen, grupos) como **jerarquía de clases** fácil de ampliar
- Cola de cocina priorizada y **tiempo de entrega estimado que aprende del historial real** de la cocina por hora
- **Alertas con sonido** al mozo (pedido listo, cliente que lo llama) y a la cocina (pedido nuevo)
- **Recomendador** («Te puede gustar») basado en lo que se pide junto, calculado con NumPy
- Inventario que se descuenta solo, **se repone al cancelar** y avisa del stock bajo
- Cobro con método (efectivo, tarjeta, Yape, Plin) y propina; la mesa se libera al cobrar
- El cliente divide la cuenta sin perder centavos, pide la cuenta y califica
- Panel admin: ingresos, ticket promedio, margen, cancelaciones, tiempos de cocina, propinas, satisfacción, métodos de pago,
  ventas por hora / categoría / mozo, mapa de calor, comparativa con el periodo anterior, ingeniería de menú,
  Pareto ABC, predicción de demanda y **exportación a CSV** (abre bien en Excel)

## Capturas

Las capturas reales de cada pantalla (con su descripción) están en [docs/capturas](docs/capturas/README.md).
Ver [TAREAS.md](TAREAS.md) para el estado del proyecto y [docs/INFORME.md](docs/INFORME.md) para el borrador del informe.
