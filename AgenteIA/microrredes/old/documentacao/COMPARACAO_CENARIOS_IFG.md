# COMPARAÇÃO DE CENÁRIOS - CASO IFG
## Instituto Federal de Goiás - Análise Comparativa

**Data da Análise:** Janeiro 2025  
**Distribuidora:** EQUATORIAL GO  
**Modalidade Tarifária:** Verde (Grupo A4)  
**Vigência Tarifária:** 22/10/2025

---

## 📊 RESUMO EXECUTIVO

Esta análise compara 4 cenários de configuração do sistema de energia do IFG, utilizando como **base o sistema fotovoltaico de 254 kWp já instalado**.

### Cenários Avaliados

| Cenário | Descrição | PV (kWp) | BESS (kWh) | Investimento Adicional |
|---------|-----------|----------|------------|------------------------|
| **Base** | Sistema existente | 254 | 0 | R$ 0 |
| **Cenário 1** | Base + BESS | 254 | 500 | R$ 950.000 |
| **Cenário 2** | Expansão PV | 324 | 0 | R$ 245.000 |
| **Cenário 3** | Expansão PV + BESS | 324 | 500 | R$ 1.195.000 |

---

## 💰 RESULTADOS FINANCEIROS

### Custos Anuais

| Cenário | Custo Mensal | Custo Anual | Economia vs Base | % Redução |
|---------|--------------|-------------|------------------|-----------|
| Base | R$ 36.130,04 | R$ 433.560,50 | - | - |
| Cenário 1 | R$ 23.295,30 | R$ 279.543,55 | R$ 154.016,95 | 35,5% |
| Cenário 2 | R$ 32.757,44 | R$ 393.089,26 | R$ 40.471,24 | 9,3% |
| Cenário 3 | R$ 17.528,22 | R$ 210.338,58 | R$ 223.221,92 | 51,5% |

### Análise de Retorno (Payback)

| Cenário | Investimento | Economia Anual | Payback | Avaliação |
|---------|--------------|----------------|---------|-----------|
| Cenário 1 | R$ 950.000 | R$ 154.017 | **6,2 anos** | ✅ Excelente |
| Cenário 2 | R$ 245.000 | R$ 40.471 | **6,1 anos** | ✅ Excelente |
| Cenário 3 | R$ 1.195.000 | R$ 223.222 | **5,4 anos** | ✅ MELHOR |

---

## ⚡ ANÁLISE ENERGÉTICA

### Balanço Energético Mensal

| Cenário | Demanda | Geração PV | Compra Rede | Venda Rede | Autossuficiência |
|---------|---------|------------|-------------|------------|------------------|
| Base | 100.290 kWh | 53.906 kWh | 48.296 kWh | 1.911 kWh | 53,7% |
| Cenário 1 | 100.290 kWh | 53.906 kWh | 51.375 kWh | 71 kWh | 53,7% |
| Cenário 2 | 100.290 kWh | 68.808 kWh | 41.461 kWh | 9.978 kWh | 68,6% |
| Cenário 3 | 100.290 kWh | 68.808 kWh | 38.835 kWh | 2.444 kWh | 68,6% |

### Principais Observações

1. **Base (PV 254 kWp)**: Exporta 1.911 kWh/mês (~3,5% da geração) devido à falta de armazenamento
2. **Cenário 1 (+ BESS)**: Reduz exportação para 71 kWh/mês (96% de aproveitamento da energia PV)
3. **Cenário 2 (PV 324)**: Aumenta geração em 27,6%, mas exporta 9.978 kWh/mês (14,5% da geração)
4. **Cenário 3 (PV 324 + BESS)**: Máxima geração com mínima exportação (3,6%)

---

## 🔋 IMPACTO DO BESS (Bateria 500 kWh)

### Cenário 1 vs Base

- **Redução de exportação**: 1.911 → 71 kWh/mês (96% de aproveitamento)
- **Economia anual**: R$ 154.017
- **Payback**: 6,2 anos
- **Mecanismo**: Armazena excesso de PV durante o dia, descarrega na ponta (18h-21h) evitando compra a R$ 2,14/kWh

### Cenário 3 vs Cenário 2

- **Benefício adicional do BESS**: R$ 182.750/ano (R$ 223.222 - R$ 40.471)
- **Custo adicional do BESS**: R$ 950.000
- **Payback incremental**: 5,2 anos
- **Vantagem**: Com PV expandido, BESS tem mais energia para arbitragem de tarifa

---

## ☀️ IMPACTO DA EXPANSÃO PV (+70 kWp)

### Cenário 2 vs Base

- **Aumento de geração**: 53.906 → 68.808 kWh/mês (+27,6%)
- **Redução de compra**: 48.296 → 41.461 kWh/mês (-14,1%)
- **Economia anual**: R$ 40.471
- **Custo**: R$ 245.000 (70 kWp × R$ 3.500/kWp)
- **Payback**: 6,1 anos
- **Limitação**: Exporta 9.978 kWh/mês compensados a apenas R$ 0,1217/kWh (SCEE)

### Cenário 3 vs Cenário 1

- **Benefício adicional da expansão**: R$ 69.205/ano (R$ 223.222 - R$ 154.017)
- **Custo adicional da expansão**: R$ 245.000
- **Payback incremental**: 3,5 anos
- **Vantagem**: Com BESS, o PV adicional é armazenado em vez de exportado

---

## 💡 INSIGHTS CRÍTICOS

### Tarifa SCEE vs Compra

A compensação de energia exportada pela tarifa SCEE é **extremamente desfavorável**:

| Período | Compra | SCEE (Venda) | % Compensação |
|---------|--------|--------------|---------------|
| Ponta | R$ 2,1410/kWh | R$ 0,1217/kWh | **5,7%** |
| Fora Ponta | R$ 0,4535/kWh | R$ 0,1217/kWh | **26,8%** |

**Implicação**: É muito mais vantajoso **armazenar energia excedente** (BESS) do que exportar para a rede.

### Sinergia PV + BESS

A combinação de expansão fotovoltaica com bateria (Cenário 3) apresenta **efeito sinérgico**:

- PV expandido gera mais energia durante o dia
- BESS armazena excesso (evitando exportação a R$ 0,12/kWh)
- BESS descarrega na ponta (evitando compra a R$ 2,14/kWh)
- **Diferencial de arbitragem**: R$ 2,02/kWh (~1700% de retorno)

---

## 📈 OPORTUNIDADE ADICIONAL: REVISÃO DE DEMANDA

### Demanda Contratada Atual vs Ótima

| Período | Atual | Ótima | Redução |
|---------|-------|-------|---------|
| Ponta | 310 kW | 130 kW | -180 kW |
| Fora Ponta | 300 kW | 260 kW | -40 kW |

### Economia Potencial

- **Economia mensal**: R$ 1.043,20
- **Economia anual**: R$ 12.518,40
- **Ação necessária**: Solicitar revisão de demanda contratada junto à EQUATORIAL GO

---

## ✅ RECOMENDAÇÕES

### 1. Solução Ótima Recomendada: **CENÁRIO 3**

**Configuração**: PV 324 kWp + BESS 500 kWh

**Justificativa**:
- Melhor payback (5,4 anos)
- Maior economia anual (R$ 223.222)
- Redução de 51,5% nos custos de energia
- Máximo aproveitamento da geração PV (96,4%)
- Maior resiliência energética

**Investimento total**: R$ 1.195.000  
**Retorno em 10 anos**: R$ 2.232.219  
**TIR estimada**: ~18% a.a.

### 2. Alternativa Conservadora: **CENÁRIO 1**

**Configuração**: PV 254 kWp (existente) + BESS 500 kWh

**Justificativa**:
- Menor investimento (R$ 950.000)
- Payback competitivo (6,2 anos)
- Aproveita 96% da geração existente
- Redução de 35,5% nos custos

**Quando escolher**: Se há restrição orçamentária ou incerteza sobre aumento futuro de demanda.

### 3. Não Recomendado: **CENÁRIO 2**

**Configuração**: PV 324 kWp sem BESS

**Justificativa**:
- Exporta 14,5% da geração a tarifa SCEE baixíssima (R$ 0,12/kWh)
- Economia anual baixa (R$ 40.471) para investimento de R$ 245.000
- Payback similar ao Cenário 1, mas com menor economia absoluta

**Conclusão**: Expansão PV **sem BESS não é eficiente** devido à baixa compensação SCEE.

### 4. Ação Complementar: **REVISÃO DE DEMANDA**

**Independente do cenário escolhido**, revisar demanda contratada gera economia adicional de **R$ 12.518/ano** sem investimento.

---

## 🎯 CONCLUSÃO FINAL

A análise demonstra que:

1. **BESS é essencial** para maximizar o retorno do investimento fotovoltaico sob regras SCEE
2. **Cenário 3 (PV 324 + BESS 500)** apresenta melhor relação custo-benefício
3. **Payback de 5,4 anos** é excelente para projetos de geração distribuída
4. **Sinergia PV+BESS** compensa amplamente o investimento adicional
5. **Exportação de energia é ineficiente** com tarifa SCEE a R$ 0,1217/kWh

**Recomendação executiva**: Implementar **Cenário 3** e solicitar **revisão de demanda contratada** para maximizar economia total.

---

## 📝 NOTAS TÉCNICAS

### Premissas da Simulação

- **Perfil de carga**: Dados reais de fevereiro 2025 (agregação por máximo horário)
- **Painel fotovoltaico**: Canadian Solar CS6.2-66TB-610 (610 Wp, eficiência 22,6%)
- **Inversor**: Eficiência 98%
- **BESS**: 500 kWh / 200 kW, eficiência 95% (round-trip)
- **Custo BESS**: R$ 1.900/kWh
- **Custo PV**: R$ 3.500/kWp
- **Simulação**: Powerflow mensal com controle otimizado de BESS

### Estratégia de Controle do BESS

1. **Carga (8h-17h)**: Absorve excesso de PV e pode complementar com rede fora ponta
2. **Descarga (18h-21h)**: Supre ponta tarifária evitando compra a R$ 2,14/kWh
3. **Objetivo**: Maximizar arbitragem de tarifa e minimizar exportação SCEE

### Validade dos Resultados

- Tarifas ANEEL vigência 22/10/2025
- Perfil de carga representativo (fevereiro 2025)
- Custos de equipamentos atualizados (janeiro 2025)
- Não considera: incentivos fiscais, degradação de equipamentos, O&M, inflação tarifária

---

**Documento gerado automaticamente por:** `comparador_cenarios_ifg.py`  
**Gráficos disponíveis em:** `comparacao_cenarios_ifg.png`
