import { useEffect, useMemo, useState } from 'react'
import api from './api'
import Sidebar from './components/Sidebar'
import DiagramEditor from './components/DiagramEditor'
import Inspector from './components/Inspector'
import SimulationPanel from './components/SimulationPanel'

export default function App() {
  const [componentes, setComponentes] = useState([])
  const [projeto, setProjeto] = useState(null)
  const [layout, setLayout] = useState({ nodes: [], edges: [] })
  const [simulacao, setSimulacao] = useState(null)
  const [selectedNode, setSelectedNode] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function bootstrap() {
      setLoading(true)
      const projetosResp = await api.get('projetos/')
      let projetoAtual = projetosResp.data[0]

      if (!projetoAtual) {
        await api.post('projetos/', {
          nome: 'Projeto Exemplo',
          descricao: 'Projeto criado automaticamente'
        })
      }

      const projetosAtualizados = await api.get('projetos/')
      projetoAtual = projetosAtualizados.data[0]
      setProjeto(projetoAtual)

      const componentesResp = await api.get('componentes/')
      setComponentes(componentesResp.data)

      const diagramaResp = await api.get(`projetos/${projetoAtual.id}/diagrama/`)
      setLayout(diagramaResp.data.layout_json || { nodes: [], edges: [] })
      setSimulacao(diagramaResp.data.simulacao_json || null)
      setLoading(false)
    }

    bootstrap()
  }, [])

  const componentesAtivos = useMemo(
    () => componentes.filter((item) => item.ativo),
    [componentes]
  )

  async function salvarLayout(novoLayout) {
    setLayout(novoLayout)
    if (!projeto?.id) return

    const resp = await api.post(`projetos/${projeto.id}/diagrama/`, {
      layout_json: novoLayout,
    })
    setSimulacao(resp.data.simulacao_json)
  }

  async function simularAgora() {
    const resp = await api.post('simular/', { layout_json: layout })
    setSimulacao(resp.data)
  }

  function atualizarNode(nodeAtualizado) {
    const novosNodes = (layout.nodes || []).map((node) =>
      node.id === nodeAtualizado.id ? nodeAtualizado : node
    )
    const novoLayout = { ...layout, nodes: novosNodes }
    setSelectedNode(nodeAtualizado)
    salvarLayout(novoLayout)
  }

  function removerNode(nodeId) {
    const novosNodes = (layout.nodes || []).filter((node) => node.id !== nodeId)
    const novasEdges = (layout.edges || []).filter(
      (edge) => edge.source !== nodeId && edge.target !== nodeId
    )
    const novoLayout = { nodes: novosNodes, edges: novasEdges }
    setSelectedNode(null)
    salvarLayout(novoLayout)
  }

  if (loading) {
    return <div className="center-screen">Carregando aplicação...</div>
  }

  return (
    <div className="app-shell">
      <Sidebar componentes={componentesAtivos} />

      <div className="main-area">
        <header className="topbar">
          <div>
            <h1>Simulador de Usina Fotovoltaica com BESS</h1>
            <p>Arraste os componentes, conecte os blocos e rode a simulação.</p>
          </div>

          <div className="topbar-actions">
            <button className="primary-btn" onClick={simularAgora}>
              Simular
            </button>
          </div>
        </header>

        <DiagramEditor
          layout={layout}
          onChange={salvarLayout}
          onSelectNode={setSelectedNode}
        />

        <SimulationPanel simulacao={simulacao} />
      </div>

      <Inspector
        selectedNode={selectedNode}
        onUpdateNode={atualizarNode}
        onDeleteNode={removerNode}
      />
    </div>
  )
}
