import { useState } from 'react'

export default function TransientScenario({ layout, onRun }) {
  const types = new Set((layout.nodes || []).map(node => node.data?.componente?.tipo_codigo))
  const hasDiesel = types.has('gerador_diesel')
  const hasSolar = types.has('modulo_fv') && types.has('bateria')
  const hasBackup = hasDiesel && types.has('bateria')
  const [scenario, setScenario] = useState({ tipo: 'perda_fv', inicio_s: 2, duracao_s: 0.5, tempo_s: 6, passo_s: 0.01, strings_totais: 16, strings_perdidas: 4, carga_kw: 100, resistencia_falta_ohm: 0, partida_diesel_s: 2, rampa_diesel_s: 1, retorno_rede_s: 1, disponibilidade_fv_percent: 0 })
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const available = scenario.tipo === 'falha_rede' ? hasBackup : scenario.tipo === 'perda_fv' ? hasSolar : hasDiesel
  function field(key, label, min, max, step = 'any') {
    return <label>{label}<input type="number" value={scenario[key]} min={min} max={max} step={step} onChange={e => setScenario(s => ({ ...s, [key]: e.target.value }))} /></label>
  }
  function suggest() {
    const generator = layout.nodes.find(node => node.data?.componente?.tipo_codigo === 'gerador_diesel')?.data?.componente
    if (scenario.tipo === 'falha_rede' && hasBackup) {
      setScenario(s => ({ ...s, inicio_s: 2, duracao_s: 6, tempo_s: 12, passo_s: 0.01, partida_diesel_s: 2, rampa_diesel_s: 1, retorno_rede_s: 1, disponibilidade_fv_percent: 0, carga_kw: Math.round(Number(generator?.potencia_kw || 200) * 0.5) }))
      setError('Sugestão de ensaio noturno: FV em 0%. Revise carga e tempos de partida e transferência.')
      return
    }
    setScenario({ ...scenario, tipo: hasSolar ? 'perda_fv' : 'degrau_carga', inicio_s: 2, duracao_s: 0.5, tempo_s: 6, passo_s: 0.01, strings_totais: 16, strings_perdidas: 4, carga_kw: Math.round(Number(generator?.potencia_kw || 100) * 0.5), resistencia_falta_ohm: 0 })
    setError('Sugestão preenchida. Revise as quantidades de strings ou a carga antes de executar.')
  }
  async function run() {
    setBusy(true); setError('')
    try {
      if (Object.entries(scenario).some(([key, value]) => key !== 'tipo' && (value === '' || !Number.isFinite(Number(value))))) throw new Error('Preencha os campos numéricos.')
      await onRun(scenario)
    } catch (e) { setError(e.response?.data?.erro || e.message) }
    finally { setBusy(false) }
  }
  return <section className="transient-scenario">
    <h3>Cenários de falha — Transitório</h3>
    <p>Escolha um evento para observar a resposta e a recuperação. Modelo reduzido, não EMT trifásico detalhado.</p>
    <div className="transient-fields">
      <label>Evento<select value={scenario.tipo} onChange={e => { const tipo = e.target.value; setScenario(s => ({ ...s, tipo, ...(tipo === 'falha_rede' ? { duracao_s: 6, tempo_s: 12 } : {}) })) }}>
        <option value="perda_fv" disabled={!hasSolar}>Perda de strings FV (FV + BESS)</option>
        <option value="degrau_carga" disabled={!hasDiesel}>Degrau de carga (gerador isolado)</option>
        <option value="curto_3ph" disabled={!hasDiesel}>Curto trifásico (gerador isolado)</option>
        <option value="falha_rede" disabled={!hasBackup}>Falha da rede distribuidora (BESS + diesel)</option>
      </select></label>
      {field('inicio_s', 'Início do evento (s)', 0, 59)}
      {field('duracao_s', 'Duração do evento (s)', 0.02, 30)}
      {field('tempo_s', 'Duração do ensaio (s)', 0.1, 60)}
      {field('passo_s', 'Passo de simulação (s)', 0.001, 0.01)}
      {scenario.tipo === 'perda_fv' ? <>{field('strings_totais', 'Strings totais (informar)', 1, 10000, 1)}{field('strings_perdidas', 'Strings perdidas', 1, scenario.strings_totais, 1)}</> : null}
      {scenario.tipo === 'degrau_carga' ? field('carga_kw', 'Carga durante o evento (kW)', 0, 100000) : null}
      {scenario.tipo === 'curto_3ph' ? field('resistencia_falta_ohm', 'Resistência da falta (Ω)', 0, 100) : null}
      {scenario.tipo === 'falha_rede' ? <>
        {field('carga_kw', 'Carga do ensaio (kW)', 0.001, 100000)}
        {field('partida_diesel_s', 'Tempo de partida do diesel (s)', 0, 30)}
        {field('rampa_diesel_s', 'Rampa até potência nominal (s)', 0.05, 30)}
        {field('retorno_rede_s', 'Espera após retorno da rede (s)', 0, 30)}
        {field('disponibilidade_fv_percent', 'Disponibilidade FV (%) — 0: noite', 0, 100)}
      </> : null}
    </div>
    {scenario.tipo === 'falha_rede' ? <p>BESS em espera assume a carga durante a partida do diesel, respeitando potência e SOC. Após o retorno e a espera configurada, a rede reassume a carga por transferência ideal. Modelo de potência, sem cálculo de tensão, frequência ou sincronismo.</p> : scenario.tipo !== 'perda_fv' ? <p>Ensaio ilhado do gerador e carga. FV, BESS e distribuidora não participam deste ensaio.</p> : <p>A sugestão de strings é ilustrativa: informe a quantidade real do arranjo.</p>}
    {!available ? <p>Adicione os equipamentos necessários ou selecione um evento compatível.</p> : null}
    {error ? <p role="status">{error}</p> : null}
    <div className="result-json-buttons"><button type="button" className="secondary-btn" onClick={suggest} disabled={busy || (!hasSolar && !hasDiesel)}>Sugerir cenário</button><button type="button" onClick={run} disabled={busy || !available}>{busy ? 'Executando transitório...' : 'Executar transitório'}</button></div>
  </section>
}
