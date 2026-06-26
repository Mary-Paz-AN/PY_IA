"""
Genera evidencia "lista para el artículo" a partir de logs/metricas.csv:

- logs/resumen_metricas.md -> tabla en Markdown (tasa de éxito por tarea, reintentos promedio, tiempo promedio, etc.)
- logs/figuras/exito_por_tarea.png -> barras: % de validación OK por tarea
- logs/figuras/distribucion_tiempos.png -> histograma de tiempos de respuesta

Uso:
instalar: pip install tabulate
python analizar_logs.py (corre después de tener varias sesiones de chat ya registradas en logs/)
"""

import os
import pandas as pd
import matplotlib.pyplot as plt

RUTA_CSV = os.path.join("logs", "metricas.csv")
CARPETA_FIGURAS = os.path.join("logs", "figuras")
RUTA_RESUMEN_MD = os.path.join("logs", "resumen_metricas.md")


def cargar_metricas() -> pd.DataFrame:
    if not os.path.exists(RUTA_CSV):
        raise FileNotFoundError(
            f"No existe {RUTA_CSV}. Corra primero el agente (agente.py) "
            f"para generar al menos una sesión de evidencia."
        )
    return pd.read_csv(RUTA_CSV)


def construir_tabla_resumen(df: pd.DataFrame) -> pd.DataFrame:
    resumen = df.groupby("task", dropna=False).agg(
        turnos=("turno", "count"),
        tasa_exito=("validacion_ok", "mean"),
        reintentos_promedio=("reintentos", "mean"),
        tiempo_promedio_s=("tiempo_s", "mean"),
        tiempo_max_s=("tiempo_s", "max"),
        hubo_error_pct=("hubo_error", "mean"),
    ).reset_index()

    resumen["tasa_exito"] = (resumen["tasa_exito"] * 100).round(1)
    resumen["hubo_error_pct"] = (resumen["hubo_error_pct"] * 100).round(1)
    resumen["reintentos_promedio"] = resumen["reintentos_promedio"].round(2)
    resumen["tiempo_promedio_s"] = resumen["tiempo_promedio_s"].round(2)
    resumen["tiempo_max_s"] = resumen["tiempo_max_s"].round(2)
    return resumen


def guardar_markdown(resumen: pd.DataFrame, total_turnos: int, total_sesiones: int):
    with open(RUTA_RESUMEN_MD, "w", encoding="utf-8") as f:
        f.write("# Resumen de validación del agente\n\n")
        f.write(f"- Sesiones registradas: **{total_sesiones}**\n")
        f.write(f"- Turnos totales: **{total_turnos}**\n\n")
        f.write(resumen.to_markdown(index=False))
        f.write("\n")
    print(f"[OK] Tabla resumen guardada en {RUTA_RESUMEN_MD}")


def graficar_exito_por_tarea(resumen: pd.DataFrame):
    os.makedirs(CARPETA_FIGURAS, exist_ok=True)
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.bar(resumen["task"].astype(str), resumen["tasa_exito"])
    ax.set_ylabel("Tasa de validación OK (%)")
    ax.set_xlabel("Tarea")
    ax.set_title("Tasa de éxito del Verifier por tarea")
    ax.set_ylim(0, 100)
    for i, v in enumerate(resumen["tasa_exito"]):
        ax.text(i, v + 1, f"{v}%", ha="center")
    plt.tight_layout()
    ruta = os.path.join(CARPETA_FIGURAS, "exito_por_tarea.png")
    plt.savefig(ruta, dpi=150)
    plt.close(fig)
    print(f"[OK] Figura guardada en {ruta}")


def graficar_distribucion_tiempos(df: pd.DataFrame):
    os.makedirs(CARPETA_FIGURAS, exist_ok=True)
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.hist(df["tiempo_s"].dropna(), bins=15)
    ax.set_xlabel("Tiempo de respuesta (s)")
    ax.set_ylabel("Frecuencia")
    ax.set_title("Distribución del tiempo de respuesta del agente")
    plt.tight_layout()
    ruta = os.path.join(CARPETA_FIGURAS, "distribucion_tiempos.png")
    plt.savefig(ruta, dpi=150)
    plt.close(fig)
    print(f"[OK] Figura guardada en {ruta}")


def main():
    df = cargar_metricas()
    resumen = construir_tabla_resumen(df)

    print("\nResumen de métricas por tarea:\n")
    print(resumen.to_string(index=False))

    guardar_markdown(
        resumen,
        total_turnos=len(df),
        total_sesiones=df["id_sesion"].nunique()
    )
    graficar_exito_por_tarea(resumen)
    graficar_distribucion_tiempos(df)


if __name__ == "__main__":
    main()
