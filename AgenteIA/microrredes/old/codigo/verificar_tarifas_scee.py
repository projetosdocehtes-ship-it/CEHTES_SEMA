"""Verifica tarifas SCEE carregadas da API"""
from tarifas_aneel import TarifasANEEL

t = TarifasANEEL('EQUATORIAL GO', usar_api=True)
tarifas = t.get_tarifas_verde()

print('\n' + '='*80)
print('TARIFAS VERDE - EQUATORIAL GO')
print('='*80)
print(f'TE Ponta:           R$ {tarifas["te_ponta"]:.4f}/kWh')
print(f'TE Fora Ponta:      R$ {tarifas["te_fora_ponta"]:.4f}/kWh')
print(f'TUSD Ponta:         R$ {tarifas["tusd_ponta_consumo"]:.4f}/kWh')
print(f'TUSD Fora Ponta:    R$ {tarifas["tusd_fora_ponta_consumo"]:.4f}/kWh')
print(f'TUSD Demanda:       R$ {tarifas["tusd_demanda"]:.2f}/kW')

total_ponta = tarifas["te_ponta"] + tarifas["tusd_ponta_consumo"]
total_fp = tarifas["te_fora_ponta"] + tarifas["tusd_fora_ponta_consumo"]

print(f'\nTarifa Total Ponta:        R$ {total_ponta:.4f}/kWh')
print(f'Tarifa Total Fora Ponta:   R$ {total_fp:.4f}/kWh')
print(f'Diferencial Ponta/FP:      {total_ponta/total_fp:.2f}x')

# Tarifas SCEE
scee = t.dados_tarifa.get('scee', {})

print('\n' + '='*80)
print('TARIFAS SCEE (Sistema de Compensação - Energia Exportada)')
print('='*80)

# Verificar ambas as modalidades
for modalidade in ['verde', 'azul']:
    scee_mod = scee.get(modalidade, {})
    
    if not scee_mod:
        continue
        
    scee_total_ponta = scee_mod.get('te_ponta', 0) + scee_mod.get('tusd_ponta', 0)
    scee_total_fp = scee_mod.get('te_fora_ponta', 0) + scee_mod.get('tusd_fora_ponta', 0)
    
    if scee_total_ponta > 0:
        print(f'\n--- Modalidade {modalidade.upper()} ---')
        print(f'TE SCEE Ponta:           R$ {scee_mod.get("te_ponta", 0):.4f}/kWh')
        print(f'TE SCEE Fora Ponta:      R$ {scee_mod.get("te_fora_ponta", 0):.4f}/kWh')
        print(f'TUSD SCEE Ponta:         R$ {scee_mod.get("tusd_ponta", 0):.4f}/kWh')
        print(f'TUSD SCEE Fora Ponta:    R$ {scee_mod.get("tusd_fora_ponta", 0):.4f}/kWh')
        
        print(f'\nTarifa SCEE Total Ponta:        R$ {scee_total_ponta:.4f}/kWh')
        print(f'Tarifa SCEE Total Fora Ponta:   R$ {scee_total_fp:.4f}/kWh')
        
        print(f'\nCompensação Ponta:      {scee_total_ponta/total_ponta*100:.1f}% da tarifa cheia')
        print(f'Compensação Fora Ponta: {scee_total_fp/total_fp*100:.1f}% da tarifa cheia')

# Se nenhuma modalidade tem SCEE
if not any(scee.get(mod, {}).get('te_ponta', 0) > 0 for mod in ['verde', 'azul']):
    print('\n⚠️  Tarifas SCEE não encontradas na API - usando fallback 70%')

print('\n' + '='*80)
