"""
pipeline.py
Orquestador principal del MEL-TP.

Ejecuta en orden:
  1. Nómina de diputados        → nomina_diputados.csv
  2. Asistencia a sesiones      → asistencia_diputados.csv
  3. TEL (si disponible)        → tel_diputados.csv
  4. Monitoreo del módulo       → detecta cambios, actualiza personal.py
  5. Genera ranking SFE final   → ranking_sfe.csv

Uso:
  python pipeline.py                    # corre todo
  python pipeline.py --solo-nomina      # solo nómina
  python pipeline.py --solo-ranking     # solo recalcula SFE
  python pipeline.py --skip-modulo      # omite monitoreo del módulo
"""
import sys
import os
import subprocess
import pandas as pd
import numpy as np
import hashlib
from datetime import datetime
from personal import VALOR_MODULO

ARGS = set(sys.argv[1:])
LOG_FILE = f"pipeline_{datetime.now().strftime('%Y%m%d_%H%M')}.log"


def log(msg: str):
    print(msg)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(msg + "\n")


def run_script(script: str, label: str) -> bool:
    log(f"\n{'─'*50}")
    log(f"▶ {label}")
    result = subprocess.run([sys.executable, script], capture_output=False)
    if result.returncode not in (0, 2):  # 2 = cambio detectado (no error)
        log(f"  ❌ Error en {script} (código {result.returncode})")
        return False
    log(f"  ✅ Completado")
    return True


def calcular_sfe_final():
    """
    Combina todas las fuentes disponibles y genera ranking_sfe.csv.
    Usa datos reales si están disponibles, proxy si no.
    """
    log("\n── Calculando SFE Final ──")

    # Nómina base
    if not os.path.exists("nomina_diputados.csv"):
        log("  ❌ nomina_diputados.csv no encontrado. Abortando ranking.")
        return

    df = pd.read_csv("nomina_diputados.csv")
    log(f"  📋 Nómina: {len(df)} diputados")

    # ── Asistencia ────────────────────────────────────────────────────────────
    if os.path.exists("asistencia_diputados.csv"):
        asist_df = pd.read_csv("asistencia_diputados.csv")[["Nombre", "asistencia_pct"]]
        df = df.merge(asist_df, on="Nombre", how="left")
        log(f"  📊 Asistencia real: {asist_df['Nombre'].nunique()} registros")
    else:
        # Proxy determinista por nombre
        def asist_proxy(nombre):
            seed = int(hashlib.md5(nombre.encode()).hexdigest(), 16) % (2**32)
            return round(float(np.random.default_rng(seed).uniform(0.55, 1.0)), 3)
        df["asistencia_pct"] = df["Nombre"].apply(asist_proxy)
        log("  ⚠  Asistencia: usando proxy (ejecutar scraper_asistencia.py)")

    # ── TEL ───────────────────────────────────────────────────────────────────
    if os.path.exists("tel_diputados.csv"):
        tel_df = pd.read_csv("tel_diputados.csv")
        # Normalizar nombre de columna autor → Nombre
        if "autor" in tel_df.columns:
            tel_df = tel_df.rename(columns={"autor": "Nombre", "tel": "tel_real"})
        df = df.merge(tel_df[["Nombre", "tel_real"]], on="Nombre", how="left")
        df["tel_real"] = df["tel_real"].fillna(0)
        log(f"  📊 TEL real: {tel_df['Nombre'].nunique()} registros")
        usar_tel_real = True
    else:
        def tel_proxy(nombre):
            seed = int(hashlib.md5((nombre + "_tel").encode()).hexdigest(), 16) % (2**32)
            return round(float(np.random.default_rng(seed).uniform(0.0, 0.5)), 3)
        df["tel_real"] = df["Nombre"].apply(tel_proxy)
        usar_tel_real = False
        log("  ⚠  TEL: usando proxy (ejecutar scripts/actualizar_tel.py)")

    # ── Bipartisan proxy (hasta integrar fuente real) ─────────────────────────
    def biprt_proxy(nombre):
        seed = int(hashlib.md5((nombre + "_bp").encode()).hexdigest(), 16) % (2**32)
        return round(float(np.random.default_rng(seed).uniform(0.1, 0.8)), 3)
    df["bipartisan"] = df["Nombre"].apply(biprt_proxy)

    # ── SFE ───────────────────────────────────────────────────────────────────
    df["sfe"] = (
        0.40 * df["asistencia_pct"] +
        0.35 * df["bipartisan"] +
        0.25 * df["tel_real"]
    ).round(4)
    df["sfe_pct"] = (df["sfe"] * 100).round(1)
    df["rank"] = df["sfe"].rank(ascending=False, method="min").astype(int)

    # ── Centro de costos estimado ─────────────────────────────────────────────
    def costo_estimado(nombre):
        seed = int(hashlib.md5((nombre + "_costo").encode()).hexdigest(), 16) % (2**32)
        rng = np.random.default_rng(seed)
        return int(
            VALOR_MODULO * 10 +                       # dieta
            VALOR_MODULO * int(rng.integers(8, 20)) + # personal
            VALOR_MODULO * 2 +                        # gastos rep
            int(rng.uniform(0, 800_000)) +            # pasajes
            int(rng.uniform(0, 500_000))              # viáticos
        )
    df["costo_mensual_est"] = df["Nombre"].apply(costo_estimado)

    # ── Exportar ──────────────────────────────────────────────────────────────
    cols = ["rank", "Nombre", "Distrito", "Bloque",
            "sfe_pct", "asistencia_pct", "bipartisan", "tel_real",
            "costo_mensual_est"]
    df_out = df[cols].sort_values("rank")
    df_out.to_csv("ranking_sfe.csv", index=False, encoding="utf-8")

    log(f"\n  ✅ ranking_sfe.csv generado — {len(df_out)} diputados")
    log(f"  📈 SFE promedio: {df_out['sfe_pct'].mean():.1f}%")
    log(f"  🏆 Top 3: {', '.join(df_out.head(3)['Nombre'].tolist())}")
    log(f"  💰 Costo total estimado: ${df_out['costo_mensual_est'].sum() / 1e9:.2f}B ARS/mes")
    log(f"  📊 TEL: {'real' if usar_tel_real else 'proxy'}")


def main():
    log(f"\n{'═'*50}")
    log(f"MEL-TP Pipeline — {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    log(f"{'═'*50}")

    if "--solo-ranking" not in ARGS:

        # 1. Nómina
        if "--solo-nomina" not in ARGS or True:
            run_script("obtener_datos.py", "Nómina de diputados")

        if "--solo-nomina" in ARGS:
            log("\n✅ Pipeline parcial completado (--solo-nomina)")
            return

        # 2. Asistencia
        run_script("scraper_asistencia.py", "Asistencia a sesiones")

        # 3. TEL
        tel_script = "scripts/actualizar_tel.py"
        if os.path.exists(tel_script):
            run_script(tel_script, "Tasa de Éxito Legislativo (TEL)")

        # 4. Módulo
        if "--skip-modulo" not in ARGS:
            modulo_script = "scripts/monitorear_modulo.py"
            if os.path.exists(modulo_script):
                log(f"\n{'─'*50}")
                log("▶ Monitoreo del Módulo")
                result = subprocess.run([sys.executable, modulo_script], capture_output=False)
                if result.returncode == 2:
                    log("  🔔 Nuevo valor detectado — revisar personal.py")

    # 5. Ranking SFE
    calcular_sfe_final()

    log(f"\n{'═'*50}")
    log(f"✅ Pipeline completado — log: {LOG_FILE}")
    log(f"{'═'*50}\n")


if __name__ == "__main__":
    main()