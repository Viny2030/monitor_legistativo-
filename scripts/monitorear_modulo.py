"""
scripts/monitorear_modulo.py
Detecta cambios en el valor del Módulo Legislativo de HCDN.

Si encuentra un valor diferente al actual en personal.py:
  1. Imprime alerta
  2. Actualiza personal.py automáticamente (opcional con --actualizar)
  3. Guarda historial en modulo_historial.csv

Uso:
  python scripts/monitorear_modulo.py               # solo consulta
  python scripts/monitorear_modulo.py --actualizar  # actualiza personal.py
"""
import sys
import re
import csv
import os
from datetime import datetime
import requests
from bs4 import BeautifulSoup

# Valor actual importado de personal.py
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from personal import VALOR_MODULO

URLS_MODULO = [
    "https://www.hcdn.gob.ar/institucional/modulo/",
    "https://www.hcdn.gob.ar/institucional/retribuciones/",
]
HISTORIAL_CSV = "modulo_historial.csv"
PERSONAL_PY   = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "personal.py")
HEADERS = {"User-Agent": "Mozilla/5.0 (MEL-TP Monitor Legislativo)"}


def scrape_valor_modulo() -> int | None:
    """Intenta extraer el valor del módulo desde el sitio de HCDN."""
    for url in URLS_MODULO:
        try:
            res = requests.get(url, headers=HEADERS, timeout=12)
            soup = BeautifulSoup(res.text, "html.parser")
            texto = soup.get_text(separator=" ")

            # Patrones: "$215.000", "$ 215.000", "215000", "215,000"
            patrones = [
                r'\$\s*([\d]{2,3}[\.\,][\d]{3})',   # $215.000
                r'módulo[^\d]{0,20}([\d]{5,7})',      # módulo ... 215000
                r'([\d]{3}[\.\,][\d]{3})\s*(?:pesos|ars|\$)',
            ]
            for patron in patrones:
                matches = re.findall(patron, texto, re.IGNORECASE)
                if matches:
                    valor_str = matches[0].replace(".", "").replace(",", "")
                    valor = int(valor_str)
                    if 50_000 <= valor <= 5_000_000:  # rango razonable
                        print(f"  ✓ Valor encontrado en {url}: ${valor:,}")
                        return valor
        except Exception as e:
            print(f"  ⚠ Error al consultar {url}: {e}")

    return None


def guardar_historial(valor: int, fuente: str):
    """Agrega una fila al historial CSV."""
    existe = os.path.exists(HISTORIAL_CSV)
    with open(HISTORIAL_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not existe:
            writer.writerow(["fecha", "valor", "fuente"])
        writer.writerow([datetime.now().strftime("%Y-%m-%d %H:%M"), valor, fuente])


def actualizar_personal_py(nuevo_valor: int):
    """Reemplaza VALOR_MODULO en personal.py."""
    with open(PERSONAL_PY, "r", encoding="utf-8") as f:
        contenido = f.read()

    nuevo = re.sub(
        r'(VALOR_MODULO\s*:\s*int\s*=\s*int\(os\.environ\.get\("VALOR_MODULO",\s*)[0-9_]+(\)\))',
        lambda m: m.group(0).replace(
            re.search(r'[0-9_]+(?=\)\))', m.group(0)).group(),
            str(nuevo_valor)
        ),
        contenido
    )

    # Fallback más simple
    if nuevo == contenido:
        nuevo = re.sub(
            r'(os\.environ\.get\("VALOR_MODULO",\s*)[0-9_]+(\))',
            lambda m: f'{m.group(1)}{nuevo_valor}{m.group(2)}',
            contenido
        )

    with open(PERSONAL_PY, "w", encoding="utf-8") as f:
        f.write(nuevo)

    print(f"  ✅ personal.py actualizado → VALOR_MODULO = {nuevo_valor:,}")


def main():
    actualizar = "--actualizar" in sys.argv

    print("=" * 50)
    print("MEL-TP — Monitor de Módulo Legislativo")
    print(f"Valor actual en personal.py: ${VALOR_MODULO:,}")
    print("=" * 50)

    valor_nuevo = scrape_valor_modulo()

    if valor_nuevo is None:
        print("\n⚠️  No se pudo obtener el valor desde HCDN.")
        print("   Verificar manualmente: https://www.hcdn.gob.ar/institucional/modulo/")
        sys.exit(1)

    if valor_nuevo == VALOR_MODULO:
        print(f"\n✅ Sin cambios. Módulo vigente: ${VALOR_MODULO:,}")
        guardar_historial(valor_nuevo, "verificacion")
        sys.exit(0)

    # ── CAMBIO DETECTADO ──────────────────────────────────────────────────────
    print(f"\n🔔 CAMBIO DETECTADO:")
    print(f"   Anterior: ${VALOR_MODULO:,}")
    print(f"   Nuevo:    ${valor_nuevo:,}")
    print(f"   Variación: {((valor_nuevo - VALOR_MODULO) / VALOR_MODULO * 100):+.1f}%")

    guardar_historial(valor_nuevo, "scraper_hcdn")

    if actualizar:
        actualizar_personal_py(valor_nuevo)
        print(f"\n  También actualizar VALOR_MODULO en api/routes/costos.py")
    else:
        print(f"\n  Para actualizar automáticamente: python scripts/monitorear_modulo.py --actualizar")
        print(f"  O actualizar manualmente VALOR_MODULO en personal.py y api/routes/costos.py")
        # Salir con código 2 para que el pipeline lo detecte
        sys.exit(2)


if __name__ == "__main__":
    main()