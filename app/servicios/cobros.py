"""Cobro, propina y division de la cuenta (usa las funciones puras de precios.py)."""
from datetime import datetime

from app.funcional.precios import dividir_cuenta, propina_sugerida, redondear
from app.models import METODOS_PAGO, Pedido

PROPINA_MAXIMA = 0.30
MAX_PERSONAS = 30


class ErrorCobro(ValueError):
    """Datos invalidos al cobrar o dividir una cuenta (se devuelve como error 400)."""


def validar_propina(pct) -> float:
    try:
        pct = float(pct or 0)
    except (TypeError, ValueError):
        raise ErrorCobro("La propina debe ser un porcentaje numérico")
    if not 0 <= pct <= PROPINA_MAXIMA:
        raise ErrorCobro(f"La propina debe estar entre 0% y {PROPINA_MAXIMA:.0%}")
    return pct


def cuenta_dividida(total: float, personas, propina_pct=0.0) -> dict:
    """Total con propina repartido en partes iguales, sin perder ni inventar centavos."""
    try:
        personas = int(personas)
    except (TypeError, ValueError):
        raise ErrorCobro("'personas' debe ser un número entero")
    if not 1 <= personas <= MAX_PERSONAS:
        raise ErrorCobro(f"Las personas deben estar entre 1 y {MAX_PERSONAS}")
    propina = propina_sugerida(total, validar_propina(propina_pct))
    total_final = redondear(total + propina)
    partes = dividir_cuenta(total_final, personas)
    return {"total": total, "propina": propina, "total_con_propina": total_final,
            "personas": personas, "partes": partes, "parte_mayor": max(partes)}


def cobrar(pedido: Pedido, metodo: str, propina_pct=0.0, ahora: datetime | None = None) -> Pedido:
    """Registra el pago de un pedido ya entregado: cierra la cuenta y libera la mesa."""
    if pedido.estado != "entregado":
        raise ErrorCobro("Solo se puede cobrar un pedido ya entregado")
    if pedido.pagado:
        raise ErrorCobro("Este pedido ya fue cobrado")
    if metodo not in METODOS_PAGO:
        raise ErrorCobro(f"Método de pago no válido. Usa: {', '.join(METODOS_PAGO)}")
    ahora = ahora or datetime.now()
    pedido.propina = propina_sugerida(pedido.total, validar_propina(propina_pct))
    pedido.metodo_pago = metodo
    pedido.pagado_en = ahora
    for aviso in pedido.avisos:                      # la cuenta ya se cobro: el aviso queda atendido
        if aviso.pendiente and aviso.tipo == "cuenta":
            aviso.atender(ahora)
    return pedido
