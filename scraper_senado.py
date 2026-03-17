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
    
    # Configuramos el driver para que funcione en el servidor de GitHub
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    url = "https://www.senado.gob.ar/senadores/listados/listaSenadoResumida"
    
    print(f"--- 🕵️ Navegando al Senado con Chrome ---")
    try:
        driver.get(url)
        time.sleep(7) # Un poco más de tiempo para asegurar la carga
        
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        filas = soup.find_all('tr')
        
        nombres = []
        for fila in filas[1:]: # Procesamos todos
            cols = fila.find_all('td')
            if len(cols) > 1:
                nombres.append(cols[1].get_text(strip=True))
        
        if nombres:
            print(f"✅ ¡LOGRADO! Se encontraron {len(nombres)} senadores.")
            for n in nombres[:5]: print(f"  👤 {n}")
            
            # Guardamos el resultado en un CSV para el futuro
            df = pd.DataFrame(nombres, columns=["Nombre"])
            df.to_csv("nomina_senadores.csv", index=False)
        else:
            print("⚠️ El sitio cargó pero no detectamos la tabla.")
            
    except Exception as e:
        print(f"❌ Falló Selenium: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    scraping_senado_real()
