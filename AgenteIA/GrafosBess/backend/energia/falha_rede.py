"""Ensaio reduzido de continuidade: rede, BESS e partida do diesel.

Não calcula tensão/frequência ou sincronismo. A retransferência é ideal.
"""
import math


def simular_falha_rede(documento, evento, passo, total, carga_kw):
    from microrredes.analises.transitorio_bess_fv import _bess_do_documento, _pv_nominal

    bess = _bess_do_documento(documento)
    diesel = documento['geradordiesel_info'][0]
    nominal = float(diesel.get('potencia_nominal_kw', 0))
    limite = float(diesel.get('potencia_maxima_kw') or nominal)
    minimo = float(diesel.get('potencia_minima_kw', 0))
    if not all(math.isfinite(v) for v in (nominal, limite, minimo)) or not 0 <= minimo <= limite <= nominal or nominal <= 0:
        raise ValueError('Informe limites de potência válidos para o gerador diesel.')
    if bess is None or bess.parametros.potencia_max_descarga_kw <= 0:
        raise ValueError('O cenário requer um BESS com potência de descarga positiva.')
    pv = _pv_nominal(documento, 0) * evento['disponibilidade_fv_percent'] / 100
    if not math.isfinite(pv):
        raise ValueError('Potência FV inválida.')
    partida = evento['inicio_s'] + evento['partida_diesel_s']
    transferencia = evento['fim_s'] + evento['retorno_rede_s']
    serie = {key: [] for key in ('tempo_s', 'pv_kw', 'carga_kw', 'bess_kw', 'diesel_kw', 'rede_kw', 'deficit_kw', 'curtailment_kw', 'soc', 'rede_disponivel', 'rede_conectada', 'diesel_conectado')}
    potencia_diesel = comando_bess = 0.0
    soc_inicial = bess.estado.soc
    # BESS assume a diferença durante a partida e a rampa do grupo gerador.
    for i in range(int(round(total / passo)) + 1):
        t = round(i * passo, 9)
        dt = 0 if i == 0 else passo
        rede_disponivel = not evento['inicio_s'] <= t < evento['fim_s']
        conectada = t < evento['inicio_s'] or t >= transferencia
        diesel_conectado = not conectada and t >= partida
        residual = carga_kw - pv
        if diesel_conectado:
            alvo = min(max(residual, minimo), limite)
            incremento = nominal / evento['rampa_diesel_s'] * dt
            potencia_diesel += max(-incremento, min(incremento, alvo - potencia_diesel))
        else:
            potencia_diesel = 0.0
        alvo_bess = 0.0 if conectada else residual - potencia_diesel
        if conectada:
            comando_bess = 0.0
        else:
            comando_bess += (alvo_bess - comando_bess) * (1 - math.exp(-dt / 0.03))
        estado = bess.passo_potencia(max(dt, 1e-12), comando_bess)
        bateria = estado.potencia_kw
        saldo = residual - potencia_diesel - bateria
        rede = saldo if conectada else 0.0
        deficit = max(saldo, 0.0) if not conectada else 0.0
        corte = max(-saldo, 0.0) if not conectada else 0.0
        valores = (t, pv, carga_kw, bateria, potencia_diesel, rede, deficit, corte, estado.soc, int(rede_disponivel), int(conectada), int(diesel_conectado))
        for key, value in zip(serie, valores):
            serie[key].append(value)
    avisos = ['BESS em espera antes da falha; FV mantido no nível de disponibilidade informado. Resposta de potência do BESS: 30 ms. Retransferência ideal, sem sincronismo modelado.']
    if partida >= transferencia:
        avisos.append('A rede foi reconectada antes da conclusão da partida: o diesel não chegou a assumir carga.')
    if pv >= carga_kw:
        avisos.append('A geração FV cobre a carga: o ensaio pode não exigir descarga do BESS ou potência do diesel.')
    return {
        'tipo_analise': 'falha_rede_balanco_dinamico_reduzido',
        'avisos': avisos,
        'marcos': [
            {'tempo_s': evento['inicio_s'], 'nome': 'Falha da rede'},
            *([{'tempo_s': partida, 'nome': 'Diesel disponível'}] if partida < transferencia else []),
            {'tempo_s': evento['fim_s'], 'nome': 'Retorno da rede'},
            {'tempo_s': transferencia, 'nome': 'Retransferência'},
        ],
        'resumo': {'soc_inicial': soc_inicial, 'soc_final': serie['soc'][-1], 'deficit_max_kw': max(serie['deficit_kw']), 'energia_nao_atendida_kwh': sum(serie['deficit_kw'][1:]) * passo / 3600},
        'serie_temporal': serie,
    }
