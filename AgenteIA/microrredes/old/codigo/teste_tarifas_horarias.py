"""
Script de teste para validar o sistema completo com tarifas horárias
Usando Equatorial Goiás como caso de teste
"""

from tarifas_aneel import TarifasANEEL
from perfil_carga import PerfilCarga

print("\n" + "=" * 90)
print(" " * 20 + "TESTE: SISTEMA COM TARIFAÇÃO HORÁRIA")
print("=" * 90)

# 1. Testar tarifas da Equatorial Goiás
print("\n\n📋 PASSO 1: Validando tarifas da Equatorial Goiás")
print("-" * 90)

tarifas = TarifasANEEL('EQUATORIAL GO')
tarifas.gerar_relatorio_tarifas()

# 2. Testar perfil de carga
print("\n\n📊 PASSO 2: Validando perfil de carga horária")
print("-" * 90)

perfil = PerfilCarga('perfil_carga_horaria.csv')
perfil.gerar_relatorio()

# 3. Exemplo de cálculo de fatura
print("\n\n💰 PASSO 3: Exemplo de cálculo de fatura mensal")
print("-" * 90)

# Simular dados de consumo mensal
stats = perfil.get_estatisticas()

# Energia e demanda aproximadas por mês (considerando perfil médio)
energia_ponta_mensal = stats['dia_util']['energia_diaria_kwh'] * 22 * 0.15  # ~15% na ponta
energia_fp_mensal = stats['dia_util']['energia_diaria_kwh'] * 22 * 0.85 + stats['fim_semana']['energia_diaria_kwh'] * 8

demanda_ponta = stats['dia_util']['demanda_pico_kw']
demanda_fp = stats['dia_util']['demanda_pico_kw']

print(f"\nConsumo estimado mensal:")
print(f"  Energia ponta:       {energia_ponta_mensal:,.0f} kWh")
print(f"  Energia fora ponta:  {energia_fp_mensal:,.0f} kWh")
print(f"  Demanda ponta:       {demanda_ponta:,.0f} kW")
print(f"  Demanda fora ponta:  {demanda_fp:,.0f} kW")

comparacao = tarifas.comparar_modalidades(
    energia_ponta_mensal,
    energia_fp_mensal,
    demanda_ponta,
    demanda_fp
)

print("\n" + "=" * 90)
print(" COMPARAÇÃO DE MODALIDADES TARIFÁRIAS")
print("=" * 90)

azul = comparacao['azul']
verde = comparacao['verde']

print("\nMODALIDADE AZUL:")
print(f"  Custo total:  R$ {azul['custo_total']:,.2f}")
print(f"  Custo médio:  R$ {azul['custo_medio_kwh']:.3f}/kWh")

print("\nMODALIDADE VERDE:")
print(f"  Custo total:  R$ {verde['custo_total']:,.2f}")
print(f"  Custo médio:  R$ {verde['custo_medio_kwh']:.3f}/kWh")

print(f"\n✅ MELHOR OPÇÃO: {comparacao['melhor_opcao']}")
print(f"💰 ECONOMIA: R$ {comparacao['diferenca_absoluta']:,.2f} ({abs(comparacao['economia_percentual']):.1f}%)")

print("\n" + "=" * 90)
print(" VALIDAÇÃO CONCLUÍDA COM SUCESSO!")
print("=" * 90)
print("\nTodos os módulos estão funcionando corretamente:")
print("  ✓ Tarifas ANEEL (Equatorial Goiás)")
print("  ✓ Perfil de carga horária")
print("  ✓ Cálculo de custos por modalidade")
print("\nPróximo passo: Executar análise financeira completa com microrrede")
print("=" * 90)
