from copy import deepcopy
from django.test import SimpleTestCase
from .equipamentos import preparar_modelo, modelo_do_layout
from .services import gerar_modelo_entradas


class EquipamentosTests(SimpleTestCase):
    def test_ensaio_irradiancia_tem_retorno_e_janela_valida(self):
        modelo = gerar_modelo_entradas({'nodes': [], 'edges': []}, 'Teste')
        with self.assertRaisesRegex(ValueError, '0,3'):
            preparar_modelo(modelo, {'tempo_s': .1, 'teste_irradiancia': True})
        dados, avisos = preparar_modelo(modelo, {'tempo_s': .3, 'teste_irradiancia': True})
        self.assertEqual(dados['Falhas_sim'][0]['Val_Irrad'], [100])
        self.assertEqual(dados['Falhas_sim'][0]['T_falha'], [.12])
        self.assertIn('retorno', avisos[0])

    def test_mppts_independentes_preservam_modulos_e_conexoes(self):
        modelo = gerar_modelo_entradas({'nodes': [], 'edges': []}, 'Teste')
        modelo['painel_info'][0].update(quantidade=[531, 1], grupos_mppt=[{'serie':18, 'paralelo':10}, {'serie':18, 'paralelo':10}, {'serie':18, 'paralelo':9}, {'serie':9, 'paralelo':1}])
        modelo['inversor_info'][0].update(Nm_MPPT=4, Imax_MPPT=200, In_Vmax=1100, In_MPP_Vmin=250, In_MPP_Vmax=900)
        dados, _ = preparar_modelo(modelo, {})
        self.assertEqual(len(dados['painel_info']), 4)
        self.assertEqual(sum(p['quantidade'][0] * p['quantidade'][1] for p in dados['painel_info']), 531)
        for p in dados['painel_info']:
            self.assertIn({'between': [p['pv_id'], 'Inv_1']}, dados['grafo_conexoes'])
            self.assertIn({'between': ['Clima_Ambiente', p['pv_id']]}, dados['grafo_conexoes'])
        modelo['inversor_info'][0]['Imax_MPPT'] = 36
        with self.assertRaisesRegex(ValueError, 'incompatível'):
            preparar_modelo(modelo, {})
        modelo['inversor_info'][0].update(Imax_MPPT=200, Nm_MPPT=3)
        with self.assertRaisesRegex(ValueError, 'excede'):
            preparar_modelo(modelo, {})

    def test_carga_em_watts_e_arranjo_preserva_modulos(self):
        modelo = gerar_modelo_entradas({'nodes': [], 'edges': []}, 'Teste')
        modelo['cargas_info'][0].update(s_instalada=120, fp=0.9)
        modelo['painel_info'][0]['quantidade'] = [531, 1]
        dados, _ = preparar_modelo(modelo, {})
        carga = dados['cargas_info'][0]
        self.assertAlmostEqual(carga['s_instalada'] * carga['fp'], 120000)
        painel = dados['painel_info'][0]
        self.assertEqual(painel['quantidade'], [9, 59])
        self.assertLessEqual(painel['quantidade'][0] * painel['Voc'], dados['inversor_info'][0]['In_Vmax'])
        repetido, _ = preparar_modelo(dados, {})
        self.assertEqual(repetido['cargas_info'], dados['cargas_info'])
        self.assertEqual(repetido['painel_info'], dados['painel_info'])

    def test_remove_equipamentos_ausentes(self):
        layout = {'nodes': [{'id': 'inv', 'data': {'componente': {'tipo_codigo': 'inversor'}}}], 'edges': []}
        modelo = modelo_do_layout(gerar_modelo_entradas(layout, 'Selecionado'), layout)
        self.assertEqual(modelo['nome_projeto'], 'Selecionado')
        self.assertEqual(len(modelo['inversor_info']), 1)
        self.assertEqual(modelo['bateria_info'], [])
        self.assertEqual(modelo['painel_info'], [])
        self.assertEqual(modelo['cargas_info'], [])

    def test_conversao_bateria_e_isolamento(self):
        modelo = gerar_modelo_entradas({'nodes': [], 'edges': []}, 'Teste')
        original = deepcopy(modelo)
        dados, avisos = preparar_modelo(modelo, {'tempo_s': 0.1})
        bateria = dados['bateria_info'][0]
        self.assertAlmostEqual(bateria['Capacidade'] * bateria['V_nom'] / 1000, original['bateria_info'][0]['capacidade_kwh'])
        self.assertAlmostEqual(bateria['I_discharge_max'] * bateria['V_nom'] / 1000, original['bateria_info'][0]['potencia_max_descarga_kw'])
        self.assertEqual(modelo, original)
        self.assertEqual(dados['Config_Simulacao'][0]['Tipo_Sim'], 'Transiente')
        self.assertTrue(avisos)

    def test_limites_execucao(self):
        for config in ({'tempo_s': 8760}, {'passo_s': 0}, {'tempo_s': float('nan')}, {'tempo_s': 2, 'passo_s': 0.000001}):
            with self.assertRaises(ValueError):
                preparar_modelo({'inversor_info': [{}]}, config)
