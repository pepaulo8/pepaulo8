import os
import pkg_resources
import json
import subprocess
import platform
from time import sleep

required = {'numpy', 'selenium', 'scipy', 'requests'}
installed = {pkg.key for pkg in pkg_resources.working_set}
missing = required - installed
for pkg in missing:
    os.system(f'pip3 install {pkg}')

from bs4 import BeautifulSoup
import requests
import numpy as np
from io import BytesIO
from scipy.io import wavfile

import pandas as pd

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

class RFBElements:
    URLmain = 'http://servicos.receita.fazenda.gov.br/Servicos/cnpjreva/Cnpjreva_Solicitacao_CS.asp'
    URLwave = 'http://servicos.receita.fazenda.gov.br/Servicos/cnpjreva/captcha/gerarSom.asp'

    BTSearch = (By.XPATH, '//*[@id="frmConsulta"]/div[3]/div/button[1]')
    INPUTCnpj = (By.XPATH, '//*[@id="cnpj"]')
    INPUTCaptcha = (By.XPATH, '//*[@id="txtTexto_captcha_serpro_gov_br"]')

    DIVContent = (By.ID, 'principal')
    CSSPrint = "<link href='http://servicos.receita.fazenda.gov.br/Servicos/cnpjreva/css/print.css' rel='stylesheet' type='text/css' />"
    IMAGEBrasao = 'http://servicos.receita.fazenda.gov.br/Servicos/cnpjreva/images/brasao2.gif'

class RFB_CNPJ:
    def __init__(self) -> None:
        self.header = {'User-Agent' : 'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.5060.134 Safari/537.36'}
        self.driver = None
        print('Iniciando o processo, vamos lá\n')

        with open('digits.json') as f:
            self.digitsData = json.load(f)

        
        if platform.system() == 'Darwin':
            self.copy_keyword = 'pbcopy'
        elif platform.system() == 'Windows':
            self.copy_keyword = 'clip'

    # def _paste_text(self, value):
    #     value = "echo %s | xsel -b" % value
    #     os.system(value)
    #     ActionChains(self.driver).key_down(Keys.CONTROL).key_down('v').key_up('v').key_up(Keys.CONTROL).perform()


    def _paste_text(self, value):
        subprocess.run(self.copy_keyword, universal_newlines=True, input=value)
        ActionChains(self.driver).key_down(Keys.CONTROL).key_down('v').key_up('v').key_up(Keys.CONTROL).perform()

    def _download_wave(self, first_try = True):
        if first_try:
            sleep(2)
        WebDriverWait(self.driver, 5).until(EC.presence_of_element_located(RFBElements.INPUTCaptcha))

        cookie_dict = {}
        for cookie in self.driver.get_cookies():
            cookie_dict[cookie['name']] = cookie['value']

        header = self.header

        r = requests.get(RFBElements.URLwave, cookies= cookie_dict, headers = header)
        
        if r.content == b'':
            print("Não consegui capturar o áudio, tentando de novo...\n")
            if not first_try:
                print('Error: Failed to download wave file, please reload the page!')
                self.driver.refresh()
                sleep(1)
                self._download_wave(first_try=True)
            else:
                sleep(1)
                r = requests.get(RFBElements.URLwave, cookies= cookie_dict, headers = header)
                if r.content == b'':
                    print(r.content, 2)
                    self._download_wave(first_try=False)
                else:
                    self.wave_rate, self.wave_data = wavfile.read(BytesIO(r.content))
                    return True
                    
        else:
            self.wave_rate, self.wave_data = wavfile.read(BytesIO(r.content))
            return True

    def _remove_noise(self, data, acc = .4, steps = 500):
        x = data.copy()
        last = 0
        for idx in range(steps, len(x), steps):
            dist = len(set(x[last:idx])) / len(x[last:idx])
            if dist > acc and dist < .91:
                x[last:idx] = self._remove_noise(x[last:idx], steps = int(steps/2))
            if dist < acc:
                x[last:idx] = 0
            last = idx
        return x

    def _find_letters(self, x, limit = 100):
        letters = []
        letter = False
        zeros = 0
        for idx, value in enumerate(x):
            if value != 0 and letter == False:
                start = idx
                letter = True
                zeros = 0
            elif value == 0 and letter:
                zeros += 1

            if (zeros > limit and letter) or (idx == len(x)-1):
                if (idx-limit) - start >= 2000:
                    letters.append(x[start:idx-limit])
                letter = False

        return letters

    def _solve_captcha(self):
        new_data = self._remove_noise(self.wave_data)
        limit = 100
        ar_letters = 'letters'
        while len(ar_letters) > 6:
            limit += 50
            ar_letters = self._find_letters(new_data, limit = limit)

        r = ''
        for letter in ar_letters:
            maxs = sorted(letter, reverse=True)[:100]
            mins = sorted(letter)[:100]

            for key, values in self.digitsData.items():
                try:
                    if (np.std(np.array(values['maxs']) - np.array(maxs)) < 10) or (np.std(np.array(values['mins']) - np.array(mins)) < 10):
                        r += key
                        break
                except ValueError as e:
                    print('Erro na operação das matrizes para resolver o captcha: ', e, '\n')
                    return False
            # print(r, :Valor do captcha')
        return r

    def _get(self, cnpj, show = False):
        

        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
        self.driver = driver
        print('ID da sessão: ', self.driver.session_id)
        self.driver.get(RFBElements.URLmain)

        if self._download_wave():
            self.driver.find_element(*RFBElements.INPUTCaptcha).click()
            # if not self._solve_captcha():
            #     return False
            captcha = self._solve_captcha()
            if not captcha:
                return False
            elif len(captcha) != 6:
                print('Não houve problema com as matrizes, mas o captcha encontrado não era o correto.\n')
                return False
            else:
                self._paste_text(captcha)
                self.driver.find_element(*RFBElements.INPUTCnpj).click()
                self._paste_text(cnpj)
                self.driver.find_element(*RFBElements.BTSearch).click()            
                return True
        else:
            return False

    def main(self, show = False):
        
        listaCnpj = []
        global listaFinal
        listaFinal = []

        data = pd.read_csv('ESTABELE_000476.CSV', header=None, sep=";")
        dfBase = pd.DataFrame(data)
        dfDropped2 = dfBase.drop(dfBase.columns[3:], axis=1)
        dfDropped = dfDropped2.drop(dfBase.index[50:])

        firstColumn = list(dfDropped[0])
        for (index, row) in enumerate(firstColumn):
            row = str(row)
            while len(row) != 8:
                row = '0' + row
                if len(row) == 8:
                    firstColumn[index] = row
                    
        secondColumn = list(dfDropped[1])
        for (index, row) in enumerate(secondColumn):
            row = str(row)
            while len(row) != 4:
                row = '0' + row
                if len(row) == 4:
                    secondColumn[index] = row

        thirdColumn = list(dfDropped[2])
        for (index, row) in enumerate(thirdColumn):
            row = str(row)
            while len(row) != 2:
                row = '0' + row
                if len(row) == 2:
                    thirdColumn[index] = row

        for (index, row) in enumerate(firstColumn):
            listaCnpj.append(str(firstColumn[index]) + str(secondColumn[index]) + str(thirdColumn[index]))

        for (loop, cnpj) in enumerate(listaCnpj):
            global sitCadastralFlag
            sitCadastralFlag = False

            print(f'CNPJ N° {loop + 1}')

            sitCadastral = {
                "CNPJ": cnpj,
                "Data de Abertura" : "//table[(((count(preceding-sibling::*) + 1) = 3) and parent::*)]",
                "Nome Empresarial" : "//table[(((count(preceding-sibling::*) + 1) = 5) and parent::*)]//b",
                "Nome Fantasia" : "//table[(((count(preceding-sibling::*) + 1) = 7) and parent::*)]//td[(((count(preceding-sibling::*) + 1) = 1) and parent::*)]//b",
                "Porte" : "//table[(((count(preceding-sibling::*) + 1) = 7) and parent::*)]//td[(((count(preceding-sibling::*) + 1) = 3) and parent::*)]//b",
                "Atividade Principal" : "//table[(((count(preceding-sibling::*) + 1) = 9) and parent::*)]//b",
                "Atividades Secundarias" : "//table[(((count(preceding-sibling::*) + 1) = 11) and parent::*)]//b",
                "Natureza Juridica" : "//table[(((count(preceding-sibling::*) + 1) = 13) and parent::*)]//b",
                "Logradouro" : "//table[(((count(preceding-sibling::*) + 1) = 15) and parent::*)]//td[(((count(preceding-sibling::*) + 1) = 1) and parent::*)]//b",
                "Numero" : "//table[(((count(preceding-sibling::*) + 1) = 15) and parent::*)]//td[(((count(preceding-sibling::*) + 1) = 3) and parent::*)]//b",
                "Complemento" : "//table[(((count(preceding-sibling::*) + 1) = 15) and parent::*)]//td[(((count(preceding-sibling::*) + 1) = 5) and parent::*)]//b",
                "CEP" : "//table[(((count(preceding-sibling::*) + 1) = 17) and parent::*)]//td[(((count(preceding-sibling::*) + 1) = 1) and parent::*)]//b",
                "Bairro" : "//table[(((count(preceding-sibling::*) + 1) = 17) and parent::*)]//td[(((count(preceding-sibling::*) + 1) = 3) and parent::*)]//b",
                "Municipio" : "//table[(((count(preceding-sibling::*) + 1) = 17) and parent::*)]//td[(((count(preceding-sibling::*) + 1) = 5) and parent::*)]//b",
                "UF" : "//td[(((count(preceding-sibling::*) + 1) = 7) and parent::*)]//b",
                "Endereco Eletronico" : "//table[(((count(preceding-sibling::*) + 1) = 19) and parent::*)]//td[(((count(preceding-sibling::*) + 1) = 1) and parent::*)]//b",
                "Telefone" : "//table[(((count(preceding-sibling::*) + 1) = 19) and parent::*)]//td[(((count(preceding-sibling::*) + 1) = 3) and parent::*)]//b",
                "EFR" : "//table[(((count(preceding-sibling::*) + 1) = 21) and parent::*)]//b",
                "Situacao Cadastral" : "//table[(((count(preceding-sibling::*) + 1) = 23) and parent::*)]//td[(((count(preceding-sibling::*) + 1) = 1) and parent::*)]//b",
                "Data da Situacao Cadastral" : "//table[(((count(preceding-sibling::*) + 1) = 23) and parent::*)]//td[(((count(preceding-sibling::*) + 1) = 3) and parent::*)]//b",
                "Motivo da Situacao Cadastral" : "//table[(((count(preceding-sibling::*) + 1) = 25) and parent::*)]//b",
                "Situacao Especial" : "//table[(((count(preceding-sibling::*) + 1) = 27) and parent::*)]//td[(((count(preceding-sibling::*) + 1) = 1) and parent::*)]//b",
                "Motivo da Situacao Especial" : "//table[(((count(preceding-sibling::*) + 1) = 27) and parent::*)]//td[(((count(preceding-sibling::*) + 1) = 3) and parent::*)]//b",
                "QSA": ""
            }

            if not self._get(cnpj, show = True):
                print('Indo pro próximo CNPJ...\n')
                self.driver.quit()
                self.driver = None
                sleep(0.25)
                continue
            
            secAtiv = []
            for index, campo in enumerate(sitCadastral):

                if list(sitCadastral.keys())[index] == "CNPJ":
                    sitCadastral[campo] = cnpj

                elif list(sitCadastral.keys())[index] == "Data de Abertura":
                    table = self.driver.find_element(By.XPATH, '//table[(((count(preceding-sibling::*) + 1) = 3) and parent::*)]')
                    html = self.driver.execute_script("return arguments[0].innerHTML;",table)
                    soup = BeautifulSoup(html, 'html.parser')
                    sitCadastral[campo] = soup.find_all("b")[-1].text


                elif list(sitCadastral.keys())[index] == "Atividade Principal":  
                    table = self.driver.find_element(By.XPATH, '//table[(((count(preceding-sibling::*) + 1) = 9) and parent::*)]//b')
                    html = self.driver.execute_script("return arguments[0].innerHTML;",table)

                    sitCadastral[campo] = { "text" : html.strip()[13:], "code" : html.strip()[:10] }

                elif list(sitCadastral.keys())[index] == "Atividades Secundarias":  
                    table = self.driver.find_element(By.XPATH, '//table[(((count(preceding-sibling::*) + 1) = 11) and parent::*)]//td')
                    html = self.driver.execute_script("return arguments[0].innerHTML;",table)

                    soup = BeautifulSoup(html, 'html.parser')
                    for i in soup.find_all("b"):
                        secAtiv.append({ "text" : i.text.strip()[13:], "code" : i.text.strip()[:10] })
                    sitCadastral[campo] = secAtiv

                elif list(sitCadastral.keys())[index] == "QSA":
                    listaSocios = []
                    self.driver.get("http://servicos.receita.fazenda.gov.br/Servicos/cnpjreva/Cnpjreva_qsa.asp")
                    scrapSocios = self.driver.find_elements(By.CLASS_NAME, 'col-md-9')
                    scrapCargos = self.driver.find_elements(By.CLASS_NAME, 'col-md-5') 
                    numSocios = len(scrapSocios) - 3
                    for i in range(numSocios):
                        listaSocios.append({"nome" : scrapSocios[i+3].text, "qual": scrapCargos[i].text})
                    sitCadastral[campo] = listaSocios  
                    
                else:
                    try:
                        WebDriverWait(self.driver, 5).until(
                            EC.presence_of_element_located((By.XPATH, sitCadastral[campo]))
                        )
                        sitCadastral[campo] = self.driver.find_element(By.XPATH, sitCadastral[campo]).text
                    except:
                        sitCadastralFlag = True
                        self.driver.quit()
                        self.driver = None
                        sleep(0.25)
                        break

            if sitCadastralFlag:
                continue

            listaFinal.append(sitCadastral)
            self.driver.quit()
            self.driver = None
            sleep(0.25)
            print(f'CNPJ: {cnpj}\nEsse foi fácil, indo pro próximo\n')
            
        with open('infoCNPJs.json', 'w') as fp:
            json.dump(listaFinal, fp, ensure_ascii=False)
            
if __name__ == '__main__':
     RFB_CNPJ().main()
