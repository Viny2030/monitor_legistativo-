"""
main.py — Monitor de Eficiencia Legislativa y Transparencia Presupuestaria
Punto de entrada principal del proyecto MEL-TP.

Uso:
    python main.py                  → Ejecuta pipeline completo
    python main.py --diagnostico    → Solo verifica disponibilidad de fuentes
    python main.py --nomina         → Solo descarga nómina de diputados
    python main.py --subsidios      → Solo descarga subsidios
    python main.py --costos         → Solo construye centro de costos
"""

import argparse
import sys
import os
import pandas as pd

# Asegura que el directorio raíz esté en el path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scrapers import (
    obtener_nomina,
    descargar_subsidios,
    descargar_nomina_personal,
    generar_tabla_remuneraciones,
    diagnosticar_fuentes,
)
from core import construir_centro_costos, resumen_centro_costos


def pipeline_completo():
    """Ejecuta el pipeline completo de extracción y procesamiento."""
    print("\n" + "🚀 " + "="*50)
    print("   MEL-TP — Monitor de Eficiencia Legislativa")
    print("   Pipeline completo iniciado")
    print("="*53 + "\n")

    # PASO 1: Nómina de diputados
    print("📋 PASO 1: Descargando nómina de diputados...")
    df_nomina = obtener_nomina()

    if df_nomina.empty:
        print("⛔ No se pudo obtener la nómina. Abortando pipeline.")
        return

    # PASO 2: Remuneraciones estimadas
    print("\n💰 PASO 2: Calculando remuneraciones estimadas...")
    df_remuneraciones = generar_tabla_remuneraciones(df_nomina)

    # PASO 3: Subsidios a terceros
    # 2024: el portal informa que no se otorgaron subsidios ese año (Excel vacío)
    # 2023: último año con datos reales confirmados
    print("\n🏦 PASO 3: Descargando subsidios...")
    df_subsidios = pd.DataFrame()
    for ano_sub in [2024, 2023, 2022, 2021]:
        df_subsidios = descargar_subsidios(ano=ano_sub)
        if not df_subsidios.empty:
            print(f"  ✅ Usando subsidios {ano_sub}")
            break
        print(f"  ⏭️  Sin datos en {ano_sub}, probando año anterior...")

    # PASO 4: Nómina de personal (asesores)
    print("\n👥 PASO 4: Descargando nómina de personal...")
    df_personal = descargar_nomina_personal()

    # PASO 5: Construir Centro de Costos
    print("\n🏗️  PASO 5: Construyendo Centro de Costos...")
    df_cc = construir_centro_costos(
        df_nomina=df_nomina,
        df_remuneraciones=df_remuneraciones,
        df_subsidios=df_subsidios if not df_subsidios.empty else None,
        df_personal=df_personal if not df_personal.empty else None,
    )

    # PASO 6: Resumen final
    resumen_centro_costos(df_cc)

    print("\n✅ Pipeline completado. Archivos generados en /data:")
    for f in os.listdir("data"):
        ruta = os.path.join("data", f)
        size = os.path.getsize(ruta)
        filas = ""
        if f.endswith(".csv") and size > 0:
            try:
                filas = f"  ({len(pd.read_csv(ruta))} filas)"
            except Exception:
                pass
        print(f"  📄 {f}  [{size:,} bytes]{filas}")


def main():
    parser = argparse.ArgumentParser(
        description="MEL-TP — Monitor de Eficiencia Legislativa"
    )
    parser.add_argument("--diagnostico", action="store_true",
                        help="Verifica disponibilidad de fuentes de datos")
    parser.add_argument("--nomina", action="store_true",
                        help="Descarga nómina de diputados")
    parser.add_argument("--subsidios", action="store_true",
                        help="Descarga subsidios del año actual")
    parser.add_argument("--personal", action="store_true",
                        help="Descarga nómina de personal")
    parser.add_argument("--costos", action="store_true",
                        help="Construye centro de costos (requiere datos previos)")

    args = parser.parse_args()

    if args.diagnostico:
        diagnosticar_fuentes()
    elif args.nomina:
        obtener_nomina()
    elif args.subsidios:
        descargar_subsidios()
    elif args.personal:
        descargar_nomina_personal()
    elif args.costos:
        df_nomina = pd.read_csv("data/nomina_diputados.csv") if os.path.exists("data/nomina_diputados.csv") else pd.DataFrame()
        df_rem    = pd.read_csv("data/remuneraciones_estimadas.csv") if os.path.exists("data/remuneraciones_estimadas.csv") else None
        df_sub    = pd.read_csv("data/subsidios_2024.csv") if os.path.exists("data/subsidios_2024.csv") else None
        df_cc = construir_centro_costos(df_nomina, df_rem, df_sub)
        resumen_centro_costos(df_cc)
    else:
        pipeline_completo()


if __name__ == "__main__":
    main()