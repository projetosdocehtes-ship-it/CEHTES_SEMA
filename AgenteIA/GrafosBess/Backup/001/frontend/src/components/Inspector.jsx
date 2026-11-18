import { useEffect, useState } from 'react'

export default function Inspector({ selectedNode, onUpdateNode, onDeleteNode }) {
  const [label, setLabel] = useState('')

  useEffect(() => {
    setLabel(selectedNode?.data?.label || '')
  }, [selectedNode])

  if (!selectedNode) {
    return (
      <aside className="inspector">
        <h2>Inspector</h2>
        <p className="muted">Selecione um componente no diagrama.</p>
      </aside>
    )
  }

  const componente = selectedNode.data?.componente || {}

  function salvarEdicao() {
    const atualizado = {
      ...selectedNode,
      data: {
        ...selectedNode.data,
        label,
      },
    }
    onUpdateNode(atualizado)
  }

  return (
    <aside className="inspector">
      <h2>Inspector</h2>

      <label className="field-label">Rótulo</label>
      <input
        className="field-input"
        value={label}
        onChange={(event) => setLabel(event.target.value)}
      />

      <div className="inspector-box">
        <p><strong>Tipo:</strong> {componente.tipo_nome}</p>
        <p><strong>Fabricante:</strong> {componente.fabricante_nome}</p>
        <p><strong>Modelo:</strong> {componente.nome_modelo}</p>
        <p><strong>Potência:</strong> {componente.potencia_kw || '-'} kW</p>
        <p><strong>Tensão:</strong> {componente.tensao_nominal_v || '-'} V</p>
        <p><strong>Corrente:</strong> {componente.corrente_nominal_a || '-'} A</p>
        <p><strong>Energia:</strong> {componente.energia_kwh || '-'} kWh</p>
        <p><strong>Modo:</strong> {componente.modo_operacao || '-'}</p>
      </div>

      <div className="inspector-actions">
        <button className="primary-btn" onClick={salvarEdicao}>
          Salvar
        </button>
        <button className="danger-btn" onClick={() => onDeleteNode(selectedNode.id)}>
          Excluir nó
        </button>
      </div>
    </aside>
  )
}
