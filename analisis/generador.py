"""Generador de datos sinteticos: simula varios dias de funcionamiento del restaurante.

Sirve para tener un historial realista con el que probar el analisis.  Los
patrones son intencionales (para que el analisis encuentre algo real):
  - horas pico en almuerzo (12-14) y cena (19-21)
  - mas movimiento viernes, sabado y domingo, con tendencia de crecimiento
  - platos que se piden juntos (hamburguesa + papas + gaseosa...)
  - cocina mas lenta en horas pico
  - ~4% de pedidos cancelados y algunos datos sucios (tiempos faltantes/absurdos)
    para que la limpieza de datos tenga trabajo que hacer
"""
from datetime import datetime, timedelta

import numpy as np

from app.extensions import db
from app.funcional.precios import Linea, calcular_total
from app.models import ItemPedido, Mesa, Pedido, Plato

PESO_HORA = {11: 1, 12: 5, 13: 8, 14: 5, 15: 1.5, 16: 1, 17: 1.5, 18: 3,
             19: 7, 20: 9, 21: 6, 22: 2}
PESO_DIA = [0.7, 0.75, 0.85, 1.0, 1.5, 1.8, 1.4]          # lunes ... domingo

PESO_PLATO = {
    "Hamburguesa clásica": 10, "Pizza pepperoni": 8, "Pizza margarita": 6, "Pasta alfredo": 5,
    "Pollo a la parrilla": 5, "Arroz con camarones": 3, "Hamburguesa vegana": 2,
    "Pizza vegetariana": 3, "Alitas BBQ": 4, "Nachos con queso": 4, "Ensalada fresca": 2,
    "Hummus con pan pita": 1, "Papas fritas": 1,
}
# Si piden X, con cierta probabilidad agregan Y
AFINIDAD = {
    "Hamburguesa clásica": {"Papas fritas": 0.65, "Gaseosa": 0.5, "Cerveza artesanal": 0.2},
    "Hamburguesa vegana": {"Papas fritas": 0.5, "Limonada": 0.4},
    "Pizza pepperoni": {"Gaseosa": 0.55, "Cerveza artesanal": 0.3},
    "Pizza margarita": {"Gaseosa": 0.4, "Limonada": 0.3},
    "Pizza vegetariana": {"Limonada": 0.4},
    "Alitas BBQ": {"Cerveza artesanal": 0.6, "Papas fritas": 0.3},
    "Nachos con queso": {"Cerveza artesanal": 0.4, "Gaseosa": 0.3},
    "Pasta alfredo": {"Jugo natural": 0.3, "Café": 0.2},
    "Pollo a la parrilla": {"Jugo natural": 0.4, "Limonada": 0.3},
    "Arroz con camarones": {"Limonada": 0.5, "Cerveza artesanal": 0.2},
}
BEBIDAS = ["Gaseosa", "Limonada", "Jugo natural", "Cerveza artesanal", "Café"]
POSTRES = ["Brownie con helado", "Flan de caramelo", "Ensalada de frutas"]


def _elegir(rng, pesos: dict) -> str:
    nombres = list(pesos)
    p = np.array([pesos[n] for n in nombres], dtype=float)
    return nombres[rng.choice(len(nombres), p=p / p.sum())]


def _armar_carrito(rng, comensales: int) -> dict[str, int]:
    """Platos de un pedido: principales por comensal + acompanantes por afinidad."""
    carrito: dict[str, int] = {}
    for _ in range(max(1, min(comensales, 4))):
        principal = _elegir(rng, PESO_PLATO)
        carrito[principal] = carrito.get(principal, 0) + 1
        for extra, prob in AFINIDAD.get(principal, {}).items():
            if rng.random() < prob:
                carrito[extra] = carrito.get(extra, 0) + 1
    if rng.random() < 0.30:
        postre = POSTRES[rng.integers(len(POSTRES))]
        carrito[postre] = carrito.get(postre, 0) + 1
    if not any(b in carrito for b in BEBIDAS) and rng.random() < 0.35:
        bebida = BEBIDAS[rng.integers(len(BEBIDAS))]
        carrito[bebida] = 1
    return carrito


def generar_historial(dias: int = 45, pedidos_base: int = 55, semilla: int = 42,
                      hasta: datetime | None = None) -> int:
    """Crea pedidos sinteticos de los ultimos `dias` dias (sin incluir hoy).

    Devuelve cuantos pedidos creo.  Usar la misma `semilla` da siempre los mismos datos.
    """
    rng = np.random.default_rng(semilla)
    platos = {p.nombre: p for p in Plato.query.all()}
    mesas = Mesa.query.all()
    if not platos or not mesas:
        raise RuntimeError("Primero siembra el menu y las mesas (flask sembrar)")

    hoy = (hasta or datetime.now()).replace(hour=0, minute=0, second=0, microsecond=0)
    horas = np.array(list(PESO_HORA))
    prob_hora = np.array(list(PESO_HORA.values()), dtype=float)
    prob_hora /= prob_hora.sum()
    peso_max = max(PESO_HORA.values())
    creados = 0

    for offset in range(dias, 0, -1):
        dia = hoy - timedelta(days=offset)
        crecimiento = 1 + 0.006 * (dias - offset)               # el negocio crece ~0.6%/dia
        n_pedidos = rng.poisson(pedidos_base * PESO_DIA[dia.weekday()] * crecimiento)

        for hora in rng.choice(horas, size=n_pedidos, p=prob_hora):
            creado = dia + timedelta(hours=int(hora), minutes=int(rng.integers(0, 60)),
                                     seconds=int(rng.integers(0, 60)))
            comensales = int(min(8, 1 + rng.geometric(0.5)))
            carrito = _armar_carrito(rng, comensales)
            lineas = [(platos[n], c) for n, c in carrito.items()]
            d = calcular_total([Linea(p.precio, c) for p, c in lineas], int(hora), comensales)

            pedido = Pedido(mesa=mesas[rng.integers(len(mesas))], comensales=comensales,
                            creado_en=creado, subtotal=d.subtotal, descuento=d.descuento,
                            total=d.total)
            pedido.items = [ItemPedido(plato=p, cantidad=c, precio_unitario=p.precio)
                            for p, c in lineas]
            _simular_tiempos(rng, pedido, int(hora), peso_max)
            db.session.add(pedido)
            creados += 1
        db.session.commit()
    return creados


def _simular_tiempos(rng, pedido: Pedido, hora: int, peso_max: float) -> None:
    """Asigna estado y marcas de tiempo; en hora pico la cocina se demora mas."""
    if rng.random() < 0.04:                                     # cancelado
        pedido.estado = "cancelado"
        return

    carga = 1 + 0.9 * PESO_HORA[hora] / peso_max                # 1.0 (tranquilo) a 1.9 (pico)
    espera = rng.exponential(1.5 * carga)
    prep = pedido.tiempo_prep_min * rng.lognormal(0, 0.18) * (0.85 + 0.15 * carga)
    pedido.estado = "entregado"
    pedido.inicio_prep_en = pedido.creado_en + timedelta(minutes=espera)
    pedido.listo_en = pedido.inicio_prep_en + timedelta(minutes=prep)
    pedido.entregado_en = pedido.listo_en + timedelta(minutes=float(rng.uniform(1, 4)))

    suerte = rng.random()
    if suerte < 0.01:                                           # marca de tiempo perdida
        pedido.listo_en = None
    elif suerte < 0.015:                                        # error de registro absurdo
        pedido.listo_en = pedido.inicio_prep_en + timedelta(minutes=prep * 8)
