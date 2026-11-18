"""
Teste rápido da API com Equatorial GO
"""

from tarifas_aneel import TarifasANEEL

print("Testando busca da Equatorial GO via API\n")

# Teste com API
tarifa = TarifasANEEL(distribuidora='EQUATORIAL GO', usar_api=True, grupo='A4')

info = tarifa.get_info_distribuidora()
print(f"Distribuidora: {info['nome']}")
print(f"UF: {info['uf']}")
print(f"Vigência: {info['vigencia']}")
print(f"Fonte: {info['fonte']}")

azul = tarifa.get_tarifas_azul()
print(f"\nTarifas Azul:")
for key, value in azul.items():
    print(f"  {key}: R$ {value:.4f}")
