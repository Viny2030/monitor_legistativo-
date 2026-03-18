"""
personal.py
Valor del Módulo Legislativo y datos de personal.

ACTUALIZAR VALOR_MODULO cuando monitorear_modulo() detecte un nuevo valor.
También se puede setear via variable de entorno: VALOR_MODULO=215000
"""
import os

# ── Módulo legislativo ────────────────────────────────────────────────────────
# Fuente: https://www.hcdn.gob.ar/institucional/modulo/
# Actualizar manualmente o via: python scripts/monitorear_modulo.py
VALOR_MODULO: int = int(os.environ.get("VALOR_MODULO", 215_000))

# ── Factores de dieta por categoría ──────────────────────────────────────────
FACTORES_DIETA = {
    "diputado":           10.0,   # dieta base = 10 módulos
    "presidente_bloque":  12.0,
    "vicepresidente":     15.0,
}

# ── Personal por diputado (promedio estimado) ─────────────────────────────────
PERSONAL_PROMEDIO_MODULOS = 14  # entre 8 y 20 módulos según dotación

# ── Rubros fijos mensuales (en módulos) ──────────────────────────────────────
GASTOS_REPRESENTACION_MODULOS = 2.0
COMUNICACIONES_BASE_ARS       = 80_000  # ARS fijo + variable


def dieta_mensual(categoria: str = "diputado") -> int:
    factor = FACTORES_DIETA.get(categoria, FACTORES_DIETA["diputado"])
    return int(VALOR_MODULO * factor)


def personal_estimado_mensual(n_empleados: int = PERSONAL_PROMEDIO_MODULOS) -> int:
    return int(VALOR_MODULO * n_empleados)


def gastos_representacion_mensual() -> int:
    return int(VALOR_MODULO * GASTOS_REPRESENTACION_MODULOS)


def costo_base_mensual(categoria: str = "diputado") -> dict:
    """Costo base fijo independiente del diputado (sin pasajes ni viáticos)."""
    return {
        "dieta":              dieta_mensual(categoria),
        "personal_promedio":  personal_estimado_mensual(),
        "gastos_rep":         gastos_representacion_mensual(),
        "comunicaciones_base": COMUNICACIONES_BASE_ARS,
        "modulo":             VALOR_MODULO,
    }


if __name__ == "__main__":
    print(f"Módulo actual: ${VALOR_MODULO:,}")
    costos = costo_base_mensual()
    for k, v in costos.items():
        print(f"  {k:30s}: ${v:>12,}")
    print(f"\n  {'TOTAL BASE':30s}: ${sum(v for k,v in costos.items() if k != 'modulo'):>12,}")