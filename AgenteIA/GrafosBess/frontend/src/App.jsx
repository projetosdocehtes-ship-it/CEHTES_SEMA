import { useEffect, useMemo, useRef, useState } from 'react'
import api from './api'
import Sidebar from './components/Sidebar'
import SingleLineDiagram from './components/SingleLineDiagram'
import Inspector from './components/Inspector'
import SimulationPanel from './components/SimulationPanel'
import TransientScenario from './components/TransientScenario'
import PopHelp from './components/PopHelp'

const perfilCarga = [
  {
    nome: 'Supermercado',
    descricao: 'Operação comercial com refrigeração.',
    prompt: 'Usina fotovoltaica com BESS para supermercado, conectado à rede e com gerador diesel de backup.',
    dados: { consumoKwh: '22000', demandaPontaKw: '150', demandaForaPontaKw: '120' },
    local: { tipo: 'Supermercado', porte: 'Médio', funcionamento: '06:00-22:00' },
  },
  {
    nome: 'Escola',
    descricao: 'Carga diurna e baixa à noite.',
    prompt: 'Usina fotovoltaica com BESS para escola, conectado à rede.',
    dados: { consumoKwh: '9000', demandaPontaKw: '60', demandaForaPontaKw: '85' },
    local: { tipo: 'Escola', porte: '500 alunos', funcionamento: '07:00-18:00' },
  },
  {
    nome: 'Hospital',
    descricao: 'Carga crítica 24h.',
    prompt: 'Usina fotovoltaica com BESS para hospital, conectado à rede e com gerador diesel de backup.',
    dados: { consumoKwh: '55000', demandaPontaKw: '380', demandaForaPontaKw: '420' },
    local: { tipo: 'Hospital', porte: '80 leitos', funcionamento: '24h' },
  },
  {
    nome: 'Indústria leve',
    descricao: 'Carga produtiva em horário comercial.',
    prompt: 'Usina fotovoltaica com BESS para indústria leve, conectado à rede.',
    dados: { consumoKwh: '35000', demandaPontaKw: '220', demandaForaPontaKw: '260' },
    local: { tipo: 'Indústria leve', porte: 'Médio', funcionamento: '07:00-19:00' },
  },
  {
    nome: 'Fazenda',
    descricao: 'Irrigação, bombeamento e apoio rural.',
    prompt: 'Usina fotovoltaica com BESS para fazenda, carga rural, parcialmente isolada.',
    dados: { consumoKwh: '12000', demandaPontaKw: '80', demandaForaPontaKw: '100' },
    local: { tipo: 'Fazenda', porte: 'Médio', funcionamento: '05:00-20:00' },
  },
  {
    nome: 'Comunidade isolada',
    descricao: 'Microrrede com autonomia.',
    prompt: 'Usina fotovoltaica off-grid com BESS para comunidade isolada e gerador diesel de backup.',
    dados: { consumoKwh: '9000', demandaPontaKw: '45', demandaForaPontaKw: '35' },
    local: { tipo: 'Comunidade isolada', porte: '80 famílias', funcionamento: '24h' },
  },
]

const exemploAssistenteIa =
  'Usina fotovoltaica com BESS em Brasília, carga comercial mercado, conectado à rede.\n' +
  'Consumo: 18000 kWh\n' +
  'Demanda ponta: 120 kW\n' +
  'Demanda fora ponta: 95 kW\n' +
  'Gerador existente: sim\n' +
  'Autonomia desejada: 2 horas\n' +
  'Carregar bateria: 10:00-16:00\n' +
  'Usar bateria: 18:00-21:00'

function numero(valor, padrao = 0) {
  const convertido = Number(String(valor ?? '').replace(',', '.'))
  return Number.isFinite(convertido) ? convertido : padrao
}

function extrairNumero(texto, regex, padrao = 0) {
  const match = texto.match(regex)
  return match ? numero(match[1], padrao) : padrao
}

function normalizarNomeProjeto(nome) {
  return String(nome || 'Projeto Simulador').replace(/^(Sugestao IA -\s*)+/i, 'Sugestao IA - ')
}

function quantidadePainelParaKwp(kwp, pmp = 610) {
  return Math.max(1, Math.round((kwp * 1000) / pmp))
}

function modeloEntradasParaLayout(modelo) {
  const nodes = []
  const edges = []
  const modelIdToNodeId = {}
  const add = (id, modelId, tipo, label, componente, x, y) => {
    nodes.push({
      id,
      position: { x, y },
      data: { label, componente: { tipo_codigo: tipo, tipo_nome: label.split(' - ')[0], nome_modelo: label.split(' - ').slice(1).join(' - '), ...componente } },
      style: estiloNode(tipo),
    })
    if (modelId) modelIdToNodeId[modelId] = id
  }

  const clima = modelo.Clima_Ambiente?.[0] || {}
  const paineis = modelo.painel_info?.length ? modelo.painel_info : [{}]
  const inversores = modelo.inversor_info?.length ? modelo.inversor_info : [{}]
  const baterias = modelo.bateria_info?.length ? modelo.bateria_info : [{}]
  const cargas = modelo.cargas_info?.length ? modelo.cargas_info : [{}]
  const barramentos = modelo.barramento_info?.length ? modelo.barramento_info : [{}]
  const geradores = modelo.geradordiesel_info || []

  add('clima_auto', clima.clima_id || 'Clima_Ambiente', 'clima', `Clima - ${clima.nome_cidade || 'Cidade'}`, { fabricante_nome: clima.pais || 'BR', dados_modelo: clima }, 40, 30)
  paineis.forEach((painel, index) => add(`pv_auto_${index + 1}`, painel.pv_id || `PV_${index + 1}`, 'modulo_fv', `Módulo FV ${index + 1} - ${painel.modelo_painel || 'Painel solar'}`, { fabricante_nome: painel.fabricante_painel, potencia_kw: numero(painel.Pmp) / 1000, dados_modelo: painel }, 270, 30 + index * 110))
  inversores.forEach((inversor, index) => add(`inv_auto_${index + 1}`, inversor.inv_id || `Inv_${index + 1}`, 'inversor', `Inversor FV ${index + 1} - ${inversor.modelo_inversor || 'Inversor'}`, { fabricante_nome: inversor.fabricante_inversor, potencia_kw: inversor.Out_Pmax, dados_modelo: inversor }, 510, 30 + index * 110))
  barramentos.forEach((bus, index) => add(`bus_auto_${index + 1}`, bus.bus_id || `Bus_ac_${index + 1}`, 'barramento', `Barramento BT - ${bus.bus_id || `Bus_ac_${index + 1}`}`, { fabricante_nome: bus.tipo || 'AC', tensao_nominal_v: bus.V_linha_nominal || 380, dados_modelo: bus }, 760, 130 + index * 110))
  cargas.forEach((carga, index) => add(`load_auto_${index + 1}`, carga.carga_id || `Load_${index + 1}`, 'carga', `Carga ${index + 1} - ${carga.nome_carga || 'Cliente'}`, { fabricante_nome: carga.tipo_carga, potencia_kw: carga.s_instalada, dados_modelo: carga }, 1010, 70 + index * 110))
  baterias.forEach((bateria, index) => {
    add(`batt_auto_${index + 1}`, bateria.bateria_id || `Batt_${index + 1}`, 'bateria', `Banco de Baterias ${index + 1} - ${bateria.modelo || 'BESS'}`, { fabricante_nome: bateria.fabricante, energia_kwh: bateria.capacidade_kwh, dados_modelo: bateria }, 270, 300 + index * 110)
  })
  geradores.forEach((diesel, index) => add(`diesel_auto_${index + 1}`, diesel.diesel_id || `Diesel_${index + 1}`, 'gerador_diesel', `Gerador Diesel ${index + 1} - ${diesel.modelo || 'Backup'}`, { fabricante_nome: diesel.fabricante, potencia_kw: diesel.potencia_nominal_kw, dados_modelo: diesel }, 760, 360 + index * 110))

  const addEdge = (source, target) => edges.push({ id: `${source}_${target}`, source, target, animated: true, style: { strokeWidth: 2 } })
  ;(modelo.grafo_conexoes || []).forEach((conexao) => {
    const [sourceModelId, targetModelId] = conexao.between || []
    const source = modelIdToNodeId[sourceModelId]
    const target = modelIdToNodeId[targetModelId]
    if (source && target) addEdge(source, target)
  })
  if (!edges.length) {
    if (modelIdToNodeId.Clima_Ambiente && modelIdToNodeId.PV_1) addEdge(modelIdToNodeId.Clima_Ambiente, modelIdToNodeId.PV_1)
    inversores.forEach((inversor, index) => {
      const invId = modelIdToNodeId[inversor.inv_id || `Inv_${index + 1}`]
      if (modelIdToNodeId.PV_1 && invId) addEdge(modelIdToNodeId.PV_1, invId)
      if (invId && modelIdToNodeId.Bus_ac_1) addEdge(invId, modelIdToNodeId.Bus_ac_1)
    })
    cargas.forEach((carga, index) => {
      const loadId = modelIdToNodeId[carga.carga_id || `Load_${index + 1}`]
      if (modelIdToNodeId.Bus_ac_1 && loadId) addEdge(modelIdToNodeId.Bus_ac_1, loadId)
    })
  }
  return { nodes, edges }
}

function estiloNode(tipoCodigo) {
  const colors = {
    clima: '#2563eb',
    modulo_fv: '#166534',
    inversor: '#0ea5e9',
    barramento: '#334155',
    bateria: '#15803d',
    pcs: '#0369a1',
    carga: '#ea580c',
    gerador_diesel: '#92400e',
  }
  const color = colors[tipoCodigo] || '#374151'
  return { border: `2px solid ${color}`, borderRadius: 12, padding: 10, width: 220, background: '#ffffff', boxShadow: '0 4px 16px rgba(0,0,0,0.08)' }
}

function gerarModeloPorTexto(texto, dadosCarga, perguntasIa, perfilLocal) {
  const cidade = texto.match(/(?:em|cidade)\s+([A-Za-zÀ-ÿ\s]+?)(?:,|\.|\n|$)/i)?.[1]?.trim() || 'Goiania'
  const kwp = extrairNumero(texto, /(\d+(?:[,.]\d+)?)\s*kWp/i, 324)
  const bateriaKwh = extrairNumero(texto, /bateria\s+(\d+(?:[,.]\d+)?)\s*kWh/i, numero(perguntasIa.autonomiaHoras) * Math.max(numero(dadosCarga.demandaPontaKw), numero(dadosCarga.demandaForaPontaKw), 250) || 500)
  const consumo = numero(dadosCarga.consumoKwh) || extrairNumero(texto, /consumo:\s*(\d+(?:[,.]\d+)?)/i, 18000)
  const demandaPonta = numero(dadosCarga.demandaPontaKw) || extrairNumero(texto, /demanda ponta:\s*(\d+(?:[,.]\d+)?)/i, 120)
  const demandaFora = numero(dadosCarga.demandaForaPontaKw) || extrairNumero(texto, /demanda fora ponta:\s*(\d+(?:[,.]\d+)?)/i, 95)
  const cargaKw = Math.max(demandaPonta, demandaFora, consumo / 150 || 120)
  const usarDiesel = perguntasIa.geradorExistente === 'sim' || /gerador|diesel|backup/i.test(texto)
  const pmp = 610

  return {
    nome_projeto: normalizarNomeProjeto('Sugestao IA - Projeto Exemplo'),
    conectado_rede: !/off.?grid|isolad/i.test(texto),
    Config_Simulacao: [{ Tipo_Sim: 'ViabilidadeEconomica', Passo_sim: 1, Tempo_sim: 8760 }],
    Clima_Ambiente: [{ clima_id: 'Clima_Ambiente', nome_cidade: cidade, pais: 'BR', data: 20240116 }],
    painel_info: [{ pv_id: 'PV_1', fabricante_painel: 'CanadianSolar', modelo_painel: 'TOPBiHiKu6-610W', Pmp: pmp, Isc: 15.97, Voc: 48, Imp: 14.96, Vmp: 40.8, Uisc: 0.05, Uvoc: -0.25, Upmp: -0.29, material_painel: 'Silicio', eficiencia: 22.6, quantidade: [quantidadePainelParaKwp(kwp, pmp), 1] }],
    inversor_info: [{ inv_id: 'Inv_1', fabricante_inversor: 'Deye', modelo_inversor: 'SUN-35K-SG01HP3-EU-BM', Nm_MPPT: 3, In_Pmax: Math.max(kwp * 1.05, 38.5), Imax_MPPT: 36, In_Vnom: 600, In_Vmin: 150, In_Vmax: 1000, In_MPP_Vmin: 150, In_MPP_Vmax: 850, Out_Pmax: Math.max(kwp * 1.05, 38.5), Out_Imax: 58.4, Out_VL_nom: 380, Out_Freq: 60, Eficiencia: 0.976, Max_THD: 3, Fator_pot: 0.9999, Nm_fases: 3, smart: false, quantidade: 1 }],
    cargas_info: [{ carga_id: 'Load_1', nome_carga: perfilLocal.tipo || 'Mercado', tipo_carga: perfilLocal.tipo || 'Comercial', curva_carga: 'perfil_carga_ifg.csv', curva_carga_pontos: parseCurvaCarga(dadosCarga.curvaCargaPontos), consumo_mensal_kwh: consumo, demanda_ponta_kw: demandaPonta, demanda_fora_ponta_kw: demandaFora, s_instalada: cargaKw, fp: 0.9999, v_nom: 380, f_rede: 60, quantidade: 1 }],
    bateria_info: [{ bateria_id: 'Batt_1', fabricante: 'BYD', modelo: 'Battery-Box Premium HVS', capacidade_kwh: bateriaKwh, tensao_nominal: 480, potencia_max_carga_kw: Math.min(bateriaKwh, cargaKw), potencia_max_descarga_kw: Math.min(bateriaKwh, cargaKw), soc_min: 20, soc_max: 100, soc_inicial: 50, eficiencia_carga: 0.95, eficiencia_descarga: 0.95, vida_util_ciclos: 6000, quantidade: 1, periodo_de_carga: { permitir_carga: true, horario_carga_permitido: perguntasIa.horarioCargaBateria || '10:00-16:00' }, periodo_de_descarga: { permitir_descarga: true, horario_descarga_permitido: perguntasIa.horarioDescargaBateria || '18:00-21:00' } }],
    barramento_info: [{ bus_id: 'Bus_ac_1', tipo: 'AC', fases: 3, V_linha_nominal: 380, V_fase_nominal: 220, V_min: 0.9, V_max: 1.1 }],
    geradordiesel_info: usarDiesel ? [{ diesel_id: 'Diesel_1', fabricante: 'Cummins', modelo: 'C275D5', potencia_nominal_kw: Math.max(275, cargaKw * 0.5), potencia_minima_kw: 82.5, tensao_nominal: 380, frequencia: 60, fases: 3, fator_potencia: 0.8, eficiencia_nominal: 0.35, consumo_especifico_diesel: 0.24, capacidade_tanque_litros: 500, custo_diesel_litro: 6.5, custo_manutencao_hora: 15, custo_investimento: 150000, vida_util_horas: 30000, tempo_partida_minutos: 2, tempo_parada_minutos: 1, emisso_co2_kg_litro: 2.68, nivel_ruido_db: 75, quantidade: 1, operacao: { modo_operacao: 'backup', prioridade: 3, permitir_paralelismo_rede: false, horario_operacao_permitido: '24h' } }] : [],
    tarifas_energia: { horarios: { ponta: { dias_uteis: '18:00-21:00', fim_semana: 'não aplica' }, fora_ponta: { dias_uteis: '00:00-18:00, 21:00-24:00', fim_semana: '00:00-24:00' } }, custos_investimento: { pv_kwp: 3500, bess_kwh: 1900, unidade: 'R$' } },
    grafo_conexoes: [{ between: ['Clima_Ambiente', 'PV_1'] }, { between: ['PV_1', 'Inv_1'] }, { between: ['Batt_1', 'Inv_1'] }, { between: ['Inv_1', 'Bus_ac_1'] }, { between: ['Bus_ac_1', 'Load_1'] }],
  }
}

function parseCurvaCarga(texto) {
  if (!texto) return []
  return String(texto)
    .split(/[\n,;]+/)
    .map((item, index) => {
      const partes = item.trim().split(':')
      if (partes.length === 2) return { hora: numero(partes[0], index), valorKw: numero(partes[1]) }
      return { hora: index, valorKw: numero(item) }
    })
    .filter((p) => p.hora >= 0 && p.hora <= 23 && p.valorKw > 0)
    .slice(0, 24)
}

function aplicarDadosCarga(modelo, dadosCarga, perguntasIa) {
  const ajustado = JSON.parse(JSON.stringify(modelo))
  const carga = ajustado.cargas_info?.[0]
  if (carga) {
    if (dadosCarga.consumoKwh) carga.consumo_mensal_kwh = numero(dadosCarga.consumoKwh)
    if (dadosCarga.demandaPontaKw) carga.demanda_ponta_kw = numero(dadosCarga.demandaPontaKw)
    if (dadosCarga.demandaForaPontaKw) carga.demanda_fora_ponta_kw = numero(dadosCarga.demandaForaPontaKw)
    if (dadosCarga.demandaPontaKw || dadosCarga.demandaForaPontaKw) carga.s_instalada = Math.max(numero(dadosCarga.demandaPontaKw), numero(dadosCarga.demandaForaPontaKw))
    if (dadosCarga.curvaCargaPontos) carga.curva_carga_pontos = parseCurvaCarga(dadosCarga.curvaCargaPontos)
  }
  const bateria = ajustado.bateria_info?.[0]
  if (bateria) {
    bateria.periodo_de_carga = { permitir_carga: true, horario_carga_permitido: perguntasIa.horarioCargaBateria || '10:00-16:00' }
    bateria.periodo_de_descarga = { permitir_descarga: true, horario_descarga_permitido: perguntasIa.horarioDescargaBateria || '18:00-21:00' }
  }
  return ajustado
}

function aplicarTarifa(modelo, tarifaCliente) {
  const grupo = tarifaCliente.grupo || 'A'
  const modalidade = tarifaCliente.modalidade || (grupo === 'A' ? 'Verde' : 'Convencional')
  const tarifa = { grupo, modalidade, unidade_consumo: 'R$/kWh', unidade_demanda: 'R$/kW' }
  if (grupo === 'A') {
    tarifa.consumo_ponta_rs_kwh = tarifaCliente.consumoPonta || null
    tarifa.consumo_fora_ponta_rs_kwh = tarifaCliente.consumoForaPonta || null
  }
  if (grupo === 'A' && modalidade === 'Verde') tarifa.demanda_rs_kw = tarifaCliente.demanda || null
  if (grupo === 'A' && modalidade === 'Azul') {
    tarifa.demanda_ponta_rs_kw = tarifaCliente.demandaPonta || null
    tarifa.demanda_fora_ponta_rs_kw = tarifaCliente.demandaForaPonta || null
  }
  if (grupo === 'B' && modalidade === 'Convencional') tarifa.consumo_rs_kwh = tarifaCliente.consumoConvencional || null
  if (grupo === 'B' && modalidade === 'Branca') {
    tarifa.consumo_fora_ponta_rs_kwh = tarifaCliente.consumoForaPonta || null
    tarifa.consumo_intermediario_rs_kwh = tarifaCliente.consumoIntermediario || null
    tarifa.consumo_ponta_rs_kwh = tarifaCliente.consumoPonta || null
  }
  return { ...modelo, tarifas_energia: { ...(modelo.tarifas_energia || {}), enquadramento_tarifario: tarifa } }
}

function analisarModelo(modelo) {
  const painel = modelo.painel_info?.[0] || {}
  const bateria = modelo.bateria_info?.[0] || {}
  const cargas = modelo.cargas_info || []
  const inversores = modelo.inversor_info || []
  const fvKwp = (numero(painel.Pmp) * numero(painel.quantidade?.[0], 1)) / 1000
  const bateriaKwh = numero(bateria.capacidade_kwh)
  const cargaKw = cargas.reduce((total, carga) => total + numero(carga.s_instalada), 0)
  const inversorKw = inversores.reduce((total, inversor) => total + numero(inversor.Out_Pmax), 0)
  const consumoKwh = cargas.reduce((total, carga) => total + numero(carga.consumo_mensal_kwh), 0)
  const demandaInformada = cargas.some((carga) => numero(carga.demanda_ponta_kw) || numero(carga.demanda_fora_ponta_kw))
  const avisos = []
  const criticos = []
  const sugestoes = []
  if (!consumoKwh) avisos.push('Informe o consumo mensal em kWh para melhorar o dimensionamento.')
  if (!demandaInformada) avisos.push('Informe demanda ponta e fora ponta em kW.')
  if (cargaKw && bateriaKwh / cargaKw < 1) avisos.push(`Autonomia estimada baixa (${(bateriaKwh / cargaKw).toFixed(2)} h).`)
  if (fvKwp && inversorKw && inversorKw < fvKwp * 0.75) avisos.push('Inversor pode estar subdimensionado em relação ao FV.')
  if (cargaKw > fvKwp * 8) sugestoes.push('Carga muito maior que a geração FV. Revise demanda ou aumente o campo solar.')
  if (bateriaKwh < cargaKw * 2) sugestoes.push('Avaliar bateria maior para atender a autonomia desejada.')
  return { fvKwp, bateriaKwh, cargaKw, inversorKw, avisos, criticos, sugestoes }
}

function metricasCenario(cenario) {
  const relatorio = cenario?.resultado_json?.analise_financeira?.relatorio || {}
  const modelo = cenario?.modelo_json || {}
  const painel = modelo.painel_info?.[0] || {}
  const bateria = modelo.bateria_info?.[0] || {}
  return {
    capex: numero(relatorio.capex?.capex_total),
    economia: numero(relatorio.economia_anual),
    vpl: numero(relatorio.vpl),
    tir: relatorio.tir == null ? null : numero(relatorio.tir) * 100,
    payback: relatorio.payback,
    fvKwp: (numero(painel.Pmp) * numero(painel.quantidade?.[0], 1)) / 1000,
    bateriaKwh: numero(bateria.capacidade_kwh),
  }
}

function melhorId(cenarios, seletor, menor = false) {
  const validos = cenarios.map((c) => ({ id: c.id, valor: seletor(metricasCenario(c)) })).filter((i) => Number.isFinite(i.valor))
  if (!validos.length) return null
  return validos.reduce((melhor, item) => (menor ? (item.valor < melhor.valor ? item : melhor) : item.valor > melhor.valor ? item : melhor)).id
}

function recomendarCenario(cenarios) {
  if (!cenarios.length) return null
  const id = melhorId(cenarios, (m) => m.vpl)
  const cenario = cenarios.find((c) => c.id === id)
  return cenario ? { cenario, motivo: 'maior VPL com apoio de economia anual, CAPEX e payback.' } : null
}

function tarifasComparacao(tarifaAtual) {
  const v = (valor, padrao) => (valor ? valor : padrao)
  return [
    { nome: 'Grupo A Verde', tarifa: { ...tarifaAtual, grupo: 'A', modalidade: 'Verde', consumoPonta: v(tarifaAtual.consumoPonta, '1,25'), consumoForaPonta: v(tarifaAtual.consumoForaPonta, '0,68'), demanda: v(tarifaAtual.demanda, '42,50') } },
    { nome: 'Grupo A Azul', tarifa: { ...tarifaAtual, grupo: 'A', modalidade: 'Azul', consumoPonta: v(tarifaAtual.consumoPonta, '1,25'), consumoForaPonta: v(tarifaAtual.consumoForaPonta, '0,68'), demandaPonta: v(tarifaAtual.demandaPonta, '65,00'), demandaForaPonta: v(tarifaAtual.demandaForaPonta, '32,00') } },
    { nome: 'Grupo B Convencional', tarifa: { ...tarifaAtual, grupo: 'B', modalidade: 'Convencional', consumoConvencional: v(tarifaAtual.consumoConvencional, '0,72') } },
    { nome: 'Grupo B Branca', tarifa: { ...tarifaAtual, grupo: 'B', modalidade: 'Branca', consumoForaPonta: v(tarifaAtual.consumoForaPonta, '0,62'), consumoIntermediario: v(tarifaAtual.consumoIntermediario, '0,82'), consumoPonta: v(tarifaAtual.consumoPonta, '1,10') } },
  ]
}

function escolherAleatorio(lista) {
  return lista[Math.floor(Math.random() * lista.length)]
}

function variarNumero(base, minimo, maximo) {
  const fator = minimo + Math.random() * (maximo - minimo)
  return Math.max(1, Math.round(base * fator))
}

function equipamentosPorTipo(componentes, tipo) {
  return componentes.filter((item) => item.tipo_codigo === tipo)
}

function gerarModeloAleatorio(modeloBase, componentes, tarifaAtual) {
  const modelo = JSON.parse(JSON.stringify(modeloBase || {}))
  const painel = modelo.painel_info?.[0]
  const inversor = modelo.inversor_info?.[0]
  const bateria = modelo.bateria_info?.[0]
  const carga = modelo.cargas_info?.[0]
  const dieselAtual = modelo.geradordiesel_info?.[0]

  const painelCatalogo = escolherAleatorio(equipamentosPorTipo(componentes, 'modulo_fv')) || null
  const inversorCatalogo = escolherAleatorio(equipamentosPorTipo(componentes, 'inversor')) || null
  const bateriaCatalogo = escolherAleatorio(equipamentosPorTipo(componentes, 'bateria')) || null
  const cargaCatalogo = escolherAleatorio(equipamentosPorTipo(componentes, 'carga')) || null
  const dieselCatalogo = escolherAleatorio(equipamentosPorTipo(componentes, 'gerador_diesel')) || null

  if (painel) {
    const pmp = numero(painelCatalogo?.potencia_kw, numero(painel.Pmp) / 1000 || 0.61) * 1000
    const kwpAtual = (numero(painel.Pmp, 610) * numero(painel.quantidade?.[0], 531)) / 1000
    const kwpNovo = variarNumero(kwpAtual || 324, 0.65, 1.75)
    painel.fabricante_painel = painelCatalogo?.fabricante_nome || painel.fabricante_painel
    painel.modelo_painel = painelCatalogo?.nome_modelo || painel.modelo_painel
    painel.Pmp = pmp
    painel.quantidade = [quantidadePainelParaKwp(kwpNovo, pmp), 1]
  }

  const kwpFinal = painel ? (numero(painel.Pmp, 610) * numero(painel.quantidade?.[0], 531)) / 1000 : 324

  if (inversor) {
    const potenciaCatalogo = numero(inversorCatalogo?.potencia_kw)
    const potenciaNova = potenciaCatalogo || Math.round(kwpFinal * (0.85 + Math.random() * 0.35))
    inversor.fabricante_inversor = inversorCatalogo?.fabricante_nome || inversor.fabricante_inversor
    inversor.modelo_inversor = inversorCatalogo?.nome_modelo || `${inversor.modelo_inversor || 'Inversor'} - variação`
    inversor.In_Pmax = potenciaNova
    inversor.Out_Pmax = potenciaNova
  }

  if (carga) {
    const cargaBase = Math.max(numero(carga.s_instalada), numero(carga.demanda_ponta_kw), numero(carga.demanda_fora_ponta_kw), 100)
    const demandaFora = variarNumero(cargaBase, 0.75, 1.45)
    const demandaPonta = variarNumero(demandaFora, 0.8, 1.25)
    carga.nome_carga = cargaCatalogo?.nome_modelo || carga.nome_carga || 'Cliente'
    carga.tipo_carga = cargaCatalogo?.nome_modelo || carga.tipo_carga || 'Comercial'
    carga.s_instalada = Math.max(demandaFora, demandaPonta)
    carga.demanda_ponta_kw = demandaPonta
    carga.demanda_fora_ponta_kw = demandaFora
    carga.consumo_mensal_kwh = variarNumero(numero(carga.consumo_mensal_kwh, carga.s_instalada * 150), 0.75, 1.35)
  }

  if (bateria) {
    const bateriaBase = numero(bateriaCatalogo?.energia_kwh, numero(bateria.capacidade_kwh, 500))
    const cargaKw = numero(carga?.s_instalada, 120)
    const autonomia = escolherAleatorio([1, 2, 3, 4])
    bateria.fabricante = bateriaCatalogo?.fabricante_nome || bateria.fabricante
    bateria.modelo = bateriaCatalogo?.nome_modelo || bateria.modelo
    bateria.capacidade_kwh = Math.max(variarNumero(bateriaBase, 0.7, 2.2), cargaKw * autonomia)
    bateria.potencia_max_carga_kw = Math.min(bateria.capacidade_kwh, cargaKw)
    bateria.potencia_max_descarga_kw = Math.min(bateria.capacidade_kwh, cargaKw)
  }

  const usarDiesel = Math.random() >= 0.35
  if (usarDiesel) {
    modelo.geradordiesel_info = [
      {
        ...(dieselAtual || {}),
        diesel_id: 'Diesel_1',
        fabricante: dieselCatalogo?.fabricante_nome || dieselAtual?.fabricante || 'Cummins',
        modelo: dieselCatalogo?.nome_modelo || dieselAtual?.modelo || 'C275D5',
        potencia_nominal_kw: numero(dieselCatalogo?.potencia_kw, numero(carga?.s_instalada, 120) * 0.6 || 275),
        custo_investimento: dieselAtual?.custo_investimento || 150000,
        operacao: dieselAtual?.operacao || { modo_operacao: 'backup', prioridade: 3, permitir_paralelismo_rede: false, horario_operacao_permitido: '24h' },
      },
    ]
  } else {
    modelo.geradordiesel_info = []
  }

  const tarifa = escolherAleatorio(tarifasComparacao(tarifaAtual))
  const modeloTarifado = aplicarTarifa(modelo, tarifa.tarifa)
  modeloTarifado.nome_projeto = `${modelo.nome_projeto || 'Projeto'} - versão aleatória ${new Date().toLocaleTimeString('pt-BR')}`
  return { modelo: modeloTarifado, nomeTarifa: tarifa.nome }
}

export default function App() {
  const [componentes, setComponentes] = useState([])
  const [projeto, setProjeto] = useState(null)
  const [layout, setLayout] = useState({ nodes: [], edges: [] })
  const [simulacao, setSimulacao] = useState(null)
  const [selectedNode, setSelectedNode] = useState(null)
  const [selectedEdge, setSelectedEdge] = useState(null)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [simulando, setSimulando] = useState(false)
  const [promptIa, setPromptIa] = useState('Usina fotovoltaica com BESS em Goiania, 324 kWp solar, bateria 500 kWh, carga comercial mercado, conectado a rede e gerador diesel de backup.')
  const [dadosCarga, setDadosCarga] = useState({ consumoKwh: '', demandaPontaKw: '', demandaForaPontaKw: '', curvaCargaPontos: '' })
  const [perguntasIa, setPerguntasIa] = useState({ geradorExistente: 'sim', autonomiaHoras: '2', horarioCargaBateria: '10:00-16:00', horarioDescargaBateria: '18:00-21:00' })
  const [perfilLocal, setPerfilLocal] = useState({ tipo: '', porte: '', funcionamento: '', observacoes: '' })
  const [tarifaCliente, setTarifaCliente] = useState({ grupo: 'A', modalidade: 'Verde', consumoPonta: '', consumoForaPonta: '', consumoIntermediario: '', consumoConvencional: '', demanda: '', demandaPonta: '', demandaForaPonta: '' })
  const [modeloSimulacao, setModeloSimulacao] = useState(null)
  const [nomeArquivoSimulacao, setNomeArquivoSimulacao] = useState('')
  const [preAnalise, setPreAnalise] = useState(null)
  const [historicoIa, setHistoricoIa] = useState([])
  const [cenarios, setCenarios] = useState([])
  const [mensagem, setMensagem] = useState('')
  const [comparandoTarifas, setComparandoTarifas] = useState(false)
  const [gerandoAleatorio, setGerandoAleatorio] = useState(false)
  const [executandoFluxo, setExecutandoFluxo] = useState(false)
  const [resultadoMicrorredes, setResultadoMicrorredes] = useState(null)
  const [resultadoTransitorio, setResultadoTransitorio] = useState(null)
  const [resultadoEquipamentos, setResultadoEquipamentos] = useState(null)
  const [executandoEquipamentos, setExecutandoEquipamentos] = useState(false)
  const [tempoEquipamentos, setTempoEquipamentos] = useState('0.1')
  const [testeIrradianciaEquipamentos, setTesteIrradianciaEquipamentos] = useState(false)
  const [activeWorkspaceTab, setActiveWorkspaceTab] = useState('simulador')
  const [consultaAneel, setConsultaAneel] = useState({ cidade: 'Goiania', uf: 'GO', distribuidora: '' })
  const [dadosAneel, setDadosAneel] = useState(null)
  const importInputRef = useRef(null)

  useEffect(() => {
    async function bootstrap() {
      setLoading(true)
      const projetosResp = await api.get('projetos/')
      let projetoAtual = projetosResp.data[0]
      if (!projetoAtual) {
        await api.post('projetos/', { nome: 'Projeto Exemplo', descricao: 'Projeto criado automaticamente' })
        projetoAtual = (await api.get('projetos/')).data[0]
      }
      setProjeto(projetoAtual)
      const [componentesResp, diagramaResp, historicoResp, cenariosResp] = await Promise.all([
        api.get('componentes/'),
        api.get(`projetos/${projetoAtual.id}/diagrama/`),
        api.get(`historico-ia/?projeto=${projetoAtual.id}`),
        api.get(`cenarios/?projeto=${projetoAtual.id}`),
      ])
      setComponentes(componentesResp.data)
      setLayout(diagramaResp.data.layout_json || { nodes: [], edges: [] })
      setSimulacao(diagramaResp.data.simulacao_json || null)
      setHistoricoIa(historicoResp.data || [])
      setCenarios(cenariosResp.data || [])
      setLoading(false)
    }
    bootstrap()
  }, [])

  const componentesAtivos = useMemo(() => componentes.filter((item) => item.ativo), [componentes])
  const recomendacao = useMemo(() => recomendarCenario(cenarios), [cenarios])
  const destaques = useMemo(() => ({
    menorCapex: melhorId(cenarios, (m) => m.capex, true),
    maiorEconomia: melhorId(cenarios, (m) => m.economia),
    melhorVpl: melhorId(cenarios, (m) => m.vpl),
    menorPayback: melhorId(cenarios, (m) => m.payback, true),
  }), [cenarios])

  async function salvarLayout(novoLayout) {
    setLayout(novoLayout)
    if (!projeto?.id) return null
    const resp = await api.post(`projetos/${projeto.id}/diagrama/`, { layout_json: novoLayout })
    setSimulacao(resp.data.simulacao_json)
    return resp.data.simulacao_json
  }

  async function montarJsonModeloDaTela() {
    const resp = await api.post('gerar-json-modelo/', { layout_json: layout, nome_projeto: projeto?.nome || 'Projeto Simulador' })
    return resp.data
  }

  async function simularAgora() {
    setSimulando(true)
    try {
      const modeloBase = await montarJsonModeloDaTela()
      const modelo = aplicarTarifa(aplicarDadosCarga(modeloBase, dadosCarga, perguntasIa), tarifaCliente)
      const previa = analisarModelo(modelo)
      setPreAnalise(previa)
      if (previa.criticos.length) throw new Error(previa.criticos.join('\n'))
      setModeloSimulacao(modelo)
      setNomeArquivoSimulacao('JSON dos blocos atuais')
      setMensagem('Executando análise econômica no prime-django...')
      const resp = await api.post('analise-financeira/', { layout_json: layout, nome_projeto: projeto?.nome || 'Projeto Simulador', modelo_entradas: modelo, modelo_origem: 'JSON dos blocos atuais' })
      setSimulacao(resp.data)
      setMensagem('Análise econômica concluída.')
      setActiveWorkspaceTab('resultado')
    } catch (error) {
      const detalhe = error.response?.data?.erro || error.message
      setMensagem(`Não foi possível simular: ${detalhe}`)
      alert(`Não foi possível gerar a análise financeira.\n\n${detalhe}`)
    } finally {
      setSimulando(false)
    }
  }

  async function executarTransitorio(cenario) {
    const modeloBase = await montarJsonModeloDaTela()
    const modelo = aplicarTarifa(aplicarDadosCarga(modeloBase, dadosCarga, perguntasIa), tarifaCliente)
    const resp = await api.post('microrredes/transitorio/', { modelo_entradas: modelo, cenario })
    setResultadoTransitorio(resp.data)
    setMensagem('Ensaio transitório concluído.')
    setActiveWorkspaceTab('resultado')
  }

  async function executarEquipamentos() {
    setExecutandoEquipamentos(true)
    setResultadoEquipamentos(null)
    setMensagem('Executando Equipamentos - Projeto...')
    try {
      const modeloBase = await montarJsonModeloDaTela()
      const modelo = aplicarDadosCarga(modeloBase, dadosCarga, perguntasIa)
      const resp = await api.post('equipamentos/simular/', {
        modelo_entradas: modelo, layout_json: layout,
        configuracao: { tempo_s: Number(tempoEquipamentos), passo_s: 0.00002, teste_irradiancia: testeIrradianciaEquipamentos },
      })
      setResultadoEquipamentos(resp.data)
      setMensagem('Equipamentos concluído. Gráficos disponíveis em Resultados.')
      setActiveWorkspaceTab('resultado')
    } catch (error) {
      setMensagem(`Não foi possível executar Equipamentos: ${error.response?.data?.erro || error.message}`)
    } finally {
      setExecutandoEquipamentos(false)
    }
  }

  async function executarFluxoPotencia() {
    setExecutandoFluxo(true)
    try {
      const modeloBase = await montarJsonModeloDaTela()
      const modelo = aplicarTarifa(aplicarDadosCarga(modeloBase, dadosCarga, perguntasIa), tarifaCliente)
      setMensagem('Executando fluxo de potência no projeto microrredes...')
      const resp = await api.post('microrredes/fluxo-potencia/', {
        layout_json: layout,
        nome_projeto: projeto?.nome || 'Projeto Simulador',
        modelo_entradas: modelo,
      })
      setResultadoMicrorredes(resp.data)
      setMensagem('Fluxo de potência concluído.')
      setActiveWorkspaceTab('resultado')
    } catch (error) {
      const detalhe = error.response?.data?.erro || error.message
      setMensagem(`Não foi possível executar o fluxo de potência: ${detalhe}`)
      alert(`Não foi possível executar o projeto microrredes.\n\n${detalhe}`)
    } finally {
      setExecutandoFluxo(false)
    }
  }

  async function gerarSugestaoIa() {
    setBusy(true)
    try {
      const modelo = aplicarTarifa(gerarModeloPorTexto(promptIa, dadosCarga, perguntasIa, perfilLocal), tarifaCliente)
      const novoLayout = modeloEntradasParaLayout(modelo)
      setLayout(novoLayout)
      setModeloSimulacao(modelo)
      setPreAnalise(analisarModelo(modelo))
      setNomeArquivoSimulacao(`${modelo.nome_projeto}.json`)
      const hist = await api.post('historico-ia/', { projeto: projeto?.id || null, prompt: promptIa, nome_arquivo: `${modelo.nome_projeto}.json`, cidade: modelo.Clima_Ambiente?.[0]?.nome_cidade || '', modelo_json: modelo, layout_json: novoLayout })
      setHistoricoIa((atual) => [hist.data, ...atual.filter((i) => i.id !== hist.data.id)])
      await salvarLayout(novoLayout)
      setMensagem('Sugestão da IA gerada. Clique em Executar análise econômica para calcular.')
      setActiveWorkspaceTab('unifilar')
    } catch (error) {
      alert('Não foi possível gerar sugestão da IA.')
    } finally {
      setBusy(false)
    }
  }

  async function gerarDiagramaBase() {
    if (!projeto?.id) return
    setBusy(true)
    try {
      const resp = await api.post(`projetos/${projeto.id}/gerar-diagrama-base/`)
      setLayout(resp.data.layout_json || { nodes: [], edges: [] })
      setSimulacao(resp.data.simulacao_json || null)
      setSelectedNode(null)
      setActiveWorkspaceTab('unifilar')
    } finally {
      setBusy(false)
    }
  }

  function atualizarNode(nodeAtualizado) {
    const novoLayout = { ...layout, nodes: (layout.nodes || []).map((node) => (node.id === nodeAtualizado.id ? nodeAtualizado : node)) }
    setSelectedNode(nodeAtualizado)
    salvarLayout(novoLayout)
  }

  function removerNode(nodeId) {
    salvarLayout({ nodes: (layout.nodes || []).filter((node) => node.id !== nodeId), edges: (layout.edges || []).filter((edge) => edge.source !== nodeId && edge.target !== nodeId) })
    setSelectedNode(null)
  }

  function selecionarPerfil(perfil) {
    setPromptIa(perfil.prompt)
    setDadosCarga({ curvaCargaPontos: '', ...perfil.dados })
    setPerfilLocal({ ...perfil.local, observacoes: perfil.descricao })
  }

  function usarExemplo() {
    setPromptIa(exemploAssistenteIa)
    setDadosCarga({ consumoKwh: '18000', demandaPontaKw: '120', demandaForaPontaKw: '95', curvaCargaPontos: '' })
    setPerguntasIa({ geradorExistente: 'sim', autonomiaHoras: '2', horarioCargaBateria: '10:00-16:00', horarioDescargaBateria: '18:00-21:00' })
  }

  async function importarJson(event) {
    const file = event.target.files?.[0]
    if (!file) return
    const texto = await file.text()
    const modelo = JSON.parse(texto)
    const novoLayout = modeloEntradasParaLayout(modelo)
    setModeloSimulacao(modelo)
    setNomeArquivoSimulacao(file.name)
    await salvarLayout(novoLayout)
    setMensagem(`JSON importado: ${file.name}`)
    setActiveWorkspaceTab('unifilar')
    event.target.value = ''
  }

  async function salvarCenarioAtual() {
    if (!simulacao?.analise_financeira?.relatorio) {
      alert('Execute uma simulação financeira antes de salvar o cenário.')
      return
    }
    const nome = window.prompt('Nome do cenário', `Cenário ${cenarios.length + 1} - ${projeto?.nome || 'Simulação'}`)
    if (!nome) return
    const modelo = modeloSimulacao || (await montarJsonModeloDaTela())
    const resp = await api.post('cenarios/', { projeto: projeto?.id || null, nome, descricao: promptIa, modelo_origem: nomeArquivoSimulacao || 'JSON da tela', modelo_json: modelo, layout_json: layout, resultado_json: simulacao })
    setCenarios((atual) => [resp.data, ...atual])
  }

  async function apagarCenario(cenario) {
    if (!window.confirm(`Apagar o cenário "${cenario.nome}"?`)) return
    await api.delete(`cenarios/${cenario.id}/`)
    setCenarios((atual) => atual.filter((item) => item.id !== cenario.id))
  }

  async function duplicarCenario(cenario) {
    const modelo = JSON.parse(JSON.stringify(cenario.modelo_json || {}))
    if (modelo.bateria_info?.[0]) modelo.bateria_info[0].capacidade_kwh = Math.round(numero(modelo.bateria_info[0].capacidade_kwh) * 1.5)
    const layoutDuplicado = modeloEntradasParaLayout(modelo)
    const nome = `${cenario.nome} - bateria maior`
    const analise = await api.post('analise-financeira/', { layout_json: layoutDuplicado, nome_projeto: nome, modelo_entradas: modelo, modelo_origem: nome })
    const resp = await api.post('cenarios/', { projeto: projeto?.id || null, nome, descricao: `Duplicado de ${cenario.nome}`, modelo_origem: nome, modelo_json: modelo, layout_json: layoutDuplicado, resultado_json: analise.data })
    setCenarios((atual) => [resp.data, ...atual])
  }

  async function simularCenarioNovamente(cenario) {
    const resp = await api.post('analise-financeira/', { layout_json: cenario.layout_json, nome_projeto: cenario.nome, modelo_entradas: cenario.modelo_json, modelo_origem: cenario.nome })
    setSimulacao(resp.data)
    setLayout(cenario.layout_json)
    setModeloSimulacao(cenario.modelo_json)
    setMensagem(`Cenário recalculado: ${cenario.nome}`)
  }

  async function compararModalidadesTarifarias() {
    setComparandoTarifas(true)
    try {
      const modeloBase = aplicarDadosCarga(modeloSimulacao || (await montarJsonModeloDaTela()), dadosCarga, perguntasIa)
      const novos = []
      for (const item of tarifasComparacao(tarifaCliente)) {
        const modelo = aplicarTarifa(JSON.parse(JSON.stringify(modeloBase)), item.tarifa)
        modelo.nome_projeto = `${projeto?.nome || 'Projeto'} - ${item.nome}`
        const respAnalise = await api.post('analise-financeira/', { layout_json: layout, nome_projeto: modelo.nome_projeto, modelo_entradas: modelo, modelo_origem: `Comparação tarifária - ${item.nome}` })
        const respCenario = await api.post('cenarios/', { projeto: projeto?.id || null, nome: modelo.nome_projeto, descricao: `Comparação tarifária - ${item.nome}`, modelo_origem: item.nome, modelo_json: modelo, layout_json: layout, resultado_json: respAnalise.data })
        novos.push(respCenario.data)
      }
      setCenarios((atual) => [...novos, ...atual])
      const melhor = recomendarCenario(novos)
      setMensagem(`Comparação concluída. Melhor opção: ${melhor?.cenario?.nome || 'ver tabela'}`)
    } catch (error) {
      alert(`Não foi possível comparar as modalidades tarifárias.\n\n${error.response?.data?.erro || error.message}`)
    } finally {
      setComparandoTarifas(false)
    }
  }

  async function gerarVersaoAleatoria() {
    setGerandoAleatorio(true)
    try {
      setMensagem('Gerando versão aleatória...')
      const modeloBase = aplicarDadosCarga(modeloSimulacao || (await montarJsonModeloDaTela()), dadosCarga, perguntasIa)
      const { modelo, nomeTarifa } = gerarModeloAleatorio(modeloBase, componentesAtivos, tarifaCliente)
      const layoutAleatorio = modeloEntradasParaLayout(modelo)
      const previa = analisarModelo(modelo)
      setPreAnalise(previa)

      const respAnalise = await api.post('analise-financeira/', {
        layout_json: layoutAleatorio,
        nome_projeto: modelo.nome_projeto,
        modelo_entradas: modelo,
        modelo_origem: `Versão aleatória - ${nomeTarifa}`,
      })
      const respCenario = await api.post('cenarios/', {
        projeto: projeto?.id || null,
        nome: modelo.nome_projeto,
        descricao: `Versão aleatória com equipamentos cadastrados e tarifa ${nomeTarifa}.`,
        modelo_origem: `Versão aleatória - ${nomeTarifa}`,
        modelo_json: modelo,
        layout_json: layoutAleatorio,
        resultado_json: respAnalise.data,
      })

      setLayout(layoutAleatorio)
      setModeloSimulacao(modelo)
      setNomeArquivoSimulacao(`${modelo.nome_projeto}.json`)
      setSimulacao(respAnalise.data)
      setCenarios((atual) => [respCenario.data, ...atual])
      setMensagem(`Versão aleatória criada e simulada: ${modelo.nome_projeto}`)
    } catch (error) {
      const detalhe = error.response?.data?.erro || error.message
      setMensagem(`Não foi possível gerar versão aleatória: ${detalhe}`)
      alert(`Não foi possível gerar a versão aleatória.\n\n${detalhe}`)
    } finally {
      setGerandoAleatorio(false)
    }
  }

  async function buscarAneel() {
    const resp = await api.get('aneel-dados/', { params: consultaAneel })
    setDadosAneel(resp.data)
  }

  if (loading) return <div className="center-screen">Carregando aplicação...</div>

  return (
    <div className={`app-shell${['resultado', 'pop'].includes(activeWorkspaceTab) ? ' results-layout' : ''}`}>
      {!['resultado', 'pop'].includes(activeWorkspaceTab) ? <Sidebar componentes={componentesAtivos} /> : null}
      <div className="main-area">
        <div className="workspace-tab-shell">
          <nav className="workspace-tab-nav" role="tablist" aria-label="Áreas do simulador" aria-orientation="vertical">
            {[
              ['simulador', 'Simulador', 'Configuração e IA'],
              ['unifilar', 'Unifilar', 'Diagrama elétrico'],
              ['resultado', 'Resultado', simulacao ? 'Simulação disponível' : 'Aguardando simulação'],
              ['cenarios', 'Cenários', `${cenarios.length} salvos`],
              ['historico', 'Histórico IA', `${historicoIa.length} pesquisas`],
              ['pop', 'POP / Ajuda', 'Procedimento e download'],
            ].map(([id, label, detail]) => (
              <button
                key={id}
                type="button"
                role="tab"
                aria-selected={activeWorkspaceTab === id}
                className={`workspace-tab-button ${activeWorkspaceTab === id ? 'active' : ''}`}
                onClick={() => setActiveWorkspaceTab(id)}
              >
                <strong>{label}</strong>
                <span>{detail}</span>
              </button>
            ))}
          </nav>

          <div className="workspace-tab-content">
        {activeWorkspaceTab === 'pop' ? <PopHelp /> : null}
        {activeWorkspaceTab === 'simulador' ? <section className="workspace-card simulator-card" role="tabpanel">
          <header className="topbar">
          <div>
            <h1>Simulador de Usina Fotovoltaica com BESS</h1>
            <span className="project-name">{projeto?.nome || 'Projeto Exemplo'}</span>
            <p>Gere o diagrama, confira o unifilar e rode a simulação.</p>
          </div>
          <div className="topbar-actions">
            <button className="secondary-btn" onClick={() => importInputRef.current?.click()}>Importar JSON gerar blocos</button>
            <input ref={importInputRef} type="file" accept=".json,application/json" hidden onChange={importarJson} />
            <button className="warning-btn" onClick={gerarDiagramaBase}>{busy ? 'Gerando...' : 'Gerar diagrama base'}</button>
          </div>
          </header>

          <div className="ai-suggestion-panel">
          <div>
            <strong>Assistente IA para sugerir diagrama</strong>
            <p>Descreva a usina desejada ou use as perguntas guiadas.</p>
          </div>
          <textarea value={promptIa} onChange={(e) => setPromptIa(e.target.value)} />
          <div className="guided-ai-panel">
            <strong>Perguntas guiadas</strong>
            <label>Gerador existente?
              <select value={perguntasIa.geradorExistente} onChange={(e) => setPerguntasIa((a) => ({ ...a, geradorExistente: e.target.value }))}>
                <option value="sim">Sim, usar como backup</option>
                <option value="nao">Não usar gerador</option>
              </select>
            </label>
            <label>Autonomia desejada (h)<input value={perguntasIa.autonomiaHoras} onChange={(e) => setPerguntasIa((a) => ({ ...a, autonomiaHoras: e.target.value }))} /></label>
            <label>Carregar bateria<input value={perguntasIa.horarioCargaBateria} onChange={(e) => setPerguntasIa((a) => ({ ...a, horarioCargaBateria: e.target.value }))} /></label>
            <label>Usar bateria<input value={perguntasIa.horarioDescargaBateria} onChange={(e) => setPerguntasIa((a) => ({ ...a, horarioDescargaBateria: e.target.value }))} /></label>
          </div>
          <div className="profile-panel">
            <strong>Biblioteca de perfis comerciais</strong>
            {perfilCarga.map((p) => <button key={p.nome} className="profile-btn" onClick={() => selecionarPerfil(p)}><strong>{p.nome}</strong><small>{p.descricao}</small></button>)}
          </div>
          <div className="ai-example-panel">
            <strong>Exemplo para o usuário</strong>
            <p>Usina FV com BESS em Brasília · Consumo 18000 kWh · Demanda ponta 120 kW · Fora ponta 95 kW · Gerador sim · Autonomia 2h</p>
            <button onClick={usarExemplo}>Usar este exemplo</button>
          </div>
          <div className="load-input-panel">
            <strong>Dados de carga do cliente</strong>
            <label>Consumo de energia (kWh)<input value={dadosCarga.consumoKwh} onChange={(e) => setDadosCarga((a) => ({ ...a, consumoKwh: e.target.value }))} placeholder="Ex.: 18000" /></label>
            <label>Demanda ponta (kW)<input value={dadosCarga.demandaPontaKw} onChange={(e) => setDadosCarga((a) => ({ ...a, demandaPontaKw: e.target.value }))} placeholder="Ex.: 120" /></label>
            <label>Demanda fora ponta (kW)<input value={dadosCarga.demandaForaPontaKw} onChange={(e) => setDadosCarga((a) => ({ ...a, demandaForaPontaKw: e.target.value }))} placeholder="Ex.: 95" /></label>
            <label className="load-curve-input">Arquivo/curva de carga (pontos kW)<textarea value={dadosCarga.curvaCargaPontos} onChange={(e) => setDadosCarga((a) => ({ ...a, curvaCargaPontos: e.target.value }))} placeholder="0:55, 1:55, 2:50 ... ou 24 valores" /></label>
          </div>
          <div className="site-profile-panel">
            <strong>Perfil do local</strong>
            <label>Tipo<input value={perfilLocal.tipo} onChange={(e) => setPerfilLocal((a) => ({ ...a, tipo: e.target.value }))} placeholder="Ex.: Supermercado" /></label>
            <label>Porte<input value={perfilLocal.porte} onChange={(e) => setPerfilLocal((a) => ({ ...a, porte: e.target.value }))} placeholder="Ex.: 500 alunos" /></label>
            <label>Funcionamento<input value={perfilLocal.funcionamento} onChange={(e) => setPerfilLocal((a) => ({ ...a, funcionamento: e.target.value }))} placeholder="Ex.: 07:00-18:00" /></label>
          </div>
          <div className="aneel-panel">
            <strong>Dados ANEEL / referência regional</strong>
            <label>Cidade<input value={consultaAneel.cidade} onChange={(e) => setConsultaAneel((a) => ({ ...a, cidade: e.target.value }))} /></label>
            <label>UF<input value={consultaAneel.uf} onChange={(e) => setConsultaAneel((a) => ({ ...a, uf: e.target.value.toUpperCase() }))} /></label>
            <label>Distribuidora<input value={consultaAneel.distribuidora} onChange={(e) => setConsultaAneel((a) => ({ ...a, distribuidora: e.target.value }))} /></label>
            <button className="secondary-btn" onClick={buscarAneel}>Buscar referência</button>
            {dadosAneel ? <p>{dadosAneel.distribuidora_sugerida}</p> : null}
          </div>
          <div className="tariff-panel">
            <strong>Enquadramento tarifário</strong>
            <label>Grupo<select value={tarifaCliente.grupo} onChange={(e) => setTarifaCliente((a) => ({ ...a, grupo: e.target.value, modalidade: e.target.value === 'A' ? 'Verde' : 'Convencional' }))}><option value="A">Grupo A</option><option value="B">Grupo B</option></select></label>
            <label>Modalidade<select value={tarifaCliente.modalidade} onChange={(e) => setTarifaCliente((a) => ({ ...a, modalidade: e.target.value }))}>{tarifaCliente.grupo === 'A' ? <><option>Verde</option><option>Azul</option></> : <><option>Convencional</option><option>Branca</option></>}</select></label>
            {tarifaCliente.grupo === 'A' ? <><label>Consumo ponta (R$/kWh)<input value={tarifaCliente.consumoPonta} onChange={(e) => setTarifaCliente((a) => ({ ...a, consumoPonta: e.target.value }))} /></label><label>Consumo fora ponta (R$/kWh)<input value={tarifaCliente.consumoForaPonta} onChange={(e) => setTarifaCliente((a) => ({ ...a, consumoForaPonta: e.target.value }))} /></label></> : null}
            {tarifaCliente.grupo === 'A' && tarifaCliente.modalidade === 'Verde' ? <label>Demanda (R$/kW)<input value={tarifaCliente.demanda} onChange={(e) => setTarifaCliente((a) => ({ ...a, demanda: e.target.value }))} /></label> : null}
            {tarifaCliente.grupo === 'A' && tarifaCliente.modalidade === 'Azul' ? <><label>Demanda ponta (R$/kW)<input value={tarifaCliente.demandaPonta} onChange={(e) => setTarifaCliente((a) => ({ ...a, demandaPonta: e.target.value }))} /></label><label>Demanda fora ponta (R$/kW)<input value={tarifaCliente.demandaForaPonta} onChange={(e) => setTarifaCliente((a) => ({ ...a, demandaForaPonta: e.target.value }))} /></label></> : null}
            {tarifaCliente.grupo === 'B' && tarifaCliente.modalidade === 'Convencional' ? <label>Consumo (R$/kWh)<input value={tarifaCliente.consumoConvencional} onChange={(e) => setTarifaCliente((a) => ({ ...a, consumoConvencional: e.target.value }))} /></label> : null}
            {tarifaCliente.grupo === 'B' && tarifaCliente.modalidade === 'Branca' ? <><label>Fora ponta (R$/kWh)<input value={tarifaCliente.consumoForaPonta} onChange={(e) => setTarifaCliente((a) => ({ ...a, consumoForaPonta: e.target.value }))} /></label><label>Intermediário (R$/kWh)<input value={tarifaCliente.consumoIntermediario} onChange={(e) => setTarifaCliente((a) => ({ ...a, consumoIntermediario: e.target.value }))} /></label><label>Ponta (R$/kWh)<input value={tarifaCliente.consumoPonta} onChange={(e) => setTarifaCliente((a) => ({ ...a, consumoPonta: e.target.value }))} /></label></> : null}
          </div>
          <div className="client-summary-panel">
            <strong>Resumo para dimensionamento</strong>
            <span>Consumo: {dadosCarga.consumoKwh || 0} kWh</span>
            <span>Maior demanda: {Math.max(numero(dadosCarga.demandaPontaKw), numero(dadosCarga.demandaForaPontaKw))} kW</span>
            <span>Tarifa: Grupo {tarifaCliente.grupo} {tarifaCliente.modalidade}</span>
            <span>Bateria: carga {perguntasIa.horarioCargaBateria}</span>
            <span>Uso: {perguntasIa.horarioDescargaBateria}</span>
          </div>
          <div className="ai-action-row">
            <button className="ai-btn" onClick={gerarSugestaoIa} disabled={busy}>IA sugerir e gerar blocos</button>
            <button className="economic-analysis-btn" onClick={simularAgora} disabled={simulando}>{simulando ? 'Executando análise...' : 'Executar análise econômica'}</button>
            <button className="power-flow-btn" onClick={executarFluxoPotencia} disabled={executandoFluxo}>{executandoFluxo ? 'Executando fluxo...' : 'Executar fluxo de potência'}</button>
          </div>
          <TransientScenario layout={layout} onRun={executarTransitorio} />
          <div className="alerts-box">
            <h4>Equipamentos - Projeto</h4>
            <p>Simula os equipamentos do projeto atual. Clima constante: 25 °C e 1000 W/m². Diesel e PCS separado não são modelados por este motor.</p>
            <label>Duração (s) <input type="number" min="0.02" max="2" step="0.02" value={tempoEquipamentos} onChange={(e) => setTempoEquipamentos(e.target.value)} disabled={executandoEquipamentos} /></label>
            <p>Passo: 20 µs. Os gráficos representam este ensaio curto.</p>
            <label><input type="checkbox" checked={testeIrradianciaEquipamentos} disabled={executandoEquipamentos} onChange={(e) => { setTesteIrradianciaEquipamentos(e.target.checked); if (e.target.checked && Number(tempoEquipamentos) < 0.3) setTempoEquipamentos('0.3') }} />Testar apoio da bateria com queda de irradiância</label>
            {testeIrradianciaEquipamentos ? <p>1000 → 100 W/m² em 0,12 s; retorno em 0,22 s.</p> : null}
            <button className="power-flow-btn" onClick={executarEquipamentos} disabled={executandoEquipamentos}>{executandoEquipamentos ? 'Executando Equipamentos...' : 'Executar Equipamentos - Projeto'}</button>
          </div>
          <span className="ai-simulation-status">{mensagem || `Selecionado: ${nomeArquivoSimulacao || 'JSON dos blocos atuais'}`}</span>
          {preAnalise ? <div className="ai-precheck-panel"><strong>Pré-análise da IA antes dos gráficos</strong><p>FV: {preAnalise.fvKwp.toFixed(1)} kWp · Inversor: {preAnalise.inversorKw.toFixed(1)} kW · Bateria: {preAnalise.bateriaKwh.toFixed(1)} kWh · Carga: {preAnalise.cargaKw.toFixed(1)} kW</p>{[...preAnalise.avisos, ...preAnalise.sugestoes].map((a, i) => <p key={i}>{a}</p>)}</div> : null}
          </div>
        </section> : null}

        {activeWorkspaceTab === 'unifilar' ? <SingleLineDiagram layout={layout} connectedToGrid={modeloSimulacao?.conectado_rede !== false} /> : null}
        {activeWorkspaceTab === 'resultado' ? <SimulationPanel simulacao={simulacao} microrredes={resultadoMicrorredes} transitorio={resultadoTransitorio} equipamentos={resultadoEquipamentos} /> : null}

        {activeWorkspaceTab === 'cenarios' ? <section className="scenario-panel" role="tabpanel">
          <div className="scenario-header">
            <div><h3>Comparador de cenários</h3><p>Salve simulações e compare indicadores lado a lado.</p></div>
            <div className="scenario-header-actions">
              <button className="random-version-btn" onClick={gerarVersaoAleatoria} disabled={gerandoAleatorio}>
                {gerandoAleatorio ? 'Gerando versão...' : 'Gerar versão aleatória'}
              </button>
              <button className="tariff-compare-btn" onClick={compararModalidadesTarifarias} disabled={comparandoTarifas}>{comparandoTarifas ? 'Comparando...' : 'Comparar modalidades tarifárias'}</button>
              <button className="secondary-btn" onClick={salvarCenarioAtual}>Salvar cenário atual</button>
            </div>
          </div>
          {recomendacao ? <div className="scenario-recommendation"><span>Cenário recomendado</span><strong>{recomendacao.cenario.nome}</strong><p>Critério: {recomendacao.motivo}</p></div> : null}
          {cenarios.length ? (
            <div className="scenario-table-wrap">
              <div className="scenario-winners">
                {[['Menor CAPEX', destaques.menorCapex], ['Maior economia anual', destaques.maiorEconomia], ['Melhor VPL', destaques.melhorVpl], ['Menor payback', destaques.menorPayback]].map(([titulo, id]) => <div className="scenario-winner-card" key={titulo}><span>{titulo}</span><strong>{cenarios.find((c) => c.id === id)?.nome || '-'}</strong></div>)}
              </div>
              <table className="scenario-table"><thead><tr><th>Cenário</th><th>Destaques</th><th>FV</th><th>Bateria</th><th>CAPEX</th><th>Economia anual</th><th>VPL</th><th>TIR</th><th>Payback</th><th>Ações</th></tr></thead><tbody>{cenarios.map((cenario) => {
                const m = metricasCenario(cenario)
                const badges = [destaques.menorCapex === cenario.id ? 'Menor CAPEX' : null, destaques.maiorEconomia === cenario.id ? 'Maior economia' : null, destaques.melhorVpl === cenario.id ? 'Melhor VPL' : null, destaques.menorPayback === cenario.id ? 'Menor payback' : null, recomendacao?.cenario.id === cenario.id ? 'Recomendado' : null].filter(Boolean)
                return <tr key={cenario.id} className={recomendacao?.cenario.id === cenario.id ? 'scenario-recommended-row' : ''}><td><strong>{cenario.nome}</strong><span>{new Date(cenario.criado_em).toLocaleString('pt-BR')}</span></td><td><div className="scenario-badges">{badges.length ? badges.map((b) => <span key={b}>{b}</span>) : <em>-</em>}</div></td><td>{m.fvKwp.toFixed(1)} kWp</td><td>{m.bateriaKwh.toFixed(1)} kWh</td><td>{m.capex.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}</td><td>{m.economia.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}</td><td>{m.vpl.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })}</td><td>{m.tir == null ? '-' : `${m.tir.toFixed(2)}%`}</td><td>{m.payback == null ? '-' : `${m.payback} anos`}</td><td><div className="scenario-actions"><div className="scenario-primary-actions"><button className="scenario-copy-btn" onClick={() => duplicarCenario(cenario)}>Duplicar</button><button className="scenario-delete-btn" onClick={() => apagarCenario(cenario)}>Apagar</button></div><div className="scenario-secondary-actions"><button className="scenario-run-btn" onClick={() => simularCenarioNovamente(cenario)}>Simular de novo</button></div></div></td></tr>
              })}</tbody></table>
            </div>
          ) : <p className="muted">Nenhum cenário salvo ainda.</p>}
        </section> : null}

        {activeWorkspaceTab === 'historico' ? <section className="ai-history" role="tabpanel">
          <div className="ai-history-title"><strong>Histórico de pesquisas da IA</strong><span>{historicoIa.length} registro(s)</span></div>
          <div className="ai-history-list">{historicoIa.map((item) => <article className="ai-history-item" key={item.id}><strong>{item.nome_arquivo}</strong><span>{new Date(item.criado_em).toLocaleString('pt-BR')}</span><p>{item.prompt}</p></article>)}</div>
        </section> : null}
          </div>
        </div>
      </div>
      {!['resultado', 'pop'].includes(activeWorkspaceTab) ? <Inspector selectedNode={selectedNode} selectedEdge={selectedEdge} onUpdateNode={atualizarNode} onDeleteNode={removerNode} /> : null}
    </div>
  )
}
