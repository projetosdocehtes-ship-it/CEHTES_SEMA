# Modificações na Classe TarifasANEEL

## Objetivo
Alterar a classe `TarifasANEEL` para buscar apenas as tarifas da distribuidora de interesse, ao invés de baixar todas as tarifas disponíveis da API da ANEEL.

## Mudanças Implementadas

### 1. **API Endpoint Atualizado**
- **Antes**: Baixava o arquivo CSV completo com todas as distribuidoras
  ```python
  API_URL = "https://dadosabertos.aneel.gov.br/.../tarifas-homologadas-distribuidoras-energia-eletrica.csv"
  ```

- **Depois**: Usa o endpoint de busca com filtro por distribuidora
  ```python
  API_BASE_URL = "https://dadosabertos.aneel.gov.br/api/3/action/datastore_search"
  RESOURCE_ID = "fcf2906c-7c32-4b9b-a637-054e7a5234f4"
  ```

### 2. **Método `_buscar_dados_api` Modificado**
- Agora aceita parâmetros `distribuidora_query` e `grupo`
- Faz requisição filtrada usando o parâmetro `q` (query)
- Retorna apenas dados da distribuidora especificada
- Sistema de cache por distribuidora (ao invés de cache global)

**Exemplo de requisição:**
```
GET https://dadosabertos.aneel.gov.br/api/3/action/datastore_search?
    resource_id=fcf2906c-7c32-4b9b-a637-054e7a5234f4&
    q=Equatorial%20GO&
    limit=1000
```

### 3. **Método `_extrair_tarifas_api` Reescrito**
A API da ANEEL retorna dados em formato granular (um registro por componente tarifário), não consolidado. Exemplos:
- Um registro para "TUSD Demanda Ponta"
- Outro registro para "TUSD Demanda Fora Ponta"
- Outro para "TE Ponta", etc.

**Nova lógica:**
- Agrega múltiplos registros da API
- Converte valores do formato brasileiro (vírgula decimal)
- Separa tarifas por modalidade (Azul e Verde)
- Identifica componentes por análise de colunas `DscDetalhe` e `NomPostoTarifario`

### 4. **Método `_carregar_dados_api` Atualizado**
- Filtra apenas modalidades Azul e Verde
- Seleciona automaticamente a vigência mais recente
- Passa DataFrame completo para agregação (ao invés de registro único)

### 5. **Cache Aprimorado**
- **Antes**: Cache global único para todos os dados
- **Depois**: Cache por distribuidora usando dicionário com chaves `{distribuidora}_{grupo}`
- Permite múltiplas distribuidoras em memória simultaneamente

### 6. **Fallback Data Atualizado**
- Suporte a variações de nomes (ex: "EQUATORIAL GO" e "EQUATORIAL GOIAS")
- Normalização automática de nomes com `replace('_', ' ')`

## Estrutura da API da ANEEL

### Colunas Principais Retornadas:
```python
{
  "SigAgente": "EQUATORIAL GO",
  "NumCNPJDistribuidora": "01543032000104",
  "DatInicioVigencia": "2013-04-08",
  "DscSubGrupo": "A4",
  "DscModalidadeTarifaria": "Azul",
  "DscDetalhe": "APE",
  "NomPostoTarifario": "Ponta",
  "VlrTUSD": "48,67",
  "VlrTE": "0,74"
}
```

### Mapeamento de Componentes:
| Componente | Identificação |
|------------|---------------|
| TUSD Demanda Ponta | `DscDetalhe` contém "Demanda" + `NomPostoTarifario` = "Ponta" |
| TUSD Demanda Fora Ponta | `DscDetalhe` contém "Demanda" + `NomPostoTarifario` = "Fora ponta" |
| TUSD Consumo Ponta | `DscDetalhe` contém "Consumo" + `NomPostoTarifario` = "Ponta" |
| TE Ponta | `VlrTE` > 0 + `NomPostoTarifario` = "Ponta" |

## Benefícios

### 1. **Performance**
- ✅ Não baixa mais ~100MB de dados desnecessários
- ✅ Requisições mais rápidas (apenas dados filtrados)
- ✅ Menor uso de memória

### 2. **Escalabilidade**
- ✅ Cache independente por distribuidora
- ✅ Suporta múltiplas distribuidoras simultaneamente
- ✅ Não sobrecarrega a API da ANEEL

### 3. **Confiabilidade**
- ✅ Menos dados transferidos = menos chance de timeout
- ✅ Fallback automático em caso de falha
- ✅ Validações específicas por distribuidora

## Uso

### Básico:
```python
from tarifas_aneel import TarifasANEEL

# Busca apenas Equatorial GO
tarifa = TarifasANEEL(distribuidora='EQUATORIAL GO', usar_api=True, grupo='A4')

info = tarifa.get_info_distribuidora()
azul = tarifa.get_tarifas_azul()
verde = tarifa.get_tarifas_verde()
```

### Nomes Aceitos:
- `'EQUATORIAL GO'` (formato da API)
- `'EQUATORIAL_GO'` (normalizado automaticamente)
- `'EQUATORIAL GOIAS'` (alias no fallback)
- `'CEMIG'`
- `'ENEL GOIAS'`
- `'CPFL PAULISTA'`

## Compatibilidade

✅ **Totalmente retrocompatível** com código existente
- Mesma interface pública
- Mesmos métodos disponíveis
- Mesma estrutura de dados retornada

## Exemplo de Saída

```
Buscando tarifas da API da ANEEL para 'EQUATORIAL GO'...
✓ 154 registros carregados da API
✓ Tarifas carregadas: EQUATORIAL GO (vigência: 2024-06-22)

Tarifas Modalidade Azul:
  TUSD Demanda Ponta: R$ 48.67/kW
  TUSD Demanda Fora Ponta: R$ 6.92/kW
  TUSD Consumo Ponta: R$ 0.8900/kWh
  TUSD Consumo Fora Ponta: R$ 0.2700/kWh
  TE Ponta: R$ 0.7400/kWh
  TE Fora Ponta: R$ 0.5800/kWh
```

## Testes

Execute o script de teste:
```bash
python teste_tarifas_api.py
```

Ou teste rápido:
```bash
python teste_rapido.py
```
