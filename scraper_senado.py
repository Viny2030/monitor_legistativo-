import time
import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service

def scraping_senado_real():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    # URL directa a la lista resumida
    url = "https://www.senado.gob.ar/senadores/listados/listaSenadoResumida"
    
    print(f"--- 🕵️ Navegando al Senado con Chrome ---")
    try:
        driver.get(url)
        time.sleep(10) # Aumentamos el tiempo para que cargue la tabla dinámica
        
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        # Buscamos la tabla específica por su clase o estructura
        nombres = []
        # En el Senado, los nombres suelen estar en la segunda columna de la tabla principal
        filas = soup.find_all('tr')
        
        for fila in filas:
            cols = fila.find_all('td')
            if len(cols) > 1:
                # El nombre suele estar en la columna que tiene el link al perfil
                nombre_texto = cols[1].get_text(strip=True)
                # Filtramos para que no capture botones como "Ordenar por"
                if len(nombre_texto) > 5 and "Ordenar" not in nombre_texto and "Relevance" not in nombre_texto:
                    nombres.append(nombre_texto)
        
        if nombres:
            print(f"✅ ¡LOGRADO! Se encontraron {len(nombres)} senadores reales.")
            for n in nombres[:10]: print(f"  👤 {n}")
            
            df = pd.DataFrame(nombres, columns=["Nombre"])
            df.to_csv("nomina_senadores.csv", index=False)
        else:
            print("⚠️ No se encontraron nombres. Posible cambio en la estructura HTML.")
            # Opcional: imprimir el texto de la página para debug si falla
            # print(soup.get_text()[:500]) 
            
    except Exception as e:
        print(f"❌ Falló Selenium: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    scraping_senado_real()
