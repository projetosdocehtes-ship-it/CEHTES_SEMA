"""Leitura determinística das séries, sem emitir parecer de conformidade."""
import math


def analisar_relatorio(resultado, evento):
    serie = resultado.get('serie_temporal') or {}
    tempos = serie.get('tempo_s') or []
    itens = []

    def valores(*chaves):
        for chave in chaves:
            dados = serie.get(chave)
            if isinstance(dados, list) and any(valido(v) for v in dados):
                return dados
        return []

    def valido(v):
        return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)

    def adicionar(titulo, texto, nivel='informacao'):
        itens.append({'titulo': titulo, 'texto': texto, 'nivel': nivel})

    def fmt(v, casas=3):
        return f'{v:.{casas}f}'.replace('.', ',')

    if not tempos:
        return {'itens': [{'titulo': 'Dados insuficientes', 'texto': 'Não há série temporal para analisar.', 'nivel': 'atencao'}], 'criterios': 'Análise indisponível.'}

    deficit = valores('deficit_kw')
    if deficit:
        pico = max(v for v in deficit if valido(v))
        energia = sum(max(deficit[i], 0) * (tempos[i + 1] - tempos[i]) for i in range(min(len(deficit), len(tempos) - 1)) if valido(deficit[i]) and tempos[i + 1] > tempos[i]) / 3600
        adicionar('Atendimento da carga', f'Pico de carga não atendida: {fmt(pico)} kW. Energia não atendida estimada: {fmt(energia, 6)} kWh. Déficit zero não comprova qualidade de tensão ou frequência.', 'atencao' if pico > 1e-6 else 'informacao')
    else:
        adicionar('Atendimento da carga', 'Este relatório não informa déficit de potência; a continuidade do atendimento não pode ser concluída apenas pelas curvas de geração.')

    soc = valores('soc')
    bess = valores('bess_kw')
    if soc:
        validos = [v for v in soc if valido(v)]
        adicionar('Reserva do BESS', f'SOC inicial {fmt(validos[0] * 100, 2)}%; final {fmt(validos[-1] * 100, 2)}%; mínimo {fmt(min(validos) * 100, 2)}%. A autonomia além da janela simulada não foi avaliada.')
    if bess:
        adicionar('Resposta do BESS', f'Pico de descarga: {fmt(max(0, max(v for v in bess if valido(v))))} kW. Pico de carga: {fmt(max(0, -min(v for v in bess if valido(v))))} kW.')
    limites = resultado.get('limites_bess')
    if limites and soc and bess:
        atingiu_soc = min(v for v in soc if valido(v)) <= limites['soc_minimo'] + 1e-6
        atingiu_potencia = max(v for v in bess if valido(v)) >= limites['potencia_max_descarga_kw'] - 1e-6
        adicionar('Limites do BESS', f"SOC mínimo configurado: {fmt(limites['soc_minimo'] * 100, 2)}%. Limite de descarga: {fmt(limites['potencia_max_descarga_kw'])} kW. " + ('Reserva mínima atingida. ' if atingiu_soc else 'Reserva mínima não atingida. ') + ('Limite de potência de descarga atingido.' if atingiu_potencia else 'Limite de potência de descarga não atingido.'), 'atencao' if atingiu_soc or atingiu_potencia else 'informacao')

    diesel = valores('diesel_kw', 'potencia_eletrica_kw')
    if diesel:
        ativos = [tempos[i] for i, v in enumerate(diesel[:len(tempos)]) if valido(v) and v > 1e-6]
        adicionar('Resposta do diesel', f'Pico de geração: {fmt(max(v for v in diesel if valido(v)))} kW. ' + (f'Primeira potência positiva em {fmt(ativos[0])} s.' if ativos else 'Não houve geração do diesel na janela simulada.'))

    apenas_potencia = evento.get('tipo') == 'falha_rede'
    if apenas_potencia:
        adicionar('Limite do modelo', 'Este cenário calcula potência e SOC. Não calcula tensão, frequência, sincronismo nem comprova transferência sem interrupção.')
        conectado = serie.get('rede_conectada') or []
        retorno = evento.get('fim_s', 0) + evento.get('retorno_rede_s', 0)
        indices = [i for i, t in enumerate(tempos) if t >= retorno]
        recuperou = bool(indices) and all(i < len(conectado) and conectado[i] == 1 and i < len(deficit) and valido(deficit[i]) and deficit[i] <= 1e-6 for i in indices)
        adicionar('Recuperação da rede', f'Retransferência prevista em {fmt(retorno)} s. ' + ('Rede conectada e déficit nulo em todas as amostras após a retransferência.' if recuperou else 'A recuperação do atendimento após a retransferência não foi confirmada nas amostras disponíveis.'), 'informacao' if recuperou else 'atencao')
    else:
        gerador = resultado.get('configuracao', {}).get('gerador', {})
        nominal = gerador.get('frequencia_nominal_hz', 60)
        for titulo, dados, referencia, tolerancia, unidade in (
            ('Frequência', valores('frequencia_hz'), nominal, 0.1, 'Hz'),
            ('Tensão', valores('tensao_pcc_pu', 'tensao_pu'), 1.0, 0.01, 'pu'),
        ):
            if not dados:
                continue
            validos = [v for v in dados if valido(v)]
            ultimo_valido = valido(dados[-1])
            recuperou = ultimo_valido and abs(dados[-1] - referencia) <= tolerancia and tempos[-1] > evento.get('fim_s', tempos[-1])
            adicionar(titulo, f'Mínimo {fmt(min(validos))} {unidade}; máximo {fmt(max(validos))} {unidade}; último valor válido {fmt(validos[-1])} {unidade}. ' + (f'A amostra final está próxima da referência {fmt(referencia)} {unidade}.' if recuperou else 'Retorno à referência não confirmado na amostra final.') + ' Isso não comprova estabilização ou conformidade.', 'informacao' if recuperou else 'atencao')

    falta = serie.get('curto_circuito_ativo')
    if falta:
        segundos = sum(max(0, tempos[i + 1] - tempos[i]) for i in range(min(len(falta), len(tempos) - 1)) if falta[i])
        adicionar('Duração do curto', f'Tempo ativo amostrado: {fmt(segundos, 6)} s = {fmt(segundos / 3600, 9)} h. Calculado pelos intervalos entre amostras, sem extrapolar a última.')
    return {'itens': itens, 'criterios': 'Leitura automática do ensaio, não laudo de conformidade. Referências de proximidade na amostra final: ±0,1 Hz da frequência nominal e ±0,01 pu de 1 pu; são critérios de leitura, não limites normativos. Energia estimada por integração retangular dos intervalos amostrados.'}
