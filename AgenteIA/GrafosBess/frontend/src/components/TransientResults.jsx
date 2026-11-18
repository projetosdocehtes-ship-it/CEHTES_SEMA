const colors = ['#2563eb', '#d97706', '#16a34a', '#9333ea', '#dc2626']

function TimeChart({ title, unit, series, keys, event, milestones = [] }) {
  const times = series.tempo_s || []
  const valid = keys.filter(([key]) => series[key]?.some(Number.isFinite))
  if (!times.length || !valid.length) return null
  const values = valid.flatMap(([key]) => series[key].filter(Number.isFinite))
  const min = Math.min(...values), max = Math.max(...values)
  const margin = Math.max((max - min) * 0.08, Math.abs(max) * 0.01, 0.01)
  const low = min - margin, high = max + margin
  const start = times[0], end = times[times.length - 1]
  const x = t => 70 + (t - start) / (end - start || 1) * 800
  const y = v => 270 - (v - low) / (high - low) * 230
  return <figure className="power-flow-figure"><figcaption>{title} ({unit})</figcaption>
    <svg viewBox="0 0 920 320" role="img" aria-label={title} style={{ width: '100%', height: 'auto' }}>
      <rect x={x(event.inicio_s)} y="40" width={Math.max(0, x(Math.min(event.fim_s, end)) - x(event.inicio_s))} height="230" fill="#ffe4e6" />
      {milestones.filter(m => m.tempo_s >= start && m.tempo_s <= end).map((m, i) => <g key={i}><line x1={x(m.tempo_s)} x2={x(m.tempo_s)} y1="40" y2="270" stroke="#64748b" strokeDasharray="5 4"><title>{m.nome}: {m.tempo_s} s</title></line><text x={x(m.tempo_s) + 3} y={55 + i * 16} fontSize="11" fill="#475569">{i + 1}</text></g>)}
      {[0, 1, 2, 3, 4].map(i => { const v = low + (high - low) * i / 4; const t = start + (end - start) * i / 4; return <g key={i}><line x1="70" x2="870" y1={y(v)} y2={y(v)} stroke="#e2e8f0" /><text x="62" y={y(v) + 4} textAnchor="end" fontSize="12">{v.toFixed(2)}</text><text x={x(t)} y="296" textAnchor="middle" fontSize="12">{t.toFixed(2)} s</text></g> })}
      {valid.map(([key, label], index) => <path key={key} d={times.map((t, i) => Number.isFinite(series[key][i]) ? `${i === 0 || !Number.isFinite(series[key][i - 1]) ? 'M' : 'L'} ${x(t).toFixed(2)} ${y(series[key][i]).toFixed(2)}` : '').join(' ')} fill="none" stroke={colors[index % colors.length]} strokeWidth="2"><title>{label}</title></path>)}
      <text x="70" y="24" fontSize="13">Faixa rosa: período do evento</text>
    </svg>
    <div className="transient-legend">{valid.map(([key, label], i) => <span key={key} style={{ color: colors[i % colors.length] }}>● {label}</span>)}</div>
  </figure>
}

export default function TransientResults({ data }) {
  const series = data.resultado.serie_temporal
  const charts = [
    ['Potências', 'kW', [['pv_kw', 'FV'], ['carga_kw', 'Carga'], ['bess_kw', 'BESS'], ['rede_kw', 'Rede'], ['diesel_kw', 'Diesel'], ['potencia_eletrica_kw', 'Elétrica do gerador'], ['potencia_mecanica_kw', 'Mecânica do gerador']]],
    ['Tensão', 'pu', [['tensao_pcc_pu', 'PCC'], ['tensao_pu', 'Gerador']]],
    ['Frequência', 'Hz', [['frequencia_hz', 'Frequência']]],
    ['Corrente no PCC', series.corrente_pcc_a ? 'A' : 'kA', [[series.corrente_pcc_a ? 'corrente_pcc_a' : 'corrente_pcc_ka', 'PCC']]],
    ['Estado de carga da bateria', 'pu', [['soc', 'SOC']]],
    ['Carga não atendida e excedente', 'kW', [['deficit_kw', 'Carga não atendida'], ['curtailment_kw', 'Excedente não absorvido']]],
    ['Estado das fontes', '0: desligado / 1: ligado', [['rede_disponivel', 'Rede disponível'], ['rede_conectada', 'Rede conectada à carga'], ['diesel_conectado', 'Diesel conectado']]],
  ]
  return <section className="transient-results"><h3>Resultado do transitório</h3><p>{data.escopo}</p><p>Evento: {({ perda_fv: 'Perda de strings FV', degrau_carga: 'Degrau de carga', curto_3ph: 'Curto trifásico', falha_rede: 'Falha da rede distribuidora' })[data.evento.tipo]} · {data.evento.inicio_s} s a {data.evento.fim_s} s</p>
    {data.resultado.marcos ? <ol>{data.resultado.marcos.map((m, i) => <li key={i}>{m.nome}: {m.tempo_s.toLocaleString('pt-BR')} s</li>)}</ol> : null}
    <p>Modelo reduzido; as curvas representam o ensaio configurado.</p>
    {data.resultado.analise_automatica ? <section className="automatic-report" aria-label="Análise automática do relatório">
      <h3>Análise automática do relatório</h3>
      <div className="automatic-report-grid">{data.resultado.analise_automatica.itens.map((item, i) => <article key={i} className={`automatic-report-item ${item.nivel}`}><h4>{item.titulo}{item.nivel === 'atencao' ? ' — Atenção' : ''}</h4><p>{item.texto}</p></article>)}</div>
      <p className="muted">{data.resultado.analise_automatica.criterios}</p>
    </section> : <p className="muted">Execute novamente o ensaio para gerar a análise automática deste relatório.</p>}
    {data.resultado.avisos?.map((warning, i) => <p key={i}>{warning}</p>)}
    {charts.map(([title, unit, keys]) => <TimeChart key={title} title={title} unit={unit} keys={keys} series={series} event={data.evento} milestones={data.resultado.marcos} />)}
  </section>
}
