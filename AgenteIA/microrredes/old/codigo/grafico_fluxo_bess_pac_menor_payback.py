"""
Gera grafico de fluxo de carga/descarga do BESS e fluxo de potencia no PAC
para o cenario de menor payback: PV 356 kWp e BESS 314 kWh.
"""

import numpy as np
import matplotlib.pyplot as plt

from caso_ifg import CasoIFG


def main():
    pv_kwp = 356.0
    bess_kwh = 314.0

    caso = CasoIFG(distribuidora="EQUATORIAL GO", modalidade="verde", perfil_carga_csv="perfil_carga_ifg.csv")
    caso.pv_potencia_kwp = pv_kwp
    caso.bess_capacidade_kwh = bess_kwh
    caso.usar_diesel = False
    caso._configurar_pv()

    resultado = caso.simular_dia(dia_semana=0)

    horas = np.array(resultado["hora"])
    fluxo_bess = np.array(resultado["potencia_bess_kw"], dtype=float)
    fluxo_pac = np.array(resultado["energia_rede_kw"], dtype=float)

    fig, axes = plt.subplots(2, 1, figsize=(12, 8), sharex=True)
    fig.suptitle("Fluxos Operacionais - Menor Payback (PV 356 kWp | BESS 314 kWh)", fontsize=13, fontweight="bold")

    # Painel 1: Fluxo da bateria
    cores_bess = ["#1f77b4" if v > 0 else "#17becf" for v in fluxo_bess]
    axes[0].bar(horas, fluxo_bess, color=cores_bess, alpha=0.85, edgecolor="black", linewidth=0.4)
    axes[0].axhline(0, color="black", linewidth=1)
    axes[0].set_ylabel("Potencia BESS (kW)")
    axes[0].set_title("BESS: + descarga | - carga")
    axes[0].grid(True, alpha=0.25, axis="y")

    # Painel 2: Fluxo de potencia no PAC
    cores_pac = ["#d62728" if v > 0 else "#2ca02c" for v in fluxo_pac]
    axes[1].bar(horas, fluxo_pac, color=cores_pac, alpha=0.85, edgecolor="black", linewidth=0.4)
    axes[1].axhline(0, color="black", linewidth=1)
    axes[1].set_xlabel("Hora")
    axes[1].set_ylabel("Potencia no PAC (kW)")
    axes[1].set_title("PAC: + importacao da rede | - exportacao para rede")
    axes[1].set_xticks(range(0, 24, 1))
    axes[1].grid(True, alpha=0.25, axis="y")

    plt.tight_layout(rect=[0, 0, 1, 0.96])

    output = "fluxo_bess_pac_menor_payback_pv356_bess314.png"
    plt.savefig(output, dpi=170, bbox_inches="tight")
    plt.close()

    print(output)


if __name__ == "__main__":
    main()
