import json
import numpy as np
from pathlib import Path

from django.conf import settings

from apps.Equipamentos import Classes, Prints, Var_globais


def carregar_entradas(json_path: Path) -> dict:
    with json_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def executar_simulacao(*, json_path: Path, output_dir: Path, por_equipamento=False):
    data = carregar_entradas(json_path)

    Equipamentos = {}

    # ✅ use .get(...) pra não quebrar se vier vazio
    for painel in data.get("painel_info") or []:
        painel_id = painel["pv_id"]
        Equipamentos[painel_id] = {
            "obj": Classes.Painel_Fotovoltaico(
                painel["pv_id"],
                painel["fabricante_painel"],
                painel["modelo_painel"],
                painel["Pmp"],
                painel["Isc"],
                painel["Voc"],
                painel["Imp"],
                painel["Vmp"],
                painel["Uisc"],
                painel["Uvoc"],
                painel["Upmp"],
                painel["material_painel"],
                painel["eficiencia"],
            ),
            "quantidade": painel.get("quantidade", 1),
        }

    for inversor in data.get("inversor_info") or []:
        inversor_id = inversor["inv_id"]
        Equipamentos[inversor_id] = {
            "obj": Classes.Inversor_DC_AC(
                inversor["inv_id"],
                inversor["Nm_MPPT"],
                inversor["In_Pmax"],
                inversor["Imax_MPPT"],
                inversor["In_Vnom"],
                inversor["In_Vmin"],
                inversor["In_Vmax"],
                inversor["In_MPP_Vmin"],
                inversor["In_MPP_Vmax"],
                inversor["Out_Pmax"],
                inversor["Out_Imax"],
                inversor["Out_VL_nom"],
                inversor["Out_Freq"],
                inversor["Eficiencia"],
                inversor["Max_THD"],
                inversor["Fator_pot"],
                inversor["Nm_fases"],
                inversor["smart"],
            ),
            "quantidade": inversor.get("quantidade", 1),
        }

    for bateria in data.get("bateria_info") or []:
        bateria_id = bateria["bat_id"]
        Equipamentos[bateria_id] = {
            "obj": Classes.Stack_Baterias(
                bateria["bat_id"],
                bateria["fabricante_bateria"],
                bateria["modelo_bateria"],
                bateria["Tipo_bateria"],
                bateria["Capacidade"],
                bateria["I_charge_max"],
                bateria["I_discharge_max"],
                bateria["V_min"],
                bateria["V_max"],
                bateria["V_nom"],
                bateria["DoD"],
                bateria["Ciclo_vida"],
            ),
            "quantidade": bateria.get("quantidade", 1),
        }

    for bateria in data.get('bateria_info') or []:
        parametros = Equipamentos[bateria['bat_id']]['obj'].Bateria_Param
        if 'soc_inicial_fracao' in bateria:
            parametros.Cond_Iniciais_soc = [bateria['soc_inicial_fracao']]
        parametros.escala_tensao_ocv = bateria.get('escala_tensao_ocv', 1)

    from apps.Equipamentos.balanco import EloCC
    for inversor in data.get('inversor_info') or []:
        if inversor.get('elo_cc'):
            Equipamentos[inversor['inv_id']]['obj'].elo_cc = EloCC(**inversor['elo_cc'])

    conectado_rede = data.get("conectado_rede", False)
    for carga in data.get("cargas_info") or []:
        carga_id = carga["carga_id"]
        Equipamentos[carga_id] = {
            "obj": Classes.Carga_ZIP(
                carga["carga_id"],
                carga["nome_carga"],
                carga["tipo_carga"],
                carga["curva_carga"],
                carga["s_instalada"],
                carga["fp"],
                carga["v_nom"],
                carga["f_rede"],
                conectado_rede,
            ),
            "quantidade": carga.get("quantidade", 1),
        }

    for barramento in data.get("barramento_info") or []:
        barramento_id = barramento["bus_id"]
        Equipamentos[barramento_id] = {
            "obj": Classes.Barramento(
                barramento["bus_id"],
                barramento["tipo"],
                barramento["fases"],
                barramento["V_linha_nominal"],
                barramento["V_fase_nominal"],
                barramento["V_min"],
                barramento["V_max"],
            ),
            "quantidade": 1,
        }

    clima_list = data.get("Clima_Ambiente") or []
    if clima_list:
        clima = clima_list[0]
        Equipamentos["Clima_Ambiente"] = {
            "obj": Classes.Clima_Ambiente(
                clima["clima_id"],
                clima["nome_cidade"],
                clima["pais"],
                clima["data"],
            ),
        }

    Config_Projeto = (data.get("Config_Simulacao") or [None])[0]
    Falhas_sim = data.get("Falhas_sim") or []
    grafo_conexoes = data.get("grafo_conexoes") or {}

    sistema = Classes.Sistema_Eletrico(Equipamentos, Config_Projeto, Falhas_sim, grafo_conexoes)

    # ✅ reseta globals por request (se usar Var_globais como estado)
    Var_globais.Passo_atual_global = 0

    for _ in range(Var_globais.Num_Iteracao_global):
        sistema.Simular_Sistema()
        Var_globais.Passo_atual_global += 1
        print(
            f"--- Passo {Var_globais.Passo_atual_global} de {Var_globais.Num_Iteracao_global} concluído ---",
        )

    # ✅ salvar gráficos em pasta conhecida
    output_dir.mkdir(parents=True, exist_ok=True)
    lista = ["Val_DC", "Val_AC", "Pot_AC", "Val_RMS", "Potencias"]
    
    # #print(json_path)
    # print(output_dir)
    # print("criar")
    # import time
    # time.sleep(5)
    
    arquivos = (Prints.Plot_Graficos_por_equipamento(Equipamentos, output_dir)
                if por_equipamento else Prints.Plot_Graficos(lista, Equipamentos, output_dir=str(output_dir)))
    
    from apps.Equipamentos.relatorio_balanco import gerar_balanco
    balanco, imagem_balanco = gerar_balanco(Equipamentos, data, output_dir, Var_globais.Passo_global, Var_globais.Num_Iteracao_global, sistema.partida)
    arquivos.insert(0, imagem_balanco)
    urls = arquivos_para_urls(arquivos, output_dir)
    resumo = {}
    janela = max(1, round(1 / 60 / Var_globais.Passo_global))
    for ident, info in Equipamentos.items():
        obj = info['obj']
        series = {}
        if isinstance(obj, Classes.Inversor_DC_AC):
            series.update(zip(('p_instantanea_w', 'p_ativa_w', 's_va', 'q_var'), obj.Resgata_Potencias_AC()))
            series.update(zip(('v_rms_v', 'i_rms_a'), obj.Resgata_Val_RMS_AC()))
        elif isinstance(obj, Classes.Stack_Baterias):
            series.update(zip(('v_dc_v', 'i_dc_a', 'p_dc_w', 'soc'), obj.Retornar_Val_Baterias()))
        elif isinstance(obj, Classes.Carga_ZIP):
            series.update(zip(('p_demandada_w', 'q_demandada_var'), obj.Retornar_Val_Carga_demandada()))
        elif isinstance(obj, Classes.Painel_Fotovoltaico):
            series.update(zip(('v_dc_v', 'i_dc_a', 'p_dc_w'), obj.Retornar_Val_Paineis()))
        elif isinstance(obj, Classes.Barramento):
            series['p_entregue_w'] = obj.P_entregue
            series['p_demandada_w'] = obj.P_demandada_total
        resumo[ident] = {}
        for chave, valores in series.items():
            arr = np.asarray(valores, dtype=float)
            if not np.all(np.isfinite(arr)):
                raise ValueError(f'Resultado não finito: {ident}/{chave}')
            resumo[ident][chave] = {'inicial': float(arr[0]), 'final': float(arr[-1]), 'min': float(arr.min()), 'max': float(arr.max()), 'media_ultimo_ciclo': float(arr[-janela:].mean())}
        if isinstance(obj, Classes.Inversor_DC_AC):
            resumo[ident]['protecoes'] = [{'tipo': str(tipo), 'tempo_s': float(passo * Var_globais.Passo_global)} for tipo, passo in obj.Protecoes_acionadas]

    return {
        "arquivos": arquivos,
        "urls": urls,
        "resumo": resumo,
        "balanco": balanco,
        "titulos": [f"{list(Equipamentos)[int(Path(a).parent.name.split('_')[-1])]} — {Path(a).stem}" if Path(a).parent.name.startswith('equipamento_') else Path(a).stem for a in arquivos] if por_equipamento else [Path(a).stem for a in arquivos],
        "passos": Var_globais.Num_Iteracao_global,
    }

def arquivos_para_urls(arquivos: list[str], output_dir: Path) -> list[str]:
    # output_dir precisa estar dentro do MEDIA_ROOT
    media_root = Path(settings.MEDIA_ROOT).resolve()
    output_dir = output_dir.resolve()

    rel_dir = output_dir.relative_to(media_root)  # ex: simulacoes/graficos/projeto_1
    base_url = settings.MEDIA_URL.rstrip("/")     # ex: /media

    urls = []
    for a in arquivos:
        name = Path(a).resolve().relative_to(output_dir).as_posix()
        urls.append(f"{base_url}/{rel_dir.as_posix()}/{name}")
    return urls
