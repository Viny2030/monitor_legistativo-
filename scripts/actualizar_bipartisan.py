import sys
from datetime import datetime
import holidays

def es_momento_de_correr():
    hoy = datetime.now()
    # 1. ¿Es fin de semana? (5=Sábado, 6=Domingo)
    if hoy.weekday() >= 5:
        return False, "Fin de semana"
    
    # 2. ¿Es feriado en Argentina?
    ar_holidays = holidays.Argentina()
    if hoy in ar_holidays:
        return False, f"Feriado ({ar_holidays.get(hoy)})"
    
    return True, "Día hábil"

def main():
    print("=" * 60)
    print("=== MEL-TP: Verificador de Calendario HCDN ===")
    
    debe_correr, motivo = es_momento_de_correr()
    if not debe_correr:
        print(f"☕ Saltando ejecución: {motivo}. Los datos no estarán actualizados hoy.")
        sys.exit(0) # Salida limpia para GitHub Actions

    print("🚀 Iniciando proceso de datos...")
    # ... resto del código que ya tienes ...
