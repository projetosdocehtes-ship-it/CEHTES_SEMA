"""
Módulo de Análise Financeira para Microrrede
Versão adaptada para uso com Django.
"""

import json
import uuid
from io import BytesIO
from pathlib import Path

import numpy as np
import numpy_financial as npf
import matplotlib

matplotlib.use("Agg")  # importante para servidor Django sem interface gráfica
import matplotlib.pyplot as plt

from django.conf import settings

from apps.AnaliseEconomica.caso_ifg import CasoIFG
from apps.AnaliseEconomica.perfil_carga import PerfilCarga
from apps.AnaliseEconomica.tarifas_aneel import TarifasANEEL


class AnaliseFinanceiraMicrorrede:
    def __init__(
        self,
        entradas_path="Entradas.json",
        distribuidora="EQUATORIAL GO",
        modalidade="verde",
        vida_util=20,
        taxa_desconto=0.08,
        curva_carga_csv=None,
        pv_kwp=None,
        bess_kwh=None,
        bess_kw=None,
    ):
        self.entradas_path = Path(entradas_path)
        self.distribuidora = distribuidora
        self.modalidade = modalidade.lower()
        self.vida_util = vida_util
        self.taxa_desconto = taxa_desconto
        self.curva_carga_csv_override = curva_carga_csv
        self.pv_kwp_override = pv_kwp
        self.bess_kwh_override = bess_kwh
        self.bess_kw_override = bess_kw

        self.config = self._carregar_entradas()
        self._extrair_parametros_config()

        self.tarifas_aneel = TarifasANEEL(self.distribuidora, usar_api=True)
        if self.modalidade == "azul":
            self.tarifas = self.tarifas_aneel.get_tarifas_azul()
        else:
            self.tarifas = self.tarifas_aneel.get_tarifas_verde()

        self.tarifa_energia_kwh = (
            self.tarifas.get("te_ponta", 0)
            + self.tarifas.get("te_fora_ponta", 0)
            + self.tarifas.get("tusd_ponta_consumo", 0)
            + self.tarifas.get("tusd_fora_ponta_consumo", 0)
        ) / 2

        if self.modalidade == "azul":
            self.tarifa_demanda_kw = (
                self.tarifas.get("tusd_ponta_demanda", 0)
                + self.tarifas.get("tusd_fora_ponta_demanda", 0)
            ) / 2
        else:
            self.tarifa_demanda_kw = self.tarifas.get("tusd_demanda", 0)

        self.custo_pv_kw = self.custo_pv_kwp_entrada
        self.custo_bess_kwh = self.custo_bess_kwh_entrada
        self.custo_diesel_kw = 1200

        self.custo_om_anual_percent = 0.02
        self.custo_diesel_litro = self.custo_diesel_litro_entrada
        self.consumo_diesel_l_kwh = 0.25

        impostos_cfg = self.config.get("tarifas_energia", {}).get("impostos", {})
        self.icms = float(impostos_cfg.get("icms", 0.0))
        self.pis = float(impostos_cfg.get("pis", 0.0))

        self.degradacao_pv_anual = 0.005
        self.escalada_tarifa = 0.04

        self.microrrede = None
        self.resultado_mes_com_bess = None
        self.resultado_mes_sem_bess = None
        self.resultados_economicos = {}

    def _carregar_entradas(self):
        if not self.entradas_path.exists():
            raise FileNotFoundError(f"Arquivo não encontrado: {self.entradas_path}")

        with self.entradas_path.open("r", encoding="utf-8") as f:
            return json.load(f)

    @staticmethod
    def _parse_janela_horaria(janela):
        if not janela or "-" not in janela:
            return 0, 5, False

        inicio_str, fim_str = janela.split("-", 1)
        inicio = int(inicio_str.strip().split(":")[0])
        fim = int(fim_str.strip().split(":")[0])

        dia_inteiro = inicio == 0 and fim == 24
        if fim == 24:
            fim = 23

        return inicio, fim, dia_inteiro

    @staticmethod
    def _janela_no_periodo_noturno(inicio, fim):
        if inicio <= fim:
            horas = list(range(inicio, fim + 1))
        else:
            horas = list(range(inicio, 24)) + list(range(0, fim + 1))
        return all((h <= 6 or h >= 22) for h in horas)

    @staticmethod
    def _janela_intersecta_ponta(inicio, fim):
        if inicio <= fim:
            horas = list(range(inicio, fim + 1))
        else:
            horas = list(range(inicio, 24)) + list(range(0, fim + 1))
        return any(TarifasANEEL.is_horario_ponta(h, dia_semana=0) for h in horas)

    def _inferir_estrategia_bess(self):
        if not self.permitir_carga_bess or self.carga_dia_inteiro:
            return "solar"

        if self._janela_no_periodo_noturno(
            self.bess_carregamento_inicio, self.bess_carregamento_fim
        ):
            return "madrugada"

        if self.permitir_descarga_bess and self._janela_intersecta_ponta(
            self.bess_descarga_inicio, self.bess_descarga_fim
        ):
            return "solar"

        return "solar"

    def _extrair_parametros_config(self):
        painel = self.config.get("painel_info", [{}])[0]
        bateria = self.config.get("bateria_info", [{}])[0]
        diesel = self.config.get("geradordiesel_info", [{}])[0]
        carga = self.config.get("cargas_info", [{}])[0]
        inv = self.config.get("tarifas_energia", {}).get("custos_investimento", {})

        qtd_painel = painel.get("quantidade", 0)
        if isinstance(qtd_painel, list):
            qtd_total = 1
            for valor in qtd_painel:
                qtd_total *= max(int(valor), 1)
        else:
            qtd_total = max(int(qtd_painel or 0), 0)

        potencia_pv_calc = (painel.get("Pmp", 0) * qtd_total) / 1000
        capacidade_bess_calc = bateria.get("capacidade_kwh", 0) * max(
            int(bateria.get("quantidade", 1)), 1
        )
        potencia_bess_calc = max(
            bateria.get("potencia_max_carga_kw", 0),
            bateria.get("potencia_max_descarga_kw", 0),
        ) * max(int(bateria.get("quantidade", 1)), 1)

        self.potencia_pv_kwp = (
            float(self.pv_kwp_override)
            if self.pv_kwp_override is not None
            else potencia_pv_calc
        )
        self.capacidade_bess_kwh = (
            float(self.bess_kwh_override)
            if self.bess_kwh_override is not None
            else capacidade_bess_calc
        )
        self.potencia_bess_kw = (
            float(self.bess_kw_override)
            if self.bess_kw_override is not None
            else potencia_bess_calc
        )
        self.soc_inicial_percent = bateria.get("soc_inicial", 50)

        self.potencia_diesel_kw = diesel.get("potencia_nominal_kw", 0) * max(
            int(diesel.get("quantidade", 1)), 1
        )
        self.custo_diesel_investimento = diesel.get("custo_investimento", 0) * max(
            int(diesel.get("quantidade", 1)), 1
        )
        self.custo_diesel_litro_entrada = diesel.get("custo_diesel_litro", 6.5)
        self.modo_operacao_diesel = diesel.get("operacao", {}).get(
            "modo_operacao", "backup"
        )

        self.perfil_carga_csv = self.curva_carga_csv_override or carga.get(
            "curva_carga", "perfil_carga_horaria.csv"
        )
        
        #self.perfil_carga = PerfilCarga(self.perfil_carga_csv)
        json_path = Path(settings.BASE_DIR) / "apps" / "AnaliseEconomica" / "Arquivos_Temp_Json" / str(self.perfil_carga_csv)
        self.perfil_carga = PerfilCarga(json_path)

        self.custo_pv_kwp_entrada = inv.get("pv_kwp", 3500)
        self.custo_bess_kwh_entrada = inv.get("bess_kwh", 2500)

        periodo_carga = bateria.get("periodo_de_carga", {})
        periodo_descarga = bateria.get("periodo_de_descarga", {})

        self.permitir_carga_bess = periodo_carga.get("permitir_carga", True)
        self.permitir_descarga_bess = periodo_descarga.get("permitir_descarga", True)

        janela_carga = periodo_carga.get("horario_carga_permitido", "00:00-05:00")
        janela_descarga = periodo_descarga.get(
            "horario_descarga_permitido", "18:00-21:00"
        )

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

    def _calcular_demanda_mensal(self, resultado_mes):
        res_util = resultado_mes["resultado_dia_util"]
        res_fds = resultado_mes["resultado_fim_semana"]

        demanda_ponta = 0.0
        demanda_fora_ponta = 0.0

        for hora, e_rede in enumerate(res_util["energia_rede_kw"]):
            if e_rede <= 0:
                continue
            if TarifasANEEL.is_horario_ponta(hora, dia_semana=0):
                demanda_ponta = max(demanda_ponta, e_rede)
            else:
                demanda_fora_ponta = max(demanda_fora_ponta, e_rede)

        for e_rede in res_fds["energia_rede_kw"]:
            if e_rede > 0:
                demanda_fora_ponta = max(demanda_fora_ponta, e_rede)

        margem = 1.10
        if self.modalidade == "azul":
            return (
                demanda_ponta * margem * self.tarifas.get("tusd_ponta_demanda", 0)
                + demanda_fora_ponta
                * margem
                * self.tarifas.get("tusd_fora_ponta_demanda", 0)
            )

        demanda_max = max(demanda_ponta, demanda_fora_ponta) * margem
        return demanda_max * self.tarifas.get("tusd_demanda", 0)

    def _calcular_custo_energia_sem_micro(self):
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

        tarifa_ponta = self.tarifas.get("te_ponta", 0) + self.tarifas.get(
            "tusd_ponta_consumo", 0
        )
        tarifa_fp = self.tarifas.get("te_fora_ponta", 0) + self.tarifas.get(
            "tusd_fora_ponta_consumo", 0
        )

        custo_energia = (
            energia_ponta * tarifa_ponta + energia_fora_ponta * tarifa_fp
        ) * (1 + self.icms + self.pis)

        margem = 1.10
        if self.modalidade == "azul":
            custo_demanda = (
                demanda_ponta * margem * self.tarifas.get("tusd_ponta_demanda", 0)
                + demanda_fora_ponta
                * margem
                * self.tarifas.get("tusd_fora_ponta_demanda", 0)
            ) * 12
            demanda_ref = max(demanda_ponta, demanda_fora_ponta) * margem
        else:
            demanda_ref = max(demanda_ponta, demanda_fora_ponta) * margem
            custo_demanda = demanda_ref * self.tarifas.get("tusd_demanda", 0) * 12

        return {
            "energia_ponta_kwh": energia_ponta,
            "energia_fora_ponta_kwh": energia_fora_ponta,
            "energia_kwh": energia_ponta + energia_fora_ponta,
            "demanda_kw": demanda_ref,
            "custo_energia": custo_energia,
            "custo_demanda": custo_demanda,
            "custo_total": custo_energia + custo_demanda,
        }

    def executar_simulacao_powerflow(self):
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
        )

        self.microrrede.pv_potencia_kwp = self.potencia_pv_kwp
        self.microrrede._configurar_pv()
        self.microrrede.bess_capacidade_kwh = self.capacidade_bess_kwh
        self.microrrede.bess_potencia_kw = self.potencia_bess_kw

        self.resultado_mes_com_bess = self.microrrede.simular_mes()
        self.resultado_mes_sem_bess = self.microrrede.calcular_cenario_sem_bess()

    def calcular_custos_sem_microrrede(self):
        return self._calcular_custo_energia_sem_micro()

    def calcular_custos_com_microrrede(self):
        if self.microrrede is None or self.resultado_mes_com_bess is None:
            raise ValueError("Execute primeiro a simulação de fluxo de potência.")

        custo_energia_liquida_ano = self.resultado_mes_com_bess["custo_mensal"] * 12
        energia_comprada_ano = self.resultado_mes_com_bess["energia_comprada_kwh"] * 12
        energia_vendida_ano = self.resultado_mes_com_bess["energia_vendida_kwh"] * 12

        custo_demanda_ano = self._calcular_demanda_mensal(self.resultado_mes_com_bess) * 12

        energia_diesel_ano = 0.0
        custo_diesel = (
            energia_diesel_ano * self.consumo_diesel_l_kwh * self.custo_diesel_litro
        )

        custo_total_anual = custo_energia_liquida_ano + custo_demanda_ano + custo_diesel

        demanda_max_kw = self._calcular_demanda_mensal(
            self.resultado_mes_com_bess
        ) / max(self.tarifa_demanda_kw, 1e-6)

        return {
            "energia_comprada_kwh": energia_comprada_ano,
            "energia_vendida_kwh": energia_vendida_ano,
            "energia_diesel_kwh": energia_diesel_ano,
            "demanda_max_kw": demanda_max_kw,
            "custo_energia_comprada": custo_energia_liquida_ano,
            "receita_energia_vendida": 0.0,
            "custo_demanda": custo_demanda_ano,
            "custo_diesel": custo_diesel,
            "custo_total": custo_total_anual,
        }

    def calcular_capex(self):
        potencia_pv_kw = self.potencia_pv_kwp
        capacidade_bess_kwh = self.capacidade_bess_kwh
        potencia_diesel_kw = self.potencia_diesel_kw

        custo_pv = potencia_pv_kw * self.custo_pv_kw
        custo_bess = capacidade_bess_kwh * self.custo_bess_kwh
        custo_diesel = (
            self.custo_diesel_investimento
            if self.custo_diesel_investimento > 0
            else (potencia_diesel_kw * self.custo_diesel_kw)
        )

        custo_equipamentos = custo_pv + custo_bess + custo_diesel
        custos_adicionais = custo_equipamentos * 0.15
        capex_total = custo_equipamentos + custos_adicionais

        return {
            "custo_pv": custo_pv,
            "custo_bess": custo_bess,
            "custo_diesel": custo_diesel,
            "custos_adicionais": custos_adicionais,
            "capex_total": capex_total,
            "potencia_pv_kw": potencia_pv_kw,
            "capacidade_bess_kwh": capacidade_bess_kwh,
            "potencia_diesel_kw": potencia_diesel_kw,
        }

    def calcular_economia_anual(self, ano=1):
        custos_base = self.calcular_custos_sem_microrrede()
        custos_micro = self.calcular_custos_com_microrrede()
        capex_info = self.calcular_capex()

        fator_degradacao = (1 - self.degradacao_pv_anual) ** (ano - 1)
        fator_tarifa = (1 + self.escalada_tarifa) ** (ano - 1)

        economia_nominal = custos_base["custo_total"] - custos_micro["custo_total"]
        economia_ajustada = economia_nominal * fator_degradacao * fator_tarifa
        custo_om = capex_info["capex_total"] * self.custo_om_anual_percent
        fluxo_caixa_liquido = economia_ajustada - custo_om

        return {
            "economia_bruta": economia_ajustada,
            "custo_om": custo_om,
            "fluxo_caixa_liquido": fluxo_caixa_liquido,
            "fator_degradacao": fator_degradacao,
            "fator_tarifa": fator_tarifa,
        }

    def calcular_vpl(self):
        capex_info = self.calcular_capex()
        investimento_inicial = capex_info["capex_total"]

        fluxos_caixa = [-investimento_inicial]
        for ano in range(1, self.vida_util + 1):
            economia = self.calcular_economia_anual(ano)
            fluxos_caixa.append(economia["fluxo_caixa_liquido"])

        vpl = npf.npv(self.taxa_desconto, fluxos_caixa)
        return vpl, fluxos_caixa

    def calcular_tir(self):
        _, fluxos_caixa = self.calcular_vpl()
        return npf.irr(fluxos_caixa)

    def calcular_payback_descontado(self):
        _, fluxos_caixa = self.calcular_vpl()
        fluxos_descontados = [
            fluxo / (1 + self.taxa_desconto) ** i
            for i, fluxo in enumerate(fluxos_caixa)
        ]
        saldo_acumulado = np.cumsum(fluxos_descontados)

        if any(saldo_acumulado >= 0):
            payback = int(np.argmax(saldo_acumulado >= 0))
        else:
            payback = np.inf

        return payback, saldo_acumulado

    def gerar_relatorio_dict(self):
        custos_base = self.calcular_custos_sem_microrrede()
        custos_micro = self.calcular_custos_com_microrrede()
        capex_info = self.calcular_capex()
        vpl, fluxos_caixa = self.calcular_vpl()
        tir = self.calcular_tir()
        payback, saldo_acumulado = self.calcular_payback_descontado()

        economia_anual = custos_base["custo_total"] - custos_micro["custo_total"]
        percentual_reducao = (
            (economia_anual / custos_base["custo_total"]) * 100
            if custos_base["custo_total"] > 0
            else 0
        )

        self.resultados_economicos = {
            "custos_base": custos_base,
            "custos_micro": custos_micro,
            "capex": capex_info,
            "economia_anual": economia_anual,
            "percentual_reducao": percentual_reducao,
            "vpl": vpl,
            "tir": tir,
            "payback": payback,
            "fluxos_caixa": fluxos_caixa,
            "saldo_acumulado": saldo_acumulado.tolist(),
        }
        return self.resultados_economicos

    def plotar_analise_financeira(self, nome_arquivo=None):
        if not self.resultados_economicos:
            self.gerar_relatorio_dict()

        fig, axes = plt.subplots(2, 2, figsize=(16, 12))

        ax1 = axes[0, 0]
        custos_base = self.resultados_economicos["custos_base"]
        custos_micro = self.resultados_economicos["custos_micro"]

        custo_mensal_sem_bess = self.resultado_mes_sem_bess["custo_mensal"]
        custo_mensal_com_bess = self.resultado_mes_com_bess["custo_mensal"]

        categorias = ["Sem\nBESS", "Com\nBESS"]
        valores = [custo_mensal_sem_bess, custo_mensal_com_bess]
        bars = ax1.bar(categorias, valores, alpha=0.8, edgecolor="black", linewidth=1.5)
        ax1.set_ylabel("Custo Mensal (R$)")
        ax1.set_title("Caso IFG: Comparação Sem BESS vs Com BESS")
        ax1.grid(True, alpha=0.3, axis="y")

        for bar, valor in zip(bars, valores):
            height = bar.get_height()
            ax1.text(
                bar.get_x() + bar.get_width() / 2.0,
                height,
                f"R$ {valor:,.0f}/mês",
                ha="center",
                va="bottom",
                fontsize=10,
                fontweight="bold",
            )

        economia = custo_mensal_sem_bess - custo_mensal_com_bess
        economia_anual = economia * 12
        ax1.text(
            0.5,
            max(valores) * 0.5,
            f"ECONOMIA\nR$ {economia:,.0f}/mês\nR$ {economia_anual:,.0f}/ano",
            ha="center",
            va="center",
            fontsize=12,
            fontweight="bold",
            bbox=dict(boxstyle="round,pad=0.8", facecolor="yellow", alpha=0.8),
        )

        ax2 = axes[0, 1]
        _, fluxos_caixa = self.calcular_vpl()
        anos = np.arange(0, self.vida_util + 1)
        ax2.bar(anos, fluxos_caixa, alpha=0.8, edgecolor="black")
        ax2.axhline(y=0, linestyle="-", linewidth=1)
        ax2.set_xlabel("Ano")
        ax2.set_ylabel("Fluxo de Caixa (R$)")
        ax2.set_title("Fluxo de Caixa Anual")
        ax2.grid(True, alpha=0.3, axis="y")

        ax3 = axes[1, 0]
        payback, saldo_acumulado = self.calcular_payback_descontado()
        ax3.plot(anos, saldo_acumulado, "o-", linewidth=2, markersize=6)
        ax3.axhline(y=0, linestyle="--", linewidth=2, label="Ponto de equilíbrio")

        if payback != np.inf:
            ax3.axvline(x=payback, linestyle="--", linewidth=2, label=f"Payback: {payback} anos")
            ax3.plot(payback, saldo_acumulado[payback], "o", markersize=12)

        ax3.set_xlabel("Ano")
        ax3.set_ylabel("Saldo Acumulado (R$)")
        ax3.set_title("Retorno do Investimento - Payback Descontado")
        ax3.legend()
        ax3.grid(True, alpha=0.3)

        vpl = self.resultados_economicos["vpl"]
        tir = self.resultados_economicos["tir"]
        ax3.text(
            0.05,
            0.95,
            f"VPL: R$ {vpl:,.0f}\nTIR: {tir*100:.2f}%",
            transform=ax3.transAxes,
            fontsize=10,
            verticalalignment="top",
            bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.8),
        )

        ax4 = axes[1, 1]
        tarifas = np.linspace(0.5, 1.5, 50)
        economias = []

        custo_energia_base = custos_base["custo_energia"]
        custo_demanda_base = custos_base["custo_demanda"]
        custo_energia_micro = custos_micro["custo_energia_comprada"]
        custo_demanda_micro = custos_micro["custo_demanda"]
        custo_diesel_micro = custos_micro["custo_diesel"]

        for tarifa_mult in tarifas:
            custo_total_base_temp = (custo_energia_base * tarifa_mult) + custo_demanda_base
            custo_total_micro_temp = (
                (custo_energia_micro * tarifa_mult)
                + custo_demanda_micro
                + custo_diesel_micro
            )
            economias.append(custo_total_base_temp - custo_total_micro_temp)

        ax4.plot(tarifas, economias, linewidth=3)
        ax4.axvline(x=1.0, linestyle="--", linewidth=2, label="Tarifa atual")
        ax4.axhline(y=0, linestyle="--", linewidth=1)
        ax4.set_xlabel("Multiplicador da Tarifa de Energia")
        ax4.set_ylabel("Economia Anual (R$)")
        ax4.set_title("Sensibilidade: Economia vs Tarifa de Energia")
        ax4.legend()
        ax4.grid(True, alpha=0.3)

        fig.suptitle(
            f"Analise Financeira - Caso IFG | PV {self.potencia_pv_kwp:.1f} kWp | "
            f"BESS {self.capacidade_bess_kwh:.0f} kWh/{self.potencia_bess_kw:.0f} kW",
            fontsize=14,
            fontweight="bold",
            y=1.02,
        )

        plt.tight_layout()

        pasta_saida = Path(settings.MEDIA_ROOT) / "analises_financeiras"
        pasta_saida.mkdir(parents=True, exist_ok=True)

        if not nome_arquivo:
            nome_arquivo = f"analise_financeira_{uuid.uuid4().hex}.png"

        caminho_arquivo = pasta_saida / nome_arquivo
        plt.savefig(caminho_arquivo, dpi=150, bbox_inches="tight")
        plt.close(fig)

        return {
            "nome_arquivo": nome_arquivo,
            "caminho_absoluto": str(caminho_arquivo),
            "url": f"{settings.MEDIA_URL}analises_financeiras/{nome_arquivo}",
        }

    def executar_analise_completa(self):
        self.executar_simulacao_powerflow()
        relatorio = self.gerar_relatorio_dict()
        grafico = self.plotar_analise_financeira()

        return {
            "relatorio": relatorio,
            "grafico": grafico,
        }