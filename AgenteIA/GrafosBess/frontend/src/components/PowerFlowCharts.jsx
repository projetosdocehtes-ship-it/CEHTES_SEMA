function ResultChart({ title, values, names, unit, reference, prefix }) {
  const entries = Object.entries(values || {}).filter(([, value]) => typeof value === 'number' && Number.isFinite(value))
  if (!entries.length) return <div className="alerts-box"><h4>{title}</h4><p>Sem valores disponíveis para este gráfico.</p></div>
  const width = 720
  const height = 60 + entries.length * 42
  const left = 220
  const plotWidth = 380
  const max = Math.max(reference, ...entries.map(([, value]) => Math.abs(value))) * 1.12
  const referenceX = left + reference / max * plotWidth
  return <figure className="power-flow-figure">
    <figcaption>{title}</figcaption>
    <div className="power-flow-chart-scroll">
      <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label={title}>
        <line x1={referenceX} x2={referenceX} y1="28" y2={height - 12} stroke="#94a3b8" strokeDasharray="4 4" />
        <text x={referenceX} y="18" textAnchor="middle" fontSize="12" fill="#475569">Referência: {reference} {unit}</text>
        {entries.map(([id, value], index) => {
          const label = names?.[id] || `${prefix} ${id}`
          const y = 38 + index * 42
          const formatted = value.toLocaleString('pt-BR', { maximumFractionDigits: unit === 'pu' ? 4 : 2 })
          return <g key={id}><title>{label}: {formatted} {unit}</title>
            <text x={left - 12} y={y + 18} textAnchor="end" fontSize="12" fill="#334155">{label.length > 28 ? `${label.slice(0, 27)}…` : label}</text>
            <rect x={left} y={y} width={Math.abs(value) / max * plotWidth} height="26" rx="4" fill={unit === '%' && value > 100 ? '#dc2626' : '#0f766e'} />
            <text x={left + Math.abs(value) / max * plotWidth + 8} y={y + 18} fontSize="12" fill="#334155">{formatted} {unit}</text>
          </g>
        })}
      </svg>
    </div>
    {entries.length < Object.keys(values || {}).length ? <p className="muted">Elementos sem resultado numérico foram omitidos.</p> : null}
  </figure>
}

export default function PowerFlowCharts({ resultado }) {
  if (!resultado) return <p className="muted">O motor não retornou dados para os gráficos.</p>
  return <div>
    <p><strong>Convergência:</strong> {resultado.convergiu === true ? 'Convergiu' : resultado.convergiu === false ? 'Não convergiu' : 'Não informada'}</p>
    <ResultChart title="Tensão por barramento" values={resultado.tensoes_pu} names={resultado.nomes_barras} unit="pu" reference={1} prefix="Barra" />
    <ResultChart title="Carregamento das linhas" values={resultado.carregamento_linhas_percentual} names={resultado.nomes_linhas} unit="%" reference={100} prefix="Linha" />
  </div>
}
