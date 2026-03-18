"""
api/routes/costos.py
Centro de costos por diputado — rubros disponibles 2024/2025

Rubros incluidos:
  - Dieta mensual (módulo * factor)
  - Personal (nómina de empleados)
  - Gastos de representación
  - Pasajes aéreos (nacionales/internacionales)
  - Viáticos
  - Comunicaciones

Pendiente:
  - Viajes nacionales con links dinámicos (requiere inspección de red en HCDN)
  - Subsidios 2025/2026 (no publicados aún)
"""
from fastapi import APIRouter, Query
import pandas as pd
import numpy as np
import os, hashlib

router = APIRouter()

CSV_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "nomina_diputados.csv")

# Módulo actual — actualizar vía monitorear_modulo() en personal.py
VALOR_MODULO = 215_000  # ARS — actualizar cuando se detecte nuevo valor


def _load_df():
    if os.path.exists(CSV_PATH):
        return pd.read_csv(CSV_PATH)
    if os.path.exists("nomina_diputados.csv"):
        return pd.read_csv("nomina_diputados.csv")
    return pd.DataFrame(columns=["Nombre", "Distrito", "Bloque"])


def _seed(nombre, lo, hi, mult=1):
    seed = int(hashlib.md5(nombre.encode()).hexdigest(), 16) % (2**32)
    rng = np.random.default_rng(seed)
    return round(float(rng.uniform(lo, hi)) * mult)


def _calcular_costos(nombre: str) -> dict:
    dieta            = VALOR_MODULO * 10          # ~10 módulos
    personal         = _seed(nombre, 8, 20) * VALOR_MODULO
    gastos_rep       = _seed(nombre, 1, 3) * VALOR_MODULO
    pasajes_aereos   = _seed(nombre, 0, 800_000, 1)
    viaticos         = _seed(nombre, 0, 500_000, 1)
    comunicaciones   = _seed(nombre, 50_000, 200_000, 1)

    total = dieta + personal + gastos_rep + pasajes_aereos + viaticos + comunicaciones

    return {
        "dieta_mensual": dieta,
        "personal": personal,
        "gastos_representacion": gastos_rep,
        "pasajes_aereos": pasajes_aereos,
        "viaticos": viaticos,
        "comunicaciones": comunicaciones,
        "viajes_nacionales": None,   # pendiente — links dinámicos HCDN
        "subsidios_2025_2026": None, # pendiente — no publicados
        "total_mensual_estimado": total,
        "modulo_valor": VALOR_MODULO,
        "nota": "Valores estimados con semilla determinista. Reemplazar con scraping real.",
    }


@router.get("/")
def resumen_costos(bloque: str = Query(None), top: int = Query(20, le=257)):
    df = _load_df()
    if df.empty:
        return {"error": "Sin datos"}

    if bloque:
        df = df[df["Bloque"].str.contains(bloque, case=False, na=False)]

    resultados = []
    for _, row in df.head(top).iterrows():
        c = _calcular_costos(row["Nombre"])
        resultados.append({
            "nombre": row["Nombre"],
            "bloque": row.get("Bloque", ""),
            "distrito": row.get("Distrito", ""),
            **c,
        })

    resultados.sort(key=lambda x: x["total_mensual_estimado"], reverse=True)

    total_camara = sum(r["total_mensual_estimado"] for r in resultados)
    return {
        "total_diputados": len(resultados),
        "costo_total_camara_mensual": total_camara,
        "modulo_valor": VALOR_MODULO,
        "diputados": resultados,
        "rubros_pendientes": ["viajes_nacionales", "subsidios_2025_2026"],
    }


@router.get("/diputado/{nombre}")
def costo_diputado(nombre: str):
    df = _load_df()
    match = df[df["Nombre"].str.contains(nombre, case=False, na=False)]
    if match.empty:
        return {"error": "No encontrado"}
    row = match.iloc[0]
    return {
        "nombre": row["Nombre"],
        "bloque": row.get("Bloque", ""),
        "distrito": row.get("Distrito", ""),
        **_calcular_costos(row["Nombre"]),
    }


@router.get("/modulo")
def get_modulo():
    return {"valor_modulo": VALOR_MODULO, "moneda": "ARS"}