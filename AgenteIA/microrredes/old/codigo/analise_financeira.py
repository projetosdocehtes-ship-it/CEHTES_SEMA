"""
Módulo de Análise Financeira para Microrrede
Calcula indicadores econômicos baseados nos resultados de simulação e tarifas ANEEL.
"""

import json
import argparse
from pathlib import Path

import numpy as np
import numpy_financial as npf
import matplotlib.pyplot as plt
from scipy.stats import gaussian_kde

from caso_ifg import CasoIFG
from perfil_carga import PerfilCarga
from tarifas_aneel import TarifasANEEL


class AnaliseFinanceiraMicrorrede:
    def __init__(self, entradas_path='Entradas.json', distribuidora='EQUATORIAL GO',
                 modalidade='verde', vida_util=20, taxa_desconto=0.08,
                 curva_carga_csv=None, pv_kwp=None, bess_kwh=None, bess_kw=None,
                 incluir_pv_no_capex=False, escala_carga=None,
                 ):
        """
        Inicializa a análise financeira da microrrede
        
        Parâmetros:
        -----------
        entradas_path : str
            Caminho do arquivo de entrada com os dados da simulação.
        distribuidora : str
            Distribuidora para consulta de tarifas na ANEEL.
        modalidade : str
            Modalidade tarifária ('verde' ou 'azul').
        vida_util : int
            Vida útil do projeto em anos (padrão: 20 anos)
        taxa_desconto : float
            Taxa de desconto para análise de VPL (padrão: 8%)
        curva_carga_csv : str | None
            Sobrescreve o arquivo de curva de carga definido no Entradas.json.
        pv_kwp : float | None
            Sobrescreve potência PV instalada (kWp).
        bess_kwh : float | None
            Sobrescreve capacidade do BESS (kWh).
        bess_kw : float | None
            Sobrescreve potência do BESS (kW).
        incluir_pv_no_capex : bool
            Se True, considera o investimento do PV no CAPEX.
            Se False, assume PV existente e não contabiliza custo de PV no CAPEX.
        escala_carga : float | None
            Fator multiplicador para ajustar a curva de carga (ex: 0.1).
            Se None, tenta usar cargas_info.fator_escala_curva do Entradas.json.
        """
        self.entradas_path = Path(entradas_path)
        self.distribuidora = distribuidora
        self.modalidade = modalidade.lower()
        self.vida_util = vida_util
        self.taxa_desconto = taxa_desconto
        self.curva_carga_csv_override = curva_carga_csv
        self.pv_kwp_override = pv_kwp
        self.bess_kwh_override = bess_kwh
        self.bess_kw_override = bess_kw
        self.incluir_pv_no_capex = incluir_pv_no_capex
        self.escala_carga_override = escala_carga

        self.config = self._carregar_entradas()
        self._extrair_parametros_config()

        self.tarifas_aneel = TarifasANEEL(self.distribuidora, usar_api=True)
        if self.modalidade == 'azul':
            self.tarifas = self.tarifas_aneel.get_tarifas_azul()
        else:
            self.tarifas = self.tarifas_aneel.get_tarifas_verde()

        # Tarifa média usada apenas para sensibilidade legada.
        self.tarifa_energia_kwh = (
            self.tarifas.get('te_ponta', 0) +
            self.tarifas.get('te_fora_ponta', 0) +
            self.tarifas.get('tusd_ponta_consumo', 0) +
            self.tarifas.get('tusd_fora_ponta_consumo', 0)
        ) / 2

        if self.modalidade == 'azul':
            self.tarifa_demanda_kw = (
                self.tarifas.get('tusd_ponta_demanda', 0) +
                self.tarifas.get('tusd_fora_ponta_demanda', 0)
            ) / 2
        else:
            self.tarifa_demanda_kw = self.tarifas.get('tusd_demanda', 0)
        
        # Custos do sistema
        self.custo_pv_kw = self.custo_pv_kwp_entrada
        self.custo_bess_kwh = self.custo_bess_kwh_entrada
        self.custo_diesel_kw = 1200  # R$/kW
        
        # Parâmetros operacionais
        self.custo_om_anual_percent = 0.02  # 2% do CAPEX
        self.custo_diesel_litro = self.custo_diesel_litro_entrada
        self.consumo_diesel_l_kwh = 0.25  # litros/kWh gerado

        impostos_cfg = self.config.get('tarifas_energia', {}).get('impostos', {})
        self.icms = float(impostos_cfg.get('icms', 0.0))
        self.pis = float(impostos_cfg.get('pis', 0.0))
        
        # Degradação e escalada
        self.degradacao_pv_anual = 0.005  # 0,5% ao ano
        self.escalada_tarifa = 0.04  # 4% ao ano (inflação energética)
        
        # Resultados da simulação
        self.microrrede = None
        self.resultado_mes_com_bess = None
        self.resultado_mes_sem_bess = None
        self.resultados_economicos = {}

    def _carregar_entradas(self):
        """Carrega arquivo de entrada JSON."""
        if not self.entradas_path.exists():
            raise FileNotFoundError(f"Arquivo não encontrado: {self.entradas_path}")

        with self.entradas_path.open('r', encoding='utf-8') as f:
            return json.load(f)

    @staticmethod
    def _parse_janela_horaria(janela):
        """Converte HH:MM-HH:MM para (hora_inicio, hora_fim, dia_inteiro)."""
        if not janela or '-' not in janela:
            return 0, 5, False

        inicio_str, fim_str = janela.split('-', 1)
        inicio = int(inicio_str.strip().split(':')[0])
        fim = int(fim_str.strip().split(':')[0])

        dia_inteiro = (inicio == 0 and fim == 24)
        if fim == 24:
            fim = 23

        return inicio, fim, dia_inteiro

    @staticmethod
    def _janela_no_periodo_noturno(inicio, fim):
        """Retorna True se a janela estiver restrita à madrugada/noite."""
        horas = []
        if inicio <= fim:
            horas = list(range(inicio, fim + 1))
        else:
            horas = list(range(inicio, 24)) + list(range(0, fim + 1))
        return all((h <= 6 or h >= 22) for h in horas)

    @staticmethod
    def _janela_intersecta_ponta(inicio, fim):
        """Retorna True se a janela tocar horário de ponta em dia útil (18h-20h)."""
        horas = []
        if inicio <= fim:
            horas = list(range(inicio, fim + 1))
        else:
            horas = list(range(inicio, 24)) + list(range(0, fim + 1))
        return any(TarifasANEEL.is_horario_ponta(h, dia_semana=0) for h in horas)

    def _inferir_estrategia_bess(self):
        """Infere estratégia considerando janelas de carga/descarga e modo operacional."""
        if not self.permitir_carga_bess or self.carga_dia_inteiro:
            return 'solar'

        if self._janela_no_periodo_noturno(self.bess_carregamento_inicio, self.bess_carregamento_fim):
            return 'madrugada'

        if self.permitir_descarga_bess and self._janela_intersecta_ponta(
            self.bess_descarga_inicio,
            self.bess_descarga_fim
        ):
            return 'solar'

        return 'solar'

    def _extrair_parametros_config(self):
        """Extrai parâmetros técnicos e econômicos de Entradas.json."""
        painel = self.config.get('painel_info', [{}])[0]
        bateria = self.config.get('bateria_info', [{}])[0]
        diesel = self.config.get('geradordiesel_info', [{}])[0]
        carga = self.config.get('cargas_info', [{}])[0]
        inv = self.config.get('tarifas_energia', {}).get('custos_investimento', {})
        inversor = self.config.get('inversor_info', [{}])[0]

        qtd_painel = painel.get('quantidade', 0)
        if isinstance(qtd_painel, list):
            qtd_total = 1
            for valor in qtd_painel:
                qtd_total *= max(int(valor), 1)
        else:
            qtd_total = max(int(qtd_painel or 0), 0)

        potencia_pv_calc = (painel.get('Pmp', 0) * qtd_total) / 1000
        capacidade_bess_calc = bateria.get('capacidade_kwh', 0) * max(int(bateria.get('quantidade', 1)), 1)
        potencia_bess_calc = max(
            bateria.get('potencia_max_carga_kw', 0),
            bateria.get('potencia_max_descarga_kw', 0)
        ) * max(int(bateria.get('quantidade', 1)), 1)

        self.potencia_pv_kwp = float(self.pv_kwp_override) if self.pv_kwp_override is not None else potencia_pv_calc
        self.capacidade_bess_kwh = float(self.bess_kwh_override) if self.bess_kwh_override is not None else capacidade_bess_calc
        self.potencia_bess_kw = float(self.bess_kw_override) if self.bess_kw_override is not None else potencia_bess_calc
        self.soc_inicial_percent = bateria.get('soc_inicial', 50)

        self.potencia_diesel_kw = diesel.get('potencia_nominal_kw', 0) * max(int(diesel.get('quantidade', 1)), 1)
        self.custo_diesel_investimento = diesel.get('custo_investimento', 0) * max(int(diesel.get('quantidade', 1)), 1)
        self.custo_diesel_litro_entrada = diesel.get('custo_diesel_litro', 6.5)
        self.modo_operacao_diesel = diesel.get('operacao', {}).get('modo_operacao', 'backup')

        self.perfil_carga_csv = self.curva_carga_csv_override or carga.get('curva_carga', 'perfil_carga_horaria.csv')
        self.perfil_carga = PerfilCarga(self.perfil_carga_csv)
        self.escala_carga = float(self.escala_carga_override) if self.escala_carga_override is not None else float(carga.get('fator_escala_curva', 1.0))

        self.custo_pv_kwp_entrada = inv.get('pv_kwp', 3500)
        self.custo_bess_kwh_entrada = inv.get('bess_kwh', 2500)

        periodo_carga = bateria.get('periodo_de_carga', {})
        periodo_descarga = bateria.get('periodo_de_descarga', {})

        self.permitir_carga_bess = periodo_carga.get('permitir_carga', True)
        self.permitir_descarga_bess = periodo_descarga.get('permitir_descarga', True)

        janela_carga = periodo_carga.get('horario_carga_permitido', '00:00-05:00')
        janela_descarga = periodo_descarga.get('horario_descarga_permitido', '18:00-21:00')

        (
            self.bess_carregamento_inicio,
            self.bess_carregamento_fim,
            self.carga_dia_inteiro,
        ) = self._parse_janela_horaria(janela_carga)
        (
            self.bess_descarga_inicio,
            self.bess_descarga_fim,
            self.descarga_dia_inteiro,
        ) = self._parse_janela_horaria(janela_descarga)

        self.estrategia_bess = self._inferir_estrategia_bess()

    def _calcular_receita_exportacao(self, energia_kwh, hora, dia_semana):
        """Calcula receita de exportação usando SCEE da ANEEL."""
        is_ponta = TarifasANEEL.is_horario_ponta(hora, dia_semana)
        scee = self.tarifas_aneel.dados_tarifa.get('scee', {})
        mod_key = self.modalidade.lower()
        scee_mod = scee.get(mod_key, {})

        if scee_mod:
            if is_ponta:
                tarifa_base = scee_mod.get('te_ponta', 0) + scee_mod.get('tusd_ponta', 0)
            else:
                tarifa_base = scee_mod.get('te_fora_ponta', 0) + scee_mod.get('tusd_fora_ponta', 0)
            if tarifa_base > 0:
                tarifa_venda = tarifa_base * 0.9
            else:
                tarifa_venda = self._tarifa_compra_horaria(hora, dia_semana) * 0.9
        else:
            tarifa_venda = self._tarifa_compra_horaria(hora, dia_semana) * 0.7

        tarifa_venda *= (1 + self.icms + self.pis)
        return energia_kwh * tarifa_venda

    def _tarifa_compra_horaria(self, hora, dia_semana):
        """Retorna tarifa de compra (TE + TUSD consumo) por horário."""
        is_ponta = TarifasANEEL.is_horario_ponta(hora, dia_semana)
        if is_ponta:
            return self.tarifas.get('te_ponta', 0) + self.tarifas.get('tusd_ponta_consumo', 0)
        return self.tarifas.get('te_fora_ponta', 0) + self.tarifas.get('tusd_fora_ponta_consumo', 0)

    def _calcular_demanda_mensal(self, resultado_mes):
        """Calcula custo mensal de demanda a partir do perfil de troca com a rede."""
        res_util = resultado_mes['resultado_dia_util']
        res_fds = resultado_mes['resultado_fim_semana']

        demanda_ponta = 0.0
        demanda_fora_ponta = 0.0

        for hora, e_rede in enumerate(res_util['energia_rede_kw']):
            if e_rede <= 0:
                continue
            if TarifasANEEL.is_horario_ponta(hora, dia_semana=0):
                demanda_ponta = max(demanda_ponta, e_rede)
            else:
                demanda_fora_ponta = max(demanda_fora_ponta, e_rede)

        for e_rede in res_fds['energia_rede_kw']:
            if e_rede > 0:
                demanda_fora_ponta = max(demanda_fora_ponta, e_rede)

        margem = 1.10
        if self.modalidade == 'azul':
            return (
                demanda_ponta * margem * self.tarifas.get('tusd_ponta_demanda', 0) +
                demanda_fora_ponta * margem * self.tarifas.get('tusd_fora_ponta_demanda', 0)
            )

        demanda_max = max(demanda_ponta, demanda_fora_ponta) * margem
        return demanda_max * self.tarifas.get('tusd_demanda', 0)

    def _calcular_custo_energia_sem_micro(self):
        """Calcula custo anual sem geração/local storage usando perfil de carga."""
        energia_ponta = 0.0
        energia_fora_ponta = 0.0
        demanda_ponta = 0.0
        demanda_fora_ponta = 0.0

        for hora in range(24):
            carga_kw = self.perfil_carga.get_demanda(hora, dia_semana=0)
            if TarifasANEEL.is_horario_ponta(hora, dia_semana=0):
                energia_ponta += carga_kw * 260
                demanda_ponta = max(demanda_ponta, carga_kw)
            else:
                energia_fora_ponta += carga_kw * 260
                demanda_fora_ponta = max(demanda_fora_ponta, carga_kw)

        for hora in range(24):
            carga_kw = self.perfil_carga.get_demanda(hora, dia_semana=6) 
            energia_fora_ponta += carga_kw * 105
            demanda_fora_ponta = max(demanda_fora_ponta, carga_kw)

        tarifa_ponta = self.tarifas.get('te_ponta', 0) + self.tarifas.get('tusd_ponta_consumo', 0)
        tarifa_fp = self.tarifas.get('te_fora_ponta', 0) + self.tarifas.get('tusd_fora_ponta_consumo', 0)

        custo_energia = (energia_ponta * tarifa_ponta + energia_fora_ponta * tarifa_fp) * (1 + self.icms + self.pis)

        margem = 1.10
        if self.modalidade == 'azul':
            custo_demanda = (
                demanda_ponta * margem * self.tarifas.get('tusd_ponta_demanda', 0) +
                demanda_fora_ponta * margem * self.tarifas.get('tusd_fora_ponta_demanda', 0)
            ) * 12
            demanda_ref = max(demanda_ponta, demanda_fora_ponta) * margem
        else:
            demanda_ref = max(demanda_ponta, demanda_fora_ponta) * margem
            custo_demanda = demanda_ref * self.tarifas.get('tusd_demanda', 0) * 12

        return {
            'energia_ponta_kwh': energia_ponta,
            'energia_fora_ponta_kwh': energia_fora_ponta,
            'energia_kwh': energia_ponta + energia_fora_ponta,
            'demanda_kw': demanda_ref,
            'custo_energia': custo_energia,
            'custo_demanda': custo_demanda,
            'custo_total': custo_energia + custo_demanda
        }
        
    def executar_simulacao_powerflow(self):
        """Executa simulação mensal com estratégia evoluída de operação."""
        print("=" * 80)
        print("EXECUTANDO SIMULAÇÃO DE FLUXO DE POTÊNCIA")
        print("=" * 80)

        self.microrrede = CasoIFG(
            distribuidora=self.distribuidora,
            modalidade=self.modalidade,
            estrategia_bess=self.estrategia_bess,
            bess_carregamento_inicio=self.bess_carregamento_inicio,
            bess_carregamento_fim=self.bess_carregamento_fim,
            icms=self.icms,
            pis=self.pis,
            aplicar_impostos_exportacao=False,
            perfil_carga_csv=self.perfil_carga_csv,
            escala_carga=self.escala_carga,
        )

        self.microrrede.pv_potencia_kwp = self.potencia_pv_kwp
        self.microrrede._configurar_pv()
        self.microrrede.bess_capacidade_kwh = self.capacidade_bess_kwh
        self.microrrede.bess_potencia_kw = self.potencia_bess_kw

        self.resultado_mes_com_bess = self.microrrede.simular_mes()
        self.resultado_mes_sem_bess = self.microrrede.calcular_cenario_sem_bess()
        
        print("\nSimulação de fluxo de potência concluída!")
        
    def calcular_custos_sem_microrrede(self):
        """
        Calcula os custos anuais do cenário base de comparação.
        Quando há resultado do CasoIFG, usa cenário SEM BESS (PV existente).
        Caso contrário, usa fallback legado sem microrrede.
        """
        if self.resultado_mes_sem_bess is not None:
            custo_energia_liquida_ano = self.resultado_mes_sem_bess['custo_mensal'] * 12
            custo_demanda_ano = 0.0
            demanda_max_kw = self._calcular_demanda_mensal(self.resultado_mes_sem_bess) / max(self.tarifa_demanda_kw, 1e-6)

            return {
                'energia_ponta_kwh': 0.0,
                'energia_fora_ponta_kwh': 0.0,
                'energia_kwh': self.resultado_mes_sem_bess['energia_comprada_kwh'] * 12,
                'demanda_kw': demanda_max_kw,
                'custo_energia': custo_energia_liquida_ano,
                'custo_demanda': custo_demanda_ano,
                'custo_total': custo_energia_liquida_ano + custo_demanda_ano
            }

        return self._calcular_custo_energia_sem_micro()
    
    def calcular_custos_com_microrrede(self):
        """
        Calcula os custos anuais COM a microrrede
        Baseado nos resultados do fluxo de potência
        """
        if self.microrrede is None or self.resultado_mes_com_bess is None:
            raise ValueError("Execute primeiro a simulação de fluxo de potência!")

        custo_energia_liquida_ano = self.resultado_mes_com_bess['custo_mensal'] * 12
        energia_comprada_ano = self.resultado_mes_com_bess['energia_comprada_kwh'] * 12
        energia_vendida_ano = self.resultado_mes_com_bess['energia_vendida_kwh'] * 12

        custo_demanda_ano = 0.0

        energia_diesel_ano = 0.0
        custo_diesel = energia_diesel_ano * self.consumo_diesel_l_kwh * self.custo_diesel_litro

        custo_total_anual = custo_energia_liquida_ano + custo_demanda_ano + custo_diesel

        demanda_max_kw = self._calcular_demanda_mensal(self.resultado_mes_com_bess) / max(self.tarifa_demanda_kw, 1e-6)
        
        return {
            'energia_comprada_kwh': energia_comprada_ano,
            'energia_vendida_kwh': energia_vendida_ano,
            'energia_diesel_kwh': energia_diesel_ano,
            'demanda_max_kw': demanda_max_kw,
            'custo_energia_comprada': custo_energia_liquida_ano,
            'receita_energia_vendida': 0.0,
            'custo_demanda': custo_demanda_ano,
            'custo_diesel': custo_diesel,
            'custo_total': custo_total_anual
        }
    
    def calcular_capex(self):
        """Calcula o investimento inicial (CAPEX)"""
        # Capacidades instaladas
        potencia_pv_kw = self.potencia_pv_kwp
        capacidade_bess_kwh = self.capacidade_bess_kwh
        usar_diesel = bool(getattr(self.microrrede, 'usar_diesel', False))
        potencia_diesel_kw = self.potencia_diesel_kw if usar_diesel else 0.0
        
        # Custos de equipamentos
        custo_pv = potencia_pv_kw * self.custo_pv_kw if self.incluir_pv_no_capex else 0.0
        custo_bess = capacidade_bess_kwh * self.custo_bess_kwh
        if usar_diesel:
            custo_diesel = self.custo_diesel_investimento if self.custo_diesel_investimento > 0 else (potencia_diesel_kw * self.custo_diesel_kw)
        else:
            custo_diesel = 0.0
        
        # No caso incremental IFG (PV existente e sem diesel), usar apenas investimento do BESS.
        if (not self.incluir_pv_no_capex) and (not usar_diesel):
            custo_equipamentos = custo_bess
            custos_adicionais = 0.0
        else:
            # Custos adicionais (15% do total de equipamentos)
            custo_equipamentos = custo_pv + custo_bess + custo_diesel
            custos_adicionais = custo_equipamentos * 0.15  # Projeto, instalação, etc.
        
        capex_total = custo_equipamentos + custos_adicionais
        
        return {
            'custo_pv': custo_pv,
            'custo_bess': custo_bess,
            'custo_diesel': custo_diesel,
            'custos_adicionais': custos_adicionais,
            'capex_total': capex_total,
            'potencia_pv_kw': potencia_pv_kw,
            'pv_considerado_no_capex': self.incluir_pv_no_capex,
            'capacidade_bess_kwh': capacidade_bess_kwh,
            'potencia_diesel_kw': potencia_diesel_kw
        }
    
    def calcular_economia_anual(self, ano=1):
        """
        Calcula a economia anual para um ano específico
        Considera degradação do PV e escalada de tarifa
        """
        custos_base = self.calcular_custos_sem_microrrede()
        custos_micro = self.calcular_custos_com_microrrede()
        capex_info = self.calcular_capex()
        
        # Ajustar pela degradação do PV e escalada de tarifa
        fator_degradacao = (1 - self.degradacao_pv_anual) ** (ano - 1)
        fator_tarifa = (1 + self.escalada_tarifa) ** (ano - 1)
        
        # Custos ajustados
        custo_base_ajustado = custos_base['custo_total'] * fator_tarifa
        
        # Economia reduzida pela degradação do PV
        economia_nominal = custos_base['custo_total'] - custos_micro['custo_total']
        economia_ajustada = economia_nominal * fator_degradacao * fator_tarifa
        
        # Custo de O&M
        custo_om = capex_info['capex_total'] * self.custo_om_anual_percent
        
        # Fluxo de caixa líquido
        fluxo_caixa_liquido = economia_ajustada - custo_om
        
        return {
            'economia_bruta': economia_ajustada,
            'custo_om': custo_om,
            'fluxo_caixa_liquido': fluxo_caixa_liquido,
            'fator_degradacao': fator_degradacao,
            'fator_tarifa': fator_tarifa
        }
    
    def calcular_vpl(self):
        """Calcula o Valor Presente Líquido (VPL)"""
        capex_info = self.calcular_capex()
        investimento_inicial = capex_info['capex_total']
        
        # Fluxos de caixa anuais
        fluxos_caixa = [-investimento_inicial]
        
        for ano in range(1, self.vida_util + 1):
            economia = self.calcular_economia_anual(ano)
            fluxos_caixa.append(economia['fluxo_caixa_liquido'])
        
        # Calcular VPL
        vpl = npf.npv(self.taxa_desconto, fluxos_caixa)
        
        return vpl, fluxos_caixa
    
    def calcular_tir(self):
        """Calcula a Taxa Interna de Retorno (TIR)"""
        _, fluxos_caixa = self.calcular_vpl()
        tir = npf.irr(fluxos_caixa)
        return tir
    
    def calcular_payback_descontado(self):
        """Calcula o período de payback descontado"""
        _, fluxos_caixa = self.calcular_vpl()
        
        # Descontar fluxos de caixa
        fluxos_descontados = [fluxo / (1 + self.taxa_desconto) ** i 
                             for i, fluxo in enumerate(fluxos_caixa)]
        
        # Saldo acumulado
        saldo_acumulado = np.cumsum(fluxos_descontados)
        
        # Encontrar payback
        if any(saldo_acumulado >= 0):
            payback = np.argmax(saldo_acumulado >= 0)
        else:
            payback = np.inf
        
        return payback, saldo_acumulado

    def calcular_payback_simples(self):
        """Calcula payback simples no padrão CasoIFG (investimento / economia anual bruta)."""
        capex_info = self.calcular_capex()
        investimento_inicial = capex_info['capex_total']
        custos_base = self.calcular_custos_sem_microrrede()
        custos_micro = self.calcular_custos_com_microrrede()
        economia_bruta_anual = custos_base['custo_total'] - custos_micro['custo_total']
        if economia_bruta_anual <= 0:
            return np.inf
        return investimento_inicial / economia_bruta_anual
    
    def gerar_relatorio_completo(self):
        """Gera relatório financeiro completo"""
        print("\n" + "=" * 80)
        print("ANÁLISE FINANCEIRA DA MICRORREDE")
        print("=" * 80)
        
        # Custos sem microrrede
        custos_base = self.calcular_custos_sem_microrrede()
        print("\n1. CENÁRIO BASE (SEM BESS - PV EXISTENTE)")
        print("-" * 80)
        print(f"   Energia consumida anual: {custos_base['energia_kwh']:,.0f} kWh")
        print(f"   Demanda contratada: {custos_base['demanda_kw']:.1f} kW")
        print(f"   Custo de energia: R$ {custos_base['custo_energia']:,.2f}")
        print(f"   Custo de demanda: R$ {custos_base['custo_demanda']:,.2f}")
        print(f"   CUSTO TOTAL ANUAL: R$ {custos_base['custo_total']:,.2f}")
        
        # Custos com microrrede
        custos_micro = self.calcular_custos_com_microrrede()
        print("\n2. CENÁRIO COM BESS (PV EXISTENTE)")
        print("-" * 80)
        print(f"   Energia comprada: {custos_micro['energia_comprada_kwh']:,.0f} kWh")
        print(f"   Energia vendida: {custos_micro['energia_vendida_kwh']:,.0f} kWh")
        print(f"   Energia gerada pelo diesel: {custos_micro['energia_diesel_kwh']:,.0f} kWh")
        print(f"   Demanda máxima: {custos_micro['demanda_max_kw']:.1f} kW")
        print(f"   Custo de energia comprada: R$ {custos_micro['custo_energia_comprada']:,.2f}")
        print(f"   Receita de energia vendida: R$ {custos_micro['receita_energia_vendida']:,.2f}")
        print(f"   Custo de demanda: R$ {custos_micro['custo_demanda']:,.2f}")
        print(f"   Custo de diesel: R$ {custos_micro['custo_diesel']:,.2f}")
        print(f"   CUSTO TOTAL ANUAL: R$ {custos_micro['custo_total']:,.2f}")
        
        # Economia
        economia_anual = custos_base['custo_total'] - custos_micro['custo_total']
        percentual_reducao = (economia_anual / custos_base['custo_total']) * 100
        
        print("\n3. ECONOMIA ANUAL")
        print("-" * 80)
        print(f"   Economia bruta: R$ {economia_anual:,.2f}")
        print(f"   Redução percentual: {percentual_reducao:.1f}%")
        
        # CAPEX
        capex_info = self.calcular_capex()
        print("\n4. INVESTIMENTO INICIAL (CAPEX)")
        print("-" * 80)
        if capex_info['pv_considerado_no_capex']:
            print(f"   Sistema Fotovoltaico ({capex_info['potencia_pv_kw']:.1f} kW): "
                  f"R$ {capex_info['custo_pv']:,.2f}")
        else:
            print(f"   Sistema Fotovoltaico ({capex_info['potencia_pv_kw']:.1f} kW): "
                  f"R$ {capex_info['custo_pv']:,.2f} (existente, não contabilizado no CAPEX)")
        print(f"   Sistema de Baterias ({capex_info['capacidade_bess_kwh']:.0f} kWh): "
              f"R$ {capex_info['custo_bess']:,.2f}")
        print(f"   Gerador Diesel ({capex_info['potencia_diesel_kw']:.0f} kW): "
              f"R$ {capex_info['custo_diesel']:,.2f}")
        print(f"   Custos adicionais (projeto, instalação, etc.): "
              f"R$ {capex_info['custos_adicionais']:,.2f}")
        print(f"   CAPEX TOTAL: R$ {capex_info['capex_total']:,.2f}")
        
        # Indicadores econômicos
        vpl, _ = self.calcular_vpl()
        tir = self.calcular_tir()
        payback, _ = self.calcular_payback_descontado()
        payback_simples = self.calcular_payback_simples()
        
        print("\n5. INDICADORES ECONÔMICOS")
        print("-" * 80)
        print(f"   Vida útil do projeto: {self.vida_util} anos")
        print(f"   Taxa de desconto: {self.taxa_desconto * 100:.1f}%")
        print(f"   VPL (Valor Presente Líquido): R$ {vpl:,.2f}")
        print(f"   TIR (Taxa Interna de Retorno): {tir * 100:.2f}%")
        if payback_simples != np.inf:
            print(f"   Payback Simples: {payback_simples:.1f} anos")
        else:
            print(f"   Payback Simples: Não atingido")
        
        if payback != np.inf:
            print(f"   Payback Descontado: {payback} anos")
        else:
            print(f"   Payback Descontado: Não atingido em {self.vida_util} anos")
        
        # Análise de viabilidade
        print("\n6. ANÁLISE DE VIABILIDADE")
        print("-" * 80)
        
        if vpl > 0:
            print(f"   ✓ VPL POSITIVO: Projeto é economicamente viável!")
        else:
            print(f"   ✗ VPL NEGATIVO: Projeto não é viável nas condições atuais.")
        
        if tir > self.taxa_desconto:
            print(f"   ✓ TIR ({tir*100:.2f}%) > Taxa de desconto ({self.taxa_desconto*100:.1f}%): "
                  f"Projeto atrativo!")
        else:
            print(f"   ✗ TIR ({tir*100:.2f}%) < Taxa de desconto ({self.taxa_desconto*100:.1f}%): "
                  f"Retorno insuficiente.")
        
        if payback != np.inf and payback <= self.vida_util / 2:
            print(f"   ✓ Payback de {payback} anos é aceitável.")
        elif payback != np.inf:
            print(f"   ⚠ Payback de {payback} anos é longo.")
        else:
            print(f"   ✗ Payback não atingido.")
        
        print("\n" + "=" * 80)
        
        # Armazenar resultados
        self.resultados_economicos = {
            'custos_base': custos_base,
            'custos_micro': custos_micro,
            'capex': capex_info,
            'economia_anual': economia_anual,
            'vpl': vpl,
            'tir': tir,
            'payback': payback,
            'payback_simples': payback_simples
        }
    
    def plotar_analise_financeira(self):
        """Gera gráficos da análise financeira"""
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        
        # Gráfico 1: Comparação de custos anuais
        ax1 = axes[0, 0]
        custos_base = self.resultados_economicos['custos_base']
        custos_micro = self.resultados_economicos['custos_micro']
        
        custo_mensal_sem_bess = self.resultado_mes_sem_bess['custo_mensal']
        custo_mensal_com_bess = self.resultado_mes_com_bess['custo_mensal']

        categorias = ['Sem\nBESS', 'Com\nBESS']
        valores = [custo_mensal_sem_bess, custo_mensal_com_bess]
        cores = ['#cc4c4c', '#2d8a4b']
        
        bars = ax1.bar(categorias, valores, color=cores, alpha=0.7, edgecolor='black', linewidth=2)
        ax1.set_ylabel('Custo Mensal (R$)', fontsize=12)
        ax1.set_title('Caso IFG: Comparação Sem BESS vs Com BESS', fontsize=14, fontweight='bold')
        ax1.grid(True, alpha=0.3, axis='y')
        
        # Adicionar valores nas barras
        for bar, valor in zip(bars, valores):
            height = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width()/2., height,
                    f'R$ {valor:,.0f}/mês',
                    ha='center', va='bottom', fontsize=11, fontweight='bold')
        
        # Adicionar economia
        economia = self.resultado_mes_sem_bess['custo_mensal'] - self.resultado_mes_com_bess['custo_mensal']
        economia_anual = economia * 12
        ax1.text(0.5, max(valores) * 0.5, 
            f'ECONOMIA\nR$ {economia:,.0f}/mês\nR$ {economia_anual:,.0f}/ano',
                ha='center', va='center', fontsize=13, fontweight='bold',
                bbox=dict(boxstyle='round,pad=0.8', facecolor='yellow', 
                         alpha=0.8, edgecolor='black', linewidth=2))
        
        # Gráfico 2: Fluxo de caixa ao longo dos anos
        ax2 = axes[0, 1]
        _, fluxos_caixa = self.calcular_vpl()
        anos = np.arange(0, self.vida_util + 1)
        
        cores_fc = ['red' if fc < 0 else 'green' for fc in fluxos_caixa]
        ax2.bar(anos, fluxos_caixa, color=cores_fc, alpha=0.7, edgecolor='black')
        ax2.axhline(y=0, color='black', linestyle='-', linewidth=1)
        ax2.set_xlabel('Ano', fontsize=12)
        ax2.set_ylabel('Fluxo de Caixa (R$)', fontsize=12)
        ax2.set_title('Fluxo de Caixa Anual', fontsize=14, fontweight='bold')
        ax2.grid(True, alpha=0.3, axis='y')
        
        # Gráfico 3: Saldo acumulado (Payback)
        ax3 = axes[1, 0]
        payback, saldo_acumulado = self.calcular_payback_descontado()
        
        ax3.plot(anos, saldo_acumulado, 'o-', linewidth=2, markersize=6, color='blue')
        ax3.axhline(y=0, color='red', linestyle='--', linewidth=2, label='Ponto de equilíbrio')
        
        if payback != np.inf:
            ax3.axvline(x=payback, color='green', linestyle='--', linewidth=2,
                       label=f'Payback: {payback} anos')
            ax3.plot(payback, saldo_acumulado[payback], 'go', markersize=15)
        
        ax3.set_xlabel('Ano', fontsize=12)
        ax3.set_ylabel('Saldo Acumulado (R$)', fontsize=12)
        ax3.set_title('Retorno do Investimento - Payback Descontado', fontsize=14, fontweight='bold')
        ax3.legend(fontsize=11)
        ax3.grid(True, alpha=0.3)
        
        # Adicionar VPL e TIR
        vpl = self.resultados_economicos['vpl']
        tir = self.resultados_economicos['tir']
        ax3.text(0.05, 0.95, f'VPL: R$ {vpl:,.0f}\nTIR: {tir*100:.2f}%',
                transform=ax3.transAxes, fontsize=11, verticalalignment='top',
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
        
        # Gráfico 4: Análise de sensibilidade da economia
        ax4 = axes[1, 1]

        # Variação da tarifa de energia (somente componentes de energia, não demanda)
        tarifas = np.linspace(0.5, 1.5, 50)
        economias = []

        custo_energia_base = custos_base['custo_energia']
        custo_demanda_base = custos_base['custo_demanda']

        custo_energia_micro = custos_micro['custo_energia_comprada']
        custo_demanda_micro = custos_micro['custo_demanda']
        custo_diesel_micro = custos_micro['custo_diesel']

        for tarifa_mult in tarifas:
            custo_total_base_temp = (custo_energia_base * tarifa_mult) + custo_demanda_base
            custo_total_micro_temp = (
                (custo_energia_micro * tarifa_mult)
                + custo_demanda_micro
                + custo_diesel_micro
            )
            economia_temp = custo_total_base_temp - custo_total_micro_temp
            economias.append(economia_temp)

        ax4.plot(tarifas, economias, linewidth=3, color='purple')
        ax4.axvline(x=1.0, color='black', linestyle='--', linewidth=2, 
                   label='Tarifa atual')
        ax4.axhline(y=0, color='red', linestyle='--', linewidth=1)
        ax4.set_xlabel('Multiplicador da Tarifa de Energia', fontsize=12)
        ax4.set_ylabel('Economia Anual (R$)', fontsize=12)
        ax4.set_title('Sensibilidade: Economia vs Tarifa de Energia', fontsize=14, fontweight='bold')
        ax4.legend(fontsize=11)
        ax4.grid(True, alpha=0.3)
        
        fig.suptitle(
            f'Analise Financeira - Caso IFG | PV {self.potencia_pv_kwp:.1f} kWp | '
            f'BESS {self.capacidade_bess_kwh:.0f} kWh/{self.potencia_bess_kw:.0f} kW',
            fontsize=14,
            fontweight='bold',
            y=1.02,
        )

        plt.tight_layout()
        plt.savefig('analise_financeira_microrrede.png', dpi=150, bbox_inches='tight')
        print("\nGráfico de análise financeira salvo como 'analise_financeira_microrrede.png'")
        plt.show()


def main():
    """Função principal para executar a análise completa."""
    parser = argparse.ArgumentParser(
        description='Executa análise financeira da microrrede usando Entradas.json e tarifas ANEEL.'
    )
    parser.add_argument('--entradas', default='Entradas.json',
                        help='Caminho do arquivo de entradas JSON.')
    parser.add_argument('--curva-carga', default=None,
                        help='Arquivo CSV da curva de carga (sobrescreve Entradas.json).')
    parser.add_argument('--distribuidora', default='EQUATORIAL GO',
                        help='Nome da distribuidora para consulta ANEEL.')
    parser.add_argument('--modalidade', default='verde', choices=['verde', 'azul'],
                        help='Modalidade tarifária.')
    parser.add_argument('--vida-util', type=int, default=20,
                        help='Vida útil do projeto (anos).')
    parser.add_argument('--taxa-desconto', type=float, default=0.08,
                        help='Taxa de desconto anual (ex: 0.08 para 8%%).')
    parser.add_argument('--pv-kwp', type=float, default=None,
                        help='Sobrescreve potência PV instalada em kWp.')
    parser.add_argument('--bess-kwh', type=float, default=None,
                        help='Sobrescreve capacidade do BESS em kWh.')
    parser.add_argument('--bess-kw', type=float, default=None,
                        help='Sobrescreve potência do BESS em kW.')
    parser.add_argument('--incluir-pv-no-capex', action='store_true',
                        help='Inclui o investimento do PV no CAPEX (padrão: PV existente, não incluir).')
    parser.add_argument('--escala-carga', type=float, default=None,
                        help='Fator multiplicador da curva de carga (ex: 0.1).')
    args = parser.parse_args()

    print("=" * 80)
    print("SISTEMA DE ANÁLISE FINANCEIRA DE MICRORREDE")
    print("=" * 80)
    
    # Criar análise financeira com dados de entrada e ANEEL
    analise = AnaliseFinanceiraMicrorrede(
        entradas_path=args.entradas,
        curva_carga_csv=args.curva_carga,
        distribuidora=args.distribuidora,
        modalidade=args.modalidade,
        vida_util=args.vida_util,
        taxa_desconto=args.taxa_desconto,
        pv_kwp=args.pv_kwp,
        bess_kwh=args.bess_kwh,
        bess_kw=args.bess_kw,
        incluir_pv_no_capex=args.incluir_pv_no_capex,
        escala_carga=args.escala_carga
    )
    
    # Executar simulação de fluxo de potência
    analise.executar_simulacao_powerflow()
    
    # Gerar relatório completo
    analise.gerar_relatorio_completo()
    
    # Plotar análises
    analise.plotar_analise_financeira()
    
    # Plotar resultados detalhados do caso simulado (dia útil)
    analise.microrrede.gerar_graficos(analise.resultado_mes_com_bess['resultado_dia_util'], titulo='Dia Útil')
    
    print("\n" + "=" * 80)
    print("ANÁLISE CONCLUÍDA COM SUCESSO!")
    print("=" * 80)


if __name__ == "__main__":
    main()
