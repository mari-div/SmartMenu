# SmartMenu: pedidos inteligentes para restaurantes

**Informe del proyecto** · borrador generado a partir del código y las pruebas reales del repositorio.
Los textos entre `[corchetes]` deben completarlos los integrantes.

---

## Portada

- **Universidad / Facultad:** [completar]
- **Curso:** [completar] · **Docente:** [completar]
- **Proyecto:** SmartMenu: pedidos inteligentes para restaurantes
- **Integrantes:** Mari Ramos Aguilar · Leslie [apellidos] · Leopoldo Brito Ruiz
- **Fecha:** [completar] · **Semestre:** [completar]

---

## 1. Introducción

En muchos restaurantes el pedido viaja en papel, la cocina no tiene un orden claro de preparación, el mozo no sabe
cuándo un plato está listo, el cliente no sabe cuánto falta y el dueño decide sin datos. **SmartMenu** es un sistema web que
conecta a los cuatro actores en un solo flujo en tiempo real: el mozo toma el pedido, la cocina lo prepara con prioridad, el mozo
recibe una alerta cuando está listo, el cliente sigue su pedido con un código QR (y puede llamar al mozo, pedir y dividir la
cuenta y calificar) y el administrador analiza las ventas con indicadores y gráficos.

El proyecto se desarrolló en **Python** con **Flask**, **PostgreSQL**, **pandas**, **NumPy** y **Matplotlib**, aplicando de forma
integrada los paradigmas de **programación funcional** y **orientada a objetos**. Los precios se expresan en soles (S/).

## 2. Objetivos

**Objetivo general.** Desarrollar un sistema de gestión de pedidos para restaurantes que agilice la atención y permita tomar
decisiones basadas en datos, aplicando programación funcional y orientada a objetos.

**Objetivos específicos.**

1. Implementar el flujo completo de un pedido (mozo → cocina → mozo → cliente → cobro) con control de acceso por rol.
2. Diseñar la lógica de negocio con funciones puras (precios, prioridad de cocina, filtros, permisos) y clases (modelos, reglas de descuento).
3. Analizar los datos de ventas con pandas y NumPy: limpieza, transformación, métricas, clasificación de platos y predicción de demanda.
4. Presentar resultados claros con gráficos interactivos y tablas, y exportarlos a CSV.
5. Verificar el sistema con pruebas automáticas y documentar el proyecto.

## 3. Alcance y herramientas

| Herramienta | Uso |
|---|---|
| Python 3.12 | Lenguaje principal |
| Flask + Flask-SQLAlchemy | Aplicación web, rutas y acceso a datos |
| PostgreSQL (SQLite en pruebas) | Base de datos |
| pandas y NumPy | Limpieza, métricas, predicción, recomendador y mapa de calor |
| Matplotlib | Gráficos del análisis avanzado |
| Chart.js | Gráficos interactivos del panel (incluido en el proyecto) |
| `qrcode` | Código QR de seguimiento |
| pytest | Pruebas automáticas |
| HTML, CSS y JavaScript | Interfaz, con modo claro y oscuro y diseño para celular |

**Límites.** Los datos del análisis son **simulados** (generador reproducible con semilla). La estimación de tiempos y la
predicción de demanda son modelos simples, adecuados para un proyecto académico.

## 4. Diseño

### 4.1 Arquitectura

```
HTML + CSS + JS  →  Flask (app/rutas)  →  Servicios (app/servicios)  →  PostgreSQL
                                                 ↓
                              Pandas + NumPy + Matplotlib (analisis/)
```

| Capa | Carpeta | Responsabilidad |
|---|---|---|
| Modelos (POO) | `app/models/`, `app/descuentos.py` | Usuario, Pedido, Plato, Mesa, Aviso… y reglas de descuento |
| Lógica pura (funcional) | `app/funcional/` | Precios, prioridad de cocina, filtros, permisos, recomendador, ajuste de tiempos |
| Servicios | `app/servicios/` | Integran modelos y funciones: pedidos, inventario, cobros, avisos, tiempos, recomendaciones, métricas |
| Rutas | `app/rutas/` | Un módulo por rol: `auth`, `mozo`, `cocina`, `cliente`, `admin`, `api` |
| Seguridad | `app/auth.py` | Sesión, roles, CSRF, bitácora, bloqueo de intentos |
| Análisis | `analisis/` | Carga SQL, limpieza, métricas, gráficos, generador de datos |

### 4.2 Modelo de datos

Tablas principales: `usuarios`, `auditoria`, `categorias`, `platos`, `ingredientes`, `plato_ingredientes`, `mesas`, `pedidos`,
`items_pedido` y `avisos`. Cada pedido guarda quién lo tomó, un **código secreto** (para el QR), las marcas de tiempo de cada
etapa (base del análisis de tiempos), el cobro (método, propina y hora) y la calificación del cliente.

### 4.3 Flujo y estados del pedido

`pendiente → en preparación → listo → entregado` (o `cancelado` desde pendiente o en preparación). Tras entregarse, el pedido queda
**por cobrar** hasta que el mozo lo cobra; entonces la mesa se libera. La cocina puede preparar, el mozo entrega y cobra, y el
administrador puede todo. Estas reglas son una función pura (`app/funcional/permisos.py`).

### 4.4 Roles y seguridad

Contraseñas con hash, sesión firmada, **protección CSRF**, control de acceso por rol en cada ruta y en la API, bloqueo temporal tras
intentos fallidos, bitácora de acciones y acceso del cliente solo con un código secreto. Capturas: `docs/capturas/` (login, usuarios, bitácora).

## 5. Aplicación de paradigmas de programación

### 5.1 Programación funcional (`app/funcional/`)

Funciones puras, sin acceso a la base de datos, fáciles de probar:

- `precios.py`: `subtotal` con `map` + `reduce`, `componer` (composición de funciones), `mejor_descuento`, `dividir_cuenta` (sin perder centavos).
- `filtros.py`: predicados (`es_vegano`, `sin_gluten`…) combinados con `filter` y `all`; alérgenos con `any(map(...))`.
- `cocina.py`: `prioridad` y `ordenar_cola` (`sorted` con `lambda`), `estimar_minutos_entrega` y `factor_ajuste` (mediana robusta).
- `permisos.py`: reglas por rol como datos inmutables (`frozenset`) y `puede_cambiar_estado`.
- `recomendador.py`: matriz de co-ocurrencia con NumPy.

### 5.2 Programación orientada a objetos

- **Modelos con comportamiento:** `Pedido` encapsula su estado y valida las transiciones (`cambiar_estado`, `avanzar`, `puede_pasar_a`);
  `Usuario` encapsula la contraseña (`set_password`, `check_password`); `Aviso.atender()`.
- **Herencia y polimorfismo** (`app/descuentos.py`): `ReglaDescuento` es una clase base **abstracta** que define `porcentaje()` y reutiliza
  `aplicar()`; `HappyHour`, `DescuentoVolumen` y `DescuentoGrupo` la heredan y cada una calcula su porcentaje a su manera. El código
  que usa las reglas las recorre sin conocer su tipo (polimorfismo), y agregar una regla nueva solo requiere una subclase.
- **Excepciones propias** que heredan de `ValueError` (`ErrorPedido`, `ErrorCobro`, `ErrorAviso`, `TransicionInvalida`).

### 5.3 Integración de ambos paradigmas

Las reglas de descuento son **objetos invocables** (`__call__`) que la función pura `mejor_descuento` trata como funciones.
`app/servicios/pedidos.py` convierte los objetos en datos, llama a las funciones puras y guarda el resultado.

## 6. Análisis y tratamiento de datos (pandas y NumPy)

**Pipeline** (`analisis/`): carga SQL → limpieza → transformación → métricas y gráficos.

| Paso | Archivo | Qué hace |
|---|---|---|
| Carga | `datos.py` | `pd.read_sql` con las ventas por línea de pedido |
| Limpieza | `limpieza.py` | Quita duplicados, excluye cancelados y marca **tiempos atípicos** con la regla IQR (`np.nanpercentile`, `np.where`) |
| Transformación | `limpieza.py` | Ingresos, margen, hora, día de la semana y tiempos de espera y preparación |
| Métricas | `metricas.py` | KPIs, ventas por hora y día, **Pareto ABC** (`np.cumsum`, `np.select`), **matriz de ingeniería de menú** (estrella, vaca, puzzle, perro) y **predicción de demanda** (tendencia con `np.polyfit` + efecto del día) |
| Panel | `app/servicios/admin.py` | Comparativa con el periodo anterior, ventas por mozo y categoría, métodos de pago, satisfacción y mapa de calor (matriz NumPy) |

**Ejemplo de depuración** (captura `admin_resumen.png`, 30 días): 3,114 pedidos leídos → 147 cancelados excluidos, 49 sin marca de
tiempo y 51 con tiempo atípico descartado → **2,967 pedidos válidos**.

**Datos simulados.** `analisis/generador.py` crea un historial reproducible (semilla) con horas pico, afinidades entre platos, cocina
más lenta en horas pico, cancelaciones y errores intencionales de registro, pagos, propinas y calificaciones que empeoran con la espera.

## 7. Pruebas y resultados

**182 pruebas automáticas** (137 funciones; algunas parametrizadas) que pasan con `python -m pytest`:

| Archivo | Qué verifica | Funciones |
|---|---|---|
| `test_precios.py`, `test_cocina_funcional.py`, `test_filtros.py` | Lógica pura: descuentos, división de cuenta, prioridad, filtros de dieta | 22 |
| `test_descuentos.py` | Herencia y polimorfismo de las reglas | 8 |
| `test_pedidos.py`, `test_rutas.py` | Estados, inventario, flujo mozo → cocina → cliente | 17 |
| `test_auth_roles.py`, `test_seguridad.py` | Login, matriz de acceso, bloqueo, bitácora, CSRF, cambio de clave | 28 |
| `test_negocio.py` | Cobro, avisos, calificación, agregar platos, stock al cancelar, tiempos, sugerencias, CSV | 28 |
| `test_admin.py` | KPIs, menú, stock, usuarios, logs | 12 |
| `test_analisis.py`, `test_recomendador.py` | Limpieza, métricas, gráficos y recomendador | 22 |

**Resultados visuales** (carpeta `docs/capturas/`, con descripción de cada una): panel del mozo, carta, QR, seguimiento del cliente,
cocina, KPIs y gráficos del administrador, matriz de menú, Pareto, predicción de demanda y la salida real de pytest.

## 8. Documentación y trabajo en equipo

- `README.md`: instalación, roles, seguridad, QR en red local y comandos.
- Código comentado en español (docstrings y el porqué de cada decisión).
- Repositorio en GitHub con una rama por integrante y Pull Requests.

| Integrante | Aportes principales |
|---|---|
| Mari | Recomendador con NumPy, servicio de inventario y endpoint de recomendaciones |
| Leslie | Matriz de ingeniería de menú, predicción de demanda y sus gráficos |
| Leopoldo | Arquitectura base, roles y seguridad, flujo con QR, cobro y avisos, panel de administración e interfaz |

[Cada integrante puede ampliar aquí su parte y lo aprendido.]

## 9. Conclusiones

1. El sistema cumple el flujo completo de un pedido y lo hace visible en tiempo real para el mozo, la cocina, el cliente y el administrador.
2. Separar la lógica en **funciones puras** y **clases** facilitó las pruebas (182 casos) y permitió ampliar el sistema (por ejemplo, una regla de descuento nueva es una subclase).
3. pandas y NumPy permitieron convertir los registros en decisiones: qué platos promocionar, cuándo se llena el local y cuánto demanda cada plato.
4. La seguridad (roles, CSRF, bitácora) y la trazabilidad de cada acción son necesarias en un sistema que maneja pedidos y cobros.
5. [Aprendizajes y dificultades del equipo.]

**Limitaciones y trabajo futuro.** Datos simulados (validar con ventas reales), pruebas con PostgreSQL y celulares en red local,
actualizaciones en vivo con SSE o WebSockets, gestión de mesas desde el panel e impresión de comandas.

## 10. Fuentes

- Documentación de Flask: https://flask.palletsprojects.com/
- Documentación de SQLAlchemy: https://docs.sqlalchemy.org/
- Documentación de pandas: https://pandas.pydata.org/docs/
- Documentación de NumPy: https://numpy.org/doc/
- Documentación de Matplotlib: https://matplotlib.org/stable/
- Documentación de PostgreSQL: https://www.postgresql.org/docs/
- Chart.js: https://www.chartjs.org/docs/
- pytest: https://docs.pytest.org/
- OWASP, falsificación de petición en sitios cruzados (CSRF): https://owasp.org/www-community/attacks/csrf
- Fotografías de los platos: Unsplash, https://unsplash.com
- Tipografías Playfair Display y Karla: Google Fonts, https://fonts.google.com
- [Material de clase y bibliografía del curso: completar]

## Anexo: capturas

Ver `docs/capturas/README.md`: cada archivo indica qué muestra y qué criterio de la rúbrica respalda.
