import numpy as np
import pytest

from app.funcional.recomendador import (
    construir_matriz_coocurrencia,
    recomendar,
    recomendar_con_ids,
)


# PRUEBAS DE CONSTRUCCIÓN DE MATRIZ

def test_construir_matriz_coocurrencia():
    pedidos = [
        [1, 2, 3],
        [1, 2],
        [1, 3],
        [2, 3],
    ]
    plato_ids = [1, 2, 3]

    matriz = construir_matriz_coocurrencia(pedidos, plato_ids)

    esperada = np.array([
        [0, 2, 2],
        [2, 0, 2],
        [2, 2, 0],
    ])

    np.testing.assert_array_equal(matriz, esperada)


# PRUEBAS DE RECOMENDACIONES

def test_recomendar_devuelve_los_mas_frecuentes():
    matriz = np.array([
        [0, 5, 2],
        [5, 0, 3],
        [2, 3, 0],
    ])

    resultado = recomendar(0, matriz, 2)

    assert resultado == [1, 2]


def test_recomendar_excluye_el_mismo_plato():
    matriz = np.array([
        [0, 4, 2],
        [4, 0, 1],
        [2, 1, 0],
    ])

    resultado = recomendar(0, matriz, 2)

    assert 0 not in resultado


def test_recomendar_no_incluye_platos_sin_coocurrencia():
    matriz = np.array([
        [0, 3, 0],
        [3, 0, 0],
        [0, 0, 0],
    ])

    resultado = recomendar(0, matriz, 5)

    assert resultado == [1]


def test_recomendar_cero_resultados():
    matriz = np.array([
        [0, 3],
        [3, 0],
    ])

    assert recomendar(0, matriz, 0) == []


def test_recomendar_rechaza_n_negativo():
    matriz = np.array([
        [0, 3],
        [3, 0],
    ])

    with pytest.raises(ValueError):
        recomendar(0, matriz, -1)


def test_recomendar_rechaza_indice_fuera_de_rango():
    matriz = np.array([
        [0, 3],
        [3, 0],
    ])

    with pytest.raises(ValueError):
        recomendar(5, matriz, 2)


def test_recomendar_matriz_vacia():
    matriz = np.zeros((0, 0), dtype=int)

    with pytest.raises(ValueError):
        recomendar(0, matriz, 2)


def test_recomendar_rechaza_matriz_no_cuadrada():
    matriz = np.array([
        [0, 1, 2],
        [1, 0, 3],
    ])

    with pytest.raises(ValueError):
        recomendar(0, matriz, 2)


# PRUEBAS DE IDENTIFICADORES REALES


def test_recomendar_con_ids_reales():
    pedidos = [
        [10, 20],
        [10, 30],
        [10, 20],
    ]
    plato_ids = [10, 20, 30]

    matriz = construir_matriz_coocurrencia(pedidos, plato_ids)

    resultado = recomendar_con_ids(10, matriz, plato_ids, 2)

    assert resultado == [20, 30]


def test_recomendar_plato_inexistente():
    matriz = np.array([
        [0, 2],
        [2, 0],
    ])

    assert recomendar_con_ids(99, matriz, [10, 20], 2) == []


def test_recomendar_con_ids_rechaza_ids_duplicados():
    matriz = np.array([
        [0, 2],
        [2, 0],
    ])

    with pytest.raises(ValueError):
        recomendar_con_ids(10, matriz, [10, 10], 2)


def test_recomendar_con_ids_rechaza_cantidad_incorrecta():
    matriz = np.array([
        [0, 2],
        [2, 0],
    ])

    with pytest.raises(ValueError):
        recomendar_con_ids(10, matriz, [10], 2)

