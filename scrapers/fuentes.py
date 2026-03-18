"""
scrapers/fuentes.py
Explorador y descargador de las fuentes oficiales de datos financieros de HCDN.

FUENTES CONFIRMADAS Y SU ESTADO:
  ✅ Subsidios a terceros:   CSV directo por año
  ✅ Remuneraciones:         CSV/Excel en portal transparencia
  ✅ Nómina de personal:     datos.hcdn.gob.ar dataset
  ⚠️  Viajes nacionales:     links dinámicos (requiere inspección de red)
  ⚠️  Contratos locación:    existe pero no confirmado si es desagregado
"""

import requests
import pandas as pd
import io
import os
from datetime import datetime


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "es-AR,es;q=0.9",
}

DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

ANO_ACTUAL = datetime.now().year


# ─────────────────────────────────────────────────────────────────────────────
# 1. SUBSIDIOS A TERCEROS
#    Columnas: DIPUTADO | BENEFICIARIO | CUIT | MONTO | PROVINCIA
#    IMPORTANTE: Es dinero que el diputado OTORGA a entidades externas,
#    NO es sueldo del despacho. Útil para análisis de gasto político.
# ─────────────────────────────────────────────────────────────────────────────
def descargar_subsidios(ano: int = None, guardar: bool = True) -> pd.DataFrame:
    """
    Descarga el CSV de subsidios a terceros de HCDN.
    URL patrón: https://www4.hcdn.gob.ar/muestra/csv/subsidio_{año}.csv
    Nota: algunos años el servidor devuelve un ZIP en lugar de CSV directo.
    """
    import zipfile

    ano = ano or ANO_ACTUAL
    url = f"https://www4.hcdn.gob.ar/muestra/csv/subsidio_{ano}.csv"
    print(f"\n📥 Subsidios {ano}: {url}")

    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        r.raise_for_status()

        content_bytes = r.content

        # Detectar si el archivo es un ZIP o Excel (firma PK\x03\x04)
        if content_bytes[:2] == b'PK':
            import zipfile
            zf = zipfile.ZipFile(io.BytesIO(content_bytes))
            nombres = zf.namelist()

            # Si tiene estructura de Excel (.xlsx)
            if any('xl/' in n for n in nombres):
                print(f"  📊 Archivo Excel (.xlsx) detectado, leyendo con openpyxl...")
                try:
                    # Leer sin header para inspeccionar filas de título
                    raw = pd.read_excel(io.BytesIO(content_bytes), engine="openpyxl", header=None)

                    # Detectar si el Excel es un aviso "no otorgó subsidios"
                    texto_completo = " ".join(raw.fillna("").astype(str).values.flatten()).lower()
                    if "no" in texto_completo and ("otorgó" in texto_completo or "otorgo" in texto_completo):
                        print(f"  ℹ️  El Excel {ano} informa que no se otorgaron subsidios ese año.")
                        return pd.DataFrame()

                    # Buscar la fila que contiene los headers reales
                    # (la fila cuyas celdas coinciden con columnas esperadas)
                    header_row = None
                    columnas_esperadas = {"diputado", "beneficiario", "monto", "cuit", "provincia"}
                    for i, row in raw.iterrows():
                        vals = set(str(v).strip().lower() for v in row if pd.notna(v))
                        if len(vals & columnas_esperadas) >= 2:
                            header_row = i
                            break

                    if header_row is not None:
                        df = pd.read_excel(
                            io.BytesIO(content_bytes), engine="openpyxl",
                            header=header_row
                        )
                    else:
                        df = pd.read_excel(io.BytesIO(content_bytes), engine="openpyxl")

                    df.columns = [str(c).strip().upper() for c in df.columns]
                    df = df.dropna(how="all")
                    print(f"  ✅ Excel leído: {len(df)} filas | Columnas: {list(df.columns)}")

                    if df.empty:
                        print(f"  ℹ️  Sin registros de subsidios para {ano}.")
                        return pd.DataFrame()

                    if guardar:
                        ruta = os.path.join(DATA_DIR, f"subsidios_{ano}.csv")
                        df.to_csv(ruta, index=False, encoding="utf-8-sig")
                        print(f"  💾 Guardado: {ruta}")
                    return df
                except Exception as e:
                    print(f"  ❌ Error leyendo Excel: {e}")
                    return pd.DataFrame()

            # Si tiene CSVs dentro del ZIP
            csv_files = [n for n in nombres if n.lower().endswith('.csv')]
            if csv_files:
                print(f"  📦 ZIP con CSV detectado: {csv_files[0]}")
                content_bytes = zf.read(csv_files[0])
            else:
                print(f"  ❌ ZIP sin CSV ni Excel reconocible. Contenido: {nombres}")
                return pd.DataFrame()

        # Parsear el CSV (detectar encoding y separador)
        df = None
        for enc in ["utf-8", "latin-1", "iso-8859-1"]:
            try:
                texto = content_bytes.decode(enc)
                for sep in [",", ";"]:
                    try:
                        df = pd.read_csv(
                            io.StringIO(texto), sep=sep,
                            skipinitialspace=True, on_bad_lines="skip"
                        )
                        if len(df.columns) >= 3:
                            break
                    except Exception:
                        continue
                if df is not None and len(df.columns) >= 3:
                    break
            except UnicodeDecodeError:
                continue

        if df is None or df.empty:
            print(f"  ❌ No se pudo parsear el CSV de {ano}")
            return pd.DataFrame()

        df.columns = [c.strip().upper() for c in df.columns]
        print(f"  ✅ {len(df)} registros | Columnas: {list(df.columns)}")

        if guardar:
            ruta = os.path.join(DATA_DIR, f"subsidios_{ano}.csv")
            df.to_csv(ruta, index=False, encoding="utf-8-sig")
            print(f"  💾 Guardado: {ruta}")

        return df

    except requests.HTTPError as e:
        print(f"  ❌ HTTP {e.response.status_code} — El archivo de {ano} puede no existir aún.")
        return pd.DataFrame()
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return pd.DataFrame()


def descargar_subsidios_historico(desde: int = 2018, hasta: int = None) -> dict:
    """Descarga subsidios para múltiples años. Retorna dict {año: DataFrame}."""
    hasta = hasta or ANO_ACTUAL
    resultado = {}
    for ano in range(desde, hasta + 1):
        df = descargar_subsidios(ano=ano, guardar=True)
        if not df.empty:
            resultado[ano] = df
    print(f"\n📊 Subsidios descargados: {len(resultado)} años con datos")
    return resultado


# ─────────────────────────────────────────────────────────────────────────────
# 2. REMUNERACIONES (DIETAS + ADICIONALES)
#    La dieta es escalafonaria (igual para todos), pero los adicionales
#    (desarraigo, movilidad) varían por provincia de origen.
# ─────────────────────────────────────────────────────────────────────────────

# Montos vigentes 2024 (ajustar cuando se publique actualización)
ESCALA_REMUNERACIONES = {
    "dieta_bruta_mensual": 5_900_000,   # Aprox. — actualizar desde Boletín Oficial
    "opciones_movilidad": {
        "sin_desarraigo":       100_000,
        "opcion_b":             250_000,
        "opcion_c":             350_000,
        "opcion_d_desarraigo":  455_000,
    },
    "porcentaje_desarraigo": 0.1421,    # 14.21% adicional para provincias con desarraigo
    "distritos_con_desarraigo": [
        "BUENOS AIRES", "CÓRDOBA", "SANTA FE", "MENDOZA",
        "TUCUMÁN", "ENTRE RÍOS", "CORRIENTES", "MISIONES",
        "CHACO", "SALTA", "JUJUY", "SANTIAGO DEL ESTERO",
        "SAN JUAN", "SAN LUIS", "CATAMARCA", "LA RIOJA",
        "NEUQUÉN", "RÍO NEGRO", "FORMOSA", "CHUBUT",
        "SANTA CRUZ", "LA PAMPA", "TIERRA DEL FUEGO",
    ]
}


def calcular_remuneracion_estimada(distrito: str, opcion_movilidad: str = "opcion_c") -> dict:
    """
    Calcula la remuneración estimada de un diputado según su distrito.
    Basado en la escala pública documentada.
    """
    e = ESCALA_REMUNERACIONES
    base = e["dieta_bruta_mensual"]
    movilidad = e["opciones_movilidad"].get(opcion_movilidad, e["opciones_movilidad"]["opcion_c"])

    tiene_desarraigo = distrito.upper() not in ["CIUDAD DE BUENOS AIRES", "BUENOS AIRES"]
    desarraigo = base * e["porcentaje_desarraigo"] if tiene_desarraigo else 0

    total = base + movilidad + desarraigo

    return {
        "Distrito":              distrito,
        "Dieta_bruta":           base,
        "Movilidad":             movilidad,
        "Desarraigo":            round(desarraigo),
        "Total_estimado_mensual": round(total),
        "Total_estimado_anual":   round(total * 12),
    }


def generar_tabla_remuneraciones(df_nomina: pd.DataFrame) -> pd.DataFrame:
    """
    Dado un DataFrame con la nómina de diputados (columna 'Distrito'),
    genera la tabla de remuneraciones estimadas para cada uno.
    """
    if "Distrito" not in df_nomina.columns and "DISTRITO" not in df_nomina.columns:
        print("❌ El DataFrame no tiene columna 'Distrito'")
        return pd.DataFrame()

    col_distrito = "Distrito" if "Distrito" in df_nomina.columns else "DISTRITO"
    col_nombre   = "Nombre"   if "Nombre"   in df_nomina.columns else (
                   "DIPUTADO" if "DIPUTADO" in df_nomina.columns else df_nomina.columns[0])

    rows = []
    for _, row in df_nomina.iterrows():
        rem = calcular_remuneracion_estimada(str(row.get(col_distrito, "")))
        rem["Nombre"] = row.get(col_nombre, "")
        rem["Bloque"] = row.get("Bloque", row.get("BLOQUE", ""))
        rows.append(rem)

    df_rem = pd.DataFrame(rows)
    ruta = os.path.join(DATA_DIR, "remuneraciones_estimadas.csv")
    df_rem.to_csv(ruta, index=False, encoding="utf-8-sig")
    print(f"💾 Remuneraciones estimadas guardadas: {ruta}  ({len(df_rem)} filas)")
    return df_rem


# ─────────────────────────────────────────────────────────────────────────────
# 3. NÓMINA DE PERSONAL (ASESORES)
#    datos.hcdn.gob.ar — dataset de empleados por categoría y área
# ─────────────────────────────────────────────────────────────────────────────
# URLs confirmadas desde datos.hcdn.gob.ar (verificadas 18/03/2026)
URLS_NOMINA_PERSONAL_CANDIDATAS = [
    # Nómina de personal (legajo, nombre, tipo de planta, categoría, área)
    "https://datos.hcdn.gob.ar/dataset/af7136d5-84eb-49b2-af2e-aaf6319e4aae/resource/6e49506e-6757-44cd-94e9-0e75f3bd8c38/download/nomina3.6.csv",
]
URL_NOMINA_PERSONAL_CSV = URLS_NOMINA_PERSONAL_CANDIDATAS[0]

# Escala salarial (categoría → sueldo)
URL_ESCALA_SALARIAL = (
    "https://datos.hcdn.gob.ar/dataset/e471dfa2-92ab-4c6d-9bd1-b46d97c6ea1b"
    "/resource/673f193d-1cfb-46e0-b6c8-e931aa0a5314/download/escala-salarial1.5.csv"
)


def descargar_nomina_personal(guardar: bool = True) -> pd.DataFrame:
    """
    Descarga la nómina de personal de la Cámara de Diputados.
    Prueba múltiples URLs candidatas en orden hasta encontrar una que responda.
    El cruce clave es el campo AREA: si referencia a un despacho legislativo,
    se puede vincular al diputado correspondiente.
    """
    r = None
    url_usada = None

    for url in URLS_NOMINA_PERSONAL_CANDIDATAS:
        print(f"\n📥 Probando nómina personal: {url}")
        try:
            resp = requests.get(url, headers=HEADERS, timeout=30)
            if resp.status_code == 200:
                r = resp
                url_usada = url
                print("  ✅ Respondió con 200")
                break
            else:
                print(f"  ⚠️  HTTP {resp.status_code} — probando siguiente...")
        except Exception as e:
            print(f"  ❌ Error: {e} — probando siguiente...")

    if r is None:
        print("  ❌ Ninguna URL respondió correctamente.")
        print("  💡 Ir manualmente a https://datos.hcdn.gob.ar y buscar 'nómina personal'")
        print("     Copiar la URL directa del CSV y actualizar URLS_NOMINA_PERSONAL_CANDIDATAS[0]")
        return pd.DataFrame()

    try:
        df = None
        for enc in ["utf-8", "latin-1"]:
            try:
                df = pd.read_csv(
                    io.StringIO(r.content.decode(enc)),
                    sep=",", skipinitialspace=True
                )
                break
            except UnicodeDecodeError:
                continue

        if df is None or df.empty:
            print("  ❌ El archivo descargado está vacío o no es un CSV válido.")
            return pd.DataFrame()

        df.columns = [c.strip().upper() for c in df.columns]
        print(f"  ✅ {len(df)} empleados | Columnas: {list(df.columns)}")

        if "AREA" in df.columns:
            asesores = df[df["AREA"].str.contains("DESPACHO|ASESOR|DIPUTADO", case=False, na=False)]
            print(f"  👥 Registros vinculables a despachos: {len(asesores)}")

        if guardar:
            ruta = os.path.join(DATA_DIR, "nomina_personal.csv")
            df.to_csv(ruta, index=False, encoding="utf-8-sig")
            print(f"  💾 Guardado: {ruta}")

        return df

    except Exception as e:
        print(f"  ❌ Error procesando el archivo: {e}")
        return pd.DataFrame()

def diagnosticar_fuentes() -> None:
    """
    Verifica qué fuentes están disponibles y responden correctamente.
    Útil para debugging cuando los archivos salen vacíos.
    """
    fuentes = {
        "Nómina diputados (HTML scraping)":
            "https://www.diputados.gov.ar/diputados/index.html",
        "Subsidios 2024":
            "https://www4.hcdn.gob.ar/muestra/csv/subsidio_2024.csv",
        "Subsidios 2023":
            "https://www4.hcdn.gob.ar/muestra/csv/subsidio_2023.csv",
        "Nómina personal (datos abiertos)":
            "https://datos.hcdn.gob.ar",
        "Portal transparencia":
            "https://www.diputados.gov.ar/institucional/transparencia/index.html",
        "Votaciones (web)":
            "https://votaciones.hcdn.gob.ar/",
        "Votaciones API actas":
            "https://votaciones.hcdn.gob.ar/api/v2/actas/?limit=1&format=json",
    }

    print("\n" + "="*60)
    print("  DIAGNÓSTICO DE FUENTES MEL-TP")
    print("="*60)

    for nombre, url in fuentes.items():
        try:
            r = requests.head(url, headers=HEADERS, timeout=10, allow_redirects=True)
            estado = f"✅ HTTP {r.status_code}"
            content_type = r.headers.get("Content-Type", "")[:40]
        except requests.Timeout:
            estado = "⏱️  TIMEOUT"
            content_type = ""
        except Exception as e:
            estado = f"❌ ERROR: {str(e)[:40]}"
            content_type = ""

        print(f"  {estado:30s} | {nombre}")
        if content_type:
            print(f"  {'':30s}   Content-Type: {content_type}")

    print("="*60)



# ─────────────────────────────────────────────────────────────────────────────
# 5. ESCALA SALARIAL
#    Permite cruzar categoría del empleado → sueldo → asignar al despacho
# ─────────────────────────────────────────────────────────────────────────────
def descargar_escala_salarial(guardar: bool = True) -> pd.DataFrame:
    """
    Descarga la escala salarial de HCDN.
    Columnas esperadas: CATEGORIA | SUELDO (o similar)
    Permite calcular el costo real de cada asesor por categoría escalafón.
    """
    print(f"\n📥 Escala salarial: {URL_ESCALA_SALARIAL}")
    try:
        r = requests.get(URL_ESCALA_SALARIAL, headers=HEADERS, timeout=20)
        r.raise_for_status()

        for enc in ["utf-8", "latin-1"]:
            try:
                df = pd.read_csv(io.StringIO(r.content.decode(enc)), skipinitialspace=True)
                break
            except UnicodeDecodeError:
                continue

        df.columns = [c.strip().upper() for c in df.columns]
        print(f"  ✅ {len(df)} categorías | Columnas: {list(df.columns)}")

        if guardar:
            ruta = os.path.join(DATA_DIR, "escala_salarial.csv")
            df.to_csv(ruta, index=False, encoding="utf-8-sig")
            print(f"  💾 Guardado: {ruta}")

        return df

    except Exception as e:
        print(f"  ❌ Error: {e}")
        return pd.DataFrame()


# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    diagnosticar_fuentes()
    print("\n--- Probando descarga de subsidios 2024 ---")
    descargar_subsidios(2024)
    print("\n--- Probando nómina de personal ---")
    descargar_nomina_personal()
    print("\n--- Probando escala salarial ---")
    descargar_escala_salarial()