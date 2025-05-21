from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import time
import os

# Caminho absoluto para o arquivo HTML
caminho_arquivo = os.path.abspath("../public/mapa_gini_ceara.html")
url_local = "file://" + caminho_arquivo

options = Options()
options.headless = True
options.add_argument("--window-size=1200,1000")

service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=options)

driver.get(url_local)
time.sleep(2)  # Dá tempo do mapa carregar

driver.save_screenshot("../public/mapa_gini_ceara.png")
driver.quit()