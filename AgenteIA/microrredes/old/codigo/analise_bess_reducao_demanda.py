"""
Análise de redução de demanda contratada com BESS (Battery Energy Storage System)
Estratégia: Peak Shaving - BESS descarrega para reduzir picos de demanda
Arquivo: dem_ativa_kw por datetime e ponto.csv
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime

class AnalisadorBESSReducaoDemanda:
    """Analisa impacto do BESS na redução de demanda contratada via peak shaving"""
    
    def __init__(self, arquivo_demanda='dem_ativa_kw por datetime e ponto.csv'):
        self.arquivo = arquivo_demanda
        self.demanda_atual_kw = 350  # Demanda contratada atual
        self.tarifa_demanda = 26.08  # R$/kW - Verde EQUATORIAL GO
        self.df_demanda = None
        
    def carregar_dados(self):
        """Carrega e processa dados de demanda"""
        print("\n📊 Carregando dados de demanda...")
        
        self.df_demanda = pd.read_csv(self.arquivo)
        self.df_demanda['datetime'] = pd.to_datetime(self.df_demanda['datetime'])
        
        # Adicionar informações temporais
        self.df_demanda['hora'] = self.df_demanda['datetime'].dt.hour
        self.df_demanda['dia_semana'] = self.df_demanda['datetime'].dt.dayofweek
        self.df_demanda['dia'] = self.df_demanda['datetime'].dt.date
        self.df_demanda['mes'] = self.df_demanda['datetime'].dt.month
        
        # Identificar ponta (18h-21h em dias úteis)
        self.df_demanda['is_ponta'] = (
            (self.df_demanda['hora'] >= 18) & 
            (self.df_demanda['hora'] < 21) & 
            (self.df_demanda['dia_semana'] < 5)
        )
        
        print(f"✓ Dados carregados: {len(self.df_demanda)} registros")
        print(f"  Período: {self.df_demanda['datetime'].min()} a {self.df_demanda['datetime'].max()}")
        
    def simular_bess_peak_shaving(self, bess_capacidade_kwh, bess_potencia_kw, limite_demanda_kw):
        """
        Simula operação do BESS para peak shaving
        
        Estratégia:
        1. BESS carrega fora dos picos (demanda < 70% do limite)
        2. BESS descarrega quando demanda > limite alvo
        3. Objetivo: "cortar" picos acima do limite
        
        Parâmetros:
        -----------
        bess_capacidade_kwh : float
            Capacidade do BESS em kWh
        bess_potencia_kw : float
            Potência máxima de carga/descarga em kW
        limite_demanda_kw : float
            Limite de demanda alvo (setpoint para peak shaving)
        """
        
        # Copiar dados para simulação
        df_sim = self.df_demanda.copy()
        
        # Estado do BESS
        soc_kwh = bess_capacidade_kwh * 0.5  # Começar com 50% de carga
        historico_soc = []
        demanda_liquida = []
        potencia_bess_usada = []
        
        # Parâmetros operacionais
        eficiencia = 0.92  # Eficiência round-trip
        soc_min = bess_capacidade_kwh * 0.10  # Mínimo 10%
        soc_max = bess_capacidade_kwh * 0.90  # Máximo 90%
        
        # Simular cada registro (intervalo de 30 min = 0.5h)
        intervalo_h = 0.5
        
        for idx, row in df_sim.iterrows():
            demanda_original = row['dem_ativa_kw']
            hora = row['hora']
            
            # Estratégia de controle do BESS
            potencia_bess = 0  # Positivo = descarga, Negativo = carga
            
            # FASE 1: DESCARGA - Quando demanda ultrapassa limite
            if demanda_original > limite_demanda_kw:
                # Calcular quanto precisamos descarregar
                excesso_demanda = demanda_original - limite_demanda_kw
                
                # Limitar pela potência do BESS e pelo SOC disponível
                potencia_descarga_max = min(
                    bess_potencia_kw,
                    (soc_kwh - soc_min) / intervalo_h,  # Não ultrapassar SOC mínimo
                    excesso_demanda  # Não descarregar mais que o necessário
                )
                
                potencia_bess = max(0, potencia_descarga_max)
                energia_descarga = potencia_bess * intervalo_h
                soc_kwh = max(soc_min, soc_kwh - energia_descarga)
            
            # FASE 2: CARGA - Quando demanda está baixa e SOC não está cheio
            elif demanda_original < limite_demanda_kw * 0.7 and soc_kwh < soc_max:
                # Carregar quando demanda está abaixo de 70% do limite
                # Priorizar horários de madrugada (tarifa mais barata)
                fator_carga = 1.0
                if 0 <= hora < 6:  # Madrugada - carregar mais
                    fator_carga = 1.5
                elif 18 <= hora < 21:  # Ponta - não carregar
                    fator_carga = 0.0
                
                # Calcular potência de carga
                potencia_carga_max = min(
                    bess_potencia_kw * fator_carga,
                    (soc_max - soc_kwh) / intervalo_h / eficiencia  # Não ultrapassar SOC máximo
                )
                
                potencia_bess = -max(0, potencia_carga_max)  # Negativo indica carga
                energia_carga = -potencia_bess * intervalo_h * eficiencia
                soc_kwh = min(soc_max, soc_kwh + energia_carga)
            
            # Calcular demanda líquida vista pela rede
            demanda_com_bess = demanda_original - potencia_bess
            
            # Armazenar resultados
            historico_soc.append(soc_kwh)
            demanda_liquida.append(demanda_com_bess)
            potencia_bess_usada.append(potencia_bess)
        
        # Adicionar ao dataframe
        df_sim['soc_kwh'] = historico_soc
        df_sim['demanda_com_bess'] = demanda_liquida
        df_sim['potencia_bess_kw'] = potencia_bess_usada
        df_sim['soc_percent'] = (df_sim['soc_kwh'] / bess_capacidade_kwh) * 100
        
        return df_sim
    
    def analisar_cenarios_bess(self):
        """Analisa múltiplos cenários de BESS"""
        print("\n" + "="*100)
        print(" "*25 + "ANÁLISE DE REDUÇÃO DE DEMANDA COM BESS - PEAK SHAVING")
        print("="*100)
        
        # Estatísticas base (sem BESS)
        dem_max_original = self.df_demanda['dem_ativa_kw'].max()
        dem_p95_original = self.df_demanda['dem_ativa_kw'].quantile(0.95)
        dem_p99_original = self.df_demanda['dem_ativa_kw'].quantile(0.99)
        
        print(f"\n📊 SITUAÇÃO ATUAL (SEM BESS):")
        print("-"*100)
        print(f"  Demanda contratada:       {self.demanda_atual_kw} kW")
        print(f"  Demanda máxima medida:    {dem_max_original:.0f} kW")
        print(f"  Demanda P99:              {dem_p99_original:.0f} kW")
        print(f"  Demanda P95:              {dem_p95_original:.0f} kW")
        print(f"  Superdimensionamento:     {self.demanda_atual_kw - dem_max_original:.0f} kW ({(self.demanda_atual_kw - dem_max_original)/self.demanda_atual_kw*100:.1f}%)")
        
        # Cenários de BESS a simular
        cenarios = [
            {'nome': 'BESS 250 kWh / 125 kW', 'capacidade': 250, 'potencia': 125},
            {'nome': 'BESS 500 kWh / 230 kW', 'capacidade': 500, 'potencia': 230},
            {'nome': 'BESS 750 kWh / 300 kW', 'capacidade': 750, 'potencia': 300},
            {'nome': 'BESS 1000 kWh / 400 kW', 'capacidade': 1000, 'potencia': 400},
        ]
        
        # Limites de demanda alvo para testar
        limites_teste = [250, 240, 230, 220, 210, 200]
        
        resultados = []
        
        print(f"\n\n🔋 SIMULANDO CENÁRIOS DE BESS:")
        print("="*100)
        
        for cenario in cenarios:
            print(f"\n{cenario['nome']}:")
            print("-"*100)
            
            for limite in limites_teste:
                # Simular BESS com este limite
                df_sim = self.simular_bess_peak_shaving(
                    bess_capacidade_kwh=cenario['capacidade'],
                    bess_potencia_kw=cenario['potencia'],
                    limite_demanda_kw=limite
                )
                
                # Calcular estatísticas
                dem_max_com_bess = df_sim['demanda_com_bess'].max()
                dem_p99_com_bess = df_sim['demanda_com_bess'].quantile(0.99)
                dem_p95_com_bess = df_sim['demanda_com_bess'].quantile(0.95)
                
                # Demanda contratada sugerida (P99 + 5% margem)
                dem_sugerida = dem_p99_com_bess * 1.05
                
                # Redução vs atual
                reducao_vs_atual = self.demanda_atual_kw - dem_sugerida
                economia_ano = reducao_vs_atual * self.tarifa_demanda * 12
                
                # Redução vs sem BESS
                reducao_vs_sem_bess = dem_p99_original - dem_p99_com_bess
                economia_adicional_ano = reducao_vs_sem_bess * self.tarifa_demanda * 12
                
                # Taxa de sucesso do peak shaving
                registros_acima_limite = (df_sim['dem_ativa_kw'] > limite).sum()
                registros_cortados = (df_sim['demanda_com_bess'] <= limite).sum() - \
                                    (df_sim['dem_ativa_kw'] <= limite).sum()
                taxa_sucesso = (registros_cortados / registros_acima_limite * 100) if registros_acima_limite > 0 else 0
                
                # Energia do BESS utilizada
                energia_descarregada_total = df_sim[df_sim['potencia_bess_kw'] > 0]['potencia_bess_kw'].sum() * 0.5
                energia_carregada_total = df_sim[df_sim['potencia_bess_kw'] < 0]['potencia_bess_kw'].sum() * -0.5
                ciclos_mes = energia_descarregada_total / cenario['capacidade'] if cenario['capacidade'] > 0 else 0
                
                resultados.append({
                    'cenario': cenario['nome'],
                    'capacidade_kwh': cenario['capacidade'],
                    'potencia_kw': cenario['potencia'],
                    'limite_alvo_kw': limite,
                    'dem_max_com_bess': dem_max_com_bess,
                    'dem_p99_com_bess': dem_p99_com_bess,
                    'dem_sugerida': dem_sugerida,
                    'reducao_vs_atual': reducao_vs_atual,
                    'economia_ano': economia_ano,
                    'reducao_vs_sem_bess': reducao_vs_sem_bess,
                    'economia_adicional_ano': economia_adicional_ano,
                    'taxa_sucesso_pct': taxa_sucesso,
                    'ciclos_mes': ciclos_mes,
                    'df_simulacao': df_sim
                })
            
            # Mostrar melhor configuração para este BESS
            resultados_cenario = [r for r in resultados if r['cenario'] == cenario['nome']]
            melhor = max(resultados_cenario, key=lambda x: x['economia_ano'])
            
            print(f"\n  ⭐ MELHOR CONFIGURAÇÃO:")
            print(f"    Limite alvo:           {melhor['limite_alvo_kw']} kW")
            print(f"    Demanda sugerida:      {melhor['dem_sugerida']:.0f} kW (P99 + 5%)")
            print(f"    Redução vs atual:      {melhor['reducao_vs_atual']:.0f} kW")
            print(f"    Economia anual:        R$ {melhor['economia_ano']:,.2f}")
            print(f"    Economia vs sem BESS:  R$ {melhor['economia_adicional_ano']:,.2f}/ano")
            print(f"    Taxa sucesso shaving:  {melhor['taxa_sucesso_pct']:.1f}%")
            print(f"    Ciclos/mês:            {melhor['ciclos_mes']:.1f}")
        
        return resultados
    
    def analise_comparativa_completa(self, resultados):
        """Análise comparativa detalhada"""
        print("\n\n" + "="*100)
        print(" "*35 + "ANÁLISE COMPARATIVA COMPLETA")
        print("="*100)
        
        # Encontrar melhor solução global
        melhor_global = max(resultados, key=lambda x: x['economia_ano'])
        
        print(f"\n🏆 MELHOR SOLUÇÃO GLOBAL:")
        print("-"*100)
        print(f"  Configuração:             {melhor_global['cenario']}")
        print(f"  Limite alvo:              {melhor_global['limite_alvo_kw']} kW")
        print(f"  Demanda contratada nova:  {melhor_global['dem_sugerida']:.0f} kW")
        print(f"  Demanda contratada atual: {self.demanda_atual_kw} kW")
        print(f"  Redução total:            {melhor_global['reducao_vs_atual']:.0f} kW ({melhor_global['reducao_vs_atual']/self.demanda_atual_kw*100:.1f}%)")
        print(f"\n  💰 ECONOMIA ANUAL (DEMANDA):")
        print(f"    Total:                  R$ {melhor_global['economia_ano']:,.2f}/ano")
        print(f"    Adicional pelo BESS:    R$ {melhor_global['economia_adicional_ano']:,.2f}/ano")
        print(f"\n  🔋 OPERAÇÃO DO BESS:")
        print(f"    Taxa sucesso shaving:   {melhor_global['taxa_sucesso_pct']:.1f}%")
        print(f"    Ciclos por mês:         {melhor_global['ciclos_mes']:.1f}")
        
        # Investimento e payback
        custo_kwh = 1900  # R$/kWh típico para BESS Li-ion
        investimento = melhor_global['capacidade_kwh'] * custo_kwh
        payback_demanda_apenas = investimento / melhor_global['economia_adicional_ano']
        
        print(f"\n  💵 ANÁLISE FINANCEIRA (só demanda):")
        print(f"    Investimento estimado:  R$ {investimento:,.2f}")
        print(f"    Payback (só demanda):   {payback_demanda_apenas:.1f} anos")
        print(f"    ⚠️  Nota: Payback real será MENOR considerando também economia de energia")
        
        # Comparação entre tamanhos de BESS
        print(f"\n\n📊 COMPARAÇÃO: TAMANHO DO BESS vs BENEFÍCIO")
        print("-"*100)
        
        # Agrupar por cenário e pegar melhor de cada
        melhores_por_cenario = {}
        for r in resultados:
            if r['cenario'] not in melhores_por_cenario or \
               r['economia_ano'] > melhores_por_cenario[r['cenario']]['economia_ano']:
                melhores_por_cenario[r['cenario']] = r
        
        print(f"\n{'BESS':<30} | Demanda Nova | Redução | Economia/ano | Invest.    | Payback")
        print("-"*100)
        for nome, r in melhores_por_cenario.items():
            invest = r['capacidade_kwh'] * custo_kwh
            pb = invest / r['economia_adicional_ano'] if r['economia_adicional_ano'] > 0 else 999
            print(f"{nome:<30} | {r['dem_sugerida']:>7.0f} kW   | {r['reducao_vs_atual']:>6.0f}kW | R$ {r['economia_ano']:>9,.0f} | R$ {invest:>8,.0f} | {pb:>5.1f} anos")
        
        # Análise de custo-benefício
        print(f"\n\n💡 RECOMENDAÇÕES:")
        print("-"*100)
        
        # Ordenar por melhor relação custo-benefício
        for nome, r in sorted(melhores_por_cenario.items(), 
                             key=lambda x: x[1]['capacidade_kwh']):
            invest = r['capacidade_kwh'] * custo_kwh
            pb = invest / r['economia_adicional_ano'] if r['economia_adicional_ano'] > 0 else 999
            roi = (r['economia_adicional_ano'] / invest * 100) if invest > 0 else 0
            
            print(f"\n  {nome}:")
            print(f"    • Investimento: R$ {invest:,.2f}")
            print(f"    • Economia adicional: R$ {r['economia_adicional_ano']:,.2f}/ano (vs sem BESS)")
            print(f"    • ROI: {roi:.1f}% ao ano (só demanda)")
            print(f"    • Payback: {pb:.1f} anos (só demanda)")
            
            if pb < 7:
                print(f"    ✅ VIÁVEL - Payback atrativo")
            elif pb < 10:
                print(f"    ⚠️  AVALIAR - Payback aceitável considerando energia também")
            else:
                print(f"    ❌ NÃO VIÁVEL - Payback muito longo só com demanda")
        
        return melhor_global, melhores_por_cenario
    
    def gerar_graficos(self, resultados, melhor_global):
        """Gera gráficos de análise"""
        fig = plt.figure(figsize=(20, 14))
        
        # Gráfico 1: Comparação demanda sem vs com BESS (série temporal)
        ax1 = plt.subplot(3, 3, 1)
        
        df_melhor = melhor_global['df_simulacao']
        dias_plot = 7
        df_plot = df_melhor[df_melhor['dia'] <= df_melhor['dia'].unique()[dias_plot-1]]
        
        ax1.plot(df_plot['datetime'], df_plot['dem_ativa_kw'], 
                label='Sem BESS', linewidth=1.5, color='#E63946', alpha=0.8)
        ax1.plot(df_plot['datetime'], df_plot['demanda_com_bess'], 
                label='Com BESS', linewidth=1.5, color='#06A77D')
        ax1.axhline(y=melhor_global['limite_alvo_kw'], color='orange', linestyle='--', 
                   label=f'Limite alvo ({melhor_global["limite_alvo_kw"]} kW)', linewidth=2)
        
        ax1.set_xlabel('Data/Hora', fontsize=10)
        ax1.set_ylabel('Demanda (kW)', fontsize=10)
        ax1.set_title(f'Peak Shaving - {melhor_global["cenario"]}', fontweight='bold', fontsize=11)
        ax1.legend(fontsize=8)
        ax1.grid(True, alpha=0.3)
        plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45, ha='right')
        
        # Gráfico 2: Estado de carga do BESS (SOC)
        ax2 = plt.subplot(3, 3, 2)
        
        ax2.plot(df_plot['datetime'], df_plot['soc_percent'], 
                linewidth=2, color='#457B9D')
        ax2.axhline(y=90, color='red', linestyle='--', alpha=0.5, label='SOC máx (90%)')
        ax2.axhline(y=10, color='red', linestyle='--', alpha=0.5, label='SOC mín (10%)')
        ax2.fill_between(df_plot['datetime'], 10, 90, alpha=0.1, color='green')
        
        ax2.set_xlabel('Data/Hora', fontsize=10)
        ax2.set_ylabel('Estado de Carga (%)', fontsize=10)
        ax2.set_title('Estado de Carga do BESS (SOC)', fontweight='bold', fontsize=11)
        ax2.legend(fontsize=8)
        ax2.grid(True, alpha=0.3)
        ax2.set_ylim(0, 100)
        plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45, ha='right')
        
        # Gráfico 3: Potência do BESS
        ax3 = plt.subplot(3, 3, 3)
        
        cores = ['red' if p > 0 else 'blue' for p in df_plot['potencia_bess_kw']]
        ax3.bar(df_plot['datetime'], df_plot['potencia_bess_kw'], 
               color=cores, alpha=0.6, width=0.02)
        ax3.axhline(y=0, color='black', linewidth=1)
        
        ax3.set_xlabel('Data/Hora', fontsize=10)
        ax3.set_ylabel('Potência BESS (kW)', fontsize=10)
        ax3.set_title('Operação do BESS (+ descarga, - carga)', fontweight='bold', fontsize=11)
        ax3.grid(True, alpha=0.3)
        plt.setp(ax3.xaxis.get_majorticklabels(), rotation=45, ha='right')
        
        # Gráfico 4: Curvas de duração com e sem BESS
        ax4 = plt.subplot(3, 3, 4)
        
        dem_sem_bess_ord = np.sort(self.df_demanda['dem_ativa_kw'].values)[::-1]
        dem_com_bess_ord = np.sort(df_melhor['demanda_com_bess'].values)[::-1]
        percentis = np.arange(len(dem_sem_bess_ord)) / len(dem_sem_bess_ord) * 100
        
        ax4.plot(percentis, dem_sem_bess_ord, linewidth=2, 
                color='#E63946', label='Sem BESS', alpha=0.8)
        ax4.plot(percentis, dem_com_bess_ord, linewidth=2, 
                color='#06A77D', label='Com BESS')
        ax4.axhline(y=self.demanda_atual_kw, color='red', linestyle='--', 
                   label=f'Atual ({self.demanda_atual_kw} kW)', linewidth=2)
        ax4.axhline(y=melhor_global['dem_sugerida'], color='green', linestyle='--', 
                   label=f'Nova ({melhor_global["dem_sugerida"]:.0f} kW)', linewidth=2)
        
        ax4.set_xlabel('Percentual do Tempo (%)', fontsize=10)
        ax4.set_ylabel('Demanda (kW)', fontsize=10)
        ax4.set_title('Curva de Duração - Efeito do BESS', fontweight='bold', fontsize=11)
        ax4.legend(fontsize=8)
        ax4.grid(True, alpha=0.3)
        ax4.set_xlim(0, 100)
        
        # Gráfico 5: Economia por tamanho de BESS
        ax5 = plt.subplot(3, 3, 5)
        
        # Agrupar melhores por cenário
        cenarios_unicos = sorted(set(r['cenario'] for r in resultados))
        melhores = []
        for cen in cenarios_unicos:
            r_cen = [r for r in resultados if r['cenario'] == cen]
            melhor_cen = max(r_cen, key=lambda x: x['economia_ano'])
            melhores.append(melhor_cen)
        
        capacidades = [r['capacidade_kwh'] for r in melhores]
        economias = [r['economia_adicional_ano']/1000 for r in melhores]
        
        bars = ax5.bar(range(len(capacidades)), economias, color='#F18F01', alpha=0.7)
        ax5.set_xticks(range(len(capacidades)))
        ax5.set_xticklabels([f"{c} kWh" for c in capacidades], rotation=15, ha='right')
        ax5.set_ylabel('Economia Adicional (R$ mil/ano)', fontsize=10)
        ax5.set_title('Economia Adicional vs Tamanho do BESS', fontweight='bold', fontsize=11)
        ax5.grid(True, alpha=0.3, axis='y')
        
        for i, (bar, val) in enumerate(zip(bars, economias)):
            ax5.text(bar.get_x() + bar.get_width()/2., val,
                    f'R$ {val:.1f}k', ha='center', va='bottom', fontsize=9)
        
        # Gráfico 6: Payback por tamanho de BESS
        ax6 = plt.subplot(3, 3, 6)
        
        custo_kwh = 1900
        investimentos = [r['capacidade_kwh'] * custo_kwh / 1000 for r in melhores]
        paybacks = [r['capacidade_kwh'] * custo_kwh / r['economia_adicional_ano'] 
                   if r['economia_adicional_ano'] > 0 else 999 for r in melhores]
        
        bars = ax6.bar(range(len(capacidades)), paybacks, color='#A23B72', alpha=0.7)
        ax6.set_xticks(range(len(capacidades)))
        ax6.set_xticklabels([f"{c} kWh" for c in capacidades], rotation=15, ha='right')
        ax6.set_ylabel('Payback (anos)', fontsize=10)
        ax6.set_title('Payback vs Tamanho do BESS (só demanda)', fontweight='bold', fontsize=11)
        ax6.axhline(y=10, color='red', linestyle='--', alpha=0.5, label='10 anos')
        ax6.axhline(y=7, color='orange', linestyle='--', alpha=0.5, label='7 anos')
        ax6.legend(fontsize=8)
        ax6.grid(True, alpha=0.3, axis='y')
        
        for i, (bar, val) in enumerate(zip(bars, paybacks)):
            if val < 20:
                ax6.text(bar.get_x() + bar.get_width()/2., val,
                        f'{val:.1f}a', ha='center', va='bottom', fontsize=9)
        
        # Gráfico 7: Demanda contratada por cenário
        ax7 = plt.subplot(3, 3, 7)
        
        demandas_nova = [r['dem_sugerida'] for r in melhores]
        demandas_atual = [self.demanda_atual_kw] * len(melhores)
        
        x = np.arange(len(capacidades))
        width = 0.35
        
        bars1 = ax7.bar(x - width/2, demandas_atual, width, label='Atual', color='red', alpha=0.6)
        bars2 = ax7.bar(x + width/2, demandas_nova, width, label='Com BESS', color='green', alpha=0.6)
        
        ax7.set_ylabel('Demanda Contratada (kW)', fontsize=10)
        ax7.set_title('Redução de Demanda Contratada', fontweight='bold', fontsize=11)
        ax7.set_xticks(x)
        ax7.set_xticklabels([f"{c} kWh" for c in capacidades], rotation=15, ha='right')
        ax7.legend(fontsize=8)
        ax7.grid(True, alpha=0.3, axis='y')
        
        # Gráfico 8: Perfil horário médio com BESS
        ax8 = plt.subplot(3, 3, 8)
        
        dem_hora_sem = self.df_demanda.groupby('hora')['dem_ativa_kw'].agg(['mean', 'max'])
        dem_hora_com = df_melhor.groupby('hora')['demanda_com_bess'].agg(['mean', 'max'])
        
        ax8.plot(dem_hora_sem.index, dem_hora_sem['max'], 'o-', 
                label='Máx sem BESS', color='red', linewidth=2)
        ax8.plot(dem_hora_com.index, dem_hora_com['max'], 's-', 
                label='Máx com BESS', color='green', linewidth=2)
        ax8.axhspan(18, 21, alpha=0.2, color='yellow')
        
        ax8.set_xlabel('Hora do Dia', fontsize=10)
        ax8.set_ylabel('Demanda (kW)', fontsize=10)
        ax8.set_title('Perfil Horário - Redução de Picos', fontweight='bold', fontsize=11)
        ax8.legend(fontsize=8)
        ax8.grid(True, alpha=0.3)
        ax8.set_xticks(range(0, 24, 2))
        
        # Gráfico 9: ROI por cenário
        ax9 = plt.subplot(3, 3, 9)
        
        rois = [(r['economia_adicional_ano'] / (r['capacidade_kwh'] * custo_kwh) * 100) 
               for r in melhores]
        
        bars = ax9.bar(range(len(capacidades)), rois, color='#06A77D', alpha=0.7)
        ax9.set_xticks(range(len(capacidades)))
        ax9.set_xticklabels([f"{c} kWh" for c in capacidades], rotation=15, ha='right')
        ax9.set_ylabel('ROI (% ao ano)', fontsize=10)
        ax9.set_title('ROI - Retorno sobre Investimento (só demanda)', fontweight='bold', fontsize=11)
        ax9.axhline(y=10, color='green', linestyle='--', alpha=0.5, label='10% a.a.')
        ax9.legend(fontsize=8)
        ax9.grid(True, alpha=0.3, axis='y')
        
        for i, (bar, val) in enumerate(zip(bars, rois)):
            ax9.text(bar.get_x() + bar.get_width()/2., val,
                    f'{val:.1f}%', ha='center', va='bottom', fontsize=9)
        
        plt.tight_layout()
        
        filename = 'analise_bess_reducao_demanda.png'
        plt.savefig(filename, dpi=150, bbox_inches='tight')
        print(f"\n📊 Gráficos salvos em: {filename}")
        plt.close()


def main():
    """Executa análise completa"""
    print("\n" + "="*100)
    print(" "*15 + "ANÁLISE DE REDUÇÃO DE DEMANDA CONTRATADA COM BESS - PEAK SHAVING")
    print(" "*30 + "Instituto Federal de Goiás")
    print("="*100)
    
    analisador = AnalisadorBESSReducaoDemanda()
    analisador.carregar_dados()
    
    # Simular cenários
    resultados = analisador.analisar_cenarios_bess()
    
    # Análise comparativa
    melhor_global, melhores_por_cenario = analisador.analise_comparativa_completa(resultados)
    
    # Gráficos
    analisador.gerar_graficos(resultados, melhor_global)
    
    # Salvar resultados detalhados
    df_resultados = pd.DataFrame([
        {
            'Cenário': r['cenario'],
            'Capacidade_kWh': r['capacidade_kwh'],
            'Potência_kW': r['potencia_kw'],
            'Limite_Alvo_kW': r['limite_alvo_kw'],
            'Demanda_Sugerida_kW': r['dem_sugerida'],
            'Redução_vs_Atual_kW': r['reducao_vs_atual'],
            'Economia_Anual_R$': r['economia_ano'],
            'Economia_Adicional_BESS_R$': r['economia_adicional_ano'],
            'Taxa_Sucesso_%': r['taxa_sucesso_pct'],
            'Ciclos_Mês': r['ciclos_mes']
        }
        for r in resultados
    ])
    
    df_resultados.to_csv('analise_bess_reducao_demanda_resultados.csv', index=False)
    print(f"\n💾 Resultados detalhados salvos em: analise_bess_reducao_demanda_resultados.csv")
    
    print("\n" + "="*100)
    print(" "*40 + "ANÁLISE CONCLUÍDA")
    print("="*100)


if __name__ == '__main__':
    main()
