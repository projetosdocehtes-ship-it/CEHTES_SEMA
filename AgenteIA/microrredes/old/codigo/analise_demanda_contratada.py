"""
Análise de otimização da demanda contratada para o IFG
Considera a curva real de demanda e os 4 cenários de geração
Modalidade Verde: demanda única (sem ponta/fora ponta)
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from caso_ifg import CasoIFG
from tarifas_aneel import TarifasANEEL

class AnalisadorDemandaContratada:
    """Analisa otimização da demanda contratada considerando PV e BESS"""
    
    def __init__(self):
        self.demanda_atual_kw = 350  # Demanda atual contratada
        self.modalidade = 'verde'
        self.distribuidora = 'EQUATORIAL GO'
        self.tarifas = None
        self.resultados = {}
        
    def carregar_tarifas(self):
        """Carrega tarifas da ANEEL"""
        print("\n📊 Carregando tarifas da EQUATORIAL GO...")
        self.tarifas = TarifasANEEL(distribuidora=self.distribuidora, grupo='A4')
        
        # Tarifa de demanda Verde (modalidade única)
        # Verde tem TUSD de demanda única, sem diferenciação ponta/fora ponta
        self.tarifa_demanda = self.tarifas.dados_tarifa['verde']['tusd_demanda']
        print(f"✓ Tarifa de demanda (Verde): R$ {self.tarifa_demanda:.2f}/kW")
        
    def analisar_demanda_necessaria(self, nome_cenario, pv_kwp, bess_kwh):
        """
        Analisa a demanda necessária considerando PV e BESS
        Demanda líquida = Demanda Consumo - Geração PV + Carga BESS
        """
        print(f"\n{'='*90}")
        print(f"Analisando: {nome_cenario}")
        print(f"  PV: {pv_kwp} kWp | BESS: {bess_kwh} kWh")
        print(f"{'='*90}")
        
        # Usar CasoIFG para simular e obter demanda líquida hora a hora
        caso = CasoIFG(distribuidora=self.distribuidora, modalidade=self.modalidade)
        caso.pv_potencia_kwp = pv_kwp
        caso.bess_capacidade_kwh = bess_kwh
        caso.usar_diesel = False
        caso._configurar_pv()
        
        # Simular mês e coletar dados horários
        # Carregar perfil de carga para análise detalhada
        df_carga = pd.read_csv('perfil_carga_ifg.csv')
        
        # Arrays para armazenar resultados horários
        demandas_liquidas = []
        demandas_liquidas_ponta = []
        demandas_liquidas_fora_ponta = []
        horas_do_dia = []
        
        # Simular cada hora e calcular demanda líquida
        for idx, row in df_carga.iterrows():
            hora = row['hora']
            demanda_consumo_kw = row['demanda_kw']
            # Determinar se é ponta (18h-21h em dias úteis)
            is_ponta = (18 <= hora < 21) and (row.get('dia_semana', 'util') == 'util')
            
            # Geração PV estimada (padrão sinusoidal durante o dia)
            if 6 <= hora <= 18:
                # Pico ao meio-dia (hora 12)
                fator_solar = np.sin((hora - 6) / 12 * np.pi)  # 0 a 1 a 0
                geracao_pv_kw = pv_kwp * fator_solar * 0.85  # 85% de eficiência média
            else:
                geracao_pv_kw = 0
            
            # Demanda líquida base
            demanda_liquida_kw = demanda_consumo_kw - geracao_pv_kw
            
            # Ajustar com BESS se presente
            if bess_kwh > 0:
                # BESS configurado no caso com potência típica de 0.46 C-rate
                potencia_bess_kw = min(230, bess_kwh * 0.46)
                
                # Durante ponta sem sol, BESS descarrega reduzindo demanda
                if is_ponta and geracao_pv_kw < 10:
                    # BESS descarrega na ponta
                    potencia_descarga = min(potencia_bess_kw, demanda_liquida_kw)
                    demanda_liquida_kw = max(0, demanda_liquida_kw - potencia_descarga)
            
            demanda_liquida_kw = max(0, demanda_liquida_kw)
            demandas_liquidas.append(demanda_liquida_kw)
            horas_do_dia.append(hora)
            
            if is_ponta:
                demandas_liquidas_ponta.append(demanda_liquida_kw)
            else:
                demandas_liquidas_fora_ponta.append(demanda_liquida_kw)
        
        # Calcular demandas máximas
        demanda_maxima_geral = max(demandas_liquidas)
        demanda_maxima_ponta = max(demandas_liquidas_ponta) if demandas_liquidas_ponta else 0
        demanda_maxima_fora_ponta = max(demandas_liquidas_fora_ponta) if demandas_liquidas_fora_ponta else 0
        
        # Demanda média e percentis
        demanda_media = np.mean(demandas_liquidas)
        demanda_p95 = np.percentile(demandas_liquidas, 95)
        demanda_p99 = np.percentile(demandas_liquidas, 99)
        
        # Opções de contratação (com margem de segurança)
        opcoes_contratacao = {
            'maxima': demanda_maxima_geral,
            'p99_segura': demanda_p99 * 1.05,  # 5% margem
            'p95_segura': demanda_p95 * 1.10,  # 10% margem
            'p99': demanda_p99,
            'p95': demanda_p95
        }
        
        # Redução vs demanda atual
        reducao_maxima = self.demanda_atual_kw - demanda_maxima_geral
        reducao_p99 = self.demanda_atual_kw - opcoes_contratacao['p99_segura']
        reducao_p95 = self.demanda_atual_kw - opcoes_contratacao['p95_segura']
        
        # Economia mensal
        economia_maxima_mensal = reducao_maxima * self.tarifa_demanda
        economia_p99_mensal = reducao_p99 * self.tarifa_demanda
        economia_p95_mensal = reducao_p95 * self.tarifa_demanda
        
        # Risco de ultrapassagem
        horas_acima_p99 = sum(1 for d in demandas_liquidas if d > opcoes_contratacao['p99_segura'])
        horas_acima_p95 = sum(1 for d in demandas_liquidas if d > opcoes_contratacao['p95_segura'])
        
        self.resultados[nome_cenario] = {
            'pv_kwp': pv_kwp,
            'bess_kwh': bess_kwh,
            'demanda_atual': self.demanda_atual_kw,
            'demanda_maxima': demanda_maxima_geral,
            'demanda_maxima_ponta': demanda_maxima_ponta,
            'demanda_maxima_fora_ponta': demanda_maxima_fora_ponta,
            'demanda_media': demanda_media,
            'demanda_p95': demanda_p95,
            'demanda_p99': demanda_p99,
            'opcoes_contratacao': opcoes_contratacao,
            'reducao_maxima': reducao_maxima,
            'reducao_p99': reducao_p99,
            'reducao_p95': reducao_p95,
            'economia_maxima_mensal': economia_maxima_mensal,
            'economia_p99_mensal': economia_p99_mensal,
            'economia_p95_mensal': economia_p95_mensal,
            'horas_acima_p99': horas_acima_p99,
            'horas_acima_p95': horas_acima_p95,
            'demandas_liquidas': demandas_liquidas,
            'horas': horas_do_dia
        }
        
        # Imprimir resultados
        print(f"\n📊 ANÁLISE DE DEMANDA LÍQUIDA:")
        print(f"  Demanda Contratada Atual:   {self.demanda_atual_kw:>6.0f} kW")
        print(f"  Demanda Máxima Líquida:     {demanda_maxima_geral:>6.1f} kW")
        print(f"  Demanda Média Líquida:      {demanda_media:>6.1f} kW")
        print(f"  Demanda P99 (1% risco):     {demanda_p99:>6.1f} kW")
        print(f"  Demanda P95 (5% risco):     {demanda_p95:>6.1f} kW")
        
        print(f"\n💡 OPÇÕES DE REDUÇÃO:")
        print(f"  Conservadora (máxima):      {demanda_maxima_geral:>6.1f} kW → Redução: {reducao_maxima:>6.1f} kW ({reducao_maxima/self.demanda_atual_kw*100:>5.1f}%)")
        print(f"  Segura (P99 + 5%):          {opcoes_contratacao['p99_segura']:>6.1f} kW → Redução: {reducao_p99:>6.1f} kW ({reducao_p99/self.demanda_atual_kw*100:>5.1f}%)")
        print(f"  Otimizada (P95 + 10%):      {opcoes_contratacao['p95_segura']:>6.1f} kW → Redução: {reducao_p95:>6.1f} kW ({reducao_p95/self.demanda_atual_kw*100:>5.1f}%)")
        
        print(f"\n💰 ECONOMIA MENSAL (Tarifa: R$ {self.tarifa_demanda:.2f}/kW):")
        print(f"  Conservadora (máxima):      R$ {economia_maxima_mensal:>8,.2f}/mês  (R$ {economia_maxima_mensal*12:>10,.2f}/ano)")
        print(f"  Segura (P99 + 5%):          R$ {economia_p99_mensal:>8,.2f}/mês  (R$ {economia_p99_mensal*12:>10,.2f}/ano)")
        print(f"  Otimizada (P95 + 10%):      R$ {economia_p95_mensal:>8,.2f}/mês  (R$ {economia_p95_mensal*12:>10,.2f}/ano)")
        
        print(f"\n⚠️  RISCO DE ULTRAPASSAGEM:")
        print(f"  P99 + 5% ({opcoes_contratacao['p99_segura']:.1f} kW):  {horas_acima_p99} horas/mês ({horas_acima_p99/len(demandas_liquidas)*100:.2f}%)")
        print(f"  P95 + 10% ({opcoes_contratacao['p95_segura']:.1f} kW): {horas_acima_p95} horas/mês ({horas_acima_p95/len(demandas_liquidas)*100:.2f}%)")
        
        return self.resultados[nome_cenario]
    
    def gerar_relatorio_comparativo(self):
        """Gera relatório comparando todos os cenários"""
        print("\n\n" + "="*100)
        print(" "*25 + "COMPARAÇÃO DE DEMANDA CONTRATADA - TODOS OS CENÁRIOS")
        print("="*100)
        
        # Tabela comparativa
        print(f"\n📊 REDUÇÃO DE DEMANDA POR CENÁRIO (Base: {self.demanda_atual_kw} kW)")
        print("-"*100)
        print(f"{'Cenário':<35} {'Dem. Máx':<12} {'Opção P99+5%':<14} {'Redução':<12} {'Economia/mês':<15} {'Economia/ano'}")
        print("-"*100)
        
        for nome, res in self.resultados.items():
            dem_max = res['demanda_maxima']
            dem_p99 = res['opcoes_contratacao']['p99_segura']
            reducao = res['reducao_p99']
            economia_mes = res['economia_p99_mensal']
            economia_ano = economia_mes * 12
            
            print(f"{nome:<35} {dem_max:>6.1f} kW    {dem_p99:>6.1f} kW      {reducao:>6.1f} kW   R$ {economia_mes:>9,.2f}   R$ {economia_ano:>11,.2f}")
        
        print("-"*100)
        
        # Análise do impacto incremental
        print(f"\n\n💡 ANÁLISE INCREMENTAL:")
        print("-"*100)
        
        base = self.resultados.get('Base (PV 254 kWp)', {})
        cen1 = self.resultados.get('Cenário 1 (PV 254 + BESS 500)', {})
        cen2 = self.resultados.get('Cenário 2 (PV 324 kWp)', {})
        cen3 = self.resultados.get('Cenário 3 (PV 324 + BESS 500)', {})
        
        if base and cen1:
            reducao_adicional = cen1['reducao_p99'] - base['reducao_p99']
            economia_adicional = reducao_adicional * self.tarifa_demanda * 12
            print(f"\nImpacto do BESS (Cenário 1 vs Base):")
            print(f"  Redução adicional de demanda: {reducao_adicional:>6.1f} kW")
            print(f"  Economia adicional:           R$ {economia_adicional:>10,.2f}/ano")
            print(f"  Investimento BESS:            R$ 950.000,00")
            print(f"  Payback (só demanda):         {950000/economia_adicional if economia_adicional > 0 else 999:.1f} anos")
        
        if base and cen2:
            reducao_adicional = cen2['reducao_p99'] - base['reducao_p99']
            economia_adicional = reducao_adicional * self.tarifa_demanda * 12
            print(f"\nImpacto da expansão PV (Cenário 2 vs Base):")
            print(f"  Redução adicional de demanda: {reducao_adicional:>6.1f} kW")
            print(f"  Economia adicional:           R$ {economia_adicional:>10,.2f}/ano")
            print(f"  Investimento PV adicional:    R$ 245.000,00")
            print(f"  Payback (só demanda):         {245000/economia_adicional if economia_adicional > 0 else 999:.1f} anos")
        
        if cen2 and cen3:
            reducao_adicional = cen3['reducao_p99'] - cen2['reducao_p99']
            economia_adicional = reducao_adicional * self.tarifa_demanda * 12
            print(f"\nImpacto do BESS em PV expandido (Cenário 3 vs Cenário 2):")
            print(f"  Redução adicional de demanda: {reducao_adicional:>6.1f} kW")
            print(f"  Economia adicional:           R$ {economia_adicional:>10,.2f}/ano")
            print(f"  Investimento BESS:            R$ 950.000,00")
            print(f"  Payback (só demanda):         {950000/economia_adicional if economia_adicional > 0 else 999:.1f} anos")
        
        # Recomendação
        print(f"\n\n⭐ RECOMENDAÇÃO:")
        print("-"*100)
        
        # Encontrar melhor cenário (maior economia)
        melhor_cenario = max(self.resultados.items(), 
                           key=lambda x: x[1]['economia_p99_mensal'])
        
        print(f"\nMelhor cenário: {melhor_cenario[0]}")
        print(f"  Demanda sugerida:    {melhor_cenario[1]['opcoes_contratacao']['p99_segura']:.0f} kW (P99 + 5% margem)")
        print(f"  Redução:             {melhor_cenario[1]['reducao_p99']:.0f} kW ({melhor_cenario[1]['reducao_p99']/self.demanda_atual_kw*100:.1f}%)")
        print(f"  Economia demanda:    R$ {melhor_cenario[1]['economia_p99_mensal']:,.2f}/mês")
        print(f"  Economia anual:      R$ {melhor_cenario[1]['economia_p99_mensal']*12:,.2f}/ano")
        print(f"  Risco ultrapassagem: {melhor_cenario[1]['horas_acima_p99']/len(melhor_cenario[1]['demandas_liquidas'])*100:.2f}% das horas")
    
    def gerar_graficos(self):
        """Gera gráficos de análise de demanda"""
        fig = plt.figure(figsize=(18, 10))
        
        nomes = list(self.resultados.keys())
        cores = ['gray', 'orange', 'blue', 'green']
        
        # Gráfico 1: Demandas contratuais
        ax1 = plt.subplot(2, 3, 1)
        
        dem_atual = [self.demanda_atual_kw] * len(nomes)
        dem_maximas = [r['demanda_maxima'] for r in self.resultados.values()]
        dem_p99 = [r['opcoes_contratacao']['p99_segura'] for r in self.resultados.values()]
        dem_p95 = [r['opcoes_contratacao']['p95_segura'] for r in self.resultados.values()]
        
        x = np.arange(len(nomes))
        width = 0.2
        
        ax1.bar(x - width*1.5, dem_atual, width, label='Atual (350 kW)', color='red', alpha=0.6)
        ax1.bar(x - width*0.5, dem_maximas, width, label='Máxima', color='darkred', alpha=0.7)
        ax1.bar(x + width*0.5, dem_p99, width, label='P99 + 5%', color='orange', alpha=0.8)
        ax1.bar(x + width*1.5, dem_p95, width, label='P95 + 10%', color='yellow', alpha=0.7)
        
        ax1.set_ylabel('Demanda (kW)')
        ax1.set_title('Opções de Demanda Contratada', fontweight='bold')
        ax1.set_xticks(x)
        ax1.set_xticklabels([n.split('(')[0].strip() for n in nomes], rotation=15, ha='right')
        ax1.legend()
        ax1.grid(True, alpha=0.3, axis='y')
        
        # Gráfico 2: Redução de demanda
        ax2 = plt.subplot(2, 3, 2)
        
        reducoes = [r['reducao_p99'] for r in self.resultados.values()]
        reducoes_pct = [r/self.demanda_atual_kw*100 for r in reducoes]
        
        bars = ax2.bar(range(len(nomes)), reducoes, color=cores)
        ax2.set_ylabel('Redução de Demanda (kW)')
        ax2.set_title('Redução vs Atual (350 kW)', fontweight='bold')
        ax2.set_xticks(range(len(nomes)))
        ax2.set_xticklabels([n.split('(')[0].strip() for n in nomes], rotation=15, ha='right')
        ax2.grid(True, alpha=0.3, axis='y')
        
        for i, (bar, red, pct) in enumerate(zip(bars, reducoes, reducoes_pct)):
            ax2.text(bar.get_x() + bar.get_width()/2., bar.get_height(),
                    f'{red:.0f} kW\n({pct:.1f}%)',
                    ha='center', va='bottom', fontsize=9)
        
        # Gráfico 3: Economia mensal
        ax3 = plt.subplot(2, 3, 3)
        
        economias = [r['economia_p99_mensal'] for r in self.resultados.values()]
        
        bars = ax3.bar(range(len(nomes)), economias, color=cores)
        ax3.set_ylabel('Economia Mensal (R$)')
        ax3.set_title('Economia na Tarifa de Demanda', fontweight='bold')
        ax3.set_xticks(range(len(nomes)))
        ax3.set_xticklabels([n.split('(')[0].strip() for n in nomes], rotation=15, ha='right')
        ax3.grid(True, alpha=0.3, axis='y')
        
        for bar, val in zip(bars, economias):
            ax3.text(bar.get_x() + bar.get_width()/2., val,
                    f'R$ {val:,.0f}',
                    ha='center', va='bottom', fontsize=9)
        
        # Gráfico 4: Curva de duração de demanda
        ax4 = plt.subplot(2, 3, 4)
        
        for i, (nome, res) in enumerate(self.resultados.items()):
            demandas_ordenadas = sorted(res['demandas_liquidas'], reverse=True)
            horas_pct = np.arange(len(demandas_ordenadas)) / len(demandas_ordenadas) * 100
            ax4.plot(horas_pct, demandas_ordenadas, label=nome.split('(')[0].strip(), 
                    color=cores[i], linewidth=2)
        
        ax4.axhline(y=self.demanda_atual_kw, color='red', linestyle='--', 
                   label='Atual (350 kW)', linewidth=2)
        ax4.set_xlabel('Percentual do Tempo (%)')
        ax4.set_ylabel('Demanda Líquida (kW)')
        ax4.set_title('Curva de Duração de Demanda', fontweight='bold')
        ax4.legend(loc='upper right', fontsize=8)
        ax4.grid(True, alpha=0.3)
        ax4.set_xlim(0, 100)
        
        # Gráfico 5: Distribuição de demanda (box plot)
        ax5 = plt.subplot(2, 3, 5)
        
        dados_box = [r['demandas_liquidas'] for r in self.resultados.values()]
        bp = ax5.boxplot(dados_box, labels=[n.split('(')[0].strip() for n in nomes],
                        patch_artist=True)
        
        for patch, cor in zip(bp['boxes'], cores):
            patch.set_facecolor(cor)
            patch.set_alpha(0.6)
        
        ax5.axhline(y=self.demanda_atual_kw, color='red', linestyle='--', 
                   label='Atual (350 kW)', linewidth=2)
        ax5.set_ylabel('Demanda Líquida (kW)')
        ax5.set_title('Distribuição de Demanda Líquida', fontweight='bold')
        ax5.set_xticklabels([n.split('(')[0].strip() for n in nomes], rotation=15, ha='right')
        ax5.legend()
        ax5.grid(True, alpha=0.3, axis='y')
        
        # Gráfico 6: Economia anual acumulada
        ax6 = plt.subplot(2, 3, 6)
        
        economias_anuais = [r['economia_p99_mensal'] * 12 for r in self.resultados.values()]
        
        bars = ax6.bar(range(len(nomes)), [e/1000 for e in economias_anuais], color=cores)
        ax6.set_ylabel('Economia Anual (R$ mil)')
        ax6.set_title('Economia Anual na Demanda', fontweight='bold')
        ax6.set_xticks(range(len(nomes)))
        ax6.set_xticklabels([n.split('(')[0].strip() for n in nomes], rotation=15, ha='right')
        ax6.grid(True, alpha=0.3, axis='y')
        
        for bar, val in zip(bars, economias_anuais):
            ax6.text(bar.get_x() + bar.get_width()/2., val/1000,
                    f'R$ {val/1000:.1f}k',
                    ha='center', va='bottom', fontsize=9)
        
        plt.tight_layout()
        
        filename = 'analise_demanda_contratada_ifg.png'
        plt.savefig(filename, dpi=150, bbox_inches='tight')
        print(f"\n📊 Gráficos salvos em: {filename}")
        plt.close()


def main():
    """Executa análise de demanda contratada"""
    print("\n" + "="*100)
    print(" "*20 + "ANÁLISE DE OTIMIZAÇÃO DE DEMANDA CONTRATADA - CASO IFG")
    print(" "*25 + "Demanda Atual: 350 kW | Modalidade: Verde")
    print("="*100)
    
    analisador = AnalisadorDemandaContratada()
    analisador.carregar_tarifas()
    
    # Analisar todos os cenários
    analisador.analisar_demanda_necessaria('Base (PV 254 kWp)', pv_kwp=254, bess_kwh=0)
    analisador.analisar_demanda_necessaria('Cenário 1 (PV 254 + BESS 500)', pv_kwp=254, bess_kwh=500)
    analisador.analisar_demanda_necessaria('Cenário 2 (PV 324 kWp)', pv_kwp=324, bess_kwh=0)
    analisador.analisar_demanda_necessaria('Cenário 3 (PV 324 + BESS 500)', pv_kwp=324, bess_kwh=500)
    
    # Relatório comparativo
    analisador.gerar_relatorio_comparativo()
    
    # Gráficos
    analisador.gerar_graficos()
    
    # Salvar dados
    dados_csv = []
    for nome, res in analisador.resultados.items():
        dados_csv.append({
            'Cenário': nome,
            'Demanda Atual (kW)': res['demanda_atual'],
            'Demanda Máxima (kW)': res['demanda_maxima'],
            'Demanda P99+5% (kW)': res['opcoes_contratacao']['p99_segura'],
            'Redução (kW)': res['reducao_p99'],
            'Redução (%)': res['reducao_p99'] / res['demanda_atual'] * 100,
            'Economia Mensal (R$)': res['economia_p99_mensal'],
            'Economia Anual (R$)': res['economia_p99_mensal'] * 12
        })
    
    df = pd.DataFrame(dados_csv)
    df.to_csv('analise_demanda_contratada_dados.csv', index=False)
    print(f"\n💾 Dados salvos em: analise_demanda_contratada_dados.csv")
    
    print("\n" + "="*100)
    print(" "*35 + "ANÁLISE CONCLUÍDA")
    print("="*100)


if __name__ == '__main__':
    main()
