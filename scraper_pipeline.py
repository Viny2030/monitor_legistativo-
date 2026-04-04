"""
scraper_pipeline.py
===================
Pipeline unificado de automatizacion de datos para monitor_legistativo (Diputados).
Genera data/diputados.json con todos los campos necesarios para el dashboard.

Fuentes:
  - diputados.gov.ar          → nomina + genero
  - hcdn.gob.ar/secparl/dclp  → asistencia por diputado
  - hcdn.gob.ar/proyectos/     → proyectos presentados / aprobados
  - presupuestoabierto.gob.ar  → ejecucion presupuestaria (API REST)
  - votaciones.hcdn.gob.ar     → votaciones nominales (IQP)

NO modifica ningun archivo HTML existente.
El HTML debe leer data/diputados.json en tiempo de ejecucion (cuando sirve desde Railway).
Para entorno local file:// el JSON se inyecta via inject_json_to_html.py (ver abajo).

Uso:
    python scraper_pipeline.py              # corre todo el pipeline
    python scraper_pipeline.py --step nomina
    python scraper_pipeline.py --step asistencia
    python scraper_pipeline.py --step proyectos
    python scraper_pipeline.py --step presupuesto
    python scraper_pipeline.py --step votaciones
"""

import argparse
import json
import os
import re
import time
from datetime import datetime

import requests
from bs4 import BeautifulSoup

# ---------------------------------------------------------------------------
# Configuracion
# ---------------------------------------------------------------------------
OUTPUT_DIR = "data"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "diputados.json")
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; MonitorLegislativo/1.0)"}
TIMEOUT = 30

# Nombres femeninos frecuentes en Argentina para deteccion de genero
# (fallback heuristico; el campo genero del scraper tiene prioridad)
_NOMBRES_F = {
    "maria", "ana", "laura", "sandra", "carolina", "andrea", "patricia",
    "monica", "claudia", "vanesa", "natalia", "silvana", "roxana", "graciela",
    "marcela", "liliana", "karina", "alejandra", "veronica", "gabriela",
    "paula", "cecilia", "florencia", "lucia", "mariana", "victoria", "beatriz",
    "norma", "susana", "stella", "mabel", "alba", "irma", "nilda", "elsa",
    "rosa", "olga", "mirta", "gladys", "silvia", "cristina", "romina",
    "lorena", "sabrina", "yamila", "celeste", "brenda", "magali", "soledad",
    "cintia", "noelia", "melisa", "valeria", "agustina", "micaela", "jimena",
    "antonella", "josefina", "belen", "pilar", "mercedes", "ines", "teresa",
    "nora", "alicia", "amanda", "esther", "estela", "amalia", "elvira",
    "adelaida", "griselda", "alejandrina", "rebeca", "eugenia", "marta"
}


def _detect_gender(nombre):
    """Heuristica de genero por primer nombre. Devuelve 'F', 'M' o 'ND'."""
    parts = nombre.lower().split()
    if not parts:
        return "ND"
    # apellido primero: "GARCIA, Maria" → tomar despues de la coma
    if "," in nombre:
        after_comma = nombre.split(",", 1)[1].strip().lower().split()
        primer = after_comma[0] if after_comma else parts[0]
    else:
        primer = parts[0]
    primer = re.sub(r"[^a-z]", "", primer)
    if primer in _NOMBRES_F:
        return "F"
    return "M"


def ensure_output_dir():
    os.makedirs(OUTPUT_DIR, exist_ok=True)


def load_existing():
    """Carga el JSON existente para hacer merge incremental."""
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"meta": {}, "diputados": [], "presupuesto": {}, "votaciones": {}}


def save(data):
    data["meta"]["ultima_actualizacion"] = datetime.now().isoformat()
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"[OK] {OUTPUT_FILE} guardado ({len(data['diputados'])} diputados)")


# ---------------------------------------------------------------------------
# STEP 1 — Nomina + Genero
# ---------------------------------------------------------------------------
def scrape_nomina():
    """
    Fuente: https://www.diputados.gov.ar/diputados/
    Campos obtenidos: nombre, distrito, bloque, mandato_hasta, genero
    """
    print("[STEP 1] Scraping nomina de diputados...")
    url = "https://www.diputados.gov.ar/diputados/"
    try:
        res = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, "html.parser")
        tabla = soup.find("table")
        if not tabla:
            print("[WARN] No se encontro tabla en diputados.gov.ar")
            return []

        diputados = []
        filas = tabla.find_all("tr")[1:]
        for fila in filas:
            cols = fila.find_all("td")
            if len(cols) < 4:
                continue
            nombre = cols[1].get_text(strip=True)
            distrito = cols[2].get_text(strip=True)
            bloque = cols[3].get_text(strip=True)
            # Columna de mandato puede variar; intentar col 4 si existe
            mandato_hasta = cols[4].get_text(strip=True) if len(cols) > 4 else ""
            diputados.append({
                "nombre": nombre,
                "distrito": distrito,
                "bloque": bloque,
                "mandato_hasta": mandato_hasta,
                "genero": _detect_gender(nombre),  # mejorar con datos oficiales
                "asistencia_pct": None,
                "proyectos_presentados": None,
                "proyectos_aprobados": None,
                "iqp": None
            })
        print(f"[OK] {len(diputados)} diputados encontrados")
        return diputados
    except Exception as e:
        print(f"[ERROR] scrape_nomina: {e}")
        return []


# ---------------------------------------------------------------------------
# STEP 2 — Asistencia por diputado
# ---------------------------------------------------------------------------
def scrape_asistencia(diputados):
    """
    Fuente: https://hcdn.gob.ar/secparl/dclp/asistencia.html
    Agrega campo asistencia_pct a cada diputado por coincidencia de nombre.
    """
    print("[STEP 2] Scraping asistencia...")
    url = "https://hcdn.gob.ar/secparl/dclp/asistencia.html"
    try:
        res = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, "html.parser")

        # Construir mapa nombre -> porcentaje de asistencia
        asistencia_map = {}
        tabla = soup.find("table")
        if tabla:
            for fila in tabla.find_all("tr")[1:]:
                cols = fila.find_all("td")
                if len(cols) >= 2:
                    nombre_raw = cols[0].get_text(strip=True).upper()
                    pct_raw = cols[-1].get_text(strip=True).replace("%", "").replace(",", ".")
                    try:
                        pct = float(pct_raw)
                        asistencia_map[nombre_raw] = pct
                    except ValueError:
                        pass

        # Match por nombre (normalizacion simple)
        matched = 0
        for d in diputados:
            key = d["nombre"].upper()
            if key in asistencia_map:
                d["asistencia_pct"] = asistencia_map[key]
                matched += 1
            else:
                # Intento de match parcial con apellido
                apellido = key.split(",")[0].strip()
                for k, v in asistencia_map.items():
                    if apellido in k:
                        d["asistencia_pct"] = v
                        matched += 1
                        break

        # Calcular NAPE por bloque
        for d in diputados:
            if d["asistencia_pct"] is not None:
                d["nape"] = round(1 - d["asistencia_pct"] / 100, 4)

        print(f"[OK] Asistencia matcheada para {matched}/{len(diputados)} diputados")
    except Exception as e:
        print(f"[ERROR] scrape_asistencia: {e}")

    return diputados


# ---------------------------------------------------------------------------
# STEP 3 — Proyectos (SIL / hcdn.gob.ar/proyectos)
# ---------------------------------------------------------------------------
def scrape_proyectos(diputados):
    """
    Fuente: https://www.hcdn.gob.ar/proyectos/
    Scrapea proyectos del anio legislativo en curso y los cuenta por autor.
    Agrega proyectos_presentados y proyectos_aprobados a cada diputado.
    """
    print("[STEP 3] Scraping proyectos del SIL...")
    anio = datetime.now().year
    # El SIL expone busqueda por anio; usar pagina de resultados
    url = f"https://www.hcdn.gob.ar/proyectos/resultado.html?anio={anio}&tipo=0"
    try:
        res = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, "html.parser")

        proyectos_map = {}  # nombre_autor -> {presentados, aprobados}
        tabla = soup.find("table", {"id": "tablaResultados"}) or soup.find("table")
        if tabla:
            for fila in tabla.find_all("tr")[1:]:
                cols = fila.find_all("td")
                if len(cols) < 4:
                    continue
                autor_raw = cols[2].get_text(strip=True).upper()
                estado = cols[3].get_text(strip=True).upper()
                if autor_raw not in proyectos_map:
                    proyectos_map[autor_raw] = {"presentados": 0, "aprobados": 0}
                proyectos_map[autor_raw]["presentados"] += 1
                if "SANCIONADO" in estado or "APROBADO" in estado:
                    proyectos_map[autor_raw]["aprobados"] += 1

        matched = 0
        for d in diputados:
            apellido = d["nombre"].split(",")[0].strip().upper()
            for k, v in proyectos_map.items():
                if apellido in k:
                    d["proyectos_presentados"] = v["presentados"]
                    d["proyectos_aprobados"] = v["aprobados"]
                    matched += 1
                    break

        print(f"[OK] Proyectos matcheados para {matched}/{len(diputados)} diputados")
    except Exception as e:
        print(f"[ERROR] scrape_proyectos: {e}")

    return diputados


# ---------------------------------------------------------------------------
# STEP 4 — Ejecucion presupuestaria (Presupuesto Abierto API REST)
# ---------------------------------------------------------------------------
def scrape_presupuesto():
    """
    Fuente: https://www.presupuestoabierto.gob.ar/sici/datos-abiertos
    API REST publica. Consulta ejecucion del ejercicio para el Poder Legislativo
    (Jurisdiccion 01 — Congreso de la Nacion).
    Devuelve dict con credito_vigente, devengado, iap.
    """
    print("[STEP 4] Consultando API de Presupuesto Abierto...")
    anio = datetime.now().year
    # Endpoint publico de datos abiertos
    base = "https://www.presupuestoabierto.gob.ar/sici/rest-api/credito"
    params = {
        "ejercicio": anio,
        "jurisdiccion": "01",   # Poder Legislativo
        "formato": "json"
    }
    try:
        res = requests.get(base, params=params, headers=HEADERS, timeout=TIMEOUT)
        res.raise_for_status()
        datos = res.json()

        # La respuesta puede ser una lista de partidas; sumar credito y devengado
        credito = 0
        devengado = 0
        for item in datos if isinstance(datos, list) else [datos]:
            credito += float(item.get("credito_vigente", 0) or 0)
            devengado += float(item.get("devengado", 0) or 0)

        iap = round(devengado / credito, 4) if credito > 0 else None
        resultado = {
            "ejercicio": anio,
            "credito_vigente_m": round(credito / 1_000_000, 2),
            "devengado_m": round(devengado / 1_000_000, 2),
            "iap": iap
        }
        print(f"[OK] IAP calculado: {iap} (devengado {devengado/1e9:.1f}B / credito {credito/1e9:.1f}B ARS)")
        return resultado
    except Exception as e:
        print(f"[ERROR] scrape_presupuesto: {e}")
        return {}


# ---------------------------------------------------------------------------
# STEP 5 — Votaciones nominales (IQP por diputado)
# ---------------------------------------------------------------------------
def scrape_votaciones(diputados):
    """
    Fuente: https://votaciones.hcdn.gob.ar/api/
    API publica de votaciones nominales de la HCDN.
    Calcula IQP (Indice de Calidad de Participacion) = votos_emitidos / sesiones_convocado.
    """
    print("[STEP 5] Consultando API de votaciones nominales...")
    anio = datetime.now().year
    api_base = "https://votaciones.hcdn.gob.ar/api"

    try:
        # Obtener periodos del anio
        res = requests.get(f"{api_base}/periodos/?format=json", headers=HEADERS, timeout=TIMEOUT)
        res.raise_for_status()
        periodos = res.json()

        # Filtrar periodo actual
        periodo_actual = None
        for p in (periodos.get("results") or periodos if isinstance(periodos, list) else []):
            if str(anio) in str(p.get("anio", "") or p.get("periodo", "")):
                periodo_actual = p
                break

        if not periodo_actual:
            print("[WARN] No se encontro periodo actual en la API de votaciones")
            return diputados

        periodo_id = periodo_actual.get("id") or periodo_actual.get("numero")

        # Obtener resumen de asistencia por legislador para ese periodo
        res2 = requests.get(
            f"{api_base}/legisladores/asistencia/?periodo={periodo_id}&format=json",
            headers=HEADERS, timeout=TIMEOUT
        )
        res2.raise_for_status()
        leg_data = res2.json()

        iqp_map = {}
        for item in (leg_data.get("results") or leg_data if isinstance(leg_data, list) else []):
            nombre = item.get("legislador", {}).get("apellido_nombre", "").upper()
            convocado = int(item.get("convocado", 0) or 0)
            emitio = int(item.get("emitio", 0) or 0)
            if convocado > 0:
                iqp_map[nombre] = round(emitio / convocado, 4)

        matched = 0
        for d in diputados:
            apellido = d["nombre"].split(",")[0].strip().upper()
            for k, v in iqp_map.items():
                if apellido in k:
                    d["iqp"] = v
                    matched += 1
                    break

        print(f"[OK] IQP calculado para {matched}/{len(diputados)} diputados")
    except Exception as e:
        print(f"[ERROR] scrape_votaciones: {e}")

    return diputados


# ---------------------------------------------------------------------------
# Pipeline completo
# ---------------------------------------------------------------------------
def run_pipeline(steps=None):
    ensure_output_dir()
    data = load_existing()

    all_steps = {"nomina", "asistencia", "proyectos", "presupuesto", "votaciones"}
    steps = set(steps) if steps else all_steps

    if "nomina" in steps:
        diputados = scrape_nomina()
        if diputados:
            data["diputados"] = diputados
    else:
        diputados = data.get("diputados", [])

    if "asistencia" in steps and diputados:
        diputados = scrape_asistencia(diputados)
        data["diputados"] = diputados

    if "proyectos" in steps and diputados:
        diputados = scrape_proyectos(diputados)
        data["diputados"] = diputados

    if "presupuesto" in steps:
        data["presupuesto"] = scrape_presupuesto()

    if "votaciones" in steps and diputados:
        diputados = scrape_votaciones(diputados)
        data["diputados"] = diputados

    save(data)
    return data


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pipeline de scraping legislativo")
    parser.add_argument(
        "--step",
        choices=["nomina", "asistencia", "proyectos", "presupuesto", "votaciones"],
        help="Correr solo un step especifico"
    )
    args = parser.parse_args()
    steps = [args.step] if args.step else None
    t0 = time.time()
    run_pipeline(steps)
    print(f"[DONE] Pipeline completado en {time.time()-t0:.1f}s")