"""
Análise detalhada do fluxo de potência nos cenários do IFG
Compara geração, consumo, exportação e uso de BESS
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from caso_ifg import CasoIFG
from tarifas_aneel import TarifasANEEL

class AnalisadorFluxoPotencia:
    """Analisa fluxo de potência em diferentes cenários"""
    
    def __init__(self):
        self.cenarios = {}
        self.distribuidora = 'EQUATORIAL GO'
        self.modalidade = 'verde'
        
    def simular_cenario(self, nome, pv_kwp, bess_kwh):
        """Simula um cenário e armazena resultados detalhados"""
        print(f"\n{'='*90}")
        print(f"Simulando: {nome}")
        print(f"{'='*90}")
        
        caso = CasoIFG(distribuidora=self.distribuidora, modalidade=self.modalidade)
        caso.pv_potencia_kwp = pv_kwp
        caso.bess_capacidade_kwh = bess_kwh
        caso.usar_diesel = False
        caso._configurar_pv()
        
        # Simular mês inteiro e coletar dados detalhados
        resultado_mensal = caso.simular_mes()
        
        # Calcular métricas adicionais
        demanda_total = resultado_mensal['energia_demanda_kwh']
        geracao_pv = resultado_mensal['energia_pv_kwh']
        compra_rede = resultado_mensal['energia_comprada_kwh']
        venda_rede = resultado_mensal['energia_vendida_kwh']
        
        # Energia que passou pelo BESS (carga + descarga)
        energia_bess = 0
        if bess_kwh > 0:
            # Estimativa: energia armazenada é a diferença entre geração e consumo instantâneo
            # que não foi exportada
            energia_bess = geracao_pv - venda_rede - (demanda_total - compra_rede)
            energia_bess = max(0, energia_bess)
        
        # Autossuficiência energética
        autossuficiencia = (geracao_pv / demanda_total * 100) if demanda_total > 0 else 0
        
        # Taxa de exportação (% da geração que foi exportada)
        taxa_exportacao = (venda_rede / geracao_pv * 100) if geracao_pv > 0 else 0
        
        # Aproveitamento da geração (% da geração que foi usada internamente)
        aproveitamento = 100 - taxa_exportacao
        
        # Energia da rede (líquida)
        energia_rede_liquida = compra_rede - venda_rede
        
        self.cenarios[nome] = {
            'pv_kwp': pv_kwp,
            'bess_kwh': bess_kwh,
            'demanda_total': demanda_total,
            'geracao_pv': geracao_pv,
            'compra_rede': compra_rede,
            'venda_rede': venda_rede,
            'energia_bess': energia_bess,
            'energia_rede_liquida': energia_rede_liquida,
            'autossuficiencia': autossuficiencia,
            'taxa_exportacao': taxa_exportacao,
            'aproveitamento': aproveitamento,
            'custo_mensal': resultado_mensal['custo_mensal'],
            'resultado_completo': resultado_mensal
        }
        
        # Imprimir resumo
        print(f"\n📊 BALANÇO ENERGÉTICO:")
        print(f"  Demanda Total:          {demanda_total:>10,.0f} kWh/mês")
        print(f"  Geração PV:             {geracao_pv:>10,.0f} kWh/mês ({autossuficiencia:.1f}% da demanda)")
        print(f"  Compra da Rede:         {compra_rede:>10,.0f} kWh/mês")
        print(f"  Venda para Rede:        {venda_rede:>10,.0f} kWh/mês ({taxa_exportacao:.1f}% da geração)")
        print(f"  Energia Rede Líquida:   {energia_rede_liquida:>10,.0f} kWh/mês")
        if bess_kwh > 0:
            print(f"  Energia pelo BESS:      {energia_bess:>10,.0f} kWh/mês (est.)")
        print(f"\n💡 APROVEITAMENTO:")
        print(f"  Geração Aproveitada:    {aproveitamento:>10.1f}% (uso interno + BESS)")
        print(f"  Geração Exportada:      {taxa_exportacao:>10.1f}% (vendida à rede)")
        print(f"\n💰 CUSTO:")
        print(f"  Custo Mensal:           R$ {resultado_mensal['custo_mensal']:>10,.2f}")
        
        return self.cenarios[nome]
    
    def gerar_relatorio_completo(self):
        """Gera relatório comparativo completo"""
        print("\n\n" + "="*100)
        print(" "*30 + "ANÁLISE DE FLUXO DE POTÊNCIA - TODOS OS CENÁRIOS")
        print("="*100)
        
        # Criar DataFrame comparativo
        dados = []
        for nome, cen in self.cenarios.items():
            dados.append({
                'Cenário': nome,
                'PV (kWp)': cen['pv_kwp'],
                'BESS (kWh)': cen['bess_kwh'],
                'Demanda (kWh)': cen['demanda_total'],
                'Geração PV (kWh)': cen['geracao_pv'],
                'Compra Rede (kWh)': cen['compra_rede'],
                'Venda Rede (kWh)': cen['venda_rede'],
                'Autossuf. (%)': cen['autossuficiencia'],
                'Export. (%)': cen['taxa_exportacao'],
                'Aproveit. (%)': cen['aproveitamento'],
                'Custo (R$)': cen['custo_mensal']
            })
        
        df = pd.DataFrame(dados)
        
        # Tabela principal
        print("\n📊 TABELA COMPARATIVA - BALANÇO ENERGÉTICO")
        print("-"*100)
        print(df.to_string(index=False))
        print("-"*100)
        
        # Análise de geração vs demanda
        print("\n\n⚡ ANÁLISE: GERAÇÃO FOTOVOLTAICA")
        print("-"*100)
        for nome, cen in self.cenarios.items():
            excesso = cen['geracao_pv'] - cen['demanda_total']
            relacao = (cen['geracao_pv'] / cen['demanda_total']) * 100
            print(f"\n{nome}:")
            print(f"  Geração: {cen['geracao_pv']:,.0f} kWh/mês ({relacao:.1f}% da demanda)")
            if excesso > 0:
                print(f"  Excesso: {excesso:,.0f} kWh/mês (necessita armazenamento ou exportação)")
            else:
                print(f"  Déficit: {-excesso:,.0f} kWh/mês (suprido pela rede)")
        
        # Análise de exportação
        print("\n\n📤 ANÁLISE: EXPORTAÇÃO DE ENERGIA")
        print("-"*100)
        print("A exportação representa energia PV não aproveitada internamente.")
        print("SCEE Verde compensa: Ponta 79,2% (R$ 1,70/kWh), Fora Ponta 41,8% (R$ 0,19/kWh)\n")
        
        for nome, cen in self.cenarios.items():
            if cen['venda_rede'] > 0:
                valor_exportacao = cen['venda_rede'] * 0.19  # Aproximação média
                print(f"{nome}:")
                print(f"  Exportação: {cen['venda_rede']:,.0f} kWh/mês ({cen['taxa_exportacao']:.1f}% da geração)")
                print(f"  Valor estimado: R$ {valor_exportacao:,.2f}/mês (~R$ 0,19/kWh médio)")
                print(f"  ⚠️  Perda vs consumo próprio: ~R$ {cen['venda_rede'] * (2.14 - 0.19):,.2f}/mês")
        
        # Análise de BESS
        print("\n\n🔋 ANÁLISE: IMPACTO DO BESS")
        print("-"*100)
        
        # Comparar cenários com e sem BESS
        base = self.cenarios.get('Base (PV 254 kWp)', {})
        com_bess = self.cenarios.get('Cenário 1 (PV 254 + BESS 500)', {})
        
        if base and com_bess:
            reducao_exportacao = base['venda_rede'] - com_bess['venda_rede']
            reducao_compra = base['compra_rede'] - com_bess['compra_rede']
            
            print(f"\nImpacto do BESS (Cenário 1 vs Base):")
            print(f"  Redução de exportação: {reducao_exportacao:,.0f} kWh/mês ({reducao_exportacao/base['venda_rede']*100:.1f}%)")
            print(f"  Aumento de compra: {-reducao_compra:,.0f} kWh/mês (para carregar BESS fora ponta)")
            print(f"  Estratégia: Carregar BESS com PV+rede fora ponta, descarregar na ponta")
            print(f"  Arbitragem: Evita compra a R$ 2,14/kWh (ponta) comprando a R$ 0,45/kWh (fora ponta)")
        
        # Comparar expansão PV com e sem BESS
        pv324 = self.cenarios.get('Cenário 2 (PV 324 kWp)', {})
        pv324_bess = self.cenarios.get('Cenário 3 (PV 324 + BESS 500)', {})
        
        if pv324 and pv324_bess:
            reducao_exportacao = pv324['venda_rede'] - pv324_bess['venda_rede']
            print(f"\nImpacto do BESS em PV expandido (Cenário 3 vs Cenário 2):")
            print(f"  Redução de exportação: {reducao_exportacao:,.0f} kWh/mês ({reducao_exportacao/pv324['venda_rede']*100:.1f}%)")
            print(f"  Valor recuperado: R$ {reducao_exportacao * (2.14 - 0.19):,.2f}/mês")
            print(f"  Conclusão: Com mais geração PV, BESS é AINDA MAIS importante")
        
        # Análise de eficiência
        print("\n\n📈 ANÁLISE: EFICIÊNCIA ENERGÉTICA")
        print("-"*100)
        for nome, cen in self.cenarios.items():
            eficiencia_uso_pv = (cen['geracao_pv'] - cen['venda_rede']) / cen['geracao_pv'] * 100 if cen['geracao_pv'] > 0 else 0
            dependencia_rede = cen['energia_rede_liquida'] / cen['demanda_total'] * 100
            
            print(f"\n{nome}:")
            print(f"  Aproveitamento de PV: {eficiencia_uso_pv:.1f}% (geração usada internamente)")
            print(f"  Dependência da rede: {dependencia_rede:.1f}% (energia líquida da rede)")
            print(f"  Autossuficiência:     {cen['autossuficiencia']:.1f}% (geração/demanda)")
        
        return df
    
    def gerar_graficos(self):
        """Gera gráficos de análise de fluxo"""
        fig = plt.figure(figsize=(18, 12))
        
        # Preparar dados
        nomes = list(self.cenarios.keys())
        cores = ['gray', 'orange', 'blue', 'green']
        
        # Gráfico 1: Balanço Energético (Sankey simplificado em barras)
        ax1 = plt.subplot(2, 3, 1)
        x = np.arange(len(nomes))
        width = 0.2
        
        demandas = [c['demanda_total'] for c in self.cenarios.values()]
        geracoes = [c['geracao_pv'] for c in self.cenarios.values()]
        compras = [c['compra_rede'] for c in self.cenarios.values()]
        vendas = [c['venda_rede'] for c in self.cenarios.values()]
        
        ax1.bar(x - width*1.5, demandas, width, label='Demanda', color='red', alpha=0.7)
        ax1.bar(x - width*0.5, geracoes, width, label='Geração PV', color='orange', alpha=0.7)
        ax1.bar(x + width*0.5, compras, width, label='Compra Rede', color='blue', alpha=0.7)
        ax1.bar(x + width*1.5, vendas, width, label='Venda Rede', color='green', alpha=0.7)
        
        ax1.set_ylabel('Energia (kWh/mês)')
        ax1.set_title('Balanço Energético Mensal', fontweight='bold')
        ax1.set_xticks(x)
        ax1.set_xticklabels([n.split('(')[0].strip() for n in nomes], rotation=15, ha='right')
        ax1.legend()
        ax1.grid(True, alpha=0.3, axis='y')
        
        # Gráfico 2: Autossuficiência e Aproveitamento
        ax2 = plt.subplot(2, 3, 2)
        autossuf = [c['autossuficiencia'] for c in self.cenarios.values()]
        aproveit = [c['aproveitamento'] for c in self.cenarios.values()]
        
        x = np.arange(len(nomes))
        width = 0.35
        
        bars1 = ax2.bar(x - width/2, autossuf, width, label='Autossuficiência', color='orange', alpha=0.8)
        bars2 = ax2.bar(x + width/2, aproveit, width, label='Aproveitamento PV', color='green', alpha=0.8)
        
        ax2.set_ylabel('Percentual (%)')
        ax2.set_title('Autossuficiência vs Aproveitamento', fontweight='bold')
        ax2.set_xticks(x)
        ax2.set_xticklabels([n.split('(')[0].strip() for n in nomes], rotation=15, ha='right')
        ax2.legend()
        ax2.grid(True, alpha=0.3, axis='y')
        ax2.set_ylim(0, 100)
        
        # Adicionar valores nas barras
        for bars in [bars1, bars2]:
            for bar in bars:
                height = bar.get_height()
                ax2.text(bar.get_x() + bar.get_width()/2., height,
                        f'{height:.1f}%', ha='center', va='bottom', fontsize=8)
        
        # Gráfico 3: Taxa de Exportação
        ax3 = plt.subplot(2, 3, 3)
        taxa_exp = [c['taxa_exportacao'] for c in self.cenarios.values()]
        
        bars = ax3.bar(range(len(nomes)), taxa_exp, color=cores)
        ax3.set_ylabel('Taxa de Exportação (%)')
        ax3.set_title('Energia Exportada (% da Geração PV)', fontweight='bold')
        ax3.set_xticks(range(len(nomes)))
        ax3.set_xticklabels([n.split('(')[0].strip() for n in nomes], rotation=15, ha='right')
        ax3.grid(True, alpha=0.3, axis='y')
        
        for i, bar in enumerate(bars):
            height = bar.get_height()
            ax3.text(bar.get_x() + bar.get_width()/2., height,
                    f'{height:.1f}%\n{vendas[i]:,.0f} kWh',
                    ha='center', va='bottom', fontsize=8)
        
        # Gráfico 4: Fluxo de Energia (origem vs destino)
        ax4 = plt.subplot(2, 3, 4)
        
        for i, (nome, cen) in enumerate(self.cenarios.items()):
            # Origem: Geração PV + Compra Rede
            origem_pv = cen['geracao_pv']
            origem_rede = cen['compra_rede']
            
            # Destino: Consumo + Venda
            consumo_interno = cen['demanda_total']
            
            ax4.barh(i, origem_pv, color='orange', alpha=0.7, label='Geração PV' if i == 0 else '')
            ax4.barh(i, origem_rede, left=origem_pv, color='blue', alpha=0.7, label='Compra Rede' if i == 0 else '')
            
            # Marcar exportação
            if cen['venda_rede'] > 0:
                ax4.barh(i, cen['venda_rede'], left=origem_pv + origem_rede, 
                        color='green', alpha=0.5, label='Exportação' if i == 0 else '')
        
        ax4.set_yticks(range(len(nomes)))
        ax4.set_yticklabels([n.split('(')[0].strip() for n in nomes])
        ax4.set_xlabel('Energia (kWh/mês)')
        ax4.set_title('Origem da Energia', fontweight='bold')
        ax4.legend(loc='lower right')
        ax4.grid(True, alpha=0.3, axis='x')
        
        # Gráfico 5: Impacto do BESS (comparações)
        ax5 = plt.subplot(2, 3, 5)
        
        # Comparar exportação com e sem BESS
        cenarios_ordem = list(self.cenarios.keys())
        exportacoes = [self.cenarios[c]['venda_rede'] for c in cenarios_ordem]
        
        colors_bess = []
        for nome in cenarios_ordem:
            if 'BESS' in nome:
                colors_bess.append('red')
            else:
                colors_bess.append('lightblue')
        
        bars = ax5.bar(range(len(cenarios_ordem)), exportacoes, color=colors_bess, alpha=0.7)
        ax5.set_ylabel('Energia Exportada (kWh/mês)')
        ax5.set_title('Impacto do BESS na Exportação', fontweight='bold')
        ax5.set_xticks(range(len(cenarios_ordem)))
        ax5.set_xticklabels([n.split('(')[0].strip() for n in cenarios_ordem], rotation=15, ha='right')
        ax5.grid(True, alpha=0.3, axis='y')
        
        for bar, val in zip(bars, exportacoes):
            if val > 0:
                ax5.text(bar.get_x() + bar.get_width()/2., val,
                        f'{val:,.0f}', ha='center', va='bottom', fontsize=9)
        
        # Gráfico 6: Custo Mensal
        ax6 = plt.subplot(2, 3, 6)
        custos = [c['custo_mensal'] for c in self.cenarios.values()]
        
        bars = ax6.bar(range(len(nomes)), [c/1000 for c in custos], color=cores)
        ax6.set_ylabel('Custo Mensal (R$ mil)')
        ax6.set_title('Custo de Energia Mensal', fontweight='bold')
        ax6.set_xticks(range(len(nomes)))
        ax6.set_xticklabels([n.split('(')[0].strip() for n in nomes], rotation=15, ha='right')
        ax6.grid(True, alpha=0.3, axis='y')
        
        for bar, val in zip(bars, custos):
            ax6.text(bar.get_x() + bar.get_width()/2., val/1000,
                    f'R$ {val/1000:.1f}k', ha='center', va='bottom', fontsize=9)
        
        plt.tight_layout()
        
        # Salvar
        filename = 'analise_fluxo_potencia_ifg.png'
        plt.savefig(filename, dpi=150, bbox_inches='tight')
        print(f"\n📊 Gráficos salvos em: {filename}")
        plt.close()


def main():
    """Executa análise completa de fluxo de potência"""
    print("\n" + "="*100)
    print(" "*25 + "ANÁLISE DE FLUXO DE POTÊNCIA - CASO IFG")
    print("="*100)
    
    analisador = AnalisadorFluxoPotencia()
    
    # Simular todos os 4 cenários
    analisador.simular_cenario('Base (PV 254 kWp)', pv_kwp=254, bess_kwh=0)
    analisador.simular_cenario('Cenário 1 (PV 254 + BESS 500)', pv_kwp=254, bess_kwh=500)
    analisador.simular_cenario('Cenário 2 (PV 324 kWp)', pv_kwp=324, bess_kwh=0)
    analisador.simular_cenario('Cenário 3 (PV 324 + BESS 500)', pv_kwp=324, bess_kwh=500)
    
    # Gerar relatório comparativo
    df = analisador.gerar_relatorio_completo()
    
    # Gerar gráficos
    analisador.gerar_graficos()
    
    # Salvar dados em CSV
    df.to_csv('analise_fluxo_potencia_dados.csv', index=False)
    print(f"\n💾 Dados salvos em: analise_fluxo_potencia_dados.csv")
    
    print("\n" + "="*100)
    print(" "*35 + "ANÁLISE CONCLUÍDA")
    print("="*100)


if __name__ == '__main__':
    main()
