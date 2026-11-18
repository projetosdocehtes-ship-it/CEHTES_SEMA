# Relatório de Análise Financeira da Microrrede

## Resumo Executivo

Foi desenvolvido um módulo integrado de análise financeira que utiliza os resultados do **fluxo de potência** da microrrede para estimar a **redução da conta de energia elétrica**.

## Metodologia

### 1. Simulação de Fluxo de Potência
- **Ferramenta**: PandaPower (biblioteca de análise de sistemas elétricos)
- **Período**: 24 horas com resolução horária
- **Componentes simulados**:
  - Sistema Fotovoltaico (400 kW nominal)
  - Sistema de Baterias BESS (±200 kW, 800 kWh)
  - Gerador Diesel (300 kW)
  - Carga constante (500 kW)
  - Conexão com rede distribuidora (13,8 kV)

### 2. Cálculo da Economia de Energia
O módulo compara dois cenários:

#### Cenário Base (SEM Microrrede)
- Toda energia vem da distribuidora
- **Energia anual**: 4.380.000 kWh
- **Demanda contratada**: 550 kW
- **Custo total anual**: R$ 3.888.000,00
  - Custo de energia: R$ 3.723.000,00
  - Custo de demanda: R$ 165.000,00

#### Cenário COM Microrrede
- Geração distribuída (PV + Diesel + BESS)
- **Energia comprada da rede**: 4.243 kWh/ano
- **Energia gerada pelo diesel**: 2.524.577 kWh/ano
- **Custo total anual**: R$ 4.106.204,44
  - Custo de energia: R$ 3.606,42
  - Custo de demanda: R$ 160,99
  - **Custo de diesel**: R$ 4.102.437,03 ⚠️

## Resultados da Configuração Atual

### ❌ Análise de Viabilidade

**PROJETO NÃO VIÁVEL** nas condições atuais devido a:

1. **Sistema PV Subdimensionado**
   - Capacidade: 400 kW
   - Geração diária: ~280 kWh
   - Demanda diária: 12.000 kWh
   - **Atende apenas 2,3% da demanda**

2. **Uso Excessivo do Diesel**
   - Geração anual: 2.524.577 kWh
   - Custo de combustível: R$ 4.102.437,03/ano
   - **Inviabiliza o projeto economicamente**

3. **Indicadores Econômicos Negativos**
   - **VPL**: -R$ 7.948.425,36 (negativo)
   - **TIR**: Não definida (sem retorno)
   - **Payback**: Não atingido em 20 anos
   - **Economia**: -R$ 218.204,44/ano (prejuízo)

### Investimento Inicial (CAPEX)
- Sistema Fotovoltaico (400 kW): R$ 1.400.560,00
- Sistema de Baterias (800 kWh): R$ 2.000.000,00
- Gerador Diesel (300 kW): R$ 360.000,00
- Custos adicionais: R$ 564.084,00
- **CAPEX Total**: R$ 4.324.644,00

## Recomendações para Viabilização

### 1. Aumentar Capacidade Fotovoltaica
Para atender maior parte da demanda:
- **Capacidade recomendada**: 2.000-3.000 kW
- **Justificativa**: Cobrir pelo menos 50-70% da demanda diária
- **Impacto**: Redução drástica do uso de diesel

### 2. Otimizar Sistema de Baterias
- **Capacidade atual**: 800 kWh (4h @ 200 kW)
- **Recomendação**: Aumentar para 2.000-3.000 kWh
- **Objetivo**: Armazenar excesso solar para uso noturno

### 3. Reduzir Dependência do Diesel
- **Uso atual**: 2.524.577 kWh/ano (57% da energia)
- **Meta**: < 5% da energia (backup apenas)
- **Estratégia**: Dimensionar PV + BESS adequadamente

### 4. Análise de Sensibilidade
O sistema permite simular diferentes cenários variando:
- Tarifa de energia (impacto direto na economia)
- Capacidade dos sistemas
- Custos de equipamentos
- Taxa de desconto

## Funcionalidades do Módulo

### `analise_financeira.py`
```python
class AnaliseFinanceiraMicrorrede:
    - executar_simulacao_powerflow()      # Roda simulação elétrica
    - calcular_custos_sem_microrrede()    # Cenário base
    - calcular_custos_com_microrrede()    # Cenário com GD
    - calcular_capex()                     # Investimento inicial
    - calcular_economia_anual()            # Economia por ano
    - calcular_vpl()                       # Valor Presente Líquido
    - calcular_tir()                       # Taxa Interna de Retorno
    - calcular_payback_descontado()        # Período de retorno
    - gerar_relatorio_completo()           # Relatório detalhado
    - plotar_analise_financeira()          # Gráficos
```

### Integrações
- ✅ **PandaPower**: Fluxo de potência AC
- ✅ **Modelo PV real**: Canadian Solar CS6.2-66TB-610 (610W)
- ✅ **Curvas I-V**: Dependentes de temperatura e irradiância
- ✅ **Numpy Financial**: VPL, TIR, Payback
- ✅ **Matplotlib**: Visualizações

## Gráficos Gerados

1. **Comparação de Custos Anuais**
   - Barras comparativas entre cenários
   - Economia anual destacada

2. **Fluxo de Caixa Anual**
   - Investimento inicial (ano 0)
   - Fluxos anuais (positivo/negativo)

3. **Payback Descontado**
   - Saldo acumulado ao longo dos anos
   - Ponto de equilíbrio (se houver)
   - VPL e TIR

4. **Análise de Sensibilidade**
   - Economia vs Variação da Tarifa
   - Identifica cenários viáveis

5. **Resultados do Fluxo de Potência**
   - Geração PV, BESS, Diesel
   - Fluxo no ponto de conexão
   - Perfil de tensão
   - Perfil de corrente

## Como Usar

### Executar Análise Completa
```bash
python analise_financeira.py
```

### Personalizar Parâmetros
```python
analise = AnaliseFinanceiraMicrorrede(
    tarifa_energia_kwh=0.85,    # R$/kWh
    tarifa_demanda_kw=25.0,     # R$/kW/mês
    vida_util=20,               # anos
    taxa_desconto=0.08          # 8% a.a.
)
```

### Modificar Configuração da Microrrede
Editar `microrrede_powerflow.py`:
```python
# Aumentar capacidade PV
self.num_paineis = 3280  # ~2000 kW

# Aumentar BESS
bess_max_mw = 0.5  # 500 kW
```

## Próximos Passos

1. **Otimização do Dimensionamento**
   - Criar função objetivo: maximizar VPL
   - Variáveis: capacidade PV, BESS, Diesel
   - Restrições: orçamento, espaço, regulatórias

2. **Modelagem Estocástica**
   - Variação de irradiância (dias nublados)
   - Variação de demanda (perfil industrial)
   - Análise de Monte Carlo

3. **Estratégias de Controle Avançadas**
   - Previsão de geração solar
   - Otimização do despacho (BESS/Diesel)
   - Resposta à demanda

4. **Análise Regulatória**
   - GD na REN 687/2015 e REN 482/2012
   - Compensação de energia
   - Tarifas diferenciadas

## Conclusão

O módulo de análise financeira integrado ao fluxo de potência permite:

✅ **Quantificar economia** baseada em simulação elétrica realista  
✅ **Avaliar viabilidade** através de VPL, TIR e Payback  
✅ **Identificar gargalos** no dimensionamento  
✅ **Otimizar configuração** através de análise de sensibilidade  

**Resultado atual**: Sistema subdimensionado (PV) e custo excessivo de diesel inviabilizam o projeto.

**Solução**: Aumentar capacidade PV para 2-3 MW e BESS para 2-3 MWh para viabilizar economicamente.
