"""
Módulo de Análise Financeira com Tarifação Horária
Integra perfil de carga variável e tarifas ANEEL (Azul/Verde)
"""

import numpy as np
import numpy_financial as npf
import matplotlib.pyplot as plt
from microrrede_powerflow import MicrorrredePowerFlow
from tarifas_aneel import TarifasANEEL
from perfil_carga import PerfilCarga


class AnaliseFinanceiraHoraria:
    """
    Análise financeira considerando:
    - Perfil de carga horária variável
    - Tarifas diferenciadas ponta/fora ponta
    - Modalidades Azul e Verde
    """
    
    def __init__(self, 
                 distribuidora='EQUATORIAL GO',
                 modalidade='verde',
                 vida_util=20, 
                 taxa_desconto=0.08,
                 perfil_carga_csv='perfil_carga_horaria.csv'):
        """
        Inicializa análise financeira com tarifação horária
        
        Parâmetros:
        -----------
        distribuidora : str
            Código da distribuidora ANEEL
        modalidade : str
            'azul' ou 'verde'
        vida_util : int
            Vida útil do projeto em anos
        taxa_desconto : float
            Taxa de desconto para VPL
        perfil_carga_csv : str
            Caminho para arquivo CSV com perfil de carga
        """
        self.distribuidora = distribuidora
        self.modalidade = modalidade.lower()
        self.vida_util = vida_util
        self.taxa_desconto = taxa_desconto
        
        # Carregar tarifas
        self.tarifas = TarifasANEEL(distribuidora)
        
        # Carregar perfil de carga
        self.perfil_carga = PerfilCarga(perfil_carga_csv)
        
        # Custos do sistema
        self.custo_pv_kw = 3200
        self.custo_bess_kwh = 2200
        self.custo_diesel_kw = 1200
        
        # Parâmetros operacionais
        self.custo_om_anual_percent = 0.02
        self.custo_diesel_litro = 6.50
        self.consumo_diesel_l_kwh = 0.25
        
        # Degradação
        self.degradacao_pv_anual = 0.005
        self.escalada_tarifa = 0.04
        
        # Inicializar microrrede com perfil de carga variável
        self.microrrede = MicrorrredePowerFlow(
            perfil_carga_csv=perfil_carga_csv,
            usar_perfil_variavel=True
        )
        
    def calcular_custos_sem_microrrede_anual(self):
        """
        Calcula custo anual SEM microrrede usando perfil de carga e tarifas reais
        """
        if self.perfil_carga is None:
            raise ValueError("Perfil de carga não carregado!")
        
        # Energia e demanda por período (ponta/fora ponta)
        energia_ponta_kwh = 0
        energia_fora_ponta_kwh = 0
        demanda_ponta_kw = 0
        demanda_fora_ponta_kw = 0
        
        # Processar dias úteis (260 dias/ano)
        for hora in range(24):
            demanda_kw = self.perfil_carga.get_demanda(hora, dia_semana=0)
            
            if TarifasANEEL.is_horario_ponta(hora, dia_semana=0):
                energia_ponta_kwh += demanda_kw * 260  # 260 dias úteis
                demanda_ponta_kw = max(demanda_ponta_kw, demanda_kw)
            else:
                energia_fora_ponta_kwh += demanda_kw * 260
                demanda_fora_ponta_kw = max(demanda_fora_ponta_kw, demanda_kw)
        
        # Processar fins de semana (105 dias/ano)
        for hora in range(24):
            demanda_kw = self.perfil_carga.get_demanda(hora, dia_semana=6)
            # Fim de semana é sempre fora ponta
            energia_fora_ponta_kwh += demanda_kw * 105
            demanda_fora_ponta_kw = max(demanda_fora_ponta_kw, demanda_kw)
        
        # Calcular custo conforme modalidade
        if self.modalidade == 'azul':
            custo = self.tarifas.calcular_custo_energia_azul(
                energia_ponta_kwh, energia_fora_ponta_kwh,
                demanda_ponta_kw * 1.1, demanda_fora_ponta_kw * 1.1
            )
        else:  # verde
            demanda_max = max(demanda_ponta_kw, demanda_fora_ponta_kw) * 1.1
            custo = self.tarifas.calcular_custo_energia_verde(
                energia_ponta_kwh, energia_fora_ponta_kwh,
                demanda_max
            )
        
        return custo
    
    def calcular_custos_com_microrrede_anual(self):
        """
        Calcula custo anual COM microrrede considerando tarifas horárias
        """
        # Inicializar contadores
        energia_comprada_ponta = 0
        energia_comprada_fp = 0
        energia_vendida_ponta = 0
        energia_vendida_fp = 0
        energia_diesel_total = 0
        
        demanda_ponta_max = 0
        demanda_fp_max = 0
        
        # Simular ano completo
        # 260 dias úteis
        for _ in range(260):
            # Resetar e simular
            self.microrrede.resultados = {k: [] for k in self.microrrede.resultados.keys()}
            self.microrrede.simular_24h(dia_semana=0)
            
            # Processar resultados
            for hora in range(24):
                p_dist_kw = self.microrrede.resultados['p_distribuidora_mw'][hora] * 1000
                p_diesel_kw = self.microrrede.resultados['p_diesel_mw'][hora] * 1000
                
                # Classificar por horário
                if TarifasANEEL.is_horario_ponta(hora, dia_semana=0):
                    if p_dist_kw > 0:
                        energia_comprada_ponta += p_dist_kw
                        demanda_ponta_max = max(demanda_ponta_max, p_dist_kw)
                    else:
                        energia_vendida_ponta += abs(p_dist_kw)
                else:
                    if p_dist_kw > 0:
                        energia_comprada_fp += p_dist_kw
                        demanda_fp_max = max(demanda_fp_max, p_dist_kw)
                    else:
                        energia_vendida_fp += abs(p_dist_kw)
                
                energia_diesel_total += p_diesel_kw
        
        # 105 dias de fim de semana
        for _ in range(105):
            self.microrrede.resultados = {k: [] for k in self.microrrede.resultados.keys()}
            self.microrrede.simular_24h(dia_semana=6)
            
            for hora in range(24):
                p_dist_kw = self.microrrede.resultados['p_distribuidora_mw'][hora] * 1000
                p_diesel_kw = self.microrrede.resultados['p_diesel_mw'][hora] * 1000
                
                # Fim de semana é sempre fora ponta
                if p_dist_kw > 0:
                    energia_comprada_fp += p_dist_kw
                    demanda_fp_max = max(demanda_fp_max, p_dist_kw)
                else:
                    energia_vendida_fp += abs(p_dist_kw)
                
                energia_diesel_total += p_diesel_kw
        
        # Calcular custos conforme modalidade
        if self.modalidade == 'azul':
            custo_energia = self.tarifas.calcular_custo_energia_azul(
                energia_comprada_ponta, energia_comprada_fp,
                demanda_ponta_max * 1.1, demanda_fp_max * 1.1
            )
        else:
            demanda_max = max(demanda_ponta_max, demanda_fp_max) * 1.1
            custo_energia = self.tarifas.calcular_custo_energia_verde(
                energia_comprada_ponta, energia_comprada_fp,
                demanda_max
            )
        
        # Receita com venda usando tarifas SCEE reais
        scee = self.tarifas.dados_tarifa.get('scee', {})
        mod_key = 'verde' if self.modalidade == 'verde' else 'azul'
        scee_mod = scee.get(mod_key, {})
        
        # Usar tarifas SCEE (compensação) se disponíveis
        if scee_mod:
            tarifa_scee_ponta = scee_mod.get('te_ponta', 0) + scee_mod.get('tusd_ponta', 0)
            tarifa_scee_fp = scee_mod.get('te_fora_ponta', 0) + scee_mod.get('tusd_fora_ponta', 0)
        else:
            # Fallback: 70% da tarifa TE
            tarifas_dict = self.tarifas.get_tarifas_verde() if self.modalidade == 'verde' else self.tarifas.get_tarifas_azul()
            tarifa_scee_ponta = tarifas_dict.get('te_ponta', 0) * 0.7
            tarifa_scee_fp = tarifas_dict.get('te_fora_ponta', 0) * 0.7
        
        receita_venda_ponta = energia_vendida_ponta * tarifa_scee_ponta
        receita_venda_fp = energia_vendida_fp * tarifa_scee_fp
        
        # Custo diesel
        custo_diesel = energia_diesel_total * self.consumo_diesel_l_kwh * self.custo_diesel_litro
        
        # Custo total líquido
        custo_total = custo_energia['custo_total'] + custo_diesel - receita_venda_ponta - receita_venda_fp
        
        return {
            **custo_energia,
            'energia_diesel_kwh': energia_diesel_total,
            'custo_diesel': custo_diesel,
            'receita_venda': receita_venda_ponta + receita_venda_fp,
            'custo_total_liquido': custo_total
        }
    
    def calcular_capex(self):
        """Calcula CAPEX do sistema"""
        if self.microrrede is None:
            raise ValueError("Microrrede não inicializada!")
        
        pv_kw = self.microrrede.pv_potencia_nominal_kw
        bess_kwh = 200 * 4  # 200 kW * 4h = 800 kWh (exemplo)
        diesel_kw = 300
        
        capex_pv = pv_kw * self.custo_pv_kw
        capex_bess = bess_kwh * self.custo_bess_kwh
        capex_diesel = diesel_kw * self.custo_diesel_kw
        capex_total = capex_pv + capex_bess + capex_diesel
        
        return {
            'capex_pv': capex_pv,
            'capex_bess': capex_bess,
            'capex_diesel': capex_diesel,
            'capex_total': capex_total
        }
    
    def calcular_vpl(self):
        """Calcula VPL do projeto"""
        custos_base = self.calcular_custos_sem_microrrede_anual()
        custos_micro = self.calcular_custos_com_microrrede_anual()
        capex = self.calcular_capex()
        
        # Fluxo de caixa
        economia_anual = custos_base['custo_total'] - custos_micro['custo_total_liquido']
        custo_om_anual = capex['capex_total'] * self.custo_om_anual_percent
        
        fluxos = [-capex['capex_total']]  # Ano 0
        
        for ano in range(1, self.vida_util + 1):
            # Degradação PV
            fator_degradacao = (1 - self.degradacao_pv_anual) ** ano
            
            # Escalada tarifária
            fator_escalada = (1 + self.escalada_tarifa) ** ano
            
            fluxo_ano = economia_anual * fator_degradacao * fator_escalada - custo_om_anual
            fluxos.append(fluxo_ano)
        
        vpl = npf.npv(self.taxa_desconto, fluxos)
        
        return vpl, fluxos
    
    def calcular_tir(self):
        """Calcula TIR do projeto"""
        _, fluxos = self.calcular_vpl()
        return npf.irr(fluxos)
    
    def gerar_relatorio_completo(self):
        """Gera relatório completo da análise"""
        print("\n" + "=" * 90)
        print(" " * 25 + "ANÁLISE FINANCEIRA COM TARIFAÇÃO HORÁRIA")
        print("=" * 90)
        
        info_dist = self.tarifas.get_info_distribuidora()
        print(f"\nDistribuidora: {info_dist['nome']}")
        print(f"Modalidade tarifária: {self.modalidade.upper()}")
        print(f"Vigência das tarifas: {info_dist['vigencia']}")
        
        print("\n" + "-" * 90)
        print("CENÁRIO SEM MICRORREDE:")
        print("-" * 90)
        custos_base = self.calcular_custos_sem_microrrede_anual()
        print(f"  Custo total anual: R$ {custos_base['custo_total']:,.2f}")
        print(f"  Energia total: {custos_base['energia_total_kwh']:,.0f} kWh")
        print(f"  Custo médio: R$ {custos_base['custo_medio_kwh']:.3f}/kWh")
        
        print("\n" + "-" * 90)
        print("CENÁRIO COM MICRORREDE:")
        print("-" * 90)
        custos_micro = self.calcular_custos_com_microrrede_anual()
        print(f"  Custo total líquido: R$ {custos_micro['custo_total_liquido']:,.2f}")
        print(f"  Energia diesel: {custos_micro['energia_diesel_kwh']:,.0f} kWh")
        
        print("\n" + "-" * 90)
        print("INVESTIMENTO:")
        print("-" * 90)
        capex = self.calcular_capex()
        print(f"  CAPEX Total: R$ {capex['capex_total']:,.2f}")
        
        print("\n" + "-" * 90)
        print("INDICADORES ECONÔMICOS:")
        print("-" * 90)
        vpl, _ = self.calcular_vpl()
        tir = self.calcular_tir()
        economia = custos_base['custo_total'] - custos_micro['custo_total_liquido']
        
        print(f"  VPL (20 anos): R$ {vpl:,.2f}")
        print(f"  TIR: {tir * 100:.2f}%")
        print(f"  Economia anual: R$ {economia:,.2f}")
        
        print("=" * 90)


def exemplo_uso():
    """Exemplo de uso da análise financeira horária"""
    
    # Criar análise
    analise = AnaliseFinanceiraHoraria(
        distribuidora='EQUATORIAL GO',
        modalidade='verde',
        vida_util=20,
        taxa_desconto=0.08
    )
    
    # Carregar perfil de carga
    analise.perfil_carga = PerfilCarga('perfil_carga_horaria.csv')
    
    # Criar e simular microrrede
    analise.microrrede = MicrorrredePowerFlow(
        perfil_carga_csv='perfil_carga_horaria.csv',
        usar_perfil_variavel=True
    )
    
    # Gerar relatório
    analise.gerar_relatorio_completo()


if __name__ == "__main__":
    exemplo_uso()
