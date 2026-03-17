from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import time

def scraping_senado_real():
    chrome_options = Options()
    chrome_options.add_argument("--headless") # No abre ventana (necesario en GitHub)
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    driver = webdriver.Chrome(options=chrome_options)
    url = "https://www.senado.gob.ar/senadores/listados/listaSenadoResumida"
    
    print(f"--- 🕵️ Navegando al Senado con Chrome ---")
    try:
        driver.get(url)
        time.sleep(5) # Esperamos que el firewall nos deje pasar
        
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        filas = soup.find_all('tr')
        
        nombres = []
        for fila in filas[1:10]:
            cols = fila.find_all('td')
            if len(cols) > 1:
                nombres.append(cols[1].get_text(strip=True))
        
        if nombres:
            print("✅ ¡LOGRADO! Senadores encontrados:")
            for n in nombres: print(f"  👤 {n}")
        else:
            print("⚠️ El sitio cargó pero no detectamos la tabla. Puede ser un cambio de diseño.")
            
    except Exception as e:
        print(f"❌ Falló Selenium: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    scraping_senado_real()
