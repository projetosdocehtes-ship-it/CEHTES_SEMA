from django.test import SimpleTestCase
from .analise_relatorio import analisar_relatorio
from .services import _carregar_motor_fluxo_potencia


class AnaliseRelatorioTests(SimpleTestCase):
    def test_horas_equivalentes_independem_do_passo(self):
        _carregar_motor_fluxo_potencia()
        from microrredes.analises.transitorio_gerador_diesel import _resumo, ConfiguracaoGeradorDiesel
        for passo in (0.01, 0.005):
            serie = [{'tempo_s': round(i * passo, 9), 'curto_circuito_ativo': 0.1 <= round(i * passo, 9) < 0.25, 'frequencia_hz': 60, 'tensao_pu': 1, 'corrente_curto_ka': 0, 'evento_carga': None} for i in range(round(0.3 / passo) + 1)]
            self.assertAlmostEqual(_resumo(serie, ConfiguracaoGeradorDiesel())['horas_equivalentes_falta'], 0.15 / 3600, places=12)
        serie = [dict(serie[0], tempo_s=0, curto_circuito_ativo=True), dict(serie[0], tempo_s=0.1, curto_circuito_ativo=True)]
        self.assertAlmostEqual(_resumo(serie, ConfiguracaoGeradorDiesel())['horas_equivalentes_falta'], 0.1 / 3600, places=12)

    def test_zero_deficit_nao_aprova_tensao(self):
        r = analisar_relatorio({'serie_temporal': {'tempo_s': [0, 1, 2], 'deficit_kw': [0, 0, 0], 'tensao_pu': [1, 0.12, 0.7], 'frequencia_hz': [60, 57.7, 59.72]}}, {'fim_s': 1.5})
        por_titulo = {item['titulo']: item for item in r['itens']}
        self.assertEqual(por_titulo['Tensão']['nivel'], 'atencao')
        self.assertEqual(por_titulo['Frequência']['nivel'], 'atencao')
        self.assertIn('não comprova', por_titulo['Atendimento da carga']['texto'])

    def test_modelo_potencia_nao_inventa_grandezas(self):
        r = analisar_relatorio({'serie_temporal': {'tempo_s': [0, 1, 2], 'deficit_kw': [0, 10, 0], 'rede_conectada': [1, 0, 1]}}, {'tipo': 'falha_rede', 'fim_s': 1.5})
        itens = {item['titulo']: item for item in r['itens']}
        self.assertNotIn('Tensão', itens)
        self.assertNotIn('Frequência', itens)
        self.assertIn('não calcula', itens['Limite do modelo']['texto'].lower())
        self.assertEqual(itens['Recuperação da rede']['nivel'], 'informacao')
        self.assertEqual(itens['Atendimento da carga']['nivel'], 'atencao')

    def test_dados_ausentes_e_final_invalido(self):
        self.assertEqual(analisar_relatorio({}, {})['itens'][0]['nivel'], 'atencao')
        r = analisar_relatorio({'serie_temporal': {'tempo_s': [0, 1, 2], 'tensao_pu': [1, 1, None]}}, {'fim_s': 1})
        self.assertEqual(next(i for i in r['itens'] if i['titulo'] == 'Tensão')['nivel'], 'atencao')
