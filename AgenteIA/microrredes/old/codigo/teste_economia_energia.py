"""
Teste de validação do cálculo de economia de energia
Simula redução de consumo da rede por hora e apresenta resultados gráficos
"""

import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
from tarifas_aneel import TarifasANEEL
from perfil_carga import PerfilCarga


class TesteEconomiaEnergia:
    """
    Testa cálculo de economia de energia com redução horária do consumo da rede
    """
    
    def __init__(self, distribuidora='EQUATORIAL GO', modalidade='azul'):
        """
        Inicializa teste de economia
        
        Parâmetros:
        -----------
        distribuidora : str
            Nome da distribuidora
        modalidade : str
            'azul' ou 'verde'
        """
        print("=" * 90)
        print(" " * 20 + f"TESTE DE ECONOMIA DE ENERGIA - {modalidade.upper()}")
        print("=" * 90)
        
        # Carregar tarifas
        print(f"\n📊 Carregando tarifas da {distribuidora}...")
        self.tarifas_aneel = TarifasANEEL(distribuidora, usar_api=True)
        self.modalidade = modalidade
        
        if modalidade == 'azul':
            self.tarifas = self.tarifas_aneel.get_tarifas_azul()
        else:
            self.tarifas = self.tarifas_aneel.get_tarifas_verde()
        
        # Carregar perfil de carga
        print("\n📈 Carregando perfil de carga...")
        self.perfil = PerfilCarga('perfil_carga_horaria.csv')
        
        print("\n✅ Inicialização completa!")
    
    def calcular_tarifa_horaria(self, hora, dia_semana=0):
        """
        Calcula tarifa total (TUSD + TE) para uma hora específica
        
        Parâmetros:
        -----------
        hora : int
            Hora do dia (0-23)
        dia_semana : int
            0-4 = dia útil, 5-6 = fim de semana
            
        Retorna:
        --------
        float : Tarifa em R$/kWh
        """
        # Verificar se é horário de ponta
        is_ponta = TarifasANEEL.is_horario_ponta(hora, dia_semana)
        
        if self.modalidade == 'azul':
            if is_ponta:
                tarifa = self.tarifas['tusd_ponta_consumo'] + self.tarifas['te_ponta']
            else:
                tarifa = self.tarifas['tusd_fora_ponta_consumo'] + self.tarifas['te_fora_ponta']
        else:  # verde
            if is_ponta:
                tarifa = self.tarifas['tusd_ponta_consumo'] + self.tarifas['te_ponta']
            else:
                tarifa = self.tarifas['tusd_fora_ponta_consumo'] + self.tarifas['te_fora_ponta']
        
        return tarifa
    
    def simular_dia_util(self, reducao_energia_percentual=50):
        """
        Simula economia para um dia útil completo (24h)
        
        Parâmetros:
        -----------
        reducao_energia_percentual : float
            Percentual de redução do consumo da rede (0-100%)
            Representa energia gerada pela microrrede (PV + BESS + Diesel)
            
        Retorna:
        --------
        dict : Resultados da simulação
        """
        horas = np.arange(24)
        resultados = {
            'hora': [],
            'demanda_original_kw': [],
            'energia_reduzida_kwh': [],
            'energia_rede_kwh': [],
            'tarifa_kwh': [],
            'custo_original_hora': [],
            'custo_com_reducao_hora': [],
            'economia_hora': [],
            'is_ponta': []
        }
        
        fator_reducao = reducao_energia_percentual / 100
        
        for hora in horas:
            # Demanda original da carga
            demanda_kw = self.perfil.get_demanda(hora, dia_semana=0)  # dia útil
            energia_original_kwh = demanda_kw  # 1 hora
            
            # Energia reduzida pela microrrede
            energia_reduzida_kwh = energia_original_kwh * fator_reducao
            energia_rede_kwh = energia_original_kwh - energia_reduzida_kwh
            
            # Tarifa horária
            tarifa = self.calcular_tarifa_horaria(hora, dia_semana=0)
            is_ponta = TarifasANEEL.is_horario_ponta(hora, 0)
            
            # Custos
            custo_original = energia_original_kwh * tarifa
            custo_com_reducao = energia_rede_kwh * tarifa
            economia = custo_original - custo_com_reducao
            
            # Armazenar resultados
            resultados['hora'].append(hora)
            resultados['demanda_original_kw'].append(demanda_kw)
            resultados['energia_reduzida_kwh'].append(energia_reduzida_kwh)
            resultados['energia_rede_kwh'].append(energia_rede_kwh)
            resultados['tarifa_kwh'].append(tarifa)
            resultados['custo_original_hora'].append(custo_original)
            resultados['custo_com_reducao_hora'].append(custo_com_reducao)
            resultados['economia_hora'].append(economia)
            resultados['is_ponta'].append(is_ponta)
        
        return resultados
    
    def simular_mes(self, reducao_energia_percentual=50):
        """
        Simula economia para um mês completo (30 dias)
        
        Parâmetros:
        -----------
        reducao_energia_percentual : float
            Percentual de redução do consumo da rede
            
        Retorna:
        --------
        dict : Resultados mensais
        """
        # Considerar 22 dias úteis e 8 fins de semana
        dias_uteis = 22
        fins_semana = 8
        
        # Simular dia útil
        resultado_util = self.simular_dia_util(reducao_energia_percentual)
        
        # Simular fim de semana (simplificado - mesma lógica)
        resultado_fds = self._simular_fim_semana(reducao_energia_percentual)
        
        # Calcular totais mensais
        energia_total_original = (sum(resultado_util['demanda_original_kw']) * dias_uteis + 
                                 sum(resultado_fds['demanda_original_kw']) * fins_semana)
        
        energia_total_reduzida = (sum(resultado_util['energia_reduzida_kwh']) * dias_uteis + 
                                 sum(resultado_fds['energia_reduzida_kwh']) * fins_semana)
        
        custo_total_original = (sum(resultado_util['custo_original_hora']) * dias_uteis + 
                               sum(resultado_fds['custo_original_hora']) * fins_semana)
        
        custo_total_com_reducao = (sum(resultado_util['custo_com_reducao_hora']) * dias_uteis + 
                                  sum(resultado_fds['custo_com_reducao_hora']) * fins_semana)
        
        economia_total = custo_total_original - custo_total_com_reducao
        economia_percentual = (economia_total / custo_total_original) * 100 if custo_total_original > 0 else 0
        
        return {
            'energia_original_kwh': energia_total_original,
            'energia_reduzida_kwh': energia_total_reduzida,
            'custo_original': custo_total_original,
            'custo_com_reducao': custo_total_com_reducao,
            'economia_mensal': economia_total,
            'economia_percentual': economia_percentual,
            'resultado_dia_util': resultado_util,
            'resultado_fim_semana': resultado_fds
        }
    
    def _simular_fim_semana(self, reducao_energia_percentual=50):
        """Simula fim de semana (lógica similar ao dia útil)"""
        horas = np.arange(24)
        resultados = {
            'hora': [],
            'demanda_original_kw': [],
            'energia_reduzida_kwh': [],
            'energia_rede_kwh': [],
            'tarifa_kwh': [],
            'custo_original_hora': [],
            'custo_com_reducao_hora': [],
            'economia_hora': [],
            'is_ponta': []
        }
        
        fator_reducao = reducao_energia_percentual / 100
        
        for hora in horas:
            demanda_kw = self.perfil.get_demanda(hora, dia_semana=6)  # domingo
            energia_original_kwh = demanda_kw
            energia_reduzida_kwh = energia_original_kwh * fator_reducao
            energia_rede_kwh = energia_original_kwh - energia_reduzida_kwh
            
            tarifa = self.calcular_tarifa_horaria(hora, dia_semana=6)
            is_ponta = TarifasANEEL.is_horario_ponta(hora, 6)
            
            custo_original = energia_original_kwh * tarifa
            custo_com_reducao = energia_rede_kwh * tarifa
            economia = custo_original - custo_com_reducao
            
            resultados['hora'].append(hora)
            resultados['demanda_original_kw'].append(demanda_kw)
            resultados['energia_reduzida_kwh'].append(energia_reduzida_kwh)
            resultados['energia_rede_kwh'].append(energia_rede_kwh)
            resultados['tarifa_kwh'].append(tarifa)
            resultados['custo_original_hora'].append(custo_original)
            resultados['custo_com_reducao_hora'].append(custo_com_reducao)
            resultados['economia_hora'].append(economia)
            resultados['is_ponta'].append(is_ponta)
        
        return resultados
    
    def gerar_graficos(self, resultado_dia, titulo="Dia Útil"):
        """
        Gera gráficos dos resultados
        
        Parâmetros:
        -----------
        resultado_dia : dict
            Resultados da simulação diária
        titulo : str
            Título do gráfico
        """
        fig, axes = plt.subplots(2, 2, figsize=(16, 10))
        fig.suptitle(f'Análise de Economia de Energia - {titulo} - Modalidade {self.modalidade.upper()}', 
                     fontsize=16, fontweight='bold')
        
        horas = resultado_dia['hora']
        
        # Gráfico 1: Demanda e Energia Reduzida
        ax1 = axes[0, 0]
        ax1.bar(horas, resultado_dia['demanda_original_kw'], alpha=0.5, label='Demanda Original', color='gray')
        ax1.bar(horas, resultado_dia['energia_reduzida_kwh'], alpha=0.8, label='Energia Reduzida (Microrrede)', color='green')
        ax1.bar(horas, resultado_dia['energia_rede_kwh'], alpha=0.8, label='Energia da Rede', color='orange')
        
        # Destacar horário de ponta
        for i, is_ponta in enumerate(resultado_dia['is_ponta']):
            if is_ponta:
                ax1.axvspan(i-0.5, i+0.5, alpha=0.1, color='red')
        
        ax1.set_xlabel('Hora do Dia', fontsize=12)
        ax1.set_ylabel('Energia (kWh)', fontsize=12)
        ax1.set_title('Perfil de Consumo de Energia', fontsize=14, fontweight='bold')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        ax1.set_xticks(range(0, 24, 2))
        
        # Gráfico 2: Tarifa Horária
        ax2 = axes[0, 1]
        cores_tarifa = ['red' if p else 'blue' for p in resultado_dia['is_ponta']]
        ax2.bar(horas, resultado_dia['tarifa_kwh'], color=cores_tarifa, alpha=0.7)
        ax2.set_xlabel('Hora do Dia', fontsize=12)
        ax2.set_ylabel('Tarifa (R$/kWh)', fontsize=12)
        ax2.set_title('Tarifa de Energia por Hora', fontsize=14, fontweight='bold')
        ax2.grid(True, alpha=0.3)
        ax2.set_xticks(range(0, 24, 2))
        
        # Adicionar legenda para cores
        from matplotlib.patches import Patch
        legend_elements = [Patch(facecolor='red', alpha=0.7, label='Ponta (18h-21h)'),
                          Patch(facecolor='blue', alpha=0.7, label='Fora Ponta')]
        ax2.legend(handles=legend_elements)
        
        # Gráfico 3: Custos por Hora
        ax3 = axes[1, 0]
        width = 0.35
        x = np.arange(len(horas))
        ax3.bar(x - width/2, resultado_dia['custo_original_hora'], width, 
                label='Custo Original', alpha=0.7, color='red')
        ax3.bar(x + width/2, resultado_dia['custo_com_reducao_hora'], width, 
                label='Custo com Microrrede', alpha=0.7, color='green')
        
        ax3.set_xlabel('Hora do Dia', fontsize=12)
        ax3.set_ylabel('Custo (R$)', fontsize=12)
        ax3.set_title('Comparação de Custos por Hora', fontsize=14, fontweight='bold')
        ax3.legend()
        ax3.grid(True, alpha=0.3)
        ax3.set_xticks(range(0, 24, 2))
        
        # Gráfico 4: Economia Acumulada
        ax4 = axes[1, 1]
        economia_acumulada = np.cumsum(resultado_dia['economia_hora'])
        ax4.plot(horas, economia_acumulada, marker='o', linewidth=2, color='darkgreen', markersize=5)
        ax4.fill_between(horas, 0, economia_acumulada, alpha=0.3, color='green')
        
        ax4.set_xlabel('Hora do Dia', fontsize=12)
        ax4.set_ylabel('Economia Acumulada (R$)', fontsize=12)
        ax4.set_title('Economia Acumulada ao Longo do Dia', fontsize=14, fontweight='bold')
        ax4.grid(True, alpha=0.3)
        ax4.set_xticks(range(0, 24, 2))
        
        # Adicionar texto com economia total
        economia_total = sum(resultado_dia['economia_hora'])
        ax4.text(0.5, 0.95, f'Economia Total: R$ {economia_total:.2f}', 
                transform=ax4.transAxes, fontsize=12, fontweight='bold',
                verticalalignment='top', bbox=dict(boxstyle='round', facecolor='lightgreen', alpha=0.8))
        
        plt.tight_layout()
        return fig
    
    def gerar_relatorio(self, reducao_percentual=50):
        """
        Gera relatório completo com gráficos e estatísticas
        
        Parâmetros:
        -----------
        reducao_percentual : float
            Percentual de redução de energia da rede
        """
        print("\n" + "=" * 90)
        print(f" SIMULAÇÃO: {reducao_percentual}% de redução do consumo da rede")
        print("=" * 90)
        
        # Simular mês
        resultado_mes = self.simular_mes(reducao_percentual)
        
        # Exibir resultados mensais
        print(f"\n📊 RESULTADOS MENSAIS (22 dias úteis + 8 fins de semana):")
        print("-" * 90)
        print(f"  Energia Original Total:       {resultado_mes['energia_original_kwh']:>12,.0f} kWh")
        print(f"  Energia Reduzida (Microrrede): {resultado_mes['energia_reduzida_kwh']:>12,.0f} kWh ({reducao_percentual}%)")
        print(f"  Custo Original:                R$ {resultado_mes['custo_original']:>12,.2f}")
        print(f"  Custo com Microrrede:          R$ {resultado_mes['custo_com_reducao']:>12,.2f}")
        print(f"  Economia Mensal:               R$ {resultado_mes['economia_mensal']:>12,.2f}")
        print(f"  Economia Percentual:           {resultado_mes['economia_percentual']:>12.2f}%")
        
        # Projeção anual
        economia_anual = resultado_mes['economia_mensal'] * 12
        print(f"\n💰 PROJEÇÃO ANUAL:")
        print("-" * 90)
        print(f"  Economia Anual Estimada:       R$ {economia_anual:>12,.2f}")
        print(f"  Custo Anual sem Microrrede:    R$ {resultado_mes['custo_original'] * 12:>12,.2f}")
        print(f"  Custo Anual com Microrrede:    R$ {resultado_mes['custo_com_reducao'] * 12:>12,.2f}")
        
        # Gerar gráficos
        print("\n📈 Gerando gráficos...")
        fig1 = self.gerar_graficos(resultado_mes['resultado_dia_util'], "Dia Útil")
        fig2 = self.gerar_graficos(resultado_mes['resultado_fim_semana'], "Fim de Semana")
        
        plt.show()
        
        return resultado_mes


def main():
    """Função principal de teste"""
    
    # Testar com modalidade AZUL
    print("\n🔵 TESTE 1: MODALIDADE AZUL")
    teste_azul = TesteEconomiaEnergia(distribuidora='EQUATORIAL GO', modalidade='azul')
    resultado_azul = teste_azul.gerar_relatorio(reducao_percentual=50)
    
    print("\n\n" + "=" * 90)
    input("Pressione ENTER para continuar com a Modalidade VERDE...")
    
    # Testar com modalidade VERDE
    print("\n\n🟢 TESTE 2: MODALIDADE VERDE")
    teste_verde = TesteEconomiaEnergia(distribuidora='EQUATORIAL GO', modalidade='verde')
    resultado_verde = teste_verde.gerar_relatorio(reducao_percentual=50)
    
    # Comparação final
    print("\n\n" + "=" * 90)
    print(" " * 25 + "COMPARAÇÃO ENTRE MODALIDADES")
    print("=" * 90)
    print(f"\nECONOMIA MENSAL:")
    print(f"  Azul:   R$ {resultado_azul['economia_mensal']:>12,.2f} ({resultado_azul['economia_percentual']:.2f}%)")
    print(f"  Verde:  R$ {resultado_verde['economia_mensal']:>12,.2f} ({resultado_verde['economia_percentual']:.2f}%)")
    
    print(f"\nECONOMIA ANUAL ESTIMADA:")
    print(f"  Azul:   R$ {resultado_azul['economia_mensal'] * 12:>12,.2f}")
    print(f"  Verde:  R$ {resultado_verde['economia_mensal'] * 12:>12,.2f}")
    
    diferenca = abs(resultado_azul['economia_mensal'] - resultado_verde['economia_mensal'])
    melhor = "AZUL" if resultado_azul['economia_mensal'] > resultado_verde['economia_mensal'] else "VERDE"
    
    print(f"\n✅ MELHOR OPÇÃO: {melhor}")
    print(f"   Diferença: R$ {diferenca:,.2f}/mês ou R$ {diferenca*12:,.2f}/ano")
    print("=" * 90)


if __name__ == "__main__":
    main()
