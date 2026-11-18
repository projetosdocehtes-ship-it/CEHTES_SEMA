from copy import deepcopy
from django.test import SimpleTestCase
from .transitorio import executar_transitorio


class TransitorioTests(SimpleTestCase):
    modelo = {
        'conectado_rede': True,
        'painel_info': [{'Pmp': 500, 'quantidade': 100}],
        'inversor_info': [{'Eficiencia': 0.98}],
        'bateria_info': [{'capacidade_kwh': 100, 'potencia_max_descarga_kw': 40}],
        'cargas_info': [{'potencia_kw': 100, 'fp': 0.95}],
        'geradordiesel_info': [{'potencia_nominal_kw': 275}],
    }
    cenario = {'inicio_s': 0.1, 'duracao_s': 0.04, 'tempo_s': 0.3, 'passo_s': 0.01}

    def test_eventos_e_recuperacao(self):
        for tipo in ('perda_fv', 'degrau_carga', 'curto_3ph'):
            with self.subTest(tipo=tipo):
                modelo = deepcopy(self.modelo)
                # Exercita o modelo FV+BESS sem diesel e o modelo isolado do gerador.
                if tipo == 'perda_fv':
                    modelo['geradordiesel_info'] = []
                original = deepcopy(modelo)
                resposta = executar_transitorio(modelo, {**self.cenario, 'tipo': tipo, 'carga_kw': 150})
                serie = resposta['resultado']['serie_temporal']
                self.assertGreater(len(serie['tempo_s']), 20)
                self.assertEqual(modelo, original)
                if tipo == 'degrau_carga':
                    self.assertEqual(serie['carga_kw'][11], 150)
                    self.assertEqual(serie['carga_kw'][-1], 100)
                elif tipo == 'curto_3ph':
                    self.assertGreater(max(serie['corrente_curto_ka']), 0)
                    self.assertEqual(serie['corrente_curto_ka'][-1], 0)
                else:
                    self.assertEqual(serie['falha_ativa'][11], 1)
                    self.assertEqual(serie['falha_ativa'][-1], 0)

    def test_rejeita_evento_fora_da_janela(self):
        with self.assertRaises(ValueError):
            executar_transitorio(self.modelo, {**self.cenario, 'tipo': 'curto_3ph', 'inicio_s': 1})

    def test_rejeita_gerador_ausente(self):
        with self.assertRaises(ValueError):
            executar_transitorio({**self.modelo, 'geradordiesel_info': []}, {**self.cenario, 'tipo': 'degrau_carga'})

    def test_rejeita_excesso_de_passos(self):
        with self.assertRaises(ValueError):
            executar_transitorio(self.modelo, {**self.cenario, 'tipo': 'perda_fv', 'tempo_s': 60, 'passo_s': 0.001})

    def test_falha_rede_partida_balanco_e_retorno(self):
        cenario = {'tipo': 'falha_rede', 'inicio_s': 0.2, 'duracao_s': 1, 'tempo_s': 2, 'passo_s': 0.01, 'partida_diesel_s': 0.3, 'rampa_diesel_s': 0.5, 'retorno_rede_s': 0.2, 'carga_kw': 100}
        resposta = executar_transitorio(self.modelo, cenario)
        s = resposta['resultado']['serie_temporal']
        self.assertGreater(s['bess_kw'][30], 0)
        self.assertEqual(s['diesel_kw'][30], 0)
        self.assertGreater(s['diesel_kw'][80], 0)
        self.assertEqual(s['rede_kw'][80], 0)
        self.assertEqual(s['rede_conectada'][125], 0)
        self.assertEqual(s['rede_disponivel'][125], 1)
        self.assertEqual(s['rede_kw'][-1], 100)
        self.assertEqual(s['bess_kw'][-1], 0)
        self.assertEqual(s['diesel_kw'][-1], 0)
        self.assertLess(s['soc'][-1], s['soc'][0])
        for i in range(len(s['tempo_s'])):
            self.assertAlmostEqual(s['pv_kw'][i] + s['bess_kw'][i] + s['diesel_kw'][i] + s['rede_kw'][i] + s['deficit_kw'][i] - s['curtailment_kw'][i], s['carga_kw'][i], places=6)

    def test_bess_sem_reserva_e_falha_curta(self):
        modelo = deepcopy(self.modelo)
        modelo['bateria_info'][0].update(soc_inicial=0.1, soc_min=0.1)
        resposta = executar_transitorio(modelo, {'tipo': 'falha_rede', 'inicio_s': 0.1, 'duracao_s': 0.1, 'tempo_s': 0.5, 'partida_diesel_s': 2, 'retorno_rede_s': 0.1})
        s = resposta['resultado']['serie_temporal']
        self.assertEqual(max(s['diesel_kw']), 0)
        self.assertEqual(max(s['bess_kw']), 0)
        self.assertGreater(max(s['deficit_kw']), 0)
        self.assertEqual(s['deficit_kw'][-1], 0)

    def test_rede_requer_bess_e_janela_recuperacao(self):
        for modelo, cenario in (
            ({**self.modelo, 'bateria_info': []}, {}),
            ({**self.modelo, 'conectado_rede': False}, {}),
            (self.modelo, {'retorno_rede_s': 20}),
        ):
            with self.assertRaises(ValueError):
                executar_transitorio(modelo, {'tipo': 'falha_rede', 'inicio_s': 1, 'duracao_s': 2, 'tempo_s': 6, **cenario})
