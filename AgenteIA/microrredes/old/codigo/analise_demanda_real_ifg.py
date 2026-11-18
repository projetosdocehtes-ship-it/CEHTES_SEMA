"""
Análise de otimização da demanda contratada para o IFG
Baseada em dados reais de medição de demanda ativa
Arquivo: dem_ativa_kw por datetime e ponto.csv
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime

class AnalisadorDemandaReal:
    """Analisa demanda contratada usando dados reais de medição"""
    
    def __init__(self, arquivo_demanda='dem_ativa_kw por datetime e ponto.csv'):
        self.arquivo = arquivo_demanda
        self.demanda_atual_kw = 350  # Demanda contratada atual
        self.tarifa_demanda = 26.08  # R$/kW - Verde EQUATORIAL GO
        self.df_demanda = None
        
    def carregar_dados(self):
        """Carrega e processa dados de demanda"""
        print("\n📊 Carregando dados de demanda...")
        
        # Carregar CSV
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
            (self.df_demanda['dia_semana'] < 5)  # Segunda a sexta
        )
        
        print(f"✓ Dados carregados: {len(self.df_demanda)} registros")
        print(f"  Período: {self.df_demanda['datetime'].min()} a {self.df_demanda['datetime'].max()}")
        print(f"  Intervalo: {(self.df_demanda['datetime'].iloc[1] - self.df_demanda['datetime'].iloc[0]).total_seconds()/60:.0f} minutos")
        
    def analisar_demanda(self):
        """Analisa estatísticas de demanda"""
        print("\n" + "="*100)
        print(" "*30 + "ANÁLISE DE DEMANDA CONTRATADA - IFG")
        print(" "*25 + f"Demanda Atual Contratada: {self.demanda_atual_kw} kW")
        print("="*100)
        
        # Estatísticas gerais
        dem_max = self.df_demanda['dem_ativa_kw'].max()
        dem_min = self.df_demanda['dem_ativa_kw'].min()
        dem_media = self.df_demanda['dem_ativa_kw'].mean()
        dem_p50 = self.df_demanda['dem_ativa_kw'].quantile(0.50)
        dem_p90 = self.df_demanda['dem_ativa_kw'].quantile(0.90)
        dem_p95 = self.df_demanda['dem_ativa_kw'].quantile(0.95)
        dem_p99 = self.df_demanda['dem_ativa_kw'].quantile(0.99)
        dem_p999 = self.df_demanda['dem_ativa_kw'].quantile(0.999)
        
        print(f"\n📈 ESTATÍSTICAS DE DEMANDA:")
        print("-"*100)
        print(f"  Demanda Máxima:             {dem_max:>6.1f} kW")
        print(f"  Demanda Média:              {dem_media:>6.1f} kW")
        print(f"  Demanda Mediana (P50):      {dem_p50:>6.1f} kW")
        print(f"  Demanda P90 (10% acima):    {dem_p90:>6.1f} kW")
        print(f"  Demanda P95 (5% acima):     {dem_p95:>6.1f} kW")
        print(f"  Demanda P99 (1% acima):     {dem_p99:>6.1f} kW")
        print(f"  Demanda P99.9 (0.1% acima): {dem_p999:>6.1f} kW")
        print(f"  Demanda Mínima:             {dem_min:>6.1f} kW")
        
        # Análise por período (ponta vs fora ponta)
        dem_ponta = self.df_demanda[self.df_demanda['is_ponta']]['dem_ativa_kw']
        dem_fora_ponta = self.df_demanda[~self.df_demanda['is_ponta']]['dem_ativa_kw']
        
        print(f"\n⚡ DEMANDA POR PERÍODO:")
        print("-"*100)
        print(f"  PONTA (18h-21h dias úteis):")
        print(f"    Máxima:    {dem_ponta.max():>6.1f} kW")
        print(f"    Média:     {dem_ponta.mean():>6.1f} kW")
        print(f"    P95:       {dem_ponta.quantile(0.95):>6.1f} kW")
        print(f"\n  FORA PONTA:")
        print(f"    Máxima:    {dem_fora_ponta.max():>6.1f} kW")
        print(f"    Média:     {dem_fora_ponta.mean():>6.1f} kW")
        print(f"    P95:       {dem_fora_ponta.quantile(0.95):>6.1f} kW")
        
        # Demanda máxima por dia
        dem_max_dia = self.df_demanda.groupby('dia')['dem_ativa_kw'].max()
        
        print(f"\n📅 DEMANDA MÁXIMA DIÁRIA:")
        print("-"*100)
        print(f"  Maior demanda diária:       {dem_max_dia.max():>6.1f} kW")
        print(f"  Média das máximas diárias:  {dem_max_dia.mean():>6.1f} kW")
        print(f"  P95 das máximas diárias:    {dem_max_dia.quantile(0.95):>6.1f} kW")
        print(f"  Menor demanda diária:       {dem_max_dia.min():>6.1f} kW")
        
        # Opções de contratação
        print(f"\n💡 OPÇÕES DE DEMANDA CONTRATADA:")
        print("-"*100)
        
        opcoes = {
            'Conservadora (Máxima absoluta)': dem_max,
            'Muito Segura (P99.9 + 5%)': dem_p999 * 1.05,
            'Segura (P99 + 5%)': dem_p99 * 1.05,
            'Balanceada (P95 + 10%)': dem_p95 * 1.10,
            'Otimizada (P90 + 15%)': dem_p90 * 1.15,
        }
        
        for nome, valor in opcoes.items():
            reducao = self.demanda_atual_kw - valor
            reducao_pct = (reducao / self.demanda_atual_kw) * 100
            economia_mes = reducao * self.tarifa_demanda
            economia_ano = economia_mes * 12
            
            # Calcular risco (% de horas acima)
            horas_acima = (self.df_demanda['dem_ativa_kw'] > valor).sum()
            risco_pct = (horas_acima / len(self.df_demanda)) * 100
            
            print(f"\n  {nome}:")
            print(f"    Contratar:     {valor:>6.1f} kW")
            print(f"    Redução:       {reducao:>6.1f} kW ({reducao_pct:>5.1f}%)")
            print(f"    Economia/mês:  R$ {economia_mes:>8,.2f}")
            print(f"    Economia/ano:  R$ {economia_ano:>9,.2f}")
            print(f"    Risco:         {risco_pct:>5.2f}% das medições acima ({horas_acima} de {len(self.df_demanda)} registros)")
        
        # Análise de ultrapassagem
        print(f"\n⚠️  ANÁLISE DE ULTRAPASSAGEM:")
        print("-"*100)
        print(f"  Demanda atual contratada: {self.demanda_atual_kw} kW")
        ultrapassagens = self.df_demanda[self.df_demanda['dem_ativa_kw'] > self.demanda_atual_kw]
        print(f"  Ultrapassagens registradas: {len(ultrapassagens)} ({len(ultrapassagens)/len(self.df_demanda)*100:.2f}%)")
        if len(ultrapassagens) > 0:
            print(f"  Demanda máxima ultrapassada: {ultrapassagens['dem_ativa_kw'].max():.1f} kW")
            print(f"  Média das ultrapassagens: {ultrapassagens['dem_ativa_kw'].mean():.1f} kW")
        else:
            print(f"  ✓ Nenhuma ultrapassagem - demanda bem dimensionada ou superdimensionada")
        
        return opcoes
    
    def analisar_padroes_horarios(self):
        """Analisa padrões de demanda por hora do dia"""
        print(f"\n\n⏰ PADRÃO DE DEMANDA POR HORA DO DIA:")
        print("-"*100)
        
        # Agrupar por hora
        dem_por_hora = self.df_demanda.groupby('hora')['dem_ativa_kw'].agg([
            ('max', 'max'),
            ('media', 'mean'),
            ('p95', lambda x: x.quantile(0.95)),
            ('p50', lambda x: x.quantile(0.50)),
            ('min', 'min')
        ])
        
        print("\nHora | Máx   | P95   | Média | P50   | Mín   | Período")
        print("-"*70)
        for hora in range(24):
            if hora in dem_por_hora.index:
                row = dem_por_hora.loc[hora]
                periodo = "PONTA" if 18 <= hora < 21 else "fora ponta"
                print(f"{hora:02d}h  | {row['max']:>5.0f} | {row['p95']:>5.0f} | {row['media']:>5.0f} | {row['p50']:>5.0f} | {row['min']:>5.0f} | {periodo}")
        
        return dem_por_hora
    
    def analisar_sazonalidade(self):
        """Analisa variação de demanda por mês/semana"""
        print(f"\n\n📆 ANÁLISE DE SAZONALIDADE:")
        print("-"*100)
        
        # Por mês
        dem_por_mes = self.df_demanda.groupby('mes')['dem_ativa_kw'].agg([
            ('max', 'max'),
            ('media', 'mean'),
            ('p95', lambda x: x.quantile(0.95))
        ])
        
        meses = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']
        print("\nMês    | Máxima | P95   | Média")
        print("-"*40)
        for mes in dem_por_mes.index:
            row = dem_por_mes.loc[mes]
            print(f"{meses[mes-1]:6s} | {row['max']:>6.0f} | {row['p95']:>5.0f} | {row['media']:>5.0f}")
        
        return dem_por_mes
    
    def gerar_graficos(self, dem_por_hora):
        """Gera gráficos de análise"""
        fig = plt.figure(figsize=(20, 12))
        
        # Gráfico 1: Curva de duração de carga
        ax1 = plt.subplot(2, 3, 1)
        demandas_ordenadas = np.sort(self.df_demanda['dem_ativa_kw'].values)[::-1]
        percentis = np.arange(len(demandas_ordenadas)) / len(demandas_ordenadas) * 100
        
        ax1.plot(percentis, demandas_ordenadas, linewidth=2, color='#2E86AB')
        ax1.axhline(y=self.demanda_atual_kw, color='red', linestyle='--', 
                   label=f'Contratada atual ({self.demanda_atual_kw} kW)', linewidth=2)
        ax1.axhline(y=self.df_demanda['dem_ativa_kw'].quantile(0.95)*1.1, 
                   color='green', linestyle='--', 
                   label=f'Sugestão P95+10% ({self.df_demanda["dem_ativa_kw"].quantile(0.95)*1.1:.0f} kW)', 
                   linewidth=2)
        
        ax1.set_xlabel('Percentual do Tempo (%)', fontsize=11)
        ax1.set_ylabel('Demanda (kW)', fontsize=11)
        ax1.set_title('Curva de Duração de Carga', fontweight='bold', fontsize=12)
        ax1.legend(fontsize=9)
        ax1.grid(True, alpha=0.3)
        ax1.set_xlim(0, 100)
        
        # Gráfico 2: Histograma de demanda
        ax2 = plt.subplot(2, 3, 2)
        ax2.hist(self.df_demanda['dem_ativa_kw'], bins=50, color='#A23B72', alpha=0.7, edgecolor='black')
        ax2.axvline(x=self.demanda_atual_kw, color='red', linestyle='--', 
                   label=f'Contratada ({self.demanda_atual_kw} kW)', linewidth=2)
        ax2.axvline(x=self.df_demanda['dem_ativa_kw'].mean(), color='blue', linestyle='--', 
                   label=f'Média ({self.df_demanda["dem_ativa_kw"].mean():.0f} kW)', linewidth=2)
        
        ax2.set_xlabel('Demanda (kW)', fontsize=11)
        ax2.set_ylabel('Frequência', fontsize=11)
        ax2.set_title('Distribuição de Demanda', fontweight='bold', fontsize=12)
        ax2.legend(fontsize=9)
        ax2.grid(True, alpha=0.3, axis='y')
        
        # Gráfico 3: Perfil horário médio
        ax3 = plt.subplot(2, 3, 3)
        
        ax3.plot(dem_por_hora.index, dem_por_hora['max'], 'o-', label='Máxima', 
                linewidth=2, markersize=6, color='red')
        ax3.plot(dem_por_hora.index, dem_por_hora['p95'], 's-', label='P95', 
                linewidth=2, markersize=5, color='orange')
        ax3.plot(dem_por_hora.index, dem_por_hora['media'], '^-', label='Média', 
                linewidth=2, markersize=5, color='blue')
        ax3.axhspan(18, 21, alpha=0.2, color='yellow', label='Horário Ponta')
        
        ax3.set_xlabel('Hora do Dia', fontsize=11)
        ax3.set_ylabel('Demanda (kW)', fontsize=11)
        ax3.set_title('Perfil de Demanda por Hora', fontweight='bold', fontsize=12)
        ax3.legend(fontsize=9)
        ax3.grid(True, alpha=0.3)
        ax3.set_xticks(range(0, 24, 2))
        
        # Gráfico 4: Box plot por hora
        ax4 = plt.subplot(2, 3, 4)
        
        horas_unicas = sorted(self.df_demanda['hora'].unique())
        dados_box = [self.df_demanda[self.df_demanda['hora'] == h]['dem_ativa_kw'].values 
                     for h in horas_unicas]
        
        bp = ax4.boxplot(dados_box, positions=horas_unicas, widths=0.6, patch_artist=True)
        
        for patch in bp['boxes']:
            patch.set_facecolor('#F18F01')
            patch.set_alpha(0.7)
        
        # Destacar horário de ponta
        for i, hora in enumerate(horas_unicas):
            if 18 <= hora < 21:
                bp['boxes'][i].set_facecolor('red')
        
        ax4.set_xlabel('Hora do Dia', fontsize=11)
        ax4.set_ylabel('Demanda (kW)', fontsize=11)
        ax4.set_title('Variabilidade de Demanda por Hora', fontweight='bold', fontsize=12)
        ax4.grid(True, alpha=0.3, axis='y')
        ax4.set_xticks(range(0, 24, 2))
        
        # Gráfico 5: Série temporal (primeiros dias)
        ax5 = plt.subplot(2, 3, 5)
        
        # Plotar primeiros 7 dias
        dias_plot = 7
        df_plot = self.df_demanda[self.df_demanda['dia'] <= self.df_demanda['dia'].unique()[dias_plot-1]]
        
        ax5.plot(df_plot['datetime'], df_plot['dem_ativa_kw'], linewidth=1, color='#06A77D')
        ax5.axhline(y=self.demanda_atual_kw, color='red', linestyle='--', 
                   label=f'Contratada ({self.demanda_atual_kw} kW)', linewidth=2)
        
        ax5.set_xlabel('Data/Hora', fontsize=11)
        ax5.set_ylabel('Demanda (kW)', fontsize=11)
        ax5.set_title(f'Série Temporal - Primeiros {dias_plot} Dias', fontweight='bold', fontsize=12)
        ax5.legend(fontsize=9)
        ax5.grid(True, alpha=0.3)
        plt.setp(ax5.xaxis.get_majorticklabels(), rotation=45, ha='right')
        
        # Gráfico 6: Economia por nível de contratação
        ax6 = plt.subplot(2, 3, 6)
        
        niveis = np.arange(100, 351, 10)
        economias = []
        riscos = []
        
        for nivel in niveis:
            reducao = self.demanda_atual_kw - nivel
            economia_ano = reducao * self.tarifa_demanda * 12
            economias.append(economia_ano)
            
            risco = (self.df_demanda['dem_ativa_kw'] > nivel).sum() / len(self.df_demanda) * 100
            riscos.append(risco)
        
        color = 'tab:blue'
        ax6.set_xlabel('Demanda Contratada (kW)', fontsize=11)
        ax6.set_ylabel('Economia Anual (R$)', color=color, fontsize=11)
        ax6.bar(niveis, economias, width=8, color=color, alpha=0.7, label='Economia')
        ax6.tick_params(axis='y', labelcolor=color)
        ax6.grid(True, alpha=0.3, axis='y')
        
        ax6_twin = ax6.twinx()
        color = 'tab:red'
        ax6_twin.set_ylabel('Risco de Ultrapassagem (%)', color=color, fontsize=11)
        ax6_twin.plot(niveis, riscos, color=color, linewidth=2, marker='o', 
                     markersize=4, label='Risco')
        ax6_twin.tick_params(axis='y', labelcolor=color)
        
        ax6.set_title('Economia vs Risco', fontweight='bold', fontsize=12)
        ax6.axvline(x=self.demanda_atual_kw, color='green', linestyle='--', 
                   linewidth=2, alpha=0.7)
        
        plt.tight_layout()
        
        filename = 'analise_demanda_real_ifg.png'
        plt.savefig(filename, dpi=150, bbox_inches='tight')
        print(f"\n📊 Gráficos salvos em: {filename}")
        plt.close()
    
    def gerar_relatorio_completo(self):
        """Gera relatório completo em texto"""
        print("\n\n" + "="*100)
        print(" "*35 + "RESUMO E RECOMENDAÇÕES")
        print("="*100)
        
        dem_p95 = self.df_demanda['dem_ativa_kw'].quantile(0.95)
        dem_p99 = self.df_demanda['dem_ativa_kw'].quantile(0.99)
        
        # Recomendação principal
        dem_recomendada = dem_p95 * 1.10  # P95 + 10% margem
        reducao = self.demanda_atual_kw - dem_recomendada
        economia_ano = reducao * self.tarifa_demanda * 12
        risco = (self.df_demanda['dem_ativa_kw'] > dem_recomendada).sum() / len(self.df_demanda) * 100
        
        print(f"\n⭐ RECOMENDAÇÃO PRINCIPAL:")
        print("-"*100)
        print(f"\n  Contratar: {dem_recomendada:.0f} kW (opção balanceada P95 + 10%)")
        print(f"  Atual:     {self.demanda_atual_kw} kW")
        print(f"  Redução:   {reducao:.0f} kW ({reducao/self.demanda_atual_kw*100:.1f}%)")
        print(f"\n  💰 ECONOMIA:")
        print(f"    Mensal:  R$ {reducao * self.tarifa_demanda:,.2f}")
        print(f"    Anual:   R$ {economia_ano:,.2f}")
        print(f"\n  ⚠️  RISCO:")
        print(f"    {risco:.2f}% de probabilidade de ultrapassagem")
        print(f"    Aproximadamente {risco * 730 / 100:.0f} horas/mês acima da demanda contratada")
        
        # Alternativas
        print(f"\n\n💡 ALTERNATIVAS:")
        print("-"*100)
        
        # Opção conservadora
        dem_conservadora = dem_p99 * 1.05
        reducao_cons = self.demanda_atual_kw - dem_conservadora
        economia_cons = reducao_cons * self.tarifa_demanda * 12
        risco_cons = (self.df_demanda['dem_ativa_kw'] > dem_conservadora).sum() / len(self.df_demanda) * 100
        
        print(f"\n  Opção SEGURA (P99 + 5%):")
        print(f"    Contratar: {dem_conservadora:.0f} kW")
        print(f"    Redução:   {reducao_cons:.0f} kW")
        print(f"    Economia:  R$ {economia_cons:,.2f}/ano")
        print(f"    Risco:     {risco_cons:.2f}%")
        
        # Opção otimizada
        dem_otimizada = self.df_demanda['dem_ativa_kw'].quantile(0.90) * 1.15
        reducao_oti = self.demanda_atual_kw - dem_otimizada
        economia_oti = reducao_oti * self.tarifa_demanda * 12
        risco_oti = (self.df_demanda['dem_ativa_kw'] > dem_otimizada).sum() / len(self.df_demanda) * 100
        
        print(f"\n  Opção OTIMIZADA (P90 + 15%):")
        print(f"    Contratar: {dem_otimizada:.0f} kW")
        print(f"    Redução:   {reducao_oti:.0f} kW")
        print(f"    Economia:  R$ {economia_oti:,.2f}/ano")
        print(f"    Risco:     {risco_oti:.2f}%")
        
        print(f"\n\n📋 PRÓXIMOS PASSOS:")
        print("-"*100)
        print(f"  1. Validar análise com histórico de faturas (verificar ultrapassagens anteriores)")
        print(f"  2. Analisar impacto de penalidades por ultrapassagem vs economia da redução")
        print(f"  3. Solicitar mudança de demanda contratada à EQUATORIAL GO")
        print(f"  4. Monitorar demanda nos primeiros meses após redução")
        print(f"  5. Considerar sistemas de gestão de demanda para evitar ultrapassagens")


def main():
    """Executa análise completa"""
    print("\n" + "="*100)
    print(" "*20 + "ANÁLISE DE OTIMIZAÇÃO DE DEMANDA CONTRATADA - INSTITUTO FEDERAL DE GOIÁS")
    print("="*100)
    
    analisador = AnalisadorDemandaReal()
    analisador.carregar_dados()
    
    # Análises
    opcoes = analisador.analisar_demanda()
    dem_por_hora = analisador.analisar_padroes_horarios()
    analisador.analisar_sazonalidade()
    
    # Gráficos
    analisador.gerar_graficos(dem_por_hora)
    
    # Relatório final
    analisador.gerar_relatorio_completo()
    
    # Salvar resumo em CSV
    resumo = []
    for nome, valor in opcoes.items():
        reducao = analisador.demanda_atual_kw - valor
        economia_ano = reducao * analisador.tarifa_demanda * 12
        risco = (analisador.df_demanda['dem_ativa_kw'] > valor).sum() / len(analisador.df_demanda) * 100
        
        resumo.append({
            'Opção': nome,
            'Demanda_Contratada_kW': valor,
            'Redução_kW': reducao,
            'Redução_%': reducao / analisador.demanda_atual_kw * 100,
            'Economia_Anual_R$': economia_ano,
            'Risco_Ultrapassagem_%': risco
        })
    
    df_resumo = pd.DataFrame(resumo)
    df_resumo.to_csv('analise_demanda_opcoes.csv', index=False)
    print(f"\n💾 Resumo salvo em: analise_demanda_opcoes.csv")
    
    print("\n" + "="*100)
    print(" "*40 + "ANÁLISE CONCLUÍDA")
    print("="*100)


if __name__ == '__main__':
    main()
