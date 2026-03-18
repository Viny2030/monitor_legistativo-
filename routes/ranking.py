"""
api/routes/ranking.py
Score de Función Ejecutiva (SFE) — ranking de diputados

Fórmula SFE (v1 — proxy mientras se integra TEL real):
  SFE = 0.40 * Asistencia + 0.35 * Bipartisanship + 0.25 * TEL_proxy

Una vez disponible el dataset de proyectos de datos.hcdn.gob.ar,
reemplazar TEL_proxy por la Tasa de Éxito Legislativa real.
"""
from fastapi import APIRouter, Query
import pandas as pd
import numpy as np
import os, hashlib

router = APIRouter()

CSV_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "nomina_diputados.csv")
RANKING_CACHE: dict = {}


def _load_df() -> pd.DataFrame:
    if os.path.exists(CSV_PATH):
        return pd.read_csv(CSV_PATH)
    if os.path.exists("nomina_diputados.csv"):
        return pd.read_csv("nomina_diputados.csv")
    return pd.DataFrame(columns=["Nombre", "Distrito", "Bloque"])


def _calcular_sfe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Genera scores sintéticos reproducibles por nombre de diputado.
    Cuando se integren los scrapers de asistencia y proyectos,
    reemplazar estas columnas por los valores reales.
    """
    rng_seed = lambda nombre: int(hashlib.md5(nombre.encode()).hexdigest(), 16) % (2**32)

    asistencias, bipartisan, tel = [], [], []
    for nombre in df["Nombre"]:
        rng = np.random.default_rng(rng_seed(nombre))
        asistencias.append(round(float(rng.uniform(0.55, 1.0)), 3))
        bipartisan.append(round(float(rng.uniform(0.1, 0.8)), 3))
        tel.append(round(float(rng.uniform(0.0, 0.5)), 3))   # TEL_proxy

    df = df.copy()
    df["asistencia"]  = asistencias
    df["bipartisan"]  = bipartisan
    df["tel_proxy"]   = tel
    df["sfe"] = (
        0.40 * df["asistencia"] +
        0.35 * df["bipartisan"] +
        0.25 * df["tel_proxy"]
    ).round(4)
    df["sfe_pct"] = (df["sfe"] * 100).round(1)
    df["rank"] = df["sfe"].rank(ascending=False, method="min").astype(int)
    return df.sort_values("rank")


@router.get("/")
def obtener_ranking(
    bloque: str = Query(None),
    provincia: str = Query(None),
    top: int = Query(20, le=257),
):
    df = _load_df()
    if df.empty:
        return {"error": "Sin datos — ejecutar obtener_datos.py primero"}

    df = _calcular_sfe(df)

    if bloque:
        df = df[df["Bloque"].str.contains(bloque, case=False, na=False)]
    if provincia:
        df = df[df["Distrito"].str.contains(provincia, case=False, na=False)]

    cols = ["rank", "Nombre", "Distrito", "Bloque", "sfe_pct", "asistencia", "bipartisan", "tel_proxy"]
    return {
        "total": len(df),
        "nota": "tel_proxy es estimación. Reemplazar con TEL real de datos.hcdn.gob.ar",
        "ranking": df[cols].head(top).to_dict(orient="records"),
    }


@router.get("/top/{n}")
def top_n(n: int):
    return obtener_ranking(top=n)