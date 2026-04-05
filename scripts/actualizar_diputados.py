#!/usr/bin/env python3
"""
actualizar_diputados.py
Lee nomina_diputados.csv y actualiza el array const DIPUTADOS = [...]
en los 3 HTMLs del dashboard de Diputados usando marcadores.

Marcadores esperados en cada HTML:
  // DIPUTADOS:START
  const DIPUTADOS = [ ... ];
  // DIPUTADOS:END

Uso:
  python scripts/actualizar_diputados.py
"""

import csv
import re
import sys
from pathlib import Path

# ── Configuración ────────────────────────────────────────────────────────────
CSV_PATH = Path("nomina_diputados.csv")

HTMLS = [
    Path("dashboard/indicadores_diputados.html"),
    Path("dashboard/nomina_detalle_diputados.html"),
    Path("dashboard/indicadores_bloques_diputados.html"),
]

MARKER_START = "// DIPUTADOS:START"
MARKER_END   = "// DIPUTADOS:END"

# ── Helpers ──────────────────────────────────────────────────────────────────
def escape_js(s: str) -> str:
    """Escapa comillas dobles para JS."""
    return s.replace("\\", "\\\\").replace('"', '\\"')

def inferir_genero(nombre: str) -> str:
    """
    Inferencia básica de género por terminación del primer nombre.
    Devuelve 'F', 'M' o 'I' (indeterminado).
    """
    # Tomar el primer nombre (antes de la coma está el apellido)
    partes = nombre.split(",")
    primer_nombre = partes[1].strip().split()[0] if len(partes) > 1 else ""
    primer_nombre = primer_nombre.lower()

    terminaciones_f = ("a", "ina", "ita", "ela", "elia", "ia", "isa")
    terminaciones_m = ("o", "os", "er", "el", "on", "in", "ar", "us")

    for t in terminaciones_f:
        if primer_nombre.endswith(t):
            return "F"
    for t in terminaciones_m:
        if primer_nombre.endswith(t):
            return "M"
    return "I"

# ── Leer CSV ─────────────────────────────────────────────────────────────────
def leer_csv() -> list[dict]:
    if not CSV_PATH.exists():
        print(f"ERROR: No se encontró {CSV_PATH}")
        sys.exit(1)

    diputados = []
    with open(CSV_PATH, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            diputados.append(row)

    print(f"  CSV leído: {len(diputados)} diputados")
    return diputados

# ── Construir bloque JS ───────────────────────────────────────────────────────
def construir_bloque_js(diputados: list[dict]) -> str:
    """
    Genera el bloque completo:
      // DIPUTADOS:START
      const DIPUTADOS = [...];
      // DIPUTADOS:END
    """
    lines = [MARKER_START, "const DIPUTADOS = ["]

    # Detectar columnas disponibles en el CSV
    if not diputados:
        lines.append("];")
        lines.append(MARKER_END)
        return "\n".join(lines)

    cols = set(diputados[0].keys())
    tiene_genero  = "genero"  in cols or "género" in cols
    tiene_mandato = "mandato" in cols

    for i, d in enumerate(diputados):
        nombre   = escape_js(d.get("Nombre", d.get("nombre", "")).strip())
        distrito = escape_js(d.get("Distrito", d.get("distrito", "")).strip().upper())
        bloque   = escape_js(d.get("Bloque", d.get("bloque", "")).strip())
        mandato  = escape_js(d.get("Mandato", d.get("mandato", d.get("mandato_hasta", ""))).strip())

        # Género: del CSV si existe, sino inferir
        if tiene_genero:
            genero = d.get("genero", d.get("género", "I")).strip()
        else:
            genero = inferir_genero(nombre)

        coma = "," if i < len(diputados) - 1 else ""
        lines.append(
            f'  {{nombre:"{nombre}",distrito:"{distrito}",'
            f'bloque:"{bloque}",mandato:"{mandato}",genero:"{genero}"}}{coma}'
        )

    lines.append("];")
    lines.append(MARKER_END)
    return "\n".join(lines)

# ── Inyectar en HTML ──────────────────────────────────────────────────────────
def inyectar_en_html(html_path: Path, bloque_nuevo: str) -> bool:
    if not html_path.exists():
        print(f"  WARN: {html_path} no existe, omitiendo")
        return False

    contenido = html_path.read_text(encoding="utf-8")

    if MARKER_START not in contenido or MARKER_END not in contenido:
        print(f"  WARN: marcadores no encontrados en {html_path.name}, omitiendo")
        return False

    # Reemplazar todo entre (e incluyendo) los marcadores
    patron = re.compile(
        re.escape(MARKER_START) + r".*?" + re.escape(MARKER_END),
        re.DOTALL
    )

    nuevo_contenido = patron.sub(bloque_nuevo, contenido)

    if nuevo_contenido == contenido:
        print(f"  {html_path.name}: sin cambios")
        return False

    html_path.write_text(nuevo_contenido, encoding="utf-8")
    print(f"  ✅ {html_path.name}: actualizado")
    return True

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    print("── Actualizando array DIPUTADOS en HTMLs ──")

    diputados = leer_csv()
    bloque    = construir_bloque_js(diputados)

    actualizados = 0
    for html in HTMLS:
        if inyectar_en_html(html, bloque):
            actualizados += 1

    print(f"\n✅ {actualizados}/{len(HTMLS)} archivos actualizados")
    print(f"   Total diputados: {len(diputados)}")

if __name__ == "__main__":
    main()