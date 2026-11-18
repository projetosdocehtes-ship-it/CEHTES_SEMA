"""Adapta os ensaios transitórios existentes para a interface web."""
import json
import math
import tempfile
from copy import deepcopy
from pathlib import Path

from .services import _carregar_motor_fluxo_potencia, _FLUXO_POTENCIA_LOCK, MICRORREDES_RUNTIME_PATH, _normalizar_valores_json
from .analise_relatorio import analisar_relatorio


def _analisar_saida(resultado, evento, documento):
    if resultado.get('tipo_analise') == 'transitorio_reduzido_on_grid':
        potencia = resultado['parametros']['bess_kw']
        resultado['limites_bess'] = {'soc_minimo': 0.1, 'soc_maximo': 0.9, 'potencia_max_descarga_kw': potencia, 'potencia_max_carga_kw': potencia}
    elif 'soc' in resultado.get('serie_temporal', {}):
        from microrredes.analises.transitorio_bess_fv import _bess_do_documento
        bess = _bess_do_documento(documento)
        if bess:
            p = bess.parametros
            resultado['limites_bess'] = {'soc_minimo': p.soc_minimo, 'soc_maximo': p.soc_maximo, 'potencia_max_descarga_kw': p.potencia_max_descarga_kw, 'potencia_max_carga_kw': p.potencia_max_carga_kw}
    resultado['analise_automatica'] = analisar_relatorio(resultado, evento)


def executar_transitorio(modelo, cenario):
    if not isinstance(modelo, dict) or not isinstance(cenario, dict):
        raise ValueError('Informe o modelo e o cenário como objetos JSON.')

    def numero(campo, padrao, minimo, maximo):
        try:
            valor = float(cenario.get(campo, padrao))
        except (ValueError, TypeError):
            raise ValueError(f'{campo}: informe um número válido.')
        if not math.isfinite(valor) or not minimo <= valor <= maximo:
            raise ValueError(f'{campo}: use um valor entre {minimo} e {maximo}.')
        return valor

    tipo = cenario.get('tipo')
    if tipo not in {'perda_fv', 'degrau_carga', 'curto_3ph', 'falha_rede'}:
        raise ValueError('Tipo de cenário não suportado.')
    inicio = numero('inicio_s', 2, 0, 59)
    duracao = numero('duracao_s', 0.2, 0.02, 30)
    total = numero('tempo_s', 6, 0.1, 60)
    passo = numero('passo_s', 0.01, 0.001, 0.01)
    if inicio + duracao >= total:
        raise ValueError('O evento deve terminar antes do fim do ensaio, para observar a recuperação.')
    if duracao < 2 * passo or total / passo > 6000:
        raise ValueError('Use pelo menos dois passos por evento e no máximo 6000 passos por ensaio.')
    documento = deepcopy(modelo)
    diesel = documento.get('geradordiesel_info') or []
    if tipo != 'perda_fv' and not diesel:
        raise ValueError('Este ensaio requer um gerador diesel no projeto.')
    if tipo == 'falha_rede' and (not documento.get('bateria_info') or not documento.get('conectado_rede', True)):
        raise ValueError('A falha da distribuidora requer BESS e um projeto conectado à rede.')
    if tipo == 'perda_fv' and (not documento.get('painel_info') or not documento.get('bateria_info')):
        raise ValueError('A perda de strings requer FV e BESS neste modelo transitório.')
    if tipo == 'perda_fv' and not diesel and not documento.get('conectado_rede', True):
        raise ValueError('O ensaio FV+BESS sem diesel requer conexão à rede.')
    carga = (documento.get('cargas_info') or [{}])[0]
    carga_kw = float(carga.get('potencia_kw') or float(carga.get('s_instalada', 0)) / 1000 * float(carga.get('fp', 1)))
    if not math.isfinite(carga_kw) or carga_kw <= 0:
        raise ValueError('Informe uma carga positiva para o ensaio.')
    documento['Config_Simulacao'] = [{'Passo_sim': passo, 'Tempo_sim': total}]
    documento['estudos'] = {'transitorio': {'Passo_sim': passo, 'Tempo_sim': total, 'modo': 'offgrid'}}
    documento['rede_teste'] = {'carga_inicial_kw': carga_kw, 'fator_potencia_carga': float(carga.get('fp', 0.95))}
    documento['eventos'] = []
    evento = {'tipo': tipo, 'inicio_s': inicio, 'duracao_s': duracao, 'fim_s': inicio + duracao}

    if tipo == 'falha_rede':
        evento.update(
            partida_diesel_s=numero('partida_diesel_s', 2, 0, 30),
            rampa_diesel_s=numero('rampa_diesel_s', 1, 0.05, 30),
            retorno_rede_s=numero('retorno_rede_s', 1, 0, 30),
            disponibilidade_fv_percent=numero('disponibilidade_fv_percent', 0, 0, 100),
            carga_kw=numero('carga_kw', carga_kw, 0.001, 100000),
        )
        if evento['fim_s'] + evento['retorno_rede_s'] >= total - passo:
            raise ValueError('Reserve tempo após o retorno e a retransferência para observar a recuperação.')
        with _FLUXO_POTENCIA_LOCK:
            _carregar_motor_fluxo_potencia()
            from .falha_rede import simular_falha_rede
            resultado = simular_falha_rede(documento, evento, passo, total, evento['carga_kw'])
        _analisar_saida(resultado, evento, documento)
        return _normalizar_valores_json({'status': 'ok', 'evento': evento, 'escopo': 'Falha da distribuidora com BESS e diesel. Modelo reduzido de continuidade e balanço de potência; não calcula tensão, frequência ou sincronismo.', 'resultado': resultado})

    with _FLUXO_POTENCIA_LOCK:
        _carregar_motor_fluxo_potencia()
        from microrredes.analises.transitorio_bess_fv import ConfiguracaoTransitorio, TransitorioBessFV
        from microrredes.analises.transitorio_gerador_diesel import ConfiguracaoTransitorioDiesel, TransitorioGeradorDiesel
        with tempfile.TemporaryDirectory(prefix='transitorio-', dir=MICRORREDES_RUNTIME_PATH) as pasta:
            entrada = Path(pasta) / 'Entradas.json'
            if tipo == 'perda_fv':
                strings = numero('strings_totais', 16, 1, 10000)
                perdidas = numero('strings_perdidas', 4, 1, strings)
                if not strings.is_integer() or not perdidas.is_integer():
                    raise ValueError('As quantidades de strings devem ser inteiras.')
                evento.update(strings_totais=int(strings), strings_perdidas=int(perdidas))
                documento['Falhas_sim'] = [{'Tipo_Falha': 'Perda_String_FV', 'T_falha': [inicio], 'duracao_falha': [duracao], 'strings_totais': [int(strings)], 'strings_perdidas': [int(perdidas)]}]
                painel = documento['painel_info'][0]
                quantidade = painel.get('quantidade', 1)
                quantidade = math.prod(quantidade) if isinstance(quantidade, list) else float(quantidade)
                pv_kw = float(painel.get('Pmp', 0)) * quantidade / 1000
                bateria = documento['bateria_info'][0]
                energia = float(bateria.get('capacidade_kwh', 0))
                potencia = float(bateria.get('potencia_max_descarga_kw') or bateria.get('potencia_max_carga_kw') or 0)
                if pv_kw <= 0 or energia <= 0 or potencia <= 0:
                    raise ValueError('Informe potência FV, capacidade e potência do BESS positivas.')
                entrada.write_text(json.dumps(documento), encoding='utf-8')
                resultado = TransitorioBessFV(ConfiguracaoTransitorio(entrada=entrada, consumo_diario_kwh=carga_kw * 24, pv_kwp=pv_kw, bess_kwh=energia, bess_kw=potencia)).executar()
                escopo = 'Modelo transitório reduzido FV+BESS com os equipamentos do projeto.'
            else:
                registro = {'tipo': tipo, 'inicio_s': inicio, 'duracao_s': duracao}
                if tipo == 'degrau_carga':
                    registro['carga_kw'] = numero('carga_kw', carga_kw * 1.25, 0, 100000)
                else:
                    registro['resistencia_falta_ohm'] = numero('resistencia_falta_ohm', 0, 0, 100)
                evento.update(registro)
                documento['eventos'] = [registro]
                entrada.write_text(json.dumps(documento), encoding='utf-8')
                resultado = TransitorioGeradorDiesel(ConfiguracaoTransitorioDiesel.from_json(entrada)).executar()
                linhas = resultado['serie_temporal']
                resultado['serie_temporal'] = {key: [row.get(key) for row in linhas] for key in linhas[0]}
                escopo = 'Ensaio isolado do gerador diesel e carga, em modo ilhado; FV, BESS e distribuidora não participam deste ensaio.'
    resultado.pop('arquivo_entrada', None)
    _analisar_saida(resultado, evento, documento)
    return _normalizar_valores_json({'status': 'ok', 'evento': evento, 'escopo': escopo, 'resultado': resultado})
