import requests
import pandas as pd
import os
import sys
from io import StringIO
import json
from datetime import datetime
try:
    import holidays
except ImportError:
    # Si no tienes la librería, fallará el check de feriados, 
    # pero el de fin de semana seguirá funcionando.
    holidays = None

def es_dia_habil():
    hoy = datetime.now()
    # 1. Check de Fin de Semana (5 es Sábado, 6 es Domingo)
    if hoy.weekday() >= 5:
        return False, "Fin de semana"
    
    # 2. Check de Feriados Argentina
    if holidays:
        feriados_ar = holidays.Argentina()
        if hoy in feriados_ar:
            return False, f"Feriado ({feriados_ar.get(hoy)})"
    
    return True, "Día hábil"

# ... (resto de tus funciones: descargar_csv, obtener_recursos_ckan, etc.)

def main():
    print("=== MEL-TP: Verificador de Calendario ===")
    habil, motivo = es_dia_habil()
    if not habil:
        print(f"☕ {motivo}. Saltando ejecución para evitar errores de API (servidores HCDN offline).")
        sys.exit(0) # Salida limpia (éxito) pero sin hacer nada

    print("🚀 Iniciando actualización...")
    # ... aquí sigue tu lógica de descargar_csv y calcular_bipartisan ...
