# 📊 ENTRADA DE DADOS DA SIMULAÇÃO - MICRORREDE

## 🏢 Configuração Geral do Sistema

### 1️⃣ **Perfil de Carga** (`perfil_carga_horaria.csv`)

#### Dias Úteis (Segunda a Sexta):
- **Demanda Mínima**: 305 kW (às 3h)
- **Demanda Máxima**: 680 kW (às 18h - horário de ponta!)
- **Demanda Média**: ~520 kW
- **Consumo Diário**: ~12.480 kWh/dia

#### Fins de Semana (Sábado e Domingo):
- **Demanda Mínima**: 245 kW (às 3h)
- **Demanda Máxima**: 455 kW (às 14h)
- **Demanda Média**: ~365 kW
- **Consumo Diário**: ~8.760 kWh/dia

#### Consumo Anual Total:
- Dias úteis: 260 dias × 12.480 kWh = **3.244.800 kWh/ano**
- Fins de semana: 105 dias × 8.760 kWh = **919.800 kWh/ano**
- **TOTAL: ~4.164.600 kWh/ano**

---

## ⚡ Tarifas de Energia (ANEEL - Vigência mais recente)

### 📍 **Distribuidora: EQUATORIAL GO**
- **Grupo Tarifário**: A4 (2,3 a 25 kV)
- **Vigência**: 2025-10-22 (mais recente da API)
- **Fonte**: API de Dados Abertos da ANEEL

### 💰 **Modalidade AZUL**:
| Componente | Ponta | Fora Ponta |
|------------|-------|------------|
| TUSD Demanda | R$ 22,46/kW | R$ 16,54/kW |
| TUSD Consumo | R$ 0,088/kWh | R$ 0,088/kWh |
| TE (Energia) | R$ 0,479/kWh | R$ 0,298/kWh |
| **Total kWh** | **R$ 0,567/kWh** | **R$ 0,386/kWh** |

### 💰 **Modalidade VERDE**:
| Componente | Ponta | Fora Ponta |
|------------|-------|------------|
| TUSD Demanda | R$ 26,08/kW (única) | - |
| TUSD Consumo | R$ 1,656/kWh | R$ 0,150/kWh |
| TE (Energia) | R$ 0,485/kWh | R$ 0,304/kWh |
| **Total kWh** | **R$ 2,141/kWh** | **R$ 0,454/kWh** |

**Horário de Ponta**: 18h às 21h (dias úteis)

---

## 🔋 Configuração da Microrrede

### **Sistema Fotovoltaico (PV)**:
- **Painel**: Canadian Solar CS6.2-66TB-610
- **Potência por painel**: 610 Wp
- **Número de painéis**: 656 unidades
- **Potência nominal total**: ~400 kW
- **Eficiência**: 22,6%
- **Degradação anual**: 0,5%
- **Eficiência do inversor**: 98%

### **Sistema de Armazenamento (BESS)**:
- **Potência máxima**: ±200 kW
- **Capacidade de energia**: 800 kWh (4 horas)
- **Tecnologia**: Baterias de íons de lítio

### **Gerador Diesel (Backup)**:
- **Potência máxima**: 300 kW
- **Consumo específico**: 0,25 L/kWh
- **Custo do diesel**: R$ 6,50/litro

---

## 💵 Parâmetros Econômicos

### **Investimento Inicial (CAPEX)**:
| Item | Custo Unitário | Quantidade | Total |
|------|---------------|-----------|-------|
| Sistema PV | R$ 3.200/kW | 400 kW | R$ 1.280.000 |
| BESS | R$ 2.200/kWh | 800 kWh | R$ 1.760.000 |
| Gerador Diesel | R$ 1.200/kW | 300 kW | R$ 360.000 |
| **Subtotal Equipamentos** | - | - | **R$ 3.400.000** |
| Custos Adicionais (15%) | - | - | R$ 510.000 |
| **CAPEX TOTAL** | - | - | **R$ 3.910.000** |

### **Parâmetros Financeiros**:
- **Vida útil do projeto**: 25 anos
- **Taxa de desconto (TMA)**: 10% a.a.
- **Custo de O&M anual**: 2% do CAPEX
- **Escalada de tarifa**: 4% a.a.
- **Compensação energia excedente**: 70% da tarifa

---

## 📈 Perfil de Geração Solar (Típico)

### **Irradiância Solar**:
- **Período de geração**: 6h às 18h
- **Pico**: 1000 W/m² (meio-dia)
- **Curva**: Senoidal típica de dia ensolarado

### **Temperatura Ambiente**:
- **Variação**: 15°C (noite) a 35°C (tarde)
- **Média**: 25°C

---

## 🎯 Estratégia de Controle

### **Prioridades**:
1. **Atender carga com PV** (durante o dia)
2. **Carregar BESS com excedente PV**
3. **Descarregar BESS quando PV < Carga**
4. **Acionar diesel apenas quando BESS esgotado**
5. **Importar/exportar da rede conforme necessário**

### **Limites Operacionais**:
- BESS: ±200 kW (carga/descarga)
- Diesel: 0 a 300 kW
- PV: 0 a 400 kW (dependente da irradiância)

---

## 📊 Formato de Dados de Entrada

### **Arquivo CSV** (`perfil_carga_horaria.csv`):
```csv
hora,demanda_kw,dia_semana
0,350,util
1,320,util
...
23,400,util
0,280,fim_semana
...
```

### **Campos**:
- `hora`: 0 a 23 (hora do dia)
- `demanda_kw`: Demanda em kW
- `dia_semana`: "util" ou "fim_semana"

---

## 🔧 Arquivos Principais

| Arquivo | Descrição |
|---------|-----------|
| `perfil_carga_horaria.csv` | Perfil de carga horária |
| `tarifas_aneel.py` | Consulta de tarifas da ANEEL (API) |
| `microrrede_powerflow.py` | Simulação de fluxo de potência |
| `analise_financeira_horaria.py` | Análise econômica com tarifas horárias |
| `fotovoltaico.py` | Modelo de painel fotovoltaico |
| `otimizador_microrrede.py` | Otimização da configuração |

---

## ✅ Checklist de Entrada de Dados

- [x] Perfil de carga horária definido (24h × 2 tipos de dia)
- [x] Tarifas atualizadas da ANEEL (API - vigência 2025-10-22)
- [x] Capacidades dos equipamentos especificadas
- [x] Custos de investimento definidos
- [x] Parâmetros econômicos configurados
- [x] Estratégia de controle implementada
- [x] Modelo de geração PV calibrado

---

## 📝 Observações Importantes

1. **As tarifas são obtidas automaticamente da API da ANEEL** - sempre a vigência mais recente
2. **Conversão corrigida**: API retorna R$/MWh → Sistema usa R$/kWh (divisão por 1000)
3. **Grupo A4**: Adequado para consumidores de média tensão (2,3 a 25 kV)
4. **Horário de ponta crítico**: 18h às 21h (tarifa muito mais alta na modalidade Verde)
5. **Perfil de carga realista**: Baseado em padrão industrial/comercial típico
