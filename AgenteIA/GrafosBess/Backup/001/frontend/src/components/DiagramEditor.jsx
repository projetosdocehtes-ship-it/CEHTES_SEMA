import { useCallback, useEffect, useMemo, useRef } from 'react'
import {
  addEdge,
  Background,
  Controls,
  MiniMap,
  ReactFlow,
  applyNodeChanges,
  applyEdgeChanges,
  useReactFlow,
  ReactFlowProvider,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'

function tipoCor(tipo) {
  const mapa = {
    modulo_fv: '#166534',
    string_box: '#1d4ed8',
    seccionadora_cc: '#0f766e',
    dps_cc: '#7c3aed',
    inversor: '#0ea5e9',
    barramento: '#334155',
    bateria: '#15803d',
    pcs: '#0369a1',
    disjuntor: '#6b7280',
    transformador: '#b45309',
    protecao_mt: '#9333ea',
    poc: '#dc2626',
  }
  return mapa[tipo] || '#374151'
}

function buildNode(componente, position) {
  const tipo = componente.tipo_codigo
  return {
    id: `${tipo}_${Date.now()}_${Math.floor(Math.random() * 100000)}`,
    position,
    data: {
      label: `${componente.tipo_nome} - ${componente.nome_modelo}`,
      componente,
    },
    style: {
      border: `2px solid ${tipoCor(tipo)}`,
      borderRadius: 12,
      padding: 10,
      width: 220,
      background: '#ffffff',
      boxShadow: '0 4px 16px rgba(0,0,0,0.08)',
    },
  }
}

function FlowCanvas({ layout, onChange, onSelectNode }) {
  const wrapperRef = useRef(null)
  const { screenToFlowPosition } = useReactFlow()

  const nodes = useMemo(() => layout.nodes || [], [layout.nodes])
  const edges = useMemo(() => layout.edges || [], [layout.edges])

  useEffect(() => {}, [nodes, edges])

  const onNodesChange = useCallback(
    (changes) => {
      const nextNodes = applyNodeChanges(changes, nodes)
      onChange({ nodes: nextNodes, edges })
    },
    [nodes, edges, onChange]
  )

  const onEdgesChange = useCallback(
    (changes) => {
      const nextEdges = applyEdgeChanges(changes, edges)
      onChange({ nodes, edges: nextEdges })
    },
    [nodes, edges, onChange]
  )

  const onConnect = useCallback(
    (params) => {
      const nextEdges = addEdge(
        {
          ...params,
          animated: true,
          style: { strokeWidth: 2 },
        },
        edges
      )
      onChange({ nodes, edges: nextEdges })
    },
    [nodes, edges, onChange]
  )

  const onDragOver = useCallback((event) => {
    event.preventDefault()
    event.dataTransfer.dropEffect = 'move'
  }, [])

  const onDrop = useCallback(
    (event) => {
      event.preventDefault()
      const raw = event.dataTransfer.getData('application/simulador-componente')
      if (!raw) return

      const componente = JSON.parse(raw)
      const position = screenToFlowPosition({
        x: event.clientX,
        y: event.clientY,
      })

      const newNode = buildNode(componente, position)
      onChange({
        nodes: [...nodes, newNode],
        edges,
      })
    },
    [screenToFlowPosition, nodes, edges, onChange]
  )

  return (
    <div className="diagram-editor" ref={wrapperRef}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        onNodeClick={(_, node) => onSelectNode(node)}
        onPaneClick={() => onSelectNode(null)}
        onDrop={onDrop}
        onDragOver={onDragOver}
        fitView
      >
        <MiniMap />
        <Controls />
        <Background gap={20} size={1} />
      </ReactFlow>
    </div>
  )
}

export default function DiagramEditor(props) {
  return (
    <ReactFlowProvider>
      <FlowCanvas {...props} />
    </ReactFlowProvider>
  )
}
