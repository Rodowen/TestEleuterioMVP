"""Generación de reporte PDF y CSV para resultados de simulación."""

from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path
from typing import Dict, List

import matplotlib.pyplot as plt
import numpy as np
from fpdf import FPDF


def _fmt(valor: float | None, sufijo: str = "") -> str:
    if valor is None:
        return "N/A"
    return f"{valor:.4f}{sufijo}"


def exportar_reporte_pdf(
    ruta_salida: str | Path,
    parametros: Dict[str, str | float],
    resultados: Dict[str, np.ndarray | float | bool | None],
    ruta_grafico: str | Path | None = None,
    resumen_opciones: List[Dict[str, str]] | None = None,
) -> Path:
    output = Path(ruta_salida)
    output.parent.mkdir(parents=True, exist_ok=True)

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=12)
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "ThermalGuard MVP - Reporte de Simulación", ln=True)

    pdf.set_font("Helvetica", size=10)
    pdf.cell(0, 7, f"Fecha: {datetime.now().isoformat(sep=' ', timespec='seconds')}", ln=True)
    pdf.ln(2)

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Parámetros de entrada", ln=True)
    pdf.set_font("Helvetica", size=10)
    for clave, valor in parametros.items():
        pdf.cell(0, 6, f"- {clave}: {valor}", ln=True)

    pdf.ln(2)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Resultados", ln=True)
    pdf.set_font("Helvetica", size=10)

    pdf.cell(0, 6, f"- Corriente nominal estimada: {_fmt(resultados.get('corriente_nominal_a'), ' A')}", ln=True)
    trip = bool(resultados.get("trip"))
    pdf.cell(0, 6, f"- Estado: {'TRIP' if trip else 'SEGURO'}", ln=True)
    pdf.cell(0, 6, f"- Tiempo estimado de trip: {_fmt(resultados.get('t_trip_s'), ' s')}", ln=True)
    pdf.cell(0, 6, f"- Corriente en trip: {_fmt(resultados.get('i_trip_a'), ' A')}", ln=True)

    pdf.ln(3)
    pdf.multi_cell(
        0,
        6,
        "Nota: Este resultado es una aproximación educativa basada en un modelo simplificado. "
        "Para diseño definitivo, contrastar con curvas certificadas del fabricante.",
    )

    if resumen_opciones:
        pdf.ln(2)
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 8, "Tabla comparativa de opciones", ln=True)
        pdf.set_font("Helvetica", size=10)
        for item in resumen_opciones:
            pdf.cell(0, 6, f"- {item['opcion']}: {item['estado']}", ln=True)

    if ruta_grafico is not None:
        img = Path(ruta_grafico)
        if img.exists():
            pdf.add_page()
            pdf.set_font("Helvetica", "B", 12)
            pdf.cell(0, 8, "Gráfico de simulación", ln=True)
            pdf.image(str(img), x=10, y=24, w=190)

    pdf.output(str(output))
    return output


def guardar_figura_png(fig, ruta_salida: str | Path) -> Path:
    output = Path(ruta_salida)
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return output


def exportar_ranking_csv(ruta_salida: str | Path, resumen_opciones: List[Dict[str, str]]) -> Path:
    output = Path(ruta_salida)
    output.parent.mkdir(parents=True, exist_ok=True)

    with output.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["opcion", "estado"])
        writer.writeheader()
        for item in resumen_opciones:
            writer.writerow(item)

    return output
