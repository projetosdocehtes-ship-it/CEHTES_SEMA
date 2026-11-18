"""
Comparador de Cenários - Caso IFG
Análise comparativa entre diferentes configurações de microrrede
"""

import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
from caso_ifg import CasoIFG
from tarifas_aneel import TarifasANEEL
from perfil_carga import PerfilCarga
from fotovoltaico import Painel_Fotovoltaico


class ComparadorCenariosIFG:
    """
    Compara diferentes cenários de configuração da microrrede IFG
    """
    
    def __init__(self, distribuidora='EQUATORIAL GO', modalidade='verde'):
        """
        Inicializa o comparador de cenários
        
        Parâmetros:
        -----------
        distribuidora : str
            Nome da distribuidora
        modalidade : str
            'azul' ou 'verde'
        """
        self.distribuidora = distribuidora
        self.modalidade = modalidade
        
        # Carregar tarifas
        self.tarifas_aneel = TarifasANEEL(distribuidora, usar_api=True)
        if modalidade == 'azul':
            self.tarifas = self.tarifas_aneel.get_tarifas_azul()
        else:
            self.tarifas = self.tarifas_aneel.get_tarifas_verde()
        
        # Carregar perfil de carga
        self.perfil = PerfilCarga('perfil_carga_ifg.csv')
        
        # Configurar painel PV
        self.pv_painel = Painel_Fotovoltaico(
            fabricante_painel="Canadian Solar",
            modelo_painel="CS6.2-66TB-610",
            Pmp=610,
            Isc=15.97,
            Voc=48,
            Imp=14.96,
            Vmp=40.8,
            Uisc=0.05,
            Uvoc=-0.25,
            Upmp=-0.29,
            material_painel="Silicio",
            eficiencia=22.6
        )
        
        # Resultados
        self.cenarios = {}
        
    def calcular_demanda_contratada_otima(self):
        """
        Calcula demanda contratada ótima baseada no perfil de carga
        Considera ponta e fora ponta separadamente
        """
        # Simular mês completo
        demanda_ponta_max = 0
        demanda_fora_ponta_max = 0
        
        for dia in range(30):
            dia_semana_num = dia % 7  # 0-6
            
            for hora in range(24):
                demanda_kw = self.perfil.get_demanda(hora, dia_semana_num)
                is_ponta = TarifasANEEL.is_horario_ponta(hora, dia_semana_num)
                
                if is_ponta:
                    demanda_ponta_max = max(demanda_ponta_max, demanda_kw)
                else:
                    demanda_fora_ponta_max = max(demanda_fora_ponta_max, demanda_kw)
        
        return {
            'ponta': demanda_ponta_max,
            'fora_ponta': demanda_fora_ponta_max
        }
    
    def simular_cenario_base(self):
        """
        Cenário Base: PV 254 kWp (sistema existente no IFG) sem BESS
        """
        print("\n" + "="*100)
        print(" "*25 + "CENÁRIO BASE - PV 254 kWp (SISTEMA EXISTENTE)")
        print("="*100)
        
        caso = CasoIFG(distribuidora=self.distribuidora, modalidade=self.modalidade)
        caso.pv_potencia_kwp = 254
        caso.bess_capacidade_kwh = 0
        caso.usar_diesel = False
        caso._configurar_pv()
        
        resultado_sim = caso.simular_mes()
        
        resultado = {
            'nome': 'Base: PV 254 kWp',
            'pv_kwp': 254,
            'bess_kwh': 0,
            'energia_total_kwh': resultado_sim['energia_demanda_kwh'],
            'energia_ponta_kwh': resultado_sim.get('energia_ponta_kwh', 0),
            'energia_fora_ponta_kwh': resultado_sim.get('energia_fora_ponta_kwh', 0),
            'energia_reservado_kwh': resultado_sim.get('energia_reservado_kwh', 0),
            'energia_comprada_kwh': resultado_sim['energia_comprada_kwh'],
            'energia_vendida_kwh': resultado_sim['energia_vendida_kwh'],
            'geracao_pv_kwh': resultado_sim['energia_pv_kwh'],
            'demanda_ponta_max_kw': resultado_sim.get('demanda_ponta_max', 0),
            'demanda_fora_ponta_max_kw': resultado_sim.get('demanda_fora_ponta_max', 0),
            'custo_mensal': resultado_sim['custo_mensal'],
            'custo_anual': resultado_sim['custo_mensal'] * 12,
            'investimento_inicial': 0,  # Já existe
            'investimento_adicional': 0,  # Já existe
            'economia_vs_base': 0
        }
        
        self._imprimir_resultado(resultado)
        self.cenarios['base'] = resultado
        return resultado
    
    def simular_cenario_pv_254_bess_500(self):
        """
        Cenário 1: PV 254 kWp + BESS 500 kWh
        Adicionar BESS ao sistema existente
        """
        print("\n" + "="*100)
        print(" "*25 + "CENÁRIO 1 - PV 254 kWp + BESS 500 kWh")
        print("="*100)
        
        caso = CasoIFG(distribuidora=self.distribuidora, modalidade=self.modalidade)
        caso.pv_potencia_kwp = 254
        caso.bess_capacidade_kwh = 500
        caso.bess_potencia_kw = 200
        caso.usar_diesel = False
        caso._configurar_pv()
        
        resultado_sim = caso.simular_mes()
        
        resultado = {
            'nome': 'PV 254 kWp + BESS 500 kWh',
            'pv_kwp': 254,
            'bess_kwh': 500,
            'energia_total_kwh': resultado_sim['energia_demanda_kwh'],
            'energia_ponta_kwh': resultado_sim.get('energia_ponta_kwh', 0),
            'energia_fora_ponta_kwh': resultado_sim.get('energia_fora_ponta_kwh', 0),
            'energia_reservado_kwh': resultado_sim.get('energia_reservado_kwh', 0),
            'energia_comprada_kwh': resultado_sim['energia_comprada_kwh'],
            'energia_vendida_kwh': resultado_sim['energia_vendida_kwh'],
            'geracao_pv_kwh': resultado_sim['energia_pv_kwh'],
            'demanda_ponta_max_kw': resultado_sim.get('demanda_ponta_max', 0),
            'demanda_fora_ponta_max_kw': resultado_sim.get('demanda_fora_ponta_max', 0),
            'custo_mensal': resultado_sim['custo_mensal'],
            'custo_anual': resultado_sim['custo_mensal'] * 12,
            'investimento_inicial': 500 * 1900,  # Apenas BESS (PV já existe)
            'investimento_adicional': 500 * 1900,  # Apenas BESS (PV já existe)
            'economia_vs_base': (self.cenarios['base']['custo_mensal'] - resultado_sim['custo_mensal']) * 12
        }
        
        self._imprimir_resultado(resultado)
        self.cenarios['pv_254_bess_500'] = resultado
        return resultado
    
    def simular_cenario_pv_324(self):
        """
        Cenário 2: PV 324 kWp (expandido) sem BESS
        Demonstra eficiência de expandir a fotovoltaica
        """
        print("\n" + "="*100)
        print(" "*25 + "CENÁRIO 2 - PV 324 kWp EXPANDIDO (SEM BESS)")
        print("="*100)
        
        caso = CasoIFG(distribuidora=self.distribuidora, modalidade=self.modalidade)
        caso.pv_potencia_kwp = 324
        caso.bess_capacidade_kwh = 0
        caso.usar_diesel = False
        caso._configurar_pv()
        
        resultado_sim = caso.simular_mes()
        
        resultado = {
            'nome': 'PV 324 kWp Expandido',
            'pv_kwp': 324,
            'bess_kwh': 0,
            'energia_total_kwh': resultado_sim['energia_demanda_kwh'],
            'energia_ponta_kwh': resultado_sim.get('energia_ponta_kwh', 0),
            'energia_fora_ponta_kwh': resultado_sim.get('energia_fora_ponta_kwh', 0),
            'energia_reservado_kwh': resultado_sim.get('energia_reservado_kwh', 0),
            'energia_comprada_kwh': resultado_sim['energia_comprada_kwh'],
            'energia_vendida_kwh': resultado_sim['energia_vendida_kwh'],
            'geracao_pv_kwh': resultado_sim['energia_pv_kwh'],
            'demanda_ponta_max_kw': resultado_sim.get('demanda_ponta_max', 0),
            'demanda_fora_ponta_max_kw': resultado_sim.get('demanda_fora_ponta_max', 0),
            'custo_mensal': resultado_sim['custo_mensal'],
            'custo_anual': resultado_sim['custo_mensal'] * 12,
            'investimento_inicial': (324 - 254) * 3500,  # Apenas expansão
            'investimento_adicional': (324 - 254) * 3500,
            'economia_vs_base': (self.cenarios['base']['custo_mensal'] - resultado_sim['custo_mensal']) * 12
        }
        
        self._imprimir_resultado(resultado)
        self.cenarios['pv_324'] = resultado
        return resultado
    
    def simular_cenario_pv_324_bess_500(self):
        """
        Cenário 3: PV 324 kWp expandido + BESS 500 kWh
        Melhor configuração: PV expandido para cobrir demanda + BESS para arbitragem
        """
        print("\n" + "="*100)
        print(" "*20 + "CENÁRIO 3 - PV 324 kWp EXPANDIDO + BESS 500 kWh")
        print("="*100)
        
        caso = CasoIFG(distribuidora=self.distribuidora, modalidade=self.modalidade)
        caso.pv_potencia_kwp = 324
        caso.bess_capacidade_kwh = 500
        caso.bess_potencia_kw = 200
        caso.usar_diesel = False
        caso._configurar_pv()
        
        resultado_sim = caso.simular_mes()
        
        resultado = {
            'nome': 'PV 324 kWp + BESS 500 kWh',
            'pv_kwp': 324,
            'bess_kwh': 500,
            'energia_total_kwh': resultado_sim['energia_demanda_kwh'],
            'energia_ponta_kwh': resultado_sim.get('energia_ponta_kwh', 0),
            'energia_fora_ponta_kwh': resultado_sim.get('energia_fora_ponta_kwh', 0),
            'energia_reservado_kwh': resultado_sim.get('energia_reservado_kwh', 0),
            'energia_comprada_kwh': resultado_sim['energia_comprada_kwh'],
            'energia_vendida_kwh': resultado_sim['energia_vendida_kwh'],
            'geracao_pv_kwh': resultado_sim['energia_pv_kwh'],
            'demanda_ponta_max_kw': resultado_sim.get('demanda_ponta_max', 0),
            'demanda_fora_ponta_max_kw': resultado_sim.get('demanda_fora_ponta_max', 0),
            'custo_mensal': resultado_sim['custo_mensal'],
            'custo_anual': resultado_sim['custo_mensal'] * 12,
            'investimento_inicial': ((324 - 254) * 3500) + (500 * 1900),  # Expansão PV + BESS
            'investimento_adicional': ((324 - 254) * 3500) + (500 * 1900),
            'economia_vs_base': (self.cenarios['base']['custo_mensal'] - resultado_sim['custo_mensal']) * 12
        }
        
        self._imprimir_resultado(resultado)
        self.cenarios['pv_324_bess_500'] = resultado
        return resultado
    
    def analisar_revisao_demanda(self):
        """
        Analisa economia potencial com revisão da demanda contratada
        """
        print("\n" + "="*100)
        print(" "*25 + "ANÁLISE DE REVISÃO DE DEMANDA CONTRATADA")
        print("="*100)
        
        demanda_otima = self.calcular_demanda_contratada_otima()
        
        # Para o cenário com PV, recalcular demanda máxima considerando geração
        # Aqui vamos usar valores típicos
        
        print(f"\n📊 DEMANDA ATUAL vs DEMANDA ÓTIMA:")
        print(f"  Ponta - Atual: assumido 310 kW")
        print(f"  Ponta - Ótima: {demanda_otima['ponta']:.1f} kW")
        print(f"  Fora Ponta - Atual: assumido 300 kW")
        print(f"  Fora Ponta - Ótima: {demanda_otima['fora_ponta']:.1f} kW")
        
        # Calcular economia na demanda
        if self.modalidade == 'verde':
            # Verde: uma única tarifa de demanda
            demanda_atual = 300  # kW (assumido)
            demanda_otima_val = demanda_otima['fora_ponta']
            economia_demanda_mensal = (demanda_atual - demanda_otima_val) * self.tarifas['tusd_demanda']
        else:
            # Azul: demanda ponta e fora ponta separadas
            demanda_ponta_atual = 310
            demanda_fp_atual = 300
            economia_ponta = (demanda_ponta_atual - demanda_otima['ponta']) * self.tarifas['tusd_ponta_demanda']
            economia_fp = (demanda_fp_atual - demanda_otima['fora_ponta']) * self.tarifas['tusd_fora_ponta_demanda']
            economia_demanda_mensal = economia_ponta + economia_fp
        
        economia_anual = economia_demanda_mensal * 12
        
        print(f"\n💰 ECONOMIA COM REVISÃO DE DEMANDA:")
        print(f"  Economia Mensal: R$ {economia_demanda_mensal:,.2f}")
        print(f"  Economia Anual:  R$ {economia_anual:,.2f}")
        
        return {
            'demanda_otima_ponta': demanda_otima['ponta'],
            'demanda_otima_fora_ponta': demanda_otima['fora_ponta'],
            'economia_mensal': economia_demanda_mensal,
            'economia_anual': economia_anual
        }
    
    def _imprimir_resultado(self, resultado):
        """Imprime resultado de um cenário"""
        print(f"\n⚡ CONFIGURAÇÃO:")
        print(f"  PV Instalado:      {resultado['pv_kwp']} kWp")
        print(f"  BESS:              {resultado['bess_kwh']} kWh")
        
        print(f"\n📊 ENERGIA:")
        print(f"  Demanda Total:     {resultado['energia_total_kwh']:>10,.0f} kWh/mês")
        if 'geracao_pv_kwh' in resultado:
            print(f"  Geração PV:        {resultado['geracao_pv_kwh']:>10,.0f} kWh/mês")
        print(f"  Compra Rede:       {resultado['energia_comprada_kwh']:>10,.0f} kWh/mês")
        print(f"  Venda Rede:        {resultado['energia_vendida_kwh']:>10,.0f} kWh/mês")
        
        print(f"\n💰 CUSTOS:")
        print(f"  Custo Mensal:      R$ {resultado['custo_mensal']:>12,.2f}")
        print(f"  Custo Anual:       R$ {resultado['custo_anual']:>12,.2f}")
        print(f"  Investimento:      R$ {resultado['investimento_inicial']:>12,.2f}")
        if resultado['economia_vs_base'] > 0:
            print(f"  Economia vs Base:  R$ {resultado['economia_vs_base']:>12,.2f}/ano")
    
    def gerar_comparacao_completa(self):
        """Gera comparação completa entre todos os cenários"""
        print("\n\n" + "="*100)
        print(" "*30 + "COMPARAÇÃO COMPLETA DE CENÁRIOS")
        print("="*100)
        
        # Criar DataFrame para comparação - 4 cenários
        dados = []
        for nome_key in ['base', 'pv_254_bess_500', 'pv_324', 'pv_324_bess_500']:
            cenario = self.cenarios[nome_key]
            dados.append({
                'Cenário': cenario['nome'],
                'PV (kWp)': cenario['pv_kwp'],
                'BESS (kWh)': cenario['bess_kwh'],
                'Custo Mensal (R$)': cenario['custo_mensal'],
                'Custo Anual (R$)': cenario['custo_anual'],
                'Investimento (R$)': cenario['investimento_adicional'],
                'Economia Anual (R$)': cenario['economia_vs_base']
            })
        
        df = pd.DataFrame(dados)
        
        print("\n")
        print(df.to_string(index=False))
        
        # Análise de eficiência
        print("\n\n" + "="*100)
        print(" "*30 + "ANÁLISE DE EFICIÊNCIA")
        print("="*100)
        
        # Comparar Base (PV 254) vs PV 254 + BESS (Cenário 1)
        base = self.cenarios['base']
        com_bess = self.cenarios['pv_254_bess_500']
        
        economia_bess = (base['custo_anual'] - com_bess['custo_anual'])
        investimento_bess = 500 * 1900
        payback_bess = investimento_bess / economia_bess if economia_bess > 0 else float('inf')
        
        print(f"\n🔋 CENÁRIO 1: BESS 500 kWh (adicionado ao PV 254 kWp existente):")
        print(f"  Investimento BESS:        R$ {investimento_bess:,.2f}")
        print(f"  Economia Anual:           R$ {economia_bess:,.2f}")
        print(f"  Payback:                  {payback_bess:.1f} anos")
        
        if economia_bess > 0:
            print(f"  ✅ Vale a pena: economia de R$ {economia_bess:,.2f}/ano")
        else:
            print(f"  ❌ Não vale a pena: prejuízo de R$ {-economia_bess:,.2f}/ano")
        
        # Comparar Base (PV 254) vs PV 324 (Cenário 2)
        pv_324 = self.cenarios['pv_324']
        
        economia_expansao = (base['custo_anual'] - pv_324['custo_anual'])
        investimento_expansao = (324 - 254) * 3500
        payback_expansao = investimento_expansao / economia_expansao if economia_expansao > 0 else float('inf')
        
        print(f"\n☀️ CENÁRIO 2: EXPANSÃO PV de 254 para 324 kWp (+70 kWp):")
        print(f"  Investimento Adicional:   R$ {investimento_expansao:,.2f}")
        print(f"  Economia Anual:           R$ {economia_expansao:,.2f}")
        print(f"  Payback:                  {payback_expansao:.1f} anos")
        
        if payback_expansao < 10:
            print(f"  ✅ RECOMENDADO: Expandir fotovoltaica é eficiente!")
        else:
            print(f"  ⚠️  Avaliar outras opções")
        
        # Comparar Cenário 3 (PV 324 + BESS) com Base
        pv_324_bess = self.cenarios['pv_324_bess_500']
        
        economia_completo = (base['custo_anual'] - pv_324_bess['custo_anual'])
        investimento_completo = ((324 - 254) * 3500) + (500 * 1900)
        payback_completo = investimento_completo / economia_completo if economia_completo > 0 else float('inf')
        
        print(f"\n🚀 CENÁRIO 3: EXPANSÃO + BESS (PV 324 kWp + BESS 500 kWh):")
        print(f"  Investimento Total:       R$ {investimento_completo:,.2f}")
        print(f"  Economia Anual:           R$ {economia_completo:,.2f}")
        print(f"  Payback:                  {payback_completo:.1f} anos")
        
        if payback_completo < 10:
            print(f"  ✅ SOLUÇÃO ÓTIMA: Melhor retorno financeiro!")
        
        return df
    
    def gerar_graficos(self):
        """Gera gráficos comparativos - 4 cenários"""
        fig, axes = plt.subplots(2, 2, figsize=(16, 10))
        fig.suptitle('Comparação de Cenários - Caso IFG', fontsize=16, fontweight='bold')
        
        # Lista dos 4 cenários na ordem correta
        cenarios_lista = [
            self.cenarios['base'],
            self.cenarios['pv_254_bess_500'],
            self.cenarios['pv_324'],
            self.cenarios['pv_324_bess_500']
        ]
        nomes = [c['nome'] for c in cenarios_lista]
        cores = ['gray', 'orange', 'blue', 'green']
        
        # Gráfico 1: Custo Anual
        ax1 = axes[0, 0]
        custos = [c['custo_anual'] for c in cenarios_lista]
        bars1 = ax1.bar(range(len(nomes)), [c/1000 for c in custos], color=cores)
        ax1.set_xticks(range(len(nomes)))
        ax1.set_xticklabels(nomes, rotation=15, ha='right', fontsize=9)
        ax1.set_ylabel('Custo Anual (R$ mil)', fontsize=12)
        ax1.set_title('Custo Anual por Cenário', fontsize=14, fontweight='bold')
        ax1.grid(True, alpha=0.3, axis='y')
        
        # Adicionar valores nas barras
        for i, bar in enumerate(bars1):
            height = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width()/2., height,
                    f'R$ {custos[i]/1000:.1f}k',
                    ha='center', va='bottom', fontsize=10)
        
        # Gráfico 2: Economia Anual vs Base
        ax2 = axes[0, 1]
        economias = [c['economia_vs_base'] for c in cenarios_lista]
        bars2 = ax2.bar(range(len(nomes)), [e/1000 for e in economias], color=cores)
        ax2.set_xticks(range(len(nomes)))
        ax2.set_xticklabels(nomes, rotation=15, ha='right', fontsize=9)
        ax2.set_ylabel('Economia Anual (R$ mil)', fontsize=12)
        ax2.set_title('Economia Anual vs Base (PV 254)', fontsize=14, fontweight='bold')
        ax2.grid(True, alpha=0.3, axis='y')
        ax2.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
        
        for i, bar in enumerate(bars2):
            height = bar.get_height()
            ax2.text(bar.get_x() + bar.get_width()/2., height,
                    f'R$ {economias[i]/1000:.1f}k',
                    ha='center', va='bottom' if height > 0 else 'top', fontsize=10)
        
        # Gráfico 3: Investimento Adicional
        ax3 = axes[1, 0]
        investimentos = [c['investimento_adicional'] for c in cenarios_lista]
        bars3 = ax3.bar(range(len(nomes)), [inv/1000 for inv in investimentos], color=cores)
        ax3.set_xticks(range(len(nomes)))
        ax3.set_xticklabels(nomes, rotation=15, ha='right', fontsize=9)
        ax3.set_ylabel('Investimento Adicional (R$ mil)', fontsize=12)
        ax3.set_title('Investimento Adicional vs Base', fontsize=14, fontweight='bold')
        ax3.grid(True, alpha=0.3, axis='y')
        
        for i, bar in enumerate(bars3):
            height = bar.get_height()
            if height > 0:
                ax3.text(bar.get_x() + bar.get_width()/2., height,
                        f'R$ {investimentos[i]/1000:.0f}k',
                        ha='center', va='bottom', fontsize=10)
        
        # Gráfico 4: Payback Simples
        ax4 = axes[1, 1]
        paybacks = []
        for c in cenarios_lista:
            if c['economia_vs_base'] > 0 and c['investimento_adicional'] > 0:
                pb = c['investimento_adicional'] / c['economia_vs_base']
                paybacks.append(min(pb, 30))  # Limitar a 30 anos para visualização
            else:
                paybacks.append(0)
        
        bars4 = ax4.bar(range(len(nomes)), paybacks, color=cores)
        ax4.set_xticks(range(len(nomes)))
        ax4.set_xticklabels(nomes, rotation=15, ha='right', fontsize=9)
        ax4.set_ylabel('Payback (anos)', fontsize=12)
        ax4.set_title('Payback Simples por Cenário', fontsize=14, fontweight='bold')
        ax4.grid(True, alpha=0.3, axis='y')
        ax4.axhline(y=10, color='orange', linestyle='--', linewidth=1, label='Referência 10 anos')
        ax4.legend()
        
        for i, bar in enumerate(bars4):
            height = bar.get_height()
            if height > 0:
                ax4.text(bar.get_x() + bar.get_width()/2., height,
                        f'{paybacks[i]:.1f}a',
                        ha='center', va='bottom', fontsize=10)
        
        plt.tight_layout()
        
        # Salvar gráfico
        filename = 'comparacao_cenarios_ifg.png'
        plt.savefig(filename, dpi=150, bbox_inches='tight')
        print(f"\n📊 Gráficos salvos em: {filename}")
        plt.close()


def main():
    """Executa comparação completa de cenários"""
    print("\n" + "="*100)
    print(" "*25 + "COMPARADOR DE CENÁRIOS - CASO IFG")
    print(" "*20 + "Instituto Federal de Goiás - Análise Comparativa")
    print("="*100)
    
    comparador = ComparadorCenariosIFG(distribuidora='EQUATORIAL GO', modalidade='verde')
    
    # Simular os 4 cenários na ordem correta
    print("\n🔄 Executando simulações dos cenários...")
    comparador.simular_cenario_base()  # Base: PV 254 kWp existente
    comparador.simular_cenario_pv_254_bess_500()  # Cenário 1: + BESS
    comparador.simular_cenario_pv_324()  # Cenário 2: Expansão PV
    comparador.simular_cenario_pv_324_bess_500()  # Cenário 3: Expansão + BESS
    
    # Análise de demanda contratada
    resultado_demanda = comparador.analisar_revisao_demanda()
    
    # Gerar comparação completa
    df_comparacao = comparador.gerar_comparacao_completa()
    
    # Gerar gráficos
    comparador.gerar_graficos()
    
    print("\n\n" + "="*100)
    print(" "*35 + "CONCLUSÕES")
    print("="*100)
    
    print("\n✅ RECOMENDAÇÕES:")
    print("  1. Base atual: PV 254 kWp já instalado no IFG")
    print("  2. Avaliar EXPANSÃO FOTOVOLTAICA (324 kWp) vs adicionar BESS")
    print("  3. Solução ótima pode ser EXPANSÃO + BESS combinados")
    print("  4. Revisar demanda contratada pode gerar economia adicional")
    print(f"  5. Economia potencial com revisão de demanda: R$ {resultado_demanda['economia_anual']:,.2f}/ano")
    print("\n💡 IMPORTANTE: Todas as simulações incluem cálculo de energia exportada com tarifa SCEE (R$ 0.1217/kWh)")

    
    print("\n" + "="*100)


if __name__ == "__main__":
    main()
