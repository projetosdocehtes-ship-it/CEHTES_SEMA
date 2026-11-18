import { useState } from 'react'
import api from '../api'
import PowerFlowCharts from './PowerFlowCharts'
import TransientResults from './TransientResults'

function JsonActions({ value, title, filename, isInput = false }) {
  const [opened, setOpened] = useState(false)
  const [draft, setDraft] = useState('')
  const [error, setError] = useState('')

  function validatedJson() {
    try {
      const formatted = JSON.stringify(JSON.parse(draft), null, 2)
      setError('')
      return formatted
    } catch {
      setError('JSON inválido. Revise a sintaxe antes de baixar ou imprimir.')
      return null
    }
  }

  function download() {
    const content = validatedJson()
    if (content === null) return
    const url = URL.createObjectURL(new Blob([content], { type: 'application/json' }))
    const link = document.createElement('a')
    link.href = url
    link.download = filename
    link.click()
    setTimeout(() => URL.revokeObjectURL(url), 1000)
  }

  function print() {
    const content = validatedJson()
    if (content === null) return
    const page = window.open('', '_blank', 'width=900,height=700')
    if (!page) {
      setError('Permita a abertura da janela de impressão no navegador.')
      return
    }
    page.opener = null
    page.document.title = title
    const heading = page.document.createElement('h1')
    heading.textContent = title
    const pre = page.document.createElement('pre')
    pre.style.whiteSpace = 'pre-wrap'
    pre.style.overflowWrap = 'anywhere'
    pre.textContent = content
    page.document.body.append(heading, pre)
    page.focus()
    page.print()
  }

  return <div className="result-json-actions">
    <button type="button" className="secondary-btn" aria-expanded={opened} onClick={() => {
      if (!opened) { setDraft(JSON.stringify(value, null, 2)); setError('') }
      setOpened(!opened)
    }}>{opened ? 'Fechar JSON' : `Editar / imprimir JSON — ${title}`}</button>
    {opened ? <div className="alerts-box">
      <label className="result-json-label">{title}
        <textarea className="result-json-editor" value={draft} onChange={(event) => setDraft(event.target.value)} spellCheck={false} />
      </label>
      <p className="muted">A edição serve para baixar ou imprimir uma cópia.{isInput ? ' Para simular com novas entradas, baixe o JSON e importe na aba Simulador.' : ' Os resultados calculados permanecem os mesmos.'}</p>
      {error ? <p role="alert">{error}</p> : null}
      <div className="result-json-buttons">
        <button type="button" onClick={download}>Baixar JSON editado</button>
        <button type="button" className="secondary-btn" onClick={print}>Imprimir JSON</button>
      </div>
    </div> : null}
  </div>
}

function numero(valor, padrao = 0) {
  const convertido = Number(String(valor ?? '').replace(',', '.'))
  return Number.isFinite(convertido) ? convertido : padrao
}

function gerarCurvaCarga(modelo) {
  const carga = modelo?.cargas_info?.[0]
  if (!carga) return null
  const pontosInformados = Array.isArray(carga.curva_carga_pontos)
    ? carga.curva_carga_pontos.map((p, index) => ({ hora: numero(p.hora, index), valorKw: numero(p.valorKw ?? p.valor_kw ?? p.kw) })).filter((p) => p.valorKw > 0).slice(0, 24)
    : []
  if (pontosInformados.length) {
    return { nome: carga.nome_carga || 'Carga', tipo: carga.tipo_carga || 'Carga', curva: 'curva informada pelo usuário', pontos: pontosInformados, picoKw: Math.max(...pontosInformados.map((p) => p.valorKw)), mediaKw: pontosInformados.reduce((s, p) => s + p.valorKw, 0) / pontosInformados.length }
  }
  const demandaPonta = numero(carga.demanda_ponta_kw)
  const demandaFora = numero(carga.demanda_fora_ponta_kw)
  const base = Math.max(numero(carga.s_instalada), demandaPonta, demandaFora)
  if (!base) return null
  const tipo = String(carga.tipo_carga || carga.nome_carga || '').toLowerCase()
  const pontos = Array.from({ length: 24 }, (_, hora) => {
    let valor = hora >= 18 && hora < 21 ? demandaPonta || base : demandaFora || base
    if (tipo.includes('hospital')) valor *= hora >= 18 && hora < 21 ? 1 : 0.85
    else if (tipo.includes('escola')) valor *= hora >= 7 && hora <= 18 ? 1 : 0.2
    else if (hora < 6) valor *= 0.5
    else if (hora >= 22) valor *= 0.65
    return { hora, valorKw: Math.round(valor * 10) / 10 }
  })
  return { nome: carga.nome_carga || 'Carga', tipo: carga.tipo_carga || 'Carga', curva: carga.curva_carga || 'curva estimada', pontos, picoKw: Math.max(...pontos.map((p) => p.valorKw)), mediaKw: pontos.reduce((s, p) => s + p.valorKw, 0) / pontos.length }
}

function LoadCurveChart({ modelo }) {
  const curva = gerarCurvaCarga(modelo)
  if (!curva) return null
  const width = 760
  const height = 260
  const padding = { left: 52, right: 18, top: 20, bottom: 34 }
  const chartWidth = width - padding.left - padding.right
  const chartHeight = height - padding.top - padding.bottom
  const maxKw = Math.max(curva.picoKw, 1)
  const pontosSvg = curva.pontos.map((p, i) => `${(padding.left + (i / 23) * chartWidth).toFixed(1)},${(padding.top + chartHeight - (p.valorKw / maxKw) * chartHeight).toFixed(1)}`).join(' ')
  return (
    <div className="load-curve-box">
      <div className="load-curve-header">
        <div><h4>Curva de carga diária</h4><p>{curva.nome} · {curva.tipo} · {curva.curva}</p></div>
        <div className="load-curve-stats"><span>Pico: {curva.picoKw.toLocaleString('pt-BR')} kW</span><span>Média: {curva.mediaKw.toFixed(1).replace('.', ',')} kW</span></div>
      </div>
      <svg className="load-curve-chart" viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Curva de carga diária">
        {[0, 0.25, 0.5, 0.75, 1].map((percentual) => {
          const y = padding.top + chartHeight - percentual * chartHeight
          return <g key={percentual}><line x1={padding.left} x2={width - padding.right} y1={y} y2={y} /><text x={padding.left - 8} y={y + 4} textAnchor="end">{Math.round(maxKw * percentual)}</text></g>
        })}
        {[0, 6, 12, 18, 23].map((hora) => {
          const x = padding.left + (hora / 23) * chartWidth
          return <g key={hora}><line className="load-curve-tick" x1={x} x2={x} y1={padding.top} y2={padding.top + chartHeight} /><text x={x} y={height - 10} textAnchor="middle">{hora}h</text></g>
        })}
        <polyline points={pontosSvg} />
        {curva.pontos.map((p, i) => {
          const x = padding.left + (i / 23) * chartWidth
          const y = padding.top + chartHeight - (p.valorKw / maxKw) * chartHeight
          return <circle key={p.hora} cx={x} cy={y} r={i % 3 === 0 ? 3 : 2} />
        })}
      </svg>
    </div>
  )
}

export default function SimulationPanel({ simulacao, microrredes, transitorio, equipamentos }) {
  const relatorio = simulacao?.analise_financeira?.relatorio
  const graficoUrl = simulacao?.analise_financeira?.grafico?.url
  const modeloCarga = simulacao?.modelo_entradas || simulacao?.modelo_entradas_financeiro
  const tarifa = relatorio?.tarifa_aplicada
  const motorAnalise = simulacao?.motor_analise
  const moeda = (valor) => Number(valor || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })

  return (
    <section className="simulation-panel">
      <div className="simulation-heading"><h3>Resultado da simulação</h3></div>
      {!simulacao && !microrredes && !transitorio && !equipamentos ? <p className="muted">Nenhuma simulação executada.</p> : null}
      {equipamentos ? <div className="alerts-box">
        <h3>Equipamentos - Projeto</h3>
        <p>{equipamentos.nome_projeto} · Duração: {equipamentos.configuracao.Tempo_sim} s · {equipamentos.passos} passos</p>
        {equipamentos.avisos.map((aviso, i) => <p key={i}>{aviso}</p>)}
        {equipamentos.balanco ? <div className="alerts-box">
          <h4>Balanço de potência e déficit</h4>
          <p>{equipamentos.balanco.modelo}</p>
          {equipamentos.balanco.partida ? <p><strong>Sequência de partida</strong>: pré-carga concluída em {equipamentos.balanco.partida.fim_precarga_s == null ? 'não atingida' : `${(equipamentos.balanco.partida.fim_precarga_s * 1000).toFixed(2)} ms`}; contator {equipamentos.balanco.partida.fechamento_contator_s == null ? 'não fechou' : `fechado em ${(equipamentos.balanco.partida.fechamento_contator_s * 1000).toFixed(2)} ms`}. Espera programada: {(equipamentos.balanco.partida.tempo_carga_desconectada_s * 1000).toFixed(2)} ms; energia adiada: {equipamentos.balanco.partida.energia_adiada_espera_wh.toFixed(4)} Wh.</p> : null}
          {Object.entries(equipamentos.balanco.elos_cc || {}).map(([id,e]) => <p key={id}><strong>Elo CC {id}</strong>: reserva útil inicial {e.reserva_util_inicial_j.toFixed(2)} J; tensão mínima {e.tensao_min_v.toFixed(3)} V e final {e.tensao_final_v.toFixed(3)} V; energia inicial {e.energia_inicial_j.toFixed(3)} J e final {e.energia_final_j.toFixed(3)} J.</p>)}
          {['ensaio_com_partida', 'apos_conexao', 'apos_partida_50ms', 'queda_irradiancia', 'recuperacao'].filter(k => equipamentos.balanco[k]?.deficit_max_kw !== undefined).map(k => {
            const b = equipamentos.balanco[k]
            return <p key={k}><strong>{{ensaio_com_partida:'Ensaio completo',apos_conexao:'Após conectar a carga',apos_partida_50ms:'Após 50 ms',queda_irradiancia:'Durante a queda',recuperacao:'Recuperação'}[k]}</strong>: entregue {b.entregue_medio_kw.toFixed(3)} kW (média); déficit máximo {b.deficit_max_kw.toFixed(3)} kW; tempo com déficit acima de 1 W {(b.duracao_deficit_s * 1000).toFixed(3)} ms; energia não atendida {b.energia_nao_atendida_wh.toFixed(6)} Wh.</p>
          })}
        </div> : null}
        {equipamentos.resumo ? <div className="alerts-box">
          <h4>Verificação do ensaio</h4>
          <p>Valores de potência abaixo: média no último ciclo de 60 Hz. Bateria positiva fornece energia; negativa recebe carga.</p>
          {Object.entries(equipamentos.resumo).map(([id, r]) => <div key={id}>
            {r.p_demandada_w ? <p>{id}: demanda {(r.p_demandada_w.media_ultimo_ciclo / 1000).toFixed(2)} kW.</p> : null}
            {r.p_ativa_w ? <p>{id}: saída AC {(r.p_ativa_w.media_ultimo_ciclo / 1000).toFixed(2)} kW.</p> : null}
            {r.p_entregue_w ? <p>{id}: potência entregue à carga {(r.p_entregue_w.media_ultimo_ciclo / 1000).toFixed(2)} kW.</p> : null}
            {r.soc ? <p>{id}: potência {(r.p_dc_w.media_ultimo_ciclo / 1000).toFixed(2)} kW; SOC inicial {(r.soc.inicial * 100).toFixed(4)}%, final {(r.soc.final * 100).toFixed(4)}%.</p> : null}
            {r.protecoes?.map((p, i) => <p key={i}>Proteção {id}: {p.tipo}, atuação em {p.tempo_s.toFixed(4)} s.</p>)}
          </div>)}
        </div> : null}
        {equipamentos.urls.map((url, i) => <figure key={url}>
          <figcaption>{equipamentos.titulos?.[i] || `Gráfico ${i + 1}`}</figcaption>
          <a href={new URL(url, api.defaults.baseURL).href} target="_blank" rel="noopener noreferrer">
            <img src={new URL(url, api.defaults.baseURL).href} alt={equipamentos.titulos?.[i] || `Equipamentos: gráfico ${i + 1}`} style={{ width: '100%', height: 'auto' }} />
            <span>Abrir figura em tamanho original</span>
          </a>
        </figure>)}
        <JsonActions value={equipamentos} title="Relatório Equipamentos" filename="equipamentos.json" />
      </div> : null}
      {transitorio ? <><TransientResults data={transitorio} /><JsonActions value={transitorio} title="Ensaio transitório" filename="transitorio.json" /></> : null}
      {simulacao ? (
        <>
          {relatorio ? (
            <>
              <div className="analysis-source-line"><strong>Análise econômica</strong><span>{motorAnalise === 'prime-django/apps/AnaliseEconomica' ? 'Motor prime-django / AnaliseEconomica' : 'Estimativa local de contingência'}</span></div>
              <div className="simulation-grid">
                <div className="info-card"><span>Economia anual</span><strong>{moeda(relatorio.economia_anual)}</strong></div>
                <div className="info-card"><span>Redução de custos</span><strong>{Number(relatorio.percentual_reducao || 0).toFixed(2)}%</strong></div>
                <div className="info-card"><span>CAPEX</span><strong>{moeda(relatorio.capex?.capex_total)}</strong></div>
                <div className="info-card"><span>VPL</span><strong>{moeda(relatorio.vpl)}</strong></div>
                <div className="info-card"><span>Payback</span><strong>{relatorio.payback == null ? 'Não calculável' : `${relatorio.payback} anos`}</strong></div>
              </div>
              {tarifa ? <div className="alerts-box tariff-result"><h4>Enquadramento tarifário usado no cálculo</h4><p>Grupo {tarifa.grupo || '-'} {tarifa.modalidade || '-'} · {tarifa.status === 'aplicada' ? 'economia recalculada com as tarifas informadas.' : tarifa.observacao}</p>{tarifa.status === 'aplicada' ? <div className="simulation-grid"><div className="info-card"><span>Custo sem microrrede</span><strong>{moeda(tarifa.custo_base_anual)}</strong></div><div className="info-card"><span>Custo com microrrede</span><strong>{moeda(tarifa.custo_microrede_anual)}</strong></div><div className="info-card"><span>O&M estimado</span><strong>{moeda(tarifa.custo_operacional_estimado)}</strong></div></div> : null}</div> : null}
              {graficoUrl ? <div className="alerts-box"><h4>Gráfico da análise financeira</h4><a href={new URL(graficoUrl, api.defaults.baseURL).href} target="_blank" rel="noopener noreferrer"><img src={new URL(graficoUrl, api.defaults.baseURL).href} alt="Gráfico da análise financeira" style={{ maxWidth: '100%', height: 'auto' }} /><span>Abrir figura em tamanho original</span></a></div> : null}
              <LoadCurveChart modelo={modeloCarga} />
            </>
          ) : (
            <>
              <div className="simulation-grid">
                <div className="info-card"><span>Status</span><strong>{simulacao.status}</strong></div>
                <div className="info-card"><span>Nós</span><strong>{simulacao.resumo?.quantidade_nos ?? 0}</strong></div>
                <div className="info-card"><span>Ligações</span><strong>{simulacao.resumo?.quantidade_ligacoes ?? 0}</strong></div>
                <div className="info-card"><span>Potência total</span><strong>{simulacao.resumo?.potencia_total_kw ?? 0} kW</strong></div>
                <div className="info-card"><span>Energia total</span><strong>{simulacao.resumo?.energia_total_kwh ?? 0} kWh</strong></div>
              </div>
              <div className="alerts-box"><h4>Alertas</h4>{simulacao.alertas?.length ? <ul>{simulacao.alertas.map((a, i) => <li key={i}>{a}</li>)}</ul> : <p className="muted">Sem alertas.</p>}</div>
              <LoadCurveChart modelo={modeloCarga} />
            </>
          )}
          {modeloCarga ? <JsonActions value={modeloCarga} title="Entradas da simulação" filename="entradas-simulacao.json" isInput /> : null}
        </>
      ) : null}
      {microrredes ? (
        <div className="microrredes-result">
          <div className="microrredes-result-heading">
            <div>
              <h4>Fluxo de potência da microrrede</h4>
              <p>Executado pelo motor {microrredes.motor}.</p>
              <p>Tempo: {Number(microrredes.tempo_execucao_segundos || 0).toFixed(3)} s{microrredes.cache_utilizado ? ' · resultado reutilizado do cache' : ''}</p>
            </div>
            <span>{microrredes.cache_utilizado ? 'Cache' : 'Concluído'}</span>
          </div>
          <PowerFlowCharts resultado={microrredes.resultado} />
          <JsonActions value={microrredes.resultado} title="Resultado do fluxo de potência" filename="resultado-fluxo-potencia.json" />
        </div>
      ) : null}
    </section>
  )
}
