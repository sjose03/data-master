from urllib.request import urlopen
from bs4 import BeautifulSoup
import json
from selenium import webdriver
from time import sleep
from datetime import date
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
import zipfile
import os

html = urlopen('https://www.portaltransparencia.gov.br/download-de-dados/servidores')
bs = BeautifulSoup(html, 'html.parser')

script_inputs = bs.findAll('script')[12]
script_text = script_inputs.getText().split('\n')
cleaned_list = [x.lstrip().replace('arquivos.push(', '').replace(');', '') for x in script_text if 'arquivos.' in x]
years_list = list(set([json.loads(x)['ano'] for x in cleaned_list]))
months_list = list(set([json.loads(x)['mes'] for x in cleaned_list]))
origins_list = list(set([json.loads(x)['origem'] for x in cleaned_list]))
years_list.sort()
months_list.sort()
origins_list.sort()

# This is not needed if chromedriver is already on your path:
chromedriver_path = "/usr/lib/chromium-browser/chromedriver"

options = Options()
# options.add_argument("--window-size=1920x1080")
# options.add_argument("--verbose")
options.add_argument("--headless")
preferences = {
                "profile.default_content_settings.popups": 0,
                "download.default_directory": os.getcwd() + os.path.sep,
                "directory_upgrade": True
            }

options.add_experimental_option('prefs', preferences)
driver = webdriver.Chrome(chromedriver_path, options=options)
driver.get("https://www.portaltransparencia.gov.br/download-de-dados/servidores")

for year in years_list:
    if int(year) < 2021:
        continue
    for month in months_list:
        for origin in origins_list:
            if 'servidores' in origin.lower():
                if int(year) == date.today().year:
                    if int(month) > (date.today().month - 1):
                        continue
                print(f'Consultando o ano {year} no mes {month} para o tipo {origin}')
                try:
                    select_ano = Select(driver.find_element(by=By.ID, value='links-anos'))
                    select_ano.select_by_value(year)
                    select_meses = Select(driver.find_element(by=By.ID, value='links-meses'))
                    select_meses.select_by_value(month.zfill(2))
                    select_origins = Select(driver.find_element(by=By.ID, value='links-origens-mes'))
                    select_origins.select_by_value(origin)
                    dowload_btn = driver.find_element(by=By.ID, value='btn')
                    dowload_btn.click()
                    sleep(3)
                except:
                    print('Essa combinacao deu ruim')
arquivos = [x for x in os.listdir('.') if '.zip' in x and '.zip.' not in x]
remove_files = [x for x in os.listdir('.') if '.zip.' in x]
[os.remove(x) for x in remove_files]

print(remove_files)
for arquivo in arquivos:
    print(arquivo)
    with zipfile.ZipFile(f'{arquivo}', 'r') as zip_ref:
        names = [x for x in zip_ref.namelist() if 'cadastro' in x.lower() or 'remuneracao' in x.lower()]
        for name in names:
            zip_ref.extract(name, 'data')
            prefixo = '_'.join(arquivo.split('.')[0].split('_')[1:])
            os.rename(f'data/{name}', f'data/{name.split(".")[0]}_{prefixo}.csv')

    os.remove(f'{arquivo}')
