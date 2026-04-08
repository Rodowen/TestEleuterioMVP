"""Aplicación Streamlit para ThermalGuard MVP."""

from __future__ import annotations

from datetime import datetime

import streamlit as st

from fisica import (
    ParametrosSimulacion,
    cargar_curvas_desde_json,
    listar_modelos_certificados,
    puntuar_alternativa,
    simular,
)
from plotting import crear_figura_comparativa
from reporting import exportar_ranking_csv, exportar_reporte_pdf, guardar_figura_png
from validaciones import validar_entradas

PRESETS_PAIS = {
    "Custom": {"sistema": "monofasico", "voltaje": 220.0},
    "LATAM 220V Monofásico": {"sistema": "monofasico", "voltaje": 220.0},
    "Norteamérica 120V Monofásico": {"sistema": "monofasico", "voltaje": 120.0},
    "Industrial 380V Trifásico": {"sistema": "trifasico", "voltaje": 380.0},
}

MODOS_RANKING = {
    "Conservador": {"seguridad": 0.8, "margen": 0.15, "sobredim": 0.05},
    "Balanceado": {"seguridad": 0.7, "margen": 0.2, "sobredim": 0.1},
    "Económico": {"seguridad": 0.6, "margen": 0.15, "sobredim": 0.25},
    "Custom": {"seguridad": 0.7, "margen": 0.2, "sobredim": 0.1},
}


def _construir_label_termico(in_termico_a: float, curva_termica: str, fabricante: str) -> str:
    return f"{fabricante} | {curva_termica}-{in_termico_a:.1f}A"


def main() -> None:
    """Punto de entrada principal de la app web."""
    st.set_page_config(page_title="ThermalGuard MVP", layout="wide")
    st.title("⚡ ThermalGuard MVP")
    st.caption("Comparación de múltiples térmicos para una carga (IEC 60898-1, modelo educativo)")

    with st.sidebar:
        st.header("Parámetros de carga")

        preset = st.selectbox("Preset eléctrico", options=list(PRESETS_PAIS.keys()), index=0)
        preset_cfg = PRESETS_PAIS[preset]

        voltaje_v = st.number_input(
            "Voltaje [V]",
            min_value=1.0,
            value=float(preset_cfg["voltaje"]),
            step=1.0,
            help="Para trifásico usar tensión línea-línea.",
        )
        sistema_fases = st.selectbox(
            "Sistema",
            options=["monofasico", "trifasico"],
            index=0 if preset_cfg["sistema"] == "monofasico" else 1,
        )

        potencia = st.number_input("Potencia", min_value=0.1, value=1500.0, step=10.0)
        unidad_potencia = st.selectbox("Unidad de potencia", options=["W", "HP"], index=0)
        tipo_carga = st.selectbox("Tipo de carga", options=["resistencia", "motor"], index=0)

        st.subheader("Arranque de motor")
        multiplicador_arranque = st.slider("Multiplicador de arranque (x In)", 1.0, 12.0, 6.0, 0.5)
        tiempo_arranque_ms = st.slider("Duración arranque [ms]", 10.0, 5000.0, 200.0, 10.0)
        factor_potencia = st.slider("Factor de potencia (motores)", 0.1, 1.0, 0.9, 0.01)
        eficiencia = st.slider("Eficiencia (motores)", 0.1, 1.0, 0.9, 0.01)

        st.subheader("Opciones de térmico")
        catalogo = cargar_curvas_desde_json()
        fabricantes = list(catalogo.keys())
        fabricante_curva = st.selectbox("Catálogo de curva", options=fabricantes, index=0)
        curva_termica = st.selectbox("Curva", options=["B", "C", "D"], index=1)

        st.subheader("Curva por modelo")
        usar_curva_certificada = st.checkbox(
            "Usar curva por modelo (si existe archivo CSV)",
            value=False,
            help="Si se activa y existe el modelo cargado, la app usa puntos de curva desde CSV.",
        )
        modelo_certificado_id = None
        if usar_curva_certificada:
            modelos = listar_modelos_certificados(fabricante_curva)
            if modelos:
                opciones_modelos = list(modelos.keys())
                modelo_certificado_id = st.selectbox(
                    "Modelo",
                    options=opciones_modelos,
                    format_func=lambda x: modelos.get(x, x),
                )
            else:
                st.warning("No hay modelos configurados para esta marca en curvas_modelos.json.")

        opciones_in = st.multiselect(
            "Comparar In [A]",
            options=[2, 4, 6, 10, 16, 20, 25, 32, 40, 50, 63, 80, 100],
            default=[10, 16, 20],
            help="Podés elegir varias opciones para comparar en el mismo gráfico.",
        )

        st.subheader("Criterio de selección")
        modo_ranking = st.selectbox("Modo", options=list(MODOS_RANKING.keys()), index=1)
        pesos = MODOS_RANKING[modo_ranking]

        if modo_ranking == "Custom":
            peso_seguridad = st.slider("Peso seguridad", 0.0, 1.0, 0.7, 0.05)
            peso_margen = st.slider("Peso margen arranque", 0.0, 1.0, 0.2, 0.05)
            peso_sobredim = st.slider("Peso sobredimensionamiento", 0.0, 1.0, 0.1, 0.05)
        else:
            peso_seguridad = pesos["seguridad"]
            peso_margen = pesos["margen"]
            peso_sobredim = pesos["sobredim"]

        simular_btn = st.button("Simular", type="primary")

    if simular_btn:
        try:
            if not opciones_in:
                raise ValueError("Seleccioná al menos una opción de In para comparar.")

            simulaciones = []
            for in_termico_a in opciones_in:
                validar_entradas(
                    voltaje_v=voltaje_v,
                    potencia=potencia,
                    in_termico_a=float(in_termico_a),
                    multiplicador_arranque=multiplicador_arranque,
                    tiempo_arranque_ms=tiempo_arranque_ms,
                    factor_potencia=factor_potencia,
                    eficiencia=eficiencia,
                )

                params = ParametrosSimulacion(
                    voltaje_v=voltaje_v,
                    potencia=potencia,
                    unidad_potencia=unidad_potencia,
                    tipo_carga=tipo_carga,
                    in_termico_a=float(in_termico_a),
                    curva_termica=curva_termica,
                    sistema_fases=sistema_fases,
                    fabricante_curva=fabricante_curva,
                    modelo_certificado_id=modelo_certificado_id,
                    factor_potencia=factor_potencia,
                    eficiencia=eficiencia,
                    multiplicador_arranque=multiplicador_arranque,
                    tiempo_arranque_ms=tiempo_arranque_ms,
                )
                data = simular(params)
                label = _construir_label_termico(float(in_termico_a), curva_termica, fabricante_curva)
                score = puntuar_alternativa(
                    data,
                    peso_seguridad,
                    peso_margen,
                    peso_sobredim,
                )
                simulaciones.append({"label": label, "data": data, "score": score})

            fig = crear_figura_comparativa(simulaciones)

            col1, col2 = st.columns([2, 1])
            with col1:
                st.pyplot(fig, clear_figure=False)

            with col2:
                st.subheader("Resumen de opciones")
                data_base = simulaciones[0]["data"]
                st.metric("Corriente nominal de carga", f"{float(data_base['corriente_nominal_a']):.2f} A")
                st.metric("Corriente pico estimada", f"{float(data_base['corriente_pico_a']):.2f} A")

                for item in simulaciones:
                    data = item["data"]
                    if data["trip"]:
                        st.error(f"{item['label']} → TRIP | score={item['score']:.1f}")
                    else:
                        st.success(f"{item['label']} → SEGURO | score={item['score']:.1f}")

                ranking = sorted(simulaciones, key=lambda x: x["score"], reverse=True)
                mejor = ranking[0] if ranking else None

                usa_modelo = any(bool(x["data"].get("usa_curva_certificada")) for x in ranking)
                if usa_modelo:
                    st.success("🧪 Modo curva por modelo activo (CSV cargado).")
                else:
                    st.info("ℹ️ Modo referencial IEC activo (sin CSV de modelo cargado).")

                if mejor is not None:
                    st.info(f"Recomendación inicial: **{mejor['label']}**")
                else:
                    st.warning("No hay opción segura en la lista actual. Probá mayor In o curva distinta.")

                st.markdown("### Ranking")
                for idx, item in enumerate(ranking, start=1):
                    estado = "TRIP" if item["data"]["trip"] else "SEGURO"
                    st.write(f"{idx}. {item['label']} — {estado} — score {item['score']:.1f}")

                st.markdown("### Tabla rápida")
                tabla = []
                for item in ranking:
                    d = item["data"]
                    tabla.append(
                        {
                            "opción": item["label"],
                            "In [A]": float(d["in_termico_a"]),
                            "I nominal [A]": round(float(d["corriente_nominal_a"]), 2),
                            "I pico [A]": round(float(d["corriente_pico_a"]), 2),
                            "estado": "TRIP" if d["trip"] else "SEGURO",
                            "score": round(float(item["score"]), 1),
                        }
                    )
                st.dataframe(tabla, use_container_width=True)

                nombre_png = f"grafico_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                ruta_png = guardar_figura_png(fig, f"reports/{nombre_png}")

                parametros = {
                    "Preset": preset,
                    "Voltaje [V]": voltaje_v,
                    "Sistema": sistema_fases,
                    "Potencia": f"{potencia} {unidad_potencia}",
                    "Tipo de carga": tipo_carga,
                    "Factor de potencia": factor_potencia,
                    "Eficiencia": eficiencia,
                    "Curva": curva_termica,
                    "Catálogo": fabricante_curva,
                    "Modelo certificado": modelo_certificado_id or "No seleccionado",
                    "Opciones In [A]": ", ".join(str(x) for x in opciones_in),
                    "Modo ranking": modo_ranking,
                    "Pesos": f"seguridad={peso_seguridad:.2f}, margen={peso_margen:.2f}, sobredim={peso_sobredim:.2f}",
                }
                resumen_opciones = []
                for item in ranking:
                    estado = "TRIP" if item["data"]["trip"] else "SEGURO"
                    resumen_opciones.append({"opcion": item["label"], "estado": f"{estado} | score={item['score']:.1f}"})

                ruta_pdf = exportar_reporte_pdf(
                    "reports/reporte_thermalguard.pdf",
                    parametros,
                    simulaciones[0]["data"],
                    ruta_grafico=ruta_png,
                    resumen_opciones=resumen_opciones,
                )
                with open(ruta_pdf, "rb") as f:
                    st.download_button(
                        label="📄 Descargar reporte PDF",
                        data=f,
                        file_name="reporte_thermalguard.pdf",
                        mime="application/pdf",
                    )

                ruta_csv = exportar_ranking_csv("reports/ranking_thermalguard.csv", resumen_opciones)
                with open(ruta_csv, "rb") as f:
                    st.download_button(
                        label="📊 Descargar ranking CSV",
                        data=f,
                        file_name="ranking_thermalguard.csv",
                        mime="text/csv",
                    )

                st.info(
                    "Este simulador usa aproximaciones educativas. "
                    "Validar siempre con curvas certificadas del fabricante antes de decisión final."
                )

        except ValueError as exc:
            st.error(f"Error de validación: {exc}")
        except ZeroDivisionError:
            st.error("Error matemático: división por cero detectada. Revisá el voltaje.")
        except Exception as exc:  # pragma: no cover
            st.error(f"Error inesperado en la simulación: {exc}")


if __name__ == "__main__":
    main()
