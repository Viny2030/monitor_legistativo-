import requests

def probar_sitios():
    sitios = {
        "Diputados": "https://www.diputados.gov.ar/diputados/",
        "Senado": "https://www.senado.gob.ar/"
    }
    
    for nombre, url in sitios.items():
        try:
            # Añadimos un 'User-Agent' para que GitHub no sea bloqueado como bot
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(url, headers=headers, timeout=15)
            print(f"✅ {nombre}: Estado {response.status_code}")
        except Exception as e:
            print(f"❌ {nombre}: Error -> {e}")

if __name__ == "__main__":
    probar_sitios()
