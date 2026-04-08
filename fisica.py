"""Módulo de cálculo eléctrico para ThermalGuard MVP."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Literal, Tuple

import numpy as np

TipoCarga = Literal["resistencia", "motor"]
TipoCurva = Literal["B", "C", "D"]
UnidadPotencia = Literal["W", "HP"]
TipoSistema = Literal["monofasico", "trifasico"]

HP_A_W = 745.7


@dataclass(frozen=True)
class ParametrosSimulacion:
    """Contenedor de parámetros de entrada para la simulación."""

    voltaje_v: float
    potencia: float
    unidad_potencia: UnidadPotencia
    tipo_carga: TipoCarga
    in_termico_a: float
    curva_termica: TipoCurva
    sistema_fases: TipoSistema = "monofasico"
    fabricante_curva: str = "generica_iec"
    modelo_certificado_id: str | None = None
    factor_potencia: float = 0.9
    eficiencia: float = 0.9
    multiplicador_arranque: float = 6.0
    tiempo_arranque_ms: float = 200.0


CURVAS_IEC: Dict[TipoCurva, Dict[str, Tuple[float, float]]] = {
    "B": {"magnetica": (3.0, 5.0)},
    "C": {"magnetica": (5.0, 10.0)},
    "D": {"magnetica": (10.0, 20.0)},
}


def cargar_curvas_desde_json(ruta: str | Path = "curvas.json") -> Dict[str, dict]:
    """Carga catálogo de curvas desde JSON con fallback seguro."""
    path = Path(ruta)
    if not path.exists():
        return {
            "generica_iec": {
                "nombre": "Genérica IEC 60898-1",
                "B": {"magnetica": list(CURVAS_IEC["B"]["magnetica"])},
                "C": {"magnetica": list(CURVAS_IEC["C"]["magnetica"])},
                "D": {"magnetica": list(CURVAS_IEC["D"]["magnetica"])},
            }
        }

    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict) and data:
            return data
    except (OSError, ValueError):
        pass

    return {
        "generica_iec": {
            "nombre": "Genérica IEC 60898-1",
            "B": {"magnetica": list(CURVAS_IEC["B"]["magnetica"])},
            "C": {"magnetica": list(CURVAS_IEC["C"]["magnetica"])},
            "D": {"magnetica": list(CURVAS_IEC["D"]["magnetica"])},
        }
    }


def cargar_catalogo_modelos_json(ruta: str | Path = "curvas_modelos.json") -> Dict[str, dict]:
    """Carga catálogo de modelos con curvas certificadas por fabricante.

    Formato esperado:
    {
      "schneider": {
        "modelos": {
          "schneider_acti9_c16": {
            "nombre": "Acti9 iC60N C16",
            "curva": "C",
            "archivo": "data/curvas_certificadas/schneider_acti9_c16.csv"
          }
        }
      }
    }
    """
    path = Path(ruta)
    if not path.exists():
        return {}

    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data
    except (OSError, ValueError):
        pass

    return {}


def listar_modelos_certificados(fabricante: str) -> Dict[str, str]:
    """Lista modelos certificados disponibles por fabricante."""
    catalogo = cargar_catalogo_modelos_json()
    bloque = catalogo.get(fabricante, {})
    modelos = bloque.get("modelos", {})
    salida: Dict[str, str] = {}
    for modelo_id, info in modelos.items():
        salida[modelo_id] = str(info.get("nombre", modelo_id))
    return salida


def cargar_curva_certificada_modelo(modelo_id: str, ruta_catalogo: str | Path = "curvas_modelos.json") -> dict | None:
    """Carga puntos certificados de un modelo desde CSV.

    CSV esperado con cabeceras:
    corriente_a,t_min_s,t_max_s
    """
    catalogo = cargar_catalogo_modelos_json(ruta_catalogo)
    for _, bloque in catalogo.items():
        modelos = bloque.get("modelos", {})
        info = modelos.get(modelo_id)
        if not info:
            continue

        archivo = info.get("archivo")
        if not archivo:
            return None

        path = Path(archivo)
        if not path.exists():
            return None

        try:
            import csv

            corrientes: list[float] = []
            t_min: list[float] = []
            t_max: list[float] = []

            with path.open("r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    corrientes.append(float(row["corriente_a"]))
                    t_min.append(float(row["t_min_s"]))
                    t_max.append(float(row["t_max_s"]))

            if not corrientes:
                return None

            idx = np.argsort(np.array(corrientes))
            c = np.array(corrientes)[idx]
            mn = np.array(t_min)[idx]
            mx = np.array(t_max)[idx]
            return {
                "corriente_a": c,
                "t_min_s": mn,
                "t_max_s": mx,
                "curva": info.get("curva"),
                "nombre": info.get("nombre", modelo_id),
            }
        except Exception:
            return None

    return None


def obtener_rango_magnetico(curva: TipoCurva, fabricante: str = "generica_iec") -> Tuple[float, float]:
    catalogo = cargar_curvas_desde_json()
    bloque_fabricante = catalogo.get(fabricante) or catalogo.get("generica_iec", {})
    bloque_curva = bloque_fabricante.get(curva)

    if not bloque_curva or "magnetica" not in bloque_curva:
        return CURVAS_IEC[curva]["magnetica"]

    mag = bloque_curva["magnetica"]
    return float(mag[0]), float(mag[1])


def convertir_potencia_a_w(potencia: float, unidad: UnidadPotencia) -> float:
    if unidad == "W":
        return potencia
    return potencia * HP_A_W


def calcular_corriente_nominal_a(
    voltaje_v: float,
    potencia: float,
    unidad: UnidadPotencia,
    sistema_fases: TipoSistema = "monofasico",
    tipo_carga: TipoCarga = "resistencia",
    factor_potencia: float = 1.0,
    eficiencia: float = 1.0,
) -> float:
    potencia_w = convertir_potencia_a_w(potencia, unidad)

    divisor = 1.0
    if tipo_carga == "motor":
        divisor = max(factor_potencia * eficiencia, 1e-6)

    if sistema_fases == "trifasico":
        return potencia_w / (np.sqrt(3.0) * voltaje_v * divisor)
    return potencia_w / (voltaje_v * divisor)


def tiempo_disparo_termico_s(multiplo_in: np.ndarray) -> np.ndarray:
    k = 25.0
    m = np.clip(multiplo_in, 1.05, None)
    tiempo = k / np.square(m - 1.0)
    return np.clip(tiempo, 0.2, 3600.0)


def curva_disparo_limites(
    curva: TipoCurva,
    multiplo_in: np.ndarray,
    fabricante: str = "generica_iec",
    in_termico_a: float | None = None,
    modelo_certificado_id: str | None = None,
) -> Tuple[np.ndarray, np.ndarray]:
    # Si hay curva certificada cargada para el modelo, se usa prioridad alta.
    if modelo_certificado_id and in_termico_a and in_termico_a > 0:
        curva_modelo = cargar_curva_certificada_modelo(modelo_certificado_id)
        if curva_modelo is not None:
            corriente_obj = multiplo_in * in_termico_a
            c = np.array(curva_modelo["corriente_a"], dtype=float)
            mn = np.array(curva_modelo["t_min_s"], dtype=float)
            mx = np.array(curva_modelo["t_max_s"], dtype=float)

            c = np.clip(c, 1e-6, None)
            mn = np.clip(mn, 1e-6, None)
            mx = np.clip(mx, 1e-6, None)

            log_c = np.log10(c)
            log_mn = np.log10(mn)
            log_mx = np.log10(mx)
            log_obj = np.log10(np.clip(corriente_obj, c.min(), c.max()))

            t_min_interp = np.power(10.0, np.interp(log_obj, log_c, log_mn))
            t_max_interp = np.power(10.0, np.interp(log_obj, log_c, log_mx))
            return t_min_interp, t_max_interp

    t_termico = tiempo_disparo_termico_s(multiplo_in)

    t_max = np.clip(t_termico * 1.6, 0.02, 3600.0)
    t_min = np.clip(t_termico * 0.6, 0.01, 3600.0)

    m_min, m_max = obtener_rango_magnetico(curva, fabricante)
    zona_magnetica = multiplo_in >= m_min

    t_max = np.where(zona_magnetica, np.minimum(t_max, 0.1), t_max)
    t_min = np.where(zona_magnetica, np.minimum(t_min, 0.01), t_min)

    ultra = multiplo_in >= m_max
    t_max = np.where(ultra, np.minimum(t_max, 0.03), t_max)
    t_min = np.where(ultra, np.minimum(t_min, 0.005), t_min)

    return t_min, t_max


def generar_curva_carga(
    params: ParametrosSimulacion,
    tiempo_s: np.ndarray,
    corriente_nominal_a: float,
) -> np.ndarray:
    if params.tipo_carga == "resistencia":
        return np.full_like(tiempo_s, fill_value=corriente_nominal_a)

    tau = max(params.tiempo_arranque_ms / 1000.0 / 4.0, 1e-3)
    i0 = corriente_nominal_a * params.multiplicador_arranque
    corriente = corriente_nominal_a + (i0 - corriente_nominal_a) * np.exp(-tiempo_s / tau)
    return np.maximum(corriente, corriente_nominal_a)


def evaluar_trip(
    in_termico_a: float,
    curva: TipoCurva,
    tiempo_s: np.ndarray,
    corriente_carga_a: np.ndarray,
    fabricante: str = "generica_iec",
    modelo_certificado_id: str | None = None,
) -> Tuple[bool, float | None, float | None]:
    multiplo = corriente_carga_a / in_termico_a
    t_min, _ = curva_disparo_limites(
        curva,
        multiplo,
        fabricante,
        in_termico_a=in_termico_a,
        modelo_certificado_id=modelo_certificado_id,
    )

    mascara_trip = t_min <= tiempo_s
    if not np.any(mascara_trip):
        return False, None, None

    idx = int(np.argmax(mascara_trip))
    return True, float(tiempo_s[idx]), float(corriente_carga_a[idx])


def simular(params: ParametrosSimulacion) -> Dict[str, np.ndarray | float | bool | None]:
    i_nom = calcular_corriente_nominal_a(
        params.voltaje_v,
        params.potencia,
        params.unidad_potencia,
        params.sistema_fases,
        params.tipo_carga,
        params.factor_potencia,
        params.eficiencia,
    )

    tiempo_s = np.logspace(-3, 3, 500)
    corriente_carga_a = generar_curva_carga(params, tiempo_s, i_nom)

    multiplo_malla = np.logspace(0, 2, 400)
    corr_malla_a = multiplo_malla * params.in_termico_a

    curva_certificada = None
    if params.modelo_certificado_id:
        curva_certificada = cargar_curva_certificada_modelo(params.modelo_certificado_id)

    t_min, t_max = curva_disparo_limites(
        params.curva_termica,
        multiplo_malla,
        params.fabricante_curva,
        in_termico_a=params.in_termico_a,
        modelo_certificado_id=params.modelo_certificado_id,
    )

    trip, t_trip, i_trip = evaluar_trip(
        params.in_termico_a,
        params.curva_termica,
        tiempo_s,
        corriente_carga_a,
        params.fabricante_curva,
        params.modelo_certificado_id,
    )

    return {
        "tiempo_s": tiempo_s,
        "corriente_carga_a": corriente_carga_a,
        "corriente_nominal_a": i_nom,
        "corriente_pico_a": float(np.max(corriente_carga_a)),
        "in_termico_a": params.in_termico_a,
        "usa_curva_certificada": bool(curva_certificada is not None),
        "corriente_malla_a": corr_malla_a,
        "t_disparo_min_s": t_min,
        "t_disparo_max_s": t_max,
        "trip": trip,
        "t_trip_s": t_trip,
        "i_trip_a": i_trip,
    }


def puntuar_alternativa(
    resultados: Dict[str, np.ndarray | float | bool | None],
    peso_seguridad: float = 0.7,
    peso_margen_arranque: float = 0.2,
    peso_sobredimensionamiento: float = 0.1,
) -> float:
    trip = bool(resultados.get("trip"))
    in_termico = float(resultados.get("in_termico_a") or 0.0)
    i_nominal = float(resultados.get("corriente_nominal_a") or 0.0)
    i_pico = float(resultados.get("corriente_pico_a") or 0.0)
    t_trip = resultados.get("t_trip_s")

    if in_termico <= 0 or i_nominal <= 0:
        return -9999.0

    ratio_dimensionamiento = in_termico / i_nominal
    margen_arranque_rel = (in_termico - i_pico) / max(i_nominal, 1e-6)

    suma_pesos = max(peso_seguridad + peso_margen_arranque + peso_sobredimensionamiento, 1e-6)
    w_seg = peso_seguridad / suma_pesos
    w_mar = peso_margen_arranque / suma_pesos
    w_sob = peso_sobredimensionamiento / suma_pesos

    score = 100.0

    if trip:
        score -= 300.0 * w_seg
        if isinstance(t_trip, float):
            score -= max(0.0, 10.0 - min(t_trip, 10.0)) * w_seg

    score += np.clip(margen_arranque_rel * 80.0, -60.0, 40.0) * w_mar
    score -= max(0.0, ratio_dimensionamiento - 1.25) * 35.0 * w_sob

    return float(score)
