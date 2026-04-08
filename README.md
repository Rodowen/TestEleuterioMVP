# ThermalGuard MVP

Simulador educativo de protecciones termomagnéticas para ayudar a elegir disyuntores para cargas resistivas y motores.

## Uso rápido (local)

```bash
pip install -r requirements.txt
streamlit run app.py
```

## ¿Qué incluye?

- Presets eléctricos (120V, 220V, 380V)
- Monofásico / Trifásico
- Carga resistencia o motor (con FP y eficiencia)
- Catálogo de marcas referenciales: Schneider, Bticino, Chnin
- Modo opcional de curva por modelo (CSV)
- Comparación de múltiples In
- Ranking automático (Conservador/Balanceado/Económico/Custom)
- Exportación a PDF y CSV
- Visualización explícita de I nominal e I pico (métricas + líneas en gráfico)

## Nota

Este MVP es de uso educativo. Para decisiones definitivas, contrastar con curvas certificadas por fabricante y normativa local.

## Curva certificada por modelo (opcional)

La app puede leer archivos CSV de curva por modelo desde:

- `curvas_modelos.json`
- `data/curvas_certificadas/*.csv`

Formato CSV:

```csv
corriente_a,t_min_s,t_max_s
16,3600,3600
20,1200,2400
...
```

Si no hay CSV válido, la app vuelve automáticamente al modo referencial IEC.
