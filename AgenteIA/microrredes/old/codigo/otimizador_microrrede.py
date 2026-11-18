"""
Otimizador de Microrrede
Encontra a configuração ótima (PV, BESS, Diesel) que minimiza o custo total
baseado em simulação de fluxo de potência e análise financeira
"""

import numpy as np
from scipy.optimize import minimize, differential_evolution
import matplotlib.pyplot as plt
import sys
from io import StringIO
import pandas as pd

from microrrede_powerflow import MicrorrredePowerFlow
from analise_financeira import AnaliseFinanceiraMicrorrede


class OtimizadorMicrorrede:
    """
    Otimizador que encontra a configuração de microrrede que minimiza
    o custo total (CAPEX + OPEX) ao longo da vida útil do projeto
    """
    
    def __init__(self, 
                 tarifa_energia_kwh=0.85,
                 tarifa_demanda_kw=25.0,
                 vida_util=20,
                 taxa_desconto=0.08,
                 custo_pv_kw=3200,
                 custo_bess_kwh=2200,
                 custo_diesel_kw=1200,
                 custo_diesel_litro=6.50):
        """
        Inicializa o otimizador
        
        Parâmetros:
        -----------
        tarifa_energia_kwh : float
            Tarifa de energia em R$/kWh
        tarifa_demanda_kw : float
            Tarifa de demanda em R$/kW/mês
        vida_util : int
            Vida útil do projeto em anos
        taxa_desconto : float
            Taxa de desconto para VPL
        custo_pv_kw : float
            Custo do sistema PV em R$/kW instalado
        custo_bess_kwh : float
            Custo do BESS em R$/kWh de capacidade
        custo_diesel_kw : float
            Custo do gerador diesel em R$/kW
        custo_diesel_litro : float
            Custo do diesel em R$/litro
        """
        self.tarifa_energia_kwh = tarifa_energia_kwh
        self.tarifa_demanda_kw = tarifa_demanda_kw
        self.vida_util = vida_util
        self.taxa_desconto = taxa_desconto
        
        self.custo_pv_kw = custo_pv_kw
        self.custo_bess_kwh = custo_bess_kwh
        self.custo_diesel_kw = custo_diesel_kw
        self.custo_diesel_litro = custo_diesel_litro
        
        # Histórico de avaliações
        self.historico = {
            'pv_kw': [],
            'bess_kw': [],
            'bess_kwh': [],
            'diesel_kw': [],
            'vpl': [],
            'custo_total': [],
            'economia_anual': [],
            'energia_diesel': [],
            'avaliacao': []
        }
        
        self.num_avaliacoes = 0
        self.melhor_config = None
        self.melhor_vpl = -np.inf
    
    def criar_microrrede_customizada(self, pv_kw, bess_kw, bess_kwh, diesel_kw):
        """
        Cria microrrede com parâmetros customizados
        """
        class MicrorrredeCustomizada(MicrorrredePowerFlow):
            def __init__(self, pv_capacity, bess_capacity_kw, bess_capacity_kwh, diesel_capacity):
                # Definir atributos ANTES de chamar super().__init__()
                self._pv_capacity = pv_capacity
                self._bess_capacity_kw = bess_capacity_kw
                self._bess_capacity_kwh = bess_capacity_kwh
                self._diesel_capacity = diesel_capacity
                
                # Inicializar rede básica
                super().__init__()
            
            def setup_pv_system(self):
                """Configurar sistema PV com capacidade customizada"""
                from fotovoltaico import Painel_Fotovoltaico
                
                self.pv_painel = Painel_Fotovoltaico(
                    fabricante_painel="Canadian Solar",
                    modelo_painel="CS6.2-66TB-610",
                    Pmp=610, Isc=15.97, Voc=48, Imp=14.96, Vmp=40.8,
                    Uisc=0.05, Uvoc=-0.25, Upmp=-0.29,
                    material_painel="Silicio", eficiencia=22.6
                )
                
                self.num_paineis = int(self._pv_capacity / 0.610)
                self.pv_potencia_nominal_kw = self.num_paineis * 0.610
            
            def controle_bess_diesel(self, p_pv_mw, p_carga_mw):
                """Controle com capacidades customizadas"""
                diferenca = p_carga_mw - p_pv_mw
                
                bess_max_mw = self._bess_capacity_kw / 1000
                diesel_max_mw = self._diesel_capacity / 1000
                
                if diferenca <= 0:
                    p_bess = max(-bess_max_mw, diferenca)
                    p_diesel = 0.0
                else:
                    if diferenca <= bess_max_mw:
                        p_bess = diferenca
                        p_diesel = 0.0
                    else:
                        p_bess = bess_max_mw
                        p_diesel = min(diesel_max_mw, diferenca - bess_max_mw)
                
                return p_bess, p_diesel
        
        return MicrorrredeCustomizada(pv_kw, bess_kw, bess_kwh, diesel_kw)
    
    def avaliar_configuracao(self, x, verbose=False):
        """
        Avalia uma configuração [pv_kw, bess_kw, bess_kwh_factor, diesel_kw]
        Retorna o custo total (negativo do VPL para minimização)
        
        Parâmetros:
        -----------
        x : array-like
            [pv_kw, bess_kw, bess_kwh_factor, diesel_kw]
            bess_kwh_factor: multiplicador (horas de armazenamento: 2-8h)
        """
        pv_kw = x[0]
        bess_kw = x[1]
        bess_kwh_factor = x[2]  # Horas de armazenamento
        diesel_kw = x[3]
        
        bess_kwh = bess_kw * bess_kwh_factor
        
        self.num_avaliacoes += 1
        
        try:
            # Redirecionar stdout para suprimir prints
            old_stdout = sys.stdout
            sys.stdout = StringIO()
            
            # Criar microrrede customizada
            microrrede = self.criar_microrrede_customizada(pv_kw, bess_kw, bess_kwh, diesel_kw)
            
            # Simular fluxo de potência
            microrrede.simular_24h()
            
            # Restaurar stdout
            sys.stdout = old_stdout
            
            # Criar análise financeira
            analise = AnaliseFinanceiraMicrorrede(
                tarifa_energia_kwh=self.tarifa_energia_kwh,
                tarifa_demanda_kw=self.tarifa_demanda_kw,
                vida_util=self.vida_util,
                taxa_desconto=self.taxa_desconto
            )
            
            analise.custo_pv_kw = self.custo_pv_kw
            analise.custo_bess_kwh = self.custo_bess_kwh
            analise.custo_diesel_kw = self.custo_diesel_kw
            analise.custo_diesel_litro = self.custo_diesel_litro
            
            analise.microrrede = microrrede
            
            # Calcular indicadores
            custos_base = analise.calcular_custos_sem_microrrede()
            custos_micro = analise.calcular_custos_com_microrrede()
            capex_info = analise.calcular_capex()
            
            economia_anual = custos_base['custo_total'] - custos_micro['custo_total']
            
            vpl, _ = analise.calcular_vpl()
            
            # Armazenar no histórico
            self.historico['pv_kw'].append(pv_kw)
            self.historico['bess_kw'].append(bess_kw)
            self.historico['bess_kwh'].append(bess_kwh)
            self.historico['diesel_kw'].append(diesel_kw)
            self.historico['vpl'].append(vpl)
            self.historico['custo_total'].append(capex_info['capex_total'])
            self.historico['economia_anual'].append(economia_anual)
            self.historico['energia_diesel'].append(custos_micro['energia_diesel_kwh'])
            self.historico['avaliacao'].append(self.num_avaliacoes)
            
            # Atualizar melhor configuração
            if vpl > self.melhor_vpl:
                self.melhor_vpl = vpl
                self.melhor_config = {
                    'pv_kw': pv_kw,
                    'bess_kw': bess_kw,
                    'bess_kwh': bess_kwh,
                    'diesel_kw': diesel_kw,
                    'vpl': vpl,
                    'capex': capex_info['capex_total'],
                    'economia_anual': economia_anual,
                    'custos_micro': custos_micro
                }
            
            if verbose or self.num_avaliacoes % 10 == 0:
                print(f"Aval {self.num_avaliacoes:3d} | "
                      f"PV={pv_kw:6.0f}kW | BESS={bess_kw:4.0f}kW/{bess_kwh:5.0f}kWh | "
                      f"Diesel={diesel_kw:4.0f}kW | VPL=R${vpl/1e6:6.2f}M")
            
            # Retornar negativo do VPL (para minimização)
            return -vpl
            
        except Exception as e:
            # Restaurar stdout em caso de erro
            sys.stdout = old_stdout
            print(f"Erro na avaliação: {e}")
            return 1e12  # Penalidade alta
    
    def otimizar_evolucao_diferencial(self, 
                                       bounds=None,
                                       maxiter=100,
                                       popsize=15,
                                       workers=1):
        """
        Otimização usando Evolução Diferencial (global)
        Melhor para encontrar ótimo global em espaço complexo
        
        Parâmetros:
        -----------
        bounds : list of tuples
            Limites [(min_pv, max_pv), (min_bess_kw, max_bess_kw), 
                     (min_hours, max_hours), (min_diesel, max_diesel)]
        maxiter : int
            Número máximo de iterações
        popsize : int
            Tamanho da população (indivíduos por geração)
        workers : int
            Número de processos paralelos
        """
        if bounds is None:
            # Limites padrão [min, max]
            bounds = [
                (200, 3000),    # PV: 200 kW a 3000 kW
                (100, 800),     # BESS potência: 100 kW a 800 kW
                (2, 8),         # BESS horas: 2h a 8h de armazenamento
                (100, 500)      # Diesel: 100 kW a 500 kW
            ]
        
        print("=" * 90)
        print(" " * 25 + "OTIMIZAÇÃO DE MICRORREDE")
        print("=" * 90)
        print("\nMétodo: Evolução Diferencial (Global)")
        print(f"População: {popsize} indivíduos")
        print(f"Máximo de iterações: {maxiter}")
        print("\nLimites de busca:")
        print(f"  PV:           {bounds[0][0]:6.0f} - {bounds[0][1]:6.0f} kW")
        print(f"  BESS potência: {bounds[1][0]:5.0f} - {bounds[1][1]:5.0f} kW")
        print(f"  BESS duração:  {bounds[2][0]:5.1f} - {bounds[2][1]:5.1f} horas")
        print(f"  Diesel:        {bounds[3][0]:5.0f} - {bounds[3][1]:5.0f} kW")
        print("\n" + "=" * 90)
        print("\nIniciando otimização...")
        print("-" * 90)
        
        # Reset histórico
        self.num_avaliacoes = 0
        self.melhor_vpl = -np.inf
        for key in self.historico:
            self.historico[key] = []
        
        # Otimização
        resultado = differential_evolution(
            self.avaliar_configuracao,
            bounds=bounds,
            maxiter=maxiter,
            popsize=popsize,
            strategy='best1bin',
            mutation=(0.5, 1.5),
            recombination=0.7,
            seed=42,
            workers=workers,
            updating='deferred' if workers > 1 else 'immediate',
            polish=True,
            disp=False
        )
        
        print("\n" + "=" * 90)
        print("OTIMIZAÇÃO CONCLUÍDA")
        print("=" * 90)
        
        # Extrair melhor solução
        x_opt = resultado.x
        pv_opt = x_opt[0]
        bess_kw_opt = x_opt[1]
        bess_kwh_opt = x_opt[1] * x_opt[2]
        diesel_opt = x_opt[3]
        
        print("\n🏆 CONFIGURAÇÃO ÓTIMA:")
        print(f"   PV:           {pv_opt:8.1f} kW")
        print(f"   BESS:         {bess_kw_opt:8.1f} kW / {bess_kwh_opt:8.1f} kWh "
              f"({x_opt[2]:.1f}h)")
        print(f"   Diesel:       {diesel_opt:8.1f} kW")
        print("\n💰 INDICADORES:")
        print(f"   VPL:          R$ {self.melhor_config['vpl']:,.2f}")
        print(f"   CAPEX:        R$ {self.melhor_config['capex']:,.2f}")
        print(f"   Economia/ano: R$ {self.melhor_config['economia_anual']:,.2f}")
        print(f"   Diesel/ano:   {self.melhor_config['custos_micro']['energia_diesel_kwh']:,.0f} kWh")
        print("\n📊 CONVERGÊNCIA:")
        print(f"   Avaliações:   {self.num_avaliacoes}")
        print(f"   Sucesso:      {'Sim' if resultado.success else 'Não'}")
        print(f"   Mensagem:     {resultado.message}")
        print("=" * 90)
        
        return resultado
    
    def otimizar_sequencial(self, x0=None, bounds=None, maxiter=50):
        """
        Otimização sequencial usando método L-BFGS-B
        Mais rápido mas pode ficar preso em ótimo local
        
        Parâmetros:
        -----------
        x0 : array-like
            Ponto inicial [pv_kw, bess_kw, bess_hours, diesel_kw]
        bounds : list of tuples
            Limites para cada variável
        maxiter : int
            Número máximo de iterações
        """
        if bounds is None:
            bounds = [
                (200, 3000),
                (100, 800),
                (2, 8),
                (100, 500)
            ]
        
        if x0 is None:
            # Ponto inicial: configuração média
            x0 = [
                (bounds[0][0] + bounds[0][1]) / 2,  # PV
                (bounds[1][0] + bounds[1][1]) / 2,  # BESS kW
                4.0,                                  # BESS horas
                (bounds[3][0] + bounds[3][1]) / 2   # Diesel
            ]
        
        print("=" * 90)
        print(" " * 25 + "OTIMIZAÇÃO DE MICRORREDE")
        print("=" * 90)
        print("\nMétodo: L-BFGS-B (Sequencial)")
        print(f"Ponto inicial: PV={x0[0]:.0f}kW, BESS={x0[1]:.0f}kW/{x0[1]*x0[2]:.0f}kWh, "
              f"Diesel={x0[3]:.0f}kW")
        print("=" * 90)
        
        # Reset
        self.num_avaliacoes = 0
        self.melhor_vpl = -np.inf
        
        # Otimização
        resultado = minimize(
            self.avaliar_configuracao,
            x0=x0,
            method='L-BFGS-B',
            bounds=bounds,
            options={'maxiter': maxiter, 'disp': True}
        )
        
        print("\n" + "=" * 90)
        print("OTIMIZAÇÃO CONCLUÍDA")
        print("=" * 90)
        
        return resultado
    
    def plotar_resultados_otimizacao(self):
        """Plota os resultados da otimização"""
        if len(self.historico['avaliacao']) == 0:
            print("Nenhuma otimização executada ainda!")
            return
        
        plt.figure(figsize=(18, 12))
        
        # Gráfico 1: Evolução do VPL
        ax1 = plt.subplot(2, 3, 1)
        avaliacoes = self.historico['avaliacao']
        vpls = np.array(self.historico['vpl'])
        
        # VPL ao longo das avaliações
        ax1.plot(avaliacoes, vpls / 1e6, 'o-', alpha=0.6, markersize=4)
        
        # Melhor VPL acumulado
        vpl_melhor_acumulado = np.maximum.accumulate(vpls)
        ax1.plot(avaliacoes, vpl_melhor_acumulado / 1e6, 'r-', linewidth=2, 
                label='Melhor VPL')
        
        ax1.set_xlabel('Avaliação', fontsize=11)
        ax1.set_ylabel('VPL (R$ Milhões)', fontsize=11)
        ax1.set_title('Convergência do VPL', fontsize=12, fontweight='bold')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # Gráfico 2: VPL vs Capacidade PV
        ax2 = plt.subplot(2, 3, 2)
        scatter = ax2.scatter(self.historico['pv_kw'], vpls / 1e6, 
                             c=self.historico['avaliacao'], 
                             cmap='viridis', s=50, alpha=0.7)
        
        # Marcar melhor ponto
        idx_melhor = np.argmax(vpls)
        ax2.plot(self.historico['pv_kw'][idx_melhor], 
                vpls[idx_melhor] / 1e6, 'r*', markersize=20, 
                label='Ótimo')
        
        ax2.set_xlabel('Capacidade PV (kW)', fontsize=11)
        ax2.set_ylabel('VPL (R$ Milhões)', fontsize=11)
        ax2.set_title('VPL vs Capacidade PV', fontsize=12, fontweight='bold')
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        plt.colorbar(scatter, ax=ax2, label='Avaliação')
        
        # Gráfico 3: VPL vs Capacidade BESS
        ax3 = plt.subplot(2, 3, 3)
        scatter = ax3.scatter(self.historico['bess_kwh'], vpls / 1e6,
                             c=self.historico['pv_kw'],
                             cmap='plasma', s=50, alpha=0.7)
        
        ax3.plot(self.historico['bess_kwh'][idx_melhor],
                vpls[idx_melhor] / 1e6, 'r*', markersize=20)
        
        ax3.set_xlabel('Capacidade BESS (kWh)', fontsize=11)
        ax3.set_ylabel('VPL (R$ Milhões)', fontsize=11)
        ax3.set_title('VPL vs Capacidade BESS', fontsize=12, fontweight='bold')
        ax3.grid(True, alpha=0.3)
        plt.colorbar(scatter, ax=ax3, label='PV (kW)')
        
        # Gráfico 4: CAPEX vs Economia Anual
        ax4 = plt.subplot(2, 3, 4)
        scatter = ax4.scatter(np.array(self.historico['custo_total']) / 1e6,
                             np.array(self.historico['economia_anual']) / 1e6,
                             c=vpls / 1e6,
                             cmap='RdYlGn', s=50, alpha=0.7)
        
        ax4.plot(self.historico['custo_total'][idx_melhor] / 1e6,
                self.historico['economia_anual'][idx_melhor] / 1e6,
                'r*', markersize=20)
        
        # Linha de break-even simplificada
        x_range = np.linspace(0, max(self.historico['custo_total']), 100) / 1e6
        y_breakeven = x_range / self.vida_util * (1 + self.taxa_desconto)
        ax4.plot(x_range, y_breakeven, 'k--', alpha=0.5, 
                label=f'Break-even ~{self.vida_util}anos')
        
        ax4.set_xlabel('CAPEX (R$ Milhões)', fontsize=11)
        ax4.set_ylabel('Economia Anual (R$ Milhões)', fontsize=11)
        ax4.set_title('CAPEX vs Economia Anual', fontsize=12, fontweight='bold')
        ax4.legend()
        ax4.grid(True, alpha=0.3)
        plt.colorbar(scatter, ax=ax4, label='VPL (R$ M)')
        
        # Gráfico 5: Uso de Diesel
        ax5 = plt.subplot(2, 3, 5)
        scatter = ax5.scatter(self.historico['pv_kw'],
                             np.array(self.historico['energia_diesel']) / 1e6,
                             c=self.historico['bess_kwh'],
                             cmap='coolwarm', s=50, alpha=0.7)
        
        ax5.plot(self.historico['pv_kw'][idx_melhor],
                self.historico['energia_diesel'][idx_melhor] / 1e6,
                'r*', markersize=20)
        
        ax5.set_xlabel('Capacidade PV (kW)', fontsize=11)
        ax5.set_ylabel('Energia Diesel (MWh/ano)', fontsize=11)
        ax5.set_title('Uso de Diesel vs Capacidade PV', fontsize=12, fontweight='bold')
        ax5.grid(True, alpha=0.3)
        plt.colorbar(scatter, ax=ax5, label='BESS (kWh)')
        
        # Gráfico 6: Distribuição de configurações testadas (3D)
        ax6 = plt.subplot(2, 3, 6, projection='3d')
        
        scatter = ax6.scatter(self.historico['pv_kw'],
                             self.historico['bess_kwh'],
                             vpls / 1e6,
                             c=vpls / 1e6,
                             cmap='viridis', s=30, alpha=0.6)
        
        # Melhor ponto
        ax6.scatter([self.historico['pv_kw'][idx_melhor]],
                   [self.historico['bess_kwh'][idx_melhor]],
                   [vpls[idx_melhor] / 1e6],
                   c='red', s=200, marker='*', edgecolors='black', linewidths=2)
        
        ax6.set_xlabel('PV (kW)', fontsize=10)
        ax6.set_ylabel('BESS (kWh)', fontsize=10)
        ax6.set_zlabel('VPL (R$ M)', fontsize=10)
        ax6.set_title('Espaço de Soluções 3D', fontsize=12, fontweight='bold')
        
        plt.tight_layout()
        plt.savefig('otimizacao_microrrede.png', dpi=150, bbox_inches='tight')
        print("\n📊 Gráfico salvo: 'otimizacao_microrrede.png'")
        plt.show()
    
    def gerar_relatorio_otimizacao(self):
        """Gera relatório detalhado da otimização"""
        if self.melhor_config is None:
            print("Nenhuma otimização executada!")
            return
        
        print("\n" + "=" * 90)
        print(" " * 30 + "RELATÓRIO DE OTIMIZAÇÃO")
        print("=" * 90)
        
        print("\n📋 PARÂMETROS ECONÔMICOS:")
        print("-" * 90)
        print(f"   Tarifa energia:        R$ {self.tarifa_energia_kwh:.2f}/kWh")
        print(f"   Tarifa demanda:        R$ {self.tarifa_demanda_kw:.2f}/kW/mês")
        print(f"   Taxa de desconto:      {self.taxa_desconto * 100:.1f}% a.a.")
        print(f"   Vida útil:             {self.vida_util} anos")
        print(f"   Custo PV:              R$ {self.custo_pv_kw:,.0f}/kW")
        print(f"   Custo BESS:            R$ {self.custo_bess_kwh:,.0f}/kWh")
        print(f"   Custo Diesel:          R$ {self.custo_diesel_kw:,.0f}/kW")
        print(f"   Custo combustível:     R$ {self.custo_diesel_litro:.2f}/litro")
        
        print("\n🏆 CONFIGURAÇÃO ÓTIMA:")
        print("-" * 90)
        print(f"   Sistema Fotovoltaico:  {self.melhor_config['pv_kw']:,.1f} kW")
        print(f"   Bateria (BESS):        {self.melhor_config['bess_kw']:,.1f} kW / "
              f"{self.melhor_config['bess_kwh']:,.1f} kWh")
        horas = self.melhor_config['bess_kwh'] / self.melhor_config['bess_kw']
        print(f"   Autonomia BESS:        {horas:.1f} horas")
        print(f"   Gerador Diesel:        {self.melhor_config['diesel_kw']:,.1f} kW")
        
        print("\n💰 INDICADORES ECONÔMICOS:")
        print("-" * 90)
        print(f"   CAPEX Total:           R$ {self.melhor_config['capex']:,.2f}")
        print(f"   VPL:                   R$ {self.melhor_config['vpl']:,.2f}")
        print(f"   Economia Anual:        R$ {self.melhor_config['economia_anual']:,.2f}")
        
        # Calcular TIR e Payback
        old_stdout = sys.stdout
        sys.stdout = StringIO()
        
        analise = AnaliseFinanceiraMicrorrede(
            tarifa_energia_kwh=self.tarifa_energia_kwh,
            tarifa_demanda_kw=self.tarifa_demanda_kw,
            vida_util=self.vida_util,
            taxa_desconto=self.taxa_desconto
        )
        
        microrrede = self.criar_microrrede_customizada(
            self.melhor_config['pv_kw'],
            self.melhor_config['bess_kw'],
            self.melhor_config['bess_kwh'],
            self.melhor_config['diesel_kw']
        )
        
        microrrede.simular_24h()
        analise.microrrede = microrrede
        analise.custo_pv_kw = self.custo_pv_kw
        analise.custo_bess_kwh = self.custo_bess_kwh
        analise.custo_diesel_kw = self.custo_diesel_kw
        
        tir = analise.calcular_tir()
        payback, _ = analise.calcular_payback_descontado()
        
        sys.stdout = old_stdout
        
        print(f"   TIR:                   {tir * 100:.2f}%")
        if payback != np.inf:
            print(f"   Payback Descontado:    {payback} anos")
        else:
            print(f"   Payback Descontado:    > {self.vida_util} anos")
        
        print("\n⚡ DESEMPENHO ENERGÉTICO:")
        print("-" * 90)
        custos = self.melhor_config['custos_micro']
        print(f"   Energia comprada:      {custos['energia_comprada_kwh']:,.0f} kWh/ano")
        print(f"   Energia vendida:       {custos['energia_vendida_kwh']:,.0f} kWh/ano")
        print(f"   Energia diesel:        {custos['energia_diesel_kwh']:,.0f} kWh/ano")
        print(f"   Demanda máxima:        {custos['demanda_max_kw']:.1f} kW")
        
        carga_total = 500 * 24 * 365  # kWh/ano
        percentual_diesel = (custos['energia_diesel_kwh'] / carga_total) * 100
        print(f"   Diesel/Carga:          {percentual_diesel:.1f}%")
        
        print("\n📊 PROCESSO DE OTIMIZAÇÃO:")
        print("-" * 90)
        print(f"   Total de avaliações:   {self.num_avaliacoes}")
        configs_unicas = len(set(zip(self.historico['pv_kw'], self.historico['bess_kw'])))
        print(f"   Configurações únicas:  {configs_unicas}")
        
        # Top 5 configurações
        vpls_array = np.array(self.historico['vpl'])
        top5_indices = np.argsort(vpls_array)[-5:][::-1]
        
        print("\n🥇 TOP 5 CONFIGURAÇÕES:")
        print("-" * 90)
        print(f"{'Rank':<6} {'PV (kW)':<12} {'BESS':<20} {'Diesel (kW)':<12} {'VPL (R$ M)':<12}")
        print("-" * 90)
        
        for rank, idx in enumerate(top5_indices, 1):
            pv = self.historico['pv_kw'][idx]
            bess_kw = self.historico['bess_kw'][idx]
            bess_kwh = self.historico['bess_kwh'][idx]
            diesel = self.historico['diesel_kw'][idx]
            vpl = self.historico['vpl'][idx]
            
            print(f"{rank:<6} {pv:>10.0f}   {bess_kw:>6.0f}kW/{bess_kwh:>7.0f}kWh   "
                  f"{diesel:>10.0f}   {vpl/1e6:>10.2f}")
        
        print("\n" + "=" * 90)
    
    def salvar_historico_csv(self, filename='otimizacao_historico.csv'):
        """Salva histórico de avaliações em CSV"""
        df = pd.DataFrame(self.historico)
        df.to_csv(filename, index=False)
        print(f"\n💾 Histórico salvo: '{filename}'")


def exemplo_otimizacao_completa():
    """Exemplo de uso completo do otimizador"""
    
    # Criar otimizador
    otimizador = OtimizadorMicrorrede(
        tarifa_energia_kwh=0.85,
        tarifa_demanda_kw=25.0,
        vida_util=20,
        taxa_desconto=0.08,
        custo_pv_kw=3200,
        custo_bess_kwh=2200,
        custo_diesel_kw=1200,
        custo_diesel_litro=6.50
    )
    
    # Definir limites de busca
    limites = [
        (400, 2500),    # PV: 400-2500 kW
        (200, 700),     # BESS potência: 200-700 kW
        (2, 6),         # BESS horas: 2-6h
        (100, 400)      # Diesel: 100-400 kW
    ]
    
    # Executar otimização
    otimizador.otimizar_evolucao_diferencial(
        bounds=limites,
        maxiter=50,      # Reduzir para teste rápido
        popsize=15,
        workers=1
    )
    
    # Gerar relatório
    otimizador.gerar_relatorio_otimizacao()
    
    # Plotar resultados
    otimizador.plotar_resultados_otimizacao()
    
    # Salvar histórico
    otimizador.salvar_historico_csv()
    
    return otimizador


if __name__ == "__main__":
    print("\n" + "=" * 90)
    print(" " * 20 + "OTIMIZADOR DE MICRORREDE - MINIMIZAÇÃO DE CUSTOS")
    print("=" * 90)
    print("\nEste módulo encontra a configuração ótima de:")
    print("  • Capacidade do sistema fotovoltaico (PV)")
    print("  • Capacidade do sistema de baterias (BESS)")
    print("  • Capacidade do gerador diesel")
    print("\nQue MAXIMIZA o VPL (minimiza custo total) baseado em:")
    print("  ✓ Simulação de fluxo de potência realista")
    print("  ✓ Custos de equipamentos (CAPEX)")
    print("  ✓ Custos operacionais (energia, diesel, O&M)")
    print("  ✓ Análise financeira ao longo da vida útil")
    print("\n" + "=" * 90)
    
    input("\nPressione ENTER para iniciar otimização...")
    
    otimizador = exemplo_otimizacao_completa()
