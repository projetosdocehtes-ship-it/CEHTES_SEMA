import unittest
from types import SimpleNamespace
import numpy as np
from apps.Equipamentos import Classes, Var_globais
from apps.Equipamentos.balanco import limitar_saida, EloCC
from apps.Equipamentos.partida import SequenciaPartida


class IntegracaoTests(unittest.TestCase):
    def test_partida_exige_precarga_e_estabilidade_continua(self):
        p = SequenciaPartida()
        self.assertFalse(p.atualizar(0, False, True))
        self.assertFalse(p.atualizar(.03, True, True))
        self.assertFalse(p.atualizar(.049, True, False))
        self.assertFalse(p.atualizar(.05, True, True))
        self.assertFalse(p.atualizar(.069, True, True))
        self.assertTrue(p.atualizar(.07, True, True))
        self.assertAlmostEqual(p.fechamento_s, .07)

    def test_protecao_impede_fechamento(self):
        p = SequenciaPartida()
        p.atualizar(0, True, True)
        self.assertFalse(p.atualizar(.03, True, True, protecao=True))
        self.assertEqual(p.estado, 'bloqueada')
        self.assertIsNone(p.fechamento_s)

    def test_precarga_parte_sem_energia_e_limita_recarga(self):
        elo = EloCC(capacitancia_f=.005, tensao_nominal_v=800, tensao_min_v=700, tensao_max_v=850, tensao_inicial_v=0, tempo_recomposicao_s=.005)
        self.assertEqual(elo.energia, 0)
        h = elo.atualizar(100000, 0, .976, .001, limite_recarga_w=50000)
        self.assertAlmostEqual(elo.energia, 50)
        self.assertAlmostEqual(h['excedente_w'], 50000)
        self.assertAlmostEqual(h['erro_j'], 0)
        onda, rms = limitar_saida([500, 300], [380, 250], p_dc=100000, demanda=0, eficiencia=.976, potencia_nominal_w=150000, corrente_max=250, fases=3, fp=1)
        self.assertEqual(list(rms), [380, 0])

    def criar_elo(self):
        return EloCC(capacitancia_f=.005, tensao_nominal_v=800, tensao_min_v=700, tensao_max_v=850, tensao_inicial_v=800, tempo_recomposicao_s=.005)

    def test_elo_esgota_reserva_sem_criar_energia(self):
        elo = self.criar_elo()
        self.assertAlmostEqual(elo.energia - elo.e_min,375)
        total_ac_j = 0
        for _ in range(500):
            disponivel = elo.potencia_disponivel(0, .00002)
            _, rms = limitar_saida([500,300],[380,250],p_dc=disponivel,demanda=120000,eficiencia=.976,potencia_nominal_w=150000,corrente_max=250,fases=3,fp=1)
            p_ac = np.sqrt(3) * rms[0] * rms[1]
            h = elo.atualizar(0,p_ac,.976,.00002)
            self.assertLess(abs(h['erro_j']),1e-8)
            self.assertGreaterEqual(h['tensao_v'],700-1e-8)
            total_ac_j += p_ac * .00002
        self.assertAlmostEqual(total_ac_j,375 * .976,places=6)
        self.assertEqual(elo.potencia_disponivel(0,.00002),0)

    def test_elo_suporta_transicao_recarrega_e_contabiliza_excedente(self):
        elo = self.criar_elo()
        inicial = elo.energia
        h = elo.atualizar(-120000,120000,.976,.00002)
        self.assertLess(h['energia_j'],inicial)
        self.assertGreater(elo.recomposicao_w,0)
        h = elo.atualizar(200000,120000,.976,.01)
        self.assertEqual(elo.energia,elo.e_max)
        self.assertGreater(h['excedente_w'],0)
        self.assertLess(abs(h['erro_j']),1e-8)
        self.assertLess(elo.recomposicao_w,0)

    def test_saida_nao_cria_energia_e_respeita_limites(self):
        for dc, demanda, nominal, corrente, esperado in [(100000,120000,150000,250,97600), (0,120000,150000,250,0), (-1000,120000,150000,250,0), (200000,120000,150000,250,120000), (200000,160000,100000,250,100000)]:
            onda, rms = limitar_saida([500,300], [380,250], p_dc=dc, demanda=demanda, eficiencia=.976, potencia_nominal_w=nominal, corrente_max=corrente, fases=3, fp=1)
            self.assertAlmostEqual(np.sqrt(3)*rms[0]*rms[1], esperado, places=6)
            self.assertLessEqual(rms[1], corrente)
        _, rms = limitar_saida([500,300], [380,250], p_dc=1e6, demanda=1e6, eficiencia=.976, potencia_nominal_w=1e6, corrente_max=50, fases=3, fp=1)
        self.assertLessEqual(rms[1], 50)

    def test_mppt_recupera_apos_queda_sem_potencia_ficticia(self):
        painel = Classes.Painel_Fotovoltaico('PV_T','Teste','610',610,15.97,48,14.96,40.8,.05,-.25,-.29,'Silicio',22.6)
        pv = Classes.Painel_Fotovoltaico.Simulacao_painel(painel.PV_Param,[18,2])
        inv = Classes.Inversor_DC_AC.Simulacao_inversor_convencional.__new__(Classes.Inversor_DC_AC.Simulacao_inversor_convencional)
        inv.MPPT_learning_rate=2; inv.In_MPP_Vmin=250; inv.In_MPP_Vmax=900
        estado={'P_ant':100000,'V_ant':850,'dir_mppt_ant':1}
        ref=850
        Var_globais.Passo_atual_global=100
        potencias=[]
        for _ in range(500):
            v,i,p = pv.Simula_PV({'T':25,'G':100},[],ref)
            self.assertAlmostEqual(p,v*i,places=6)
            potencias.append(p)
            ref=inv.MPPT(p*36,v*18,-1,estado)
        il,io,voc=pv.Calcula_Param_auxiliares(25,100)
        referencia=max(pv.Perdas_Painel(v*pv.Newton_Raphson_Corrente(v,1,il,io),v)[0] for v in np.linspace(1,voc,200))
        self.assertGreater(np.mean(potencias[-30:]),referencia*.95)
        self.assertEqual(pv.Simula_PV({'T':25,'G':0},[],ref),(0,0,0))

    def test_bateria_publica_medicoes_e_soc_correto(self):
        for acao, sinal in [('descarregar', 1), ('carregar', -1)]:
            b = Classes.Stack_Baterias('B', 'Teste', 'Teste', 'Generica', 100, 50, 50, 270, 310, 300, 0.8, 6000)
            b.receive('I', 'Inversor', 'saida_bateria', {'B': {'acao': acao, 'Pot_requerida': 1000}})
            mensagens = {}
            agente = SimpleNamespace(publicar_msg=lambda topico, dados: mensagens.update({topico: dados}))
            Var_globais.Passo_atual_global = 0
            b.Simular_equipamento([1, 1], agente)
            leitura = mensagens['B/medicoes_bateria']['B']
            self.assertGreater(leitura['I_bat'] * sinal, 0)
            self.assertGreater(leitura['P_bat'] * sinal, 0)
            self.assertLess((b.SOC[-1] - 0.8) * sinal, 0)

    def test_barramento_registra_deficit_sem_inventar_energia(self):
        b = Classes.Barramento.Simulacao_Barramento(SimpleNamespace(nm_fases=3))
        Var_globais.Passo_atual_global = 1
        inv = np.array([['OutroInversor', 380, 50, 0, 0]], dtype=object)
        cargas = np.array([['OutraCarga', 120000, 0]], dtype=object)
        demanda, entrega = b.Simula_barramento(inv, cargas)
        self.assertEqual(demanda[0][1], 120000)
        self.assertAlmostEqual(entrega[0][3], np.sqrt(3) * 380 * 50)
        self.assertAlmostEqual(entrega[0][2], 50)


if __name__ == '__main__':
    unittest.main()
