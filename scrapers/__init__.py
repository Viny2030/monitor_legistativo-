from .diputados import obtener_nomina
from .fuentes import (
    descargar_subsidios,
    descargar_subsidios_historico,
    descargar_nomina_personal,
    generar_tabla_remuneraciones,
    diagnosticar_fuentes,
)
from .votaciones import descargar_votaciones, calcular_indicadores_votacion

__all__ = [
    "obtener_nomina",
    "descargar_subsidios",
    "descargar_subsidios_historico",
    "descargar_nomina_personal",
    "generar_tabla_remuneraciones",
    "diagnosticar_fuentes",
    "descargar_votaciones",
    "calcular_indicadores_votacion",
]