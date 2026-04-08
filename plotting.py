"""Utilidades de visualización para ThermalGuard MVP."""

from __future__ import annotations

from typing import Dict, List

import matplotlib.pyplot as plt
import numpy as np


def crear_figura_comparativa(simulaciones: List[Dict[str, object]]):
    """Construye figura comparando múltiples térmicos para la misma carga."""
    if not simulaciones:
        raise ValueError("No hay simulaciones para graficar.")

    fig, ax = plt.subplots(figsize=(11, 7))
    colores = ["tab:red", "tab:orange", "tab:green", "tab:purple", "tab:brown"]

    data_base = simulaciones[0]["data"]
    tiempo_s = data_base["tiempo_s"]
    corriente_carga_a = data_base["corriente_carga_a"]
    corriente_nominal_a = float(data_base.get("corriente_nominal_a", 0.0))
    corriente_pico_a = float(data_base.get("corriente_pico_a", 0.0))
    ax.loglog(corriente_carga_a, tiempo_s, "b", linewidth=2.3, label="Curva de carga")

    if corriente_nominal_a > 0:
        ax.axvline(corriente_nominal_a, color="tab:blue", linestyle=":", linewidth=1.5, label=f"I nominal {corriente_nominal_a:.2f} A")
    if corriente_pico_a > 0:
        ax.axvline(corriente_pico_a, color="tab:cyan", linestyle=":", linewidth=1.5, label=f"I pico {corriente_pico_a:.2f} A")

    for i, item in enumerate(simulaciones):
        label = item["label"]
        data = item["data"]
        color = colores[i % len(colores)]

        corriente_malla_a = data["corriente_malla_a"]
        t_min = data["t_disparo_min_s"]
        t_max = data["t_disparo_max_s"]

        ax.loglog(corriente_malla_a, t_min, linestyle="--", color=color, linewidth=1.3)
        ax.loglog(corriente_malla_a, t_max, linestyle="-", color=color, linewidth=1.3, label=f"{label}")

        if data.get("trip"):
            ax.scatter([data["i_trip_a"]], [data["t_trip_s"]], color=color, s=50, zorder=5)

    ax.set_xlabel("Corriente [A]")
    ax.set_ylabel("Tiempo [s]")
    ax.set_title("ThermalGuard - Comparación de opciones de protección")
    ax.grid(which="both", linestyle=":", alpha=0.6)
    ax.legend()
    return fig
