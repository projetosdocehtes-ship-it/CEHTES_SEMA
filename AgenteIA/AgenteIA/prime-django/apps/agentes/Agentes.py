import mesa
import numpy as np
from scipy.integrate import solve_ivp

from Var_globais import Iteracao_Sim

# ------------------------------------ Agentes -------------------------------------
class Agente_Clima(mesa.Agent):
    def __init__(self, model, Clima):
        super().__init__(model)   # Pass the parameters to the parent class.
        self.temperatura, self.irradiancia = Clima.Retorna_Curvas()

    def Simula_Clima_Transiente(self):

        if self.model.steps == 1:
          self.temperatura = np.full_like(self.temperatura, 25)
          self.irradiancia = np.full_like(self.irradiancia, 1000)

        self.step_total = Iteracao_Sim  # Total de steps
        self.step_atual = self.model.steps  # Passo atual
        self.Step_mudanca = self.step_total / 2  # Dividido em 4 partes
        self.last_printed = False  # Variável para controlar quando já imprimiu

        if (self.step_atual % self.Step_mudanca == 0) and not self.last_printed:
            self.Nova_Irrad = self.irradiancia[1]
            self.irradiancia = np.full_like(self.irradiancia, self.Nova_Irrad-200)

            self.last_printed = True  # Impede que imprima mais de uma vez no mesmo step
            # print(f"Entrou Irrad = {self.irradiancia}, nova_Irrad = {self.Nova_Irrad}")
        else:
            # Caso o passo não corresponda, se não for o momento de imprimir, reseta
            if self.step_atual % self.Step_mudanca != 0:
                self.last_printed = False

    def Simula_Clima_Estatico(self):
        if self.model.steps == 1:
          self.temperatura = np.full_like(self.temperatura, 25)
          self.irradiancia = np.full_like(self.irradiancia, 1000)

class Agente_Painel(mesa.Agent):
    def __init__(self, model, Painel):
        super().__init__(model)   # Pass the parameters to the parent class.
        self.Rsh, self.Rs, self.Io, self.IL, self.nT, self.n = Painel.Retorna_Parametros_Calculados()
        self.Pmp, self.Isc, self.Voc, self.Uisc, self.Uvoc, self.Upmp = Painel.Retorna_Parametros_Datasheet()

        self.V_MPPT = self.Voc / 3
        self.Array = "Array_1"

        self.G_antigo = 1000

    def Simula_PV(self):
      if (self.model.Clima[0].temperatura.size == 0 or self.model.Clima[0].irradiancia.size == 0):
        T_Atual = 0.0001
        G_Atual = 0.0001
      else:
        T_Atual = self.model.Clima[0].temperatura[self.model.steps - 1]
        G_Atual = self.model.Clima[0].irradiancia[self.model.steps - 1]

      IL_GT, Io_GT, _ = self.Calcula_Param_auxiliares(T_Atual, G_Atual)

      I_init = self.Isc / 2
      self.I_calc = self.Newton_Raphson_Corrente(self.V_MPPT, I_init, IL_GT, Io_GT)

      if G_Atual != self.G_antigo:
        self.V_MPPT = self.Voc / 3

      self.Pot_calc = self.V_MPPT * self.I_calc
      self.V_MPPT = self.model.Inversor[0].MPPT(self.Pot_calc, self.V_MPPT)
      self.G_antigo = G_Atual

      self.Perda_sombreamento = 1 - (self.Pot_calc / (self.Pmp*1.01))
      # print(f"I = {I_calc}, V = {self.V_MPPT}, P = {self.Pot_calc}")

    def Calcula_Param_auxiliares(self, T_sim, G_sim):
      C1 = 5.468511e-2
      C2 = 5.973869e-3
      C3 = 7.616178e-4
      T_STC_C = 25
      G_STC = 1000

      T_sim_K = T_sim + 273.15
      nT_sim = (T_sim + 273.15)*self.n
      if G_sim <= 0:
        G_sim = 1e-4
      aG = G_sim / G_STC  # Irradiância relativa

      IL_T = self.Isc + self.Uisc * (T_sim - T_STC_C)  # Corrente de curto-circuito ajustada # Foi alterada da formula do artigo
      IL_GT = IL_T * aG  # Corrente de curto-circuito com irradiância
      Voc_GT = self.Voc * (1 + C1*np.log(aG) + C2*np.log(aG)**2 + C3*np.log(aG)**3)  + self.Uvoc * (T_sim - T_STC_C)
      Io_GT = aG * ((IL_T - (Voc_GT / self.Rsh)) / (np.exp(Voc_GT / self.nT) - 1))  # Corrente de saturação ajustada

      return IL_GT, Io_GT, Voc_GT

    def Newton_Raphson_Corrente(self, V_init, I_init, IL, Io):
      for _ in range(100):
          exp_term = np.exp((V_init + I_init * self.Rs) / self.nT)
          f = IL - Io * (exp_term - 1) - (V_init + I_init * self.Rs) / self.Rsh - I_init
          df = -Io * (self.Rs / self.nT) * exp_term - self.Rs / self.Rsh - 1          # Derivada da função
          I_new = I_init - f / df

          if np.abs(I_new - I_init) < 1e-6:
              if I_new < 0:
                  return 0
              else:
                return I_new
          I_init = I_new          # Atualizar corrente para próxima iteração

    def Gerar_curva_IV(self, T_sim, G_sim):
      IL_GT, Io_GT, Voc_GT = self.Calcula_Param_auxiliares(T_sim, G_sim)
      V_array= np.linspace(0, Voc_GT, 10000)  # Vd_max variando de 0 até Voc_GT com 10000 pontos
      I_init = self.Isc / 2
      I_array = []
      for V_init in V_array:  # Limite de iterações
        I = self.Newton_Raphson_Corrente(V_init, I_init, IL_GT, Io_GT)
        I_array.append(I)

      return V_array, I_array

class Agente_Inversor(mesa.Agent):
    def __init__(self, model, Inversor):
        super().__init__(model)   # Pass the parameters to the parent class.

        #Valores Relacionados ao MPPT
        self.P_PV_Anterior = 0
        self.V_PV_Anterior = 0
        self.MPPT_learning_rate =  0.2

        #Valores Relacionados ao Filtro RLC
        self.Out_V_PP, self.Out_Freq, self.eficiencia = Inversor.Retorna_Parametros_Sim()

        self.Perda_inversor = 1 - self.eficiencia

        self.Filtro_R = 3.4
        self.Filtro_L = 0.01
        self.Filtro_C = 680e-6

        self.Cond_Iniciais_V = [0, 0]
        self.Cond_Iniciais_I = [0, 0]
        self.Passo = 5E-5
        self.Tempo_Sim = 0  # Começa do tempo 0

    def Sim_Inversor(self):
        self.V_out, self.I_out = self.Sim_VI()   #------------------------------------------------------------------------------------------------------------------------------------ Continuar sim Inversor e testar tudo

    # ------------------------------ Saída Tensão -----------------------------------------

    def Modulacao_PWM(self, t):
        Onda_triangular = self.Amp_Tri * ( 1 - 2 * np.abs( (t / self.T_sw) - np.floor( (t / self.T_sw) + (1 / 2) ) ) )

        Onda_seno1 = np.sin(2 * np.pi * self.Out_Freq * t + 0)
        Onda_PWM1 = 0.5 * (1 + np.sign(Onda_seno1 - Onda_triangular))

        Onda_seno2 = np.sin(2 * np.pi * self.Out_Freq * t + np.pi)
        Onda_PWM2 = 0.5 * (1 + np.sign(Onda_seno2 - Onda_triangular))

        pwm_resultante = Onda_PWM1 - Onda_PWM2

        return pwm_resultante

    def EDO_Filtro_RLC(self, t, y):
        q, dq_dt = y
        m_t = self.Modulacao_PWM(t)     # Modulação PWM fictícia para teste
        d2q_dt2 = (1 / self.Filtro_L) * (self.model.V_DC_Total * m_t - q / self.Filtro_C - dq_dt * self.Filtro_R) # EDO do filtro RLC em uma onda PWM
        return [dq_dt, d2q_dt2]

    def EDO_Corrente_carga(self, t, y, Vout):
        R = self.model.Carga[0].Carga_R
        L = self.model.Carga[0].Carga_L
        C = self.model.Carga[0].Carga_C

        i = y[0]  # Corrente no circuito
        v_c = y[1] if C != 0 else 0  # Tensão no capacitor

        # Equações diferenciais para o circuito RLC (ou RL, se C = 0)
        if C != 0:
            di_dt = (Vout - R * i - v_c) / L
            dv_c_dt = i / C
        else:  # Caso RL apenas
            di_dt = (Vout - R * i) / L
            dv_c_dt = 0  # Sem variação de tensão no capacitor

        di_dt = di_dt * (1 - self.model.Perdas_totais)
        return [di_dt, dv_c_dt]

    def Sim_VI(self):
      self.Calcula_Param_Modulacao(self.model.V_DC_Total)

      sol_V = solve_ivp(self.EDO_Filtro_RLC, (self.Tempo_Sim, self.Tempo_Sim + self.Passo), self.Cond_Iniciais_V, method='RK45', t_eval=[self.Tempo_Sim + self.Passo], rtol=1e-8)

      self.Cond_Iniciais_V = sol_V.y[:, -1]  # Atualiza o estado da Tensão
      q_solution = self.Cond_Iniciais_V[0]
      V_out = q_solution / self.Filtro_C

      sol_I = solve_ivp(lambda t, y: self.EDO_Corrente_carga(t, y, V_out), (self.Tempo_Sim, self.Tempo_Sim + self.Passo), self.Cond_Iniciais_I, method='RK45', t_eval=[self.Tempo_Sim + self.Passo], rtol=1e-8)

      self.Cond_Iniciais_I = sol_I.y[:, -1]  # Atualiza o estado da Corrente
      I_out = self.Cond_Iniciais_I[0]

      self.Tempo_Sim = sol_V.t[-1]  # Atualiza o tempo
      return V_out, I_out

    def Calcula_Param_Modulacao(self, V_In):
        # Parametros calculados
        self.Mf = 35                              # Modulação de Frequência
        self.Ma = self.Out_V_PP / V_In    # Modulação de Amplitude
        Amp_sine = 1                              # Amplitude da onda seno referencia
        self.Amp_Tri = Amp_sine / self.Ma         # Amplitude inicial da onda triangular carrier
        self.f_tri = self.Mf * self.Out_Freq      # Frequencia chaveamento
        self.T_sw = 1 / self.f_tri                # Tempo de chaveamento

    # ------------------------------ MPPT -----------------------------------------

    def MPPT(self, P_Atual, V_Atual):

      if (P_Atual >= self.P_PV_Anterior) and (P_Atual > 0.001):    # Se a potência aumentou
          if V_Atual >= self.V_PV_Anterior:                           # e a tensão aumentou
              V_MPPT_Novo = V_Atual + self.MPPT_learning_rate         # Aumenta a tensão
          if V_Atual < self.V_PV_Anterior:                            # e a tensão diminuiu
              V_MPPT_Novo = V_Atual - self.MPPT_learning_rate         # diminui a tensão

      elif (P_Atual < self.P_PV_Anterior) and (P_Atual > 0.001):  # Se a potência diminuiu
          if V_Atual >= self.V_PV_Anterior:                           # e a tensão aumentou
              V_MPPT_Novo = V_Atual - self.MPPT_learning_rate         # diminui a tensão
          if V_Atual < self.V_PV_Anterior:                            # e a tensão diminuiu
              V_MPPT_Novo = V_Atual + self.MPPT_learning_rate         # Aumenta a tensão

      else:                                                       # Se a potência for igual a 0
          V_MPPT_Novo = V_Atual                                      # Mantém a tensão

      self.P_PV_Anterior = P_Atual
      self.V_PV_Anterior = V_MPPT_Novo

      return V_MPPT_Novo

class Agente_Carga(mesa.Agent):
    def __init__(self, model):
        super().__init__(model)   # Pass the parameters to the parent class.
        self.Carga_R = 10
        self.Carga_L = 0.1
        self.Carga_C = 0.001

    def Mudanca_Carga(self):
        self.step_total = Iteracao_Sim  # Total de steps
        self.step_atual = self.model.steps  # Passo atual
        self.Step_mudanca = self.step_total / 2  # Dividido em 4 partes
        self.last_printed = False  # Variável para controlar quando já imprimiu

        if (self.step_atual % self.Step_mudanca == 0) and not self.last_printed:
            self.Carga_R = self.Carga_R*0.75
            self.Carga_L = self.Carga_L*0.75
            self.Carga_C = self.Carga_C*0.75
            self.last_printed = True  # Impede que imprima mais de uma vez no mesmo step
        else:
            # Caso o passo não corresponda, se não for o momento de imprimir, reseta
            if self.step_atual % self.Step_mudanca != 0:
                self.last_printed = False

# ------------------------------------ Modelos -------------------------------------
class Modelo_Fotovoltaico(mesa.Model):
    def __init__(self, Painel, n_painel, Inversor, n_inversor, Clima, seed=None):
        super().__init__(seed=seed)                                 #Inicia o modelo com uma semente
        self.num_agentes_totais = n_painel + n_inversor             # Define o número de agentes

        self.Clima = Agente_Clima.create_agents(model=self, n=1, Clima=Clima)                           # Cria o agente Clima
        self.Modulo_PV = Agente_Painel.create_agents(model=self, n=n_painel, Painel=Painel)             # Cria os agentes painéis
        self.Array_PV = self.Modulo_PV.groupby("Array", result_type="list")                             # Agrupa os paineis por array
        self.Inversor = Agente_Inversor.create_agents(model=self, n=n_inversor, Inversor=Inversor)      # Cria os agentes inversores
        self.Carga = Agente_Carga.create_agents(model=self, n=1)                                        # Cria o agente Carga

        self.Valores_Painel_DC = mesa.DataCollector( agent_reporters={"Corrente_DC": "I_calc"}, model_reporters={"Pot_DC_Total": lambda model: model.Pot_DC_Total, "Tensao_DC_Total": lambda model: model.V_DC_Total} )
        self.Valores_Inversor_AC = mesa.DataCollector( agent_reporters={"Tensao_AC": "V_out", "Corrente_AC": "I_out"} )

        self.Perda_Cabo = 0.00
        self.Perda_Mismatch = 0.00

    def step(self):
        self.Clima.do("Simula_Clima_Transiente")   # Simula o clima transiente
        # self.Clima.do("Simula_Clima_Estatico")   # Simula o clima Estático
        self.Modulo_PV.do("Simula_PV")   # Simula o Painel

        self.Pot_DC_Total = 0                               # Define a variavel de armazenamento da Potência total DC do sistema
        self.V_DC_Total = 0                               # Define a variavel de armazenamento da Potência total DC do sistema
        for painel_group in self.Array_PV.groups.values():  # Itera sobre os grupos
            for painel in painel_group:  # Itera sobre os agentes (painéis) em cada grupo
                self.Pot_DC_Total += painel.Pot_calc
                self.V_DC_Total += painel.V_MPPT

        self.Valores_Painel_DC.collect(self)

        self.Perdas_totais = self.Modulo_PV[0].Perda_sombreamento + self.Inversor[0].Perda_inversor + self.Perda_Cabo + self.Perda_Mismatch # --------------- Considerar perda relacionado ao angulo do painel - Total_perdas = 25%

        self.Inversor.do("Sim_Inversor")   # Simula o Painel
        # self.Carga.do("Mudanca_Carga")   # Simula o Painel

        self.Valores_Inversor_AC.collect(self)
