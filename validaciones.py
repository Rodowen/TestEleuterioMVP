"""Validaciones de entradas para ThermalGuard MVP."""

from __future__ import annotations


def validar_positivo(valor: float, nombre: str) -> None:
    if valor is None:
        raise ValueError(f"{nombre} no puede ser nulo.")
    if not isinstance(valor, (int, float)):
        raise ValueError(f"{nombre} debe ser numérico.")
    if valor <= 0:
        raise ValueError(f"{nombre} debe ser mayor que cero.")


def validar_rango(valor: float, nombre: str, minimo: float, maximo: float) -> None:
    if valor < minimo or valor > maximo:
        raise ValueError(f"{nombre} debe estar entre {minimo} y {maximo}.")


def validar_entradas(
    voltaje_v: float,
    potencia: float,
    in_termico_a: float,
    multiplicador_arranque: float,
    tiempo_arranque_ms: float,
    factor_potencia: float = 1.0,
    eficiencia: float = 1.0,
) -> None:
    validar_positivo(voltaje_v, "Voltaje")
    validar_positivo(potencia, "Potencia")
    validar_positivo(in_termico_a, "In del térmico")
    validar_positivo(multiplicador_arranque, "Multiplicador de arranque")
    validar_positivo(tiempo_arranque_ms, "Tiempo de arranque")
    validar_positivo(factor_potencia, "Factor de potencia")
    validar_positivo(eficiencia, "Eficiencia")

    validar_rango(voltaje_v, "Voltaje", 12.0, 1000.0)
    validar_rango(in_termico_a, "In del térmico", 0.5, 630.0)
    validar_rango(multiplicador_arranque, "Multiplicador de arranque", 1.0, 12.0)
    validar_rango(tiempo_arranque_ms, "Tiempo de arranque", 10.0, 5000.0)
    validar_rango(factor_potencia, "Factor de potencia", 0.1, 1.0)
    validar_rango(eficiencia, "Eficiencia", 0.1, 1.0)
