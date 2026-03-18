"""
core/cost_center.py
Construye el Centro de Costos por diputado cruzando todas las fuentes disponibles.

Centro de Costos = Dieta + Movilidad/Desarraigo + Asesores + Subsidios a terceros
"""

import pandas as pd
import os

DATA_DIR = "data"


def construir_centro_costos(
    df_nomina: pd.DataFrame,
    df_remuneraciones: pd.DataFrame = None,
    df_subsidios: pd.DataFrame = None,
    df_personal: pd.DataFrame = None,
) -> pd.DataFrame:
    """
    Construye la tabla maestra de Centro de Costos por diputado.

    Parámetros:
        df_nomina:        Nómina de diputados (Nombre, Distrito, Bloque)
        df_remuneraciones: Remuneraciones estimadas (de fuentes.py)
        df_subsidios:     Subsidios a terceros otorgados
        df_personal:      Nómina de personal (asesores vinculados)

    Retorna:
        DataFrame con una fila por diputado y todos los rubros de gasto.
    """
    if df_nomina is None or df_nomina.empty:
        print("❌ Se necesita la nómina de diputados para construir el centro de costos.")
        return pd.DataFrame()

    # Normalizar nombre de columnas
    col_nombre  = _detectar_col(df_nomina, ["Nombre", "DIPUTADO", "NOMBRE"])
    col_distrito = _detectar_col(df_nomina, ["Distrito", "DISTRITO"])
    col_bloque   = _detectar_col(df_nomina, ["Bloque", "BLOQUE"])

    df_cc = df_nomina[[col_nombre, col_distrito, col_bloque]].copy()
    df_cc.columns = ["Nombre", "Distrito", "Bloque"]
    df_cc["Nombre_norm"] = df_cc["Nombre"].apply(_normalizar_nombre)

    # ── Columna: Dieta + Movilidad ────────────────────────────────────────────
    if df_remuneraciones is not None and not df_remuneraciones.empty:
        col_rem_nombre = _detectar_col(df_remuneraciones, ["Nombre", "NOMBRE"])
        df_rem_merge = df_remuneraciones.copy()
        df_rem_merge["Nombre_norm"] = df_rem_merge[col_rem_nombre].str.upper().str.strip()

        df_cc = df_cc.merge(
            df_rem_merge[["Nombre_norm", "Dieta_bruta", "Movilidad", "Desarraigo", "Total_estimado_mensual"]],
            on="Nombre_norm", how="left"
        )
    else:
        df_cc["Dieta_bruta"] = None
        df_cc["Movilidad"]   = None
        df_cc["Desarraigo"]  = None
        df_cc["Total_estimado_mensual"] = None

    # ── Columna: Subsidios a Terceros ─────────────────────────────────────────
    if df_subsidios is not None and not df_subsidios.empty:
        col_diputado_sub = _detectar_col(df_subsidios, ["DIPUTADO", "Diputado", "NOMBRE"])
        col_monto_sub    = _detectar_col(df_subsidios, ["MONTO", "Monto", "IMPORTE"])

        if col_diputado_sub and col_monto_sub:
            df_sub_agg = (
                df_subsidios
                .assign(Nombre_norm=df_subsidios[col_diputado_sub].apply(_normalizar_nombre))
                .groupby("Nombre_norm")[col_monto_sub]
                .sum()
                .reset_index()
                .rename(columns={col_monto_sub: "Subsidios_otorgados_total"})
            )
            df_cc = df_cc.merge(df_sub_agg, on="Nombre_norm", how="left")
            # Mostrar cuántos matchearon
            matcheados = df_cc["Subsidios_otorgados_total"].notna().sum()
            print(f"  💰 Subsidios cruzados: {matcheados} diputados con datos")
        else:
            df_cc["Subsidios_otorgados_total"] = None
    else:
        df_cc["Subsidios_otorgados_total"] = None

    # ── Columna: Personal / Asesores ──────────────────────────────────────────
    if df_personal is not None and not df_personal.empty:
        col_area = _detectar_col(df_personal, ["AREA", "Area", "AREA_TRABAJO"])
        if col_area:
            # Contar empleados cuya área menciona al diputado
            # (esto requiere refinamiento posterior cuando se conozca el formato exacto)
            df_cc["Asesores_contados"] = 0  # placeholder
            df_cc["Nota_personal"] = "Requiere cruce por campo AREA"
    else:
        df_cc["Asesores_contados"] = None

    # ── Limpiar columna auxiliar ──────────────────────────────────────────────
    df_cc = df_cc.drop(columns=["Nombre_norm"])

    # ── Estado de disponibilidad de datos ────────────────────────────────────
    df_cc["Datos_completos"] = df_cc[
        ["Dieta_bruta", "Total_estimado_mensual"]
    ].notna().all(axis=1)

    ruta = os.path.join(DATA_DIR, "centro_costos.csv")
    os.makedirs(DATA_DIR, exist_ok=True)
    df_cc.to_csv(ruta, index=False, encoding="utf-8-sig")
    print(f"💾 Centro de costos guardado: {ruta}  ({len(df_cc)} diputados)")

    return df_cc


def _detectar_col(df: pd.DataFrame, candidatas: list) -> str:
    """Retorna el primer nombre de columna que exista en el DataFrame."""
    for c in candidatas:
        if c in df.columns:
            return c
    return None


def _normalizar_nombre(nombre: str) -> str:
    """
    Normaliza nombres para cruce entre fuentes con distintos formatos.
    Convierte a mayúsculas, elimina tildes, signos y espacios extra.
    Ejemplo:
      'Agüero, Guillermo César' → 'AGUERO GUILLERMO CESAR'
      'AGUERO, GUILLERMO CESAR' → 'AGUERO GUILLERMO CESAR'
    """
    import unicodedata
    if not isinstance(nombre, str):
        return ""
    # Quitar tildes
    nombre = unicodedata.normalize("NFKD", nombre)
    nombre = "".join(c for c in nombre if not unicodedata.combining(c))
    # Mayúsculas, quitar comas y puntos, colapsar espacios
    nombre = nombre.upper()
    nombre = nombre.replace(",", " ").replace(".", " ")
    nombre = " ".join(nombre.split())
    return nombre


def resumen_centro_costos(df_cc: pd.DataFrame) -> None:
    """Imprime un resumen estadístico del centro de costos."""
    if df_cc.empty:
        print("DataFrame vacío.")
        return

    print("\n" + "="*60)
    print("  RESUMEN CENTRO DE COSTOS")
    print("="*60)
    print(f"  Total diputados:    {len(df_cc)}")

    if "Total_estimado_mensual" in df_cc.columns:
        total_mensual = df_cc["Total_estimado_mensual"].sum()
        print(f"  Costo mensual est.: ${total_mensual:,.0f}")
        print(f"  Costo anual est.:   ${total_mensual * 12:,.0f}")

    if "Subsidios_otorgados_total" in df_cc.columns:
        total_subsidios = df_cc["Subsidios_otorgados_total"].sum()
        print(f"  Subsidios totales:  ${total_subsidios:,.0f}")

    if "Bloque" in df_cc.columns and "Total_estimado_mensual" in df_cc.columns:
        print("\n  Top bloques por costo mensual estimado:")
        por_bloque = (
            df_cc.groupby("Bloque")["Total_estimado_mensual"]
            .agg(["sum", "count", "mean"])
            .sort_values("sum", ascending=False)
            .head(8)
        )
        por_bloque.columns = ["Total", "Diputados", "Promedio"]
        print(por_bloque.to_string())

    print("="*60)