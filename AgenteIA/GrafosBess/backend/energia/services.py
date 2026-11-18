from copy import deepcopy
from functools import lru_cache
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile
import threading
import time

from django.conf import settings

from energia.models import Componente


DEFAULT_CLIMA = {
    "clima_id": "Clima_Ambiente",
    "nome_cidade": "Goiania",
    "pais": "BR",
    "data": 20240116,
}

DEFAULT_TARIFAS_ENERGIA = {
    "horarios": {
        "ponta": {"dias_uteis": "18:00-21:00", "fim_semana": "nao aplica"},
        "fora_ponta": {"dias_uteis": "00:00-18:00, 21:00-24:00", "fim_semana": "00:00-24:00"},
    },
    "custos_investimento": {"pv_kwp": 3500, "bess_kwh": 1900, "unidade": "R$"},
}

DEFAULT_MODELO_ANALISE_FINANCEIRA = {
    "nome_projeto": "Projeto Simulador",
    "conectado_rede": True,
    "Config_Simulacao": [{"Tipo_Sim": "ViabilidadeEconomica", "Passo_sim": 1, "Tempo_sim": 8760}],
    "Clima_Ambiente": [DEFAULT_CLIMA],
    "painel_info": [],
    "inversor_info": [],
    "cargas_info": [],
    "bateria_info": [],
    "barramento_info": [],
    "geradordiesel_info": [],
    "grafo_conexoes": [],
    "tarifas_energia": DEFAULT_TARIFAS_ENERGIA,
}

MODELO_ANALISE_FINANCEIRA_PATH = (
    Path(__file__).resolve().parents[3]
    / "prime-django"
    / "apps"
    / "AnaliseEconomica"
    / "Arquivos_Temp_Json"
    / "Modelo_Entradas.json"
)
MODELOS_ANALISE_FINANCEIRA_DIR = MODELO_ANALISE_FINANCEIRA_PATH.parent
PRIME_DJANGO_PATH = MODELO_ANALISE_FINANCEIRA_PATH.parents[3]
PRIME_DJANGO_PYTHON = PRIME_DJANGO_PATH / "venv" / "Scripts" / "python.exe"
ANALISE_FINANCEIRA_RUNNER = Path(__file__).resolve().parent / "analise_financeira_runner.py"
MICRORREDES_PATH = Path(__file__).resolve().parents[3] / "microrredes"
MICRORREDES_VENV_PYTHON = MICRORREDES_PATH / ".venv" / "Scripts" / "python.exe"
MICRORREDES_RUNTIME_PATH = Path(settings.BASE_DIR) / ".runtime" / "microrredes"
_FLUXO_POTENCIA_LOCK = threading.Lock()
_FLUXO_POTENCIA_CACHE: dict[str, dict] = {}
_FLUXO_POTENCIA_CACHE_MAX_ITEMS = 32


def _safe_float(value):
    try:
        if isinstance(value, str):
            value = value.strip()
            value = value.replace(".", "").replace(",", ".") if "," in value else value
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _safe_int(value, default=0):
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _node_componente(node: dict) -> dict:
    return ((node.get("data") or {}).get("componente") or {})


def _dados_modelo(node: dict) -> dict:
    dados = _node_componente(node).get("dados_modelo")
    return dados if isinstance(dados, dict) else {}


def _first_node_by_tipo(nodes: list, tipo_codigo: str) -> dict | None:
    for node in nodes:
        if _node_componente(node).get("tipo_codigo") == tipo_codigo:
            return node
    return None


def _nodes_by_tipo(nodes: list, tipo_codigo: str) -> list[dict]:
    return [node for node in nodes if _node_componente(node).get("tipo_codigo") == tipo_codigo]


def _node_style(tipo_codigo: str) -> dict:
    colors = {
        "modulo_fv": "#166534",
        "inversor": "#0ea5e9",
        "barramento": "#334155",
        "bateria": "#15803d",
        "pcs": "#0369a1",
        "carga": "#ea580c",
        "gerador_diesel": "#92400e",
        "clima": "#2563eb",
        "poc": "#dc2626",
        "transformador": "#b45309",
        "string_box": "#1d4ed8",
        "seccionadora_cc": "#0f766e",
        "dps_cc": "#7c3aed",
        "protecao_mt": "#9333ea",
    }
    color = colors.get(tipo_codigo, "#374151")
    return {
        "border": f"2px solid {color}",
        "borderRadius": 12,
        "padding": 10,
        "width": 220,
        "background": "#ffffff",
        "boxShadow": "0 4px 16px rgba(0,0,0,0.08)",
    }


def carregar_modelo_analise_financeira() -> dict:
    try:
        with MODELO_ANALISE_FINANCEIRA_PATH.open("r", encoding="utf-8") as arquivo:
            modelo = json.load(arquivo)
        return modelo if isinstance(modelo, dict) else deepcopy(DEFAULT_MODELO_ANALISE_FINANCEIRA)
    except (OSError, json.JSONDecodeError):
        return deepcopy(DEFAULT_MODELO_ANALISE_FINANCEIRA)


def obter_modelo_analise_financeira_mais_recente() -> Path:
    modelos = sorted(
        MODELOS_ANALISE_FINANCEIRA_DIR.glob("Modelo_Entradas*.json"),
        key=lambda caminho: caminho.stat().st_mtime,
        reverse=True,
    )
    if not modelos:
        raise FileNotFoundError(f"Nenhum Modelo_Entradas*.json encontrado em: {MODELOS_ANALISE_FINANCEIRA_DIR}")
    return modelos[0]


def adaptar_para_analise_financeira(modelo_equipamentos: dict, modelo_financeiro: dict | None = None) -> dict:
    dados = deepcopy(modelo_equipamentos)
    modelo = deepcopy(modelo_financeiro or carregar_modelo_analise_financeira())

    for chave in (
        "Config_Simulacao",
        "Clima_Ambiente",
        "cargas_info",
        "painel_info",
        "inversor_info",
        "bateria_info",
        "barramento_info",
        "geradordiesel_info",
        "grafo_conexoes",
    ):
        if not isinstance(dados.get(chave), list):
            dados[chave] = deepcopy(modelo.get(chave, []))

    if not isinstance(dados.get("tarifas_energia"), dict):
        dados["tarifas_energia"] = deepcopy(modelo.get("tarifas_energia", DEFAULT_TARIFAS_ENERGIA))

    if not dados["Config_Simulacao"]:
        dados["Config_Simulacao"] = [{"Tipo_Sim": "ViabilidadeEconomica", "Passo_sim": 1, "Tempo_sim": 8760}]
    if not dados["Clima_Ambiente"]:
        dados["Clima_Ambiente"] = [deepcopy(DEFAULT_CLIMA)]
    if not dados["bateria_info"] and modelo.get("bateria_info"):
        dados["bateria_info"] = deepcopy(modelo["bateria_info"])
    if not dados["geradordiesel_info"] and modelo.get("geradordiesel_info"):
        dados["geradordiesel_info"] = deepcopy(modelo["geradordiesel_info"])

    for config in dados["Config_Simulacao"]:
        if isinstance(config, dict) and config.get("Tipo_Sim") == "ViabilidadeEconomica":
            config.setdefault("Passo_sim", 1)
            config["Tempo_sim"] = 8760

    for carga in dados["cargas_info"]:
        if isinstance(carga, dict):
            carga.setdefault("curva_carga", "perfil_carga_ifg.csv")
            carga.setdefault("tipo_carga", "Comercial")
            carga.setdefault("quantidade", 1)

    pv_kwp = dados["tarifas_energia"].get("custos_investimento", {}).get("pv_kwp", 3500)
    for painel in dados["painel_info"]:
        if isinstance(painel, dict):
            painel.setdefault("custo_kwp", pv_kwp)

    return dados


def _painel_info(node: dict) -> dict:
    comp = _node_componente(node)
    dados = _dados_modelo(node)
    pmp = _safe_float(dados.get("Pmp") or comp.get("potencia_kw")) or 610
    quantidade = _safe_int(dados.get("quantidade") or comp.get("quantidade"), 531)
    if pmp < 10:
        pmp *= 1000
    return {
        "pv_id": "PV_1",
        "fabricante_painel": dados.get("fabricante_painel") or comp.get("fabricante_nome") or "CanadianSolar",
        "modelo_painel": dados.get("modelo_painel") or comp.get("nome_modelo") or "TOPBiHiKu6-610W",
        "Pmp": pmp,
        "Isc": _safe_float(dados.get("Isc")) or 15.97,
        "Voc": _safe_float(dados.get("Voc")) or 48,
        "Imp": _safe_float(dados.get("Imp")) or 14.96,
        "Vmp": _safe_float(dados.get("Vmp")) or 40.8,
        "Uisc": _safe_float(dados.get("Uisc")) or 0.05,
        "Uvoc": _safe_float(dados.get("Uvoc")) or -0.25,
        "Upmp": _safe_float(dados.get("Upmp")) or -0.29,
        "material_painel": dados.get("material_painel") or "Silicio",
        "eficiencia": _safe_float(dados.get("eficiencia")) or 22.6,
        "quantidade": [quantidade, 1],
    }


def _inversor_info(node: dict, indice: int = 1) -> dict:
    comp = _node_componente(node)
    dados = _dados_modelo(node)
    return {
        "inv_id": f"Inv_{indice}",
        "fabricante_inversor": dados.get("fabricante_inversor") or comp.get("fabricante_nome") or "Deye",
        "modelo_inversor": dados.get("modelo_inversor") or comp.get("nome_modelo") or "SUN-35K-SG01HP3-EU-BM",
        "Nm_MPPT": _safe_int(dados.get("Nm_MPPT"), 3),
        "In_Pmax": _safe_float(dados.get("In_Pmax") or comp.get("potencia_kw")) or 56,
        "Imax_MPPT": _safe_float(dados.get("Imax_MPPT")) or 36,
        "In_Vnom": _safe_float(dados.get("In_Vnom") or comp.get("tensao_nominal_v")) or 600,
        "In_Vmin": _safe_float(dados.get("In_Vmin")) or 150,
        "In_Vmax": _safe_float(dados.get("In_Vmax")) or 1000,
        "In_MPP_Vmin": _safe_float(dados.get("In_MPP_Vmin")) or 150,
        "In_MPP_Vmax": _safe_float(dados.get("In_MPP_Vmax")) or 850,
        "Out_Pmax": _safe_float(dados.get("Out_Pmax") or comp.get("potencia_kw")) or 38.5,
        "Out_Imax": _safe_float(dados.get("Out_Imax")) or 58.4,
        "Out_VL_nom": _safe_float(dados.get("Out_VL_nom")) or 380,
        "Out_Freq": _safe_float(dados.get("Out_Freq")) or 60,
        "Eficiencia": _safe_float(dados.get("Eficiencia")) or 0.976,
        "Max_THD": _safe_float(dados.get("Max_THD")) or 3,
        "Fator_pot": _safe_float(dados.get("Fator_pot")) or 0.9999,
        "Nm_fases": _safe_int(dados.get("Nm_fases"), 3),
        "smart": bool(dados.get("smart", False)),
        "quantidade": _safe_int(dados.get("quantidade"), 1),
    }


def _carga_info(node: dict, indice: int = 1) -> dict:
    comp = _node_componente(node)
    dados = _dados_modelo(node)
    return {
        "carga_id": f"Load_{indice}",
        "nome_carga": dados.get("nome_carga") or comp.get("nome_modelo") or "Mercado",
        "tipo_carga": dados.get("tipo_carga") or "Comercial",
        "curva_carga": dados.get("curva_carga") or "perfil_carga_ifg.csv",
        "curva_carga_pontos": dados.get("curva_carga_pontos") or [],
        "consumo_mensal_kwh": _safe_float(dados.get("consumo_mensal_kwh")),
        "demanda_ponta_kw": _safe_float(dados.get("demanda_ponta_kw")),
        "demanda_fora_ponta_kw": _safe_float(dados.get("demanda_fora_ponta_kw")),
        "s_instalada": _safe_float(dados.get("s_instalada") or comp.get("potencia_kw")) or 12000,
        "fp": _safe_float(dados.get("fp")) or 0.9999,
        "v_nom": _safe_float(dados.get("v_nom") or comp.get("tensao_nominal_v")) or 380,
        "f_rede": _safe_float(dados.get("f_rede")) or 60,
        "quantidade": _safe_int(dados.get("quantidade"), 1),
    }


def _bateria_info(node: dict) -> dict:
    comp = _node_componente(node)
    dados = _dados_modelo(node)
    capacidade = _safe_float(dados.get("capacidade_kwh") or comp.get("energia_kwh")) or 500
    potencia = _safe_float(dados.get("potencia_max_descarga_kw") or comp.get("potencia_kw")) or min(capacidade, 230)
    return {
        "bateria_id": "Batt_1",
        "fabricante": dados.get("fabricante") or comp.get("fabricante_nome") or "BYD",
        "modelo": dados.get("modelo") or comp.get("nome_modelo") or "Battery-Box Premium HVS",
        "capacidade_kwh": capacidade,
        "tensao_nominal": _safe_float(dados.get("tensao_nominal") or comp.get("tensao_nominal_v")) or 480,
        "potencia_max_carga_kw": _safe_float(dados.get("potencia_max_carga_kw")) or potencia,
        "potencia_max_descarga_kw": potencia,
        "soc_min": _safe_float(dados.get("soc_min")) or 20,
        "soc_max": _safe_float(dados.get("soc_max")) or 100,
        "soc_inicial": _safe_float(dados.get("soc_inicial")) or 50,
        "eficiencia_carga": _safe_float(dados.get("eficiencia_carga")) or 0.95,
        "eficiencia_descarga": _safe_float(dados.get("eficiencia_descarga")) or 0.95,
        "vida_util_ciclos": _safe_int(dados.get("vida_util_ciclos"), 6000),
        "quantidade": _safe_int(dados.get("quantidade"), 1),
        "periodo_de_carga": dados.get("periodo_de_carga") or {"permitir_carga": True, "horario_carga_permitido": "10:00-16:00"},
        "periodo_de_descarga": dados.get("periodo_de_descarga") or {"permitir_descarga": True, "horario_descarga_permitido": "18:00-21:00"},
    }


def gerar_modelo_entradas(layout_json: dict, nome_projeto: str = "Projeto Simulador") -> dict:
    nodes = layout_json.get("nodes", []) or []
    edges = layout_json.get("edges", []) or []
    pv_node = _first_node_by_tipo(nodes, "modulo_fv")
    inv_nodes = _nodes_by_tipo(nodes, "inversor")
    carga_nodes = _nodes_by_tipo(nodes, "carga")
    bateria_node = _first_node_by_tipo(nodes, "bateria")
    bus_node = _first_node_by_tipo(nodes, "barramento")
    diesel_node = _first_node_by_tipo(nodes, "gerador_diesel")
    clima_node = _first_node_by_tipo(nodes, "clima")

    modelo = {
        "nome_projeto": nome_projeto,
        "conectado_rede": True,
        "Config_Simulacao": [{"Tipo_Sim": "ViabilidadeEconomica", "Passo_sim": 1, "Tempo_sim": 8760}],
        "Clima_Ambiente": [{**deepcopy(DEFAULT_CLIMA), **_dados_modelo(clima_node or {})}],
        "painel_info": [_painel_info(pv_node)] if pv_node else [_painel_info({})],
        "inversor_info": [_inversor_info(node, indice) for indice, node in enumerate(inv_nodes, 1)] if inv_nodes else [_inversor_info({})],
        "cargas_info": [_carga_info(node, indice) for indice, node in enumerate(carga_nodes, 1)] if carga_nodes else [_carga_info({})],
        "bateria_info": [_bateria_info(bateria_node)] if bateria_node else [_bateria_info({})],
        "barramento_info": [{"bus_id": "Bus_ac_1", "tipo": "AC", "fases": 3, "V_linha_nominal": 380, "V_fase_nominal": 220, "V_min": 0.9, "V_max": 1.1}],
        "geradordiesel_info": [],
        "tarifas_energia": deepcopy(DEFAULT_TARIFAS_ENERGIA),
        "grafo_conexoes": [],
    }

    if diesel_node:
        comp = _node_componente(diesel_node)
        dados = _dados_modelo(diesel_node)
        modelo["geradordiesel_info"] = [{
            "diesel_id": "Diesel_1",
            "fabricante": dados.get("fabricante") or comp.get("fabricante_nome") or "Cummins",
            "modelo": dados.get("modelo") or comp.get("nome_modelo") or "C275D5",
            "potencia_nominal_kw": _safe_float(dados.get("potencia_nominal_kw") or comp.get("potencia_kw")) or 275,
            "potencia_minima_kw": 82.5,
            "tensao_nominal": _safe_float(dados.get("tensao_nominal") or comp.get("tensao_nominal_v")) or 380,
            "frequencia": 60,
            "fases": 3,
            "fator_potencia": 0.8,
            "eficiencia_nominal": 0.35,
            "consumo_especifico_diesel": 0.24,
            "capacidade_tanque_litros": 500,
            "custo_diesel_litro": 6.5,
            "custo_manutencao_hora": 15.0,
            "custo_investimento": 150000,
            "vida_util_horas": 30000,
            "tempo_partida_minutos": 2,
            "tempo_parada_minutos": 1,
            "emisso_co2_kg_litro": 2.68,
            "nivel_ruido_db": 75,
            "quantidade": 1,
            "operacao": {"modo_operacao": "backup", "prioridade": 3, "permitir_paralelismo_rede": False, "horario_operacao_permitido": "24h"},
        }]

    prefixo_por_tipo = {
        "modulo_fv": "PV",
        "inversor": "Inv",
        "bateria": "Batt",
        "barramento": "Bus_ac",
        "carga": "Load",
        "gerador_diesel": "Diesel",
    }
    contadores = {}
    mapa = {}
    for node in nodes:
        tipo = _node_componente(node).get("tipo_codigo")
        if tipo == "clima":
            mapa[node.get("id")] = "Clima_Ambiente"
            continue
        prefixo = prefixo_por_tipo.get(tipo)
        if not prefixo:
            continue
        contadores[tipo] = contadores.get(tipo, 0) + 1
        mapa[node.get("id")] = f"{prefixo}_{contadores[tipo]}"
    for edge in edges:
        source = mapa.get(edge.get("source"))
        target = mapa.get(edge.get("target"))
        if source and target:
            modelo["grafo_conexoes"].append({"between": [source, target]})
    if not modelo["grafo_conexoes"]:
        modelo["grafo_conexoes"] = [
            {"between": ["Clima_Ambiente", "PV_1"]},
            {"between": ["PV_1", "Inv_1"]},
            {"between": ["Batt_1", "Inv_1"]},
        ]
        modelo["grafo_conexoes"].extend(
            {"between": [f"Inv_{indice}", "Bus_ac_1"]}
            for indice in range(1, len(modelo["inversor_info"]) + 1)
        )
        modelo["grafo_conexoes"].extend(
            {"between": ["Bus_ac_1", f"Load_{indice}"]}
            for indice in range(1, len(modelo["cargas_info"]) + 1)
        )

    return adaptar_para_analise_financeira(modelo)


def gerar_diagrama_base() -> dict:
    tipos_em_ordem = [
        ("clima", {"x": 40, "y": 30}),
        ("modulo_fv", {"x": 260, "y": 30}),
        ("inversor", {"x": 500, "y": 30}),
        ("barramento", {"x": 740, "y": 120}),
        ("carga", {"x": 980, "y": 120}),
        ("bateria", {"x": 260, "y": 250}),
        ("pcs", {"x": 500, "y": 250}),
        ("gerador_diesel", {"x": 740, "y": 300}),
    ]
    componentes_por_tipo = {}
    for codigo, _ in tipos_em_ordem:
        comp = (
            Componente.objects.select_related("fabricante", "tipo")
            .filter(tipo__codigo=codigo, ativo=True)
            .order_by("id")
            .first()
        )
        if comp:
            componentes_por_tipo[codigo] = {
                "id": comp.id,
                "fabricante": comp.fabricante_id,
                "fabricante_nome": comp.fabricante.nome,
                "tipo": comp.tipo_id,
                "tipo_nome": comp.tipo.nome,
                "tipo_codigo": comp.tipo.codigo,
                "nome_modelo": comp.nome_modelo,
                "descricao": comp.descricao,
                "ativo": comp.ativo,
                "potencia_kw": str(comp.potencia_kw) if comp.potencia_kw is not None else None,
                "tensao_nominal_v": str(comp.tensao_nominal_v) if comp.tensao_nominal_v is not None else None,
                "corrente_nominal_a": str(comp.corrente_nominal_a) if comp.corrente_nominal_a is not None else None,
                "energia_kwh": str(comp.energia_kwh) if comp.energia_kwh is not None else None,
                "modo_operacao": comp.modo_operacao,
            }
    fallback = {
        "clima": {"tipo_nome": "Clima", "fabricante_nome": "Sistema", "nome_modelo": "Goiania", "tipo_codigo": "clima", "dados_modelo": DEFAULT_CLIMA},
        "carga": {"tipo_nome": "Carga", "fabricante_nome": "Cliente", "nome_modelo": "Mercado", "tipo_codigo": "carga", "potencia_kw": "12000"},
        "gerador_diesel": {"tipo_nome": "Gerador Diesel", "fabricante_nome": "Cummins", "nome_modelo": "C275D5", "tipo_codigo": "gerador_diesel", "potencia_kw": "275"},
    }

    nodes = []
    for codigo, position in tipos_em_ordem:
        componente = componentes_por_tipo.get(codigo) or fallback.get(codigo)
        if not componente:
            continue
        nodes.append({
            "id": f"{codigo}_auto",
            "position": position,
            "data": {"label": f"{componente['tipo_nome']} - {componente['nome_modelo']}", "componente": componente},
            "style": _node_style(codigo),
        })

    def edge(source, target):
        return {"id": f"{source}_{target}", "source": source, "target": target, "animated": True, "style": {"strokeWidth": 2}}

    existing = {node["id"] for node in nodes}
    chain = [
        ("clima_auto", "modulo_fv_auto"),
        ("modulo_fv_auto", "inversor_auto"),
        ("bateria_auto", "pcs_auto"),
        ("pcs_auto", "barramento_auto"),
        ("inversor_auto", "barramento_auto"),
        ("barramento_auto", "carga_auto"),
        ("gerador_diesel_auto", "barramento_auto"),
    ]
    edges = [edge(source, target) for source, target in chain if source in existing and target in existing]
    return {"nodes": nodes, "edges": edges}


def _normalizar_valores_json(valor):
    if isinstance(valor, float) and not math.isfinite(valor):
        return None
    if isinstance(valor, dict):
        return {chave: _normalizar_valores_json(item) for chave, item in valor.items()}
    if isinstance(valor, list):
        return [_normalizar_valores_json(item) for item in valor]
    return valor


def _valor_tarifa(enquadramento: dict, chave: str) -> float | None:
    valor = enquadramento.get(chave)
    if valor in (None, "", 0, "0"):
        return None
    convertido = _safe_float(valor)
    return convertido if convertido > 0 else None


def _dividir_energia_por_periodo(energia_total: float, custos_base: dict) -> dict:
    energia_base = _safe_float(custos_base.get("energia_kwh"))
    ponta_base = _safe_float(custos_base.get("energia_ponta_kwh"))
    fora_base = _safe_float(custos_base.get("energia_fora_ponta_kwh"))
    if energia_base <= 0:
        energia_base = ponta_base + fora_base
    if energia_base <= 0:
        return {"ponta": 0.0, "intermediario": 0.0, "fora_ponta": energia_total}
    proporcao_ponta = min(max(ponta_base / energia_base, 0.0), 1.0)
    energia_ponta = energia_total * proporcao_ponta
    energia_restante = max(energia_total - energia_ponta, 0.0)
    energia_intermediaria = energia_restante * 0.15
    return {"ponta": energia_ponta, "intermediario": energia_intermediaria, "fora_ponta": energia_restante - energia_intermediaria}


def _calcular_custo_tarifario(enquadramento: dict, energia: dict, demanda_kw: float, custos_base: dict) -> float | None:
    grupo = str(enquadramento.get("grupo") or "A").upper()
    modalidade = str(enquadramento.get("modalidade") or "").lower()
    energia_total = _safe_float(energia.get("energia_kwh")) or _safe_float(energia.get("energia_comprada_kwh"))
    periodos = _dividir_energia_por_periodo(energia_total, custos_base)
    energia_ponta = _safe_float(energia.get("energia_ponta_kwh")) or periodos["ponta"]
    energia_fora = _safe_float(energia.get("energia_fora_ponta_kwh")) or periodos["fora_ponta"]
    energia_intermediaria = _safe_float(energia.get("energia_intermediario_kwh")) or periodos["intermediario"]

    if grupo == "A" and modalidade == "verde":
        valores = [_valor_tarifa(enquadramento, "consumo_ponta_rs_kwh"), _valor_tarifa(enquadramento, "consumo_fora_ponta_rs_kwh"), _valor_tarifa(enquadramento, "demanda_rs_kw")]
        if any(valor is None for valor in valores):
            return None
        return energia_ponta * valores[0] + energia_fora * valores[1] + demanda_kw * valores[2]
    if grupo == "A" and modalidade == "azul":
        valores = [
            _valor_tarifa(enquadramento, "consumo_ponta_rs_kwh"),
            _valor_tarifa(enquadramento, "consumo_fora_ponta_rs_kwh"),
            _valor_tarifa(enquadramento, "demanda_ponta_rs_kw"),
            _valor_tarifa(enquadramento, "demanda_fora_ponta_rs_kw"),
        ]
        if any(valor is None for valor in valores):
            return None
        proporcao_ponta = energia_ponta / max(energia_ponta + energia_fora, 1.0)
        demanda_ponta_kw = demanda_kw * min(max(proporcao_ponta, 0.0), 1.0)
        demanda_fora_kw = max(demanda_kw - demanda_ponta_kw, 0.0)
        return energia_ponta * valores[0] + energia_fora * valores[1] + demanda_ponta_kw * valores[2] + demanda_fora_kw * valores[3]
    if grupo == "B" and modalidade == "convencional":
        consumo = _valor_tarifa(enquadramento, "consumo_rs_kwh")
        return None if consumo is None else energia_total * consumo
    if grupo == "B" and modalidade == "branca":
        valores = [
            _valor_tarifa(enquadramento, "consumo_fora_ponta_rs_kwh"),
            _valor_tarifa(enquadramento, "consumo_intermediario_rs_kwh"),
            _valor_tarifa(enquadramento, "consumo_ponta_rs_kwh"),
        ]
        if any(valor is None for valor in valores):
            return None
        return energia_fora * valores[0] + energia_intermediaria * valores[1] + energia_ponta * valores[2]
    return None


def _calcular_vpl(fluxos: list[float], taxa: float = 0.08) -> float:
    return sum(_safe_float(fluxo) / ((1 + taxa) ** indice) for indice, fluxo in enumerate(fluxos))


def _calcular_tir(fluxos: list[float]) -> float | None:
    if not fluxos or not any(fluxo < 0 for fluxo in fluxos) or not any(fluxo > 0 for fluxo in fluxos):
        return None
    baixo, alto = -0.99, 1.0
    for _ in range(80):
        meio = (baixo + alto) / 2
        vpl = _calcular_vpl(fluxos, meio)
        if vpl > 0:
            baixo = meio
        else:
            alto = meio
    return (baixo + alto) / 2


def _calcular_payback(fluxos: list[float]) -> int | None:
    acumulado = 0.0
    for indice, fluxo in enumerate(fluxos):
        acumulado += _safe_float(fluxo)
        if indice > 0 and acumulado >= 0:
            return indice
    return None


def aplicar_enquadramento_tarifario(resultado: dict, modelo_entradas: dict) -> dict:
    relatorio = ((resultado or {}).get("relatorio") or {})
    tarifas = (modelo_entradas or {}).get("tarifas_energia") or {}
    enquadramento = tarifas.get("enquadramento_tarifario") or {}
    if not isinstance(relatorio, dict) or not isinstance(enquadramento, dict) or not enquadramento:
        return resultado

    custos_base = relatorio.get("custos_base") or {}
    custos_micro = relatorio.get("custos_micro") or {}
    custo_base = _calcular_custo_tarifario(enquadramento, {"energia_kwh": custos_base.get("energia_kwh"), "energia_ponta_kwh": custos_base.get("energia_ponta_kwh"), "energia_fora_ponta_kwh": custos_base.get("energia_fora_ponta_kwh")}, _safe_float(custos_base.get("demanda_kw")), custos_base)
    custo_micro = _calcular_custo_tarifario(enquadramento, {"energia_comprada_kwh": custos_micro.get("energia_comprada_kwh")}, _safe_float(custos_micro.get("demanda_max_kw")), custos_base)
    if custo_base is None or custo_micro is None:
        relatorio["tarifa_aplicada"] = {"grupo": enquadramento.get("grupo"), "modalidade": enquadramento.get("modalidade"), "status": "incompleta", "observacao": "Preencha todas as tarifas da modalidade para recalcular a economia."}
        return resultado

    receita_vendida = _safe_float(custos_micro.get("receita_energia_vendida"))
    custo_diesel = _safe_float(custos_micro.get("custo_diesel"))
    custo_micro_liquido = max(custo_micro - receita_vendida + custo_diesel, 0.0)
    economia_original = _safe_float(relatorio.get("economia_anual"))
    capex_total = _safe_float((relatorio.get("capex") or {}).get("capex_total"))
    fluxo_ano_1_original = _safe_float((relatorio.get("fluxos_caixa") or [0, 0])[1])
    custo_operacional_estimado = max(economia_original - fluxo_ano_1_original, capex_total * 0.02)
    economia_anual = max(custo_base - custo_micro_liquido, 0.0)
    fluxo_liquido_ano_1 = economia_anual - custo_operacional_estimado
    fluxos = [-capex_total] + [fluxo_liquido_ano_1 * (1.035 ** (ano - 1)) for ano in range(1, 21)]
    saldo = []
    acumulado = 0.0
    for fluxo in fluxos:
        acumulado += fluxo
        saldo.append(acumulado)

    relatorio["custos_base"] = {**custos_base, "custo_total": custo_base}
    relatorio["custos_micro"] = {**custos_micro, "custo_total": custo_micro_liquido}
    relatorio["economia_anual_original"] = economia_original
    relatorio["economia_anual"] = economia_anual
    relatorio["percentual_reducao"] = (economia_anual / custo_base * 100) if custo_base else 0
    relatorio["fluxos_caixa"] = fluxos
    relatorio["saldo_acumulado"] = saldo
    relatorio["vpl"] = _calcular_vpl(fluxos)
    relatorio["tir"] = _calcular_tir(fluxos)
    relatorio["payback"] = _calcular_payback(fluxos)
    relatorio["tarifa_aplicada"] = {**enquadramento, "status": "aplicada", "custo_base_anual": custo_base, "custo_microrede_anual": custo_micro_liquido, "custo_operacional_estimado": custo_operacional_estimado, "observacao": "Economia recalculada conforme enquadramento tarifário informado pelo usuário."}
    return resultado


def preparar_modelo_para_motor_financeiro(modelo_entradas: dict) -> dict:
    modelo_runner = deepcopy(modelo_entradas)
    tarifas = modelo_runner.get("tarifas_energia")
    if isinstance(tarifas, dict):
        tarifas.pop("enquadramento_tarifario", None)
    return modelo_runner


@lru_cache(maxsize=1)
def _carregar_motor_fluxo_potencia():
    """Carrega o pandapower uma vez por processo do Django."""
    MICRORREDES_RUNTIME_PATH.mkdir(parents=True, exist_ok=True)
    numba_cache = MICRORREDES_RUNTIME_PATH / "numba-cache"
    numba_cache.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("NUMBA_CACHE_DIR", str(numba_cache))
    os.environ.setdefault("NUMBA_DISABLE_JIT", "1")

    microrredes_path = str(MICRORREDES_PATH)
    if microrredes_path not in sys.path:
        sys.path.insert(0, microrredes_path)

    # Uma configuração AutoRun do cmd torna a detecção padrão do Windows lenta.
    original_syscmd_ver = getattr(platform, "_syscmd_ver", None)
    if original_syscmd_ver is not None:
        platform._syscmd_ver = lambda *args, **kwargs: ("Microsoft", "Windows", "10.0")
    try:
        from microrredes.analises.fluxo_potencia import AnaliseFluxoPotencia
    finally:
        if original_syscmd_ver is not None:
            platform._syscmd_ver = original_syscmd_ver
    return AnaliseFluxoPotencia()


def _chave_cache_fluxo_potencia(modelo_entradas: dict) -> str:
    conteudo = json.dumps(
        modelo_entradas,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    return hashlib.sha256(conteudo).hexdigest()


def aquecer_motor_fluxo_potencia() -> None:
    """Antecipa a importação e a primeira inicialização do solucionador."""
    with _FLUXO_POTENCIA_LOCK:
        _carregar_motor_fluxo_potencia().executar_demo()


def executar_fluxo_potencia_microrredes(modelo_entradas: dict) -> dict:
    if not MICRORREDES_PATH.is_dir():
        raise FileNotFoundError(f"Projeto microrredes não encontrado em: {MICRORREDES_PATH}")
    if not isinstance(modelo_entradas, dict):
        raise TypeError("O fluxo de potência requer um objeto JSON com os equipamentos.")

    chave_cache = _chave_cache_fluxo_potencia(modelo_entradas)
    resultado_cache = _FLUXO_POTENCIA_CACHE.get(chave_cache)
    if resultado_cache is not None:
        resposta = deepcopy(resultado_cache)
        resposta["cache_utilizado"] = True
        resposta["tempo_execucao_segundos"] = 0.0
        return resposta

    inicio = time.perf_counter()
    with _FLUXO_POTENCIA_LOCK:
        resultado_cache = _FLUXO_POTENCIA_CACHE.get(chave_cache)
        if resultado_cache is not None:
            resposta = deepcopy(resultado_cache)
            resposta["cache_utilizado"] = True
            resposta["tempo_execucao_segundos"] = 0.0
            return resposta

        MICRORREDES_RUNTIME_PATH.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="fluxo-", dir=str(MICRORREDES_RUNTIME_PATH)) as pasta_temp:
            entrada_path = Path(pasta_temp) / "Entradas.json"
            with entrada_path.open("w", encoding="utf-8") as arquivo:
                json.dump(modelo_entradas, arquivo, ensure_ascii=False, indent=2)
            resultado = _carregar_motor_fluxo_potencia().executar_arquivo(entrada_path)

        resposta = {
            "status": "ok",
            "analise": "fluxo-potencia",
            "motor": "ProjetoPowerFlow/microrredes (carregado no backend)",
            "resultado": _normalizar_valores_json(resultado),
            "mensagem": "Fluxo de potência concluído.",
            "cache_utilizado": False,
            "tempo_execucao_segundos": round(time.perf_counter() - inicio, 3),
        }
        if len(_FLUXO_POTENCIA_CACHE) >= _FLUXO_POTENCIA_CACHE_MAX_ITEMS:
            _FLUXO_POTENCIA_CACHE.pop(next(iter(_FLUXO_POTENCIA_CACHE)))
        _FLUXO_POTENCIA_CACHE[chave_cache] = deepcopy(resposta)

    return resposta


def _resultado_financeiro_estimado(modelo_entradas: dict) -> dict:
    painel = (modelo_entradas.get("painel_info") or [{}])[0]
    bateria = (modelo_entradas.get("bateria_info") or [{}])[0]
    cargas = modelo_entradas.get("cargas_info") or [{}]
    diesel = (modelo_entradas.get("geradordiesel_info") or [{}])[0]
    tarifas = modelo_entradas.get("tarifas_energia") or DEFAULT_TARIFAS_ENERGIA
    pmp_kw = _safe_float(painel.get("Pmp")) / 1000
    qtd = painel.get("quantidade") or [1, 1]
    qtd_paineis = _safe_int(qtd[0] if isinstance(qtd, list) else qtd, 1)
    pv_kwp = pmp_kw * qtd_paineis
    bateria_kwh = _safe_float(bateria.get("capacidade_kwh"))
    carga_kw = sum(
        _safe_float(carga.get("s_instalada"))
        or max(_safe_float(carga.get("demanda_ponta_kw")), _safe_float(carga.get("demanda_fora_ponta_kw")), 0)
        for carga in cargas
    ) or 100
    energia_mensal = sum(_safe_float(carga.get("consumo_mensal_kwh")) for carga in cargas)
    energia_base = energia_mensal * 12 or carga_kw * 3650
    energia_ponta = energia_base * 0.08
    energia_fora = energia_base - energia_ponta
    energia_gerada = pv_kwp * 1550
    energia_comprada = max(energia_base - energia_gerada * 0.72, energia_base * 0.25)
    custos_inv = tarifas.get("custos_investimento", {})
    capex_pv = pv_kwp * _safe_float(custos_inv.get("pv_kwp") or 3500)
    capex_bess = bateria_kwh * _safe_float(custos_inv.get("bess_kwh") or 1900)
    capex_diesel = _safe_float(diesel.get("custo_investimento")) if diesel else 0
    capex_total = capex_pv + capex_bess + capex_diesel + (capex_pv + capex_bess) * 0.15
    custo_total_base = energia_ponta * 1.35 + energia_fora * 0.72 + carga_kw * 38
    custo_total_micro = energia_comprada * 0.72 + carga_kw * 22
    economia = max(custo_total_base - custo_total_micro, 0)
    fluxos = [-capex_total] + [(economia - capex_total * 0.02) * (1.035 ** (ano - 1)) for ano in range(1, 21)]
    saldo = []
    acumulado = 0.0
    for fluxo in fluxos:
        acumulado += fluxo
        saldo.append(acumulado)
    return {
        "relatorio": {
            "custos_base": {"energia_ponta_kwh": energia_ponta, "energia_fora_ponta_kwh": energia_fora, "energia_kwh": energia_base, "demanda_kw": carga_kw, "custo_total": custo_total_base},
            "custos_micro": {"energia_comprada_kwh": energia_comprada, "energia_vendida_kwh": max(energia_gerada - energia_base, 0), "demanda_max_kw": carga_kw * 0.7, "custo_total": custo_total_micro, "receita_energia_vendida": 0, "custo_diesel": 0},
            "capex": {"custo_pv": capex_pv, "custo_bess": capex_bess, "custo_diesel": capex_diesel, "custos_adicionais": capex_total - capex_pv - capex_bess - capex_diesel, "capex_total": capex_total, "potencia_pv_kw": pv_kwp, "capacidade_bess_kwh": bateria_kwh, "potencia_diesel_kw": _safe_float(diesel.get("potencia_nominal_kw")) if diesel else 0},
            "economia_anual": economia,
            "percentual_reducao": (economia / custo_total_base * 100) if custo_total_base else 0,
            "vpl": _calcular_vpl(fluxos),
            "tir": _calcular_tir(fluxos),
            "payback": _calcular_payback(fluxos),
            "fluxos_caixa": fluxos,
            "saldo_acumulado": saldo,
        },
        "grafico": {},
    }


def executar_analise_financeira(layout_json: dict, nome_projeto: str = "Projeto Simulador", modelo_entradas: dict | None = None, modelo_origem: str | None = None) -> dict:
    if modelo_entradas is None:
        modelo_path = obter_modelo_analise_financeira_mais_recente()
        with modelo_path.open("r", encoding="utf-8") as arquivo:
            modelo_entradas = json.load(arquivo)
        modelo_origem = str(modelo_path)
    if not isinstance(modelo_entradas, dict):
        raise TypeError("O arquivo selecionado deve conter um objeto JSON.")

    resultado = None
    motor_analise = "estimativa_local_grafosbess"
    if PRIME_DJANGO_PYTHON.is_file():
        try:
            with tempfile.TemporaryDirectory(prefix="grafosbess-financeiro-") as pasta_temp:
                pasta_temp = Path(pasta_temp)
                entradas_path = pasta_temp / "Entradas.json"
                resultado_path = pasta_temp / "Resultado.json"
                modelo_runner = preparar_modelo_para_motor_financeiro(modelo_entradas)
                with entradas_path.open("w", encoding="utf-8") as arquivo:
                    json.dump(modelo_runner, arquivo, ensure_ascii=False, indent=2)
                processo = subprocess.run(
                    [str(PRIME_DJANGO_PYTHON), str(ANALISE_FINANCEIRA_RUNNER), str(entradas_path), str(resultado_path), str(settings.MEDIA_ROOT), str(PRIME_DJANGO_PATH)],
                    capture_output=True,
                    text=True,
                    timeout=180,
                    env={**os.environ, "PYTHONIOENCODING": "utf-8"},
                )
                if processo.returncode == 0 and resultado_path.exists():
                    with resultado_path.open("r", encoding="utf-8") as arquivo:
                        resultado = _normalizar_valores_json(json.load(arquivo))
                    motor_analise = "prime-django/apps/AnaliseEconomica"
                else:
                    detalhe = processo.stderr.strip() or processo.stdout.strip()
                    print(f"Falha no motor financeiro externo, usando estimativa local: {detalhe}")
        except Exception as exc:
            print(f"Falha no motor financeiro externo, usando estimativa local: {exc}")
    if resultado is None:
        resultado = _resultado_financeiro_estimado(modelo_entradas)

    resultado = aplicar_enquadramento_tarifario(resultado, modelo_entradas)
    return {
        "status": "ok",
        "modelo_origem": modelo_origem or "JSON da tela atual",
        "motor_analise": motor_analise,
        "modelo_entradas": modelo_entradas,
        "analise_financeira": resultado,
    }


def simular_diagrama(layout_json: dict, nome_projeto: str = "Projeto Simulador") -> dict:
    nodes = layout_json.get("nodes", []) or []
    edges = layout_json.get("edges", []) or []
    alertas = []
    total_potencia_kw = 0.0
    total_energia_kwh = 0.0
    nodes_by_id = {node.get("id"): node for node in nodes}
    tipos = []
    for node in nodes:
        componente = _node_componente(node)
        tipos.append(componente.get("tipo_codigo"))
        total_potencia_kw += _safe_float(componente.get("potencia_kw"))
        total_energia_kwh += _safe_float(componente.get("energia_kwh"))
        tipo_codigo = componente.get("tipo_codigo")
        label = (node.get("data") or {}).get("label") or node.get("id")
        if tipo_codigo == "bateria" and not componente.get("energia_kwh"):
            alertas.append(f"A bateria '{label}' está sem energia_kwh cadastrada.")
        if tipo_codigo in {"inversor", "pcs", "transformador"} and not componente.get("potencia_kw"):
            alertas.append(f"O componente '{label}' está sem potencia_kw cadastrada.")

    if "bateria" in tipos and "pcs" not in tipos and "inversor" not in tipos:
        alertas.append("Há bateria no projeto, mas não existe PCS ou inversor para conexão.")
    for edge in edges:
        source = edge.get("source")
        target = edge.get("target")
        if not source or not target:
            alertas.append("Existe uma conexão sem origem ou destino.")
            continue
        source_tipo = _node_componente(nodes_by_id.get(source) or {}).get("tipo_codigo")
        target_tipo = _node_componente(nodes_by_id.get(target) or {}).get("tipo_codigo")
        if source_tipo == "bateria" and target_tipo == "inversor":
            alertas.append("Bateria ligada diretamente em inversor FV. Verifique se este inversor opera como híbrido/PCS.")

    modelo_entradas_financeiro = gerar_modelo_entradas(layout_json, nome_projeto)
    return {
        "status": "ok" if not alertas else "atencao",
        "resumo": {"quantidade_nos": len(nodes), "quantidade_ligacoes": len(edges), "potencia_total_kw": round(total_potencia_kw, 2), "energia_total_kwh": round(total_energia_kwh, 2)},
        "alertas": alertas,
        "modelo_entradas": modelo_entradas_financeiro,
        "modelo_entradas_financeiro": modelo_entradas_financeiro,
    }
