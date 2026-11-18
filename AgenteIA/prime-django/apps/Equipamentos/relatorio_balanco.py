from pathlib import Path
import json
import numpy as np
import matplotlib.pyplot as plt


def gerar_balanco(equipamentos, dados, pasta, passo, n, partida=None):
    series = {k: np.zeros(n) for k in ('fv_w', 'bateria_w', 'elo_w', 'excedente_cc_w', 'capacidade_ac_w', 'saida_ac_w', 'demanda_w', 'entregue_w', 'carga_prevista_w')}
    elos, resumo_elos = {}, {}
    for ident, info in equipamentos.items():
        obj = info['obj']
        tipo = type(obj).__name__
        if tipo == 'Painel_Fotovoltaico':
            series['fv_w'] += np.asarray(obj.Retornar_Val_Paineis()[2])
        elif tipo == 'Stack_Baterias':
            series['bateria_w'] += np.asarray(obj.P_Baterias)
        elif tipo == 'Inversor_DC_AC':
            potencia_elo = np.zeros(n)
            if obj.elo_cc:
                elos[ident] = obj.historico_elo_cc
                potencia_elo = np.array([h['potencia_w'] for h in obj.historico_elo_cc])
                series['elo_w'] += potencia_elo
                series['excedente_cc_w'] += np.array([h['excedente_w'] for h in obj.historico_elo_cc])
                energias = [obj.elo_cc.energia_inicial] + [h['energia_j'] for h in obj.historico_elo_cc]
                tensoes = [np.sqrt(2 * obj.elo_cc.energia_inicial / obj.elo_cc.c)] + [h['tensao_v'] for h in obj.historico_elo_cc]
                resumo_elos[ident] = {'energia_inicial_j': obj.elo_cc.energia_inicial, 'energia_final_j': energias[-1],
                    'energia_min_j': min(energias), 'reserva_util_inicial_j': max(0, obj.elo_cc.energia_inicial - obj.elo_cc.e_min),
                    'tensao_min_v': min(tensoes), 'tensao_max_v': max(tensoes), 'tensao_final_v': tensoes[-1],
                    'erro_balanco_max_j': max(abs(h['erro_j']) for h in obj.historico_elo_cc)}
            series['capacidade_ac_w'] += np.maximum(np.asarray(obj.p_dc_liquida_w) + potencia_elo, 0) * obj.Inversor_Param.Eficiencia
            series['saida_ac_w'] += np.asarray(obj.saida_P_AC)
        elif tipo == 'Carga_ZIP':
            series['carga_prevista_w'] += np.asarray(obj.P_Prevista)
        elif tipo == 'Barramento':
            if len(obj.P_entregue) != n:
                raise ValueError('Balanço requer barramentos conectados com medições em todos os passos.')
            series['demanda_w'] += np.asarray(obj.P_demandada_total)
            series['entregue_w'] += np.asarray(obj.P_entregue)
    tempo = np.arange(n) * passo
    deficit = np.maximum(series['demanda_w'] - series['entregue_w'], 0)
    series['deficit_w'] = deficit
    def medidas(inicio, fim):
        mask = (tempo >= inicio - 1e-10) & (tempo < fim - 1e-10)
        if not mask.any():
            return {}
        return {'inicio_s': inicio, 'fim_s': fim,
                **{k.replace('_w', '_medio_kw'): float(v[mask].mean() / 1000) for k, v in series.items()},
                'deficit_max_kw': float(deficit[mask].max() / 1000),
                'duracao_deficit_s': float(np.count_nonzero(deficit[mask] > 1) * passo),
                'energia_nao_atendida_wh': float(deficit[mask].sum() * passo / 3600)}
    resumo = {'modelo': 'Modelo reduzido de potência média CC/CA. Reserva capacitiva finita quando configurada; não é um modelo EMT validado.',
              'elos_cc': resumo_elos,
              'erro_conservacao_max_w': float(np.maximum(series['saida_ac_w'] - series['capacidade_ac_w'], 0).max()),
              'ensaio_com_partida': medidas(0, n * passo), 'apos_partida_50ms': medidas(0.05, n * passo)}
    if partida:
        espera = tempo < partida.fechamento_s if partida.fechamento_s is not None else np.ones(n, dtype=bool)
        resumo['partida'] = {'estado_final': partida.estado, 'fim_precarga_s': partida.fim_precarga_s,
            'fechamento_contator_s': partida.fechamento_s, 'tempo_estavel_exigido_s': partida.tempo_estavel_s,
            'tempo_carga_desconectada_s': float(espera.sum() * passo),
            'energia_adiada_espera_wh': float(series['carga_prevista_w'][espera].sum() * passo / 3600)}
        if partida.fechamento_s is not None:
            resumo['apos_conexao'] = medidas(partida.fechamento_s, n * passo)
    for falha in dados.get('Falhas_sim', []):
        if falha['Tipo_Falha'] == 'Mudanca_Irradiancia' and falha['T_falha']:
            inicio, duracao = falha['T_falha'][0], falha['duracao_falha'][0]
            resumo['queda_irradiancia'] = medidas(inicio, inicio + duracao)
            resumo['recuperacao'] = medidas(inicio + duracao, n * passo)
            break
    Path(pasta, 'series_balanco.json').write_text(json.dumps({'tempo_s': tempo.tolist(), 'elos_cc': elos, **{k: v.tolist() for k, v in series.items()}}), encoding='utf-8')
    fig, axes = plt.subplots(4 if elos else 3, 1, figsize=(12, 14 if elos else 11), sharex=True)
    for chave, label in [('demanda_w', 'Demanda'), ('entregue_w', 'Entregue à carga'), ('capacidade_ac_w', 'Disponível após perdas CC/CA')]:
        axes[0].plot(tempo, series[chave] / 1000, label=label)
    if partida:
        axes[0].plot(tempo, series['carga_prevista_w'] / 1000, '--', label='Carga prevista (aguarda contator)')
        for instante, label in [(partida.fim_precarga_s, 'Fim da pré-carga'), (partida.fechamento_s, 'Fechamento do contator')]:
            if instante is not None:
                axes[0].axvline(instante, linestyle=':', label=label)
    for chave, label in [('fv_w', 'FV CC'), ('bateria_w', 'Bateria CC (+descarga / -carga)'), ('elo_w', 'Elo CC (+fornecimento / -recarga)')]:
        axes[1].plot(tempo, series[chave] / 1000, label=label)
    axes[2].plot(tempo, deficit / 1000, label='Carga não atendida', color='red')
    # Evita ampliar arredondamentos de ponto flutuante como déficits visíveis.
    axes[2].set_ylim(0, max(1.0, float(deficit.max() / 1000) * 1.1))
    for ax in axes:
        ax.set_ylabel('Potência [kW]')
        ax.grid(True)
    if elos:
        for ident, h in elos.items():
            axes[3].plot(tempo, [p['tensao_v'] for p in h], label=f'{ident}: tensão do elo CC')
        axes[3].set_ylabel('Tensão [V]')
    for ax in axes:
        ax.legend()
    axes[-1].set_xlabel('Tempo [s]')
    fig.suptitle('Balanço de potência CC/CA e atendimento da carga')
    fig.tight_layout()
    caminho = Path(pasta, 'Balanco_CC_CA.png')
    fig.savefig(caminho, dpi=150)
    plt.close(fig)
    return resumo, str(caminho)
