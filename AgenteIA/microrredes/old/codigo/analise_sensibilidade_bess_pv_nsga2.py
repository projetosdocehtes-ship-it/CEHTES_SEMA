"""
Otimização Multiobjetivo (NSGA-II): BESS vs PV para o IFG
Objetivos:
- Minimizar payback
- Maximizar VPL (implementado como minimização de -VPL)

Esta versão substitui a varredura discreta de cenários por NSGA-II.
"""

import random
from typing import Dict, List, Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from caso_ifg import CasoIFG


class AnalisadorSensibilidadeBESSPVNSGA2:
    """Analisa BESS e PV com NSGA-II (payback vs VPL)."""

    def __init__(
        self,
        considerar_base_324kwp: bool = True,
        pv_limites_kwp: Tuple[float, float] | None = None,
        bess_limites_kwh: Tuple[float, float] = (0, 500),
        passo_pv_kwp: float = 1,
        passo_bess_kwh: float = 1,
        tamanho_populacao: int = 28,
        num_geracoes: int = 18,
        taxa_crossover: float = 0.9,
        taxa_mutacao: float = 0.2,
        geracoes_sem_melhoria_max: int = 6,
        melhoria_minima: float = 1e-3,
        seed: int = 42,
    ):
        self.distribuidora = "EQUATORIAL GO"
        self.modalidade = "verde"

        self.considerar_base_324kwp = considerar_base_324kwp
        self.pv_base_kwp = 324 if considerar_base_324kwp else 0
        self.bess_base_kwh = 0

        if pv_limites_kwp is None:
            self.pv_limites_kwp = (324, 600) if considerar_base_324kwp else (0, 600)
        else:
            self.pv_limites_kwp = pv_limites_kwp

        self.bess_limites_kwh = bess_limites_kwh
        self.passo_pv_kwp = passo_pv_kwp
        self.passo_bess_kwh = passo_bess_kwh

        self.tamanho_populacao = tamanho_populacao
        self.num_geracoes = num_geracoes
        self.taxa_crossover = taxa_crossover
        self.taxa_mutacao = taxa_mutacao
        self.geracoes_sem_melhoria_max = geracoes_sem_melhoria_max
        self.melhoria_minima = melhoria_minima

        self.rng = random.Random(seed)
        np.random.seed(seed)

        # Custos de investimento (R$/unidade)
        self.custo_pv_kwp = 3000
        self.custo_bess_kwh = 1900

        # Tarifa de demanda
        self.tarifa_demanda_kw = 26.08

        # Parâmetros financeiros
        self.taxa_desconto = 0.10
        self.horizonte_anos = 10
        self.taxa_inflacao = 0.05

        self.custo_base = None
        self.demanda_base_kw = None
        self.energia_vendida_base = None

        self._cache_avaliacoes: Dict[Tuple[int, int], Dict] = {}
        self.df_todos_resultados = pd.DataFrame()
        self.df_pareto = pd.DataFrame()

    def _normalizar_valor(self, valor: float, limite: Tuple[float, float], passo: float) -> float:
        v = min(max(valor, limite[0]), limite[1])
        if passo > 0:
            v = round(v / passo) * passo
        return float(v)

    def _normalizar_decisao(self, pv_kwp: float, bess_kwh: float) -> Tuple[float, float]:
        pv_kwp = self._normalizar_valor(pv_kwp, self.pv_limites_kwp, self.passo_pv_kwp)
        bess_kwh = self._normalizar_valor(bess_kwh, self.bess_limites_kwh, self.passo_bess_kwh)
        return pv_kwp, bess_kwh

    def _calcular_demanda_maxima(self, resultado_simulacao: Dict) -> float:
        return resultado_simulacao.get("demanda_maxima_kw", 0)

    def _calcular_vpl(self, investimento_inicial: float, economia_anual: float) -> float:
        vpl = -investimento_inicial
        for ano in range(1, self.horizonte_anos + 1):
            economia_ano = economia_anual * ((1 + self.taxa_inflacao) ** (ano - 1))
            valor_presente = economia_ano / ((1 + self.taxa_desconto) ** ano)
            vpl += valor_presente
        return vpl

    def _calcular_tir(self, investimento_inicial: float, economia_anual: float) -> float:
        if investimento_inicial <= 0:
            return 0.0
        fluxos = [-investimento_inicial]
        for ano in range(1, self.horizonte_anos + 1):
            economia_ano = economia_anual * ((1 + self.taxa_inflacao) ** (ano - 1))
            fluxos.append(economia_ano)
        try:
            tir = np_financial_irr(np.array(fluxos, dtype=float))
            return float(tir) if np.isfinite(tir) else 0.0
        except Exception:
            return 0.0

    def simular_cenario_base(self):
        print("\n" + "=" * 100)
        print(" " * 30 + "SIMULANDO CENARIO BASE")
        print("=" * 100)
        print(f"  Considerar base 324 kWp: {self.considerar_base_324kwp}")
        print(f"  PV base: {self.pv_base_kwp} kWp")
        print(f"  BESS base: {self.bess_base_kwh} kWh")

        caso_base = CasoIFG(distribuidora=self.distribuidora, modalidade=self.modalidade)
        caso_base.pv_potencia_kwp = self.pv_base_kwp
        caso_base.bess_capacidade_kwh = self.bess_base_kwh
        caso_base.usar_diesel = False
        caso_base._configurar_pv()

        resultado_base = caso_base.simular_mes()
        self.custo_base = float(resultado_base["custo_mensal"])
        self.energia_vendida_base = float(resultado_base["energia_vendida_kwh"])
        self.demanda_base_kw = float(self._calcular_demanda_maxima(resultado_base))

        print("\nResultado base:")
        print(f"  Custo mensal: R$ {self.custo_base:,.2f}")
        print(f"  Custo anual:  R$ {self.custo_base * 12:,.2f}")
        print(f"  Demanda max:  {self.demanda_base_kw:.0f} kW")

    def simular_cenario(self, pv_kwp: float, bess_kwh: float, descricao: str = "") -> Dict:
        pv_kwp, bess_kwh = self._normalizar_decisao(pv_kwp, bess_kwh)
        cache_key = (int(round(pv_kwp)), int(round(bess_kwh)))
        if cache_key in self._cache_avaliacoes:
            return self._cache_avaliacoes[cache_key]

        caso = CasoIFG(distribuidora=self.distribuidora, modalidade=self.modalidade)
        caso.pv_potencia_kwp = pv_kwp
        caso.bess_capacidade_kwh = bess_kwh
        caso.usar_diesel = False
        caso._configurar_pv()

        resultado = caso.simular_mes()
        custo_mensal = float(resultado["custo_mensal"])
        demanda_max_kw = float(self._calcular_demanda_maxima(resultado))

        reducao_demanda_kw = max(0.0, self.demanda_base_kw - demanda_max_kw)
        economia_demanda_anual = reducao_demanda_kw * self.tarifa_demanda_kw * 12

        energia_comprada = float(resultado["energia_comprada_kwh"])
        energia_vendida = float(resultado["energia_vendida_kwh"])
        variacao_exportacao_kwh = energia_vendida - self.energia_vendida_base

        economia_energia_mensal = self.custo_base - custo_mensal
        economia_energia_anual = economia_energia_mensal * 12
        economia_total_anual = economia_energia_anual + economia_demanda_anual

        if self.considerar_base_324kwp:
            investimento_pv = max(0.0, pv_kwp - self.pv_base_kwp) * self.custo_pv_kwp
        else:
            investimento_pv = pv_kwp * self.custo_pv_kwp
        investimento_bess = bess_kwh * self.custo_bess_kwh
        investimento_total = investimento_pv + investimento_bess

        payback_anos = investimento_total / economia_total_anual if economia_total_anual > 0 else 999.0
        vpl = self._calcular_vpl(investimento_total, economia_total_anual)
        tir = self._calcular_tir(investimento_total, economia_total_anual)

        resultado_cenario = {
            "pv_kwp": pv_kwp,
            "bess_kwh": bess_kwh,
            "descricao": descricao or f"PV {pv_kwp:.0f} + BESS {bess_kwh:.0f}",
            "custo_mensal": custo_mensal,
            "custo_anual": custo_mensal * 12,
            "demanda_max_kw": demanda_max_kw,
            "reducao_demanda_kw": reducao_demanda_kw,
            "economia_demanda_anual": economia_demanda_anual,
            "economia_energia_anual": economia_energia_anual,
            "economia_total_anual": economia_total_anual,
            "energia_comprada": energia_comprada,
            "energia_vendida": energia_vendida,
            "variacao_exportacao_kwh": variacao_exportacao_kwh,
            "investimento_pv": investimento_pv,
            "investimento_bess": investimento_bess,
            "investimento_total": investimento_total,
            "payback_anos": float(payback_anos),
            "vpl_10anos": float(vpl),
            "tir": float(tir),
            "f1_payback_min": float(payback_anos),
            "f2_neg_vpl_min": float(-vpl),
            "tipo": "Cenario",
        }

        self._cache_avaliacoes[cache_key] = resultado_cenario
        return resultado_cenario

    def _individuo_aleatorio(self) -> Tuple[float, float]:
        pv = self.rng.uniform(self.pv_limites_kwp[0], self.pv_limites_kwp[1])
        bess = self.rng.uniform(self.bess_limites_kwh[0], self.bess_limites_kwh[1])
        return self._normalizar_decisao(pv, bess)

    def _populacao_inicial_estratificada(self, n: int) -> List[Tuple[float, float]]:
        """Gera população inicial com melhor cobertura do espaço de busca."""
        n = max(2, n)
        bins = np.linspace(0, 1, n + 1)
        amostras = []
        for i in range(n):
            u_pv = self.rng.uniform(float(bins[i]), float(bins[i + 1]))
            u_bess = self.rng.uniform(float(bins[i]), float(bins[i + 1]))
            pv = self.pv_limites_kwp[0] + u_pv * (self.pv_limites_kwp[1] - self.pv_limites_kwp[0])
            bess = self.bess_limites_kwh[0] + u_bess * (self.bess_limites_kwh[1] - self.bess_limites_kwh[0])
            amostras.append(self._normalizar_decisao(pv, bess))

        self.rng.shuffle(amostras)

        # Remover duplicatas mantendo ordem
        unicos = list(dict.fromkeys(amostras))
        while len(unicos) < n:
            unicos.append(self._individuo_aleatorio())
            unicos = list(dict.fromkeys(unicos))

        return unicos[:n]

    @staticmethod
    def _domina(a: Dict, b: Dict) -> bool:
        return (
            (a["f1_payback_min"] <= b["f1_payback_min"] and a["f2_neg_vpl_min"] <= b["f2_neg_vpl_min"])
            and (a["f1_payback_min"] < b["f1_payback_min"] or a["f2_neg_vpl_min"] < b["f2_neg_vpl_min"])
        )

    def _fast_non_dominated_sort(self, pop: List[Dict]) -> List[List[int]]:
        dominates = [set() for _ in pop]
        domination_count = [0 for _ in pop]
        fronts: List[List[int]] = [[]]

        for i, p in enumerate(pop):
            for j, q in enumerate(pop):
                if i == j:
                    continue
                if self._domina(p, q):
                    dominates[i].add(j)
                elif self._domina(q, p):
                    domination_count[i] += 1
            if domination_count[i] == 0:
                p["rank"] = 0
                fronts[0].append(i)

        f = 0
        while f < len(fronts) and fronts[f]:
            next_front = []
            for i in fronts[f]:
                for j in dominates[i]:
                    domination_count[j] -= 1
                    if domination_count[j] == 0:
                        pop[j]["rank"] = f + 1
                        next_front.append(j)
            if next_front:
                fronts.append(next_front)
            f += 1

        return fronts

    @staticmethod
    def _crowding_distance(pop: List[Dict], front: List[int]) -> Dict[int, float]:
        if not front:
            return {}
        distance = {i: 0.0 for i in front}
        objetivos = ["f1_payback_min", "f2_neg_vpl_min"]

        for obj in objetivos:
            ordenados = sorted(front, key=lambda i: pop[i][obj])
            min_v = pop[ordenados[0]][obj]
            max_v = pop[ordenados[-1]][obj]

            distance[ordenados[0]] = float("inf")
            distance[ordenados[-1]] = float("inf")

            if max_v == min_v:
                continue

            for k in range(1, len(ordenados) - 1):
                prev_v = pop[ordenados[k - 1]][obj]
                next_v = pop[ordenados[k + 1]][obj]
                distance[ordenados[k]] += (next_v - prev_v) / (max_v - min_v)

        return distance

    def _atribuir_rank_crowding(self, pop: List[Dict]) -> List[List[int]]:
        fronts = self._fast_non_dominated_sort(pop)
        for front in fronts:
            crowd = self._crowding_distance(pop, front)
            for i in front:
                pop[i]["crowding"] = crowd.get(i, 0.0)
        return fronts

    def _torneio_binario(self, pop: List[Dict]) -> Dict:
        a, b = self.rng.sample(pop, 2)
        if a["rank"] < b["rank"]:
            return a
        if b["rank"] < a["rank"]:
            return b
        return a if a["crowding"] >= b["crowding"] else b

    def _crossover(self, p1: Tuple[float, float], p2: Tuple[float, float]) -> Tuple[Tuple[float, float], Tuple[float, float]]:
        if self.rng.random() > self.taxa_crossover:
            return p1, p2

        alpha_pv = self.rng.random()
        alpha_bess = self.rng.random()

        c1_pv = alpha_pv * p1[0] + (1 - alpha_pv) * p2[0]
        c2_pv = alpha_pv * p2[0] + (1 - alpha_pv) * p1[0]

        c1_bess = alpha_bess * p1[1] + (1 - alpha_bess) * p2[1]
        c2_bess = alpha_bess * p2[1] + (1 - alpha_bess) * p1[1]

        c1 = self._normalizar_decisao(c1_pv, c1_bess)
        c2 = self._normalizar_decisao(c2_pv, c2_bess)
        return c1, c2

    def _mutacao(self, x: Tuple[float, float]) -> Tuple[float, float]:
        pv, bess = x

        if self.rng.random() < self.taxa_mutacao:
            sigma_pv = (self.pv_limites_kwp[1] - self.pv_limites_kwp[0]) * 0.1
            pv += self.rng.gauss(0, sigma_pv)

        if self.rng.random() < self.taxa_mutacao:
            sigma_bess = (self.bess_limites_kwh[1] - self.bess_limites_kwh[0]) * 0.1
            bess += self.rng.gauss(0, sigma_bess)

        return self._normalizar_decisao(pv, bess)

    def _avaliar_populacao(self, pop_x: List[Tuple[float, float]]) -> List[Dict]:
        pop = []
        for pv, bess in pop_x:
            res = self.simular_cenario(pv, bess)
            pop.append(dict(res))
        return pop

    def executar_otimizacao(self):
        if self.custo_base is None:
            self.simular_cenario_base()

        print("\n" + "=" * 100)
        print(" " * 24 + "OTIMIZACAO MULTIOBJETIVO COM NSGA-II")
        print("=" * 100)
        print(f"Populacao: {self.tamanho_populacao}")
        print(f"Geracoes: {self.num_geracoes}")
        print(f"Limites PV (kWp): {self.pv_limites_kwp}")
        print(f"Limites BESS (kWh): {self.bess_limites_kwh}")

        # População inicial com melhor dispersão
        pop_x = self._populacao_inicial_estratificada(self.tamanho_populacao)
        pop = self._avaliar_populacao(pop_x)
        self._atribuir_rank_crowding(pop)

        sem_melhoria = 0
        melhor_payback_global = float("inf")
        melhor_vpl_global = float("-inf")

        for geracao in range(1, self.num_geracoes + 1):
            offspring_x: List[Tuple[float, float]] = []
            offspring_set = set()
            while len(offspring_x) < self.tamanho_populacao:
                p1 = self._torneio_binario(pop)
                p2 = self._torneio_binario(pop)
                f1 = (p1["pv_kwp"], p1["bess_kwh"])
                f2 = (p2["pv_kwp"], p2["bess_kwh"])

                c1, c2 = self._crossover(f1, f2)
                c1 = self._mutacao(c1)
                c2 = self._mutacao(c2)
                if c1 not in offspring_set:
                    offspring_x.append(c1)
                    offspring_set.add(c1)
                if len(offspring_x) < self.tamanho_populacao and c2 not in offspring_set:
                    offspring_x.append(c2)
                    offspring_set.add(c2)

                # Evita laço infinito quando mutação/crossover geram repetição
                if len(offspring_x) < self.tamanho_populacao and len(offspring_set) < self.tamanho_populacao:
                    if self.rng.random() < 0.15:
                        r = self._individuo_aleatorio()
                        if r not in offspring_set:
                            offspring_x.append(r)
                            offspring_set.add(r)

            offspring_x = offspring_x[: self.tamanho_populacao]
            offspring = self._avaliar_populacao(offspring_x)

            # Elitismo NSGA-II
            combinado = pop + offspring
            fronts = self._atribuir_rank_crowding(combinado)

            nova_pop = []
            nova_pop_set = set()
            for front in fronts:
                candidatos = [combinado[i] for i in front]
                if len(nova_pop) + len(candidatos) <= self.tamanho_populacao:
                    for c in candidatos:
                        key = (c["pv_kwp"], c["bess_kwh"])
                        if key not in nova_pop_set:
                            nova_pop.append(c)
                            nova_pop_set.add(key)
                else:
                    faltantes = self.tamanho_populacao - len(nova_pop)
                    ordenado = sorted(front, key=lambda i: combinado[i]["crowding"], reverse=True)
                    for i in ordenado:
                        c = combinado[i]
                        key = (c["pv_kwp"], c["bess_kwh"])
                        if key not in nova_pop_set:
                            nova_pop.append(c)
                            nova_pop_set.add(key)
                        if len(nova_pop) >= self.tamanho_populacao:
                            break
                    break

            while len(nova_pop) < self.tamanho_populacao:
                candidato = dict(self.simular_cenario(*self._individuo_aleatorio()))
                key = (candidato["pv_kwp"], candidato["bess_kwh"])
                if key not in nova_pop_set:
                    nova_pop.append(candidato)
                    nova_pop_set.add(key)

            pop = nova_pop
            self._atribuir_rank_crowding(pop)

            f0 = [ind for ind in pop if ind["rank"] == 0]
            melhor_payback = min(ind["payback_anos"] for ind in f0) if f0 else min(ind["payback_anos"] for ind in pop)
            melhor_vpl = max(ind["vpl_10anos"] for ind in f0) if f0 else max(ind["vpl_10anos"] for ind in pop)

            melhorou_payback = (melhor_payback_global - melhor_payback) > self.melhoria_minima
            melhorou_vpl = (melhor_vpl - melhor_vpl_global) > self.melhoria_minima
            if melhorou_payback:
                melhor_payback_global = melhor_payback
            if melhorou_vpl:
                melhor_vpl_global = melhor_vpl

            if melhorou_payback or melhorou_vpl:
                sem_melhoria = 0
            else:
                sem_melhoria += 1

            print(
                f"Geracao {geracao:>3}/{self.num_geracoes} | "
                f"Fronteira Pareto atual: {len(f0):>2} solucoes | "
                f"Melhor payback: {melhor_payback:>6.2f} anos | "
                f"Melhor VPL: R$ {melhor_vpl:>12,.0f}"
            )

            if sem_melhoria >= self.geracoes_sem_melhoria_max:
                print(
                    f"Parada antecipada na geracao {geracao}: "
                    f"sem melhoria por {sem_melhoria} geracoes."
                )
                break

        # Fronteira final
        self._atribuir_rank_crowding(pop)
        pareto = [dict(ind) for ind in pop if ind["rank"] == 0]

        self.df_pareto = pd.DataFrame(pareto).drop_duplicates(subset=["pv_kwp", "bess_kwh"]).sort_values(
            ["payback_anos", "vpl_10anos"], ascending=[True, False]
        )
        self.df_todos_resultados = pd.DataFrame(list(self._cache_avaliacoes.values()))

        self.df_todos_resultados.to_csv("analise_nsga2_bess_pv_todos_resultados.csv", index=False)
        self.df_pareto.to_csv("analise_nsga2_bess_pv_pareto.csv", index=False)

        print("\nArquivos gerados:")
        print("  - analise_nsga2_bess_pv_todos_resultados.csv")
        print("  - analise_nsga2_bess_pv_pareto.csv")

    def gerar_relatorio(self, top_n: int = 10):
        if self.df_pareto.empty:
            raise RuntimeError("Execute executar_otimizacao() antes de gerar_relatorio().")

        print("\n" + "=" * 100)
        print(" " * 30 + "RELATORIO NSGA-II")
        print("=" * 100)
        print(f"Solucoes na fronteira de Pareto: {len(self.df_pareto)}")

        print("\nTop solucoes por menor payback (na fronteira de Pareto):")
        cols = [
            "pv_kwp",
            "bess_kwh",
            "investimento_total",
            "economia_total_anual",
            "payback_anos",
            "vpl_10anos",
            "tir",
        ]
        print(self.df_pareto[cols].head(top_n).to_string(index=False))

        melhor_payback = self.df_pareto.loc[self.df_pareto["payback_anos"].idxmin()]
        melhor_vpl = self.df_pareto.loc[self.df_pareto["vpl_10anos"].idxmax()]

        print("\nMelhor por payback:")
        print(
            f"  PV={melhor_payback['pv_kwp']:.0f} kWp | "
            f"BESS={melhor_payback['bess_kwh']:.0f} kWh | "
            f"Payback={melhor_payback['payback_anos']:.2f} anos | "
            f"VPL=R$ {melhor_payback['vpl_10anos']:,.2f}"
        )

        print("\nMelhor por VPL:")
        print(
            f"  PV={melhor_vpl['pv_kwp']:.0f} kWp | "
            f"BESS={melhor_vpl['bess_kwh']:.0f} kWh | "
            f"Payback={melhor_vpl['payback_anos']:.2f} anos | "
            f"VPL=R$ {melhor_vpl['vpl_10anos']:,.2f}"
        )

    def gerar_curva_pareto(self, filename: str = "analise_nsga2_bess_pv_curva_pareto.png"):
        """Gera gráfico da curva de Pareto com payback x VPL."""
        if self.df_todos_resultados.empty or self.df_pareto.empty:
            raise RuntimeError("Execute executar_otimizacao() antes de gerar_curva_pareto().")

        df_todos = self.df_todos_resultados.copy()
        df_pareto = self.df_pareto.sort_values("payback_anos")

        plt.figure(figsize=(11, 7))

        # Pontos avaliados pelo NSGA-II
        plt.scatter(
            df_todos["payback_anos"],
            df_todos["vpl_10anos"] / 1000,
            s=28,
            alpha=0.35,
            color="#9aa5b1",
            label="Solucoes avaliadas",
        )

        # Fronteira de Pareto
        plt.plot(
            df_pareto["payback_anos"],
            df_pareto["vpl_10anos"] / 1000,
            "-o",
            color="#d62728",
            linewidth=2.2,
            markersize=5,
            label="Fronteira de Pareto",
        )

        # Destaque dos extremos
        melhor_payback = df_pareto.loc[df_pareto["payback_anos"].idxmin()]
        melhor_vpl = df_pareto.loc[df_pareto["vpl_10anos"].idxmax()]

        plt.scatter(
            melhor_payback["payback_anos"],
            melhor_payback["vpl_10anos"] / 1000,
            s=120,
            marker="*",
            color="#1f77b4",
            edgecolors="black",
            linewidths=0.8,
            zorder=5,
            label="Melhor payback",
        )
        plt.scatter(
            melhor_vpl["payback_anos"],
            melhor_vpl["vpl_10anos"] / 1000,
            s=120,
            marker="D",
            color="#2ca02c",
            edgecolors="black",
            linewidths=0.8,
            zorder=5,
            label="Melhor VPL",
        )

        plt.xlabel("Payback (anos)")
        plt.ylabel("VPL em 10 anos (R$ mil)")
        plt.title("Curva de Pareto - Otimizacao NSGA-II (BESS x PV)")
        plt.grid(True, alpha=0.25)
        plt.legend()
        plt.tight_layout()
        plt.savefig(filename, dpi=160, bbox_inches="tight")
        plt.close()

        print(f"\nCurva de Pareto salva em: {filename}")

    def gerar_grafico_solucoes_pv_bess(
        self,
        filename: str = "analise_nsga2_bess_pv_espaco_solucoes.png",
    ):
        """Gera gráfico do espaço de soluções PV x BESS."""
        if self.df_todos_resultados.empty or self.df_pareto.empty:
            raise RuntimeError("Execute executar_otimizacao() antes de gerar_grafico_solucoes_pv_bess().")

        df_todos = self.df_todos_resultados.copy()
        df_pareto = self.df_pareto.copy()

        plt.figure(figsize=(11, 7))

        # Todas as combinações avaliadas no NSGA-II
        plt.scatter(
            df_todos["pv_kwp"],
            df_todos["bess_kwh"],
            s=26,
            alpha=0.35,
            color="#8c8c8c",
            label="Solucoes avaliadas",
        )

        # Soluções na fronteira de Pareto
        plt.scatter(
            df_pareto["pv_kwp"],
            df_pareto["bess_kwh"],
            s=58,
            alpha=0.9,
            color="#d62728",
            edgecolors="black",
            linewidths=0.5,
            label="Solucoes Pareto",
            zorder=5,
        )

        melhor_payback = df_pareto.loc[df_pareto["payback_anos"].idxmin()]
        melhor_vpl = df_pareto.loc[df_pareto["vpl_10anos"].idxmax()]

        plt.scatter(
            melhor_payback["pv_kwp"],
            melhor_payback["bess_kwh"],
            s=140,
            marker="*",
            color="#1f77b4",
            edgecolors="black",
            linewidths=0.8,
            label="Melhor payback",
            zorder=6,
        )
        plt.scatter(
            melhor_vpl["pv_kwp"],
            melhor_vpl["bess_kwh"],
            s=120,
            marker="D",
            color="#2ca02c",
            edgecolors="black",
            linewidths=0.8,
            label="Melhor VPL",
            zorder=6,
        )

        plt.xlabel("PV instalado (kWp)")
        plt.ylabel("Capacidade BESS (kWh)")
        plt.title("Espaco de Solucoes NSGA-II: PV x BESS")
        plt.grid(True, alpha=0.25)
        plt.legend()
        plt.tight_layout()
        plt.savefig(filename, dpi=160, bbox_inches="tight")
        plt.close()

        print(f"Grafico PV x BESS salvo em: {filename}")


def np_financial_irr(fluxos: np.ndarray) -> float:
    """Calcula TIR sem depender de numpy_financial."""
    taxa_min, taxa_max = -0.99, 5.0

    def vpl_taxa(taxa: float) -> float:
        periods = np.arange(len(fluxos), dtype=float)
        return float(np.sum(fluxos / ((1 + taxa) ** periods)))

    f_min = vpl_taxa(taxa_min)
    f_max = vpl_taxa(taxa_max)
    if f_min * f_max > 0:
        return np.nan

    for _ in range(120):
        mid = (taxa_min + taxa_max) / 2
        f_mid = vpl_taxa(mid)
        if abs(f_mid) < 1e-8:
            return mid
        if f_min * f_mid < 0:
            taxa_max = mid
            f_max = f_mid
        else:
            taxa_min = mid
            f_min = f_mid
    return (taxa_min + taxa_max) / 2


def main():
    analisador = AnalisadorSensibilidadeBESSPVNSGA2(
        considerar_base_324kwp=True,
        pv_limites_kwp=(324, 650),
        bess_limites_kwh=(0, 500),
        passo_pv_kwp=1,
        passo_bess_kwh=1,
        tamanho_populacao=28,
        num_geracoes=18,
        taxa_crossover=0.9,
        taxa_mutacao=0.25,
        geracoes_sem_melhoria_max=6,
        melhoria_minima=1e-3,
        seed=42,
    )

    analisador.executar_otimizacao()
    analisador.gerar_relatorio(top_n=15)
    analisador.gerar_curva_pareto()
    analisador.gerar_grafico_solucoes_pv_bess()


if __name__ == "__main__":
    main()
