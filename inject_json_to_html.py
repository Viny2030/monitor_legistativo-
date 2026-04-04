"""
inject_json_to_html.py
======================
Helper para entorno local (file://).

En Railway el HTML consume /api/diputados via fetch().
En local (file://) fetch() a localhost falla por CORS / mixed content.

Este script lee data/diputados.json e inyecta los datos directamente
en el HTML como una variable JS global, de modo que el dashboard
funcione sin servidor.

Uso:
    python inject_json_to_html.py
    # genera dashboard/indicadores_diputados_local.html (NO modifica el original)

El HTML debe tener el marcador:
    /* __INJECT_DATA__ */
dentro de un <script> para que la inyeccion funcione. Si no existe,
el script agrega el bloque al principio del primer <script>.
"""

import json
import os
import re
import shutil
from datetime import datetime

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
DATA_FILE = os.path.join("data", "diputados.json")
HTML_SRC = os.path.join("dashboard", "indicadores_diputados.html")
HTML_OUT = os.path.join("dashboard", "indicadores_diputados_local.html")

MARKER = "/* __INJECT_DATA__ */"

INJECT_TEMPLATE = """
/* === DATOS INYECTADOS AUTOMATICAMENTE por inject_json_to_html.py === */
/* Generado: {timestamp} */
window.__MONITOR_DATA__ = {json_data};
/* === FIN DATOS INYECTADOS === */
"""


def inject():
    # Verificar archivos fuente
    if not os.path.exists(DATA_FILE):
        print(f"[ERROR] {DATA_FILE} no existe. Correr scraper_pipeline.py primero.")
        return

    if not os.path.exists(HTML_SRC):
        print(f"[ERROR] {HTML_SRC} no existe.")
        return

    # Leer datos
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    json_str = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    inject_block = INJECT_TEMPLATE.format(
        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M"),
        json_data=json_str
    )

    # Leer HTML original
    with open(HTML_SRC, "r", encoding="utf-8") as f:
        html = f.read()

    # Estrategia 1: reemplazar marcador si existe
    if MARKER in html:
        html = html.replace(MARKER, inject_block, 1)
        print(f"[OK] Marcador '{MARKER}' encontrado y reemplazado")
    else:
        # Estrategia 2: insertar al inicio del primer <script>
        match = re.search(r"(<script[^>]*>)", html, re.IGNORECASE)
        if match:
            pos = match.end()
            html = html[:pos] + "\n" + inject_block + html[pos:]
            print(f"[OK] Datos inyectados al inicio del primer <script>")
        else:
            # Estrategia 3: agregar <script> antes de </body>
            html = html.replace(
                "</body>",
                f"<script>{inject_block}</script>\n</body>",
                1
            )
            print(f"[OK] Datos inyectados via nuevo <script> antes de </body>")

    # Escribir HTML de salida (NUNCA sobreescribe el original)
    with open(HTML_OUT, "w", encoding="utf-8") as f:
        f.write(html)

    n = len(data.get("diputados", []))
    print(f"[OK] {HTML_OUT} generado con {n} diputados")
    print(f"     Abrir en: file:///{os.path.abspath(HTML_OUT).replace(os.sep, '/')}")


if __name__ == "__main__":
    inject()