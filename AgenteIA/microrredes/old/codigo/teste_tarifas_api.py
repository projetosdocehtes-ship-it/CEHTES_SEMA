"""
Script para testar a classe TarifasANEEL modificada
Testa a busca filtrada pela distribuidora de interesse
"""

from tarifas_aneel import TarifasANEEL

def testar_EQUATORIALGO():
    """Testa busca de tarifas da Equatorial Goiás"""
    print("=" * 60)
    print("Teste: Equatorial Goiás")
    print("=" * 60)
    
    try:
        # Inicializar com API - usar 'EQUATORIAL GO' conforme a API
        tarifa = TarifasANEEL(distribuidora='EQUATORIAL GO', usar_api=True, grupo='A4')
        
        # Mostrar informações
        info = tarifa.get_info_distribuidora()
        print(f"\nInformações da Distribuidora:")
        print(f"  Nome: {info['nome']}")
        print(f"  UF: {info['uf']}")
        print(f"  Grupo: {info['grupo']}")
        print(f"  Vigência: {info['vigencia']}")
        print(f"  Fonte: {info['fonte']}")
        
        # Mostrar tarifas Azul
        azul = tarifa.get_tarifas_azul()
        print(f"\nTarifas Modalidade Azul:")
        print(f"  TUSD Demanda Ponta: R$ {azul['tusd_ponta_demanda']:.2f}/kW")
        print(f"  TUSD Demanda Fora Ponta: R$ {azul['tusd_fora_ponta_demanda']:.2f}/kW")
        print(f"  TUSD Consumo Ponta: R$ {azul['tusd_ponta_consumo']:.4f}/kWh")
        print(f"  TUSD Consumo Fora Ponta: R$ {azul['tusd_fora_ponta_consumo']:.4f}/kWh")
        print(f"  TE Ponta: R$ {azul['te_ponta']:.4f}/kWh")
        print(f"  TE Fora Ponta: R$ {azul['te_fora_ponta']:.4f}/kWh")
        
        # Mostrar tarifas Verde
        verde = tarifa.get_tarifas_verde()
        print(f"\nTarifas Modalidade Verde:")
        print(f"  TUSD Demanda: R$ {verde['tusd_demanda']:.2f}/kW")
        print(f"  TUSD Consumo Ponta: R$ {verde['tusd_ponta_consumo']:.4f}/kWh")
        print(f"  TUSD Consumo Fora Ponta: R$ {verde['tusd_fora_ponta_consumo']:.4f}/kWh")
        print(f"  TE Ponta: R$ {verde['te_ponta']:.4f}/kWh")
        print(f"  TE Fora Ponta: R$ {verde['te_fora_ponta']:.4f}/kWh")
        
        print("\n✓ Teste bem-sucedido!")
        return True
        
    except Exception as e:
        print(f"\n✗ Erro no teste: {e}")
        import traceback
        traceback.print_exc()
        return False

def testar_cemig():
    """Testa busca de tarifas da CEMIG"""
    print("\n" + "=" * 60)
    print("Teste: CEMIG")
    print("=" * 60)
    
    try:
        # Inicializar com API
        tarifa = TarifasANEEL(distribuidora='CEMIG', usar_api=True, grupo='A4')
        
        # Mostrar informações
        info = tarifa.get_info_distribuidora()
        print(f"\nInformações da Distribuidora:")
        print(f"  Nome: {info['nome']}")
        print(f"  UF: {info['uf']}")
        print(f"  Vigência: {info['vigencia']}")
        print(f"  Fonte: {info['fonte']}")
        
        print("\n✓ Teste bem-sucedido!")
        return True
        
    except Exception as e:
        print(f"\n✗ Erro no teste: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("Testando a classe TarifasANEEL com busca filtrada\n")
    
    resultado1 = testar_EQUATORIALGO()
    resultado2 = testar_cemig()
    
    print("\n" + "=" * 60)
    print("RESUMO DOS TESTES")
    print("=" * 60)
    print(f"Equatorial Goiás: {'✓ Passou' if resultado1 else '✗ Falhou'}")
    print(f"CEMIG: {'✓ Passou' if resultado2 else '✗ Falhou'}")
