"""Paradigma FUNCIONAL: recomendaciones de platos por coocurrencia.

Utiliza una matriz NumPy para identificar platos que suelen pedirse juntos.
Las funciones reciben los datos como argumentos y no modifican la matriz.
"""
import numpy as np


def construir_matriz_coocurrencia(pedidos: list[list[int]],
                                  plato_ids: list[int]) -> np.ndarray:
    """Construye una matriz que cuenta los platos solicitados juntos.

    Cada lista de pedidos contiene los IDs de los platos de un pedido.
    La diagonal se conserva en cero.
    """
    cantidad = len(plato_ids)
    matriz = np.zeros((cantidad, cantidad), dtype=int)

    indices = {plato_id: i for i, plato_id in enumerate(plato_ids)}

    for pedido in pedidos:
        # Un plato repetido dentro del mismo pedido cuenta una sola vez.
        posiciones = sorted({
            indices[plato_id]
            for plato_id in pedido
            if plato_id in indices
        })

        for i in posiciones:
            for j in posiciones:
                if i != j:
                    matriz[i, j] += 1

    return matriz


def recomendar(plato_id: int, matriz: np.ndarray, n: int) -> list[int]:
    """Devuelve los IDs de los n platos con mayor coocurrencia.

    La matriz debe utilizar el mismo orden de IDs que la lista plato_ids
    empleada al construirla. Para obtener los IDs, se usa recomendar_con_ids.
    """
    if matriz.ndim != 2 or matriz.shape[0] != matriz.shape[1]:
        raise ValueError("La matriz debe ser cuadrada.")

    if not isinstance(n, int) or n < 0:
        raise ValueError("n debe ser un entero mayor o igual a cero.")

    if not isinstance(plato_id, int) or not 0 <= plato_id < matriz.shape[0]:
        raise ValueError("plato_id debe ser un índice válido de la matriz.")

    if n == 0:
        return []

    puntuaciones = matriz[plato_id].copy()
    puntuaciones[plato_id] = 0

    indices = np.arange(matriz.shape[0])
    ordenados = np.lexsort((indices, -puntuaciones))

    recomendados = [
        int(i) for i in ordenados
        if i != plato_id and puntuaciones[i] > 0
    ]

    return recomendados[:n]


def recomendar_con_ids(plato_id: int, matriz: np.ndarray,
                       plato_ids: list[int], n: int) -> list[int]:
    """Recomienda utilizando el ID real del plato, no su posición."""
    if len(plato_ids) != matriz.shape[0]:
        raise ValueError("La cantidad de IDs no coincide con la matriz.")

    if len(set(plato_ids)) != len(plato_ids):
        raise ValueError("Los IDs de platos no deben repetirse.")

    if plato_id not in plato_ids:
        return []

    indice = plato_ids.index(plato_id)
    indices_recomendados = recomendar(indice, matriz, n)

    return [plato_ids[i] for i in indices_recomendados]
