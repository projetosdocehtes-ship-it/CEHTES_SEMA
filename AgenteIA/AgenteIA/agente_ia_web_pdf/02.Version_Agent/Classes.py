import numpy as np
import requests
import json
from scipy.interpolate import interp1d

from Var_globais import Resolucao_Clima

class Painel_Fotovoltaico:
    def __init__(self, Pmp, Isc, Voc, Imp, Vmp, Uisc, Uvoc, Upmp, material_painel, eficiencia):

        self.Pmp = Pmp      # Potência Max do painel ok
        self.Isc = Isc      # Corrente de curto circuito ok
        self.Voc = Voc      # Tensão de circuito aberto ok
        self.Imp = Imp      # Corrente de maxima potência ok
        self.Vmp = Vmp      # Tensão de maxima potência ok
        self.Uisc = Uisc    # Coeficiente de temperatura de corrente
        self.Uvoc = Uvoc    # Coeficiente de temperatura de tensão
        self.Upmp = Upmp    # Coeficiente de temperatura de potência

        if material_painel == "Silicio": #ok
          self.Cs = 0.11175
          self.Csh = 34.49692
        elif material_painel == "HIT":
          self.Cs = 0.16129000
          self.Csh = 124.48114

        self.Rsho = self.Csh * (self.Voc / self.Isc)   #Eq 21
        self.Rso = self.Cs * (self.Voc / self.Isc)     #Eq 21
        self.T_STC_C = 25
        self.T_STC_K = self.T_STC_C + 273.15
        self.G_STC = 1000
        self.eficiencia = eficiencia  # Eficiência

        self.Rsh = 0
        self.Rs  = 0
        self.Io  = 0
        self.IL  = 0
        self.nT  = 0
        self.n   = 0

        self.Calcular_Parametros_painel()

    def Retorna_Parametros_Calculados(self):
      return self.Rsh, self.Rs, self.Io, self.IL, self.nT, self.n

    def Retorna_Parametros_Datasheet(self):
      return self.Pmp, self.Isc, self.Voc, self.Uisc, self.Uvoc, self.Upmp

    def Normalizar_Parametros(self):
      Vrange = self.Voc
      Irange = self.Isc
      Voc_norm = self.Voc / Vrange
      Isc_norm = self.Isc / Irange
      Vmp_norm = self.Vmp / Vrange
      Imp_norm = self.Imp / Irange
      Rsho_norm = self.Rsho / Vrange * Irange
      Rso_norm = self.Rso / Vrange * Irange
      return Voc_norm, Isc_norm, Vmp_norm, Imp_norm, Rsho_norm, Rso_norm

    def sgn(self, x):
      if x > 0:
          return 1
      elif x < 0:
          return -1
      else:
          return 0

    def Calcular_Parametros_painel(self):
        Accuracy = 0.00001
        Rs = 0.01
        Step = 0.001
        Sign1 = 1
        Diff = Accuracy + 1

        Voc, Isc, Vmp, Imp, Rsho, Rso = self.Normalizar_Parametros()

        while 1:
            nT = (Vmp + Imp*Rs - Voc) / np.log(((Isc - Imp)*Rsho - (Vmp + Imp*Rs)) / (Isc*Rsho - Voc))
            Io = (Isc - Voc / Rsho) / (np.exp(Voc/nT) - 1)
            Diff = (Io / nT * np.exp(Voc/nT) + 1 / Rsho) / (1 + Rs * (Io / nT*np.exp(Voc/nT) + 1 / Rsho)) - 1 / Rso

            if abs(Diff) <= Accuracy:
                break
            Sign2 = self.sgn(Diff)
            if Sign1 != Sign2:  # Verifica se x1 é diferente de x2
                Step = -Step / 3
            Rs = Rs + Step
            Sign1 = Sign2

        self.Rsh = self.Rsho
        self.Rs = Rs * self.Voc / self.Isc
        self.Io = Io * self.Isc
        self.IL = self.Isc
        self.nT = nT * self.Voc
        self.n = nT / self.T_STC_K    #Diode Quality Factor

        return 0

class Inversor_DC_AC:
    def __init__(self, Nm_MPPT, In_Pmax, Imax_MPPT, In_Vnom, In_Vmin, In_Vmax, In_MPP_Vmin,  In_MPP_Vmax, Out_Pmax, Out_Imax, Out_Vnom, Out_Freq, Eficiencia, Max_THD, Fator_pot):
        # Parametros de Entrada
        self.Nm_MPPT = Nm_MPPT          # Numero de MPPT's
        self.In_Pmax = In_Pmax          # Potência Max do painel
        self.Imax_MPPT = Imax_MPPT      # Corrente Max por MPPT
        self.In_Vnom = In_Vnom          # Tensão nominal de entrada
        self.In_Vmin = In_Vmin          # Tensão minima de entrada
        self.In_Vmax = In_Vmax          # Tensão maxima de entrada
        self.In_MPP_Vmin = In_MPP_Vmin  # Tensão minima de ajuste MPPT
        self.In_MPP_Vmax = In_MPP_Vmax  # Tensão maxima de ajuste MPPT

        # Parametros de Saida
        self.Out_Pmax = Out_Pmax                  # Potencia max de saida
        self.Out_Imax = Out_Imax                  # Corrente max de saida
        self.Out_Vnom_RMS = Out_Vnom              # Tensão nominal de saida RMS
        self.Out_Vnom_PP = Out_Vnom * np.sqrt(2)  # Tensão nominal de saida Pico a Pico
        self.Out_Freq = Out_Freq                  # Frequencia de saida

        # Outros
        self.Eficiencia = Eficiencia  # Eficiencia do inversor
        self.Max_THD = Max_THD        # Maxima distorção harmonica
        self.Fator_pot = Fator_pot    # Fator de potência do inversor

    def Retorna_Parametros_Sim(self):
        return self.Out_Vnom_PP, self.Out_Freq, self.Eficiencia

class Clima_Ambiente:
    def __init__(self, nome_cidade, pais, data):
        self.nome_cidade = nome_cidade
        self.pais = pais
        self.data = data

        self.latitude = 0
        self.longitude = 0
        self.Temperatura = 0
        self.Irradiancia = 0

        self.Obter_Dados_Cidade()
        self.Temperatura_Interpolada = self.Arruma_Array(self.Temperatura, "T")
        self.Irradiancia_Interpolada = self.Arruma_Array(self.Irradiancia, "G")

        print("Dados da cidade obtidos !!!")

    def Retorna_Curvas(self):
      return self.Temperatura_Interpolada, self.Irradiancia_Interpolada

    def Retorna_Array(self):
      return self.Temperatura, self.Irradiancia

    def Obter_Dados_Cidade(self):
      # Etapa 1: Obter latitude e longitude
      url_nominatim = "https://nominatim.openstreetmap.org/search"
      params_nominatim = {
          'q': f"{self.nome_cidade}, {self.pais}",
          'format': 'json',
          'limit': 1,
          'addressdetails': 1
      }
      headers_nominatim = {
          'User-Agent': 'YourAppName/1.0 (your.email@domain.com)',
          'Referer': 'https://yourdomain.com'
      }

      response = requests.get(url_nominatim, params=params_nominatim, headers=headers_nominatim)

      if response.status_code == 200:
          data_nominatim = response.json()
          if not data_nominatim:
              raise ValueError("Cidade não encontrada.")
          latitude = float(data_nominatim[0]['lat'])
          longitude = float(data_nominatim[0]['lon'])
      else:
          raise ConnectionError(f"Erro na requisição Nominatim: {response.status_code}")

      # Etapa 2: Obter dados climáticos
      base_url_nasa = "https://power.larc.nasa.gov/api/temporal/hourly/point?"
      api_url_nasa = (
          f"{base_url_nasa}"
          f"start={self.data}&end={self.data}&"
          f"latitude={latitude}&longitude={longitude}&"
          f"community=ag&parameters=ALLSKY_SFC_SW_DWN,T2M&"
          f"format=json&header=true&time-standard=utc"
      )

      response = requests.get(api_url_nasa)

      if response.status_code == 200:
          data_nasa = response.json()
          try:
              allsky_data = data_nasa["properties"]["parameter"]["ALLSKY_SFC_SW_DWN"]
              t2m_data = data_nasa["properties"]["parameter"]["T2M"]
          except KeyError:
              raise KeyError("Dados de irradiância ou temperatura não encontrados na resposta da API.")

          array_irradiancia = list(allsky_data.values())
          array_temperatura = list(t2m_data.values())

          array_irradiancia = np.roll(array_irradiancia, -3)
          array_temperatura = np.roll(array_temperatura, -3)
          print("Sucesso na requisição NASA")
      else:
          raise ConnectionError(f"Erro na requisição NASA: {response.status_code}")

      self.latitude = latitude
      self.longitude = longitude
      self.Temperatura = array_temperatura
      self.Irradiancia = array_irradiancia

      return 1

    def Arruma_Array(self, array, tipo):
      t = np.linspace(0, 23, Resolucao_Clima)

      if tipo == 'G':
        array = np.array(array) * 1000 / 2.5

      array[array == 0] = 1
      tempo_original = np.linspace(0, len(array) - 1, len(array))
      interp = interp1d(tempo_original, array, kind='cubic', fill_value="extrapolate")
      curva_interpolada = interp(t)
      curva_interpolada = np.clip(curva_interpolada, 0.5, None)

      return curva_interpolada
