import { useMemo } from 'react'

const NODE_WIDTH = 176
const NODE_HEIGHT = 82
const STEP_X = 218
const BRANCH_GAP = 126

const typeNames = {
  clima: 'Clima / ambiente', modulo_fv: 'Painel FV', string_box: 'String box',
  seccionadora_cc: 'Seccionadora CC', dps_cc: 'DPS CC', inversor: 'Inversor CC/CA',
  bateria: 'BESS', pcs: 'PCS bidirecional', gerador_diesel: 'Gerador', carga: 'Carga',
  barramento: 'Barramento AC', transformador: 'Transformador', protecao_mt: 'Proteção MT',
  poc: 'Ponto de conexão', disjuntor: 'Disjuntor',
}

const colors = {
  clima: '#2563eb', modulo_fv: '#7c3aed', string_box: '#2563eb',
  seccionadora_cc: '#0f766e', dps_cc: '#7c3aed', inversor: '#7c3aed',
  bateria: '#16a34a', pcs: '#0891b2', gerador_diesel: '#b45309',
  carga: '#334155', barramento: '#dc2626', transformador: '#9333ea',
  protecao_mt: '#7e22ce', poc: '#dc2626', disjuntor: '#475569',
}

const rightSideTypes = new Set(['transformador', 'protecao_mt', 'poc'])

function nodeType(node) {
  return node?.data?.componente?.tipo_codigo || ''
}

function shortText(value, limit = 24) {
  const text = String(value || '')
  return text.length > limit ? `${text.slice(0, limit - 1)}…` : text
}

function nodeDetails(node) {
  const component = node?.data?.componente || {}
  const type = nodeType(node)
  if (type === 'modulo_fv') return component.potencia_kw ? `${component.potencia_kw} kW/módulo` : component.fabricante_nome
  if (type === 'bateria') return component.energia_kwh ? `${component.energia_kwh} kWh` : component.fabricante_nome
  if (['inversor', 'pcs', 'gerador_diesel', 'carga'].includes(type)) return component.potencia_kw ? `${component.potencia_kw} kW` : component.fabricante_nome
  if (type === 'barramento') return component.tensao_nominal_v ? `${component.tensao_nominal_v} V` : component.fabricante_nome
  return component.fabricante_nome || ''
}

function branchPriority(nodes) {
  const types = new Set(nodes.map(nodeType))
  if (types.has('modulo_fv') || types.has('inversor') || types.has('clima')) return 10
  if (types.has('bateria') || types.has('pcs')) return 20
  if (types.has('gerador_diesel')) return 30
  if (types.has('carga')) return 40
  return 50
}

function edgeDomain(edge) {
  const sourceType = nodeType(edge.sourceNode)
  const targetType = nodeType(edge.targetNode)
  if (sourceType === 'clima' || targetType === 'clima') return 'context'
  if (['bateria', 'pcs'].includes(sourceType) || ['bateria', 'pcs'].includes(targetType)) return 'storage'
  if (['modulo_fv', 'string_box', 'seccionadora_cc', 'dps_cc'].includes(sourceType)) return 'dc'
  if (sourceType === 'carga' || targetType === 'carga') return 'load'
  return 'ac'
}

function buildSchematic(layout) {
  const nodes = (layout?.nodes || []).filter((node) => node?.id)
  const nodesById = new Map(nodes.map((node) => [node.id, node]))
  const invalidEdges = []
  const edges = []
  ;(layout?.edges || []).forEach((edge, index) => {
    const sourceNode = nodesById.get(edge?.source)
    const targetNode = nodesById.get(edge?.target)
    if (!sourceNode || !targetNode) invalidEdges.push(edge)
    else edges.push({ ...edge, id: edge.id || `ligacao-${index}`, sourceNode, targetNode })
  })

  const bus = nodes.find((node) => nodeType(node) === 'barramento') || null
  const nonBusNodes = nodes.filter((node) => node.id !== bus?.id)
  const adjacency = new Map(nonBusNodes.map((node) => [node.id, []]))
  edges.forEach((edge) => {
    if (edge.source !== bus?.id && edge.target !== bus?.id) {
      adjacency.get(edge.source)?.push(edge.target)
      adjacency.get(edge.target)?.push(edge.source)
    }
  })

  const components = []
  const visited = new Set()
  nonBusNodes.forEach((node) => {
    if (visited.has(node.id)) return
    const ids = []
    const queue = [node.id]
    visited.add(node.id)
    while (queue.length) {
      const id = queue.shift()
      ids.push(id)
      ;(adjacency.get(id) || []).forEach((neighbor) => {
        if (!visited.has(neighbor)) {
          visited.add(neighbor)
          queue.push(neighbor)
        }
      })
    }
    const items = ids.map((id) => nodesById.get(id))
    components.push({
      nodes: items,
      side: items.some((item) => rightSideTypes.has(nodeType(item))) ? 'right' : 'left',
      priority: branchPriority(items),
      originalY: Math.min(...items.map((item) => Number(item.position?.y || 0))),
    })
  })

  const leftBranches = components.filter((item) => item.side === 'left').sort((a, b) => a.priority - b.priority || a.originalY - b.originalY)
  const rightBranches = components.filter((item) => item.side === 'right').sort((a, b) => a.originalY - b.originalY)
  const connectedIds = new Set(edges.flatMap((edge) => [edge.source, edge.target]))
  const orphanNodes = nodes.filter((node) => node.id !== bus?.id && !connectedIds.has(node.id))

  const graphAdjacency = new Map(nodes.map((node) => [node.id, []]))
  edges.forEach((edge) => {
    graphAdjacency.get(edge.source)?.push(edge.target)
    graphAdjacency.get(edge.target)?.push(edge.source)
  })
  const distance = new Map()
  if (bus) {
    const queue = [bus.id]
    distance.set(bus.id, 0)
    while (queue.length) {
      const id = queue.shift()
      ;(graphAdjacency.get(id) || []).forEach((neighbor) => {
        if (!distance.has(neighbor)) {
          distance.set(neighbor, distance.get(id) + 1)
          queue.push(neighbor)
        }
      })
    }
  }

  const maxLeftDepth = Math.max(1, ...leftBranches.flatMap((branch) => branch.nodes.map((node) => distance.get(node.id) || 1)))
  const maxRightDepth = rightBranches.length
    ? Math.max(1, ...rightBranches.flatMap((branch) => branch.nodes.map((node) => distance.get(node.id) || 1)))
    : 0
  const branchCount = Math.max(leftBranches.length, rightBranches.length, 3)
  const height = Math.max(590, 100 + branchCount * BRANCH_GAP)
  const busX = 96 + maxLeftDepth * STEP_X + NODE_WIDTH
  const rightExtent = maxRightDepth ? maxRightDepth * STEP_X + NODE_WIDTH + 250 : 250
  const width = Math.max(1180, busX + rightExtent)
  const busTop = 60
  const busBottom = height - 60
  const positions = new Map()

  function positionBranches(branches, side) {
    branches.forEach((branch, branchIndex) => {
      const centerY = 92 + branchIndex * BRANCH_GAP
      const byDepth = new Map()
      branch.nodes.forEach((node) => {
        const depth = distance.get(node.id) || 1
        if (!byDepth.has(depth)) byDepth.set(depth, [])
        byDepth.get(depth).push(node)
      })
      byDepth.forEach((items, depth) => {
        items.sort((a, b) => (a.position?.y || 0) - (b.position?.y || 0))
        items.forEach((node, index) => {
          const rowOffset = (index - (items.length - 1) / 2) * (NODE_HEIGHT + 16)
          const x = side === 'left'
            ? busX - depth * STEP_X - NODE_WIDTH
            : busX + depth * STEP_X
          positions.set(node.id, { x, y: centerY - NODE_HEIGHT / 2 + rowOffset })
        })
      })
    })
  }

  positionBranches(leftBranches, 'left')
  positionBranches(rightBranches, 'right')
  if (bus) positions.set(bus.id, { x: busX, y: height / 2 })

  return { nodes, edges, bus, positions, width, height, busX, busTop, busBottom, invalidEdges, orphanNodes, rightBranches }
}

function loadKind(component) {
  const description = String(component.dados_modelo?.tipo_carga || component.tipo_carga || '').toLowerCase()
  if (/\bzip\b/.test(description)) return 'ZIP'
  if (description.includes('capacitiv')) return 'Capacitiva'
  if (description.includes('indutiv')) return 'Indutiva'
  if (description.includes('resistiv')) return 'Resistiva'
  return 'ZIP'
}

function ElectricalGlyph({ type, x, y, color, component = {} }) {
  const cx = x + 35
  const cy = y + 37
  const common = { fill: 'none', stroke: color, strokeWidth: 2.4, strokeLinecap: 'round', strokeLinejoin: 'round' }

  if (type === 'modulo_fv') return <g {...common}><rect x={x + 9} y={y + 15} width="51" height="40" rx="2" /><line x1={x + 26} y1={y + 15} x2={x + 26} y2={y + 55} /><line x1={x + 43} y1={y + 15} x2={x + 43} y2={y + 55} /><line x1={x + 9} y1={y + 35} x2={x + 60} y2={y + 35} /><line x1={x + 17} y1={y + 62} x2={x + 52} y2={y + 62} /></g>
  if (type === 'inversor') return (
    <g {...common}>
      <rect x={x + 8} y={y + 10} width="55" height="55" rx="4" />
      <line x1={x + 8} y1={y + 65} x2={x + 63} y2={y + 10} />
      <g aria-label="Corrente contínua">
        <line x1={x + 17} y1={y + 23} x2={x + 33} y2={y + 23} />
        <line x1={x + 17} y1={y + 29} x2={x + 33} y2={y + 29} strokeDasharray="3 3.5" />
      </g>
      <path aria-label="Corrente alternada" d={`M ${x + 36} ${y + 49} c 3 -8 7 -8 10 0 s 7 8 10 0`} />
    </g>
  )
  if (type === 'bateria') return <g {...common}><rect x={x + 8} y={y + 16} width="54" height="43" rx="4" /><line x1={x + 25} y1={y + 25} x2={x + 25} y2={y + 49} /><line x1={x + 31} y1={y + 30} x2={x + 31} y2={y + 44} /><line x1={x + 45} y1={y + 25} x2={x + 45} y2={y + 49} /><line x1={x + 51} y1={y + 30} x2={x + 51} y2={y + 44} /></g>
  if (type === 'pcs') return <g {...common}><rect x={x + 8} y={y + 13} width="55" height="49" rx="5" /><path d={`M ${x + 17} ${y + 31} H ${x + 51} l -7 -6 m 7 6 l -7 6 M ${x + 54} ${y + 46} H ${x + 20} l 7 -6 m -7 6 l 7 6`} /></g>
  if (type === 'gerador_diesel') return <g {...common}><circle cx={cx} cy={cy} r="27" /><text x={cx} y={cy} textAnchor="middle" dominantBaseline="central" className="visio-glyph-letter">G</text><path d={`M ${cx - 12} ${cy + 16} c 4 -6 8 -6 12 0 s 8 6 12 0`} /></g>
  if (type === 'carga') {
    const kind = loadKind(component)
    return <g {...common} aria-label={`Carga ${kind}`}>
      <title>{kind === 'ZIP' ? 'Carga ZIP: impedância, corrente e potência constantes' : `Carga ${kind.toLowerCase()}`}</title>
      {kind === 'Capacitiva' ? <path d={`M ${x + 9} ${cy} H ${cx - 5} M ${cx - 5} ${cy - 16} V ${cy + 16} M ${cx + 5} ${cy - 16} V ${cy + 16} M ${cx + 5} ${cy} H ${x + 61}`} />
        : kind === 'Indutiva' ? <path d={`M ${x + 9} ${cy} H ${x + 15} c 0 -16 10 -16 10 0 c 0 -16 10 -16 10 0 c 0 -16 10 -16 10 0 c 0 -16 10 -16 10 0 H ${x + 61}`} />
          : kind === 'Resistiva' ? <path d={`M ${x + 9} ${cy} H ${x + 17} l 5 -10 l 8 20 l 8 -20 l 8 20 l 6 -10 H ${x + 61}`} />
            : <><path d={`M ${cx} ${y + 10} V ${y + 22} M ${x + 13} ${y + 22} H ${x + 57} L ${cx} ${y + 63} Z`} /><text x={cx} y={cy} textAnchor="middle" dominantBaseline="central" fill={color} stroke="none" fontSize="12" fontWeight="700">ZIP</text></>}
    </g>
  }
  if (type === 'transformador') return <g {...common}><circle cx={x + 27} cy={cy} r="20" /><circle cx={x + 45} cy={cy} r="20" /></g>
  if (['protecao_mt', 'disjuntor', 'seccionadora_cc'].includes(type)) return <g {...common}><line x1={x + 9} y1={cy} x2={x + 25} y2={cy} /><circle cx={x + 25} cy={cy} r="3" fill={color} /><circle cx={x + 53} cy={cy} r="3" fill={color} /><line x1={x + 27} y1={cy - 2} x2={x + 49} y2={cy - 17} /><line x1={x + 56} y1={cy} x2={x + 64} y2={cy} /></g>
  if (type === 'clima') return <g {...common}><circle cx={cx} cy={cy} r="16" /><line x1={cx} y1={y + 8} x2={cx} y2={y + 15} /><line x1={cx} y1={y + 59} x2={cx} y2={y + 66} /><line x1={x + 6} y1={cy} x2={x + 13} y2={cy} /><line x1={x + 57} y1={cy} x2={x + 64} y2={cy} /></g>
  if (type === 'dps_cc') return <g {...common}><rect x={x + 17} y={y + 13} width="36" height="49" /><path d={`M ${x + 25} ${y + 48} l 19 -23 m -13 0 h 13 v 13`} /></g>
  if (type === 'string_box') return <g {...common}><rect x={x + 10} y={y + 12} width="52" height="51" rx="3" /><circle cx={x + 24} cy={y + 28} r="4" /><circle cx={x + 48} cy={y + 28} r="4" /><path d={`M ${x + 24} ${y + 32} V ${y + 48} H ${x + 48} V ${y + 32} M ${x + 36} ${y + 48} V ${y + 58}`} /></g>
  if (type === 'poc') return <g {...common}><circle cx={cx} cy={cy} r="25" /><path d={`M ${cx - 13} ${cy} H ${cx + 13} M ${cx} ${cy - 13} V ${cy + 13}`} /></g>
  return <g {...common}><rect x={x + 10} y={y + 13} width="52" height="49" rx="3" /><path d={`M ${x + 20} ${cy} H ${x + 52}`} /></g>
}

function EquipmentSymbol({ node, position, orphan }) {
  const type = nodeType(node)
  const component = node?.data?.componente || {}
  const title = type === 'carga' ? `Carga ${loadKind(component)}` : typeNames[type] || component.tipo_nome || 'Equipamento'
  const model = component.nome_modelo || node?.data?.label?.split(' - ').slice(1).join(' - ') || ''
  const color = colors[type] || '#334155'
  const { x, y } = position
  const textClipId = `visio-text-${String(node.id).replace(/[^a-zA-Z0-9_-]/g, '-')}`
  return (
    <g className={`visio-equipment ${orphan ? 'visio-equipment-orphan' : ''}`}>
      <title>{node?.data?.label || title}{orphan ? ' (sem ligação)' : ''}</title>
      <defs><clipPath id={textClipId}><rect x={x + 80} y={y + 8} width={NODE_WIDTH - 87} height={NODE_HEIGHT - 16} /></clipPath></defs>
      <rect x={x} y={y} width={NODE_WIDTH} height={NODE_HEIGHT} rx="8" className="visio-symbol-bg" />
      <ElectricalGlyph type={type} x={x + 2} y={y + 3} color={color} component={component} />
      <line x1={x + 73} y1={y + 10} x2={x + 73} y2={y + NODE_HEIGHT - 10} className="visio-symbol-divider" />
      <g clipPath={`url(#${textClipId})`}>
        <text x={x + 83} y={y + 24} className="unifilar-card-title">{shortText(title, 14)}</text>
        <text x={x + 83} y={y + 45} className="unifilar-card-model">{shortText(model, 13)}</text>
        <text x={x + 83} y={y + 64} className="unifilar-card-detail">{shortText(nodeDetails(node), 14)}</text>
      </g>
      <circle cx={x} cy={y + NODE_HEIGHT / 2} r="4" className="unifilar-terminal" />
      <circle cx={x + NODE_WIDTH} cy={y + NODE_HEIGHT / 2} r="4" className="unifilar-terminal" />
      {orphan ? <text x={x + NODE_WIDTH - 8} y={y + 17} textAnchor="end" className="unifilar-orphan-mark">!</text> : null}
    </g>
  )
}

function connectionPath(edge, schematic) {
  const source = schematic.positions.get(edge.source)
  const target = schematic.positions.get(edge.target)
  if (!source || !target) return ''
  const sourceIsBus = edge.source === schematic.bus?.id
  const targetIsBus = edge.target === schematic.bus?.id
  if (sourceIsBus || targetIsBus) {
    const nodePosition = sourceIsBus ? target : source
    const nodeCenterY = nodePosition.y + NODE_HEIGHT / 2
    const nodeCenterX = nodePosition.x < schematic.busX ? nodePosition.x + NODE_WIDTH : nodePosition.x
    return sourceIsBus
      ? `M ${schematic.busX} ${nodeCenterY} H ${nodeCenterX}`
      : `M ${nodeCenterX} ${nodeCenterY} H ${schematic.busX}`
  }
  const sourceCenterX = source.x + NODE_WIDTH / 2
  const targetCenterX = target.x + NODE_WIDTH / 2
  const sourceX = targetCenterX >= sourceCenterX ? source.x + NODE_WIDTH : source.x
  const targetX = targetCenterX >= sourceCenterX ? target.x : target.x + NODE_WIDTH
  const sourceY = source.y + NODE_HEIGHT / 2
  const targetY = target.y + NODE_HEIGHT / 2
  const midX = sourceX + (targetX - sourceX) / 2
  return `M ${sourceX} ${sourceY} H ${midX} V ${targetY} H ${targetX}`
}

function GridSymbol({ x, y }) {
  return <g className="visio-grid-symbol" aria-label="Rede da distribuidora"><title>Rede elétrica da distribuidora</title><rect x={x} y={y} width="154" height="96" rx="8" className="visio-symbol-bg grid" /><path d={`M ${x + 20} ${y + 74} L ${x + 38} ${y + 18} L ${x + 56} ${y + 74} M ${x + 17} ${y + 34} H ${x + 59} M ${x + 13} ${y + 47} H ${x + 63} M ${x + 29} ${y + 47} L ${x + 50} ${y + 61} H ${x + 25} L ${x + 45} ${y + 47} M ${x + 17} ${y + 34} V ${y + 40} M ${x + 59} ${y + 34} V ${y + 40} M ${x + 13} ${y + 47} V ${y + 53} M ${x + 63} ${y + 47} V ${y + 53}`} /><text x={x + 107} y={y + 41} textAnchor="middle" className="unifilar-grid-title">REDE</text><text x={x + 107} y={y + 60} textAnchor="middle" className="unifilar-grid-detail">Distribuidora</text></g>
}

export default function SingleLineDiagram({ layout, connectedToGrid = true }) {
  const schematic = useMemo(() => buildSchematic(layout), [layout])
  if (!schematic.nodes.length) return <section className="unifilar-panel"><div className="unifilar-heading"><div><h3>Diagrama unifilar</h3><p>Visualização elétrica automática dos blocos.</p></div></div><p className="muted">Adicione ou gere blocos para visualizar o diagrama unifilar.</p></section>

  const gridX = schematic.width - 190
  const gridY = schematic.height / 2 - 48
  const rightNodes = schematic.rightBranches.flatMap((branch) => branch.nodes)
  const gridAnchor = rightNodes.sort((a, b) => (schematic.positions.get(b.id)?.x || 0) - (schematic.positions.get(a.id)?.x || 0))[0]
  const gridAnchorPosition = gridAnchor ? schematic.positions.get(gridAnchor.id) : null
  const gridStartX = gridAnchorPosition ? gridAnchorPosition.x + NODE_WIDTH : schematic.busX
  const gridStartY = gridAnchorPosition ? gridAnchorPosition.y + NODE_HEIGHT / 2 : schematic.height / 2

  return (
    <section className="unifilar-panel">
      <div className="unifilar-heading">
        <div><h3>Diagrama unifilar</h3><p>Modelo elétrico no estilo Visio, sincronizado com as ligações dos blocos.</p></div>
        <div className="unifilar-topology-summary"><span>{schematic.nodes.length} equipamentos</span><span>{schematic.edges.length} ligações</span><span className={connectedToGrid ? 'grid-connected' : 'grid-isolated'}>{connectedToGrid ? 'Conectado à rede' : 'Sistema isolado'}</span></div>
      </div>
      {(!schematic.bus || schematic.orphanNodes.length || schematic.invalidEdges.length) ? <div className="unifilar-warning">{!schematic.bus ? 'Adicione um barramento para organizar as derivações. ' : ''}{schematic.orphanNodes.length ? `${schematic.orphanNodes.length} bloco(s) sem ligação. ` : ''}{schematic.invalidEdges.length ? `${schematic.invalidEdges.length} ligação(ões) inválidas.` : ''}</div> : null}
      <div className="unifilar-scroll visio-unifilar-scroll">
        <svg className="unifilar-svg" width={schematic.width} height={schematic.height} viewBox={`0 0 ${schematic.width} ${schematic.height}`} role="img" aria-label="Diagrama unifilar com símbolos elétricos">
          <defs>
            {['ac', 'dc', 'storage', 'load', 'context'].map((domain) => <marker key={domain} id={`visio-arrow-${domain}`} viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" className={`marker-${domain}`} /></marker>)}
          </defs>
          {schematic.edges.map((edge, index) => { const domain = edgeDomain(edge); return <path key={`${edge.id}-${index}`} d={connectionPath(edge, schematic)} className={`unifilar-topology-edge edge-${domain}`} markerEnd={`url(#visio-arrow-${domain})`}><title>{edge.sourceNode.data?.label || edge.source} → {edge.targetNode.data?.label || edge.target}</title></path> })}
          {schematic.bus ? <g><line x1={schematic.busX} y1={schematic.busTop} x2={schematic.busX} y2={schematic.busBottom} className="unifilar-bus-shadow" /><line x1={schematic.busX} y1={schematic.busTop} x2={schematic.busX} y2={schematic.busBottom} className="unifilar-bus" /><rect x={schematic.busX - 82} y="10" width="164" height="42" rx="13" className="unifilar-bus-label-bg" /><text x={schematic.busX} y="29" textAnchor="middle" className="unifilar-bus-label">BARRAMENTO AC</text><text x={schematic.busX} y="44" textAnchor="middle" className="unifilar-bus-detail">{shortText(nodeDetails(schematic.bus), 18)}</text></g> : null}
          {connectedToGrid && schematic.bus ? <g><path d={`M ${gridStartX} ${gridStartY} H ${gridStartX + 34} V ${schematic.height / 2} H ${gridX}`} className="unifilar-project-grid-edge" markerEnd="url(#visio-arrow-ac)" /><GridSymbol x={gridX} y={gridY} /></g> : <text x={schematic.busX + 55} y={schematic.height / 2} className="unifilar-offgrid">SISTEMA ISOLADO</text>}
          {schematic.nodes.filter((node) => node.id !== schematic.bus?.id).map((node) => <EquipmentSymbol key={node.id} node={node} position={schematic.positions.get(node.id)} orphan={schematic.orphanNodes.some((orphan) => orphan.id === node.id)} />)}
        </svg>
      </div>
      <div className="unifilar-legend"><span><i className="legend-dc" />CC</span><span><i className="legend-ac" />CA</span><span><i className="legend-storage" />BESS/PCS</span><span><i className="legend-load" />Carga</span><span><i className="legend-context" />Contexto</span></div>
    </section>
  )
}
