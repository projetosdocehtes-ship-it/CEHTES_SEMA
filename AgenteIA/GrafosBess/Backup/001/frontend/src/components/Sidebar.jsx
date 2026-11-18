function onDragStart(event, componente) {
  event.dataTransfer.setData('application/simulador-componente', JSON.stringify(componente))
  event.dataTransfer.effectAllowed = 'move'
}

export default function Sidebar({ componentes }) {
  return (
    <aside className="sidebar">
      <h2>Catálogo</h2>
      <p className="muted">Arraste um item para o diagrama.</p>

      <div className="component-list">
        {componentes.map((item) => (
          <div
            key={item.id}
            className="component-card"
            draggable
            onDragStart={(event) => onDragStart(event, item)}
          >
            <strong>{item.tipo_nome}</strong>
            <span>{item.fabricante_nome}</span>
            <span>{item.nome_modelo}</span>
          </div>
        ))}
      </div>
    </aside>
  )
}
