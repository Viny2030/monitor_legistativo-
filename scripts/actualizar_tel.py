"""
scripts/actualizar_tel.py
Tasa de Éxito Legislativo (TEL) — Prioridad Media

Fuente: Dataset de proyectos parlamentarios en datos.hcdn.gob.ar
  - URL base: https://datos.hcdn.gob.ar/dataset/proyectos-parlamentarios

TEL = proyectos_aprobados / proyectos_presentados  (por autor, período)

Reemplaza el proxy bipartisanship actual en el SFE.
"""
import requests
import pandas as pd
import os

BASE_URL = "https://datos.hcdn.gob.ar"

# Endpoint CKAN de datasets de proyectos
CKAN_API  = f"{BASE_URL}/api/3/action/package_show"
DATASET_ID = "proyectos-parlamentarios"


def obtener_url_recursos():
    """Obtiene los links de descarga de los recursos del dataset."""
    try:
        res = requests.get(CKAN_API, params={"id": DATASET_ID}, timeout=15)
        data = res.json()
        recursos = data.get("result", {}).get("resources", [])
        return [(r.get("name"), r.get("url")) for r in recursos if r.get("url")]
    except Exception as e:
        print(f"⚠️  Error al consultar API CKAN: {e}")
        return []


def calcular_tel(df_proyectos: pd.DataFrame) -> pd.DataFrame:
    """
    Calcula la TEL por diputado.

    Espera columnas: autor, tipo_resultado (APROBADO / RECHAZADO / etc.)
    Adaptar según estructura real del CSV de HCDN.
    """
    if "autor" not in df_proyectos.columns:
        print("⚠️  Columna 'autor' no encontrada. Revisar estructura del dataset.")
        return pd.DataFrame()

    total      = df_proyectos.groupby("autor").size().rename("presentados")
    aprobados  = (
        df_proyectos[df_proyectos.get("tipo_resultado", pd.Series()).str.upper() == "APROBADO"]
        .groupby("autor")
        .size()
        .rename("aprobados")
    )
    tel = pd.concat([total, aprobados], axis=1).fillna(0)
    tel["tel"] = (tel["aprobados"] / tel["presentados"]).round(4)
    return tel.reset_index()


def main():
    print("=== Actualizando TEL desde datos.hcdn.gob.ar ===")
    recursos = obtener_url_recursos()

    if not recursos:
        print("❌ No se pudieron obtener recursos. Verificar conectividad o URL del dataset.")
        return

    for nombre, url in recursos:
        print(f"  📄 Recurso: {nombre} — {url}")

    # Intento de descarga del primer CSV encontrado
    csv_recursos = [(n, u) for n, u in recursos if u.endswith(".csv")]
    if not csv_recursos:
        print("⚠️  No se encontraron recursos CSV. Inspeccionar manualmente:")
        for n, u in recursos:
            print(f"     {u}")
        return

    nombre_res, url_csv = csv_recursos[0]
    print(f"\n⬇️  Descargando: {url_csv}")
    try:
        df = pd.read_csv(url_csv, encoding="utf-8", low_memory=False)
        print(f"✅  Descargado: {len(df)} filas · columnas: {list(df.columns)}")

        tel_df = calcular_tel(df)
        if not tel_df.empty:
            out = "tel_diputados.csv"
            tel_df.to_csv(out, index=False)
            print(f"✅  TEL calculado y guardado en '{out}'")
            print(tel_df.head(10))
        else:
            print("⚠️  No se pudo calcular TEL. Adaptar calcular_tel() según columnas reales.")
    except Exception as e:
        print(f"❌ Error al procesar CSV: {e}")


if __name__ == "__main__":
    main()