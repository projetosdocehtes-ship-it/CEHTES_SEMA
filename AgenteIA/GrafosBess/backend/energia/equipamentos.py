"""Execução isolada do motor legado, sem compartilhar entradas ou estado global."""
from copy import deepcopy
import json
import math
import os
from pathlib import Path
import subprocess
import sys
from uuid import uuid4

from django.conf import settings


def modelo_do_layout(modelo, layout):
    """Remove os equipamentos padrão e usa somente os nós presentes na tela."""
    from .services import _painel_info, _bateria_info, _dados_modelo
    dados = deepcopy(modelo)
    mapa = {}
    tipos = {'modulo_fv': ('painel_info', 'pv_id', 'PV'), 'inversor': ('inversor_info', 'inv_id', 'Inv'), 'bateria': ('bateria_info', 'bateria_id', 'Batt'), 'carga': ('cargas_info', 'carga_id', 'Load'), 'barramento': ('barramento_info', 'bus_id', 'Bus_ac'), 'clima': ('Clima_Ambiente', 'clima_id', 'Clima')}
    for tipo, (campo, chave, prefixo) in tipos.items():
        nodes = [n for n in layout.get('nodes', []) if n.get('data', {}).get('componente', {}).get('tipo_codigo') == tipo]
        anteriores = dados.get(campo, [])
        dados[campo] = []
        for i, node in enumerate(nodes):
            if tipo == 'modulo_fv':
                item = _painel_info(node)
                if _dados_modelo(node).get('grupos_mppt'):
                    item['grupos_mppt'] = deepcopy(_dados_modelo(node)['grupos_mppt'])
            elif tipo == 'bateria':
                item = _bateria_info(node)
            else:
                item = deepcopy(anteriores[min(i, len(anteriores) - 1)]) if anteriores else _dados_modelo(node)
            item[chave] = 'Clima_Ambiente' if tipo == 'clima' else f'{prefixo}_{i + 1}'
            if tipo == 'inversor' and _dados_modelo(node).get('elo_cc'):
                item['elo_cc'] = deepcopy(_dados_modelo(node)['elo_cc'])
            mapa[node['id']] = item[chave]
            dados[campo].append(item)
    dados['grafo_conexoes'] = [{'between': [mapa[e['source']], mapa[e['target']]]} for e in layout.get('edges', []) if e.get('source') in mapa and e.get('target') in mapa]
    return dados


def preparar_modelo(modelo, config):
    if not isinstance(modelo, dict) or not modelo.get('inversor_info'):
        raise ValueError('Inclua um inversor no projeto para executar Equipamentos.')
    config = config or {}
    tempo = float(config.get('tempo_s', 0.1))
    passo = float(config.get('passo_s', 0.00002))
    if not math.isfinite(tempo) or not math.isfinite(passo) or not 0.02 <= tempo <= 2 or not 0.000001 <= passo <= 0.0001 or tempo / passo > 100000:
        raise ValueError('Use duração de 0,02 a 2 s, passo de 1 a 100 µs e até 100.000 passos.')
    dados = deepcopy(modelo)
    dados['Config_Simulacao'] = [{'Tipo_Sim': 'Transiente', 'Tempo_sim': tempo, 'Passo_sim': passo}]
    partida = config.get('partida_sequenciada', True) and all(inv.get('elo_cc') for inv in dados['inversor_info'])
    if partida:
        dados['Config_Simulacao'][0]['partida_sequenciada'] = True
        for inv in dados['inversor_info']:
            inv['elo_cc']['tensao_inicial_v'] = 0.0
    avisos = ['Motor Equipamentos: clima constante de 25 °C e 1000 W/m²; não consulta meteorologia. O PCS separado e a dinâmica da rede distribuidora não são modelados.']
    if config.get('teste_irradiancia'):
        if tempo < 0.3:
            raise ValueError('Use pelo menos 0,3 s para testar queda e retorno da irradiância.')
        dados['Falhas_sim'] = [{'Tipo_Falha': 'Mudanca_Irradiancia', 'T_falha': [0.12], 'duracao_falha': [0.1], 'Val_Irrad': [100]}]
        avisos[0] = 'Ensaio de apoio da bateria: irradiância de 1000 para 100 W/m² em 0,12 s, retorno em 0,22 s; temperatura 25 °C. PCS separado e rede distribuidora não modelados.'
    avisos.append('A saída CA respeita a potência CC e a reserva finita do elo quando configurada; o relatório inclui a partida e as transições do modelo reduzido.')
    if partida:
        avisos.append('Partida sequenciada: pré-carga limitada a 50 kW até 95% da tensão nominal do elo; inversor estabilizado em ±2% da tensão nominal por 20 ms antes de fechar a carga. Fechamento e regulador de corrente em modelo médio ideal; o período desconectado é contabilizado como espera programada.')
    for inv in dados['inversor_info']:
        if inv.get('elo_cc'):
            elo = inv['elo_cc']
            avisos.append(f"{inv['inv_id']}: elo CC de {elo['capacitancia_f'] * 1000:g} mF; tensão inicial {elo['tensao_inicial_v']:g} V, faixa {elo['tensao_min_v']:g}–{elo['tensao_max_v']:g} V; recomposição em {elo['tempo_recomposicao_s'] * 1000:g} ms. Energia inicial e recarga contabilizadas no balanço.")
    # Cada grupo é uma entrada MPPT independente. Não comparar a corrente
    # agregada de toda a usina com o limite de uma única entrada.
    paineis = []
    for painel in dados.get('painel_info', []):
        grupos = painel.pop('grupos_mppt', None)
        if not grupos:
            paineis.append(painel)
            continue
        if sum(int(g['serie']) * int(g['paralelo']) for g in grupos) != math.prod(painel['quantidade']):
            raise ValueError('A distribuição dos MPPTs deve preservar a quantidade total de módulos.')
        origem = painel['pv_id']
        conexoes = [e for e in dados['grafo_conexoes'] if origem in e['between']]
        dados['grafo_conexoes'] = [e for e in dados['grafo_conexoes'] if origem not in e['between']]
        for indice, grupo in enumerate(grupos, 1):
            item = deepcopy(painel)
            item.update(pv_id=f'{origem}_MPPT_{indice}', quantidade=[int(grupo['serie']), int(grupo['paralelo'])], arranjo_serie_paralelo=True, mppt_independente=True)
            if min(item['quantidade']) <= 0:
                raise ValueError('Quantidades de módulos e strings devem ser positivas.')
            paineis.append(item)
            dados['grafo_conexoes'].extend({'between': [item['pv_id'] if i == origem else i for i in e['between']]} for e in conexoes)
            avisos.append(f"{item['pv_id']}: {grupo['serie']} módulos/string × {grupo['paralelo']} strings; Vmp={grupo['serie'] * painel['Vmp']:.1f} V, Isc={grupo['paralelo'] * painel['Isc']:.2f} A.")
    dados['painel_info'] = paineis
    for inv in dados['inversor_info']:
        grupos = [p for p in paineis if p.get('mppt_independente') and any(set(e['between']) == {p['pv_id'], inv['inv_id']} for e in dados.get('grafo_conexoes', []))]
        if len(grupos) > int(inv['Nm_MPPT']):
            raise ValueError('Quantidade de grupos FV excede as entradas MPPT.')
        for p in grupos:
            ns, np = p['quantidade']
            if ns * p['Voc'] > inv['In_Vmax'] or not inv['In_MPP_Vmin'] <= ns * p['Vmp'] <= inv['In_MPP_Vmax'] or np * p['Isc'] > inv['Imax_MPPT']:
                raise ValueError(f"{p['pv_id']}: tensão ou corrente incompatível com o MPPT de {inv['inv_id']}.")
    for carga in dados.get('cargas_info', []):
        if carga.get('unidade_s_instalada') != 'VA':
            fp = float(carga['fp'])
            if not 0 < fp <= 1:
                raise ValueError('Fator de potência da carga deve estar entre 0 e 1.')
            carga['s_instalada'] = float(carga['s_instalada']) * 1000 / fp
            carga['unidade_s_instalada'] = 'VA'
    for painel in dados.get('painel_info', []):
        if painel.get('arranjo_serie_paralelo'):
            continue
        ligados = [inv for inv in dados['inversor_info'] if any(set(e['between']) == {painel['pv_id'], inv['inv_id']} for e in dados.get('grafo_conexoes', []))]
        if not ligados:
            continue
        total = math.prod(painel['quantidade'])
        limite = min(min(float(inv['In_Vmax']) / float(painel['Voc']), float(inv['In_MPP_Vmax']) / float(painel['Vmp'])) for inv in ligados)
        minimo = max(float(inv['In_MPP_Vmin']) / float(painel['Vmp']) for inv in ligados)
        candidatos = [n for n in range(max(1, math.ceil(minimo)), math.floor(limite) + 1) if total % n == 0]
        if not candidatos:
            raise ValueError('Não há arranjo uniforme compatível com a quantidade FV e as tensões do inversor. Informe strings reais.')
        serie = max(candidatos)
        paralelo = int(total // serie)
        painel['quantidade'] = [serie, paralelo]
        painel['arranjo_serie_paralelo'] = True
        avisos.append(f"{painel['pv_id']}: arranjo equivalente sugerido de {serie} módulos em série × {paralelo} strings paralelas, preservando {total} módulos; validar distribuição física nos MPPTs.")
        if any(paralelo * float(painel['Imp']) > float(inv['Imax_MPPT']) * int(inv['Nm_MPPT']) for inv in ligados):
            avisos.append('Corrente total FV excede a capacidade agregada dos MPPTs do inversor selecionado; o arranjo não constitui dimensionamento aprovado.')
    for inv in dados['inversor_info']:
        capacidade = (math.sqrt(3) if int(inv['Nm_fases']) > 1 else 1) * float(inv['Out_VL_nom']) * float(inv['Out_Imax']) / 1000
        avisos.append(f"{inv['inv_id']}: limite AC por tensão/corrente = {capacidade:.2f} kVA; potência cadastrada = {inv['Out_Pmax']} kW.")
    for bateria in dados.get('bateria_info', []):
        if 'bat_id' in bateria:
            continue
        v = float(bateria['tensao_nominal'])
        if v <= 0 or float(bateria['capacidade_kwh']) <= 0:
            raise ValueError('A bateria precisa de tensão e capacidade positivas.')
        bateria.update(bat_id=bateria['bateria_id'], fabricante_bateria=bateria['fabricante'], modelo_bateria=bateria['modelo'], Tipo_bateria='Generica',
                       Capacidade=float(bateria['capacidade_kwh']) * 1000 / v,
                       I_charge_max=float(bateria['potencia_max_carga_kw']) * 1000 / v,
                       I_discharge_max=float(bateria['potencia_max_descarga_kw']) * 1000 / v,
                       V_min=v * 0.9, V_max=v * 1.1, V_nom=v, DoD=1 - float(bateria['soc_min']) / 100,
                       Ciclo_vida=bateria['vida_util_ciclos'], soc_inicial_fracao=float(bateria['soc_inicial']) / 100,
                       escala_tensao_ocv=v / 298.3, quantidade=[1, int(bateria.get('quantidade', 1))])
        avisos.append(f"{bateria['bat_id']}: capacidade convertida de kWh para Ah; curva de tensão genérica normalizada à tensão nominal. Limites e eficiência do PCS não são reproduzidos.")
    for campo in ('geradordiesel_info', 'geradorbiogas_info', 'eletrolizador_info', 'celulahidrogenio_info', 'turbinaeolica_info'):
        if dados.get(campo):
            avisos.append(f'{campo}: componente presente no projeto, mas não simulado por este motor.')
        dados[campo] = []
    ids = set()
    for campo, chave in [('painel_info', 'pv_id'), ('inversor_info', 'inv_id'), ('bateria_info', 'bat_id'), ('cargas_info', 'carga_id'), ('barramento_info', 'bus_id'), ('Clima_Ambiente', 'clima_id')]:
        for item in dados.get(campo, []):
            ident = item[chave]
            if ident in ids:
                raise ValueError(f'Identificador duplicado: {ident}')
            ids.add(ident)
    dados['grafo_conexoes'] = [edge for edge in dados.get('grafo_conexoes', []) if all(i in ids for i in edge['between'])]
    ligados = {i for e in dados['grafo_conexoes'] for i in e['between']}
    for ident in sorted(ids - ligados):
        avisos.append(f'{ident} está sem conexão compatível com este motor; sua ligação não foi alterada.')
    return dados, avisos


def executar_equipamentos(modelo, config=None):
    dados, avisos = preparar_modelo(modelo, config)
    prime = Path(__file__).resolve().parents[3] / 'prime-django'
    pasta = Path(settings.MEDIA_ROOT).resolve() / 'equipamentos' / uuid4().hex
    pasta.mkdir(parents=True)
    entrada, saida = pasta / 'entradas.json', pasta / 'resultado.json'
    entrada.write_text(json.dumps(dados, ensure_ascii=False), encoding='utf-8')
    python = prime / 'venv' / 'Scripts' / 'python.exe'
    runner = Path(__file__).with_name('equipamentos_runner.py')
    with (pasta / 'execucao.log').open('w', encoding='utf-8') as log:
        try:
            processo = subprocess.run([str(python if python.is_file() else sys.executable), str(runner), str(entrada), str(saida), str(Path(settings.MEDIA_ROOT).resolve()), str(prime)], stdout=log, stderr=log, timeout=180, env={**os.environ, 'MPLBACKEND': 'Agg', 'PYTHONIOENCODING': 'utf-8'})
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError('Equipamentos excedeu 180 s. Reduza a duração ou a quantidade de equipamentos.') from exc
    if processo.returncode:
        detalhe = (pasta / 'execucao.log').read_text(encoding='utf-8')[-2000:]
        raise RuntimeError(f'Falha no motor Equipamentos: {detalhe}')
    resultado = json.loads(saida.read_text(encoding='utf-8'))
    if not resultado.get('urls'):
        raise RuntimeError('O motor terminou sem produzir gráficos.')
    return {**resultado, 'nome_projeto': dados.get('nome_projeto'), 'motor': 'Equipamentos - Projeto', 'avisos': avisos, 'configuracao': dados['Config_Simulacao'][0], 'modelo_entradas': dados}

