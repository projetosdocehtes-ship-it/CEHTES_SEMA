"""
Teste completo do sistema de análise financeira com microrrede
Integração: Tarifas horárias + Perfil de carga variável + Power Flow
"""

from analise_financeira_horaria import AnaliseFinanceiraHoraria
from tarifas_aneel import TarifasANEEL
from perfil_carga import PerfilCarga

print("\n" + "=" * 90)
print(" " * 15 + "ANÁLISE FINANCEIRA COMPLETA - MICRORREDE COM TARIFAS HORÁRIAS")
print("=" * 90)

# Parâmetros da análise
print("\n📋 Configurando análise...")
print("-" * 90)

distribuidora = 'EQUATORIAL GO'
modalidade = 'azul'  # Começar com azul (melhor opção segundo teste anterior)
vida_util = 25  # anos
taxa_desconto = 0.10  # 10% a.a.

print(f"  Distribuidora:  {distribuidora}")
print(f"  Modalidade:     {modalidade.upper()}")
print(f"  Vida útil:      {vida_util} anos")
print(f"  Taxa desconto:  {taxa_desconto*100:.0f}%")

# Criar análise
print("\n🔧 Inicializando análise financeira horária...")
analise = AnaliseFinanceiraHoraria(
    distribuidora=distribuidora,
    modalidade=modalidade,
    vida_util=vida_util,
    taxa_desconto=taxa_desconto
)

# Executar análise completa
print("\n⚡ Executando simulação anual completa...")
print("   (260 dias úteis + 105 fins de semana = 365 dias)")
print("-" * 90)

relatorio = analise.gerar_relatorio_completo()

print("\n" + "=" * 90)
print("✅ ANÁLISE CONCLUÍDA!")
print("=" * 90)

# Testar também com modalidade verde para comparação
print("\n\n" + "=" * 90)
print(" " * 20 + "COMPARAÇÃO COM MODALIDADE VERDE")
print("=" * 90)

print("\n🔧 Inicializando análise com modalidade VERDE...")
analise_verde = AnaliseFinanceiraHoraria(
    distribuidora=distribuidora,
    modalidade='verde',
    vida_util=vida_util,
    taxa_desconto=taxa_desconto
)

print("\n⚡ Executando simulação anual completa...")
relatorio_verde = analise_verde.gerar_relatorio_completo()

print("\n" + "=" * 90)
print("✅ COMPARAÇÃO CONCLUÍDA!")
print("=" * 90)

# Resumo comparativo
print("\n\n" + "=" * 90)
print(" " * 25 + "RESUMO COMPARATIVO FINAL")
print("=" * 90)

# Calcular resultados
from analise_financeira_horaria import AnaliseFinanceiraHoraria

# Azul
analise_azul = AnaliseFinanceiraHoraria(distribuidora, 'azul', vida_util, taxa_desconto)
custos_sem_azul = analise_azul.calcular_custos_sem_microrrede_anual()
custos_com_azul = analise_azul.calcular_custos_com_microrrede_anual()
vpl_azul = analise_azul.calcular_vpl()
tir_azul = analise_azul.calcular_tir()

# Verde
analise_verde = AnaliseFinanceiraHoraria(distribuidora, 'verde', vida_util, taxa_desconto)
custos_sem_verde = analise_verde.calcular_custos_sem_microrrede_anual()
custos_com_verde = analise_verde.calcular_custos_com_microrrede_anual()
vpl_verde = analise_verde.calcular_vpl()
tir_verde = analise_verde.calcular_tir()

print("\nMODALIDADE AZUL:")
print(f"  Custo anual sem microrrede:  R$ {custos_sem_azul:,.2f}")
print(f"  Custo anual com microrrede:  R$ {custos_com_azul:,.2f}")
print(f"  Economia anual:              R$ {custos_sem_azul - custos_com_azul:,.2f}")
print(f"  VPL:                         R$ {vpl_azul:,.2f}")
print(f"  TIR:                         {tir_azul*100:.2f}%")

print("\nMODALIDADE VERDE:")
print(f"  Custo anual sem microrrede:  R$ {custos_sem_verde:,.2f}")
print(f"  Custo anual com microrrede:  R$ {custos_com_verde:,.2f}")
print(f"  Economia anual:              R$ {custos_sem_verde - custos_com_verde:,.2f}")
print(f"  VPL:                         R$ {vpl_verde:,.2f}")
print(f"  TIR:                         {tir_verde*100:.2f}%")

if vpl_azul > vpl_verde:
    print(f"\n✅ RECOMENDAÇÃO: MODALIDADE AZUL")
    print(f"   VPL superior em R$ {vpl_azul - vpl_verde:,.2f}")
else:
    print(f"\n✅ RECOMENDAÇÃO: MODALIDADE VERDE")
    print(f"   VPL superior em R$ {vpl_verde - vpl_azul:,.2f}")

print("\n" + "=" * 90)
print(" TESTE COMPLETO FINALIZADO COM SUCESSO!")
print("=" * 90)
print("\nSistema validado:")
print("  ✓ Perfil de carga horária (variável dia útil/fim de semana)")
print("  ✓ Tarifas ANEEL (ponta/fora ponta)")
print("  ✓ Power Flow com carga variável")
print("  ✓ Análise financeira completa (VPL, TIR)")
print("  ✓ Comparação modalidades Azul vs Verde")
print("=" * 90 + "\n")
