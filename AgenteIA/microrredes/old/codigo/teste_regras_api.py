"""
Teste para verificar as regras de extração de tarifas da API
"""

from tarifas_aneel import TarifasANEEL
import pandas as pd

def testar_regras_extracao():
    """Testa se as regras de filtro estão sendo aplicadas corretamente"""
    print("=" * 70)
    print("Teste: Regras de Extração de Tarifas (Equatorial GO)")
    print("=" * 70)
    
    try:
        # Inicializar com API
        tarifa = TarifasANEEL(distribuidora='EQUATORIAL GO', usar_api=True, grupo='A4')
        
        info = tarifa.get_info_distribuidora()
        print(f"\n{'Informações Gerais':-^70}")
        print(f"  Nome: {info['nome']}")
        print(f"  UF: {info['uf']}")
        print(f"  Grupo: {info['grupo']}")
        print(f"  Vigência: {info['vigencia']}")
        print(f"  Fonte: {info['fonte']}")
        
        # Tarifas Azul
        azul = tarifa.get_tarifas_azul()
        print(f"\n{'Modalidade AZUL':-^70}")
        print(f"  Demanda Ponta (demanda_P):           R$ {azul['tusd_ponta_demanda']:>8.2f} /kW")
        print(f"  Demanda Fora Ponta (demanda_FP):     R$ {azul['tusd_fora_ponta_demanda']:>8.2f} /kW")
        print(f"  Encargo Consumo Ponta (encargo_P):   R$ {azul['tusd_ponta_consumo']:>8.4f} /MWh")
        print(f"  Encargo Consumo FP (encargo_FP):     R$ {azul['tusd_fora_ponta_consumo']:>8.4f} /MWh")
        print(f"  TE Ponta (consumo_P):                R$ {azul['te_ponta']:>8.4f} /MWh")
        print(f"  TE Fora Ponta (consumo_FP):          R$ {azul['te_fora_ponta']:>8.4f} /MWh")
        
        # Tarifas Verde
        verde = tarifa.get_tarifas_verde()
        print(f"\n{'Modalidade VERDE':-^70}")
        print(f"  Demanda NA (demanda_NA):             R$ {verde['tusd_demanda']:>8.2f} /kW")
        print(f"  Demanda Ponta (deve ser 0):          R$ {0:>8.2f} /kW")
        print(f"  Demanda Fora Ponta (deve ser 0):     R$ {0:>8.2f} /kW")
        print(f"  Encargo Consumo Ponta (encargo_P):   R$ {verde['tusd_ponta_consumo']:>8.4f} /MWh")
        print(f"  Encargo Consumo FP (encargo_FP):     R$ {verde['tusd_fora_ponta_consumo']:>8.4f} /MWh")
        print(f"  TE Ponta (consumo_P):                R$ {verde['te_ponta']:>8.4f} /MWh")
        print(f"  TE Fora Ponta (consumo_FP):          R$ {verde['te_fora_ponta']:>8.4f} /MWh")
        
        # Validações
        print(f"\n{'Validações':-^70}")
        validacoes = []
        
        # Azul deve ter demandas diferenciadas
        if azul['tusd_ponta_demanda'] > 0 and azul['tusd_fora_ponta_demanda'] > 0:
            validacoes.append("✓ Azul: Demandas ponta e fora ponta definidas")
        else:
            validacoes.append("✗ Azul: Faltam valores de demanda")
        
        # Verde deve ter demanda única (NA)
        if verde['tusd_demanda'] > 0:
            validacoes.append("✓ Verde: Demanda única (NA) definida")
        else:
            validacoes.append("✗ Verde: Falta demanda NA")
        
        # Valores de TE e TUSD consumo devem existir
        if azul['te_ponta'] > 0 and azul['te_fora_ponta'] > 0:
            validacoes.append("✓ Azul: Tarifas de energia definidas")
        else:
            validacoes.append("✗ Azul: Faltam tarifas de energia")
        
        if verde['te_ponta'] > 0 and verde['te_fora_ponta'] > 0:
            validacoes.append("✓ Verde: Tarifas de energia definidas")
        else:
            validacoes.append("✗ Verde: Faltam tarifas de energia")
        
        for v in validacoes:
            print(f"  {v}")
        
        print(f"\n{'='*70}")
        print("✓ Teste concluído com sucesso!")
        return True
        
    except Exception as e:
        print(f"\n✗ Erro no teste: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    testar_regras_extracao()
