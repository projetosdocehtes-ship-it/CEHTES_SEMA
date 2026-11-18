import { useMemo, useState } from 'react'

function onDragStart(event, componente) {
  event.dataTransfer.setData('application/simulador-componente', JSON.stringify(componente))
  event.dataTransfer.effectAllowed = 'move'
}

export default function Sidebar({ componentes }) {
  const grupos = useMemo(() => {
    const mapa = new Map()
    componentes.forEach((item) => {
      const chave = item.tipo_codigo || item.tipo_nome
      if (!mapa.has(chave)) mapa.set(chave, [])
      mapa.get(chave).push(item)
    })
    return Array.from(mapa.entries()).map(([codigo, itens]) => ({ codigo, itens }))
  }, [componentes])
  const [selecionados, setSelecionados] = useState({})

  return (
    <aside className="sidebar">
      <h2>Catálogo</h2>
      <p className="muted">Escolha um equipamento e arraste o card para o diagrama.</p>

      <div className="component-list">
        {grupos.map(({ codigo, itens }) => {
          const escolhido = itens.find((item) => String(item.id) === String(selecionados[codigo])) || itens[0]
          return (
            <div
              key={codigo}
              className="component-card"
              draggable
              onDragStart={(event) => onDragStart(event, escolhido)}
            >
              <strong>{escolhido.tipo_nome}</strong>
              {itens.length > 1 ? (
                <select
                  className="catalog-select"
                  value={escolhido.id}
                  onChange={(event) => setSelecionados((atual) => ({ ...atual, [codigo]: event.target.value }))}
                  onMouseDown={(event) => event.stopPropagation()}
                >
                  {itens.map((item) => (
                    <option key={item.id} value={item.id}>
                      {item.fabricante_nome} - {item.nome_modelo}
                    </option>
                  ))}
                </select>
              ) : null}
              <span>{escolhido.fabricante_nome}</span>
              <span>{escolhido.nome_modelo}</span>
              {escolhido.potencia_kw ? <span>{Number(escolhido.potencia_kw).toLocaleString('pt-BR')} kW</span> : null}
              {escolhido.energia_kwh ? <span>{Number(escolhido.energia_kwh).toLocaleString('pt-BR')} kWh</span> : null}
            </div>
          )
        })}
      </div>
    </aside>
  )
}
