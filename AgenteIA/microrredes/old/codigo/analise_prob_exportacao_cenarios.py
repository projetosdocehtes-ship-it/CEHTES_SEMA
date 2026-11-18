"""
Calcula probabilidade de exportacao para rede (PAC < 0) para multiplos cenarios PV/BESS.
"""

from __future__ import annotations

import pandas as pd

from analise_fluxo_potencia_estocastica import AnalisadorFluxoPotenciaEstocastico


def main():
    cenarios = [
        (356.0, 314.0),
        (374.0, 305.0),
        (387.0, 304.0),
        (408.0, 301.0),
        (413.0, 317.0),
        (404.0, 431.0),
        (432.0, 416.0),
        (437.0, 431.0),
        (445.0, 431.0),
        (454.0, 431.0),
        (464.0, 428.0),
        (466.0, 430.0),
        (471.0, 433.0),
        (483.0, 430.0),
        (499.0, 429.0),
    ]

    num_amostras = 250
    resultados = []

    print("=" * 90)
    print("PROBABILIDADE DE EXPORTACAO POR CENARIO (MONTE CARLO)")
    print("=" * 90)
    print(f"Amostras por cenario: {num_amostras}")

    for i, (pv_kwp, bess_kwh) in enumerate(cenarios, start=1):
        print(f"\n[{i}/{len(cenarios)}] Simulando PV={pv_kwp:.0f} kWp | BESS={bess_kwh:.0f} kWh")

        analisador = AnalisadorFluxoPotenciaEstocastico(
            num_amostras=num_amostras,
            pv_kwp=pv_kwp,
            bess_kwh=bess_kwh,
            distribuidora="EQUATORIAL GO",
            modalidade="verde",
            perfil_carga_csv="perfil_carga_horaria.csv",
            seed=42,
        )
        analisador.executar()

        r = analisador.resumo
        resultados.append(
            {
                "pv_kwp": pv_kwp,
                "bess_kwh": bess_kwh,
                "prob_exportacao": r["prob_exportacao"],
                "prob_importacao": r["prob_importacao"],
                "media_pac_kw": r["media_pac_kw"],
                "q05_pac_kw": r["q05_pac_kw"],
                "mediana_pac_kw": r["mediana_pac_kw"],
                "q95_pac_kw": r["q95_pac_kw"],
                "pico_importacao_kw": r["pico_importacao_kw"],
                "pico_exportacao_kw": r["pico_exportacao_kw"],
            }
        )

    df = pd.DataFrame(resultados)
    df = df.sort_values(["prob_exportacao", "media_pac_kw"], ascending=[False, True])

    print("\n" + "=" * 90)
    print("RESULTADO - PROBABILIDADE DE EXPORTACAO")
    print("=" * 90)
    tabela = df[["pv_kwp", "bess_kwh", "prob_exportacao", "prob_importacao", "media_pac_kw"]].copy()
    tabela["prob_exportacao"] = (tabela["prob_exportacao"] * 100).round(3)
    tabela["prob_importacao"] = (tabela["prob_importacao"] * 100).round(3)
    tabela = tabela.rename(
        columns={
            "prob_exportacao": "prob_exportacao_pct",
            "prob_importacao": "prob_importacao_pct",
        }
    )
    print(tabela.to_string(index=False))

    output = "analise_estocastica_prob_exportacao_cenarios.csv"
    df.to_csv(output, index=False)
    print(f"\nArquivo salvo: {output}")


if __name__ == "__main__":
    main()
