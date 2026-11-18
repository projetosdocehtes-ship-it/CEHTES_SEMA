"""
Analise estocastica de fluxo de potencia no PAC (Ponto de Acoplamento Comum).

Objetivo:
- Variar incertezas de irradiancia e carga (Monte Carlo)
- Avaliar como a microrrede responde tecnicamente
- Gerar distribuicao de probabilidade do fluxo no PAC

Convencao do PAC (kW):
- Valor positivo: importacao da rede
- Valor negativo: exportacao para a rede
"""

from __future__ import annotations

import io
from contextlib import redirect_stdout
from dataclasses import dataclass

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from caso_ifg import CasoIFG


@dataclass
class ParametrosIncerteza:
    media_irradiancia: float = 1.0
    desvio_irradiancia: float = 0.12
    min_irradiancia: float = 0.65
    max_irradiancia: float = 1.25

    media_carga: float = 1.0
    desvio_carga: float = 0.10
    min_carga: float = 0.75
    max_carga: float = 1.30


class AnalisadorFluxoPotenciaEstocastico:
    """Executa simulacoes Monte Carlo e analisa o fluxo no PAC."""

    def __init__(
        self,
        num_amostras: int = 250,
        pv_kwp: float = 324,
        bess_kwh: float = 500,
        distribuidora: str = "EQUATORIAL GO",
        modalidade: str = "verde",
        perfil_carga_csv: str = "perfil_carga_horaria.csv",
        seed: int = 42,
        incertezas: ParametrosIncerteza | None = None,
    ):
        self.num_amostras = int(num_amostras)
        self.pv_kwp = float(pv_kwp)
        self.bess_kwh = float(bess_kwh)
        self.distribuidora = distribuidora
        self.modalidade = modalidade
        self.perfil_carga_csv = perfil_carga_csv
        self.rng = np.random.default_rng(seed)
        self.incertezas = incertezas or ParametrosIncerteza()

        self.df_amostras = pd.DataFrame()
        self.df_pac = pd.DataFrame()
        self.resumo = {}

    def _sortear_fatores(self) -> tuple[float, float]:
        irr = self.rng.normal(self.incertezas.media_irradiancia, self.incertezas.desvio_irradiancia)
        irr = float(np.clip(irr, self.incertezas.min_irradiancia, self.incertezas.max_irradiancia))

        carga = self.rng.normal(self.incertezas.media_carga, self.incertezas.desvio_carga)
        carga = float(np.clip(carga, self.incertezas.min_carga, self.incertezas.max_carga))

        return irr, carga

    def _simular_um_cenario(self, fator_irr: float, fator_carga: float) -> tuple[list[float], list[float]]:
        # Suprime logs volumosos do CasoIFG para acelerar e limpar a saida
        with redirect_stdout(io.StringIO()):
            caso = CasoIFG(
                distribuidora=self.distribuidora,
                modalidade=self.modalidade,
                perfil_carga_csv=self.perfil_carga_csv,
            )
            caso.pv_potencia_kwp = self.pv_kwp
            caso.bess_capacidade_kwh = self.bess_kwh
            caso.usar_diesel = False
            caso._configurar_pv()

            # Aplica incerteza multiplicativa na demanda horaria
            demanda_original = caso.perfil.get_demanda

            def demanda_escalada(hora: int, dia_semana: int = 0):
                return demanda_original(hora, dia_semana) * fator_carga

            caso.perfil.get_demanda = demanda_escalada

            # Aplica incerteza multiplicativa na geracao PV (irradiancia efetiva)
            pv_original = caso.calcular_potencia_pv

            def pv_escalado(hora: int, temperatura_C: float = 25):
                return pv_original(hora, temperatura_C) * fator_irr

            caso.calcular_potencia_pv = pv_escalado

            dia_util = caso.simular_dia(dia_semana=0)
            fim_semana = caso.simular_dia(dia_semana=6)

        pac_util = [float(v) for v in dia_util["energia_rede_kw"]]
        pac_fds = [float(v) for v in fim_semana["energia_rede_kw"]]
        return pac_util, pac_fds

    def executar(self):
        registros_amostra = []
        registros_pac = []

        print("=" * 90)
        print(" " * 18 + "ANALISE ESTOCASTICA DE FLUXO DE POTENCIA NO PAC")
        print("=" * 90)
        print(f"Amostras Monte Carlo: {self.num_amostras}")
        print(f"PV: {self.pv_kwp:.0f} kWp | BESS: {self.bess_kwh:.0f} kWh | Modalidade: {self.modalidade}")

        for i in range(self.num_amostras):
            fator_irr, fator_carga = self._sortear_fatores()
            pac_util, pac_fds = self._simular_um_cenario(fator_irr, fator_carga)

            registros_amostra.append(
                {
                    "amostra": i,
                    "fator_irradiancia": fator_irr,
                    "fator_carga": fator_carga,
                    "pac_util_media_kw": float(np.mean(pac_util)),
                    "pac_util_pico_import_kw": float(np.max(pac_util)),
                    "pac_util_pico_export_kw": float(np.min(pac_util)),
                    "pac_fds_media_kw": float(np.mean(pac_fds)),
                    "pac_fds_pico_import_kw": float(np.max(pac_fds)),
                    "pac_fds_pico_export_kw": float(np.min(pac_fds)),
                }
            )

            for hora in range(24):
                registros_pac.append(
                    {
                        "amostra": i,
                        "tipo_dia": "util",
                        "hora": hora,
                        "fator_irradiancia": fator_irr,
                        "fator_carga": fator_carga,
                        "pac_kw": pac_util[hora],
                    }
                )
                registros_pac.append(
                    {
                        "amostra": i,
                        "tipo_dia": "fim_semana",
                        "hora": hora,
                        "fator_irradiancia": fator_irr,
                        "fator_carga": fator_carga,
                        "pac_kw": pac_fds[hora],
                    }
                )

            if (i + 1) % max(1, self.num_amostras // 10) == 0:
                print(f"  progresso: {i + 1}/{self.num_amostras}")

        self.df_amostras = pd.DataFrame(registros_amostra)
        self.df_pac = pd.DataFrame(registros_pac)

        self._calcular_resumo()

        self.df_amostras.to_csv("analise_estocastica_pac_amostras.csv", index=False)
        self.df_pac.to_csv("analise_estocastica_pac_horario.csv", index=False)

        print("\nArquivos salvos:")
        print("  - analise_estocastica_pac_amostras.csv")
        print("  - analise_estocastica_pac_horario.csv")

    def _calcular_resumo(self):
        pac = self.df_pac["pac_kw"].to_numpy(dtype=float)

        prob_importacao = float(np.mean(pac > 0))
        prob_exportacao = float(np.mean(pac < 0))
        prob_proximo_zero = float(np.mean(np.abs(pac) <= 10.0))

        q05, q50, q95 = np.quantile(pac, [0.05, 0.50, 0.95])

        self.resumo = {
            "media_pac_kw": float(np.mean(pac)),
            "desvio_pac_kw": float(np.std(pac)),
            "q05_pac_kw": float(q05),
            "mediana_pac_kw": float(q50),
            "q95_pac_kw": float(q95),
            "prob_importacao": prob_importacao,
            "prob_exportacao": prob_exportacao,
            "prob_quase_neutro_abs_le_10kw": prob_proximo_zero,
            "pico_importacao_kw": float(np.max(pac)),
            "pico_exportacao_kw": float(np.min(pac)),
        }

    def gerar_graficos(self):
        if self.df_pac.empty:
            raise RuntimeError("Execute executar() antes de gerar_graficos().")

        pac = self.df_pac["pac_kw"].to_numpy(dtype=float)

        fig, axes = plt.subplots(1, 2, figsize=(15, 6))

        # Histograma de probabilidade do PAC
        axes[0].hist(
            pac,
            bins=60,
            density=True,
            alpha=0.75,
            color="#1f77b4",
            edgecolor="black",
            linewidth=0.4,
        )
        axes[0].axvline(0, color="red", linestyle="--", linewidth=1.5, label="PAC = 0")
        axes[0].set_title("Distribuicao de Probabilidade do Fluxo no PAC")
        axes[0].set_xlabel("Fluxo no PAC (kW) | +Importa / -Exporta")
        axes[0].set_ylabel("Densidade")
        axes[0].grid(True, alpha=0.25)
        axes[0].legend()

        # CDF empirica
        pac_sort = np.sort(pac)
        cdf = np.arange(1, len(pac_sort) + 1) / len(pac_sort)
        axes[1].plot(pac_sort, cdf, color="#2ca02c", linewidth=2)
        axes[1].axvline(0, color="red", linestyle="--", linewidth=1.5, label="PAC = 0")
        axes[1].set_title("CDF Empirica do Fluxo no PAC")
        axes[1].set_xlabel("Fluxo no PAC (kW)")
        axes[1].set_ylabel("Probabilidade acumulada")
        axes[1].grid(True, alpha=0.25)
        axes[1].legend()

        plt.tight_layout()
        plt.savefig("analise_estocastica_pac_distribuicao.png", dpi=160, bbox_inches="tight")
        plt.close()

        # Probabilidade horaria de importacao no PAC
        df_prob_hora = (
            self.df_pac.assign(importa=lambda d: d["pac_kw"] > 0)
            .groupby(["tipo_dia", "hora"], as_index=False)["importa"]
            .mean()
        )

        plt.figure(figsize=(12, 5))
        for tipo_dia, grupo in df_prob_hora.groupby("tipo_dia"):
            plt.plot(grupo["hora"], grupo["importa"], marker="o", linewidth=2, label=tipo_dia)

        plt.ylim(0, 1)
        plt.xlabel("Hora")
        plt.ylabel("Probabilidade de importacao no PAC")
        plt.title("Probabilidade Horaria de Importacao da Rede")
        plt.grid(True, alpha=0.25)
        plt.legend()
        plt.tight_layout()
        plt.savefig("analise_estocastica_pac_prob_importacao_horaria.png", dpi=160, bbox_inches="tight")
        plt.close()

        print("Graficos salvos:")
        print("  - analise_estocastica_pac_distribuicao.png")
        print("  - analise_estocastica_pac_prob_importacao_horaria.png")

    def imprimir_resumo(self):
        if not self.resumo:
            raise RuntimeError("Execute executar() antes de imprimir_resumo().")

        r = self.resumo
        print("\n" + "=" * 90)
        print(" " * 28 + "RESUMO ESTOCASTICO DO PAC")
        print("=" * 90)
        print(f"Media PAC:                    {r['media_pac_kw']:>10.1f} kW")
        print(f"Desvio padrao PAC:            {r['desvio_pac_kw']:>10.1f} kW")
        print(f"Percentil 5% (Q05):           {r['q05_pac_kw']:>10.1f} kW")
        print(f"Mediana (Q50):                {r['mediana_pac_kw']:>10.1f} kW")
        print(f"Percentil 95% (Q95):          {r['q95_pac_kw']:>10.1f} kW")
        print(f"Pico importacao:              {r['pico_importacao_kw']:>10.1f} kW")
        print(f"Pico exportacao:              {r['pico_exportacao_kw']:>10.1f} kW")
        print(f"Prob. importar da rede:       {r['prob_importacao'] * 100:>9.2f}%")
        print(f"Prob. exportar para rede:     {r['prob_exportacao'] * 100:>9.2f}%")
        print(f"Prob. PAC ~ neutro (|P|<=10): {r['prob_quase_neutro_abs_le_10kw'] * 100:>9.2f}%")


def main():
    analisador = AnalisadorFluxoPotenciaEstocastico(
        num_amostras=250,
        pv_kwp=324,
        bess_kwh=500,
        distribuidora="EQUATORIAL GO",
        modalidade="verde",
        perfil_carga_csv="perfil_carga_horaria.csv",
        seed=42,
    )

    analisador.executar()
    analisador.imprimir_resumo()
    analisador.gerar_graficos()


if __name__ == "__main__":
    main()
